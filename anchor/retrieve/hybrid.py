"""
hybrid.py — Multi-Store Hybrid Retrieval Engine (Dense LanceDB + Sparse Tantivy + RRF Fusion)
"""

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Any, Optional

from anchor.config import settings
from anchor.models.embedder import BGEEmbedder
from anchor.stores.lancedb_store import query_vector
from anchor.stores.tantivy_store import search_bm25


@dataclass
class RetrievedChunk:
    """Standardized retrieved regulatory chunk with RRF score and provenance metadata."""

    chunk_id: str
    doc_id: str
    schedule_no: int
    section: str
    breadcrumb: str
    page_no: int
    bbox: list[float]
    text: str
    sha256: str
    score: float
    dense_rank: Optional[int] = None
    sparse_rank: Optional[int] = None
    publish_year: int = 2026
    conflict_flag: bool = False
    precedence_note: Optional[str] = None


class HybridRetriever:
    """
    Multi-store hybrid retrieval engine:
    - Dense vector search via LanceDB (1024-d BGE-M3 embeddings)
    - Sparse lexical search via Tantivy (stemmed BM25)
    - Reciprocal Rank Fusion (RRF k=60)
    - Temporal weighting multiplier (1.5x for post-2024 documents)
    """

    def __init__(
        self,
        embedder: Optional[BGEEmbedder] = None,
        lancedb_dir: Optional[Path] = None,
        tantivy_dir: Optional[Path] = None,
        rrf_k: int = 60,
        temporal_multiplier: float = 1.5,
    ) -> None:
        self._embedder = embedder
        self.lancedb_dir = lancedb_dir or settings.LANCEDB_DIR
        self.tantivy_dir = tantivy_dir or settings.TANTIVY_DIR
        self.rrf_k = rrf_k
        self.temporal_multiplier = temporal_multiplier

    @property
    def embedder(self) -> BGEEmbedder:
        """Lazy load BGE-M3 embedder on demand."""
        if self._embedder is None:
            self._embedder = BGEEmbedder()
        return self._embedder

    @staticmethod
    def infer_publish_year(doc_id: str, breadcrumb: str = "") -> int:
        """Infer document publication year from doc_id or breadcrumb."""
        text = f"{doc_id} {breadcrumb}".lower()
        if "2026" in text or "dfpds" in text:
            return 2026
        if "2025" in text or "dpm" in text:
            return 2025
        if "2009" in text:
            return 2009
        if "navy_regs" in text or "navy regs" in text:
            return 2020
        return 2026

    def dense_search(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
        """Execute 1024-d dense vector search on LanceDB."""
        if not query or not query.strip():
            return []

        query_vec = self.embedder.encode(query.strip())[0].tolist()
        try:
            return query_vector(query_vec, top_k=top_k, db_dir=self.lancedb_dir)
        except Exception:
            return []

    def sparse_search(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
        """Execute BM25 lexical search on Tantivy index."""
        if not query or not query.strip():
            return []

        try:
            return search_bm25(query.strip(), top_k=top_k, index_dir=self.tantivy_dir)
        except Exception:
            return []

    def reciprocal_rank_fusion(
        self,
        dense_hits: list[dict[str, Any]],
        sparse_hits: list[dict[str, Any]],
        k: Optional[int] = None,
    ) -> list[RetrievedChunk]:
        """
        Merge ranked dense and sparse search results using Reciprocal Rank Fusion (RRF).

        RRF_Score(d) = sum(1 / (k + rank_m(d))) for m in {dense, sparse}
        """
        smooth_k = k or self.rrf_k
        chunk_map: dict[str, dict[str, Any]] = {}
        rrf_scores: dict[str, float] = {}
        dense_ranks: dict[str, int] = {}
        sparse_ranks: dict[str, int] = {}

        # 1. Process dense rankings (1-based rank)
        for rank, hit in enumerate(dense_hits, start=1):
            cid = str(hit.get("chunk_id", ""))
            if not cid:
                continue
            dense_ranks[cid] = rank
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (smooth_k + rank)
            if cid not in chunk_map:
                chunk_map[cid] = hit

        # 2. Process sparse rankings (1-based rank)
        for rank, hit in enumerate(sparse_hits, start=1):
            cid = str(hit.get("chunk_id", ""))
            if not cid:
                continue
            sparse_ranks[cid] = rank
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (smooth_k + rank)
            if cid not in chunk_map:
                chunk_map[cid] = hit

        # 3. Construct unified RetrievedChunk list
        merged_chunks: list[RetrievedChunk] = []
        for cid, raw_hit in chunk_map.items():
            doc_id = str(raw_hit.get("doc_id", ""))
            breadcrumb = str(raw_hit.get("breadcrumb", ""))
            year = self.infer_publish_year(doc_id, breadcrumb)

            bbox_raw = raw_hit.get("bbox", [0.0, 0.0, 0.0, 0.0])
            if isinstance(bbox_raw, list):
                bbox = [float(x) for x in bbox_raw]
            else:
                bbox = [0.0, 0.0, 0.0, 0.0]

            try:
                s_no = int(raw_hit.get("schedule_no", 0) or 0)
            except (ValueError, TypeError):
                s_no = 0

            try:
                p_no = int(raw_hit.get("page_no", 1) or 1)
            except (ValueError, TypeError):
                p_no = 1

            chunk = RetrievedChunk(
                chunk_id=cid,
                doc_id=doc_id,
                schedule_no=s_no,
                section=str(raw_hit.get("section", "")),
                breadcrumb=breadcrumb,
                page_no=p_no,
                bbox=bbox,
                text=str(raw_hit.get("text", "")),
                sha256=str(raw_hit.get("sha256", "")),
                score=float(rrf_scores.get(cid, 0.0)),
                dense_rank=dense_ranks.get(cid),
                sparse_rank=sparse_ranks.get(cid),
                publish_year=year,
            )
            merged_chunks.append(chunk)

        # Sort descending by fused RRF score
        merged_chunks.sort(key=lambda c: c.score, reverse=True)
        return merged_chunks

    def apply_temporal_weighting(
        self,
        chunks: list[RetrievedChunk],
        multiplier: Optional[float] = None,
    ) -> list[RetrievedChunk]:
        """
        Apply a 1.5x score boost to documents published in 2024 or later (DFPDS-2026, DPM-2025).
        """
        boost = multiplier or self.temporal_multiplier
        weighted_list: list[RetrievedChunk] = []

        for chunk in chunks:
            if chunk.publish_year >= 2024:
                chunk.score = float(chunk.score * boost)
            weighted_list.append(chunk)

        # Re-sort after applying temporal weighting
        weighted_list.sort(key=lambda c: c.score, reverse=True)
        return weighted_list

    def retrieve(self, query: str, top_k: int = 10) -> list[RetrievedChunk]:
        """
        Execute full hybrid retrieval pipeline:
        1. Dense LanceDB vector search (top_k * 2)
        2. Sparse Tantivy BM25 lexical search (top_k * 2)
        3. Reciprocal Rank Fusion (k=60)
        4. Temporal weighting (1.5x post-2024)
        5. Return top_k candidates
        """
        if not query or not query.strip():
            return []

        search_k = max(top_k * 2, 20)
        dense_hits = self.dense_search(query, top_k=search_k)
        sparse_hits = self.sparse_search(query, top_k=search_k)

        fused_chunks = self.reciprocal_rank_fusion(dense_hits, sparse_hits, k=self.rrf_k)
        weighted_chunks = self.apply_temporal_weighting(
            fused_chunks, multiplier=self.temporal_multiplier
        )

        return weighted_chunks[:top_k]
