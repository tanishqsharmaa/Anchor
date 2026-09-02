"""
anchor.evals package initialization
"""

from anchor.evals.eval_suite import (
    BenchmarkQuestion,
    BENCHMARK_DATASET,
    EvaluationHarness,
)
from anchor.evals.kaggle_formatter import (
    KaggleRow,
    format_kaggle_row,
    export_kaggle_submission_csv,
)
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
from anchor.evals.threshold_registry import (
    MetricThresholds,
    ThresholdRegistry,
    GateDecision,
    QualityGateFailure,
    evaluate_run,
    default_registry,
)

__all__ = [
    "BenchmarkQuestion",
    "BENCHMARK_DATASET",
    "EvaluationHarness",
    "KaggleRow",
    "format_kaggle_row",
    "export_kaggle_submission_csv",
    "EvaluationResult",
    "MetricSummary",
    "compute_faithfulness",
    "compute_citation_precision",
    "compute_context_recall",
    "compute_abstention_accuracy",
    "compute_hallucination_rate",
    "compute_structured_accuracy",
    "compute_aggregate_metrics",
    "MetricThresholds",
    "ThresholdRegistry",
    "GateDecision",
    "QualityGateFailure",
    "evaluate_run",
    "default_registry",
]
