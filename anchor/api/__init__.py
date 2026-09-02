"""
anchor.api — FastAPI Route Handlers for PROJECT ANCHOR
"""

from anchor.api.routes_ingest import router as ingest_router

__all__ = ["ingest_router"]
