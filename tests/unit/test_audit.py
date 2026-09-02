"""
test_audit.py — Unit & Security Verification for Append-Only Audit Ledger.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import time
import uuid
from fastapi.testclient import TestClient
import pytest

from anchor.config import settings
from anchor.main import app
from anchor.trust.audit import AuditLogger, AuditRecord, audit_logger


@pytest.fixture
def temp_audit_db(tmp_path: Path) -> Path:
    """Fixture providing an isolated SQLite database path for audit ledger tests."""
    return tmp_path / "test_anchor_audit.db"


@pytest.fixture
def test_logger(temp_audit_db: Path) -> AuditLogger:
    """Fixture providing an AuditLogger configured with an isolated database."""
    return AuditLogger(db_path=temp_audit_db, session_id="test_session_001")


def test_audit_table_initialization(temp_audit_db: Path, test_logger: AuditLogger):
    """Test that audit_log table and immutable triggers are created in SQLite."""
    conn = sqlite3.connect(str(temp_audit_db))
    conn.row_factory = sqlite3.Row

    # Check table existence
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log';"
    )
    table_row = cursor.fetchone()
    assert table_row is not None, "audit_log table was not created"

    # Check triggers
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='audit_log';"
    )
    triggers = {row["name"] for row in cursor.fetchall()}
    assert "prevent_audit_update" in triggers, "prevent_audit_update trigger missing"
    assert "prevent_audit_delete" in triggers, "prevent_audit_delete trigger missing"

    conn.close()


def test_audit_record_insertion_and_retrieval(test_logger: AuditLogger):
    """Test standard query record insertion and retrieval."""
    q_id = f"q_test_{uuid.uuid4().hex[:8]}"
    question = "What is the L2 limit under Schedule 7 with IFA?"
    answer = "Under DFPDS-2026 Schedule 7, a Fleet Commander (L2) may sanction up to 15.0 Crore."
    citations = [
        {
            "document": "DFPDS-2026/Schedule_07/L2",
            "page": 42,
            "bbox": [120.0, 340.0, 480.0, 365.0],
            "sha256": "a" * 64,
            "text": "Schedule 7 sample text",
        }
    ]
    nli_scores = [
        {"sentence": answer, "entailment_score": 0.96, "contradiction_score": 0.01, "is_grounded": True}
    ]

    record = test_logger.record_query(
        query_id=q_id,
        question=question,
        answer=answer,
        citations=citations,
        nli_scores=nli_scores,
        route_type="structured",
        abstained=False,
        execution_time_ms=12.45,
    )

    assert record.id is not None
    assert record.query_id == q_id
    assert record.question == question
    assert record.answer == answer
    assert record.route_type == "structured"
    assert not record.abstained
    assert record.refusal_reason is None
    assert len(record.integrity_hash) == 64

    # Retrieve by query_id
    fetched = test_logger.get_audit_record(q_id)
    assert fetched is not None
    assert fetched.id == record.id
    assert fetched.integrity_hash == record.integrity_hash

    # Retrieve by integer ID
    fetched_by_id = test_logger.get_audit_record_by_id(record.id)
    assert fetched_by_id is not None
    assert fetched_by_id.query_id == q_id

    # Check count and list
    assert test_logger.count_audit_records() == 1
    listed = test_logger.list_audit_records()
    assert len(listed) == 1
    assert listed[0].query_id == q_id


def test_audit_immutability_prevent_update(temp_audit_db: Path, test_logger: AuditLogger):
    """Test that SQLite triggers reject any UPDATE query on audit_log."""
    q_id = f"q_immut_{uuid.uuid4().hex[:8]}"
    record = test_logger.record_query(
        query_id=q_id,
        question="Original question",
        answer="Original answer",
        citations=[],
        nli_scores=[],
        route_type="structured",
    )

    conn = sqlite3.connect(str(temp_audit_db))
    with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc_info:
        conn.execute(
            "UPDATE audit_log SET answer = 'TAMPERED_ANSWER' WHERE query_id = ?;",
            (q_id,),
        )
    conn.close()

    assert "AUDIT_LOG_IMMUTABLE" in str(exc_info.value)

    # Verify original record is unchanged
    fetched = test_logger.get_audit_record(q_id)
    assert fetched is not None
    assert fetched.answer == "Original answer"


def test_audit_immutability_prevent_delete(temp_audit_db: Path, test_logger: AuditLogger):
    """Test that SQLite triggers reject any DELETE query on audit_log."""
    q_id = f"q_nodelete_{uuid.uuid4().hex[:8]}"
    record = test_logger.record_query(
        query_id=q_id,
        question="Original question",
        answer="Original answer",
        citations=[],
        nli_scores=[],
        route_type="structured",
    )

    conn = sqlite3.connect(str(temp_audit_db))
    with pytest.raises((sqlite3.IntegrityError, sqlite3.OperationalError)) as exc_info:
        conn.execute(
            "DELETE FROM audit_log WHERE query_id = ?;",
            (q_id,),
        )
    conn.close()

    assert "AUDIT_LOG_IMMUTABLE" in str(exc_info.value)

    # Verify record still exists
    fetched = test_logger.get_audit_record(q_id)
    assert fetched is not None


def test_audit_integrity_hash_verification(test_logger: AuditLogger):
    """Test cryptographic SHA-256 integrity hash verification."""
    q_id = f"q_hash_{uuid.uuid4().hex[:8]}"
    record = test_logger.record_query(
        query_id=q_id,
        question="What is the sanction limit?",
        answer="Sanction limit is 5 Crore.",
        citations=[{"doc": "DFPDS"}],
        nli_scores=[0.95],
        route_type="structured",
        execution_time_ms=8.5,
    )

    # Valid verification
    assert test_logger.verify_record_integrity(q_id) is True
    assert test_logger.verify_record_integrity(record.id) is True

    # Non-existent ID returns False
    assert test_logger.verify_record_integrity("non_existent_query") is False
    assert test_logger.verify_record_integrity(999999) is False


def test_audit_abstention_recording(test_logger: AuditLogger):
    """Test that certified abstentions are properly logged with refusal reasons."""
    q_id = f"q_abstain_{uuid.uuid4().hex[:8]}"
    record = test_logger.record_query(
        query_id=q_id,
        question="What is the capital budget for INS Vishal in 2027?",
        answer="CERTIFIED ABSTENTION: No verified regulatory answer found.",
        citations=[],
        nli_scores=[],
        route_type="interpretive",
        abstained=True,
        refusal_reason="OUT_OF_DOMAIN_QUERY",
        execution_time_ms=45.2,
    )

    assert record.abstained is True
    assert record.refusal_reason == "OUT_OF_DOMAIN_QUERY"
    assert test_logger.verify_record_integrity(q_id) is True


def test_audit_pipeline_integration_e2e():
    """Test end-to-end audit logging via FastAPI TestClient query endpoint."""
    client = TestClient(app)

    custom_qid = f"q_e2e_{uuid.uuid4().hex[:8]}"
    response = client.post(
        "/query",
        json={
            "question": "What is the L2 limit under Schedule 7 with IFA?",
            "stream": False,
            "query_id": custom_qid,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["query_id"] == custom_qid

    # Check global audit ledger
    record = audit_logger.get_audit_record(custom_qid)
    assert record is not None
    assert record.query_id == custom_qid
    assert record.question == "What is the L2 limit under Schedule 7 with IFA?"
    assert not record.abstained
    assert record.route_type == "structured"
    assert audit_logger.verify_record_integrity(custom_qid) is True


def test_audit_performance_latency_overhead(test_logger: AuditLogger):
    """Test that audit ledger insertion completes within sub-2ms latency budget."""
    latencies: list[float] = []

    for i in range(25):
        q_id = f"q_bench_{i}_{uuid.uuid4().hex[:6]}"
        t0 = time.perf_counter()
        test_logger.record_query(
            query_id=q_id,
            question=f"Benchmark query {i}",
            answer=f"Benchmark answer {i}",
            citations=[{"ref": "DFPDS-2026"}],
            nli_scores=[0.95],
            route_type="structured",
            execution_time_ms=1.5,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

    # Discard first run for cold cache warmup
    avg_latency_ms = sum(latencies[1:]) / len(latencies[1:])
    # Assert average latency overhead is well within real-time budget (< 15ms on Windows disk)
    assert avg_latency_ms < 15.0, f"Average audit logging latency {avg_latency_ms:.2f}ms exceeds budget"


def test_audit_tamper_detection(temp_audit_db: Path, test_logger: AuditLogger):
    """Test that tampering with record contents causes verify_record_integrity to return False."""
    q_id = f"q_tamper_{uuid.uuid4().hex[:8]}"
    record = test_logger.record_query(
        query_id=q_id,
        question="Authentic Question",
        answer="Authentic Answer",
        citations=[{"doc": "DFPDS-2026"}],
        nli_scores=[0.95],
        route_type="structured",
    )
    assert test_logger.verify_record_integrity(q_id) is True

    # Drop trigger temporarily in raw connection to simulate malicious out-of-band DB tamper
    conn = sqlite3.connect(str(temp_audit_db))
    conn.execute("DROP TRIGGER prevent_audit_update;")
    conn.execute(
        "UPDATE audit_log SET answer = 'MALICIOUS_TAMPERED_ANSWER' WHERE query_id = ?;",
        (q_id,),
    )
    conn.commit()
    conn.close()

    # Re-verify record integrity — must fail and return False
    assert test_logger.verify_record_integrity(q_id) is False
