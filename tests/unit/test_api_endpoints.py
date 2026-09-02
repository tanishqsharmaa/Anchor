from fastapi.testclient import TestClient
import pytest
from anchor.main import app

client = TestClient(app)

def test_get_health_endpoint():
    """Test GET /health returns liveness status and model registry."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert isinstance(data["models_loaded"], list)
    assert "ollama_available" in data

def test_get_ready_endpoint():
    """Test GET /ready returns store connectivity and readiness status."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["schedules_loaded"] == 32
    assert "stores" in data
    assert data["stores"]["sqlite"] is True
    assert data["stores"]["lancedb"] is True
    assert data["stores"]["tantivy"] is True

def test_cors_headers_configured():
    """Test CORS preflight headers accept tactical console origins."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") in [
        "http://localhost:3000",
        "*",
    ]

def test_stub_endpoints():
    """Test /ingest path traversal check and /query responses."""
    res_trav = client.post("/ingest", json={"pdf_paths": ["../etc/passwd"]})
    assert res_trav.status_code == 200
    assert res_trav.json()["success"] is False
    assert res_trav.json()["error"]["code"] == "PATH_TRAVERSAL_REJECTED"

    res_query = client.post(
        "/query",
        json={"question": "What is the financial limit for Chief of Naval Staff under Schedule 1 with IFA?", "stream": False},
    )
    assert res_query.status_code == 200
    assert res_query.json()["success"] is True


def test_get_eval_endpoint():
    """Test GET /eval returns statutory metric scores."""
    response = client.get("/eval")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    metrics = data["data"]
    assert "faithfulness" in metrics
    assert "citation_precision" in metrics
    assert "context_recall" in metrics
    assert "hallucination_rate" in metrics
    assert "abstention_accuracy" in metrics
    assert "structured_accuracy" in metrics
    assert "peak_ram_gb" in metrics
    assert metrics["faithfulness"] >= 0.92
    assert metrics["citation_precision"] >= 0.95


def test_post_eval_run_endpoint():
    """Test POST /eval/run returns benchmark run results and quality gate status."""
    response = client.post("/eval/run")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["passed"] is True
    assert "metrics" in data["data"]
    assert "thresholds" in data["data"]


def test_get_pdf_endpoint_success():
    """Test GET /pdf/{doc_name} serves binary PDF with correct headers."""
    response = client.get("/pdf/DFPDS_2026_Schedule_01.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "inline" in response.headers["content-disposition"]
    assert len(response.content) > 100


def test_get_pdf_endpoint_path_traversal():
    """Test GET /pdf/{doc_name} rejects path traversal attempts."""
    # Invalid characters / dotdot in path parameter
    res1 = client.get("/pdf/..%2F..%2Fsecret.pdf")
    assert res1.status_code in [400, 403, 404]

    res2 = client.get("/pdf/invalid*name.pdf")
    assert res2.status_code == 400
    assert res2.json()["error"]["code"] == "INVALID_FILENAME"


def test_get_pdf_endpoint_not_found():
    """Test GET /pdf/{doc_name} returns 404 for missing PDF file."""
    response = client.get("/pdf/NonExistent_Schedule_99.pdf")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"

