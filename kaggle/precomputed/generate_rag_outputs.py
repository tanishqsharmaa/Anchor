"""
generate_rag_outputs.py — Precomputed RAG Outputs Generator & Kaggle Submission #2 Formatter
"""

import asyncio
import json
import logging
from pathlib import Path
import sys
import time
from typing import Any

# Ensure Build directory is in sys.path
build_dir = Path(__file__).resolve().parent.parent.parent
if str(build_dir) not in sys.path:
    sys.path.insert(0, str(build_dir))

from anchor.api.routes_query import orchestrator
from anchor.config import settings
from anchor.evals.kaggle_formatter import KaggleRow, export_kaggle_submission_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Standard benchmark queries representing naval procurement compliance scenarios
BENCHMARK_QUERIES: list[dict[str, Any]] = [
    {
        "id": "Q001",
        "question": "What is the financial limit for Chief of the Naval Staff under Schedule 1 with IFA concurrence?",
        "expected_type": "structured",
        "category": "CFA Financial Delegation",
    },
    {
        "id": "Q002",
        "question": "What is the financial power of a Fleet Commander under Schedule 7 for major repairs with IFA?",
        "expected_type": "structured",
        "category": "CFA Financial Delegation",
    },
    {
        "id": "Q003",
        "question": "What is the sanction limit for Commodore under Schedule 18 for communication systems without IFA?",
        "expected_type": "structured",
        "category": "CFA Financial Delegation",
    },
    {
        "id": "Q004",
        "question": "What is the financial threshold for mandatory Open Tender Enquiry (OTE) under DPM-2025?",
        "expected_type": "structured",
        "category": "Procurement Threshold",
    },
    {
        "id": "Q005",
        "question": "What is the standard Performance Bank Guarantee (PBG) percentage required for naval procurement contracts?",
        "expected_type": "structured",
        "category": "Procurement Threshold",
    },
    {
        "id": "Q006",
        "question": "What is the maximum Liquidated Damages (LD) rate and ceiling permitted under DPM-2025 for delivery delays?",
        "expected_type": "structured",
        "category": "Procurement Threshold",
    },
    {
        "id": "Q007",
        "question": "Can a Commanding Officer of a Frigate invoke emergency procurement powers to bypass standard GeM portal rules for urgent propulsion repairs in operational waters?",
        "expected_type": "interpretive",
        "category": "Emergency Powers & GeM Compliance",
    },
    {
        "id": "Q008",
        "question": "Under what specific operational conditions is Single Tender Enquiry (STE) justified for proprietary defence hardware replenishment?",
        "expected_type": "interpretive",
        "category": "Tendering Modes & Single Source",
    },
    {
        "id": "Q009",
        "question": "Explain the statutory conflict resolution hierarchy when DFPDS-2026 delegations overlap with general DPM-2025 procurement procedures.",
        "expected_type": "interpretive",
        "category": "Statutory Precedence & Conflict Resolution",
    },
    {
        "id": "Q010",
        "question": "What are the statutory duties and navigational responsibilities of the Officer of the Watch (OOW) under Navy Regulations Part I?",
        "expected_type": "interpretive",
        "category": "Navy Regulations Governance",
    },
    {
        "id": "Q011",
        "question": "What is the capital budget allocation for INS Vishal aircraft carrier construction in FY 2027?",
        "expected_type": "abstain",
        "category": "Out of Domain Refusal",
    },
    {
        "id": "Q012",
        "question": "What is the financial delegation limit for Vice Chief of Naval Staff under Schedule 99?",
        "expected_type": "abstain",
        "category": "Out of Bounds Schedule",
    },
]


async def run_pipeline_for_query(item: dict[str, Any]) -> tuple[dict[str, Any], KaggleRow]:
    """Execute live query pipeline and construct JSON record and KaggleRow."""
    qid = item["id"]
    question = item["question"]
    logger.info(f"Processing {qid}: '{question[:60]}...'")

    events: list[dict[str, Any]] = []
    final_answer: str = ""
    citations: list[dict[str, Any]] = []
    query_type = "interpretive"
    status_val = "complete"
    reason = None
    explanation = None

    t0 = time.perf_counter()
    async for event_dict in orchestrator.execute_stream(question):
        data_str = event_dict.get("data", "{}")
        parsed = json.loads(data_str)
        stage = parsed.get("stage")
        data = parsed.get("data", {})
        events.append(parsed)

        if stage == "classify":
            query_type = data.get("type", "interpretive")
        elif stage in ("resolve", "complete"):
            final_answer = data.get("answer", "")
            citations = data.get("citations", [])
            status_val = "certified"
        elif stage == "abstain":
            reason = data.get("reason")
            explanation = data.get("explanation")
            status_val = "abstain"
            final_answer = f"[CERTIFIED ABSTENTION: {reason}] {explanation}"

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    # Derive statutory source and section
    pred_source = "DFPDS-2026"
    pred_section = "General Provision"

    if citations:
        pred_source = citations[0].get("document", "DFPDS-2026")
        pred_section = f"Page {citations[0].get('page', 1)}"
    elif query_type == "structured":
        cls_res = orchestrator.classifier.classify(question)
        if cls_res.schedule_no:
            pred_source = f"DFPDS-2026/NAVY/SCH-{cls_res.schedule_no:02d}"
            pred_section = cls_res.tier or "Financial Delegation Table"
        elif cls_res.dpm_mode:
            pred_source = "DPM-2025"
            pred_section = f"Mode: {cls_res.dpm_mode}"

    json_record = {
        "id": qid,
        "question": question,
        "category": item["category"],
        "query_type": query_type,
        "status": status_val,
        "prediction": final_answer,
        "pred_source": pred_source,
        "pred_section": pred_section,
        "citations": citations,
        "reason": reason,
        "explanation": explanation,
        "latency_ms": elapsed_ms,
        "events_count": len(events),
    }

    kaggle_row = KaggleRow(
        id=str(qid),
        prediction=final_answer,
        pred_source=pred_source,
        pred_section=pred_section,
    )

    return json_record, kaggle_row


async def main() -> None:
    """Generate precomputed RAG outputs and export Kaggle submission 2."""
    logger.info("=== PROJECT ANCHOR: Generating Precomputed RAG Outputs for Milestone #2 ===")

    json_results: dict[str, Any] = {}
    kaggle_rows: list[KaggleRow] = []

    for item in BENCHMARK_QUERIES:
        json_rec, k_row = await run_pipeline_for_query(item)
        json_results[item["id"]] = json_rec
        kaggle_rows.append(k_row)

    output_dir = settings.BASE_DIR / "kaggle" / "precomputed"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "rag_outputs.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    logger.info(f"[SUCCESS] Exported RAG precomputed outputs to: {json_path}")

    csv_path = settings.BASE_DIR / "kaggle" / "submission_2.csv"
    export_kaggle_submission_csv(kaggle_rows, csv_path)
    logger.info(f"[SUCCESS] Exported Kaggle Submission #2 CSV to: {csv_path}")


if __name__ == "__main__":
    asyncio.run(main())
