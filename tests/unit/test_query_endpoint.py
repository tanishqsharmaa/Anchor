"""
test_query_endpoint.py — Unit Tests for Full SSE Streaming Query Route Engine
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from anchor.main import app
from anchor.retrieve.classifier import ClassificationResult
from anchor.retrieve.hybrid import RetrievedChunk
from anchor.retrieve.resolver import ResolverResult
from anchor.trust.hash import compute_sha256


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


class TestQueryEndpoint:
    """Unit tests for POST /query endpoint (SSE Streaming and JSON modes)."""

    def test_query_input_boundary_validation(self, client: TestClient) -> None:
        # Question too short (<3 chars)
        res_short = client.post("/query", json={"question": "hi", "stream": True})
        assert res_short.status_code == 422

        # Question too long (>2000 chars)
        res_long = client.post("/query", json={"question": "x" * 2005, "stream": True})
        assert res_long.status_code == 422

    def test_query_structured_sse_stream(self, client: TestClient) -> None:
        payload = {
            "question": "What is the financial limit for a Fleet Commander under Schedule 7 with IFA concurrence?",
            "stream": True,
        }
        res = client.post("/query", json=payload)
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]

        events = _parse_sse_events(res.text)
        assert len(events) >= 3

        stages = [e["stage"] for e in events]
        assert "classify" in stages
        assert "resolve" in stages
        assert "complete" in stages

        # Inspect classify stage data
        classify_ev = next(e for e in events if e["stage"] == "classify")
        assert classify_ev["data"]["type"] == "structured"
        assert classify_ev["data"]["entities"]["schedule_no"] == 7
        assert classify_ev["data"]["entities"]["tier"] == "Tier 3"

        # Inspect resolve stage data
        resolve_ev = next(e for e in events if e["stage"] == "resolve")
        assert "Fleet Commander" in resolve_ev["data"]["answer"]
        citations = resolve_ev["data"]["citations"]
        assert len(citations) >= 1
        assert citations[0]["document"] == "DFPDS-2026/NAVY/SCH-07"
        assert len(citations[0]["sha256"]) == 64
        assert len(citations[0]["bbox"]) == 4

    def test_query_structured_non_streaming_json(self, client: TestClient) -> None:
        payload = {
            "question": "What is the limit for Chief of Naval Staff under Schedule 1 without IFA?",
            "stream": False,
        }
        res = client.post("/query", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["type"] == "structured"
        assert "Chief of the Naval Staff" in data["data"]["answer"]
        assert len(data["data"]["citations"]) >= 1

    def test_query_out_of_range_structured_abstention(self, client: TestClient) -> None:
        payload = {
            "question": "What is the limit for CNS under Schedule 99 with IFA?",
            "stream": True,
        }
        res = client.post("/query", json=payload)
        assert res.status_code == 200

        events = _parse_sse_events(res.text)
        stages = [e["stage"] for e in events]
        assert "abstain" in stages

        abstain_ev = next(e for e in events if e["stage"] == "abstain")
        assert "OUT_OF_DOMAIN_QUERY" in abstain_ev["data"]["reason"]

    def test_query_interpretive_sse_stream_mocked(self, client: TestClient) -> None:
        """Verify the full interpretive SSE pipeline trace with mocked neural inference."""
        sample_chunk = RetrievedChunk(
            chunk_id="chunk_test_01",
            doc_id="DFPDS-2026",
            schedule_no=7,
            section="Schedule 07",
            breadcrumb="DFPDS-2026/Schedule_07/Major_Repairs",
            page_no=3,
            bbox=[72.0, 100.0, 540.0, 200.0],
            text="Under Schedule 07, emergency powers allow fleet repairs without standard delays.",
            sha256=compute_sha256("Under Schedule 07, emergency powers allow fleet repairs without standard delays."),
            score=0.95,
        )

        with patch("anchor.api.routes_query.orchestrator.classifier.classify") as mock_classify, \
             patch("anchor.api.routes_query.orchestrator.hybrid.retrieve") as mock_retrieve, \
             patch("anchor.api.routes_query.orchestrator.reranker.rerank") as mock_rerank, \
             patch("anchor.api.routes_query.orchestrator.gate.filter_chunks") as mock_gate, \
             patch("anchor.api.routes_query.orchestrator.synthesizer.synthesize_stream") as mock_synth_stream, \
             patch("anchor.api.routes_query.orchestrator.nli_gate.verify_synthesis") as mock_verify:

            mock_classify.return_value = ClassificationResult(
                query_type="interpretive",
                routing_reason="Procedural query",
                confidence=0.99,
            )
            mock_retrieve.return_value = [sample_chunk]
            mock_rerank.return_value = [sample_chunk]
            mock_gate.return_value = ([sample_chunk], True)
            mock_synth_stream.return_value = iter(["Emergency ", "powers ", "permit ", "fleet ", "repairs."])
            
            from anchor.generate.nli_gate import SentenceVerification
            mock_verify.return_value = (
                [
                    SentenceVerification(
                        sentence_idx=0,
                        text="Emergency powers permit fleet repairs.",
                        best_premise_chunk_id="chunk_test_01",
                        entailment_score=0.96,
                        status="certified",
                    )
                ],
                True,
                "Emergency powers permit fleet repairs.",
            )

            payload = {
                "question": "Can emergency powers bypass GeM for fleet propulsion repairs?",
                "stream": True,
            }
            res = client.post("/query", json=payload)
            assert res.status_code == 200

            events = _parse_sse_events(res.text)
            stages = [e["stage"] for e in events]

            expected_stages = ["classify", "retrieve", "rerank", "gate", "generate", "verify", "complete"]
            for st in expected_stages:
                assert st in stages, f"Expected stage '{st}' in {stages}"

            complete_ev = next(e for e in events if e["stage"] == "complete")
            assert "Emergency powers permit fleet repairs." in complete_ev["data"]["answer"]
            assert len(complete_ev["data"]["citations"]) == 1
            assert complete_ev["data"]["citations"][0]["document"] == "DFPDS-2026/Schedule_07/Major_Repairs"

    def test_query_interpretive_gating_abstention(self, client: TestClient) -> None:
        """Verify that when corrective gate fails, an abstain event is emitted."""
        with patch("anchor.api.routes_query.orchestrator.classifier.classify") as mock_classify, \
             patch("anchor.api.routes_query.orchestrator.hybrid.retrieve") as mock_retrieve, \
             patch("anchor.api.routes_query.orchestrator.reranker.rerank") as mock_rerank, \
             patch("anchor.api.routes_query.orchestrator.gate.filter_chunks") as mock_gate:

            mock_classify.return_value = ClassificationResult(query_type="interpretive")
            mock_retrieve.return_value = []
            mock_rerank.return_value = []
            mock_gate.return_value = ([], False)

            payload = {
                "question": "What is the capital budget for INS Vishal in FY 2027?",
                "stream": True,
            }
            res = client.post("/query", json=payload)
            assert res.status_code == 200

            events = _parse_sse_events(res.text)
            stages = [e["stage"] for e in events]
            assert "abstain" in stages
            abstain_ev = next(e for e in events if e["stage"] == "abstain")
            assert "INSUFFICIENT_CORPUS_CONTEXT" in abstain_ev["data"]["reason"]
