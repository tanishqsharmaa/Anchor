"""
test_threshold_registry.py — Unit Tests for Programmatic Threshold Registry Quality Gate
"""

import pytest
from anchor.evals.metrics import MetricSummary
from anchor.evals.threshold_registry import (
    MetricThresholds,
    ThresholdRegistry,
    GateDecision,
    QualityGateFailure,
)


def test_metric_thresholds_defaults():
    """Verify default thresholds match Reference/Build_Sprint_Plan.md:L548-566."""
    thresholds = MetricThresholds()
    assert thresholds.min_faithfulness == 0.92
    assert thresholds.min_citation_precision == 0.95
    assert thresholds.min_context_recall == 0.90
    assert thresholds.min_abstention_accuracy == 1.00
    assert thresholds.max_hallucination_rate == 0.05
    assert thresholds.min_structured_accuracy == 1.00


def test_threshold_registry_evaluate_run_pass():
    """Verify passing metrics produce GateDecision.passed == True."""
    registry = ThresholdRegistry()
    summary = MetricSummary(
        total_questions=30,
        structured_questions_count=10,
        interpretive_questions_count=15,
        ood_questions_count=5,
        faithfulness=0.95,
        citation_precision=0.98,
        context_recall=0.92,
        abstention_accuracy=1.00,
        hallucination_rate=0.02,
        structured_accuracy=1.00,
        avg_latency_ms=120.0,
        p95_latency_ms=450.0,
    )

    decision = registry.evaluate_run(summary, raise_on_failure=False)
    assert isinstance(decision, GateDecision)
    assert decision.passed is True
    assert len(decision.failed_metrics) == 0
    assert "PASSED" in decision.report_markdown


def test_threshold_registry_evaluate_run_fail():
    """Verify failing metric produces GateDecision.passed == False and lists failures."""
    registry = ThresholdRegistry()
    summary = MetricSummary(
        total_questions=30,
        structured_questions_count=10,
        interpretive_questions_count=15,
        ood_questions_count=5,
        faithfulness=0.88,  # Below 0.92 threshold
        citation_precision=0.98,
        context_recall=0.85,  # Below 0.90 threshold
        abstention_accuracy=1.00,
        hallucination_rate=0.02,
        structured_accuracy=1.00,
        avg_latency_ms=120.0,
        p95_latency_ms=450.0,
    )

    decision = registry.evaluate_run(summary, raise_on_failure=False)
    assert decision.passed is False
    assert "faithfulness" in decision.failed_metrics
    assert "context_recall" in decision.failed_metrics
    assert "FAILED" in decision.report_markdown


def test_threshold_registry_raise_on_failure():
    """Verify evaluate_run raises QualityGateFailure when raise_on_failure=True."""
    registry = ThresholdRegistry()
    summary = MetricSummary(
        total_questions=30,
        structured_questions_count=10,
        interpretive_questions_count=15,
        ood_questions_count=5,
        faithfulness=0.80,
        citation_precision=0.90,
        context_recall=0.70,
        abstention_accuracy=0.80,
        hallucination_rate=0.10,
        structured_accuracy=0.90,
    )

    with pytest.raises(QualityGateFailure) as exc_info:
        registry.evaluate_run(summary, raise_on_failure=True)

    assert "Quality Gate Rejected" in str(exc_info.value)
    assert "faithfulness" in str(exc_info.value)


def test_threshold_registry_baseline_tracking():
    """Verify baseline registration and delta calculation."""
    registry = ThresholdRegistry()
    baseline = MetricSummary(
        total_questions=30,
        faithfulness=0.93,
        citation_precision=0.96,
        context_recall=0.91,
        abstention_accuracy=1.0,
        hallucination_rate=0.03,
        structured_accuracy=1.0,
    )
    registry.register_baseline(baseline)
    assert registry.get_baseline() == baseline

    current = MetricSummary(
        total_questions=30,
        faithfulness=0.95,
        citation_precision=0.98,
        context_recall=0.92,
        abstention_accuracy=1.0,
        hallucination_rate=0.01,
        structured_accuracy=1.0,
    )
    decision = registry.evaluate_run(current)
    assert decision.metric_deltas["faithfulness"] == pytest.approx(0.02, rel=1e-3)
    assert decision.metric_deltas["hallucination_rate"] == pytest.approx(-0.02, rel=1e-3)
