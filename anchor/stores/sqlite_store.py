import json
from pathlib import Path
import sqlite3
from typing import Any, Optional

from anchor.config import settings


def get_sqlite_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a SQLite connection configured with WAL mode and Row factory."""
    target_path = db_path or settings.SQLITE_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_sqlite_db(db_path: Optional[Path] = None) -> None:
    """Initialize DDL tables for DFPDS-2026, DPM-2025, and Navy Regulations."""
    conn = get_sqlite_connection(db_path)
    with conn:
        # 1. DFPDS-2026 Structured Delegations
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dfpds_2026 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_no INTEGER NOT NULL,
                schedule_name TEXT NOT NULL,
                reference TEXT NOT NULL,
                gazette_notification TEXT,
                effective_date TEXT,
                tier TEXT NOT NULL,
                tier_name TEXT NOT NULL,
                with_ifa REAL NOT NULL,
                without_ifa REAL NOT NULL,
                pac_limit REAL NOT NULL,
                notes TEXT,
                UNIQUE(schedule_no, tier)
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dfpds_sched_tier ON dfpds_2026(schedule_no, tier);")

        # 2. DPM-2025 Procurement Clauses
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dpm_2025 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_no INTEGER NOT NULL,
                chapter_title TEXT NOT NULL,
                reference TEXT NOT NULL,
                clause_no INTEGER NOT NULL,
                clause_text TEXT NOT NULL,
                UNIQUE(chapter_no, clause_no)
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dpm_chapter ON dpm_2025(chapter_no);")

        # 3. Navy Regulations Statutory Articles
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS navy_regs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_no INTEGER NOT NULL,
                part_title TEXT NOT NULL,
                reference TEXT NOT NULL,
                article_no TEXT NOT NULL,
                article_title TEXT NOT NULL,
                article_text TEXT NOT NULL,
                UNIQUE(part_no, article_no)
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_navyregs_part_art ON navy_regs(part_no, article_no);")

        # 4. PDF Ingestion Manifest Table (ENH-022)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS pdf_manifest (
                filename TEXT PRIMARY KEY,
                sha256 TEXT NOT NULL,
                last_indexed_at TEXT NOT NULL,
                chunk_count INTEGER NOT NULL
            );
            """
        )
    conn.close()


