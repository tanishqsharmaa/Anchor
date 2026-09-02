"""
test_query_pipeline.py — End-to-End Dual-Path Integration Tests (Path A vs Path B)
"""

import pytest
from anchor.retrieve.classifier import QuestionClassifier
from anchor.retrieve.resolver import resolve_dfpds_delegation, resolve_dpm_threshold
from anchor.retrieve.hybrid import HybridRetriever
from anchor.retrieve.conflict_resolver import ConflictResolver


@pytest.fixture(scope="module")
def classifier():
    return QuestionClassifier()


@pytest.fixture(scope="module")
def retriever():
    return HybridRetriever()


@pytest.fixture(scope="module")
def conflict_resolver():
    return ConflictResolver()


def test_path_a_structured_query_end_to_end(classifier):
    """Verify Path A: Question -> Classifier -> Structured Resolver -> Exact statutory INR value."""
    question = "What is the financial limit for a Fleet Commander under Schedule 7 with IFA?"

    # 1. Classification
    class_res = classifier.classify(question)
    assert class_res.query_type == "structured"
    assert class_res.schedule_no == 7
    assert class_res.tier == "Tier 3"
    assert class_res.with_ifa is True

    # 2. Deterministic SQL Resolution
    resolved = resolve_dfpds_delegation(
        schedule_no=class_res.schedule_no,
        tier=class_res.tier,
        ifa_concurrence=class_res.with_ifa,
        is_pac=class_res.is_pac,
    )

    assert resolved is not None
    assert resolved.schedule_no == 7
    assert resolved.sanction_limit == 21.00
    assert resolved.reference == "DFPDS-2026/NAVY/SCH-07"
    assert "₹21.00 Crore with IFA concurrence" in resolved.formatted_answer


def test_path_a_dpm_threshold_end_to_end(classifier):
    """Verify Path A: DPM Question -> Classifier -> DPM Threshold Resolver -> Exact rules."""
    question = "What is the mandatory threshold for Open Tender Enquiry (OTE) under DPM 2025?"

    class_res = classifier.classify(question)
    assert class_res.query_type == "structured"
    assert class_res.dpm_mode == "OTE"

    dpm_rule = resolve_dpm_threshold(class_res.dpm_mode)
    assert dpm_rule is not None
    assert dpm_rule["mode"] == "Open Tender Enquiry"
    assert dpm_rule["threshold_inr_lakhs"] == 25.0
    assert dpm_rule["reference"] == "DPM-2025/DMA/CH-02"


def test_path_b_interpretive_query_end_to_end(classifier, retriever, conflict_resolver):
    """Verify Path B: Question -> Classifier -> Hybrid Retrieval -> Conflict Resolution -> Top-3 Candidate Chunks."""
    question = "Can a CO Frigate invoke emergency powers to bypass GeM for critical propulsion repair at sea?"

    # 1. Classification
    class_res = classifier.classify(question)
    assert class_res.query_type == "interpretive"

    # 2. Multi-Store Hybrid Retrieval
    retrieved = retriever.retrieve(question, top_k=5)
    assert len(retrieved) > 0

    # 3. Cross-Regulatory Conflict Resolution
    resolved_chunks = conflict_resolver.resolve_conflicts(retrieved)
    assert len(resolved_chunks) > 0

    top_chunk = resolved_chunks[0]
    assert len(top_chunk.text) > 0
    assert len(top_chunk.sha256) == 64
    assert top_chunk.score > 0
    assert top_chunk.publish_year >= 2020


def test_dual_path_routing_determinism(classifier):
    """Verify routing determinism across mixed statutory query batches."""
    queries = [
        ("What is the Tier 1 limit under Schedule 1 with IFA?", "structured"),
        ("What is the Tier 6 limit under Schedule 32 without IFA?", "structured"),
        ("What is the penalty ceiling for Liquidated Damages LD?", "structured"),
        ("Explain the procedure for single tender enquiry justifications.", "interpretive"),
        ("How are statutory command duties delegated under Navy Regulations?", "interpretive"),
    ]

    for q, expected_path in queries:
        res = classifier.classify(q)
        assert res.query_type == expected_path, f"Failed for query: {q}"
