"""
chunker.py — Semantic-Aware Regulatory Token Chunker with SHA-256 Byte Anchors
"""

from dataclasses import dataclass, field
import hashlib
from typing import Optional
from anchor.ingest.clause_parser import ParsedHierarchy, ClauseNode


@dataclass
class RegulatoryChunk:
    """Represents an atomic, cryptographically anchored chunk ready for indexing."""
    chunk_id: str
    doc_id: str
    schedule_no: int
    section: str
    breadcrumb: str
    page_no: int
    bbox: list[float]  # [x0, y0, x1, y1]
    text: str
    sha256: str
    token_count: int

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "schedule_no": self.schedule_no,
            "section": self.section,
            "breadcrumb": self.breadcrumb,
            "page_no": self.page_no,
            "bbox": self.bbox,
            "text": self.text,
            "sha256": self.sha256,
            "token_count": self.token_count,
        }


def _estimate_token_count(text: str) -> int:
    """Estimate token count using whitespace and punctuation heuristics (~1.3 tokens/word)."""
    words = text.strip().split()
    if not words:
        return 0
    return max(len(words), int(len(words) * 1.3))


def _combine_bboxes(bboxes: list[tuple[float, float, float, float]]) -> list[float]:
    """Calculate the bounding box union [min_x0, min_y0, max_x1, max_y1]."""
    valid = [b for b in bboxes if len(b) == 4 and (b[2] > b[0] or b[3] > b[1])]
    if not valid:
        return [0.0, 0.0, 100.0, 100.0]
    min_x0 = min(b[0] for b in valid)
    min_y0 = min(b[1] for b in valid)
    max_x1 = max(b[2] for b in valid)
    max_y1 = max(b[3] for b in valid)
    return [float(min_x0), float(min_y0), float(max_x1), float(max_y1)]


def chunk_regulatory_hierarchy(
    hierarchy: ParsedHierarchy,
    min_tokens: int = 64,
    max_tokens: int = 512,
    overlap_tokens: int = 64,
) -> list[RegulatoryChunk]:
    """
    Chunk parsed regulatory clauses into token-bounded semantic units (256-512 tokens)
    with 64-token overlap and cryptographic SHA-256 byte anchors.

    Args:
        hierarchy: ParsedHierarchy containing flat clause blocks.
        min_tokens: Target minimum token length when merging small clauses.
        max_tokens: Maximum allowed token window per chunk.
        overlap_tokens: Sliding token overlap for multi-chunk splits.

    Returns:
        List of RegulatoryChunk objects with deterministic hashes.
    """
    doc_id = hierarchy.doc_id
    chunks: list[RegulatoryChunk] = []
    chunk_counter = 1

    current_texts: list[str] = []
    current_bboxes: list[tuple[float, float, float, float]] = []
    current_breadcrumb = ""
    current_schedule_no = 0
    current_section = ""
    current_page = 1
    current_token_count = 0

    def flush_current():
        nonlocal chunk_counter, current_texts, current_bboxes, current_breadcrumb
        nonlocal current_schedule_no, current_section, current_page, current_token_count

        if not current_texts:
            return

        combined_text = "\n".join(current_texts).strip()
        if not combined_text:
            current_texts = []
            current_bboxes = []
            current_token_count = 0
            return

        sha256_hash = hashlib.sha256(combined_text.encode("utf-8")).hexdigest()
        chunk_id = f"{doc_id}_chunk_{chunk_counter:04d}"
        bbox_union = _combine_bboxes(current_bboxes)

        chunk = RegulatoryChunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            schedule_no=current_schedule_no,
            section=current_section or "Clause",
            breadcrumb=current_breadcrumb or doc_id,
            page_no=current_page,
            bbox=bbox_union,
            text=combined_text,
            sha256=sha256_hash,
            token_count=current_token_count,
        )
        chunks.append(chunk)
        chunk_counter += 1

        current_texts = []
        current_bboxes = []
        current_token_count = 0

    for clause in hierarchy.flat_clauses:
        clause_text = clause.text.strip()
        if not clause_text:
            continue

        clause_tokens = _estimate_token_count(clause_text)

        # If a single clause exceeds max_tokens, split it using sliding window
        if clause_tokens > max_tokens:
            flush_current()
            words = clause_text.split()
            step = max(1, max_tokens - overlap_tokens)
            for start_idx in range(0, len(words), step):
                window_words = words[start_idx : start_idx + max_tokens]
                if not window_words:
                    continue
                window_text = " ".join(window_words)
                sha256_hash = hashlib.sha256(window_text.encode("utf-8")).hexdigest()
                chunk_id = f"{doc_id}_chunk_{chunk_counter:04d}"

                chunk = RegulatoryChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    schedule_no=clause.schedule_no,
                    section=clause.title[:60] or "Clause",
                    breadcrumb=clause.breadcrumb,
                    page_no=clause.page_no,
                    bbox=[float(x) for x in clause.bbox],
                    text=window_text,
                    sha256=sha256_hash,
                    token_count=_estimate_token_count(window_text),
                )
                chunks.append(chunk)
                chunk_counter += 1
                if start_idx + max_tokens >= len(words):
                    break
            continue

        # If adding this clause exceeds max_tokens, flush previous accumulator
        if current_texts and (current_token_count + clause_tokens > max_tokens):
            flush_current()

        # Start new or append to accumulator
        if not current_texts:
            current_breadcrumb = clause.breadcrumb
            current_schedule_no = clause.schedule_no
            current_section = clause.title[:60]
            current_page = clause.page_no

        current_texts.append(clause_text)
        current_bboxes.append(clause.bbox)
        current_token_count += clause_tokens

        # If accumulator is large enough, flush it
        if current_token_count >= min_tokens:
            flush_current()

    flush_current()
    return chunks
