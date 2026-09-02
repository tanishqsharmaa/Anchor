import json
from pathlib import Path
import pytest

from anchor.config import settings
from anchor.retrieve.resolver import (
    ResolverResult,
    resolve_dfpds_delegation,
    resolve_dpm_threshold,
    normalize_cfa_tier,
    format_bluf_answer,
)


def test_cfa_tier_normalization():
    """Verify that naval CFA appointments and rank aliases normalize accurately to canonical Tier 1–6."""
    # Tier 1
    assert normalize_cfa_tier("CNS") == "Tier 1"
    assert normalize_cfa_tier("Chief of the Naval Staff") == "Tier 1"
    assert normalize_cfa_tier("Chief of Naval Staff") == "Tier 1"
    assert normalize_cfa_tier("Admiral") == "Tier 1"
    assert normalize_cfa_tier("Tier 1") == "Tier 1"
    assert normalize_cfa_tier("T1") == "Tier 1"
    assert normalize_cfa_tier("L1") == "Tier 1"

    # Tier 2
    assert normalize_cfa_tier("FOC-in-C") == "Tier 2"
    assert normalize_cfa_tier("FOCINC") == "Tier 2"
    assert normalize_cfa_tier("Flag Officer Commanding-in-Chief") == "Tier 2"
    assert normalize_cfa_tier("VCNS") == "Tier 2"
    assert normalize_cfa_tier("Vice Chief of the Naval Staff") == "Tier 2"
    assert normalize_cfa_tier("Vice Chief of Naval Staff") == "Tier 2"
    assert normalize_cfa_tier("C-in-C") == "Tier 2"
    assert normalize_cfa_tier("Tier 2") == "Tier 2"
    assert normalize_cfa_tier("L2") == "Tier 2"

    # Tier 3
    assert normalize_cfa_tier("Fleet Commander") == "Tier 3"
    assert normalize_cfa_tier("FOMA") == "Tier 3"
    assert normalize_cfa_tier("ASD") == "Tier 3"
    assert normalize_cfa_tier("ASD (Naval Dockyard)") == "Tier 3"
    assert normalize_cfa_tier("ASD Dockyard") == "Tier 3"
    assert normalize_cfa_tier("Admiral Superintendent Dockyard") == "Tier 3"
    assert normalize_cfa_tier("Flag Officer Commanding Western Fleet") == "Tier 3"
    assert normalize_cfa_tier("Tier 3") == "Tier 3"
    assert normalize_cfa_tier("L3") == "Tier 3"

    # Tier 4
    assert normalize_cfa_tier("CSO") == "Tier 4"
    assert normalize_cfa_tier("Chief Staff Officer") == "Tier 4"
    assert normalize_cfa_tier("NOIC") == "Tier 4"
    assert normalize_cfa_tier("Naval Officer-in-Charge") == "Tier 4"
    assert normalize_cfa_tier("Naval Officer in Charge") == "Tier 4"
    assert normalize_cfa_tier("Commodore") == "Tier 4"
    assert normalize_cfa_tier("Tier 4") == "Tier 4"
    assert normalize_cfa_tier("L4") == "Tier 4"

    # Tier 5
    assert normalize_cfa_tier("CO Capital Ship") == "Tier 5"
    assert normalize_cfa_tier("CO - Capital Ship") == "Tier 5"
    assert normalize_cfa_tier("Commanding Officer Capital Ship") == "Tier 5"
    assert normalize_cfa_tier("Carrier") == "Tier 5"
    assert normalize_cfa_tier("Destroyer") == "Tier 5"
    assert normalize_cfa_tier("Frigate") == "Tier 5"
    assert normalize_cfa_tier("Captain") == "Tier 5"
    assert normalize_cfa_tier("Tier 5") == "Tier 5"
    assert normalize_cfa_tier("L5") == "Tier 5"

    # Tier 6
    assert normalize_cfa_tier("CO Minor War Vessel") == "Tier 6"
    assert normalize_cfa_tier("CO - Minor War Vessel") == "Tier 6"
    assert normalize_cfa_tier("Commanding Officer Minor War Vessel") == "Tier 6"
    assert normalize_cfa_tier("Shore Base") == "Tier 6"
    assert normalize_cfa_tier("Corvette") == "Tier 6"
    assert normalize_cfa_tier("Patrol Vessel") == "Tier 6"
    assert normalize_cfa_tier("Tier 6") == "Tier 6"
    assert normalize_cfa_tier("L6") == "Tier 6"

    # Invalid / Out-of-bounds
    assert normalize_cfa_tier("General") is None
    assert normalize_cfa_tier("Invalid Designation") is None
    assert normalize_cfa_tier("") is None


def _load_ground_truth_dfpds():
    schema_path = settings.SCHEMAS_DIR / "dfpds_2026.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _generate_384_permutations():
    ground_truth = _load_ground_truth_dfpds()
    cases = []
    for sch in ground_truth:
        s_no = sch["schedule_no"]
        s_name = sch["schedule_name"]
        ref = sch["reference"]
        for t in sch["tiers"]:
            tier_code = t["tier"]
            tier_name = t["tier_name"]
            # Case 1: with_ifa = True
            cases.append((s_no, s_name, ref, tier_code, tier_name, True, t["with_ifa"], t["pac_limit"], t.get("notes")))
            # Case 2: with_ifa = False
            cases.append((s_no, s_name, ref, tier_code, tier_name, False, t["without_ifa"], t["pac_limit"], t.get("notes")))
    return cases


