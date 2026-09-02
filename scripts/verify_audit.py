"""
verify_audit.py — Audit Log Export & Integrity Verification CLI (ENH-017)
Cryptographically verifies SHA-256 tamper seals for all audit entries in SQLite
and provides JSON / CSV export capabilities for naval statutory compliance officers.
"""

import argparse
import csv
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from anchor.config import settings
from anchor.trust.audit import AuditLogger, AuditRecord


def verify_and_export_audit_logs(
    db_path: Path,
    export_json: Path | None = None,
    export_csv: Path | None = None,
) -> int:
    """
    Verify all audit records in database and optionally export report.
    Returns 0 if all verified, 1 if tampering or errors detected.
    """
    if not db_path.exists():
        print(f"[ERROR] Database file not found: {db_path}", file=sys.stderr)
        return 1

    audit_logger = AuditLogger(db_path=db_path)
    records = audit_logger.get_all_records()
    total_count = len(records)

    print("=" * 80)
    print("PROJECT ANCHOR — DEFENSE AUDIT LEDGER INTEGRITY VERIFIER")
    print("=" * 80)
    print(f"Target Database: {db_path}")
    print(f"Total Audit Records: {total_count}")
    print("-" * 80)

    if total_count == 0:
        print("[INFO] Ledger is currently empty (0 records).")
        return 0

    valid_count = 0
    corrupted_records: list[dict] = []
    verified_records: list[dict] = []

    for r in records:
        is_valid = audit_logger.verify_record_integrity(r)
        rec_data = r.to_dict()
        rec_data["tamper_seal_valid"] = is_valid

        if is_valid:
            valid_count += 1
            verified_records.append(rec_data)
        else:
            corrupted_records.append(rec_data)
            print(f"[SECURITY ALERT] Tamper seal mismatch on Query ID: {r.query_id} (ID: {r.id})")

    print("-" * 80)
    print(f"Verified Valid Records:    {valid_count} / {total_count} ({valid_count / total_count * 100:.1f}%)")
    print(f"Tampered/Corrupt Records:  {len(corrupted_records)}")

    # Export to JSON
    if export_json:
        export_json.parent.mkdir(parents=True, exist_ok=True)
        with open(export_json, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "total_records": total_count,
                    "valid_count": valid_count,
                    "tampered_count": len(corrupted_records),
                    "records": verified_records + corrupted_records,
                },
                f,
                indent=2,
            )
        print(f"[EXPORT] JSON audit report written to: {export_json}")

    # Export to CSV
    if export_csv:
        export_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(export_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "query_id", "timestamp", "session_id", "question", "answer",
                "route_type", "abstained", "refusal_reason", "execution_time_ms",
                "integrity_hash", "tamper_seal_valid"
            ])
            for r in verified_records + corrupted_records:
                writer.writerow([
                    r["id"], r["query_id"], r["timestamp"], r["session_id"],
                    r["question"], r["answer"], r["route_type"], r["abstained"],
                    r["refusal_reason"], r["execution_time_ms"], r["integrity_hash"],
                    r["tamper_seal_valid"]
                ])
        print(f"[EXPORT] CSV audit report written to: {export_csv}")

    print("=" * 80)
    if len(corrupted_records) > 0:
        print("[VERDICT] AUDIT INTEGRITY CHECK FAILED — CORRUPTED RECORDS DETECTED", file=sys.stderr)
        return 1
    else:
        print("[VERDICT] AUDIT LEDGER CRYPTOGRAPHICALLY VERIFIED — 100% INTEGRITY")
        return 0


def main():
    parser = argparse.ArgumentParser(description="PROJECT ANCHOR Audit Ledger Integrity Verification CLI")
    parser.add_argument("--db", type=Path, default=settings.SQLITE_PATH, help="Path to SQLite database")
    parser.add_argument("--export", type=Path, default=None, help="Export verified audit log to JSON file")
    parser.add_argument("--export-csv", type=Path, default=None, help="Export verified audit log to CSV file")
    args = parser.parse_args()

    exit_code = verify_and_export_audit_logs(
        db_path=args.db,
        export_json=args.export,
        export_csv=args.export_csv,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
