"""
classifier.py — Two-Tier Question Classifier (Rule-Based Regex + DeBERTa Fallback)
"""

from dataclasses import dataclass, field
import re
from typing import Any, Optional

from anchor.models.nli_model import DeBERTaNLI
from anchor.models.translator import hindi_translator, is_hindi_text
from anchor.retrieve.resolver import normalize_cfa_tier


ROMAN_NUMERALS: dict[str, int] = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
    "viii": 8,
    "ix": 9,
    "x": 10,
    "xi": 11,
    "xii": 12,
    "xiii": 13,
    "xiv": 14,
    "xv": 15,
    "xvi": 16,
    "xvii": 17,
    "xviii": 18,
    "xix": 19,
    "xx": 20,
    "xxi": 21,
    "xxii": 22,
    "xxiii": 23,
    "xxiv": 24,
    "xxv": 25,
    "xxvi": 26,
    "xxvii": 27,
    "xxviii": 28,
    "xxix": 29,
    "xxx": 30,
    "xxxi": 31,
    "xxxii": 32,
}

DPM_TERMS: dict[str, str] = {
    "ote": "OTE",
    "open tender": "OTE",
    "open tender enquiry": "OTE",
    "lte": "LTE",
    "limited tender": "LTE",
    "limited tender enquiry": "LTE",
    "gte": "GTE",
    "global tender": "GTE",
    "global tender enquiry": "GTE",
    "pbg": "PBG",
    "performance bank guarantee": "PBG",
    "bank guarantee": "PBG",
    "ld": "LD",
    "liquidated damages": "LD",
    "pac": "PAC",
    "proprietary article": "PAC",
    "proprietary article certificate": "PAC",
    "warranty": "WARRANTY",
}


@dataclass
class ClassificationResult:
    """Result of query classification and entity extraction."""

    query_type: str  # "structured" | "interpretive"
    schedule_no: Optional[int] = None
    schedule_nos: list[int] = field(default_factory=list)
    tier: Optional[str] = None  # Canonical "Tier 1" .. "Tier 6"
    with_ifa: bool = True
    is_pac: bool = False
    dpm_mode: Optional[str] = None
    archetype: str = "interpretive"
    language: str = "en"
    entities: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    routing_reason: str = ""


