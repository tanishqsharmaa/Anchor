"""
test_pdf_parser.py — Unit Tests for PyMuPDF Layout Parsing and Coordinate Extraction
"""

from pathlib import Path
import pytest
from anchor.config import settings
from anchor.ingest.pdf_parser import (
    parse_pdf_layout,
    DocumentLayout,
    PageLayout,
    TextBlock,
    TextSpan,
)


def test_pdf_parser_on_dfpds_schedule():
    """Assert PDF parser extracts layout, text spans, and bounding boxes from DFPDS schedule PDF."""
    pdf_path = settings.PDFS_DIR / "DFPDS_2026_Schedule_07.pdf"
    assert pdf_path.exists(), f"Test PDF does not exist: {pdf_path}"

    layout = parse_pdf_layout(pdf_path)
    assert isinstance(layout, DocumentLayout)
    assert layout.doc_id == "DFPDS_2026_Schedule_07"
    assert layout.total_pages >= 1

    page = layout.pages[0]
    assert isinstance(page, PageLayout)
    assert page.page_no == 1
    assert page.width > 0
    assert page.height > 0
    assert len(page.blocks) > 0

    # Verify bounding boxes and text content
    found_heading = False
    for block in page.blocks:
        assert isinstance(block, TextBlock)
        x0, y0, x1, y1 = block.bbox
        assert 0 <= x0 <= x1 <= page.width
        assert 0 <= y0 <= y1 <= page.height
        if block.is_heading:
            found_heading = True

    assert found_heading, "Expected at least one heading block in schedule layout"
    full_text = layout.full_text
    assert "SCHEDULE" in full_text.upper()


def test_pdf_parser_on_dpm_chapter():
    """Assert PDF parser extracts layout from DPM chapter PDF."""
    pdf_path = settings.PDFS_DIR / "DPM_2025_Chapter_01.pdf"
    assert pdf_path.exists(), f"Test PDF does not exist: {pdf_path}"

    layout = parse_pdf_layout(pdf_path)
    assert layout.doc_id == "DPM_2025_Chapter_01"
    assert len(layout.pages) >= 1
    assert len(layout.full_text) > 50


def test_pdf_parser_on_navy_regs():
    """Assert PDF parser extracts layout from Navy Regulations PDF."""
    pdf_path = settings.PDFS_DIR / "NAVY_REGS_Part_01.pdf"
    assert pdf_path.exists(), f"Test PDF does not exist: {pdf_path}"

    layout = parse_pdf_layout(pdf_path)
    assert layout.doc_id == "NAVY_REGS_Part_01"
    assert len(layout.pages) >= 1
    assert len(layout.full_text) > 50


def test_pdf_parser_missing_file():
    """Assert FileNotFoundError is raised for non-existent PDF."""
    with pytest.raises(FileNotFoundError):
        parse_pdf_layout(Path("non_existent_document.pdf"))
