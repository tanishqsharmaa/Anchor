import asyncio
import json
from pathlib import Path
import time
from typing import Any, AsyncGenerator
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from anchor.config import settings
from anchor.ingest.indexer import TripleStoreIndexer
from anchor.retrieve.resolver import clear_resolver_cache

router = APIRouter(tags=["ingest"])
_indexer: TripleStoreIndexer | None = None


def get_indexer() -> TripleStoreIndexer:
    global _indexer
    if _indexer is None:
        _indexer = TripleStoreIndexer()
    return _indexer


class IngestRequest(BaseModel):
    pdf_paths: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="List of relative PDF paths to ingest (empty for all)",
    )
    force_reindex: bool = Field(
        default=False,
        description="Whether to purge existing index prior to indexing",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream real-time SSE ingestion progress events (ENH-007)",
    )


async def generate_ingest_stream(req: IngestRequest) -> AsyncGenerator[dict[str, str], None]:
    """Stream SSE progress events during batch PDF ingestion (ENH-007)."""
    indexer = get_indexer()
    if req.force_reindex:
        indexer.purge_stores()
    clear_resolver_cache()

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def progress_callback(event_payload: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event_payload)

    def run_indexing():
        try:
            res = indexer.index_all_regulatory_pdfs(
                pdfs_dir=settings.PDFS_DIR,
                force_reindex=req.force_reindex,
                progress_callback=progress_callback,
            )
            loop.call_soon_threadsafe(queue.put_nowait, {"_done": True, "result": res})
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, {"_error": str(e)})

    # Run in background thread
    indexing_task = asyncio.create_task(asyncio.to_thread(run_indexing))

    while True:
        event = await queue.get()
        if "_done" in event:
            res = event["result"]
            yield {
                "event": "message",
                "data": json.dumps({
                    "stage": "complete",
                    "data": {
                        "total_chunks": res["total_chunks"],
                        "total_documents": res["total_documents"],
                        "elapsed_ms": res["elapsed_ms"],
                    },
                }),
            }
            break
        elif "_error" in event:
            yield {
                "event": "message",
                "data": json.dumps({
                    "stage": "error",
                    "data": {"error": event["_error"]},
                }),
            }
            break
        else:
            yield {
                "event": "message",
                "data": json.dumps(event),
            }

    await indexing_task


@router.post("/ingest", status_code=status.HTTP_200_OK)
async def ingest_documents(req: IngestRequest) -> Any:
    """
    Ingest regulatory PDFs into LanceDB, Tantivy, and SQLite.
    If pdf_paths is empty, ingests the full regulatory corpus from settings.PDFS_DIR.
    Supports SSE streaming progress when req.stream=True (ENH-007).
    """
    # 1. Path traversal security sanitization
    for p in req.pdf_paths:
        if (
            ".." in p
            or p.startswith("/")
            or "\\" in p
            or ":" in p
            or "\x00" in p
            or Path(p).is_absolute()
        ):
            return {
                "success": False,
                "error": {
                    "code": "PATH_TRAVERSAL_REJECTED",
                    "message": f"Illegal path traversal sequence in path: {p}",
                },
            }

    # Invalidate cached structured results (ENH-003)
    clear_resolver_cache()

    if req.stream:
        return EventSourceResponse(
            generate_ingest_stream(req),
            media_type="text/event-stream",
        )

    indexer = get_indexer()
    start_time = time.perf_counter()

    if req.force_reindex:
        indexer.purge_stores()

    total_chunks = 0
    docs_processed = 0

    if not req.pdf_paths:
        # Ingest entire regulatory corpus
        res = indexer.index_all_regulatory_pdfs(
            pdfs_dir=settings.PDFS_DIR, force_reindex=req.force_reindex
        )
        total_chunks = res["total_chunks"]
        docs_processed = res["total_documents"]
    else:
        for rel_path in req.pdf_paths:
            cand1 = settings.BASE_DIR / rel_path
            cand2 = settings.PDFS_DIR / rel_path
            target_file = cand1 if cand1.is_file() else cand2

            if not target_file.is_file():
                return {
                    "success": False,
                    "error": {
                        "code": "FILE_NOT_FOUND",
                        "message": f"Specified PDF file was not found: {rel_path}",
                    },
                }

            chunks = indexer.index_pdf_document(target_file)
            total_chunks += len(chunks)
            docs_processed += 1

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

    return {
        "success": True,
        "data": {
            "chunks_indexed": total_chunks,
            "documents_processed": docs_processed,
            "time_ms": elapsed_ms,
        },
    }
