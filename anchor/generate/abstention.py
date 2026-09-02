"""
abstention.py — Certified Abstention & Structured Military Refusal Engine
"""

from enum import Enum
import logging
from typing import Any, Optional
from pydantic import BaseModel, Field

from anchor.generate.nli_gate import SentenceVerification

logger = logging.getLogger(__name__)


class RefusalReasonCode(str, Enum):
    """
    Standardized taxonomy of refusal codes for PROJECT ANCHOR.
    """

    INSUFFICIENT_CORPUS_CONTEXT = "INSUFFICIENT_CORPUS_CONTEXT"
    HIGH_CONTRADICTION_DETECTED = "HIGH_CONTRADICTION_DETECTED"
    UNVERIFIED_STATUTORY_CLAIM = "UNVERIFIED_STATUTORY_CLAIM"
    OUT_OF_DOMAIN_QUERY = "OUT_OF_DOMAIN_QUERY"


class RefusalPayload(BaseModel):
    """
    Structured refusal payload for ungrounded or contradictory queries.
    """

    is_refusal: bool = Field(default=True)
    code: RefusalReasonCode
    refusal_message: str
    explanation: str
    remedy_suggestions: list[str] = Field(default_factory=list)
    grounding_telemetry: dict[str, Any] = Field(default_factory=dict)


class CertifiedAbstention:
    """
    Certified Abstention Handler.
    Generates structured, auditable refusal responses when queries cannot be verified
    with mathematical certainty against the regulatory corpus.
    """

    def create_refusal(
        self,
        query: str,
        code: RefusalReasonCode = RefusalReasonCode.INSUFFICIENT_CORPUS_CONTEXT,
        details: Optional[str] = None,
        nli_records: Optional[list[SentenceVerification]] = None,
    ) -> RefusalPayload:
        """
        Construct a structured refusal payload.

        Args:
            query: The original search or compliance query string.
            code: The specific RefusalReasonCode.
            details: Optional custom explanation detail.
            nli_records: Optional list of SentenceVerification records with score breakdowns.

        Returns:
            RefusalPayload: Structured refusal response object.
        """
        telemetry: dict[str, Any] = {}
        if nli_records:
            contra_scores = [r.contradiction_score for r in nli_records]
            entail_scores = [r.entailment_score for r in nli_records]
            telemetry["sentence_count"] = len(nli_records)
            telemetry["max_contradiction"] = float(max(contra_scores)) if contra_scores else 0.0
            telemetry["min_entailment"] = float(min(entail_scores)) if entail_scores else 0.0
            telemetry["failed_sentences"] = [
                {"idx": r.sentence_idx, "text": r.text, "status": r.status}
                for r in nli_records
                if r.status != "certified"
            ]

        # Determine explanation and remedy suggestions based on code
        if code == RefusalReasonCode.OUT_OF_DOMAIN_QUERY:
            explanation = (
                details
                or f"The requested query '{query.strip()}' lies outside the scope of DFPDS-2026, DPM 2025, and Navy Regulations."
            )
            remedy_suggestions = [
                "Verify that the query pertains to naval revenue procurements, financial delegations, or DPM tendering procedures.",
                "Specify a valid DFPDS Schedule number (e.g., Schedule 1 through 32) or Competent Financial Authority appointment.",
            ]
        elif code == RefusalReasonCode.HIGH_CONTRADICTION_DETECTED:
            explanation = (
                details
                or "A direct statutory contradiction or prohibited action was detected against regulatory provisions."
            )
            remedy_suggestions = [
                "Review the specific CFA tier thresholds or IFA concurrence requirements.",
                "Ensure emergency or sole-source procurement conditions are explicitly cited.",
            ]
        elif code == RefusalReasonCode.UNVERIFIED_STATUTORY_CLAIM:
            explanation = (
                details
                or "The synthesized claims could not meet the mandatory NLI entailment threshold (>= 0.85) against source text."
            )
            remedy_suggestions = [
                "Refine the question to target specific clause provisions or schedule tables.",
                "Check whether additional context or schedule appendices are required.",
            ]
        else:
            # INSUFFICIENT_CORPUS_CONTEXT
            explanation = (
                details
                or "No sufficiently relevant or authoritative clauses were found in the indexed regulatory corpus."
            )
            remedy_suggestions = [
                "Rephrase the question using standard naval terminology (e.g., CFA, IFA, STE, PAC, OTE).",
                "Ensure the requested authority or financial power is covered under the current regulatory framework.",
            ]

        refusal_message = (
            f"No verified answer found in the regulatory corpus for: '{query.strip()}'."
        )

        return RefusalPayload(
            is_refusal=True,
            code=code,
            refusal_message=refusal_message,
            explanation=explanation,
            remedy_suggestions=remedy_suggestions,
            grounding_telemetry=telemetry,
        )

    def format_military_refusal(self, payload: RefusalPayload) -> str:
        """
        Format a RefusalPayload into a standard C4ISR tactical refusal banner.
        """
        lines = [
            "⚠️ CERTIFIED ABSTENTION — No verified answer found in the regulatory corpus.",
            f"[Reason Code]: {payload.code.value}",
            f"[Explanation]: {payload.explanation}",
            "\n[Remedy Suggestions]:",
        ]
        for suggestion in payload.remedy_suggestions:
            lines.append(f"  • {suggestion}")

        return "\n".join(lines)