class QuestionClassifier:
    """
    Two-tier question classifier:
    - Tier 1: High-speed rule-based regex entity extraction routing structured queries to Path A.
    - Tier 2: DeBERTa-v3 NLI zero-shot classification fallback for ambiguous queries.
    """

    def __init__(self, nli_model: Optional[DeBERTaNLI] = None) -> None:
        self._nli_model = nli_model

    @property
    def nli_model(self) -> DeBERTaNLI:
        """Lazy load DeBERTa NLI model on demand."""
        if self._nli_model is None:
            self._nli_model = DeBERTaNLI()
        return self._nli_model

    def extract_schedule_numbers(self, query: str) -> list[int]:
        """Extract all DFPDS schedule numbers (1–32) via Arabic or Roman numerals (ENH-002)."""
        q_lower = query.lower()
        found: list[int] = []

        # 1. Match Arabic numerals
        for m in re.finditer(r"\b(?:schedule|sch|s)[\s\-_#.:]*([0-9]{1,4})\b", q_lower):
            val = int(m.group(1))
            if val not in found:
                found.append(val)

        # 2. Match Roman numerals
        for m in re.finditer(r"\b(?:schedule|sch|s)[\s\-_#.:]*([ivx]{1,6})\b", q_lower):
            rom_str = m.group(1).lower()
            if rom_str in ROMAN_NUMERALS:
                val = ROMAN_NUMERALS[rom_str]
                if val not in found:
                    found.append(val)

        return found

    def extract_schedule_number(self, query: str) -> Optional[int]:
        """Extract primary DFPDS schedule number (1–32) via Arabic or Roman numerals."""
        nums = self.extract_schedule_numbers(query)
        return nums[0] if nums else None

    def extract_cfa_tier(self, query: str) -> Optional[str]:
        """Extract Competent Financial Authority tier (Tier 1..6) or naval title."""
        q_lower = query.lower()

        # 1. Check explicit tier / L-designation (e.g. Tier 3, L2, T1, Tier-5)
        tier_match = re.search(r"\b(?:tier|l|t)[\s\-_]?([1-6])\b", q_lower)
        if tier_match:
            return f"Tier {tier_match.group(1)}"

        # 2. Match specific naval authority designations (check more specific multi-word titles first)
        # Tier 3 specific titles
        if (
            "admiral superintendent" in q_lower
            or "asd dockyard" in q_lower
            or "asd (naval dockyard)" in q_lower
            or "fleet commander" in q_lower
            or "flag officer commanding western fleet" in q_lower
            or "flag officer commanding eastern fleet" in q_lower
            or re.search(r"\basd\b", q_lower)
            or re.search(r"\bfoma\b", q_lower)
            or re.search(r"\bfocwf\b", q_lower)
            or re.search(r"\bfocef\b", q_lower)
        ):
            return "Tier 3"

        # Tier 2 specific titles
        if (
            "flag officer commanding-in-chief" in q_lower
            or "flag officer commanding in chief" in q_lower
            or "foc-in-c" in q_lower
            or "focinc" in q_lower
            or "vice chief of the naval staff" in q_lower
            or "vice chief of naval staff" in q_lower
            or "vice chief" in q_lower
            or re.search(r"\bvcns\b", q_lower)
        ):
            return "Tier 2"

        # Tier 1 specific titles
        if (
            "chief of the naval staff" in q_lower
            or "chief of naval staff" in q_lower
            or re.search(r"\bcns\b", q_lower)
            or re.search(r"\badmiral\b", q_lower)
        ):
            return "Tier 1"

        # Tier 4 specific titles
        if (
            "chief staff officer" in q_lower
            or re.search(r"\bcso\b", q_lower)
            or re.search(r"\bnoic\b", q_lower)
            or "naval officer-in-charge" in q_lower
            or "naval officer in charge" in q_lower
            or "commodore" in q_lower
        ):
            return "Tier 4"

        # Tier 5 specific titles (Capital Ships)
        if (
            "capital ship" in q_lower
            or "co frigate" in q_lower
            or "co destroyer" in q_lower
            or "co carrier" in q_lower
            or "co - capital ship" in q_lower
            or re.search(r"\bfrigate\b", q_lower)
            or re.search(r"\bdestroyer\b", q_lower)
            or re.search(r"\bcarrier\b", q_lower)
        ):
            return "Tier 5"

        # Tier 6 specific titles (Minor War Vessels & Shore Bases)
        if (
            "minor war vessel" in q_lower
            or "shore base" in q_lower
            or "co minor war vessel" in q_lower
            or "co - minor war vessel" in q_lower
            or "corvette" in q_lower
            or "patrol vessel" in q_lower
        ):
            return "Tier 6"

        if "commanding officer" in q_lower or re.search(r"\b(?:c\.?o\.?|c/o)\b", q_lower):
            # Guard against common false positive prefix words (e.g. co-operate, co-pilot)
            if not re.search(r"\bco[\s\-]*(?:operate|operation|ordinate|ordination|author|founder|exist|pilot|worker|sign|opt|locate|host)\b", q_lower):
                return "Tier 5"

        return None


    def extract_ifa_status(self, query: str) -> bool:
        """Detect whether IFA concurrence is required or negated."""
        q_lower = query.lower()

        # Explicit negation: without IFA, no IFA, non-IFA, sans IFA
        if (
            "without ifa" in q_lower
            or "without-ifa" in q_lower
            or "no ifa" in q_lower
            or "non-ifa" in q_lower
            or "sans ifa" in q_lower
            or "excluding ifa" in q_lower
            or "without concurrence" in q_lower
        ):
            return False

        # Default is with IFA (standard statutory baseline)
        return True

    def extract_pac_status(self, query: str) -> bool:
        """Detect whether query references PAC (Proprietary Article Certificate)."""
        q_lower = query.lower()
        return bool(
            re.search(r"\bpac\b", q_lower)
            or "proprietary article" in q_lower
            or "single source" in q_lower
            or "sole source" in q_lower
        )

    def extract_dpm_mode(self, query: str) -> Optional[str]:
        """Detect standard DPM-2025 procurement modes or contract terms."""
        q_lower = query.lower()
        for term, mode in DPM_TERMS.items():
            if re.search(r"\b" + re.escape(term) + r"\b", q_lower):
                return mode
        return None

    def is_complex_interpretive_query(self, query: str) -> bool:
        """Detect open-ended, procedural, multi-hop, or statutory conflict language."""
        q_lower = query.lower()

        # Key phrases indicating policy / interpretive reasoning
        interpretive_indicators = [
            "bypass gem",
            "emergency powers",
            "under what conditions",
            "under what specific",
            "explain the conflict",
            "statutory conflict",
            "make in india",
            "indigenisation",
            "international waters",
            "procedure for obtaining",
            "statutory duties",
            "officer of the watch",
            "justified for",
            "operational conditions",
            "single tender enquiry",
        ]

        for phrase in interpretive_indicators:
            if phrase in q_lower:
                return True

        return False


    def classify(self, query: str) -> ClassificationResult:
        """
        Classify user query into Path A (Structured) or Path B (Interpretive)
        and extract all relevant statutory entities.
        """
        if not query or not query.strip():
            return ClassificationResult(
                query_type="interpretive",
                routing_reason="Empty query default",
                confidence=0.5,
            )

        q_clean = query.strip()
        lang = "hi" if is_hindi_text(q_clean) else "en"
        effective_query = hindi_translator.translate_to_english(q_clean) if lang == "hi" else q_clean

        # Fast-check for complex interpretive queries
        if self.is_complex_interpretive_query(effective_query):
            return ClassificationResult(
                query_type="interpretive",
                language=lang,
                routing_reason="Policy / procedural query indicators detected",
                confidence=0.98,
                entities={"raw_query": q_clean, "effective_query": effective_query},
            )

        # Entity extraction
        schedule_nos = self.extract_schedule_numbers(effective_query)
        schedule_no = schedule_nos[0] if schedule_nos else None
        tier = self.extract_cfa_tier(effective_query)
        with_ifa = self.extract_ifa_status(effective_query)
        is_pac = self.extract_pac_status(effective_query)
        dpm_mode = self.extract_dpm_mode(effective_query)

        entities: dict[str, Any] = {
            "raw_query": q_clean,
            "effective_query": effective_query,
            "schedule_no": schedule_no,
            "schedule_nos": schedule_nos,
            "tier": tier,
            "with_ifa": with_ifa,
            "is_pac": is_pac,
            "dpm_mode": dpm_mode,
        }

        # Case 0: Multi-Schedule Comparison Lookup (ENH-002)
        if len(schedule_nos) > 1 and tier is not None:
            return ClassificationResult(
                query_type="structured",
                schedule_no=schedule_no,
                schedule_nos=schedule_nos,
                tier=tier,
                with_ifa=with_ifa,
                is_pac=is_pac,
                dpm_mode=dpm_mode,
                archetype="comparative",
                language=lang,
                entities=entities,
                confidence=1.0,
                routing_reason="Multi-schedule comparison matched for structured resolution",
            )

        # Case 1: Direct DFPDS Financial Delegation Lookup (Schedule + Tier)
        if schedule_no is not None and tier is not None:
            return ClassificationResult(
                query_type="structured",
                schedule_no=schedule_no,
                schedule_nos=schedule_nos,
                tier=tier,
                with_ifa=with_ifa,
                is_pac=is_pac,
                dpm_mode=dpm_mode,
                archetype="structured",
                entities=entities,
                confidence=1.0,
                routing_reason="Exact schedule and CFA tier matched for SQL resolution",
            )

        # Case 2: Direct DPM Threshold Lookup (OTE, LTE, GTE, PBG, LD, PAC)
        if dpm_mode is not None and schedule_no is None:
            # Check if it's asking for standard numerical threshold / percentage
            if any(
                kw in q_clean.lower()
                for kw in [
                    "threshold",
                    "limit",
                    "ceiling",
                    "rate",
                    "percentage",
                    "required for",
                    "mandatory",
                    "penalty",
                ]
            ):
                return ClassificationResult(
                    query_type="structured",
                    schedule_no=None,
                    schedule_nos=[],
                    tier=None,
                    with_ifa=with_ifa,
                    is_pac=is_pac or (dpm_mode == "PAC"),
                    dpm_mode=dpm_mode,
                    archetype="financial" if dpm_mode in ("PBG", "LD", "PAC") else "structured",
                    entities=entities,
                    confidence=0.95,
                    routing_reason=f"DPM {dpm_mode} statutory threshold lookup",
                )

        # Case 3: Partial entity with strong financial inquiry (Schedule only or Tier only)
        if schedule_no is not None or tier is not None:
            # If asking about limits / sanctions but one entity is missing or generic
            if any(
                kw in q_clean.lower()
                for kw in ["limit", "ceiling", "sanction", "how much", "power", "approve"]
            ):
                # Fallback to DeBERTa to verify if it is an exact lookup request
                try:
                    scores = self.nli_model.predict(
                        premise=q_clean,
                        hypothesis="This query requests an exact numerical financial delegation limit or schedule lookup.",
                    )
                    if scores["entailment"] > 0.65:
                        return ClassificationResult(
                            query_type="structured",
                            schedule_no=schedule_no,
                            schedule_nos=schedule_nos,
                            tier=tier,
                            with_ifa=with_ifa,
                            is_pac=is_pac,
                            dpm_mode=dpm_mode,
                            archetype="structured",
                            entities=entities,
                            confidence=float(scores["entailment"]),
                            routing_reason="DeBERTa NLI verified structured financial lookup",
                        )
                except Exception:
                    pass

        # Detect archetype for interpretive queries (ENH-005)
        archetype = "interpretive"
        q_lower = q_clean.lower()
        if any(w in q_lower for w in ["crore", "lakh", "rs.", "inr", "percentage", "amount", "budget", "cost", "price", "fee"]):
            archetype = "financial"
        elif any(w in q_lower for w in ["procedure", "step", "how to", "process", "rule", "condition", "flow", "documentation", "approval"]):
            archetype = "procedural"

        # Case 4: Default to Interpretive Hybrid RAG (Path B)
        return ClassificationResult(
            query_type="interpretive",
            schedule_no=schedule_no,
            schedule_nos=schedule_nos,
            tier=tier,
            with_ifa=with_ifa,
            is_pac=is_pac,
            dpm_mode=dpm_mode,
            archetype=archetype,
            entities=entities,
            confidence=0.90,
            routing_reason="Interpretive regulatory inquiry routed to hybrid RAG",
        )
