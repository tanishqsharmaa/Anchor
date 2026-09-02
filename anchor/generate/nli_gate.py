"""
nli_gate.py — Per-Sentence DeBERTa-v3 Natural Language Inference Verification Gate
"""

import logging
import re
from typing import Any, Optional
from pydantic import BaseModel, Field
import spacy

from anchor.config import settings
from anchor.models.nli_model import DeBERTaNLI
from anchor.retrieve.hybrid import RetrievedChunk

logger = logging.getLogger(__name__)


class SentenceVerification(BaseModel):
    """
    Verification record for an individual atomic sentence evaluated against source chunks.
    """

    sentence_idx: int
    text: str
    best_premise_chunk_id: Optional[str] = None
    best_premise_breadcrumb: Optional[str] = None
    entailment_score: float = 0.0
    neutral_score: float = 0.0
    contradiction_score: float = 0.0
    status: str = Field(
        default="abstain",
        description="Verification status: 'certified' (>=0.85), 'regen' (0.50-0.85), 'abstain' (<0.50 or contra>0.08)",
    )


class NLIGate:
    """
    Sentence-Level Natural Language Inference (NLI) Verification Gate.
    Decomposes synthesized response into atomic sentences via spaCy, computes
    DeBERTa-v3 3-way probabilities against top-3 source chunks, and executes
    multi-tier threshold verification and targeted regeneration.
    """

    # Regex protection patterns for abbreviations and currency prefixes
    _ABBREVIATION_PATTERNS = [
        (re.compile(r"\bRs\.\s*", re.IGNORECASE), "Rs_DOT_ "),
        (re.compile(r"\bi\.e\.\s*", re.IGNORECASE), "i_DOT_e_DOT_ "),
        (re.compile(r"\be\.g\.\s*", re.IGNORECASE), "e_DOT_g_DOT_ "),
        (re.compile(r"\bSch\.\s*", re.IGNORECASE), "Sch_DOT_ "),
        (re.compile(r"\bNo\.\s*", re.IGNORECASE), "No_DOT_ "),
        (re.compile(r"\bTier\s+(\d+)\.\s*", re.IGNORECASE), r"Tier_\1_DOT_ "),
        (re.compile(r"\bpara\.\s*", re.IGNORECASE), "para_DOT_ "),
        (re.compile(r"\bvs\.\s*", re.IGNORECASE), "vs_DOT_ "),
    ]

    def __init__(
        self,
        nli_model: Optional[DeBERTaNLI] = None,
        spacy_nlp: Optional[Any] = None,
        entailment_threshold: float = 0.85,
        regen_min_threshold: float = 0.50,
        contradiction_threshold: float = 0.08,
    ) -> None:
        self._nli_model = nli_model
        self._nlp = spacy_nlp
        self.entailment_threshold = entailment_threshold
        self.regen_min_threshold = regen_min_threshold
        self.contradiction_threshold = contradiction_threshold

    @property
    def nli_model(self) -> DeBERTaNLI:
        """Lazy load DeBERTaNLI model on demand."""
        if self._nli_model is None:
            self._nli_model = DeBERTaNLI()
        return self._nli_model

    @property
    def nlp(self) -> Any:
        """Lazy load spaCy language pipeline with sentencizer on demand."""
        if self._nlp is None:
            self._nlp = spacy.blank("en")
            self._nlp.add_pipe("sentencizer")
        return self._nlp

    def split_atomic_sentences(self, text: str) -> list[str]:
        """
        Split synthesized text into atomic sentences while preserving abbreviations and currency tokens.
        """
        if not text or not text.strip():
            return []

        processed_text = text.strip()

        # Mask abbreviations before sentence splitting
        for pattern, replacement in self._ABBREVIATION_PATTERNS:
            processed_text = pattern.sub(replacement, processed_text)

        doc = self.nlp(processed_text)
        raw_sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]

        # Unmask abbreviations
        final_sentences: list[str] = []
        for sent in raw_sentences:
            unmasked = sent
            unmasked = unmasked.replace("Rs_DOT_ ", "Rs. ")
            unmasked = unmasked.replace("i_DOT_e_DOT_ ", "i.e. ")
            unmasked = unmasked.replace("e_DOT_g_DOT_ ", "e.g. ")
            unmasked = unmasked.replace("Sch_DOT_ ", "Sch. ")
            unmasked = unmasked.replace("No_DOT_ ", "No. ")
            unmasked = re.sub(r"Tier_(\d+)_DOT_\s*", r"Tier \1. ", unmasked)
            unmasked = unmasked.replace("para_DOT_ ", "para. ")
            unmasked = unmasked.replace("vs_DOT_ ", "vs. ")
            if unmasked.strip():
                final_sentences.append(unmasked.strip())

        return final_sentences

    def get_archetype_threshold(self, archetype: Optional[str]) -> float:
        """Resolve NLI entailment threshold based on query archetype (ENH-005)."""
        if not archetype:
            return self.entailment_threshold
        arch_clean = archetype.lower()
        if arch_clean in ("financial", "money", "pricing"):
            return 0.90
        elif arch_clean in ("procedural", "process", "workflow"):
            return 0.80
        elif arch_clean in ("structured", "deterministic"):
            return 1.00
        return self.entailment_threshold

    def verify_sentence(
        self,
        sentence: str,
        chunks: list[RetrievedChunk],
        sentence_idx: int = 0,
        archetype: Optional[str] = None,
        entailment_threshold: Optional[float] = None,
    ) -> SentenceVerification:
        """
        Evaluate NLI probabilities for a single sentence against all retrieved context chunks.
        """
        if not sentence or not sentence.strip():
            return SentenceVerification(
                sentence_idx=sentence_idx,
                text="",
                status="abstain",
            )

        if not chunks:
            return SentenceVerification(
                sentence_idx=sentence_idx,
                text=sentence,
                status="abstain",
                entailment_score=0.0,
                neutral_score=1.0,
                contradiction_score=0.0,
            )

        effective_threshold = entailment_threshold or self.get_archetype_threshold(archetype)

        # Build premise-hypothesis pairs: (chunk.text, sentence)
        pairs = [(chunk.text.strip(), sentence.strip()) for chunk in chunks]
        prob_results = self.nli_model.predict_batch(pairs)

        # Identify candidate chunk yielding highest entailment score
        best_idx = 0
        best_prob = prob_results[0]
        max_entail = best_prob.get("entailment", 0.0)

        for idx, prob in enumerate(prob_results):
            entail = prob.get("entailment", 0.0)
            if entail > max_entail:
                max_entail = entail
                best_idx = idx
                best_prob = prob

        best_chunk = chunks[best_idx]
        p_entail = float(best_prob.get("entailment", 0.0))
        p_neutral = float(best_prob.get("neutral", 0.0))
        p_contra = float(best_prob.get("contradiction", 0.0))

        # Multi-Tier Policy
        if p_contra > self.contradiction_threshold or p_entail < self.regen_min_threshold:
            status = "abstain"
        elif p_entail >= effective_threshold and p_contra <= self.contradiction_threshold:
            status = "certified"
        else:
            # 0.50 <= p_entail < effective_threshold and p_contra <= 0.08
            status = "regen"

        return SentenceVerification(
            sentence_idx=sentence_idx,
            text=sentence.strip(),
            best_premise_chunk_id=best_chunk.chunk_id,
            best_premise_breadcrumb=best_chunk.breadcrumb,
            entailment_score=float(round(p_entail, 4)),
            neutral_score=float(round(p_neutral, 4)),
            contradiction_score=float(round(p_contra, 4)),
            status=status,
        )

    def verify_synthesis(
        self,
        text: str,
        chunks: list[RetrievedChunk],
        synthesizer: Optional[Any] = None,
        max_regen_attempts: int = 2,
        archetype: Optional[str] = None,
        entailment_threshold: Optional[float] = None,
    ) -> tuple[list[SentenceVerification], bool, str]:
        """
        Verify all atomic sentences in synthesized text with bounded regeneration loops on borderline claims.

        Args:
            text: Synthesized answer string.
            chunks: Context chunks from retrieval/reranker.
            synthesizer: Optional Synthesizer instance to execute targeted regenerations.
            max_regen_attempts: Maximum retry attempts for borderline sentences (default 2).
            archetype: Optional query archetype for archetype-specific thresholding.
            entailment_threshold: Explicit entailment ceiling override.

        Returns:
            tuple[list[SentenceVerification], bool, str]:
                - list of SentenceVerification records for each sentence.
                - is_grounded (True only if all emitted sentences are certified).
                - final_text (reassembled text with regenerated or certified sentences).
        """
        raw_sentences = self.split_atomic_sentences(text)
        if not raw_sentences:
            return [], False, ""

        verifications: list[SentenceVerification] = []
        final_sentence_texts: list[str] = []

        for idx, sentence in enumerate(raw_sentences):
            ver = self.verify_sentence(
                sentence,
                chunks,
                sentence_idx=idx,
                archetype=archetype,
                entailment_threshold=entailment_threshold,
            )

            # Check if regeneration is triggered and synthesizer is available
            attempt = 0
            curr_sentence = sentence
            while ver.status == "regen" and synthesizer is not None and attempt < max_regen_attempts:
                if hasattr(synthesizer, "generator") and hasattr(synthesizer.generator, "is_available") and not synthesizer.generator.is_available():
                    break
                attempt += 1
                logger.info(
                    f"[NLIGate] Sentence {idx} entailment={ver.entailment_score:.2f} triggered regen attempt {attempt}/{max_regen_attempts}"
                )
                regen_prompt = (
                    f"Rewrite the following statement to be strictly grounded and verifiable using ONLY the context chunks:\n"
                    f"Statement: {curr_sentence}"
                )
                try:
                    new_text = synthesizer.synthesize(query=regen_prompt, chunks=chunks, temperature=0.0)
                    new_sentences = self.split_atomic_sentences(new_text)
                    if new_sentences:
                        curr_sentence = new_sentences[0]
                        ver = self.verify_sentence(
                            curr_sentence,
                            chunks,
                            sentence_idx=idx,
                            archetype=archetype,
                            entailment_threshold=entailment_threshold,
                        )
                    else:
                        break
                except Exception as e:
                    logger.warning(f"[NLIGate] Regeneration attempt failed: {e}")
                    break

            verifications.append(ver)
            final_sentence_texts.append(ver.text)

        is_grounded = all(v.status == "certified" for v in verifications) and len(verifications) > 0
        final_text = " ".join(final_sentence_texts)

        return verifications, is_grounded, final_text
