import time
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Optional

from anchor.config import settings
from anchor.stores.sqlite_store import get_sqlite_connection


@dataclass
class ResolverResult:
    """Deterministic resolution result for a regulatory financial query."""

    schedule_no: int
    schedule_name: str
    reference: str
    gazette_notification: Optional[str]
    effective_date: Optional[str]
    tier: str
    tier_name: str
    sanction_limit: float  # In INR Crore
    with_ifa: bool
    is_pac: bool
    pac_limit: float
    formatted_answer: str
    notes: Optional[str] = None


@dataclass
class ComparisonResult:
    """Deterministic multi-schedule comparative resolution result."""

    schedules: list[ResolverResult]
    tier: str
    with_ifa: bool
    is_pac: bool
    formatted_answer: str


# In-memory query result cache with 300s TTL (ENH-003)
_RESOLVER_CACHE: dict[tuple[int, str, bool, bool, Optional[str]], tuple[float, Optional[ResolverResult]]] = {}
_CACHE_TTL_SECONDS: float = 300.0


def clear_resolver_cache() -> None:
    """Clear in-memory structured query resolver cache."""
    _RESOLVER_CACHE.clear()


CFA_TIER_MAPPINGS: dict[str, str] = {
    # Tier 1 - Chief of the Naval Staff
    "cns": "Tier 1",
    "chief of the naval staff": "Tier 1",
    "chief of naval staff": "Tier 1",
    "admiral": "Tier 1",
    "tier 1": "Tier 1",
    "tier-1": "Tier 1",
    "tier1": "Tier 1",
    "t1": "Tier 1",
    "l1": "Tier 1",
    # Tier 2 - Flag Officer Commanding-in-Chief / VCNS
    "foc-in-c": "Tier 2",
    "focinc": "Tier 2",
    "flag officer commanding-in-chief": "Tier 2",
    "flag officer commanding in chief": "Tier 2",
    "foc-in-c (command)": "Tier 2",
    "vcns": "Tier 2",
    "vice chief of the naval staff": "Tier 2",
    "vice chief of naval staff": "Tier 2",
    "c-in-c": "Tier 2",
    "tier 2": "Tier 2",
    "tier-2": "Tier 2",
    "tier2": "Tier 2",
    "t2": "Tier 2",
    "l2": "Tier 2",
    # Tier 3 - Fleet Commander / ASD (Naval Dockyard) / FOMA
    "fleet commander": "Tier 3",
    "flag officer commanding western fleet": "Tier 3",
    "flag officer commanding eastern fleet": "Tier 3",
    "focwf": "Tier 3",
    "focef": "Tier 3",
    "foma": "Tier 3",
    "flag officer commanding maharashtra naval area": "Tier 3",
    "asd": "Tier 3",
    "asd (naval dockyard)": "Tier 3",
    "asd dockyard": "Tier 3",
    "admiral superintendent dockyard": "Tier 3",
    "admiral superintendent naval dockyard": "Tier 3",
    "tier 3": "Tier 3",
    "tier-3": "Tier 3",
    "tier3": "Tier 3",
    "t3": "Tier 3",
    "l3": "Tier 3",
    # Tier 4 - Chief Staff Officer / NOIC
    "cso": "Tier 4",
    "chief staff officer": "Tier 4",
    "chief staff officer (operations)": "Tier 4",
    "cso (ops)": "Tier 4",
    "noic": "Tier 4",
    "naval officer-in-charge": "Tier 4",
    "naval officer in charge": "Tier 4",
    "commodore": "Tier 4",
    "tier 4": "Tier 4",
    "tier-4": "Tier 4",
    "tier4": "Tier 4",
    "t4": "Tier 4",
    "l4": "Tier 4",
    # Tier 5 - Commanding Officer (CO) — Capital Ship
    "co capital ship": "Tier 5",
    "co - capital ship": "Tier 5",
    "commanding officer capital ship": "Tier 5",
    "commanding officer (co) — capital ship": "Tier 5",
    "commanding officer (co) - capital ship": "Tier 5",
    "carrier": "Tier 5",
    "destroyer": "Tier 5",
    "frigate": "Tier 5",
    "co frigate": "Tier 5",
    "co destroyer": "Tier 5",
    "co carrier": "Tier 5",
    "captain": "Tier 5",
    "captain co": "Tier 5",
    "tier 5": "Tier 5",
    "tier-5": "Tier 5",
    "tier5": "Tier 5",
    "t5": "Tier 5",
    "l5": "Tier 5",
    # Tier 6 - Commanding Officer (CO) — Minor War Vessel / Shore Base
    "co minor war vessel": "Tier 6",
    "co - minor war vessel": "Tier 6",
    "commanding officer minor war vessel": "Tier 6",
    "commanding officer (co) — minor war vessel / shore base": "Tier 6",
    "commanding officer (co) - minor war vessel / shore base": "Tier 6",
    "shore base": "Tier 6",
    "corvette": "Tier 6",
    "co corvette": "Tier 6",
    "patrol vessel": "Tier 6",
    "co patrol vessel": "Tier 6",
    "tier 6": "Tier 6",
    "tier-6": "Tier 6",
    "tier6": "Tier 6",
    "t6": "Tier 6",
    "l6": "Tier 6",
}


