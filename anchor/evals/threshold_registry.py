"""
threshold_registry.py — Non-Negotiable Quality Regression Gate & Threshold Registry
"""

from dataclasses import dataclass, field
import logging
from typing import Optional
from pydantic import BaseModel, Field

from anchor.evals.metrics import MetricSummary

logger = logging.getLogger(__name__)


class QualityGateFailure(Exception):
    """Raised when evaluation metrics violate non-negotiable quality contract thresholds."""


class ArchetypeThresholds(BaseModel):
    """
    Configurable NLI entailment thresholds per query archetype (ENH-005).
    """

    structured_entailment: float = Field(default=1.00, description="Deterministic, no NLI needed")
    interpretive_entailment: float = Field(default=0.85, description="Standard interpretive threshold")
    financial_entailment: float = Field(default=0.90, description="Stricter for money figures")
    procedural_entailment: float = Field(default=0.80, description="Slightly relaxed for process questions")


class MetricThresholds(BaseModel):
    """
    Non-negotiable minimum quality thresholds defined in Reference/Build_Sprint_Plan.md:L548-566
    and Reference/PROJECT_ANCHOR_BLUEPRINT.md:L390-406.
    """

    min_faithfulness: float = Field(default=0.92, description="Minimum ratio of NLI-verified claims (>=0.85)")
    min_citation_precision: float = Field(default=0.95, description="Minimum ratio of valid SHA-256 byte citations")
    min_context_recall: float = Field(default=0.90, description="Minimum MRR@10 and top-3 retrieval recall")
    min_abstention_accuracy: float = Field(default=1.00, description="Minimum correct refusal rate on OOD queries")
    max_hallucination_rate: float = Field(default=0.05, description="Maximum permissible ungrounded/contradiction claims")
    min_structured_accuracy: float = Field(default=1.00, description="Minimum exact match on deterministic SQL resolver")

    # Per-Question Latency Budgets (ENH-014)
    max_structured_latency_ms: float = Field(default=1000.0, description="Ceiling for structured SQL queries")
    max_interpretive_latency_ms: float = Field(default=8000.0, description="Ceiling for interpretive RAG queries")
    max_abstention_latency_ms: float = Field(default=500.0, description="Ceiling for out-of-domain abstentions")
    max_deck_latency_ms: float = Field(default=5000.0, description="Ceiling for AutoDeck generation")
    archetypes: ArchetypeThresholds = Field(default_factory=ArchetypeThresholds)


@dataclass
class GateDecision:
    """
    Evaluation quality gate decision record.
    """

    passed: bool
    summary: MetricSummary
    thresholds: MetricThresholds
    failed_metrics: list[str] = field(default_factory=list)
    failed_details: list[str] = field(default_factory=list)
    metric_deltas: dict[str, float] = field(default_factory=dict)
    report_markdown: str = ""


