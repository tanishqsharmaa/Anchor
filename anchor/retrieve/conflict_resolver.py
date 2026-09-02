"""
conflict_resolver.py — Cross-Regulatory Conflict Resolver (DFPDS-2026 > DPM-2025 > Navy Regs)
"""

from typing import Optional
from anchor.retrieve.hybrid import RetrievedChunk


class ConflictResolver:
    """
    Cross-regulatory conflict resolver enforcing canonical statutory precedence:
    1. DFPDS-2026: Supreme authority on delegation of financial powers and CFA sanction limits.
    2. DPM-2025: Supreme authority on defence procurement procedures, tendering modes, and commercial terms.
    3. Navy Regulations: Authority on operational command hierarchy and administrative duties.
    """

    PRECEDENCE_WEIGHTS: dict[str, int] = {
        "dfpds": 300,
        "dpm": 200,
        "navy_regs": 100,
    }

    @staticmethod
    def get_document_family(doc_id: str, breadcrumb: str = "") -> str:
        """Categorize chunk into its regulatory statutory family."""
        text = f"{doc_id} {breadcrumb}".lower()
        if "dfpds" in text or "schedule" in text:
            return "dfpds"
        if "dpm" in text:
            return "dpm"
        if "navy_regs" in text or "navy regs" in text:
            return "navy_regs"
        return "dfpds"

    def detect_financial_delegation_conflict(
        self, chunks: list[RetrievedChunk]
    ) -> bool:
        """Check if chunks contain conflicting financial delegation guidance across bodies."""
        families = {self.get_document_family(c.doc_id, c.breadcrumb) for c in chunks}
        has_financial_keywords = any(
            any(
                kw in c.text.lower()
                for kw in [
                    "sanction",
                    "financial limit",
                    "delegation",
                    "crore",
                    "lakhs",
                    "financial powers",
                ]
            )
            for c in chunks
        )
        return ("dfpds" in families and ("dpm" in families or "navy_regs" in families)) and has_financial_keywords

    def detect_procurement_mode_conflict(
        self, chunks: list[RetrievedChunk]
    ) -> bool:
        """Check if chunks contain conflicting procurement mode guidance between DPM and Navy Regs."""
        families = {self.get_document_family(c.doc_id, c.breadcrumb) for c in chunks}
        has_procurement_keywords = any(
            any(
                kw in c.text.lower()
                for kw in [
                    "open tender",
                    "limited tender",
                    "ote",
                    "lte",
                    "single tender",
                    "quotation",
                    "purchase procedure",
                ]
            )
            for c in chunks
        )
        return ("dpm" in families and "navy_regs" in families) and has_procurement_keywords

    def resolve_conflicts(
        self, chunks: list[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        """
        Reconcile cross-regulatory conflicts according to statutory supremacy:
        - DFPDS-2026 overrides DPM-2025 and Navy Regs on financial delegations.
        - DPM-2025 overrides Navy Regs on procurement modes and commercial terms.
        - Lower-precedence conflicting chunks are flagged with conflict_flag=True.
        - Winning chunks receive precedence notes.
        """
        if not chunks:
            return []

        has_fin_conflict = self.detect_financial_delegation_conflict(chunks)
        has_proc_conflict = self.detect_procurement_mode_conflict(chunks)

        import copy

        resolved_chunks: list[RetrievedChunk] = []

        for original_chunk in chunks:
            chunk = copy.copy(original_chunk)
            family = self.get_document_family(chunk.doc_id, chunk.breadcrumb)
            score_multiplier = 1.0

            # 1. Financial Delegation Conflict Resolution
            if has_fin_conflict:
                if family == "dfpds":
                    score_multiplier *= 1.5
                    chunk.precedence_note = (
                        "DFPDS-2026: Statutory supremacy on financial power delegation."
                    )
                elif family in ("dpm", "navy_regs") and any(
                    kw in chunk.text.lower()
                    for kw in ["sanction", "delegation", "crore", "lakhs", "financial powers"]
                ):
                    chunk.conflict_flag = True
                    chunk.precedence_note = (
                        "Overridden by DFPDS-2026 statutory financial delegation authority."
                    )
                    score_multiplier *= 0.5

            # 2. Procurement Mode Conflict Resolution
            if has_proc_conflict:
                if family == "dpm":
                    score_multiplier *= 1.3
                    if not chunk.precedence_note:
                        chunk.precedence_note = (
                            "DPM-2025: Statutory supremacy on defence procurement procedures."
                        )
                elif family == "navy_regs" and any(
                    kw in chunk.text.lower()
                    for kw in ["open tender", "limited tender", "ote", "lte", "quotation", "purchase"]
                ):
                    chunk.conflict_flag = True
                    chunk.precedence_note = (
                        "Overridden by DPM-2025 statutory procurement procedures."
                    )
                    score_multiplier *= 0.6

            chunk.score = float(chunk.score * score_multiplier)
            resolved_chunks.append(chunk)

        # Re-sort to guarantee authoritative winning chunks rank highest
        resolved_chunks.sort(key=lambda c: (not c.conflict_flag, c.score), reverse=True)
        return resolved_chunks