def normalize_cfa_tier(designation: Optional[str]) -> Optional[str]:
    """Normalize naval officer designations, ranks, or tier strings to canonical Tier 1..6.

    Returns None if the designation cannot be mapped or contains hostile/injection characters.
    """
    if not designation or not isinstance(designation, str):
        return None

    cleaned = designation.strip().lower()
    if not cleaned or len(cleaned) > 200:
        return None

    # Rejection of SQL/script injection markers
    if any(ch in cleaned for ch in ["'", '"', ";", "/*", "*/", "<", ">", "{", "}", "$"]):
        return None

    # 1. Exact match in lookup table
    if cleaned in CFA_TIER_MAPPINGS:
        return CFA_TIER_MAPPINGS[cleaned]

    # 2. Match standard clean tier formats (e.g. "tier 1", "tier-1", "tier1", "l1", "t1")
    tier_match = re.fullmatch(r"(tier|l|t)[\s\-_]?([1-6])", cleaned)
    if tier_match:
        return f"Tier {tier_match.group(2)}"

    # 3. Substring matching for distinctive designations
    if "chief of the naval staff" in cleaned or "chief of naval staff" in cleaned or cleaned == "cns":
        return "Tier 1"
    if "foc-in-c" in cleaned or "focinc" in cleaned or "vice chief" in cleaned or "vcns" in cleaned:
        return "Tier 2"
    if "fleet commander" in cleaned or "naval dockyard" in cleaned or "foma" in cleaned or "asd" in cleaned:
        return "Tier 3"
    if "chief staff officer" in cleaned or "cso" in cleaned or "noic" in cleaned or "officer-in-charge" in cleaned:
        return "Tier 4"
    if "capital ship" in cleaned or "carrier" in cleaned or "destroyer" in cleaned or "frigate" in cleaned:
        return "Tier 5"
    if "minor war vessel" in cleaned or "shore base" in cleaned or "corvette" in cleaned or "patrol vessel" in cleaned:
        return "Tier 6"

    return None


def format_bluf_answer(
    schedule_name: str,
    reference: str,
    tier_name: str,
    tier: str,
    amount_cr: float,
    with_ifa: bool,
    is_pac: bool = False,
    pac_limit: float = 0.0,
    notes: Optional[str] = None,
) -> str:
    """Format canonical regulatory answer following Indian Naval Staff BLUF-v2026 standards."""
    ifa_clause = "with IFA concurrence" if with_ifa else "without IFA concurrence"
    bluf_body = (
        f"Under DFPDS-2026 {schedule_name} ({reference}), "
        f"a {tier_name} ({tier}) may sanction up to ₹{amount_cr:.2f} Crore {ifa_clause}."
    )

    parts = [bluf_body]

    if is_pac:
        parts.append(
            f"Under PAC guidelines (DPM-2025 Ch 3), the ceiling is ₹{pac_limit:.2f} Crore (50% of delegation)."
        )

    if notes and notes.strip():
        parts.append(f"Statutory Note: {notes.strip()}")

    return "\n".join(parts)


