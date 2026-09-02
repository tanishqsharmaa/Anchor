import asyncio
from contextlib import asynccontextmanager
import json
import logging
import sys
import time
from typing import Any, AsyncGenerator, Optional
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel, Field

from anchor.config import settings
from anchor.stores.sqlite_store import get_sqlite_connection
from anchor.stores.lancedb_store import count_chunks
from anchor.stores.tantivy_store import count_documents


# 1. Structured Logging with JSON Lines Output (ENH-020)
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def configure_logging() -> None:
    if settings.LOG_JSON_LINES:
        root_logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        root_logger.handlers = [handler]
        root_logger.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)


configure_logging()
logger = logging.getLogger(__name__)

# Global in-flight query tracker for graceful shutdown (ENH-021)
_in_flight_queries: int = 0
_in_flight_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for PROJECT ANCHOR backend services."""
    # 1. Startup phase: Verify core paths & stores
    target_db = settings.SQLITE_PATH
    target_db.parent.mkdir(parents=True, exist_ok=True)
    try:
        from anchor.stores.sqlite_store import init_sqlite_db
        init_sqlite_db(target_db)
    except Exception as e:
        logger.warning(f"Failed to auto-init SQLite DB on startup: {e}")
    logger.info(f"[{settings.APP_NAME}] Backend initialized in {settings.ENVIRONMENT} mode.")
    yield
    # 2. Shutdown phase: Graceful in-flight query drain (ENH-021)
    logger.info(f"[{settings.APP_NAME}] Shutdown initiated. Draining in-flight requests...")
    drain_start = time.time()
    while True:
        async with _in_flight_lock:
            in_flight = _in_flight_queries
        if in_flight <= 0 or (time.time() - drain_start) >= 10.0:
            break
        await asyncio.sleep(0.1)
    logger.info(f"[{settings.APP_NAME}] Graceful shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Sovereign, air-gapped, zero-hallucination regulatory AI intelligence system for the Indian Navy.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware for Next.js 15 Tactical Console (Localhost only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Rate Limiting Storage: IP -> list of request timestamps (ENH-016)
_rate_limit_records: dict[str, list[float]] = {}


@app.middleware("http")
async def rate_limit_and_auth_middleware(request: Request, call_next) -> Response:
    """
    Enforces Rate Limiting (ENH-016), Session Auth (ENH-018), and In-Flight Request Tracking (ENH-021).
    """
    global _in_flight_queries
    path = request.url.path

    # Public exemptions
    public_paths = {"/health", "/ready", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}
    if path in public_paths or path.startswith("/docs") or path.startswith("/pdf/"):
        return await call_next(request)

    # 1. Session-Level Authentication check (ENH-018)
    if settings.AUTH_PIN:
        pin = request.headers.get("X-Session-PIN")
        auth_hdr = request.headers.get("Authorization", "")
        bearer_pin = auth_hdr.replace("Bearer ", "").strip() if auth_hdr.startswith("Bearer ") else None
        if pin != settings.AUTH_PIN and bearer_pin != settings.AUTH_PIN:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": {
                        "code": "UNAUTHORIZED_SESSION",
                        "message": "Valid X-Session-PIN or Bearer token is required.",
                    },
                },
            )

    # 2. Rate Limiting Sliding Window (ENH-016)
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    cutoff = now - 60.0

    # Periodic cleanup of expired IPs if dict grows large
    if len(_rate_limit_records) > 200:
        stale_ips = [ip for ip, t_list in list(_rate_limit_records.items()) if not t_list or t_list[-1] < cutoff]
        for ip in stale_ips:
            _rate_limit_records.pop(ip, None)

    timestamps = _rate_limit_records.setdefault(client_ip, [])
    # Prune timestamps older than 60s
    _rate_limit_records[client_ip] = [ts for ts in timestamps if ts >= cutoff]
    if len(_rate_limit_records[client_ip]) >= settings.RATE_LIMIT_RPM:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit of {settings.RATE_LIMIT_RPM} requests per minute exceeded.",
                },
            },
        )
    _rate_limit_records[client_ip].append(now)

    # 3. Track in-flight queries (ENH-021)
    is_query = path.startswith("/query") or path.startswith("/deck") or path.startswith("/ingest")
    if is_query:
        async with _in_flight_lock:
            _in_flight_queries += 1

    try:
        response: Response = await call_next(request)
        return response
    finally:
        if is_query:
            async with _in_flight_lock:
                _in_flight_queries = max(0, _in_flight_queries - 1)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    """Inject defensive security headers on all HTTP responses."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "frame-ancestors 'self' http://localhost:3000 http://127.0.0.1:3000; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' http://localhost:8000 http://localhost:11434 http://127.0.0.1:8000 http://127.0.0.1:11434;"
    )
    return response


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, Any]:
    """Liveness probe returning server status, model residency metadata, and live Ollama watchdog check (ENH-006)."""
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            res = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            ollama_ok = res.status_code == 200
    except Exception:
        ollama_ok = False

    return {
        "status": "ok",
        "version": settings.VERSION,
        "models_loaded": ["deberta-v3-nli"],
        "ollama_available": ollama_ok,
    }


