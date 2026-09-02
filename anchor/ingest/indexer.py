"""
indexer.py — Triple-Store Parallel Indexing Engine for LanceDB, Tantivy, and SQLite
"""

from pathlib import Path
import hashlib
import time
from typing import Any, Callable, Optional, Union
import shutil

from anchor.config import settings
from anchor.models.embedder import BGEEmbedder
from anchor.ingest.pdf_parser import parse_pdf_layout
from anchor.ingest.clause_parser import parse_regulatory_hierarchy
from anchor.ingest.chunker import chunk_regulatory_hierarchy, RegulatoryChunk
from anchor.stores.lancedb_store import (
    get_lancedb_connection,
    init_lancedb_table,
    insert_chunks,
    count_chunks,
    clear_lancedb_cache,
)
from anchor.stores.tantivy_store import (
    get_or_create_tantivy_index,
    add_documents,
    count_documents,
    clear_tantivy_cache,
)
from anchor.stores.sqlite_store import (
    get_manifest_entry,
    update_manifest_entry,
    clear_manifest,
)


def compute_file_hash(path: Path) -> str:
    """Compute SHA-256 checksum of a file on disk."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class TripleStoreIndexer:
    """Coordinates parsing, chunking, embedding, and parallel triple-store indexing with incremental delta detection."""

    def __init__(self, embedder: Optional[BGEEmbedder] = None) -> None:
        self._embedder = embedder

    @property
    def embedder(self) -> BGEEmbedder:
        if self._embedder is None:
            self._embedder = BGEEmbedder()
        return self._embedder

    def purge_stores(self) -> None:
        """Purge and recreate LanceDB table, Tantivy index, and PDF manifest."""
        # Clear module caches
        clear_lancedb_cache()
        clear_tantivy_cache()

        # Purge LanceDB table
        try:
            db = get_lancedb_connection()
            try:
                db.drop_table("regulatory_chunks")
            except Exception:
                pass
            init_lancedb_table()
        except Exception:
            pass

        # Purge Tantivy index
        try:
            if settings.TANTIVY_DIR.exists():
                shutil.rmtree(settings.TANTIVY_DIR)
            get_or_create_tantivy_index()
        except Exception:
            pass

        # Purge Manifest
        try:
            clear_manifest()
        except Exception:
            pass

    def index_pdf_document(
        self,
        pdf_path: Union[Path, str],
    ) -> list[RegulatoryChunk]:
        """
        Process and index a single regulatory PDF document across all triple stores.

        Args:
            pdf_path: Path to the regulatory PDF.

        Returns:
            List of indexed RegulatoryChunk objects.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF document not found: {path}")

        # 1. Layout Parse
        layout = parse_pdf_layout(path)

        # 2. Hierarchy Decomposition
        hierarchy = parse_regulatory_hierarchy(layout)

        # 3. Semantic Token Chunking
        chunks = chunk_regulatory_hierarchy(hierarchy)
        if not chunks:
            return []

        # 4. Generate 1024-d Dense Embeddings
        chunk_texts = [c.text for c in chunks]
        embeddings = self.embedder.encode(chunk_texts, batch_size=16)

        # 5. LanceDB Batch Write
        lancedb_records = []
        for idx, chunk in enumerate(chunks):
            lancedb_records.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "schedule_no": int(chunk.schedule_no),
                    "section": chunk.section,
                    "page_no": int(chunk.page_no),
                    "bbox": [float(x) for x in chunk.bbox],
                    "text": chunk.text,
                    "sha256": chunk.sha256,
                    "vector": [float(v) for v in embeddings[idx]],
                }
            )
        insert_chunks(lancedb_records)

        # 6. Tantivy BM25 Batch Write
        tantivy_records = []
        for chunk in chunks:
            tantivy_records.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "section": chunk.section,
                    "breadcrumb": chunk.breadcrumb,
                    "text": chunk.text,
                    "schedule_no": int(chunk.schedule_no),
                    "sha256": chunk.sha256,
                }
            )
        add_documents(tantivy_records)

        # 7. Update Manifest (ENH-022)
        try:
            f_hash = compute_file_hash(path)
            update_manifest_entry(path.name, f_hash, len(chunks))
        except Exception:
            pass

        return chunks

    def index_all_regulatory_pdfs(
        self,
        pdfs_dir: Optional[Union[Path, str]] = None,
        force_reindex: bool = False,
        progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        """
        Index all regulatory PDFs from the specified directory with delta skipping and progress reporting.

        Args:
            pdfs_dir: Target directory containing regulatory PDFs (defaults to settings.PDFS_DIR).
            force_reindex: Whether to purge existing index prior to indexing.
            progress_callback: Optional callback for streaming progress events (ENH-007).

        Returns:
            Dictionary containing indexing summary telemetry.
        """
        target_dir = Path(pdfs_dir) if pdfs_dir else settings.PDFS_DIR
        if not target_dir.exists():
            raise FileNotFoundError(f"PDFs directory not found: {target_dir}")

        if force_reindex:
            self.purge_stores()

        pdf_files = sorted(list(target_dir.glob("*.pdf")))
        total_files = len(pdf_files)
        if not pdf_files:
            if progress_callback:
                progress_callback({
                    "stage": "complete",
                    "data": {"total_chunks": 0, "total_documents": 0},
                })
            return {
                "total_chunks": 0,
                "total_documents": 0,
                "elapsed_ms": 0,
                "documents": [],
            }

        start_time = time.perf_counter()
        total_chunks = 0
        processed_docs = []

        for idx, pdf_file in enumerate(pdf_files, start=1):
            f_hash = compute_file_hash(pdf_file)
            manifest = get_manifest_entry(pdf_file.name)

            # Incremental Re-Indexing Check (ENH-022)
            if not force_reindex and manifest and manifest["sha256"] == f_hash:
                total_chunks += int(manifest.get("chunk_count", 0))
                processed_docs.append(pdf_file.name)
                if progress_callback:
                    progress_callback({
                        "stage": "indexing",
                        "data": {
                            "document": pdf_file.name,
                            "status": "cached",
                            "chunks_so_far": total_chunks,
                            "progress": f"{idx}/{total_files}",
                        },
                    })
                continue

            if progress_callback:
                progress_callback({
                    "stage": "parsing",
                    "data": {
                        "document": pdf_file.name,
                        "progress": f"{idx}/{total_files}",
                    },
                })

            chunks = self.index_pdf_document(pdf_file)
            total_chunks += len(chunks)
            processed_docs.append(pdf_file.name)

            if progress_callback:
                progress_callback({
                    "stage": "indexing",
                    "data": {
                        "document": pdf_file.name,
                        "chunks_so_far": total_chunks,
                        "progress": f"{idx}/{total_files}",
                    },
                })

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        if progress_callback:
            progress_callback({
                "stage": "complete",
                "data": {
                    "total_chunks": total_chunks,
                    "total_documents": len(processed_docs),
                    "elapsed_ms": elapsed_ms,
                },
            })

        return {
            "total_chunks": total_chunks,
            "total_documents": len(processed_docs),
            "elapsed_ms": elapsed_ms,
            "documents": processed_docs,
        }
