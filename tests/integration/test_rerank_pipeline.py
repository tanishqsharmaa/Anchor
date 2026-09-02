"""
test_rerank_pipeline.py — Integration Tests for Hybrid Retrieval -> Reranker -> Corrective Gate Pipeline
"""

import pytest
from anchor.retrieve.classifier import QuestionClassifier
from anchor.retrieve.hybrid import HybridRetriever
from anchor.retrieve.conflict_resolver import ConflictResolver
from anchor.retrieve.reranker import Reranker
from anchor.retrieve.corrective_gate import CorrectiveGate
from anchor.models.loader import model_orchestrator


@pytest.fixture(scope="module")
def pipeline():
    return {
        "classifier": QuestionClassifier(),
        "retriever": HybridRetriever(),
        "conflict_resolver": ConflictResolver(),
        "reranker": Reranker(),
        "corrective_gate": CorrectiveGate(min_rerank_score=0.20, min_cosine_sim=0.50),
    }


def test_end_to_end_rerank_and_gate_pipeline(pipeline):
    """
    Verify complete Stage 2 retrieval pipeline:
    Query -> Hybrid Retrieval (top-10) -> Conflict Resolution -> Cross-Encoder Reranker (top-3) -> Corrective Gate
    """
    question = "Can a Commanding Officer invoke emergency procurement powers for ship propulsion repairs?"

    # 1. Classification
    class_res = pipeline["classifier"].classify(question)
    assert class_res.query_type == "interpretive"

    # 2. Hybrid Dense + Sparse Retrieval (Top-10 candidates)
    raw_chunks = pipeline["retriever"].retrieve(question, top_k=10)
    assert len(raw_chunks) > 0

    # 3. Cross-Regulatory Conflict Resolution
    deconflicted_chunks = pipeline["conflict_resolver"].resolve_conflicts(raw_chunks)
    assert len(deconflicted_chunks) > 0

    # 4. Cross-Encoder Reranker (Top-10 -> Top-3)
    reranked_chunks = pipeline["reranker"].rerank(question, deconflicted_chunks, top_k=3)
    assert len(reranked_chunks) <= 3
    assert len(reranked_chunks) > 0

    # Scores should be sorted descending
    for i in range(len(reranked_chunks) - 1):
        assert reranked_chunks[i].score >= reranked_chunks[i + 1].score

    # 5. Corrective Relevance Gate
    verified_chunks, is_sufficient = pipeline["corrective_gate"].filter_chunks(
        question, reranked_chunks
    )

    assert is_sufficient is True
    assert len(verified_chunks) > 0
    top_verified = verified_chunks[0]
    assert len(top_verified.text) > 0
    assert len(top_verified.sha256) == 64
    assert len(top_verified.bbox) == 4


def test_end_to_end_abstention_pipeline(pipeline):
    """
    Verify that an adversarial/out-of-domain query is rejected by the Corrective Gate.
    """
    ood_query = "What is the capital budget allocation for the construction of INS Vishal in FY 2027?"

    # 1. Retrieve candidates (may return weak generic hits from index)
    raw_chunks = pipeline["retriever"].retrieve(ood_query, top_k=5)

    # 2. Rerank
    reranked = pipeline["reranker"].rerank(ood_query, raw_chunks, top_k=3)

    # 3. Corrective Gate with strict threshold should identify lack of ground-truth relevance
    strict_gate = CorrectiveGate(min_rerank_score=0.70)
    passed_chunks, is_sufficient = strict_gate.filter_chunks(ood_query, reranked)

    # Should flag insufficient context for certified abstention
    assert is_sufficient is False
    assert len(passed_chunks) == 0


def test_pipeline_peak_ram_under_load():
    """Verify that peak RAM consumption during full pipeline execution respects the 12.5 GB ceiling."""
    stats = model_orchestrator.get_memory_stats()
    assert stats["peak_ram_within_budget"] is True
    assert stats["process_rss_gb"] < 12.5
