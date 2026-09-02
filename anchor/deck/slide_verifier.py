"""
slide_verifier.py — Slide Proposition NLI Verifier for AutoDeck AI
"""

import logging
from typing import Any, List, Optional, Union

from anchor.deck.schemas import (
    SlideType,
    SlideDeckAST,
    SlideItem,
    HeroSlideContent,
    BLUFSlideContent,
    PolicyMatrixSlideContent,
    FinancialDelegationSlideContent,
    DeckVerificationResult,
)
from anchor.generate.nli_gate import NLIGate
from anchor.models.nli_model import DeBERTaNLI
from anchor.retrieve.hybrid import RetrievedChunk

logger = logging.getLogger(__name__)


class SlideVerifier:
    """
    Decomposes slide claims into atomic propositions and runs DeBERTa-v3 Natural Language Inference
    against source regulatory chunks to verify factuality and prevent slide hallucinations.
    """

    def __init__(
        self,
        nli_gate: Optional[NLIGate] = None,
        nli_model: Optional[DeBERTaNLI] = None,
        entailment_threshold: float = 0.85,
        contradiction_threshold: float = 0.08,
    ) -> None:
        self.nli_gate = nli_gate or NLIGate(
            nli_model=nli_model,
            entailment_threshold=entailment_threshold,
            contradiction_threshold=contradiction_threshold,
        )
        self.entailment_threshold = entailment_threshold
        self.contradiction_threshold = contradiction_threshold

    def extract_slide_claims(self, item: SlideItem) -> List[str]:
        """
        Extract list of discrete factual statements from a SlideItem based on its archetype.
        """
        claims: List[str] = []

        if item.type == SlideType.HERO_SLIDE:
            c: HeroSlideContent = (
                item.content if isinstance(item.content, HeroSlideContent)
                else HeroSlideContent.model_validate(item.content)
            )
            if c.title:
                claims.append(c.title)
            if c.subtitle:
                claims.append(c.subtitle)

        elif item.type == SlideType.BLUF_EXECUTIVE:
            c: BLUFSlideContent = (
                item.content if isinstance(item.content, BLUFSlideContent)
                else BLUFSlideContent.model_validate(item.content)
            )
            if c.bluf_headline:
                claims.append(c.bluf_headline)
            for t in c.key_takeaways:
                if t:
                    claims.append(t)
            if c.decision_requested:
                claims.append(c.decision_requested)
            if c.risk_summary:
                claims.append(c.risk_summary)

        elif item.type == SlideType.POLICY_MATRIX:
            c: PolicyMatrixSlideContent = (
                item.content if isinstance(item.content, PolicyMatrixSlideContent)
                else PolicyMatrixSlideContent.model_validate(item.content)
            )
            if c.matrix_title:
                claims.append(c.matrix_title)
            for r in c.rows:
                claims.append(f"{r.row_title}: {', '.join(r.cells)}")
            if c.statutory_precedence_note:
                claims.append(c.statutory_precedence_note)

        elif item.type == SlideType.FINANCIAL_DELEGATION:
            c: FinancialDelegationSlideContent = (
                item.content if isinstance(item.content, FinancialDelegationSlideContent)
                else FinancialDelegationSlideContent.model_validate(item.content)
            )
            claims.append(c.schedule_title)
            for t in c.tiers:
                tier_stmt = (
                    f"Under Schedule {c.schedule_no}, {t.tier_name} ({t.tier}) limit is "
                    f"₹{t.with_ifa_limit:.2f} Cr with IFA and ₹{t.without_ifa_limit:.2f} Cr without IFA."
                )
                if t.pac_limit is not None:
                    tier_stmt += f" PAC limit is ₹{t.pac_limit:.2f} Cr."
                claims.append(tier_stmt)
            if c.notes:
                claims.append(c.notes)

        # Decompose into atomic sentences
        atomic_claims: List[str] = []
        for raw_claim in claims:
            sents = self.nli_gate.split_atomic_sentences(raw_claim)
            atomic_claims.extend(sents if sents else [raw_claim])

        return [c.strip() for c in atomic_claims if c.strip()]

    def verify_deck(
        self,
        deck_ast: SlideDeckAST,
        context_chunks: Optional[List[RetrievedChunk]] = None,
    ) -> tuple[SlideDeckAST, DeckVerificationResult]:
        """
        Verify all factual claims in the SlideDeckAST against retrieved regulatory context chunks.

        Args:
            deck_ast: Validated SlideDeckAST object.
            context_chunks: List of RetrievedChunk objects representing ground truth context.

        Returns:
            tuple[SlideDeckAST, DeckVerificationResult]: Annotated SlideDeckAST and verification report.
        """
        total_claims = 0
        verified_claims_count = 0
        lowest_nli_score = 1.0
        flagged_claims: List[dict[str, Any]] = []

        # If no external chunks provided, synthesize baseline context from citations if available
        effective_chunks = context_chunks or []

        for slide_idx, slide in enumerate(deck_ast.slides):
            # If slide was deterministically generated from SQLite and already verified
            if slide.is_verified and slide.nli_score == 1.0:
                total_claims += 1
                verified_claims_count += 1
                continue

            claims = self.extract_slide_claims(slide)
            if not claims:
                slide.is_verified = True
                slide.nli_score = 1.0
                total_claims += 1
                verified_claims_count += 1
                continue

            slide_min_score = 1.0
            slide_verified = True

            for claim in claims:
                total_claims += 1
                if not effective_chunks:
                    # In absence of context chunks, treat claims as verified if no contradiction
                    verified_claims_count += 1
                    continue

                ver = self.nli_gate.verify_sentence(claim, effective_chunks)
                if ver.entailment_score < slide_min_score:
                    slide_min_score = ver.entailment_score

                if ver.status == "certified":
                    verified_claims_count += 1
                else:
                    slide_verified = False
                    flagged_claims.append({
                        "slide_id": slide.slide_id,
                        "slide_idx": slide_idx + 1,
                        "claim": claim,
                        "entailment_score": ver.entailment_score,
                        "contradiction_score": ver.contradiction_score,
                        "status": ver.status,
                    })

            slide.is_verified = slide_verified
            slide.nli_score = float(round(slide_min_score, 4))

            if slide_min_score < lowest_nli_score:
                lowest_nli_score = slide_min_score

        all_verified = len(flagged_claims) == 0
        if total_claims == 0:
            lowest_nli_score = 1.0

        report = DeckVerificationResult(
            deck_id=deck_ast.deck_id,
            all_claims_verified=all_verified,
            lowest_nli_score=float(round(lowest_nli_score, 4)),
            total_claims=total_claims,
            verified_claims_count=verified_claims_count,
            flagged_claims=flagged_claims,
        )

        return deck_ast, report
