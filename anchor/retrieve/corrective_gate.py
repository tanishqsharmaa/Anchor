"""
corrective_gate.py — Corrective Relevance Gate for Retrieval Quality Assurance
"""

from typing import Optional
from anchor.config import settings
from anchor.models.embedder import BGEEmbedder
from anchor.retrieve.hybrid import RetrievedChunk


class CorrectiveGate:
    """
    Corrective Relevance Gate verifying retrieval candidates before LLM synthesis.
    Filters out noisy, low-confidence passages and determines if sufficient
    grounded context exists to avoid hallucinations (or signal Certified Abstention).
    """

    def __init__(
        self,
        embedder: Optional[BGEEmbedder] = None,
        min_rerank_score: float = 0.25,
        min_cosine_sim: float = 0.60,
    ) -> None:
        self._embedder = embedder
        self.min_rerank_score = min_rerank_score
        self.min_cosine_sim = min_cosine_sim

    @property
    def embedder(self) -> Optional[BGEEmbedder]:
        """Lazy load BGE-M3 embedder if needed."""
        return self._embedder

    def is_chunk_relevant(
        self,
        query: str,
        chunk: RetrievedChunk,
        check_cosine: bool = False,
    ) -> bool:
        """
        Verify whether a single retrieved chunk satisfies relevance thresholds.

        Args:
            query: The user search query.
            chunk: RetrievedChunk candidate.
            check_cosine: Whether to compute dense vector cosine similarity.

        Returns:
            bool: True if chunk satisfies relevance criteria, False otherwise.
        """
        if not chunk or not chunk.text or not chunk.text.strip():
            return False

        # 1. Primary Gate: Cross-encoder / reranker confidence score
        if chunk.score < self.min_rerank_score:
            return False

        # 2. Optional Secondary Gate: Dense vector cosine similarity
        if check_cosine and self.embedder is not None and query and query.strip():
            try:
                q_vec = self.embedder.encode(query.strip())[0]
                c_vec = self.embedder.encode(chunk.text.strip())[0]
                sim = BGEEmbedder.compute_similarity(q_vec, c_vec)
                if sim < self.min_cosine_sim:
                    return False
            except Exception:
                pass

        return True

    def filter_chunks(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        check_cosine: bool = False,
    ) -> tuple[list[RetrievedChunk], bool]:
        """
        Filter candidate chunks against quality thresholds and assess sufficiency.

        Args:
            query: The user search query.
            chunks: Candidate chunks (top-3 from reranker).
            check_cosine: Whether to explicitly compute dense cosine similarity.

        Returns:
            tuple[list[RetrievedChunk], bool]:
                - list of filtered, relevant chunks
                - is_sufficient (True if at least one high-confidence chunk exists)
        """
        if not query or not query.strip() or not chunks:
            return [], False

        passed_chunks: list[RetrievedChunk] = []

        for chunk in chunks:
            if self.is_chunk_relevant(query, chunk, check_cosine=check_cosine):
                passed_chunks.append(chunk)

        is_sufficient = len(passed_chunks) > 0
        return passed_chunks, is_sufficient
