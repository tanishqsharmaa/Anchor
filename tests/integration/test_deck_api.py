"""
test_deck_api.py — Integration Tests for AutoDeck API Endpoints
"""

from fastapi.testclient import TestClient
import pytest

from anchor.main import app

client = TestClient(app)


def test_generate_deck_endpoint_schedule():
    response = client.post(
        "/deck",
        json={
            "topic": "DFPDS Schedule 7 Tactical Drones",
            "schedule_no": 7,
            "num_slides": 4,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert "deck_id" in data
    assert len(data["html_slides"]) == 4
    assert "pptx_url" in data
    assert data["verification_report"]["all_claims_verified"] is True
    assert data["generation_time_ms"] >= 0

    deck_id = data["deck_id"]

    # Test binary download
    dl_response = client.get(f"/deck/{deck_id}/download")
    assert dl_response.status_code == 200
    assert "presentation" in dl_response.headers["content-type"]
    assert len(dl_response.content) > 1000


def test_download_deck_not_found():
    response = client.get("/deck/deck_non_existent_999999/download")
    assert response.status_code == 404


def test_download_deck_path_traversal_rejection():
    response = client.get("/deck/..%2F..%2Fsecret/download")
    assert response.status_code in [400, 404]
