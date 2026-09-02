"""
clause_parser.py — Hierarchical Regulatory Clause Decomposition and Canonical Breadcrumbs
"""

from dataclasses import dataclass, field
import re
from typing import Optional
from anchor.ingest.pdf_parser import DocumentLayout, TextBlock, TextSpan


@dataclass
class ClauseNode:
    """Represents a decomposed node in the regulatory hierarchy."""
    breadcrumb: str
    doc_id: str
    schedule_no: int
    title: str
    level: str  # document, schedule, chapter, clause, tier, section
    text: str
    page_no: int
    bbox: tuple[float, float, float, float]
    spans: list[TextSpan] = field(default_factory=list)
    children: list["ClauseNode"] = field(default_factory=list)


@dataclass
class ParsedHierarchy:
    """Represents the complete decomposed hierarchy of a regulatory document."""
    doc_id: str
    root_nodes: list[ClauseNode] = field(default_factory=list)
    flat_clauses: list[ClauseNode] = field(default_factory=list)


# Regulatory Regex Patterns
RE_DFPDS_SCH = re.compile(r"SCHEDULE\s*[-–:]*\s*0*(\d+)", re.IGNORECASE)
RE_DPM_CHAP = re.compile(r"CHAPTER\s*[-–:]*\s*0*(\d+)", re.IGNORECASE)
RE_NAVY_PART = re.compile(r"PART\s*[-–:]*\s*([IVX]+|\d+)", re.IGNORECASE)
RE_CLAUSE = re.compile(r"(?:CLAUSE|SECTION|PARA|RULE)\s*[-–:]*\s*(\d+(?:\.\d+)*)", re.IGNORECASE)
RE_TIER = re.compile(r"(?:TIER|LEVEL|L)\s*0*(\d+)\s*(?:\(([^)]+)\))?", re.IGNORECASE)


def _slugify(text: str, max_len: int = 30) -> str:
    """Convert title string into a clean breadcrumb slug."""
    clean = re.sub(r"[^\w\s-]", "", text).strip()
    slug = re.sub(r"[-\s]+", "_", clean)
    return slug[:max_len].strip("_")


def parse_regulatory_hierarchy(layout: DocumentLayout) -> ParsedHierarchy:
    """
    Decompose a DocumentLayout into a hierarchical tree of regulatory clauses
    with canonical breadcrumb metadata.

    Args:
        layout: DocumentLayout parsed from PDF.

    Returns:
        ParsedHierarchy with root tree and flattened clause blocks.
    """
    doc_id = layout.doc_id
    flat_clauses: list[ClauseNode] = []
    root_nodes: list[ClauseNode] = []

    # Detect document category
    is_dfpds = "DFPDS" in doc_id.upper()
    is_dpm = "DPM" in doc_id.upper()
    is_navy_regs = "NAVY" in doc_id.upper() or "REGS" in doc_id.upper()

    schedule_no = 0
    if is_dfpds:
        sch_match = RE_DFPDS_SCH.search(doc_id) or RE_DFPDS_SCH.search(layout.full_text[:500])
        if sch_match:
            schedule_no = int(sch_match.group(1))

    # Base document breadcrumb prefix
    if is_dfpds:
        base_prefix = f"DFPDS-2026/Schedule_{schedule_no:02d}" if schedule_no > 0 else "DFPDS-2026"
    elif is_dpm:
        chap_match = RE_DPM_CHAP.search(doc_id) or RE_DPM_CHAP.search(layout.full_text[:500])
        chap_no = int(chap_match.group(1)) if chap_match else 1
        base_prefix = f"DPM-2025/Chapter_{chap_no:02d}"
    elif is_navy_regs:
        part_match = RE_NAVY_PART.search(doc_id) or RE_NAVY_PART.search(layout.full_text[:500])
        part_str = part_match.group(1) if part_match else "I"
        base_prefix = f"Navy_Regulations/Part_{part_str}"
    else:
        base_prefix = doc_id

    current_section = "General"
    current_tier: Optional[str] = None

    for page in layout.pages:
        for block in page.blocks:
            text = block.text.strip()
            if not text:
                continue

            # Check for structural heading triggers
            if block.is_heading or len(text.split("\n")) <= 2 and len(text) < 120:
                tier_match = RE_TIER.search(text)
                clause_match = RE_CLAUSE.search(text)

                if tier_match:
                    tier_num = tier_match.group(1)
                    tier_name = tier_match.group(2) or f"Tier_{tier_num}"
                    current_tier = f"Tier_{tier_num}"
                    breadcrumb = f"{base_prefix}/{current_tier}/{_slugify(tier_name)}"
                    node = ClauseNode(
                        breadcrumb=breadcrumb,
                        doc_id=doc_id,
                        schedule_no=schedule_no,
                        title=text,
                        level="tier",
                        text=text,
                        page_no=page.page_no,
                        bbox=block.bbox,
                        spans=block.spans,
                    )
                    flat_clauses.append(node)
                    continue

                if clause_match:
                    clause_no = clause_match.group(1)
                    current_section = f"Clause_{clause_no}"
                    breadcrumb = f"{base_prefix}/{current_section}/{_slugify(text)}"
                    node = ClauseNode(
                        breadcrumb=breadcrumb,
                        doc_id=doc_id,
                        schedule_no=schedule_no,
                        title=text,
                        level="clause",
                        text=text,
                        page_no=page.page_no,
                        bbox=block.bbox,
                        spans=block.spans,
                    )
                    flat_clauses.append(node)
                    continue

                if is_dfpds and "SCHEDULE" in text.upper():
                    current_section = _slugify(text)
                    breadcrumb = f"{base_prefix}/{current_section}"
                    node = ClauseNode(
                        breadcrumb=breadcrumb,
                        doc_id=doc_id,
                        schedule_no=schedule_no,
                        title=text,
                        level="schedule",
                        text=text,
                        page_no=page.page_no,
                        bbox=block.bbox,
                        spans=block.spans,
                    )
                    flat_clauses.append(node)
                    continue

            # Standard clause body block
            if current_tier:
                breadcrumb = f"{base_prefix}/{current_tier}"
            else:
                breadcrumb = f"{base_prefix}/{_slugify(current_section)}"

            node = ClauseNode(
                breadcrumb=breadcrumb,
                doc_id=doc_id,
                schedule_no=schedule_no,
                title=text[:60],
                level="section",
                text=text,
                page_no=page.page_no,
                bbox=block.bbox,
                spans=block.spans,
            )
            flat_clauses.append(node)

    return ParsedHierarchy(
        doc_id=doc_id,
        root_nodes=[n for n in flat_clauses if n.level in ("schedule", "tier", "clause", "document")],
        flat_clauses=flat_clauses,
    )
