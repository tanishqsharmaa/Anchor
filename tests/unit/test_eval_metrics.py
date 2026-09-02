"""
test_eval_metrics.py — Unit Tests for Evaluation Metric Formulas
"""

import pytest
from anchor.evals.metrics import (
    EvaluationResult,
    MetricSummary,
    compute_faithfulness,
    compute_citation_precision,
    compute_context_recall,
    compute_abstention_accuracy,
    compute_hallucination_rate,
    compute_structured_accuracy,
    compute_aggregate_metrics,
)


def test_compute_faithfulness_perfect():
    """All claims entailed with score >= 0.85 -> 1.0."""
    nli_scores = [0.95, 0.88, 0.91, 0.85]
    assert compute_faithfulness(nli_scores) == 1.0


def test_compute_faithfulness_partial():
    """3 out of 4 claims entailed with score >= 0.85 -> 0.75."""
    nli_scores = [0.95, 0.88, 0.86, 0.40]
    assert compute_faithfulness(nli_scores) == 0.75


def test_compute_faithfulness_empty():
    """Empty scores should return 1.0 (no unfaithful claims)."""
    assert compute_faithfulness([]) == 1.0


def test_compute_citation_precision():
    """Test valid vs total citation count ratio."""
    # 95 valid out of 100
    assert compute_citation_precision(valid_citations=95, total_citations=100) == 0.95
    # 0 total citations defaults to 1.0
    assert compute_citation_precision(valid_citations=0, total_citations=0) == 1.0
    # valid > total is capped at 1.0
    assert compute_citation_precision(valid_citations=10, total_citations=5) == 1.0


def test_compute_context_recall():
    """Test retrieved relevant top-3 chunks vs ground truth chunks."""
    retrieved_chunk_ids = ["chunk_1", "chunk_2", "chunk_3", "chunk_4"]
    ground_truth_chunk_ids = ["chunk_1", "chunk_2", "chunk_5"]

    # Top-3 contains chunk_1 and chunk_2 (2 out of 3 ground truth)
    recall = compute_context_recall(
        retrieved_chunk_ids=retrieved_chunk_ids,
        ground_truth_chunk_ids=ground_truth_chunk_ids,
        top_k=3,
    )
    assert pytest.approx(recall, rel=1e-3) == 2.0 / 3.0

    # Empty ground truth returns 1.0
    assert compute_context_recall(retrieved_chunk_ids, [], top_k=3) == 1.0


def test_compute_abstention_accuracy():
    """Test correct abstention decisions on OOD queries."""
    # 5 out of 5 correct refusals
    assert compute_abstention_accuracy(correct_abstentions=5, total_ood_queries=5) == 1.0
    # 4 out of 5 correct refusals
    assert compute_abstention_accuracy(correct_abstentions=4, total_ood_queries=5) == 0.8
    # 0 OOD queries returns 1.0
    assert compute_abstention_accuracy(correct_abstentions=0, total_ood_queries=0) == 1.0


def test_compute_hallucination_rate():
    """Test ratio of unverified / contradictory claims."""
    # 1 unverified / contradiction claim out of 20
    assert pytest.approx(compute_hallucination_rate(unverified_claims=1, total_claims=20), rel=1e-3) == 0.05
    # 0 claims returns 0.0
    assert compute_hallucination_rate(unverified_claims=0, total_claims=0) == 0.0


def test_compute_structured_accuracy():
    """Test exact match on deterministic SQL lookups."""
    # 10 exact matches out of 10
    assert compute_structured_accuracy(exact_matches=10, total_structured=10) == 1.0
    # 9 out of 10
    assert compute_structured_accuracy(exact_matches=9, total_structured=10) == 0.9
    # 0 structured queries returns 1.0
    assert compute_structured_accuracy(exact_matches=0, total_structured=0) == 1.0


def test_compute_aggregate_metrics():
    """Test aggregate MetricSummary computation across multiple evaluation results."""
    eval_results = [
        EvaluationResult(
            question_id="Q01",
            archetype="STRUCTURED",
            question="What is L2 limit under Schedule 7 with IFA?",
            expected_answer="₹18.00 Crore",
            actual_answer="Under DFPDS-2026 Schedule 07 (DFPDS-2026/NAVY/SCH-07), a Fleet Commander (Tier 3) may sanction up to ₹18.00 Crore with IFA concurrence.",
            is_structured_exact_match=True,
            nli_scores=[0.96],
            valid_citations_count=1,
            total_citations_count=1,
            retrieved_chunk_ids=["sch_07_t3"],
            ground_truth_chunk_ids=["sch_07_t3"],
            is_abstained=False,
            expected_abstained=False,
            latency_ms=85.0,
        ),
        EvaluationResult(
            question_id="Q02",
            archetype="INTERPRETIVE",
            question="Can CO Frigate bypass GeM for emergency propulsion repair?",
            expected_answer="Yes, emergency repairs allow bypass with written justification.",
            actual_answer="Under DPM 2025 Chapter 3, emergency propulsion repairs permit local procurement bypass.",
            is_structured_exact_match=None,
            nli_scores=[0.92, 0.88],
            valid_citations_count=2,
            total_citations_count=2,
            retrieved_chunk_ids=["dpm_ch3_01", "dpm_ch3_02"],
            ground_truth_chunk_ids=["dpm_ch3_01"],
            is_abstained=False,
            expected_abstained=False,
            latency_ms=1250.0,
        ),
        EvaluationResult(
            question_id="Q03",
            archetype="ABSTENTION",
            question="What is the capital budget for INS Vishal in FY 2027?",
            expected_answer="Abstain",
            actual_answer="CERTIFIED ABSTENTION: Out of domain",
            is_structured_exact_match=None,
            nli_scores=[],
            valid_citations_count=0,
            total_citations_count=0,
            retrieved_chunk_ids=[],
            ground_truth_chunk_ids=[],
            is_abstained=True,
            expected_abstained=True,
            latency_ms=120.0,
        ),
    ]

    summary = compute_aggregate_metrics(eval_results)

    assert isinstance(summary, MetricSummary)
    assert summary.total_questions == 3
    assert summary.faithfulness >= 0.92
    assert summary.citation_precision >= 0.95
    assert summary.context_recall >= 0.90
    assert summary.abstention_accuracy == 1.0
    assert summary.hallucination_rate <= 0.05
    assert summary.structured_accuracy == 1.0
    assert summary.avg_latency_ms > 0
