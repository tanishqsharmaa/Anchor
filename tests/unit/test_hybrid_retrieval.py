"""
test_hybrid_retrieval.py — Unit Tests for Multi-Store Hybrid Retrieval & RRF Fusion
"""

import pytest
from anchor.retrieve.hybrid import HybridRetriever, RetrievedChunk


@pytest.fixture(scope="module")
def retriever():
    """Module-level fixture providing HybridRetriever."""
    return HybridRetriever()


def test_rrf_fusion_mathematical_ranking():
    """Verify Reciprocal Rank Fusion calculation: RRF_score = sum(1 / (k + rank))."""
    retriever_inst = HybridRetriever(embedder=None)

    dense_hits = [
        {"chunk_id": "chunk_A", "doc_id": "DFPDS_2026_01", "text": "Text A", "schedule_no": 1, "section": "S1", "breadcrumb": "B1", "page_no": 1, "bbox": [0,0,0,0], "sha256": "shaA"},
        {"chunk_id": "chunk_B", "doc_id": "DFPDS_2026_02", "text": "Text B", "schedule_no": 2, "section": "S2", "breadcrumb": "B2", "page_no": 1, "bbox": [0,0,0,0], "sha256": "shaB"},
        {"chunk_id": "chunk_C", "doc_id": "Navy_Regs_I", "text": "Text C", "schedule_no": 0, "section": "S3", "breadcrumb": "B3", "page_no": 1, "bbox": [0,0,0,0], "sha256": "shaC"},
    ]

    sparse_hits = [
        {"chunk_id": "chunk_B", "doc_id": "DFPDS_2026_02", "text": "Text B", "schedule_no": 2, "section": "S2", "breadcrumb": "B2", "page_no": 1, "bbox": [0,0,0,0], "sha256": "shaB"},
        {"chunk_id": "chunk_D", "doc_id": "DPM_2025_01", "text": "Text D", "schedule_no": 0, "section": "S4", "breadcrumb": "B4", "page_no": 1, "bbox": [0,0,0,0], "sha256": "shaD"},
        {"chunk_id": "chunk_A", "doc_id": "DFPDS_2026_01", "text": "Text A", "schedule_no": 1, "section": "S1", "breadcrumb": "B1", "page_no": 1, "bbox": [0,0,0,0], "sha256": "shaA"},
    ]

    # k = 60
    # chunk_B: dense rank 2, sparse rank 1 -> 1/62 + 1/61 = 0.016129 + 0.016393 = 0.032522
    # chunk_A: dense rank 1, sparse rank 3 -> 1/61 + 1/63 = 0.016393 + 0.015873 = 0.032266
    # chunk_D: dense unranked, sparse rank 2 -> 1/62 = 0.016129
    # chunk_C: dense rank 3, sparse unranked -> 1/63 = 0.015873

    fused = retriever_inst.reciprocal_rank_fusion(dense_hits, sparse_hits, k=60)

    assert len(fused) == 4
    assert fused[0].chunk_id == "chunk_B"
    assert fused[1].chunk_id == "chunk_A"
    assert fused[2].chunk_id == "chunk_D"
    assert fused[3].chunk_id == "chunk_C"

    assert fused[0].score > fused[1].score > fused[2].score > fused[3].score


def test_temporal_weighting_multiplier():
    """Verify 1.5x multiplier is applied to post-2024 documents (DFPDS-2026, DPM-2025)."""
    retriever_inst = HybridRetriever(embedder=None)

    chunk_modern = RetrievedChunk(
        chunk_id="chunk_modern",
        doc_id="DPM_2025_Chapter_02",
        schedule_no=0,
        section="OTE",
        breadcrumb="DPM-2025/CH-02",
        page_no=1,
        bbox=[0, 0, 0, 0],
        text="Modern procurement rules",
        sha256="sha1",
        score=0.020,
        publish_year=2025,
    )

    chunk_legacy = RetrievedChunk(
        chunk_id="chunk_legacy",
        doc_id="Navy_Regs_Part_I",
        schedule_no=0,
        section="Duties",
        breadcrumb="Navy_Regs/Part_I",
        page_no=1,
        bbox=[0, 0, 0, 0],
        text="Legacy statutory duties",
        sha256="sha2",
        score=0.025,
        publish_year=2020,
    )

    chunks = [chunk_legacy, chunk_modern]
    # Before weighting: chunk_legacy (0.025) > chunk_modern (0.020)
    assert chunks[0].chunk_id == "chunk_legacy"

    weighted = retriever_inst.apply_temporal_weighting(chunks, multiplier=1.5)
    # After weighting: chunk_modern (0.020 * 1.5 = 0.030) > chunk_legacy (0.025)
    assert weighted[0].chunk_id == "chunk_modern"
    assert pytest.approx(weighted[0].score, abs=1e-4) == 0.030
    assert pytest.approx(weighted[1].score, abs=1e-4) == 0.025


def test_live_corpus_hybrid_retrieval(retriever):
    """Verify end-to-end hybrid retrieval against the live indexed LanceDB and Tantivy stores."""
    query = "dry docking and ship repair in naval dockyards"
    results = retriever.retrieve(query, top_k=5)

    assert len(results) > 0
    assert len(results) <= 5

    for chunk in results:
        assert isinstance(chunk, RetrievedChunk)
        assert len(chunk.chunk_id) > 0
        assert len(chunk.text) > 0
        assert len(chunk.sha256) == 64
        assert chunk.score > 0

    # Top result should reference Schedule 1 (Dry Docking) or ship refits
    top_chunk = results[0]
    assert "dry docking" in top_chunk.text.lower() or "repair" in top_chunk.text.lower() or "schedule" in top_chunk.breadcrumb.lower()


def test_acronym_sparse_retrieval_fusion(retriever):
    """Verify exact military acronym query (PAC / STE / OTE) retrieves relevant clauses."""
    query = "Proprietary Article Certificate PAC delegation ceiling"
    results = retriever.retrieve(query, top_k=5)

    assert len(results) > 0
    matched_pac = any("pac" in c.text.lower() or "proprietary" in c.text.lower() for c in results)
    assert matched_pac, "Expected PAC or Proprietary terms in top hybrid retrieved chunks"


def test_empty_query_handling(retriever):
    """Verify empty query returns empty list gracefully without throwing exceptions."""
    results = retriever.retrieve("", top_k=10)
    assert results == []
