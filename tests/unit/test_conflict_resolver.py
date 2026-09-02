"""
test_conflict_resolver.py — Unit Tests for Cross-Regulatory Conflict Resolver
"""

import pytest
from anchor.retrieve.conflict_resolver import ConflictResolver
from anchor.retrieve.hybrid import RetrievedChunk


@pytest.fixture(scope="module")
def resolver():
    """Module-level fixture providing ConflictResolver."""
    return ConflictResolver()


def test_dfpds_overrides_dpm_on_financial_delegation(resolver):
    """Verify DFPDS-2026 takes statutory precedence over DPM-2025 on financial delegation."""
    dfpds_chunk = RetrievedChunk(
        chunk_id="dfpds_sch07_tier3",
        doc_id="DFPDS_2026_Schedule_07",
        schedule_no=7,
        section="Tier 3 Fleet Commander",
        breadcrumb="DFPDS-2026/Schedule_07/Tier_3",
        page_no=1,
        bbox=[0, 0, 0, 0],
        text="Under DFPDS-2026 Schedule 7, Fleet Commander may sanction up to ₹18.00 Crore with IFA concurrence.",
        sha256="sha_dfpds",
        score=0.030,
        publish_year=2026,
    )

    dpm_chunk = RetrievedChunk(
        chunk_id="dpm_ch02_general",
        doc_id="DPM_2025_Chapter_02",
        schedule_no=0,
        section="General Financial Powers",
        breadcrumb="DPM-2025/Chapter_02",
        page_no=5,
        bbox=[0, 0, 0, 0],
        text="General delegation limits for Command level authorities shall not exceed ₹10.00 Crore without MoD approval.",
        sha256="sha_dpm",
        score=0.035,  # Artificially higher initial score to test re-ordering
        publish_year=2025,
    )

    resolved = resolver.resolve_conflicts([dpm_chunk, dfpds_chunk])

    # DFPDS must rank first due to statutory financial supremacy
    assert resolved[0].chunk_id == "dfpds_sch07_tier3"
    assert resolved[0].precedence_note is not None
    assert "DFPDS-2026" in resolved[0].precedence_note

    # DPM chunk must be flagged as conflicting / overridden
    assert resolved[1].chunk_id == "dpm_ch02_general"
    assert resolved[1].conflict_flag is True


def test_dpm_overrides_navy_regs_on_procurement_procedures(resolver):
    """Verify DPM-2025 takes precedence over Navy Regulations on procurement procedures and tendering."""
    dpm_chunk = RetrievedChunk(
        chunk_id="dpm_ch02_ote",
        doc_id="DPM_2025_Chapter_02",
        schedule_no=0,
        section="Tendering Modes",
        breadcrumb="DPM-2025/Chapter_02/OTE",
        page_no=2,
        bbox=[0, 0, 0, 0],
        text="Open Tender Enquiry (OTE) is mandatory for all procurement values above INR 25 Lakhs.",
        sha256="sha_dpm_ote",
        score=0.025,
        publish_year=2025,
    )

    navy_regs_chunk = RetrievedChunk(
        chunk_id="navy_regs_part2_stores",
        doc_id="Navy_Regs_Part_II",
        schedule_no=0,
        section="Local Purchase Procedures",
        breadcrumb="Navy_Regs/Part_II/Stores",
        page_no=12,
        bbox=[0, 0, 0, 0],
        text="Commanding Officers may resort to direct market quotation for stores up to INR 50 Lakhs.",
        sha256="sha_navy_regs",
        score=0.028,
        publish_year=2020,
    )

    resolved = resolver.resolve_conflicts([navy_regs_chunk, dpm_chunk])

    assert resolved[0].chunk_id == "dpm_ch02_ote"
    assert resolved[1].chunk_id == "navy_regs_part2_stores"
    assert resolved[1].conflict_flag is True


def test_non_conflicting_chunks_preserved(resolver):
    """Verify independent non-conflicting chunks retain their natural rank and status."""
    chunk1 = RetrievedChunk(
        chunk_id="dfpds_sch01",
        doc_id="DFPDS_2026_Schedule_01",
        schedule_no=1,
        section="Dry Docking",
        breadcrumb="DFPDS-2026/Schedule_01",
        page_no=1,
        bbox=[0, 0, 0, 0],
        text="Dry docking sanctions for naval ships in commercial docks.",
        sha256="sha1",
        score=0.040,
        publish_year=2026,
    )

    chunk2 = RetrievedChunk(
        chunk_id="dfpds_sch02",
        doc_id="DFPDS_2026_Schedule_02",
        schedule_no=2,
        section="Ship Repairs",
        breadcrumb="DFPDS-2026/Schedule_02",
        page_no=1,
        bbox=[0, 0, 0, 0],
        text="Operational refits and emergent voyage repairs.",
        sha256="sha2",
        score=0.030,
        publish_year=2026,
    )

    resolved = resolver.resolve_conflicts([chunk1, chunk2])

    assert len(resolved) == 2
    assert resolved[0].chunk_id == "dfpds_sch01"
    assert resolved[1].chunk_id == "dfpds_sch02"
    assert resolved[0].conflict_flag is False
    assert resolved[1].conflict_flag is False
