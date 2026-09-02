"""
test_ingest_endpoint.py — Unit Tests for Live Ingestion API Endpoint & Readiness Probe
"""

from fastapi.testclient import TestClient
from anchor.main import app


def test_ingest_endpoint_path_traversal_rejection():
    """Assert POST /ingest rejects path traversal attempts."""
    with TestClient(app) as client:
        response = client.post(
            "/ingest",
            json={"pdf_paths": ["../../etc/passwd"], "force_reindex": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "PATH_TRAVERSAL_REJECTED"


def test_ingest_endpoint_single_document():
    """Assert POST /ingest successfully indexes a specified relative PDF."""
    with TestClient(app) as client:
        response = client.post(
            "/ingest",
            json={"pdf_paths": ["DFPDS_2026_Schedule_07.pdf"], "force_reindex": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["chunks_indexed"] > 0
        assert data["data"]["documents_processed"] == 1


def test_ready_probe_reflects_chunks():
    """Assert GET /ready reports accurate store availability and chunk count."""
    with TestClient(app) as client:
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert data["chunks_indexed"] >= 0
        assert data["stores"]["lancedb"] is True
        assert data["stores"]["tantivy"] is True
        assert data["stores"]["sqlite"] is True
