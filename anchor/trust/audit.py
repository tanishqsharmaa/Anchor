"""
audit.py — Append-Only SQLite Audit Ledger with Cryptographic SHA-256 Provenance & Trigger Immutability.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hmac
import json
from pathlib import Path
import sqlite3
from typing import Any, Optional, Union
import uuid

from anchor.config import settings
from anchor.stores.sqlite_store import get_sqlite_connection
from anchor.trust.hash import compute_sha256, verify_sha256


@dataclass
class AuditRecord:
    """Immutable audit record representing a single query execution."""

    id: Optional[int]
    query_id: str
    timestamp: str
    session_id: str
    question: str
    answer: str
    citations_json: str
    nli_scores_json: str
    route_type: str
    abstained: bool
    refusal_reason: Optional[str]
    execution_time_ms: float
    integrity_hash: str

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary."""
        return asdict(self)


class AuditLogger:
    """
    Append-only defense-grade audit ledger for PROJECT ANCHOR.
    Enforces SQLite trigger-level immutability (rejects UPDATE and DELETE)
    and session-signed SHA-256 integrity hash verification.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        session_id: Optional[str] = None,
        auto_init: bool = True,
    ) -> None:
        self.db_path = db_path or settings.SQLITE_PATH
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:12]}"
        self._initialized = False
        if auto_init:
            self.init_audit_table()

    def _get_connection(self) -> sqlite3.Connection:
        """Obtain a database connection with WAL mode configured."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        return get_sqlite_connection(self.db_path)

    def _ensure_table(self) -> None:
        """Ensure audit table is created before read/write operations."""
        if not self._initialized:
            self.init_audit_table()

    def init_audit_table(self) -> None:
        """Initialize audit_log table and immutable trigger constraints."""
        conn = self._get_connection()
        with conn:
            # 1. Audit Ledger Table DDL
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    citations_json TEXT NOT NULL,
                    nli_scores_json TEXT NOT NULL,
                    route_type TEXT NOT NULL,
                    abstained INTEGER NOT NULL,
                    refusal_reason TEXT,
                    execution_time_ms REAL NOT NULL,
                    integrity_hash TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_query_id ON audit_log(query_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);")

            # 2. Immutable UPDATE Trigger
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS prevent_audit_update
                BEFORE UPDATE ON audit_log
                BEGIN
                    SELECT RAISE(FAIL, 'AUDIT_LOG_IMMUTABLE: UPDATE operations are strictly prohibited on defense audit ledger.');
                END;
                """
            )

            # 3. Immutable DELETE Trigger
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
                BEFORE DELETE ON audit_log
                BEGIN
                    SELECT RAISE(FAIL, 'AUDIT_LOG_IMMUTABLE: DELETE operations are strictly prohibited on defense audit ledger.');
                END;
                """
            )
        conn.close()
        self._initialized = True

    @staticmethod
    def compute_integrity_hash(
        query_id: str,
        timestamp: str,
        session_id: str,
        question: str,
        answer: str,
        citations_json: str,
        nli_scores_json: str,
        route_type: str,
        abstained: bool,
        refusal_reason: Optional[str],
        execution_time_ms: float,
    ) -> str:
        """
        Compute canonical SHA-256 integrity hash linking all transaction parameters.
        """
        canonical_payload = (
            f"query_id={query_id}|"
            f"timestamp={timestamp}|"
            f"session_id={session_id}|"
            f"question={question.strip()}|"
            f"answer={answer.strip()}|"
            f"citations={citations_json.strip()}|"
            f"nli={nli_scores_json.strip()}|"
            f"route={route_type}|"
            f"abstained={1 if abstained else 0}|"
            f"reason={refusal_reason or ''}|"
            f"latency={execution_time_ms:.2f}"
        )
        return compute_sha256(canonical_payload)

    def record_query(
        self,
        query_id: str,
        question: str,
        answer: str,
        citations: Union[list[dict[str, Any]], str],
        nli_scores: Union[list[dict[str, Any]], list[float], str],
        route_type: str = "interpretive",
        abstained: bool = False,
        refusal_reason: Optional[str] = None,
        execution_time_ms: float = 0.0,
        timestamp: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AuditRecord:
        """
        Record a query execution in the append-only audit ledger.
        """
        self._ensure_table()
        rec_time = timestamp or datetime.now(timezone.utc).isoformat()
        rec_session = session_id or self.session_id

        citations_str = citations if isinstance(citations, str) else json.dumps(citations, sort_keys=True)
        nli_str = nli_scores if isinstance(nli_scores, str) else json.dumps(nli_scores, sort_keys=True)

        integrity_hash = self.compute_integrity_hash(
            query_id=query_id,
            timestamp=rec_time,
            session_id=rec_session,
            question=question,
            answer=answer,
            citations_json=citations_str,
            nli_scores_json=nli_str,
            route_type=route_type,
            abstained=abstained,
            refusal_reason=refusal_reason,
            execution_time_ms=execution_time_ms,
        )

        conn = self._get_connection()
        record_id: Optional[int] = None
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_log (
                    query_id, timestamp, session_id, question, answer,
                    citations_json, nli_scores_json, route_type, abstained,
                    refusal_reason, execution_time_ms, integrity_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    query_id,
                    rec_time,
                    rec_session,
                    question,
                    answer,
                    citations_str,
                    nli_str,
                    route_type,
                    1 if abstained else 0,
                    refusal_reason,
                    execution_time_ms,
                    integrity_hash,
                ),
            )
            record_id = cursor.lastrowid
        conn.close()

        return AuditRecord(
            id=record_id,
            query_id=query_id,
            timestamp=rec_time,
            session_id=rec_session,
            question=question,
            answer=answer,
            citations_json=citations_str,
            nli_scores_json=nli_str,
            route_type=route_type,
            abstained=abstained,
            refusal_reason=refusal_reason,
            execution_time_ms=execution_time_ms,
            integrity_hash=integrity_hash,
        )

    def get_audit_record(self, query_id: str) -> Optional[AuditRecord]:
        """Retrieve an audit record by its unique query_id."""
        self._ensure_table()
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM audit_log WHERE query_id = ?;", (query_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return AuditRecord(
            id=row["id"],
            query_id=row["query_id"],
            timestamp=row["timestamp"],
            session_id=row["session_id"],
            question=row["question"],
            answer=row["answer"],
            citations_json=row["citations_json"],
            nli_scores_json=row["nli_scores_json"],
            route_type=row["route_type"],
            abstained=bool(row["abstained"]),
            refusal_reason=row["refusal_reason"],
            execution_time_ms=float(row["execution_time_ms"]),
            integrity_hash=row["integrity_hash"],
        )

    def get_audit_record_by_id(self, record_id: int) -> Optional[AuditRecord]:
        """Retrieve an audit record by its integer primary key ID."""
        self._ensure_table()
        conn = self._get_connection()
        cursor = conn.execute("SELECT * FROM audit_log WHERE id = ?;", (record_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return AuditRecord(
            id=row["id"],
            query_id=row["query_id"],
            timestamp=row["timestamp"],
            session_id=row["session_id"],
            question=row["question"],
            answer=row["answer"],
            citations_json=row["citations_json"],
            nli_scores_json=row["nli_scores_json"],
            route_type=row["route_type"],
            abstained=bool(row["abstained"]),
            refusal_reason=row["refusal_reason"],
            execution_time_ms=float(row["execution_time_ms"]),
            integrity_hash=row["integrity_hash"],
        )

    def verify_record_integrity(self, query_id_or_id: Union[str, int]) -> bool:
        """
        Verify cryptographic integrity of an audit record by recomputing its payload hash.
        Returns True if authentic and untampered; False if modified.
        """
        if isinstance(query_id_or_id, int):
            record = self.get_audit_record_by_id(query_id_or_id)
        else:
            record = self.get_audit_record(str(query_id_or_id))

        if not record:
            return False

        recomputed = self.compute_integrity_hash(
            query_id=record.query_id,
            timestamp=record.timestamp,
            session_id=record.session_id,
            question=record.question,
            answer=record.answer,
            citations_json=record.citations_json,
            nli_scores_json=record.nli_scores_json,
            route_type=record.route_type,
            abstained=record.abstained,
            refusal_reason=record.refusal_reason,
            execution_time_ms=record.execution_time_ms,
        )

        return hmac.compare_digest(recomputed.lower(), record.integrity_hash.lower())

    def list_audit_records(self, limit: int = 50, offset: int = 0) -> list[AuditRecord]:
        """List audit records in chronological order with pagination."""
        self._ensure_table()
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM audit_log ORDER BY id ASC LIMIT ? OFFSET ?;",
            (limit, offset),
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            AuditRecord(
                id=row["id"],
                query_id=row["query_id"],
                timestamp=row["timestamp"],
                session_id=row["session_id"],
                question=row["question"],
                answer=row["answer"],
                citations_json=row["citations_json"],
                nli_scores_json=row["nli_scores_json"],
                route_type=row["route_type"],
                abstained=bool(row["abstained"]),
                refusal_reason=row["refusal_reason"],
                execution_time_ms=float(row["execution_time_ms"]),
                integrity_hash=row["integrity_hash"],
            )
            for row in rows
        ]

    def count_audit_records(self) -> int:
        """Return total count of logged audit records."""
        self._ensure_table()
        conn = self._get_connection()
        cursor = conn.execute("SELECT COUNT(*) FROM audit_log;")
        count = cursor.fetchone()[0]
        conn.close()
        return int(count)


# Global singleton instance (lazy initialization)
audit_logger = AuditLogger(auto_init=False)
