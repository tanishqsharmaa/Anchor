"""
test_synthesis_pipeline.py — Integration Tests for Synthesis, NLI Verification, and Certified Abstention Pipeline
"""

from unittest.mock import MagicMock
import pytest

from anchor.generate.abstention import CertifiedAbstention, RefusalReasonCode
from anchor.generate.nli_gate import NLIGate
from anchor.generate.synthesizer import Synthesizer
from anchor.models.generator import QwenGenerator
from anchor.models.loader import model_orchestrator
from anchor.models.nli_model import DeBERTaNLI
from anchor.retrieve.corrective_gate import CorrectiveGate
from anchor.retrieve.hybrid import RetrievedChunk


@pytest.fixture
def top3_chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id="chk_dfpds_07_1",
            doc_id="DFPDS_2026_Schedule_07.pdf",
            schedule_no=7,
            section="Tier 3",
            breadcrumb="DFPDS-2026/Schedule_07/Tier_3/Fleet_Commander",
            page_no=3,
            bbox=[50.0, 100.0, 450.0, 150.0],
            text="Under Schedule 07 (Procurement of Tactical Drones), a Fleet Commander (Tier 3) is delegated financial powers up to Rs 18.00 Crore with IFA concurrence.",
            sha256="abc123sha256",
            score=0.92,
            dense_rank=1,
            sparse_rank=1,
            publish_year=2026,
            conflict_flag=False,
            precedence_note=None,
        ),
        RetrievedChunk(
            chunk_id="chk_dfpds_07_2",
            doc_id="DFPDS_2026_Schedule_07.pdf",
            schedule_no=7,
            section="Tier 4",
            breadcrumb="DFPDS-2026/Schedule_07/Tier_4/Commodore",
            page_no=3,
            bbox=[50.0, 160.0, 450.0, 200.0],
            text="A Commodore (Tier 4) may sanction expenditure up to Rs 5.00 Crore without IFA concurrence under Schedule 07.",
            sha256="def456sha256",
            score=0.88,
            dense_rank=2,
            sparse_rank=2,
            publish_year=2026,
            conflict_flag=False,
            precedence_note=None,
        ),
    ]


def test_end_to_end_synthesis_and_nli_certification_pipeline(top3_chunks):
    query = "What is the financial power of a Fleet Commander under Schedule 7?"

    # 1. Corrective Gate
    gate = CorrectiveGate(min_rerank_score=0.25)
    filtered_chunks, is_sufficient = gate.filter_chunks(query=query, chunks=top3_chunks)
    assert is_sufficient is True
    assert len(filtered_chunks) == 2

    # 2. Synthesizer
    mock_gen = MagicMock(spec=QwenGenerator)
    mock_gen.generate.return_value = (
        "Under DFPDS-2026 Schedule 07, a Fleet Commander is authorized up to Rs 18.00 Crore with IFA concurrence. "
        "Without IFA concurrence, a Commodore is authorized up to Rs 5.00 Crore."
    )
    synthesizer = Synthesizer(generator=mock_gen)
    raw_synthesis = synthesizer.synthesize(query=query, chunks=filtered_chunks)

    # 3. NLI Gate
    mock_nli = MagicMock(spec=DeBERTaNLI)
    mock_nli.predict_batch.side_effect = [
        # Sentence 1 evaluated against 2 chunks
        [{"entailment": 0.95, "neutral": 0.04, "contradiction": 0.01}, {"entailment": 0.20, "neutral": 0.70, "contradiction": 0.10}],
        # Sentence 2 evaluated against 2 chunks
        [{"entailment": 0.15, "neutral": 0.75, "contradiction": 0.10}, {"entailment": 0.92, "neutral": 0.07, "contradiction": 0.01}],
    ]
    nli_gate = NLIGate(nli_model=mock_nli)
    verifications, is_grounded, final_text = nli_gate.verify_synthesis(
        text=raw_synthesis,
        chunks=filtered_chunks,
        synthesizer=synthesizer,
    )

    assert is_grounded is True
    assert len(verifications) == 2
    assert verifications[0].status == "certified"
    assert verifications[1].status == "certified"
    assert "Rs 18.00 Crore" in final_text
    assert "Rs 5.00 Crore" in final_text


def test_out_of_domain_certified_abstention_pipeline():
    ood_query = "What is the capital budget for INS Vishal in FY 2027?"
    ood_chunks = []

    # 1. Corrective Gate fails on empty context
    gate = CorrectiveGate()
    filtered_chunks, is_sufficient = gate.filter_chunks(query=ood_query, chunks=ood_chunks)
    assert is_sufficient is False

    # 2. Certified Abstention Trigger
    abstain_handler = CertifiedAbstention()
    refusal = abstain_handler.create_refusal(
        query=ood_query,
        code=RefusalReasonCode.OUT_OF_DOMAIN_QUERY,
    )

    assert refusal.is_refusal is True
    assert refusal.code == RefusalReasonCode.OUT_OF_DOMAIN_QUERY
    assert "INS Vishal" in refusal.refusal_message or "INS Vishal" in refusal.explanation

    military_banner = abstain_handler.format_military_refusal(refusal)
    assert "CERTIFIED ABSTENTION" in military_banner


def test_synthesis_pipeline_memory_budget():
    mem_stats = model_orchestrator.get_memory_stats()
    assert mem_stats["peak_ram_within_budget"] is True
    assert mem_stats["process_rss_gb"] <= 12.5
