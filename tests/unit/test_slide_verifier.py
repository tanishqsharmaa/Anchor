"""
test_slide_verifier.py — Unit Tests for Slide NLI Verifier
"""

from unittest.mock import MagicMock
import pytest

from anchor.deck.slide_verifier import SlideVerifier
from anchor.deck.schemas import (
    SlideType,
    HeroSlideContent,
    BLUFSlideContent,
    PolicyMatrixSlideContent,
    MatrixRow,
    FinancialDelegationSlideContent,
    FinancialTierItem,
    SlideItem,
    SlideDeckAST,
    DeckVerificationResult,
)
from anchor.generate.nli_gate import SentenceVerification
from anchor.retrieve.hybrid import RetrievedChunk


def test_extract_slide_claims_all_types():
    verifier = SlideVerifier()

    hero = SlideItem(
        slide_id="s1",
        type=SlideType.HERO_SLIDE,
        title="Cover",
        content=HeroSlideContent(
            title="TACTICAL UAV BRIEFING",
            subtitle="Western Naval Command Operational Reserve",
        ),
    )
    claims_hero = verifier.extract_slide_claims(hero)
    assert len(claims_hero) >= 2
    assert "TACTICAL UAV BRIEFING" in claims_hero[0]

    bluf = SlideItem(
        slide_id="s2",
        type=SlideType.BLUF_EXECUTIVE,
        title="BLUF",
        content=BLUFSlideContent(
            bluf_headline="Sanction required for 12 UAVs.",
            key_takeaways=["Reserve at 30%.", "Tier 3 authorized up to 18 Cr."],
            decision_requested="Approve financial sanction.",
            risk_summary="Supply chain lead time 45 days.",
        ),
    )
    claims_bluf = verifier.extract_slide_claims(bluf)
    assert len(claims_bluf) >= 4


def test_verify_deck_grounded_claims():
    # Mock NLIGate
    mock_gate = MagicMock()
    mock_gate.split_atomic_sentences.side_effect = lambda text: [text]
    mock_gate.verify_sentence.return_value = SentenceVerification(
        sentence_idx=0,
        text="Sample claim",
        entailment_score=0.95,
        neutral_score=0.04,
        contradiction_score=0.01,
        status="certified",
    )

    verifier = SlideVerifier(nli_gate=mock_gate)

    bluf = SlideItem(
        slide_id="s1",
        type=SlideType.BLUF_EXECUTIVE,
        title="BLUF",
        content=BLUFSlideContent(
            bluf_headline="Grounded headline.",
            key_takeaways=["Grounded takeaway 1."],
            decision_requested="Decision.",
        ),
    )

    deck_ast = SlideDeckAST(
        deck_id="deck_test_grounded",
        title="Grounded Deck",
        topic="Grounded Topic",
        slides=[bluf],
    )

    dummy_chunk = RetrievedChunk(
        chunk_id="chk_01",
        doc_id="DFPDS-2026",
        schedule_no=7,
        section="Schedule 7",
        breadcrumb="DFPDS-2026/Sch_07",
        page_no=1,
        bbox=[0.0, 0.0, 100.0, 100.0],
        text="Grounded source context",
        sha256="abc123def456",
        score=0.85,
    )

    updated_ast, report = verifier.verify_deck(deck_ast, context_chunks=[dummy_chunk])

    assert report.all_claims_verified is True
    assert report.lowest_nli_score == 0.95
    assert len(report.flagged_claims) == 0
    assert updated_ast.slides[0].is_verified is True


def test_verify_deck_flagged_claims():
    mock_gate = MagicMock()
    mock_gate.split_atomic_sentences.side_effect = lambda text: [text]
    mock_gate.verify_sentence.return_value = SentenceVerification(
        sentence_idx=0,
        text="Hallucinated claim",
        entailment_score=0.30,
        neutral_score=0.40,
        contradiction_score=0.30,
        status="abstain",
    )

    verifier = SlideVerifier(nli_gate=mock_gate)

    bluf = SlideItem(
        slide_id="s1",
        type=SlideType.BLUF_EXECUTIVE,
        title="BLUF",
        content=BLUFSlideContent(
            bluf_headline="Hallucinated headline statement.",
            key_takeaways=["Takeaway."],
            decision_requested="Decision.",
        ),
    )

    deck_ast = SlideDeckAST(
        deck_id="deck_test_hallucinated",
        title="Hallucinated Deck",
        topic="Hallucinated Topic",
        slides=[bluf],
    )

    dummy_chunk = RetrievedChunk(
        chunk_id="chk_01",
        doc_id="DFPDS-2026",
        schedule_no=7,
        section="Schedule 7",
        breadcrumb="DFPDS-2026/Sch_07",
        page_no=1,
        bbox=[0.0, 0.0, 100.0, 100.0],
        text="Grounded source context",
        sha256="abc123def456",
        score=0.85,
    )

    updated_ast, report = verifier.verify_deck(deck_ast, context_chunks=[dummy_chunk])

    assert report.all_claims_verified is False
    assert report.lowest_nli_score == 0.30
    assert len(report.flagged_claims) > 0
    assert updated_ast.slides[0].is_verified is False
