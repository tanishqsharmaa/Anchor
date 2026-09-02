"""
test_reranker.py — Unit Tests for Cross-Encoder Reranker Engine
"""

import pytest
from anchor.retrieve.hybrid import RetrievedChunk
from anchor.retrieve.reranker import Reranker


def make_test_chunk(
    chunk_id: str,
    text: str,
    doc_id: str = "DFPDS-2026",
    schedule_no: int = 7,
    score: float = 0.5,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        schedule_no=schedule_no,
        section=f"Section_{schedule_no}",
        breadcrumb=f"{doc_id}/Schedule_{schedule_no:02d}",
        page_no=1,
        bbox=[100.0, 200.0, 300.0, 400.0],
        text=text,
        sha256=f"hash_{chunk_id}",
        score=score,
    )


@pytest.fixture(scope="module")
def reranker():
    return Reranker()


def test_reranker_truncation_to_top_3(reranker):
    """Verify reranker truncates 10 input candidate chunks to top-3."""
    query = "What is the financial limit for Fleet Commander under Schedule 7?"
    chunks = [
        make_test_chunk(f"c_{i}", f"General information clause {i} with non-specific limits.")
        for i in range(10)
    ]
    # Make chunk 7 highly specific
    chunks[7] = make_test_chunk(
        "c_7",
        "Under DFPDS-2026 Schedule 07, Fleet Commander (Tier 3) financial power is ₹18.00 Crore with IFA.",
    )

    reranked = reranker.rerank(query, chunks, top_k=3)

    assert len(reranked) == 3
    # Most relevant chunk should be ranked first
    assert reranked[0].chunk_id == "c_7"
    assert reranked[0].score >= reranked[1].score >= reranked[2].score


def test_reranker_provenance_preservation(reranker):
    """Verify all cryptographic and spatial metadata properties are preserved."""
    query = "Dry docking financial threshold"
    chunk = make_test_chunk(
        "dock_01",
        "DFPDS-2026 Schedule 01 covers Dry Docking and Ship Repairs in Naval Dockyards.",
        doc_id="DFPDS-2026/SCH-01",
        schedule_no=1,
        score=0.1,
    )

    reranked = reranker.rerank(query, [chunk], top_k=1)

    assert len(reranked) == 1
    c = reranked[0]
    assert c.chunk_id == "dock_01"
    assert c.doc_id == "DFPDS-2026/SCH-01"
    assert c.schedule_no == 1
    assert c.page_no == 1
    assert c.bbox == [100.0, 200.0, 300.0, 400.0]
    assert c.sha256 == "hash_dock_01"
    assert c.breadcrumb == chunk.breadcrumb
    assert c.score > 0.0


def test_reranker_mrr_at_10(reranker):
    """Verify MRR@10 >= 0.90 across benchmark test queries."""
    benchmarks = [
        {
            "query": "Who is the Competent Financial Authority for Emergency Procurement under DFPDS Schedule 28?",
            "target_id": "target_sch28",
            "candidates": [
                make_test_chunk("noise_1", "Routine office stationary purchases."),
                make_test_chunk("noise_2", "Mess maintenance committee procedures."),
                make_test_chunk("target_sch28", "Schedule 28: Emergency Procurement powers delegated to Vice Chief of Naval Staff and FOC-in-C up to ₹50 Crore."),
                make_test_chunk("noise_3", "Uniform and clothing inspection rules."),
            ],
        },
        {
            "query": "Single Tender Enquiry justification and PAC certificate limit under DPM 2025.",
            "target_id": "target_pac",
            "candidates": [
                make_test_chunk("noise_4", "Open tender enquiry advertisement timeline in national newspapers."),
                make_test_chunk("target_pac", "DPM 2025 Chapter 3: Single Tender Enquiry (STE) requires a Proprietary Article Certificate (PAC) approved by CFA."),
                make_test_chunk("noise_5", "Disposal of obsolete naval scrap stores."),
            ],
        },
        {
            "query": "Liquidated damages rate for delay in delivery of naval stores.",
            "target_id": "target_ld",
            "candidates": [
                make_test_chunk("target_ld", "Liquidated Damages (LD) shall be levied at 0.5% per week of delay up to a maximum of 10%."),
                make_test_chunk("noise_6", "Warranty clause for electronic communication equipment."),
                make_test_chunk("noise_7", "Performance Bank Guarantee submission within 30 days."),
            ],
        },
    ]

    reciprocal_ranks = []
    for b in benchmarks:
        results = reranker.rerank(b["query"], b["candidates"], top_k=len(b["candidates"]))
        rank = next((idx + 1 for idx, c in enumerate(results) if c.chunk_id == b["target_id"]), None)
        assert rank is not None, f"Target chunk not found in reranked results for query {b['query']}"
        reciprocal_ranks.append(1.0 / rank)

    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
    assert mrr >= 0.90, f"MRR@10 is {mrr:.2f}, expected >= 0.90"


def test_reranker_empty_input(reranker):
    """Verify reranker handles empty chunk lists gracefully."""
    assert reranker.rerank("some query", [], top_k=3) == []