class ThresholdRegistry:
    """
    Programmatic Quality Gate enforcing the quality contract across all sprint evaluations.
    """

    def __init__(self, thresholds: Optional[MetricThresholds] = None) -> None:
        self.thresholds = thresholds or MetricThresholds()
        self._baseline: Optional[MetricSummary] = None

    def register_baseline(self, baseline: MetricSummary) -> None:
        """Register the baseline evaluation metrics summary."""
        self._baseline = baseline

    def get_baseline(self) -> Optional[MetricSummary]:
        """Retrieve the currently registered baseline metrics."""
        return self._baseline

    def evaluate_run(
        self,
        summary: MetricSummary,
        raise_on_failure: bool = False,
    ) -> GateDecision:
        """
        Evaluate an evaluation run against minimum quality thresholds and baseline deltas.
        """
        failed_metrics: list[str] = []
        failed_details: list[str] = []

        if summary.faithfulness < self.thresholds.min_faithfulness:
            failed_metrics.append("faithfulness")
            failed_details.append(
                f"faithfulness ({summary.faithfulness:.4f} < {self.thresholds.min_faithfulness:.4f})"
            )
        if summary.citation_precision < self.thresholds.min_citation_precision:
            failed_metrics.append("citation_precision")
            failed_details.append(
                f"citation_precision ({summary.citation_precision:.4f} < {self.thresholds.min_citation_precision:.4f})"
            )
        if summary.context_recall < self.thresholds.min_context_recall:
            failed_metrics.append("context_recall")
            failed_details.append(
                f"context_recall ({summary.context_recall:.4f} < {self.thresholds.min_context_recall:.4f})"
            )
        if summary.abstention_accuracy < self.thresholds.min_abstention_accuracy:
            failed_metrics.append("abstention_accuracy")
            failed_details.append(
                f"abstention_accuracy ({summary.abstention_accuracy:.4f} < {self.thresholds.min_abstention_accuracy:.4f})"
            )
        if summary.hallucination_rate > self.thresholds.max_hallucination_rate:
            failed_metrics.append("hallucination_rate")
            failed_details.append(
                f"hallucination_rate ({summary.hallucination_rate:.4f} > {self.thresholds.max_hallucination_rate:.4f})"
            )
        if summary.structured_accuracy < self.thresholds.min_structured_accuracy:
            failed_metrics.append("structured_accuracy")
            failed_details.append(
                f"structured_accuracy ({summary.structured_accuracy:.4f} < {self.thresholds.min_structured_accuracy:.4f})"
            )

        passed = len(failed_metrics) == 0

        # Compute deltas against baseline if available
        deltas: dict[str, float] = {}
        if self._baseline:
            deltas["faithfulness"] = round(summary.faithfulness - self._baseline.faithfulness, 4)
            deltas["citation_precision"] = round(summary.citation_precision - self._baseline.citation_precision, 4)
            deltas["context_recall"] = round(summary.context_recall - self._baseline.context_recall, 4)
            deltas["abstention_accuracy"] = round(summary.abstention_accuracy - self._baseline.abstention_accuracy, 4)
            deltas["hallucination_rate"] = round(summary.hallucination_rate - self._baseline.hallucination_rate, 4)
            deltas["structured_accuracy"] = round(summary.structured_accuracy - self._baseline.structured_accuracy, 4)

        report_lines = [
            f"## Quality Gate Report: {'PASSED [OK]' if passed else 'FAILED [ERROR]'}",
            "",
            "| Metric | Value | Threshold | Status |",
            "| :--- | :---: | :---: | :---: |",
            f"| Faithfulness | {summary.faithfulness:.4f} | $\\ge {self.thresholds.min_faithfulness:.4f}$ | {'[PASS]' if summary.faithfulness >= self.thresholds.min_faithfulness else '[FAIL]'} |",
            f"| Citation Precision | {summary.citation_precision:.4f} | $\\ge {self.thresholds.min_citation_precision:.4f}$ | {'[PASS]' if summary.citation_precision >= self.thresholds.min_citation_precision else '[FAIL]'} |",
            f"| Context Recall (MRR@10) | {summary.context_recall:.4f} | $\\ge {self.thresholds.min_context_recall:.4f}$ | {'[PASS]' if summary.context_recall >= self.thresholds.min_context_recall else '[FAIL]'} |",
            f"| Abstention Accuracy | {summary.abstention_accuracy:.4f} | $= {self.thresholds.min_abstention_accuracy:.4f}$ | {'[PASS]' if summary.abstention_accuracy >= self.thresholds.min_abstention_accuracy else '[FAIL]'} |",
            f"| Hallucination Rate | {summary.hallucination_rate:.4f} | $\\le {self.thresholds.max_hallucination_rate:.4f}$ | {'[PASS]' if summary.hallucination_rate <= self.thresholds.max_hallucination_rate else '[FAIL]'} |",
            f"| Structured Accuracy | {summary.structured_accuracy:.4f} | $= {self.thresholds.min_structured_accuracy:.4f}$ | {'[PASS]' if summary.structured_accuracy >= self.thresholds.min_structured_accuracy else '[FAIL]'} |",
        ]

        if not passed:
            report_lines.extend(["", "### Violations:", *[f"- {d}" for d in failed_details]])

        report_markdown = "\n".join(report_lines)

        decision = GateDecision(
            passed=passed,
            summary=summary,
            thresholds=self.thresholds,
            failed_metrics=failed_metrics,
            failed_details=failed_details,
            metric_deltas=deltas,
            report_markdown=report_markdown,
        )

        if not passed and raise_on_failure:
            msg = f"Quality Gate Rejected Sprint Build! Violations: {', '.join(failed_details)}"
            logger.error(msg)
            raise QualityGateFailure(msg)

        return decision


default_registry = ThresholdRegistry()


def evaluate_run(summary: MetricSummary, raise_on_failure: bool = False) -> GateDecision:
    """Convenience helper to evaluate an evaluation run against default quality thresholds."""
    return default_registry.evaluate_run(summary, raise_on_failure=raise_on_failure)
