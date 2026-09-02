"""
test_indexer.py — Unit Tests for Triple-Store Indexing Engine
"""

from pathlib import Path
from anchor.config import settings
from anchor.models.embedder import BGEEmbedder
from anchor.ingest.indexer import TripleStoreIndexer
from anchor.stores.lancedb_store import query_vector, count_chunks
from anchor.stores.tantivy_store import search_bm25, count_documents


def test_indexer_single_document(bge_m3_model_path: Path):
    """Assert indexing a single PDF writes rows to LanceDB and Tantivy."""
    embedder = BGEEmbedder(model_path=bge_m3_model_path)
    indexer = TripleStoreIndexer(embedder=embedder)

    pdf_path = settings.PDFS_DIR / "DFPDS_2026_Schedule_07.pdf"
    chunks = indexer.index_pdf_document(pdf_path)

    assert len(chunks) > 0
    assert count_chunks() >= len(chunks)
    assert count_documents() >= len(chunks)

    # Test Vector Query Retrieval
    q_vec = embedder.encode("Schedule 07 Ship Repairs Refits Dry-Docking and Hull Preservation")[0].tolist()
    dense_hits = query_vector(q_vec, top_k=5)
    assert len(dense_hits) > 0
    assert any("DFPDS_2026_Schedule_07" in h.get("doc_id", "") for h in dense_hits)

    # Test Tantivy BM25 Keyword Search
    sparse_hits = search_bm25("Schedule 07 Ship Repairs Dry-Docking", top_k=5)
    assert len(sparse_hits) > 0
    assert any("DFPDS_2026_Schedule_07" in h.get("doc_id", "") for h in sparse_hits)