def get_manifest_entry(filename: str, db_path: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """Retrieve PDF manifest metadata entry by filename (ENH-022)."""
    conn = get_sqlite_connection(db_path)
    cursor = conn.execute("SELECT * FROM pdf_manifest WHERE filename = ?;", (filename,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_manifest_entry(
    filename: str, sha256: str, chunk_count: int, db_path: Optional[Path] = None
) -> None:
    """Insert or update PDF manifest metadata entry with UTC timestamp (ENH-022)."""
    from datetime import datetime, timezone

    conn = get_sqlite_connection(db_path)
    now_ts = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO pdf_manifest (filename, sha256, last_indexed_at, chunk_count)
            VALUES (?, ?, ?, ?);
            """,
            (filename, sha256, now_ts, chunk_count),
        )
    conn.close()


def clear_manifest(db_path: Optional[Path] = None) -> None:
    """Clear all PDF manifest records (ENH-022)."""
    conn = get_sqlite_connection(db_path)
    with conn:
        conn.execute("DELETE FROM pdf_manifest;")
    conn.close()


def populate_sqlite_from_schemas(
    schemas_dir: Optional[Path] = None, db_path: Optional[Path] = None
) -> dict[str, int]:
    """Ingest JSON schemas and populate SQLite tables."""
    target_schemas = schemas_dir or settings.SCHEMAS_DIR
    init_sqlite_db(db_path)
    conn = get_sqlite_connection(db_path)

    counts = {"dfpds": 0, "dpm": 0, "navy_regs": 0}

    with conn:
        # 1. DFPDS-2026
        dfpds_file = target_schemas / "dfpds_2026.json"
        if dfpds_file.exists():
            with open(dfpds_file, "r", encoding="utf-8") as f:
                dfpds_data = json.load(f)
            for sch in dfpds_data:
                sch_no = sch.get("schedule_no", 1)
                sch_name = sch.get("schedule_name", "")
                ref = sch.get("reference", "")
                notif = sch.get("gazette_notification", "")
                eff_date = sch.get("effective_date", "")

                for t in sch.get("tiers", []):
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO dfpds_2026 (
                            schedule_no, schedule_name, reference, gazette_notification,
                            effective_date, tier, tier_name, with_ifa, without_ifa, pac_limit, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            sch_no,
                            sch_name,
                            ref,
                            notif,
                            eff_date,
                            t.get("tier", ""),
                            t.get("tier_name", ""),
                            float(t.get("with_ifa", 0.0)),
                            float(t.get("without_ifa", 0.0)),
                            float(t.get("pac_limit", 0.0)),
                            t.get("notes", ""),
                        ),
                    )
                    counts["dfpds"] += 1

        # 2. DPM-2025
        dpm_file = target_schemas / "dpm_2025.json"
        if dpm_file.exists():
            with open(dpm_file, "r", encoding="utf-8") as f:
                dpm_data = json.load(f)
            for ch in dpm_data:
                ch_no = ch.get("chapter_no", 1)
                ch_title = ch.get("chapter_title", "")
                ref = ch.get("reference", "")
                for idx, clause in enumerate(ch.get("clauses", []), start=1):
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO dpm_2025 (
                            chapter_no, chapter_title, reference, clause_no, clause_text
                        ) VALUES (?, ?, ?, ?, ?);
                        """,
                        (ch_no, ch_title, ref, idx, clause),
                    )
                    counts["dpm"] += 1

        # 3. Navy Regulations
        navy_file = target_schemas / "navy_regs.json"
        if navy_file.exists():
            with open(navy_file, "r", encoding="utf-8") as f:
                navy_data = json.load(f)
            for part in navy_data:
                part_no = part.get("part_no", 1)
                part_title = part.get("part_title", "")
                ref = part.get("reference", "")
                for art in part.get("articles", []):
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO navy_regs (
                            part_no, part_title, reference, article_no, article_title, article_text
                        ) VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (
                            part_no,
                            part_title,
                            ref,
                            art.get("article_no", ""),
                            art.get("title", ""),
                            art.get("text", ""),
                        ),
                    )
                    counts["navy_regs"] += 1

    conn.close()
    return counts


def query_dfpds(
    schedule_no: int, tier: Optional[str] = None, db_path: Optional[Path] = None
) -> list[dict[str, Any]]:
    """Query DFPDS delegations by schedule number and optional tier."""
    conn = get_sqlite_connection(db_path)
    if tier:
        cursor = conn.execute(
            "SELECT * FROM dfpds_2026 WHERE schedule_no = ? AND (tier = ? OR tier_name LIKE ?);",
            (schedule_no, tier, f"%{tier}%"),
        )
    else:
        cursor = conn.execute(
            "SELECT * FROM dfpds_2026 WHERE schedule_no = ? ORDER BY id ASC;",
            (schedule_no,),
        )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def query_dpm(chapter_no: int, db_path: Optional[Path] = None) -> list[dict[str, Any]]:
    """Query DPM clauses by chapter number."""
    conn = get_sqlite_connection(db_path)
    cursor = conn.execute(
        "SELECT * FROM dpm_2025 WHERE chapter_no = ? ORDER BY clause_no ASC;",
        (chapter_no,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def query_navy_regs(
    part_no: int, article_no: Optional[str] = None, db_path: Optional[Path] = None
) -> list[dict[str, Any]]:
    """Query Navy Regulations by part and optional article number."""
    conn = get_sqlite_connection(db_path)
    if article_no:
        cursor = conn.execute(
            "SELECT * FROM navy_regs WHERE part_no = ? AND article_no = ?;",
            (part_no, article_no),
        )
    else:
        cursor = conn.execute(
            "SELECT * FROM navy_regs WHERE part_no = ? ORDER BY id ASC;",
            (part_no,),
        )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
