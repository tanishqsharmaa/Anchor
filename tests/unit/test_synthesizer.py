"""
test_synthesizer.py — Unit Tests for Constrained LLM Synthesizer Engine
"""

from typing import Iterator
from unittest.mock import MagicMock
import pytest

from anchor.generate.synthesizer import Synthesizer
from anchor.models.generator import QwenGenerator
from anchor.retrieve.hybrid import RetrievedChunk


@pytest.fixture
def sample_chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id="chk_001",
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
            chunk_id="chk_002",
            doc_id="DFPDS_2026_Schedule_07.pdf",
            schedule_no=7,
            section="Tier 4",
            breadcrumb="DFPDS-2026/Schedule_07/Tier_4/Commodore",
            page_no=3,
            bbox=[50.0, 160.0, 450.0, 200.0],
            text="A Commodore (Tier 4) may sanction expenditure up to Rs 5.00 Crore without IFA concurrence under Schedule 07.",
            sha256="def456sha256",
            score=0.85,
            dense_rank=2,
            sparse_rank=2,
            publish_year=2026,
            conflict_flag=False,
            precedence_note=None,
        ),
    ]


def test_synthesizer_initialization():
    synth = Synthesizer()
    assert synth.generator is not None
    assert isinstance(synth.generator, QwenGenerator)


def test_synthesizer_grounding_system_prompt():
    synth = Synthesizer()
    prompt = synth.build_grounding_system_prompt()
    assert "Indian Navy" in prompt
    assert "EXCLUSIVELY" in prompt or "ONLY" in prompt
    assert "extrapolate" in prompt.lower() or "speculate" in prompt.lower()


def test_synthesizer_format_context(sample_chunks):
    synth = Synthesizer()
    formatted = synth.format_context(sample_chunks)
    assert "[Chunk 1]" in formatted
    assert "DFPDS-2026/Schedule_07/Tier_3/Fleet_Commander" in formatted
    assert "Rs 18.00 Crore" in formatted
    assert "[Chunk 2]" in formatted
    assert "Rs 5.00 Crore" in formatted


def test_synthesizer_synthesize_sync(sample_chunks):
    mock_gen = MagicMock(spec=QwenGenerator)
    mock_gen.generate.return_value = "Under DFPDS-2026 Schedule 07, Fleet Commander can sanction up to Rs 18.00 Crore with IFA concurrence."

    synth = Synthesizer(generator=mock_gen)
    result = synth.synthesize(
        query="What is the financial power of Fleet Commander under Schedule 7?",
        chunks=sample_chunks,
        temperature=0.1,
    )

    assert "Fleet Commander" in result
    assert "18.00 Crore" in result
    mock_gen.generate.assert_called_once()
    kwargs = mock_gen.generate.call_args.kwargs
    assert kwargs["temperature"] == 0.1
    assert "Schedule 7" in kwargs["prompt"]


def test_synthesizer_synthesize_empty_context():
    mock_gen = MagicMock(spec=QwenGenerator)
    synth = Synthesizer(generator=mock_gen)

    result = synth.synthesize(query="Any question?", chunks=[])
    assert "No relevant regulatory context" in result
    mock_gen.generate.assert_not_called()


def test_synthesizer_synthesize_stream(sample_chunks):
    mock_gen = MagicMock(spec=QwenGenerator)
    tokens = ["Under ", "Schedule 07, ", "Fleet Commander ", "sanctions ₹18.00 Cr."]
    mock_gen.generate_stream.return_value = iter(tokens)

    synth = Synthesizer(generator=mock_gen)
    stream = synth.synthesize_stream(
        query="What is Fleet Commander power?",
        chunks=sample_chunks,
    )

    assert isinstance(stream, Iterator)
    output = "".join(list(stream))
    assert output == "Under Schedule 07, Fleet Commander sanctions ₹18.00 Cr."
