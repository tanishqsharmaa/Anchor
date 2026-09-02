"""
test_deck.py — Comprehensive AutoDeck AI Quality Gate and Benchmark Suite
Validates AST Validity >= 94%, Slide Generation Latency < 850ms p95, and NLI verification.
"""

import time
import numpy as np
import pytest
from pptx import Presentation

from anchor.deck.ast_compiler import ASTCompiler
from anchor.deck.html_renderer import HTMLRenderer
from anchor.deck.pptx_renderer import PPTXRenderer
from anchor.deck.schemas import SlideDeckAST
from anchor.deck.slide_verifier import SlideVerifier


def test_autodeck_ast_validity_and_latency_benchmark(tmp_path):
    """
    Evaluates 20 test deck generations to benchmark:
    - Slide AST validity (target >= 94%)
    - Generation latency p95 (target < 850ms)
    """
    compiler = ASTCompiler()
    pptx_renderer = PPTXRenderer(output_dir=tmp_path)
    html_renderer = HTMLRenderer()
    verifier = SlideVerifier()

    latencies_ms: list[float] = []
    valid_decks = 0
    total_test_cases = 20

    # 20 distinct schedule numbers and scenarios across all naval operational domains
    test_schedules = [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
        11, 12, 13, 14, 15, 16, 17, 18, 19, 20
    ]

    for sch_no in test_schedules:
        start_t = time.perf_counter()

        # Compile deterministic schedule deck
        deck_ast = compiler.compile_deterministic_schedule(
            schedule_no=sch_no,
            topic=f"Procurement Briefing under DFPDS Schedule {sch_no}",
        )

        # Verify claims
        verified_ast, report = verifier.verify_deck(deck_ast)

        # Render PPTX
        pptx_file = pptx_renderer.render(verified_ast, output_filename=f"sch_{sch_no:02d}.pptx")

        # Render HTML
        html_slides = html_renderer.render_deck(verified_ast)

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        latencies_ms.append(elapsed_ms)

        # Validate PPTX can be opened
        prs = Presentation(str(pptx_file))
        is_pptx_valid = len(prs.slides) == verified_ast.total_slides

        # Validate HTML output
        is_html_valid = len(html_slides) == verified_ast.total_slides and all(len(s) > 100 for s in html_slides)

        if isinstance(verified_ast, SlideDeckAST) and is_pptx_valid and is_html_valid and report.all_claims_verified:
            valid_decks += 1

    validity_rate = valid_decks / total_test_cases
    p95_latency = float(np.percentile(latencies_ms, 95))
    avg_latency = float(np.mean(latencies_ms))

    print(f"\n[AutoDeck Benchmark] Validity: {validity_rate * 100:.1f}% ({valid_decks}/{total_test_cases})")
    print(f"[AutoDeck Benchmark] Avg Latency: {avg_latency:.2f}ms | p95 Latency: {p95_latency:.2f}ms")

    # Statutory Quality Gate Assertions
    assert validity_rate >= 0.94, f"Slide AST validity {validity_rate:.2%} below statutory threshold 94%"
    assert p95_latency < 850.0, f"Slide generation p95 latency {p95_latency:.2f}ms exceeded budget 850ms"
