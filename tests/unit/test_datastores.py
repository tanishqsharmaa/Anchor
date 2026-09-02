import tempfile
from pathlib import Path
import pytest
import sqlite3
from anchor.config import settings


def test_sqlite_store_schema_and_population(tmp_path):
    from anchor.stores.sqlite_store import (
        init_sqlite_db,
        populate_sqlite_from_schemas,
        query_dfpds,
        get_sqlite_connection,
    )

    test_db = tmp_path / "test_anchor.db"
    init_sqlite_db(test_db)
    
    # Populate with production schemas
    rows_loaded = populate_sqlite_from_schemas(schemas_dir=settings.SCHEMAS_DIR, db_path=test_db)
    assert rows_loaded["dfpds"] == 192  # 32 schedules * 6 tiers
    assert rows_loaded["dpm"] >= 18
    assert rows_loaded["navy_regs"] >= 12

    # Query Schedule 1 - CNS
    results = query_dfpds(schedule_no=1, tier="Tier 1", db_path=test_db)
    assert len(results) == 1
    cns = results[0]
    assert cns["tier_name"] == "Chief of the Naval Staff (CNS)"
    assert cns["with_ifa"] == 120.0
    assert cns["without_ifa"] == 12.0
    assert cns["pac_limit"] == 60.0

    # Query Schedule 7 - Fleet Commander (Tier 3)
    results_sch7 = query_dfpds(schedule_no=7, tier="Tier 3", db_path=test_db)
    assert len(results_sch7) == 1


def test_lancedb_store_schema_and_crud(tmp_path):
    from anchor.stores.lancedb_store import (
        init_lancedb_table,
        insert_chunks,
        query_vector,
        count_chunks,
    )

    test_lancedb_dir = tmp_path / "lancedb"
    table = init_lancedb_table(db_dir=test_lancedb_dir)
    assert table is not None

    # Create 2 sample dummy chunks with 1024-d vectors
    vec1 = [0.1] * 1024
    vec2 = [-0.1] * 1024

    sample_chunks = [
        {
            "chunk_id": "DFPDS/SCH-01/C01",
            "doc_id": "DFPDS_2026_Schedule_01",
            "schedule_no": 1,
            "section": "Schedule 01",
            "page_no": 1,
            "bbox": [50.0, 100.0, 500.0, 200.0],
            "text": "Chief of the Naval Staff financial powers under Schedule 01.",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "vector": vec1,
        },
        {
            "chunk_id": "DPM/CH-01/C01",
            "doc_id": "DPM_2025_Chapter_01",
            "schedule_no": 0,
            "section": "Chapter 01",
            "page_no": 1,
            "bbox": [50.0, 100.0, 500.0, 200.0],
            "text": "General principles of Defence Procurement Manual 2025.",
            "sha256": "a3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "vector": vec2,
        },
    ]

    inserted = insert_chunks(sample_chunks, db_dir=test_lancedb_dir)
    assert inserted == 2
    assert count_chunks(db_dir=test_lancedb_dir) == 2

    # Query nearest neighbor for vec1
    search_res = query_vector(vector=vec1, top_k=1, db_dir=test_lancedb_dir)
    assert len(search_res) == 1
    assert search_res[0]["chunk_id"] == "DFPDS/SCH-01/C01"


def test_tantivy_store_schema_and_search(tmp_path):
    from anchor.stores.tantivy_store import (
        get_or_create_tantivy_index,
        add_documents,
        search_bm25,
        count_documents,
    )

    test_tantivy_dir = tmp_path / "tantivy"
    idx = get_or_create_tantivy_index(index_dir=test_tantivy_dir)
    assert idx is not None

    sample_docs = [
        {
            "chunk_id": "DFPDS/SCH-07/C01",
            "doc_id": "DFPDS_2026_Schedule_07",
            "section": "Schedule 07",
            "breadcrumb": "DFPDS-2026/Schedule_07/Tactical_Drones",
            "text": "Procurement of tactical unmanned aerial vehicles and drones for naval surveillance.",
            "schedule_no": 7,
            "sha256": "f3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
        {
            "chunk_id": "DPM/CH-03/C01",
            "doc_id": "DPM_2025_Chapter_03",
            "section": "Chapter 03",
            "breadcrumb": "DPM-2025/Chapter_03/PAC",
            "text": "Proprietary Article Certificate PAC rules for sole source procurement.",
            "schedule_no": 0,
            "sha256": "c3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        },
    ]

    added = add_documents(sample_docs, index_dir=test_tantivy_dir)
    assert added == 2
    assert count_documents(index_dir=test_tantivy_dir) == 2

    # BM25 Search
    results = search_bm25("drones surveillance", top_k=2, index_dir=test_tantivy_dir)
    assert len(results) >= 1
    assert results[0]["chunk_id"] == "DFPDS/SCH-07/C01"
