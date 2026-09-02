"""
test_abstention.py — Unit Tests for Certified Abstention Logic
"""

import pytest

from anchor.generate.abstention import (
    CertifiedAbstention,
    RefusalPayload,
    RefusalReasonCode,
)
from anchor.generate.nli_gate import SentenceVerification


def test_abstention_create_insufficient_context_refusal():
    abstain = CertifiedAbstention()
    payload = abstain.create_refusal(
        query="What is the capital budget for INS Vishal in FY 2027?",
        code=RefusalReasonCode.OUT_OF_DOMAIN_QUERY,
        details="Capital budget allocation for future aircraft carriers is not covered by DFPDS-2026 or DPM 2025.",
    )

    assert isinstance(payload, RefusalPayload)
    assert payload.is_refusal is True
    assert payload.code == RefusalReasonCode.OUT_OF_DOMAIN_QUERY
    assert "INS Vishal" in payload.refusal_message or "INS Vishal" in payload.explanation
    assert len(payload.remedy_suggestions) > 0


def test_abstention_create_contradiction_refusal():
    abstain = CertifiedAbstention()
    mock_record = SentenceVerification(
        sentence_idx=0,
        text="A Fleet Commander may sanction Rs 100 Cr without IFA.",
        entailment_score=0.04,
        neutral_score=0.10,
        contradiction_score=0.86,
        status="abstain",
    )

    payload = abstain.create_refusal(
        query="Can Fleet Commander sanction 100 Cr without IFA?",
        code=RefusalReasonCode.HIGH_CONTRADICTION_DETECTED,
        nli_records=[mock_record],
    )

    assert payload.code == RefusalReasonCode.HIGH_CONTRADICTION_DETECTED
    assert payload.grounding_telemetry["max_contradiction"] == 0.86
    assert "contradiction" in payload.explanation.lower()


def test_abstention_military_formatting():
    abstain = CertifiedAbstention()
    payload = abstain.create_refusal(
        query="What is the capital budget?",
        code=RefusalReasonCode.INSUFFICIENT_CORPUS_CONTEXT,
    )

    banner = abstain.format_military_refusal(payload)
    assert "CERTIFIED ABSTENTION" in banner
    assert "INSUFFICIENT_CORPUS_CONTEXT" in banner
    assert "[Remedy Suggestions]" in banner
