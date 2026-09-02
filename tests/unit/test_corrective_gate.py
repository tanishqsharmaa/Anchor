"""
test_corrective_gate.py — Unit Tests for Corrective Relevance Gate
"""

import pytest
from anchor.retrieve.hybrid import RetrievedChunk
from anchor.retrieve.corrective_gate import CorrectiveGate


def make_chunk(chunk_id: str, text: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        doc_id="DFPDS-2026",
        schedule_no=7,
        section="Section_07",
        breadcrumb="DFPDS-2026/Schedule_07",
        page_no=1,
        bbox=[0.0, 0.0, 10.0, 10.0],
        text=text,
        sha256=f"hash_{chunk_id}",
        score=score,
    )


@pytest.fixture(scope="module")
def gate():
    return CorrectiveGate(min_rerank_score=0.25, min_cosine_sim=0.60)


def test_corrective_gate_passes_relevant_chunks(gate):
    """Verify that chunks with high cross-encoder relevance pass through."""
    query = "What are the financial powers under Schedule 7 for Fleet Commander?"
    chunks = [
        make_chunk("c_high", "Under Schedule 7, Fleet Commander has powers up to 18 Crore.", score=0.85),
        make_chunk("c_med", "DFPDS Schedule 7 covers tactical drone procurement.", score=0.65),
    ]

    passed, is_sufficient = gate.filter_chunks(query, chunks)

    assert is_sufficient is True
    assert len(passed) == 2
    assert passed[0].chunk_id == "c_high"


def test_corrective_gate_filters_noisy_chunks(gate):
    """Verify that low-scoring noisy chunks are filtered out."""
    query = "What is the L2 limit under Schedule 7?"
    chunks = [
        make_chunk("c_good", "Schedule 7 L2 limit is 18 Crore with IFA.", score=0.75),
        make_chunk("c_noise", "Cooking gas refill allowance for naval base mess.", score=0.08),
    ]

    passed, is_sufficient = gate.filter_chunks(query, chunks)

    assert is_sufficient is True
    assert len(passed) == 1
    assert passed[0].chunk_id == "c_good"


def test_corrective_gate_abstention_flag_on_insufficient_context(gate):
    """Verify that when all chunks are noise, gate returns is_sufficient=False."""
    query = "What is the capital budget for INS Vishal in FY 2027?"
    chunks = [
        make_chunk("c_noise_1", "General stationary procurement procedures.", score=0.12),
        make_chunk("c_noise_2", "Mess maintenance committee meeting minutes.", score=0.05),
    ]

    passed, is_sufficient = gate.filter_chunks(query, chunks)

    assert is_sufficient is False
    assert len(passed) == 0


def test_corrective_gate_empty_input(gate):
    """Verify gate handles empty query or empty chunks."""
    passed, is_sufficient = gate.filter_chunks("", [])
    assert is_sufficient is False
    assert passed == []

    passed2, is_sufficient2 = gate.filter_chunks("valid query", [])
    assert is_sufficient2 is False
    assert passed2 == []


def test_corrective_gate_custom_thresholds():
    """Verify custom threshold configuration is respected."""
    strict_gate = CorrectiveGate(min_rerank_score=0.90)
    chunk = make_chunk("c_borderline", "Relevant but moderate confidence.", score=0.80)

    passed, is_sufficient = strict_gate.filter_chunks("test query", [chunk])
    assert is_sufficient is False
    assert len(passed) == 0
