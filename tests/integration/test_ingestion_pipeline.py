"""
test_ingestion_pipeline.py — End-to-End Ingestion Integration & Seed Retrieval Verification
"""

from pathlib import Path
import pytest
from anchor.config import settings
from anchor.models.embedder import BGEEmbedder
from anchor.ingest.indexer import TripleStoreIndexer
from anchor.stores.lancedb_store import query_vector, count_chunks
from anchor.stores.tantivy_store import search_bm25, count_documents


def test_full_corpus_ingestion_and_seed_retrieval(bge_m3_model_path: Path):
    """
    End-to-end integration test:
    1. Ingests all 46 regulatory PDFs into LanceDB and Tantivy.
    2. Asserts >= 100 chunks successfully indexed.
    3. Verifies top-3 retrieval (dense + BM25) on 5 seed regulatory questions.
    """
    embedder = BGEEmbedder(model_path=bge_m3_model_path)
    indexer = TripleStoreIndexer(embedder=embedder)

    if count_chunks() < 100:
        summary = indexer.index_all_regulatory_pdfs(
            pdfs_dir=settings.PDFS_DIR,
            force_reindex=True,
        )
        assert summary["total_documents"] == 46, f"Expected 46 documents, got {summary['total_documents']}"
        assert summary["total_chunks"] >= 100, f"Expected >= 100 chunks, got {summary['total_chunks']}"

    lancedb_count = count_chunks()
    tantivy_count = count_documents()

    assert lancedb_count >= 100, f"LanceDB count: {lancedb_count}"
    assert tantivy_count >= 100, f"Tantivy count: {tantivy_count}"

    # 5 Seed Regulatory Questions Verification
    seed_queries = [
        # Q1: Schedule 7 Ship Repairs / Fleet Commander
        {
            "query": "What is the financial power of Fleet Commander under Schedule 7 for ship repair with IFA concurrence?",
            "expected_doc": "DFPDS_2026_Schedule_07",
            "bm25_terms": "Ship Repairs Fleet Commander",
        },
        # Q2: Schedule 1 CNS Capital Spares and Armament Stores
        {
            "query": "What is the financial power of Chief of Naval Staff CNS under Schedule 1 for Armament Stores?",
            "expected_doc": "DFPDS_2026_Schedule_01",
            "bm25_terms": "Armament Stores Chief of the Naval Staff CNS",
        },
        # Q3: DPM 2025 Chapter 3 Single Tender Enquiry
        {
            "query": "What is the procedure for Single Tender Enquiry STE under DPM 2025?",
            "expected_doc": "DPM_2025_Chapter_03",
            "bm25_terms": "Single Tender Enquiry DPM",
        },
        # Q4: Schedule 8 Submarine Maintenance and Battery Replenishment
        {
            "query": "What are the financial powers for Submarine Maintenance and Battery Replenishment under Schedule 8?",
            "expected_doc": "DFPDS_2026_Schedule_08",
            "bm25_terms": "Submarine Maintenance Battery Replenishment",
        },
        # Q5: Schedule 3 Marine Commando Equipment
        {
            "query": "What is the financial delegation for Special Operations and Marine Commando Equipment under Schedule 3?",
            "expected_doc": "DFPDS_2026_Schedule_03",
            "bm25_terms": "Marine Commando Equipment Special Operations",
        },
    ]

    for seed in seed_queries:
        query_text = seed["query"]
        expected_doc = seed["expected_doc"]

        # Dense Vector Retrieval Top-3
        q_vec = embedder.encode(query_text)[0].tolist()
        dense_hits = query_vector(q_vec, top_k=3)
        assert len(dense_hits) > 0, f"No dense hits for query: {query_text}"
        dense_doc_ids = [h.get("doc_id", "") for h in dense_hits]

        # BM25 Sparse Search Top-3
        sparse_hits = search_bm25(seed["bm25_terms"], top_k=3)
        assert len(sparse_hits) > 0, f"No BM25 hits for terms: {seed['bm25_terms']}"
        sparse_doc_ids = [h.get("doc_id", "") for h in sparse_hits]

        # At least one retrieval modality must return expected document in top-3
        assert (
            any(expected_doc in d for d in dense_doc_ids) or
            any(expected_doc in d for d in sparse_doc_ids)
        ), f"Failed to retrieve {expected_doc} in top-3 for query '{query_text}'. Dense: {dense_doc_ids}, Sparse: {sparse_doc_ids}"