@app.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> dict[str, Any]:
    """Readiness probe checking SQLite, LanceDB, and Tantivy store states."""
    sqlite_ok = False
    schedules_loaded = 0
    try:
        conn = get_sqlite_connection()
        cursor = conn.execute("SELECT COUNT(DISTINCT schedule_no) FROM dfpds_2026;")
        row = cursor.fetchone()
        if row:
            schedules_loaded = int(row[0])
            sqlite_ok = schedules_loaded > 0
        conn.close()
    except Exception:
        sqlite_ok = False

    lancedb_ok = False
    chunks_indexed = 0
    try:
        chunks_indexed = count_chunks()
        lancedb_ok = True
    except Exception:
        lancedb_ok = False

    tantivy_ok = False
    try:
        _ = count_documents()
        tantivy_ok = True
    except Exception:
        tantivy_ok = False

    all_ready = sqlite_ok and lancedb_ok and tantivy_ok

    return {
        "ready": all_ready,
        "chunks_indexed": chunks_indexed,
        "schedules_loaded": schedules_loaded,
        "stores": {
            "sqlite": sqlite_ok,
            "lancedb": lancedb_ok,
            "tantivy": tantivy_ok,
        },
    }


from anchor.api.routes_ingest import router as ingest_router
from anchor.api.routes_query import router as query_router
from anchor.api.routes_deck import router as deck_router
from anchor.api.routes_eval import router as eval_router

app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(deck_router)
app.include_router(eval_router)


@app.get("/pdf/{doc_name}", status_code=status.HTTP_200_OK)
async def serve_regulatory_pdf(doc_name: str):
    """
    GET /pdf/{doc_name}: Serve raw regulatory gazette PDF for the frontend
    PDF citation inspector with strict path traversal validation.
    """
    import re
    from fastapi.responses import FileResponse, JSONResponse

    if not re.match(r"^[a-zA-Z0-9_\-]+\.pdf$", doc_name):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "INVALID_FILENAME",
                    "message": f"Document name '{doc_name}' contains invalid characters or path traversal elements.",
                },
            },
        )

    pdf_file = settings.PDFS_DIR / doc_name
    try:
        pdf_file = pdf_file.resolve()
        pdfs_dir = settings.PDFS_DIR.resolve()
        if not str(pdf_file).startswith(str(pdfs_dir)):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "success": False,
                    "error": {
                        "code": "PATH_TRAVERSAL_REJECTED",
                        "message": "Access outside PDF repository is forbidden.",
                    },
                },
            )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "PATH_RESOLUTION_FAILED",
                    "message": "Failed to resolve file path.",
                },
            },
        )

    if not pdf_file.exists() or not pdf_file.is_file():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "DOCUMENT_NOT_FOUND",
                    "message": f"Regulatory PDF '{doc_name}' not found.",
                },
            },
        )

    return FileResponse(
        path=pdf_file,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={doc_name}",
            "Cache-Control": "public, max-age=3600",
        },
    )

