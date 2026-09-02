"""
test_html_renderer.py — Unit Tests for HTML5 Slide Preview Renderer
"""

import pytest

from anchor.deck.ast_compiler import ASTCompiler
from anchor.deck.html_renderer import HTMLRenderer
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
)


def test_html_renderer_all_slide_types():
    renderer = HTMLRenderer()

    hero = SlideItem(
        slide_id="s1",
        type=SlideType.HERO_SLIDE,
        title="Cover",
        content=HeroSlideContent(
            title="TACTICAL DRONE BRIEFING",
            subtitle="Western Fleet",
            officer="CDR SHARMA",
        ),
    )
    bluf = SlideItem(
        slide_id="s2",
        type=SlideType.BLUF_EXECUTIVE,
        title="BLUF Summary",
        content=BLUFSlideContent(
            bluf_headline="Sanction required for UAV units.",
            key_takeaways=["Point A", "Point B"],
            decision_requested="Approve sanction.",
        ),
    )
    matrix = SlideItem(
        slide_id="s3",
        type=SlideType.POLICY_MATRIX,
        title="Policy Matrix",
        content=PolicyMatrixSlideContent(
            matrix_title="Mode Comparison",
            headers=["Mode", "Rule"],
            rows=[MatrixRow(row_title="OTE", cells=["Open tender"])],
        ),
    )
    fin = SlideItem(
        slide_id="s4",
        type=SlideType.FINANCIAL_DELEGATION,
        title="Financial Limits",
        content=FinancialDelegationSlideContent(
            schedule_title="Schedule 7",
            schedule_no=7,
            tiers=[
                FinancialTierItem(
                    tier="Tier 1",
                    tier_name="CNS",
                    with_ifa_limit=50.0,
                    without_ifa_limit=5.0,
                )
            ],
        ),
    )

    deck_ast = SlideDeckAST(
        deck_id="deck_html_01",
        title="Briefing Presentation",
        topic="Drones",
        slides=[hero, bluf, matrix, fin],
    )

    html_slides = renderer.render_deck(deck_ast)
    assert len(html_slides) == 4
    for slide_str in html_slides:
        assert isinstance(slide_str, str)
        assert "<section class='c4isr-slide" in slide_str
        assert "</section>" in slide_str


def test_html_renderer_escaping():
    renderer = HTMLRenderer()
    hero = SlideItem(
        slide_id="s1",
        type=SlideType.HERO_SLIDE,
        title="Cover Title",
        content=HeroSlideContent(
            title="<img src=x onerror=alert(1)>",
            subtitle="<b>Safe Subtitle</b>",
        ),
    )
    html_out = renderer.render_slide(hero)
    assert "<img src=x" not in html_out
    assert "&lt;img src=x onerror=alert(1)&gt;" in html_out
    assert "&lt;b&gt;Safe Subtitle&lt;/b&gt;" in html_out


def test_html_renderer_deterministic_deck():
    compiler = ASTCompiler()
    deck_ast = compiler.compile_deterministic_schedule(schedule_no=7)

    renderer = HTMLRenderer()
    html_slides = renderer.render_deck(deck_ast)

    assert len(html_slides) == deck_ast.total_slides
    assert "DFPDS-2026 SCHEDULE 07" in html_slides[0]