def resolve_dfpds_delegation(
    schedule_no: int,
    tier: str,
    ifa_concurrence: bool = True,
    is_pac: bool = False,
    db_path: Optional[Path] = None,
) -> Optional[ResolverResult]:
    """Execute parameterized SQL lookup for DFPDS-2026 financial delegation with in-memory caching.

    Bypasses LLM inference completely for 100% precision. Returns None if out-of-range or unmapped.
    """
    if type(schedule_no) is not int or schedule_no < 1 or schedule_no > 32:
        return None

    canonical_tier = normalize_cfa_tier(tier)
    if not canonical_tier:
        return None

    cache_key = (schedule_no, canonical_tier, ifa_concurrence, is_pac, str(db_path) if db_path else None)
    now = time.time()
    cached = _RESOLVER_CACHE.get(cache_key)
    if cached is not None:
        cached_time, cached_res = cached
        if now - cached_time < _CACHE_TTL_SECONDS:
            return cached_res

    conn = get_sqlite_connection(db_path)
    cursor = conn.execute(
        """
        SELECT schedule_no, schedule_name, reference, gazette_notification,
               effective_date, tier, tier_name, with_ifa, without_ifa, pac_limit, notes
        FROM dfpds_2026
        WHERE schedule_no = ? AND tier = ?;
        """,
        (schedule_no, canonical_tier),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        _RESOLVER_CACHE[cache_key] = (now, None)
        return None

    with_ifa_val = float(row["with_ifa"])
    without_ifa_val = float(row["without_ifa"])
    pac_limit_val = float(row["pac_limit"])
    sanction_val = with_ifa_val if ifa_concurrence else without_ifa_val

    formatted_text = format_bluf_answer(
        schedule_name=row["schedule_name"],
        reference=row["reference"],
        tier_name=row["tier_name"],
        tier=row["tier"],
        amount_cr=sanction_val,
        with_ifa=ifa_concurrence,
        is_pac=is_pac,
        pac_limit=pac_limit_val,
        notes=row["notes"],
    )

    result = ResolverResult(
        schedule_no=row["schedule_no"],
        schedule_name=row["schedule_name"],
        reference=row["reference"],
        gazette_notification=row["gazette_notification"],
        effective_date=row["effective_date"],
        tier=row["tier"],
        tier_name=row["tier_name"],
        sanction_limit=sanction_val,
        with_ifa=ifa_concurrence,
        is_pac=is_pac,
        pac_limit=pac_limit_val,
        formatted_answer=formatted_text,
        notes=row["notes"],
    )

    _RESOLVER_CACHE[cache_key] = (now, result)
    return result


def resolve_dfpds_comparison(
    schedule_nos: list[int],
    tier: str,
    ifa_concurrence: bool = True,
    is_pac: bool = False,
    db_path: Optional[Path] = None,
) -> Optional[ComparisonResult]:
    """
    Execute structured comparative lookups across multiple DFPDS schedules for a CFA tier (ENH-002).
    Generates side-by-side BLUF comparison text.
    """
    if not schedule_nos:
        return None

    canonical_tier = normalize_cfa_tier(tier)
    if not canonical_tier:
        return None

    results: list[ResolverResult] = []
    for s_no in schedule_nos:
        res = resolve_dfpds_delegation(
            schedule_no=s_no,
            tier=canonical_tier,
            ifa_concurrence=ifa_concurrence,
            is_pac=is_pac,
            db_path=db_path,
        )
        if res is not None:
            results.append(res)

    if not results:
        return None

    ifa_clause = "with IFA concurrence" if ifa_concurrence else "without IFA concurrence"
    first_tier_name = results[0].tier_name

    lines = [
        f"Under DFPDS-2026, comparative financial delegation for {first_tier_name} ({canonical_tier}) {ifa_clause}:",
    ]
    for r in results:
        pac_note = f" (PAC ceiling: ₹{r.pac_limit:.2f} Cr)" if is_pac else ""
        lines.append(
            f"• {r.schedule_name} ({r.reference}): ₹{r.sanction_limit:.2f} Crore{pac_note}"
        )

    formatted_answer = "\n".join(lines)
    return ComparisonResult(
        schedules=results,
        tier=canonical_tier,
        with_ifa=ifa_concurrence,
        is_pac=is_pac,
        formatted_answer=formatted_answer,
    )


def resolve_dpm_threshold(
    query_type: str,
    value_inr_cr: Optional[float] = None,
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Retrieve DPM-2025 procurement thresholds and statutory tendering rules."""
    if not query_type or not isinstance(query_type, str):
        return {}

    qt = query_type.strip().upper()

    dpm_rules: dict[str, dict[str, Any]] = {
        "OTE": {
            "mode": "Open Tender Enquiry",
            "threshold_inr_lakhs": 25.0,
            "threshold_inr_cr": 0.25,
            "mandatory_above": True,
            "reference": "DPM-2025/DMA/CH-02",
            "portals": ["CPPP", "GeM"],
            "description": "OTE is mandatory default mode for all goods and services valued above INR 25 Lakhs.",
        },
        "LTE": {
            "mode": "Limited Tender Enquiry",
            "threshold_inr_lakhs": 25.0,
            "threshold_inr_cr": 0.25,
            "max_limit": True,
            "min_registered_suppliers": 3,
            "reference": "DPM-2025/DMA/CH-02",
            "description": "LTE may be adopted for values up to INR 25 Lakhs where registered suppliers exceed three.",
        },
        "GTE": {
            "mode": "Global Tender Enquiry",
            "threshold_inr_cr": 200.0,
            "prohibited_under": True,
            "reference": "DPM-2025/DMA/CH-02",
            "mandate": "Make in India",
            "description": "GTE is barred for procurements valued under INR 200 Crore under Make in India mandate.",
        },
        "PBG": {
            "term": "Performance Bank Guarantee",
            "pbg_min_percent": 3.0,
            "pbg_max_percent": 5.0,
            "validity_days_post_warranty": 60,
            "reference": "DPM-2025/DMA/CH-04",
            "description": "Successful bidders shall furnish PBG of 3% to 5% of contract value, valid for 60 days beyond warranty.",
        },
        "LD": {
            "term": "Liquidated Damages",
            "ld_rate_per_week_percent": 0.5,
            "ld_max_ceiling_percent": 10.0,
            "reference": "DPM-2025/DMA/CH-04",
            "description": "LD shall be levied at 0.5% per week or part thereof, up to a maximum ceiling of 10%.",
        },
        "PAC": {
            "term": "Proprietary Article Certificate",
            "delegation_ceiling_percent": 50.0,
            "reference": "DPM-2025/DMA/CH-03",
            "description": "PAC procurement requires technical Directorate certification; CFA delegation ceiling is capped at 50%.",
        },
        "WARRANTY": {
            "term": "Warranty Support",
            "warranty_months": 24,
            "reference": "DPM-2025/DMA/CH-04",
            "description": "All defence stores shall carry a minimum 24-month comprehensive OEM warranty from final naval acceptance.",
        },
    }

    return dpm_rules.get(qt, {})
