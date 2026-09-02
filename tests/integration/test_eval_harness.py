"""
test_eval_harness.py — End-to-End Integration Test for Evaluation Suite & Threshold Quality Gate
"""

import asyncio
import json
from pathlib import Path
import pytest
from anchor.config import settings
from anchor.evals.eval_suite import (
    BENCHMARK_DATASET,
    EvaluationHarness,
)
from anchor.evals.threshold_registry import GateDecision


def test_eval_suite_dataset_coverage():
    """
    Verify benchmark dataset contains >= 30 questions and covers all 7 statutory archetypes.
    """
    assert len(BENCHMARK_DATASET) >= 30, f"Expected >=30 questions, found {len(BENCHMARK_DATASET)}"

    archetypes = {q.archetype for q in BENCHMARK_DATASET}
    required_archetypes = {
        "STRUCTURED",
        "INTERPRETIVE",
        "ABSTENTION",
        "MULTI_HOP",
        "COMPARATIVE",
        "BOUNDARY_EDGE",
        "NEGATIVE_CONSTRAINT",
    }

    assert required_archetypes.issubset(archetypes), f"Missing archetypes: {required_archetypes - archetypes}"

    # Verify counts per archetype
    structured_count = sum(1 for q in BENCHMARK_DATASET if q.archetype == "STRUCTURED")
    interpretive_count = sum(1 for q in BENCHMARK_DATASET if q.archetype == "INTERPRETIVE")
    abstention_count = sum(1 for q in BENCHMARK_DATASET if q.archetype == "ABSTENTION")

    assert structured_count >= 10, f"Expected >=10 structured questions, found {structured_count}"
    assert interpretive_count >= 5, f"Expected >=5 interpretive questions, found {interpretive_count}"
    assert abstention_count >= 5, f"Expected >=5 abstention questions, found {abstention_count}"


def test_eval_harness_execution_and_thresholds(tmp_path):
    """
    Execute full evaluation suite against live dual-path backend and assert all quality gates pass.
    """
    harness = EvaluationHarness()
    report_file = tmp_path / "eval_report_test.json"

    summary, decision = asyncio.run(harness.run_suite(export_path=str(report_file)))

    assert isinstance(decision, GateDecision)
    assert decision.passed is True, f"Quality gate failed: {decision.failed_details}"

    # Explicit threshold validations
    assert summary.faithfulness >= 0.92, f"Faithfulness {summary.faithfulness} < 0.92"
    assert summary.citation_precision >= 0.95, f"Citation Precision {summary.citation_precision} < 0.95"
    assert summary.context_recall >= 0.90, f"Context Recall {summary.context_recall} < 0.90"
    assert summary.abstention_accuracy == 1.00, f"Abstention Accuracy {summary.abstention_accuracy} != 1.00"
    assert summary.hallucination_rate <= 0.05, f"Hallucination Rate {summary.hallucination_rate} > 0.05"
    assert summary.structured_accuracy == 1.00, f"Structured Accuracy {summary.structured_accuracy} != 1.00"

    # Verify exported JSON report
    assert report_file.exists()
    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["passed"] is True
    assert data["total_questions"] == summary.total_questions
    assert len(data["results"]) == summary.total_questions
