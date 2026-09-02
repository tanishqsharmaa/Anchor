"""
test_nli_gate.py — Unit Tests for Per-Sentence DeBERTa-v3 NLI Verification Gate
"""

from unittest.mock import MagicMock
import pytest

from anchor.generate.nli_gate import NLIGate, SentenceVerification
from anchor.generate.synthesizer import Synthesizer
from anchor.models.nli_model import DeBERTaNLI
from anchor.retrieve.hybrid import RetrievedChunk


@pytest.fixture
def sample_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chk_dfpds_07",
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
    )


def test_nli_gate_atomic_sentence_splitting():
    gate = NLIGate()
    text = (
        "Under DFPDS-2026 Schedule 07, a Fleet Commander may sanction up to Rs. 18.00 Crore with IFA concurrence. "
        "However, without IFA concurrence, the delegated threshold is limited to Rs. 5.00 Crore. "
        "Single Tender Enquiry requires prior approval from the administrative authority."
    )
    sentences = gate.split_atomic_sentences(text)
    assert len(sentences) == 3
    assert "Rs. 18.00 Crore" in sentences[0]
    assert "Rs. 5.00 Crore" in sentences[1]
    assert "Single Tender Enquiry" in sentences[2]


def test_nli_gate_verify_sentence_certified(sample_chunk):
    mock_nli = MagicMock(spec=DeBERTaNLI)
    # High entailment, low contradiction
    mock_nli.predict_batch.return_value = [
        {"entailment": 0.94, "neutral": 0.05, "contradiction": 0.01}
    ]

    gate = NLIGate(nli_model=mock_nli)
    sentence = "A Fleet Commander has financial powers up to Rs 18.00 Crore with IFA concurrence."
    res = gate.verify_sentence(sentence, [sample_chunk])

    assert isinstance(res, SentenceVerification)
    assert res.status == "certified"
    assert res.entailment_score == 0.94
    assert res.best_premise_breadcrumb == "DFPDS-2026/Schedule_07/Tier_3/Fleet_Commander"


def test_nli_gate_verify_sentence_contradiction_triggers_abstain(sample_chunk):
    mock_nli = MagicMock(spec=DeBERTaNLI)
    # High contradiction (> 0.08)
    mock_nli.predict_batch.return_value = [
        {"entailment": 0.05, "neutral": 0.10, "contradiction": 0.85}
    ]

    gate = NLIGate(nli_model=mock_nli)
    sentence = "A Fleet Commander may sanction up to Rs 100.00 Crore without any IFA concurrence."
    res = gate.verify_sentence(sentence, [sample_chunk])

    assert res.status == "abstain"
    assert res.contradiction_score == 0.85


def test_nli_gate_verify_sentence_borderline_triggers_regen(sample_chunk):
    mock_nli = MagicMock(spec=DeBERTaNLI)
    # Borderline entailment (0.50 <= P < 0.85) and low contradiction (<= 0.08)
    mock_nli.predict_batch.return_value = [
        {"entailment": 0.72, "neutral": 0.25, "contradiction": 0.03}
    ]

    gate = NLIGate(nli_model=mock_nli)
    sentence = "Tactical drones might be procured under various schedules."
    res = gate.verify_sentence(sentence, [sample_chunk])

    assert res.status == "regen"
    assert res.entailment_score == 0.72


def test_nli_gate_verify_synthesis_end_to_end_with_regen(sample_chunk):
    mock_nli = MagicMock(spec=DeBERTaNLI)
    # First call: sentence 1 -> certified (0.92), sentence 2 -> regen (0.65)
    # After regen retry: sentence 2 -> certified (0.88)
    mock_nli.predict_batch.side_effect = [
        [{"entailment": 0.92, "neutral": 0.06, "contradiction": 0.02}],  # s1
        [{"entailment": 0.65, "neutral": 0.32, "contradiction": 0.03}],  # s2 initial
        [{"entailment": 0.88, "neutral": 0.10, "contradiction": 0.02}],  # s2 regenerated
    ]

    mock_synth = MagicMock(spec=Synthesizer)
    mock_synth.synthesize.return_value = "The procurement requires IFA concurrence under Schedule 07."

    gate = NLIGate(nli_model=mock_nli)
    raw_text = (
        "Under Schedule 07, Fleet Commander sanctions up to Rs 18.00 Crore with IFA. "
        "Procurement rules apply broadly across sectors."
    )

    verifications, is_grounded, final_text = gate.verify_synthesis(
        text=raw_text,
        chunks=[sample_chunk],
        synthesizer=mock_synth,
        max_regen_attempts=2,
    )

    assert is_grounded is True
    assert len(verifications) == 2
    assert verifications[0].status == "certified"
    assert verifications[1].status == "certified"
    assert "Schedule 07" in final_text
    mock_synth.synthesize.assert_called_once()
