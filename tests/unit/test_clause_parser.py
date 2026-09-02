"""
test_clause_parser.py — Unit Tests for Hierarchical Clause Parsing and Breadcrumb Metadata
"""

from anchor.config import settings
from anchor.ingest.pdf_parser import parse_pdf_layout
from anchor.ingest.clause_parser import (
    parse_regulatory_hierarchy,
    ParsedHierarchy,
    ClauseNode,
)


def test_clause_parser_dfpds():
    """Assert hierarchy decomposition generates canonical breadcrumbs for DFPDS schedules."""
    pdf_path = settings.PDFS_DIR / "DFPDS_2026_Schedule_07.pdf"
    layout = parse_pdf_layout(pdf_path)
    hierarchy = parse_regulatory_hierarchy(layout)

    assert isinstance(hierarchy, ParsedHierarchy)
    assert hierarchy.doc_id == "DFPDS_2026_Schedule_07"
    assert len(hierarchy.flat_clauses) > 0

    breadcrumbs = [c.breadcrumb for c in hierarchy.flat_clauses]
    assert any("DFPDS-2026/Schedule_07" in b for b in breadcrumbs)
    for clause in hierarchy.flat_clauses:
        assert isinstance(clause, ClauseNode)
        assert clause.schedule_no == 7
        assert clause.page_no >= 1
        assert len(clause.text) > 0


def test_clause_parser_dpm():
    """Assert hierarchy decomposition generates canonical breadcrumbs for DPM chapters."""
    pdf_path = settings.PDFS_DIR / "DPM_2025_Chapter_03.pdf"
    layout = parse_pdf_layout(pdf_path)
    hierarchy = parse_regulatory_hierarchy(layout)

    assert hierarchy.doc_id == "DPM_2025_Chapter_03"
    breadcrumbs = [c.breadcrumb for c in hierarchy.flat_clauses]
    assert any("DPM-2025/Chapter_03" in b for b in breadcrumbs)


def test_clause_parser_navy_regs():
    """Assert hierarchy decomposition generates canonical breadcrumbs for Navy Regulations."""
    pdf_path = settings.PDFS_DIR / "NAVY_REGS_Part_01.pdf"
    layout = parse_pdf_layout(pdf_path)
    hierarchy = parse_regulatory_hierarchy(layout)

    assert hierarchy.doc_id == "NAVY_REGS_Part_01"
    breadcrumbs = [c.breadcrumb for c in hierarchy.flat_clauses]
    assert any("Navy_Regulations/Part" in b for b in breadcrumbs)
