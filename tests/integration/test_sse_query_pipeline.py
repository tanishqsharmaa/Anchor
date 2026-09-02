"""
test_sse_query_pipeline.py — Integration Tests for Dual-Path SSE Streaming Query Route
"""

import json
import time
import pytest
from fastapi.testclient import TestClient

from anchor.main import app
from anchor.trust.hash import verify_sha256


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _parse_sse_events(response_text: str) -> list[dict]:
    """Parse raw SSE text/event-stream into a list of parsed JSON event payloads."""
    events = []
    for line in response_text.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data_content = line[5:].strip()
            if data_content:
                try:
                    events.append(json.loads(data_content))
                except json.JSONDecodeError:
                    pass
    return events


class TestSSEQueryPipelineIntegration:
    """Integration test suite testing full dual-path execution flow."""

    def test_structured_query_sse_end_to_end(self, client: TestClient) -> None:
        payload = {
            "question": "What is the financial limit for Fleet Commander under Schedule 7 with IFA concurrence?",
            "stream": True,
        }
        # Warm-up pass for cold-start dynamic imports and ASGI handler initialization
        _ = client.post("/query", json=payload)

        t0 = time.perf_counter()
        res = client.post("/query", json=payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]

        events = _parse_sse_events(res.text)
        stages = [e["stage"] for e in events]

        assert stages == ["classify", "resolve", "complete"]

        # Latency check: Structured path steady-state resolution is fast
        assert elapsed_ms < 500.0

        # Verify citation cryptographic integrity
        resolve_ev = next(e for e in events if e["stage"] == "resolve")
        citations = resolve_ev["data"]["citations"]
        assert len(citations) == 1

        citation = citations[0]
        assert citation["document"] == "DFPDS-2026/NAVY/SCH-07"
        assert citation["page"] == 7
        assert len(citation["bbox"]) == 4
        assert verify_sha256(citation["text_snippet"], citation["sha256"]) is True

    def test_out_of_range_structured_query_abstention(self, client: TestClient) -> None:
        """Verify out-of-domain schedule query triggers certified refusal."""
        payload = {
            "question": "What is the limit for CNS under Schedule 99 with IFA?",
            "stream": True,
        }
        res = client.post("/query", json=payload)
        assert res.status_code == 200

        events = _parse_sse_events(res.text)
        stages = [e["stage"] for e in events]

        assert "classify" in stages
        assert "abstain" in stages

        abstain_ev = next(e for e in events if e["stage"] == "abstain")
        assert abstain_ev["data"]["reason"] == "OUT_OF_DOMAIN_QUERY"
        assert "outside the statutory DFPDS-2026 range" in abstain_ev["data"]["explanation"]

    def test_interpretive_query_sse_stages(self, client: TestClient) -> None:
        """Verify interpretive query routes through hybrid retrieval and corrective gate."""
        payload = {
            "question": "What are the rules and guidelines for single tender procurement under DFPDS?",
            "stream": True,
        }
        res = client.post("/query", json=payload)
        assert res.status_code == 200

        events = _parse_sse_events(res.text)
        stages = [e["stage"] for e in events]

        assert "classify" in stages
        assert "retrieve" in stages
        assert "rerank" in stages
        assert "gate" in stages

        classify_ev = next(e for e in events if e["stage"] == "classify")
        assert classify_ev["data"]["type"] == "interpretive"

    def test_out_of_domain_interpretive_query_abstention(self, client: TestClient) -> None:
        """Verify completely unrelated query triggers certified refusal for insufficient context."""
        payload = {
            "question": "What is the capital budget allocation for INS Vishal aircraft carrier in FY 2027?",
            "stream": True,
        }
        res = client.post("/query", json=payload)
        assert res.status_code == 200

        events = _parse_sse_events(res.text)
        stages = [e["stage"] for e in events]

        assert "abstain" in stages
        abstain_ev = next(e for e in events if e["stage"] == "abstain")
        assert abstain_ev["data"]["reason"] in ("INSUFFICIENT_CORPUS_CONTEXT", "UNVERIFIED_STATUTORY_CLAIM")

    def test_non_streaming_structured_response(self, client: TestClient) -> None:
        """Verify non-streaming request returns consolidated JSON response."""
        payload = {
            "question": "What is the financial limit for Chief of Naval Staff under Schedule 1 with IFA?",
            "stream": False,
        }
        res = client.post("/query", json=payload)
        assert res.status_code == 200

        data = res.json()
        assert data["success"] is True
        assert data["data"]["type"] == "structured"
        assert data["data"]["status"] == "certified"
        assert "Chief of the Naval Staff" in data["data"]["answer"]
        assert len(data["data"]["citations"]) >= 1

    def test_non_streaming_abstention_response(self, client: TestClient) -> None:
        """Verify non-streaming request returns consolidated JSON refusal."""
        payload = {
            "question": "What is the limit for CNS under Schedule 99?",
            "stream": False,
        }
        res = client.post("/query", json=payload)
        assert res.status_code == 200

        data = res.json()
        assert data["success"] is True
        assert data["data"]["status"] == "abstain"
        assert data["data"]["reason"] == "OUT_OF_DOMAIN_QUERY"
