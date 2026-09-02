"""
test_chunker.py — Unit Tests for Semantic Token Chunking and Cryptographic Anchors
"""

import hashlib
from anchor.config import settings
from anchor.ingest.pdf_parser import parse_pdf_layout
from anchor.ingest.clause_parser import parse_regulatory_hierarchy
from anchor.ingest.chunker import (
    chunk_regulatory_hierarchy,
    RegulatoryChunk,
)


def test_chunker_on_dfpds_schedule():
    """Assert chunker generates bounded chunks with valid SHA-256 hashes and breadcrumbs."""
    pdf_path = settings.PDFS_DIR / "DFPDS_2026_Schedule_07.pdf"
    layout = parse_pdf_layout(pdf_path)
    hierarchy = parse_regulatory_hierarchy(layout)
    chunks = chunk_regulatory_hierarchy(hierarchy)

    assert len(chunks) > 0
    for chunk in chunks:
        assert isinstance(chunk, RegulatoryChunk)
        assert chunk.doc_id == "DFPDS_2026_Schedule_07"
        assert chunk.schedule_no == 7
        assert len(chunk.text) > 0
        assert chunk.token_count > 0

        # Verify cryptographic SHA-256 hash match
        expected_sha = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
        assert chunk.sha256 == expected_sha

        # Verify bounding box validity
        assert len(chunk.bbox) == 4
        x0, y0, x1, y1 = chunk.bbox
        assert x0 <= x1
        assert y0 <= y1

        # Verify breadcrumb format
        assert "DFPDS-2026" in chunk.breadcrumb


def test_chunker_on_dpm_chapter():
    """Assert chunker correctly processes DPM chapter PDFs."""
    pdf_path = settings.PDFS_DIR / "DPM_2025_Chapter_03.pdf"
    layout = parse_pdf_layout(pdf_path)
    hierarchy = parse_regulatory_hierarchy(layout)
    chunks = chunk_regulatory_hierarchy(hierarchy)

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.doc_id == "DPM_2025_Chapter_03"
        assert "DPM-2025" in chunk.breadcrumb
        assert len(chunk.sha256) == 64


def test_chunker_empty_hierarchy():
    """Assert chunker returns empty list for empty hierarchy."""
    from anchor.ingest.clause_parser import ParsedHierarchy
    empty_hier = ParsedHierarchy(doc_id="empty_doc")
    chunks = chunk_regulatory_hierarchy(empty_hier)
    assert chunks == []
