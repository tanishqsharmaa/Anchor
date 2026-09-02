"""
test_deck_compiler.py — Unit Tests for Slide AST Compiler
"""

import json
from unittest.mock import MagicMock
import pytest

from anchor.deck.ast_compiler import ASTCompiler, extract_json_from_text
from anchor.deck.schemas import SlideDeckAST, SlideType


def test_extract_json_from_markdown():
    raw_markdown = """
Here is the generated briefing deck:

```json
{
  "deck_id": "deck_test_01",
  "title": "Tactical Drone Procurement",
  "topic": "Tactical Drones",
  "classification": "RESTRICTED // FOR OFFICIAL USE ONLY",
  "slides": [
    {
      "slide_id": "s1",
      "type": "HERO_SLIDE",
      "title": "Title",
      "content": {
        "title": "TACTICAL DRONES",
        "dtg": "310300Z AUG 2026"
      }
    }
  ]
}
```

Hope this helps!
"""
    extracted = extract_json_from_text(raw_markdown)
    assert extracted["deck_id"] == "deck_test_01"
    assert len(extracted["slides"]) == 1


def test_extract_json_raw_string():
    raw = '{"deck_id": "deck_raw", "title": "Raw Title", "topic": "Topic", "slides": []}'
    extracted = extract_json_from_text(raw)
    assert extracted["deck_id"] == "deck_raw"


def test_compile_deterministic_schedule_07():
    compiler = ASTCompiler()
    deck = compiler.compile_deterministic_schedule(schedule_no=7)
    assert isinstance(deck, SlideDeckAST)
    assert deck.total_slides == 4
    assert deck.slides[0].type == SlideType.HERO_SLIDE
    assert deck.slides[1].type == SlideType.BLUF_EXECUTIVE
    assert deck.slides[2].type == SlideType.FINANCIAL_DELEGATION
    assert deck.slides[3].type == SlideType.POLICY_MATRIX

    fin_slide = deck.slides[2].content
    assert fin_slide.schedule_no == 7
    assert len(fin_slide.tiers) >= 1
    # Verify Tier limits are populated
    cns_tier = next((t for t in fin_slide.tiers if "Tier 1" in t.tier or "CNS" in t.tier_name), None)
    assert cns_tier is not None
    assert cns_tier.with_ifa_limit > 0


def test_compile_deterministic_schedule_invalid():
    compiler = ASTCompiler()
    with pytest.raises(ValueError):
        compiler.compile_deterministic_schedule(schedule_no=99)


def test_compile_ast_mock_generator():
    sample_json = {
        "deck_id": "deck_mock_1",
        "title": "Mock Briefing Deck",
        "topic": "Naval Logistics",
        "classification": "RESTRICTED // FOR OFFICIAL USE ONLY",
        "dtg": "310300Z AUG 2026",
        "slides": [
            {
                "slide_id": "slide_1",
                "type": "HERO_SLIDE",
                "title": "Cover",
                "content": {
                    "title": "NAVAL LOGISTICS BRIEFING",
                    "dtg": "310300Z AUG 2026"
                }
            },
            {
                "slide_id": "slide_2",
                "type": "BLUF_EXECUTIVE",
                "title": "BLUF",
                "content": {
                    "bluf_headline": "Critical supply chain replenishment required.",
                    "key_takeaways": ["Takeaway 1", "Takeaway 2"],
                    "decision_requested": "Sanction replenishment.",
                    "risk_summary": "Low risk."
                }
            }
        ]
    }

    mock_gen = MagicMock()
    mock_gen.generate.return_value = f"```json\n{json.dumps(sample_json)}\n```"

    compiler = ASTCompiler(generator=mock_gen)
    deck = compiler.compile_ast(topic="Naval Logistics")

    assert deck.deck_id == "deck_mock_1"
    assert deck.total_slides == 2
    assert deck.slides[0].type == SlideType.HERO_SLIDE


def test_compile_with_repair_first_pass_succeeds():
    sample_json = {
        "deck_id": "deck_repair_0",
        "title": "Mock Briefing Deck",
        "topic": "Maritime Patrol",
        "classification": "RESTRICTED // FOR OFFICIAL USE ONLY",
        "slides": [
            {
                "slide_id": "slide_1",
                "type": "HERO_SLIDE",
                "title": "Cover",
                "content": {
                    "title": "MARITIME PATROL BRIEFING",
                    "dtg": "310300Z AUG 2026"
                }
            }
        ]
    }

    mock_gen = MagicMock()
    mock_gen.generate.return_value = json.dumps(sample_json)

    compiler = ASTCompiler(generator=mock_gen)
    deck = compiler.compile_with_repair(topic="Maritime Patrol")

    assert deck.deck_id == "deck_repair_0"
    assert mock_gen.generate.call_count == 1


def test_compile_with_repair_second_pass_succeeds():
    # Pass 1: Broken JSON / invalid schema
    bad_output = "I am generating slides... { invalid json"
    # Pass 2: Repaired valid JSON
    good_json = {
        "deck_id": "deck_repaired_ok",
        "title": "Repaired Briefing Deck",
        "topic": "Undersea Surveillance",
        "classification": "RESTRICTED // FOR OFFICIAL USE ONLY",
        "slides": [
            {
                "slide_id": "slide_1",
                "type": "HERO_SLIDE",
                "title": "Cover",
                "content": {
                    "title": "UNDERSEA SURVEILLANCE",
                    "dtg": "310300Z AUG 2026"
                }
            }
        ]
    }

    mock_gen = MagicMock()
    mock_gen.generate.side_effect = [
        bad_output,
        f"```json\n{json.dumps(good_json)}\n```",
    ]

    compiler = ASTCompiler(generator=mock_gen)
    deck = compiler.compile_with_repair(topic="Undersea Surveillance")

    assert deck.deck_id == "deck_repaired_ok"
    assert mock_gen.generate.call_count == 2