@pytest.mark.parametrize(
    "schedule_no, expected_name, expected_ref, tier, expected_tier_name, with_ifa, expected_amount, expected_pac, expected_notes",
    _generate_384_permutations(),
)
def test_dfpds_resolver_384_permutations(
    schedule_no,
    expected_name,
    expected_ref,
    tier,
    expected_tier_name,
    with_ifa,
    expected_amount,
    expected_pac,
    expected_notes,
):
    """Exhaustively verify 100% exact numerical match across all 384 statutory permutations (32 schedules x 6 tiers x 2 IFA states)."""
    result = resolve_dfpds_delegation(
        schedule_no=schedule_no,
        tier=tier,
        ifa_concurrence=with_ifa,
        is_pac=False,
    )

    assert result is not None, f"Failed to resolve schedule {schedule_no}, tier {tier}"
    assert result.schedule_no == schedule_no
    assert result.schedule_name == expected_name
    assert result.reference == expected_ref
    assert result.tier == tier
    assert result.tier_name == expected_tier_name
    assert result.with_ifa == with_ifa
    assert result.sanction_limit == pytest.approx(expected_amount, 0.0001)
    assert result.pac_limit == pytest.approx(expected_pac, 0.0001)

    # Verify BLUF answer string
    ifa_str = "with IFA concurrence" if with_ifa else "without IFA concurrence"
    assert f"Under DFPDS-2026 {expected_name} ({expected_ref})" in result.formatted_answer
    assert f"a {expected_tier_name} ({tier}) may sanction up to ₹{expected_amount:.2f} Crore {ifa_str}." in result.formatted_answer


def test_dfpds_pac_delegation_limits():
    """Verify PAC delegation limits and statutory notes in formatted BLUF response."""
    result = resolve_dfpds_delegation(
        schedule_no=7,
        tier="Fleet Commander",
        ifa_concurrence=True,
        is_pac=True,
    )
    assert result is not None
    assert result.is_pac is True
    assert result.pac_limit == 10.5  # 50% of 21.0 Cr for Schedule 7 Tier 3
    assert "Under PAC guidelines (DPM-2025 Ch 3)" in result.formatted_answer
    assert "₹10.50 Crore" in result.formatted_answer


def test_dpm_threshold_lookups():
    """Verify DPM-2025 statutory threshold queries."""
    # OTE
    ote = resolve_dpm_threshold("OTE")
    assert ote["threshold_inr_lakhs"] == 25.0
    assert ote["threshold_inr_cr"] == 0.25
    assert ote["mode"] == "Open Tender Enquiry"
    assert "DPM-2025/DMA/CH-02" in ote["reference"]

    # LTE
    lte = resolve_dpm_threshold("LTE")
    assert lte["threshold_inr_lakhs"] == 25.0
    assert lte["mode"] == "Limited Tender Enquiry"

    # GTE
    gte = resolve_dpm_threshold("GTE")
    assert gte["threshold_inr_cr"] == 200.0
    assert gte["mode"] == "Global Tender Enquiry"

    # PBG
    pbg = resolve_dpm_threshold("PBG")
    assert pbg["pbg_min_percent"] == 3.0
    assert pbg["pbg_max_percent"] == 5.0

    # LD
    ld = resolve_dpm_threshold("LD")
    assert ld["ld_rate_per_week_percent"] == 0.5
    assert ld["ld_max_ceiling_percent"] == 10.0

    # Warranty
    war = resolve_dpm_threshold("WARRANTY")
    assert war["warranty_months"] == 24

    # Unknown
    unknown = resolve_dpm_threshold("NON_EXISTENT")
    assert unknown == {}


def test_out_of_range_and_edge_cases():
    """Verify boundary condition handling and graceful refusal (None)."""
    # Schedule out of bounds
    assert resolve_dfpds_delegation(schedule_no=0, tier="Tier 1") is None
    assert resolve_dfpds_delegation(schedule_no=33, tier="Tier 1") is None
    assert resolve_dfpds_delegation(schedule_no=99, tier="Tier 1") is None
    assert resolve_dfpds_delegation(schedule_no=-5, tier="Tier 1") is None

    # Invalid tier
    assert resolve_dfpds_delegation(schedule_no=1, tier="General") is None
    assert resolve_dfpds_delegation(schedule_no=1, tier="NonExistentTier") is None
    assert resolve_dfpds_delegation(schedule_no=1, tier="") is None


def test_bluf_formatting_syntax():
    """Verify custom BLUF formatting generation."""
    answer = format_bluf_answer(
        schedule_name="Schedule 07: Procurement of Tactical Remotely Piloted Aircraft and Autonomous Systems",
        reference="DFPDS-2026/NAVY/SCH-07",
        tier_name="Fleet Commander / ASD (Naval Dockyard) / FOMA",
        tier="Tier 3",
        amount_cr=18.0,
        with_ifa=True,
        is_pac=False,
        pac_limit=9.0,
        notes="Annexure A conditions apply.",
    )
    assert answer.startswith("Under DFPDS-2026 Schedule 07: Procurement of Tactical Remotely Piloted Aircraft and Autonomous Systems (DFPDS-2026/NAVY/SCH-07)")
    assert "a Fleet Commander / ASD (Naval Dockyard) / FOMA (Tier 3) may sanction up to ₹18.00 Crore with IFA concurrence." in answer
    assert "Statutory Note: Annexure A conditions apply." in answer
