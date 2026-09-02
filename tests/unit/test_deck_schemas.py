"""
test_deck_schemas.py — Unit Tests for AutoDeck AST Pydantic Schemas
"""

import pytest
from pydantic import ValidationError

from anchor.deck.schemas import (
    SlideType,
    ClassificationMarking,
    UrgencyTier,
    HeroSlideContent,
    BLUFSlideContent,
    MatrixRow,
    PolicyMatrixSlideContent,
    FinancialTierItem,
    FinancialDelegationSlideContent,
    SlideItem,
    SlideDeckAST,
    DeckVerificationResult,
)


def test_hero_slide_schema_valid():
    content = HeroSlideContent(
        title="TACTICAL DRONE PROCUREMENT BRIEFING",
        subtitle="Operational Replenishment for Western Fleet",
        dtg="310300Z AUG 2026",
        classification=ClassificationMarking.RESTRICTED_OFFICIAL.value,
        officer="CDR A. SHARMA, SO (PLANS)",
        unit="HQ WESTERN NAVAL COMMAND",
    )
    assert content.title == "TACTICAL DRONE PROCUREMENT BRIEFING"
    assert content.classification == "RESTRICTED // FOR OFFICIAL USE ONLY"


def test_hero_slide_schema_length_rejection():
    with pytest.raises(ValidationError):
        HeroSlideContent(
            title="A" * 125,  # Exceeds max 100 chars
        )


def test_bluf_slide_schema_valid():
    content = BLUFSlideContent(
        bluf_headline="Sanction of ₹18.00 Cr required under DFPDS Schedule 7 for 12 Tactical UAV units.",
        key_takeaways=[
            "Western Fleet operational reserve depleted to 30%.",
            "CFA Tier 3 (Fleet Commander) authorized up to ₹18.00 Cr with IFA concurrence.",
            "Indigenisation content meets 60% Make-in-India requirement.",
        ],
        decision_requested="Fleet Commander financial sanction with IFA concurrence.",
        risk_summary="Supply chain lead time 45 days if PAC invoked.",
        urgency=UrgencyTier.OPERATIONAL_IMMEDIATE,
    )
    assert len(content.key_takeaways) == 3
    assert content.urgency == UrgencyTier.OPERATIONAL_IMMEDIATE


def test_bluf_slide_takeaway_length_rejection():
    with pytest.raises(ValidationError):
        BLUFSlideContent(
            bluf_headline="Short headline",
            key_takeaways=["Valid", "X" * 210],  # Exceeds 180 chars
            decision_requested="Decision",
        )


def test_policy_matrix_slide_schema_valid():
    content = PolicyMatrixSlideContent(
        matrix_title="Procurement Mode Statutory Comparison",
        headers=["Parameter", "Open Tender (OTE)", "Single Tender (STE/PAC)"],
        rows=[
            MatrixRow(
                row_title="Competition Requirement",
                cells=["Minimum 3 bids required", "Proprietary justification required"],
            ),
            MatrixRow(
                row_title="IFA Concurrence",
                cells=["Mandatory above Tier 4", "Mandatory across all tiers"],
            ),
        ],
        statutory_precedence_note="DFPDS-2026 Schedule 7 takes precedence over DPM-2025.",
    )
    assert len(content.rows) == 2
    assert len(content.headers) == 3


def test_policy_matrix_cell_count_mismatch_rejection():
    with pytest.raises(ValidationError):
        PolicyMatrixSlideContent(
            matrix_title="Mismatched Matrix",
            headers=["Col 1", "Col 2", "Col 3"],
            rows=[
                MatrixRow(
                    row_title="Row 1",
                    cells=["Cell A", "Cell B", "Cell C", "Cell D"],
                )
            ],
        )


def test_financial_delegation_slide_schema_valid():
    content = FinancialDelegationSlideContent(
        schedule_title="Schedule 7: Procurement of Tactical Drones & Spares",
        schedule_no=7,
        head_of_account="Major Head 2077 - Navy, Minor Head 110",
        tiers=[
            FinancialTierItem(
                tier="Tier 1",
                tier_name="Chief of the Naval Staff",
                with_ifa_limit=50.0,
                without_ifa_limit=5.0,
                pac_limit=25.0,
            ),
            FinancialTierItem(
                tier="Tier 2",
                tier_name="Flag Officer Commanding-in-Chief",
                with_ifa_limit=25.0,
                without_ifa_limit=2.5,
                pac_limit=12.5,
            ),
            FinancialTierItem(
                tier="Tier 3",
                tier_name="Fleet Commander",
                with_ifa_limit=18.0,
                without_ifa_limit=1.0,
                pac_limit=5.0,
            ),
        ],
        indigenisation_percentage=60.0,
        notes="All sanctions above ₹5.0 Cr require mandatory IFA concurrence.",
    )
    assert content.schedule_no == 7
    assert len(content.tiers) == 3


def test_financial_delegation_invalid_schedule_rejection():
    with pytest.raises(ValidationError):
        FinancialDelegationSlideContent(
            schedule_title="Invalid Schedule",
            schedule_no=99,  # Out of range 1..32
            tiers=[
                FinancialTierItem(
                    tier="Tier 1",
                    tier_name="CNS",
                    with_ifa_limit=10.0,
                    without_ifa_limit=1.0,
                )
            ],
        )


def test_slide_item_polymorphic_validation():
    hero_content = HeroSlideContent(
        title="TITLE",
        dtg="310300Z AUG 2026",
    )
    slide = SlideItem(
        slide_id="slide_01",
        type=SlideType.HERO_SLIDE,
        title="Hero Title",
        content=hero_content,
    )
    assert slide.type == SlideType.HERO_SLIDE
    assert isinstance(slide.content, HeroSlideContent)


def test_slide_item_type_content_mismatch():
    bluf_content = BLUFSlideContent(
        bluf_headline="Headline",
        key_takeaways=["Takeaway 1"],
        decision_requested="Decision",
    )
    with pytest.raises(ValidationError):
        SlideItem(
            slide_id="slide_01",
            type=SlideType.HERO_SLIDE,
            title="Hero Title",
            content=bluf_content,
        )


def test_slide_deck_ast_valid():
    hero = SlideItem(
        slide_id="s1",
        type=SlideType.HERO_SLIDE,
        title="Cover",
        content=HeroSlideContent(title="Briefing Title"),
    )
    bluf = SlideItem(
        slide_id="s2",
        type=SlideType.BLUF_EXECUTIVE,
        title="BLUF",
        content=BLUFSlideContent(
            bluf_headline="Main decision headline",
            key_takeaways=["Point 1", "Point 2"],
            decision_requested="Approve budget",
        ),
    )
    deck = SlideDeckAST(
        deck_id="deck_test_123",
        title="Tactical Briefing Deck",
        topic="Tactical Drones Schedule 7",
        slides=[hero, bluf],
    )
    assert deck.total_slides == 2
    assert deck.slides[0].type == SlideType.HERO_SLIDE
    assert deck.slides[1].type == SlideType.BLUF_EXECUTIVE


def test_deck_verification_result():
    res = DeckVerificationResult(
        deck_id="deck_123",
        all_claims_verified=True,
        lowest_nli_score=0.92,
        total_claims=6,
        verified_claims_count=6,
        flagged_claims=[],
    )
    assert res.all_claims_verified is True
    assert res.lowest_nli_score == 0.92
