"""
metrics.py — Quantitative Evaluation Metrics Calculation Engine
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    """
    Evaluation telemetry and verification scores for an individual test question.
    """

    question_id: str = Field(..., description="Unique question identifier (e.g. Q01)")
    archetype: str = Field(..., description="Statutory archetype (STRUCTURED, INTERPRETIVE, ABSTENTION, etc.)")
    question: str = Field(..., description="Original question string")
    expected_answer: Optional[str] = Field(None, description="Ground truth answer or expected response summary")
    actual_answer: Optional[str] = Field(None, description="Actual answer emitted by the pipeline")
    is_structured_exact_match: Optional[bool] = Field(None, description="Exact match on deterministic SQL lookup")
    nli_scores: list[float] = Field(default_factory=list, description="Per-sentence NLI entailment scores")
    contradiction_scores: list[float] = Field(default_factory=list, description="Per-sentence NLI contradiction scores")
    valid_citations_count: int = Field(default=0, ge=0, description="Number of claims with valid byte-offset anchors")
    total_citations_count: int = Field(default=0, ge=0, description="Total number of citations generated")
    retrieved_chunk_ids: list[str] = Field(default_factory=list, description="Chunk IDs or breadcrumbs retrieved by hybrid search")
    ground_truth_chunk_ids: list[str] = Field(default_factory=list, description="Ground truth relevant chunk IDs or doc refs")
    is_abstained: bool = Field(default=False, description="Whether the pipeline emitted a certified abstention")
    expected_abstained: bool = Field(default=False, description="Whether this question is expected to trigger abstention")
    refusal_reason: Optional[str] = Field(None, description="Reason code if abstained")
    latency_ms: float = Field(default=0.0, ge=0.0, description="End-to-end execution latency in milliseconds")


class MetricSummary(BaseModel):
    """
    Quantified summary of evaluation metrics adhering to Reference/PROJECT_ANCHOR_BLUEPRINT.md:L390-406.
    """

    total_questions: int = Field(default=0, ge=0)
    structured_questions_count: int = Field(default=0, ge=0)
    interpretive_questions_count: int = Field(default=0, ge=0)
    ood_questions_count: int = Field(default=0, ge=0)
    faithfulness: float = Field(default=1.0, ge=0.0, le=1.0, description="Ratio of NLI-verified claims (>=0.85)")
    citation_precision: float = Field(default=1.0, ge=0.0, le=1.0, description="Ratio of valid byte-anchored citations")
    context_recall: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-3 retrieval recall against ground truth")
    abstention_accuracy: float = Field(default=1.0, ge=0.0, le=1.0, description="Correct refusal rate on OOD queries")
    hallucination_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Proportion of unverified/contradictory claims")
    structured_accuracy: float = Field(default=1.0, ge=0.0, le=1.0, description="Exact match on deterministic SQL resolver")
    avg_latency_ms: float = Field(default=0.0, ge=0.0, description="Average question execution latency in milliseconds")
    p95_latency_ms: float = Field(default=0.0, ge=0.0, description="95th percentile latency in milliseconds")


def compute_faithfulness(nli_scores: list[float], threshold: float = 0.85) -> float:
    """
    Compute Faithfulness ratio:
    Faithfulness = (Count of claims with NLI entailment >= threshold) / (Total claims)
    """
    if not nli_scores:
        return 1.0
    verified_count = sum(1 for s in nli_scores if s >= threshold)
    return round(float(verified_count / len(nli_scores)), 4)


def compute_citation_precision(valid_citations: int, total_citations: int) -> float:
    """
    Compute Citation Precision ratio:
    Citation Precision = (Claims with valid byte-offset anchor) / (Total cited claims)
    """
    if total_citations <= 0:
        return 1.0
    precision = min(1.0, float(valid_citations / total_citations))
    return round(precision, 4)


def compute_context_recall(
    retrieved_chunk_ids: list[str],
    ground_truth_chunk_ids: list[str],
    top_k: int = 3,
) -> float:
    """
    Compute Context Recall (MRR / top-k hit ratio against ground truth chunks):
    Context Recall = (Relevant ground truth chunks found in top-k) / (Total ground truth chunks)
    """
    if not ground_truth_chunk_ids:
        return 1.0
    top_retrieved = retrieved_chunk_ids[:top_k]
    hits = 0
    for gt in ground_truth_chunk_ids:
        gt_clean = gt.lower().replace("-", "_").replace(" ", "_").replace(".pdf", "").strip()
        for r in top_retrieved:
            r_clean = r.lower().replace("-", "_").replace(" ", "_").replace(".pdf", "").strip()
            if gt_clean in r_clean or r_clean in gt_clean:
                hits += 1
                break
    return round(float(hits / len(ground_truth_chunk_ids)), 4)


def compute_abstention_accuracy(correct_abstentions: int, total_ood_queries: int) -> float:
    """
    Compute Abstention Accuracy:
    Abstention Accuracy = (Correct abstentions) / (Total OOD / contradictory queries)
    """
    if total_ood_queries <= 0:
        return 1.0
    return round(float(correct_abstentions / total_ood_queries), 4)


def compute_hallucination_rate(unverified_claims: int, total_claims: int) -> float:
    """
    Compute Hallucination Rate:
    Hallucination Rate = (Unverified or contradictory claims) / (Total claims)
    """
    if total_claims <= 0:
        return 0.0
    rate = min(1.0, float(unverified_claims / total_claims))
    return round(rate, 4)


def compute_structured_accuracy(exact_matches: int, total_structured: int) -> float:
    """
    Compute Structured Query Accuracy:
    Structured Accuracy = (Exact matches on deterministic SQL resolver) / (Total structured questions)
    """
    if total_structured <= 0:
        return 1.0
    return round(float(exact_matches / total_structured), 4)


def compute_aggregate_metrics(results: list[EvaluationResult]) -> MetricSummary:
    """
    Compute aggregate MetricSummary across all evaluation question results.
    """
    if not results:
        return MetricSummary()

    total_questions = len(results)
    structured_results = [r for r in results if r.archetype == "STRUCTURED" or r.is_structured_exact_match is not None]
    interpretive_results = [r for r in results if r.archetype != "STRUCTURED" and not r.expected_abstained]
    ood_results = [r for r in results if r.expected_abstained or r.archetype == "ABSTENTION"]

    # 1. Structured accuracy
    exact_matches = sum(1 for r in structured_results if r.is_structured_exact_match is True)
    structured_acc = compute_structured_accuracy(exact_matches, len(structured_results))

    # 2. Faithfulness & Hallucination (evaluated across non-abstained emitted claims)
    all_nli_scores: list[float] = []
    for r in results:
        if not r.is_abstained and r.nli_scores:
            all_nli_scores.extend(r.nli_scores)

    faithfulness = compute_faithfulness(all_nli_scores, threshold=0.85)

    unverified_count = sum(1 for s in all_nli_scores if s < 0.85)
    hallucination_rate = compute_hallucination_rate(unverified_count, len(all_nli_scores))

    # 3. Citation Precision
    total_valid_cit = sum(r.valid_citations_count for r in results if not r.is_abstained)
    total_cit = sum(r.total_citations_count for r in results if not r.is_abstained)
    citation_precision = compute_citation_precision(total_valid_cit, total_cit)

    # 4. Context Recall
    recalls = [
        compute_context_recall(r.retrieved_chunk_ids, r.ground_truth_chunk_ids, top_k=3)
        for r in interpretive_results
        if r.ground_truth_chunk_ids
    ]
    context_recall = round(float(sum(recalls) / len(recalls)), 4) if recalls else 1.0

    # 5. Abstention Accuracy
    correct_refusals = sum(1 for r in ood_results if r.is_abstained is True)
    abstention_accuracy = compute_abstention_accuracy(correct_refusals, len(ood_results))

    # 6. Latency statistics
    latencies = sorted([r.latency_ms for r in results])
    avg_latency = round(float(sum(latencies) / len(latencies)), 2)
    p95_idx = int(len(latencies) * 0.95)
    p95_latency = round(float(latencies[min(p95_idx, len(latencies) - 1)]), 2)

    return MetricSummary(
        total_questions=total_questions,
        structured_questions_count=len(structured_results),
        interpretive_questions_count=len(interpretive_results),
        ood_questions_count=len(ood_results),
        faithfulness=faithfulness,
        citation_precision=citation_precision,
        context_recall=context_recall,
        abstention_accuracy=abstention_accuracy,
        hallucination_rate=hallucination_rate,
        structured_accuracy=structured_acc,
        avg_latency_ms=avg_latency,
        p95_latency_ms=p95_latency,
    )
