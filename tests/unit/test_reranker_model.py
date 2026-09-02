"""
test_reranker_model.py — Unit Tests for OpenVINO INT8 BGE-Reranker-Large Model Wrapper
"""

import time
import pytest
from anchor.models.reranker_model import BGEReranker


@pytest.fixture(scope="module")
def reranker_model():
    """Module-level fixture providing compiled BGE-Reranker-Large OpenVINO model."""
    return BGEReranker()


def test_reranker_initialization(reranker_model):
    """Verify BGE-Reranker-Large loads cleanly and resolves tokenizer."""
    assert reranker_model is not None
    assert reranker_model.model is not None
    assert reranker_model.tokenizer is not None


def test_reranker_single_pair_score_range(reranker_model):
    """Verify single query-passage pair scoring returns a float in [0, 1]."""
    query = "What is the financial limit for Fleet Commander under Schedule 7 with IFA?"
    passage = "Under DFPDS-2026 Schedule 07 (Fleet Support), a Fleet Commander (Tier 3) may sanction up to ₹18.00 Crore with IFA."

    score = reranker_model.score(query, passage)

    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0, f"Score out of range [0, 1]: {score}"


def test_reranker_semantic_discrimination(reranker_model):
    """Verify that a relevant passage scores significantly higher than an irrelevant passage."""
    query = "What is the financial delegation for Dry Docking repairs under Schedule 1?"
    relevant_passage = "DFPDS-2026 Schedule 01 covers Dry Docking and Ship Repairs in Naval Dockyards with specific financial limits for Fleet Officers."
    irrelevant_passage = "Cooking gas refills and mess maintenance allowances are governed by naval administrative order 14/2021."

    rel_score = reranker_model.score(query, relevant_passage)
    irrel_score = reranker_model.score(query, irrelevant_passage)

    assert rel_score > irrel_score
    assert rel_score > 0.40, f"Expected relevant score > 0.40, got {rel_score}"
    assert irrel_score < 0.30, f"Expected irrelevant score < 0.30, got {irrel_score}"


def test_reranker_batch_scoring(reranker_model):
    """Verify batched cross-encoding processes multiple passages and preserves ordering."""
    query = "Who is the Competent Financial Authority for procurement of tactical drones?"
    passages = [
        "Procurement of Tactical Drones and UAV subsystems is governed under Schedule 07 with Tier 2/3 approvals.",
        "Stationery purchase guidelines for naval administrative headquarters.",
        "Emergency procurement of drone payloads authorized for Western Naval Command.",
    ]

    scores = reranker_model.score_batch(query, passages)

    assert isinstance(scores, list)
    assert len(scores) == 3
    for s in scores:
        assert isinstance(s, float)
        assert 0.0 <= s <= 1.0

    # Passage 0 and 2 are relevant to drones, passage 1 is stationery
    assert scores[0] > scores[1]
    assert scores[2] > scores[1]


def test_reranker_empty_and_edge_inputs(reranker_model):
    """Verify reranker handles empty strings, whitespace, and empty lists gracefully."""
    assert reranker_model.score_batch("test query", []) == []

    # Blank passage should return a valid low float
    score_blank = reranker_model.score("test query", "   ")
    assert isinstance(score_blank, float)
    assert 0.0 <= score_blank <= 1.0


def test_reranker_latency_budget(reranker_model):
    """Verify inference latency is within the real-time operational budget (<35ms steady state)."""
    query = "What is the L2 limit under Schedule 7 with IFA?"
    passage = "Under DFPDS-2026 Schedule 7, a Fleet Commander (Tier 3) may sanction up to ₹18.00 Crore with IFA."

    # Warmup runs
    for _ in range(3):
        _ = reranker_model.score(query, passage)

    # Measure 5 runs average
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        _ = reranker_model.score(query, passage)
        times.append((time.perf_counter() - t0) * 1000)

    avg_ms = sum(times) / len(times)
    # Operational budget: <250ms on CPU test run, target <35ms on accelerated hardware
    assert avg_ms < 250.0, f"Average reranker latency took {avg_ms:.2f}ms, exceeding budget"
