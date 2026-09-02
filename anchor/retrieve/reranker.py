"""
reranker.py — High-Precision Cross-Encoder Candidate Reranker Engine
"""

from typing import Optional
from anchor.config import settings
from anchor.models.reranker_model import BGEReranker
from anchor.retrieve.hybrid import RetrievedChunk


class Reranker:
    """
    Cross-encoder reranking engine utilizing OpenVINO INT8 BGE-Reranker-Large.
    Re-scores candidate chunks from hybrid retrieval, sort descending, and truncates to top-k.
    Preserves all spatial bounding boxes and cryptographic SHA-256 anchors.
    """

    def __init__(self, reranker_model: Optional[BGEReranker] = None) -> None:
        self._model = reranker_model

    @property
    def model(self) -> BGEReranker:
        """Lazy load BGE-Reranker model on demand."""
        if self._model is None:
            self._model = BGEReranker()
        return self._model

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        """
        Re-score candidate chunks using cross-encoder and return top-k sorted descending.

        Args:
            query: The search query string.
            chunks: List of RetrievedChunk candidates (e.g. top-10 from hybrid retrieval).
            top_k: Number of highest-ranked chunks to return (default 3).

        Returns:
            list[RetrievedChunk]: Top-k chunks with updated cross-encoder scores.
        """
        if not chunks or not query or not query.strip():
            return []

        passages = [chunk.text for chunk in chunks]
        scores = self.model.score_batch(query=query.strip(), passages=passages)

        reranked_chunks: list[RetrievedChunk] = []
        for chunk, score in zip(chunks, scores):
            # Create a cloned chunk with the updated cross-encoder score
            updated_chunk = RetrievedChunk(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                schedule_no=chunk.schedule_no,
                section=chunk.section,
                breadcrumb=chunk.breadcrumb,
                page_no=chunk.page_no,
                bbox=list(chunk.bbox),
                text=chunk.text,
                sha256=chunk.sha256,
                score=float(score),
                dense_rank=chunk.dense_rank,
                sparse_rank=chunk.sparse_rank,
                publish_year=chunk.publish_year,
                conflict_flag=chunk.conflict_flag,
                precedence_note=chunk.precedence_note,
            )
            reranked_chunks.append(updated_chunk)

        # Sort descending by cross-encoder score
        reranked_chunks.sort(key=lambda c: c.score, reverse=True)

        return reranked_chunks[:top_k]

    @staticmethod
    def compute_mrr(rankings: list[list[str]], target_ids: list[str]) -> float:
        """
        Compute Mean Reciprocal Rank (MRR) across a set of ranked results and target chunk IDs.
        """
        if not rankings or not target_ids or len(rankings) != len(target_ids):
            return 0.0

        reciprocal_ranks: list[float] = []
        for ranked_list, target in zip(rankings, target_ids):
            try:
                rank = ranked_list.index(target) + 1
                reciprocal_ranks.append(1.0 / rank)
            except ValueError:
                reciprocal_ranks.append(0.0)

        return float(sum(reciprocal_ranks) / len(reciprocal_ranks))
