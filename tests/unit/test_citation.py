"""
test_citation.py — Unit Tests for SHA-256 Hashing and Citation Anchoring Engine
"""

import hashlib
import tempfile
from pathlib import Path
import pytest
from pydantic import ValidationError

from anchor.generate.citation import ByteAnchor, Citation, CitationAnchorer
from anchor.generate.nli_gate import SentenceVerification
from anchor.retrieve.hybrid import RetrievedChunk
from anchor.retrieve.resolver import ResolverResult
from anchor.trust.hash import compute_file_sha256, compute_sha256, verify_sha256


class TestTrustHashing:
    """Unit tests for anchor/trust/hash.py cryptographic functions."""

    def test_compute_sha256_deterministic(self) -> None:
        sample_text = "Under DFPDS-2026 Schedule 07, Fleet Commander has financial limit of Rs 15 Cr."
        expected = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()
        digest = compute_sha256(sample_text)
        assert digest == expected
        assert len(digest) == 64
        assert digest.islower()

    def test_compute_sha256_type_error(self) -> None:
        with pytest.raises(TypeError):
            compute_sha256(12345)  # type: ignore

    def test_compute_file_sha256(self) -> None:
        content = b"Official Gazette of India - Naval Financial Delegation 2026"
        expected = hashlib.sha256(content).hexdigest()
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            digest = compute_file_sha256(tmp_path)
            assert digest == expected
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_compute_file_sha256_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            compute_file_sha256("non_existent_file_path_12345.pdf")

    def test_verify_sha256_valid_and_tampered(self) -> None:
        text = "Genuine regulatory clause text"
        h = compute_sha256(text)
        assert verify_sha256(text, h) is True
        assert verify_sha256(text + " tampered", h) is False
        assert verify_sha256(text, "invalid_short_hash") is False
        assert verify_sha256(text, 1234) is False  # type: ignore


class TestCitationModels:
    """Unit tests for ByteAnchor and Citation data structures."""

    def test_byte_anchor_instantiation(self) -> None:
        anchor = ByteAnchor(
            document="DFPDS-2026/Schedule_07",
            page=4,
            bbox=[72.0, 100.0, 540.0, 200.0],
            byte_offset=1024,
            byte_length=150,
            sha256=compute_sha256("test text"),
            text="test text",
        )
        assert anchor.document == "DFPDS-2026/Schedule_07"
        assert anchor.page == 4
        assert len(anchor.bbox) == 4

    def test_citation_pydantic_valid(self) -> None:
        text = "Sample regulatory excerpt"
        h = compute_sha256(text)
        citation = Citation(
            document="DFPDS-2026/Schedule_01",
            page=2,
            bbox=[50.0, 80.0, 500.0, 180.0],
            byte_offset=0,
            byte_length=len(text.encode("utf-8")),
            sha256=h,
            text_snippet=text,
        )
        assert citation.page == 2
        assert citation.sha256 == h
        dump = citation.model_dump()
        assert dump["document"] == "DFPDS-2026/Schedule_01"

    def test_citation_pydantic_invalid(self) -> None:
        # Invalid page (page < 1)
        with pytest.raises(ValidationError):
            Citation(
                document="DFPDS-2026",
                page=0,
                sha256=compute_sha256("x"),
                text_snippet="sample",
            )
        # Invalid hash length
        with pytest.raises(ValidationError):
            Citation(
                document="DFPDS-2026",
                page=1,
                sha256="short_hash",
                text_snippet="sample",
            )


class TestCitationAnchorer:
    """Unit tests for CitationAnchorer resolution logic."""

    @pytest.fixture
    def anchorer(self) -> CitationAnchorer:
        return CitationAnchorer()

    @pytest.fixture
    def sample_chunk(self) -> RetrievedChunk:
        text = "Under DFPDS-2026 Schedule 07, Fleet Commander has financial powers up to Rs 15.0 Crore with IFA."
        return RetrievedChunk(
            chunk_id="chunk_sch07_tier3",
            doc_id="DFPDS-2026",
            schedule_no=7,
            section="Schedule 07 - Major Repairs",
            breadcrumb="DFPDS-2026/Schedule_07/Tier_3/Fleet_Commander",
            page_no=3,
            bbox=[72.0, 120.0, 540.0, 240.0],
            text=text,
            sha256=compute_sha256(text),
            score=0.92,
        )

    def test_anchor_chunk(self, anchorer: CitationAnchorer, sample_chunk: RetrievedChunk) -> None:
        citation = anchorer.anchor_chunk(sample_chunk)
        assert citation.document == "DFPDS-2026/Schedule_07/Tier_3/Fleet_Commander"
        assert citation.page == 3
        assert citation.sha256 == sample_chunk.sha256
        assert len(citation.bbox) == 4
        assert "Fleet Commander" in citation.text_snippet

    def test_anchor_verified_sentences(
        self, anchorer: CitationAnchorer, sample_chunk: RetrievedChunk
    ) -> None:
        verifications = [
            SentenceVerification(
                sentence_idx=0,
                text="Fleet Commander can sanction up to Rs 15 Crore with IFA.",
                best_premise_chunk_id="chunk_sch07_tier3",
                best_premise_breadcrumb="DFPDS-2026/Schedule_07/Tier_3/Fleet_Commander",
                entailment_score=0.94,
                status="certified",
            ),
            SentenceVerification(
                sentence_idx=1,
                text="Unverified claim that contradicts regulations.",
                best_premise_chunk_id="chunk_sch07_tier3",
                entailment_score=0.12,
                contradiction_score=0.75,
                status="abstain",
            ),
        ]

        citations = anchorer.anchor_verified_sentences(verifications, [sample_chunk])
        assert len(citations) == 1
        assert citations[0].document == "DFPDS-2026/Schedule_07/Tier_3/Fleet_Commander"
        assert citations[0].page == 3

    def test_anchor_structured_record(self, anchorer: CitationAnchorer) -> None:
        record = ResolverResult(
            schedule_no=7,
            schedule_name="Major Repairs",
            reference="DFPDS-2026/NAVY/SCH-07",
            gazette_notification="MoD/N/2026/DFPDS/07",
            effective_date="2026-04-01",
            tier="Tier 3",
            tier_name="Fleet Commander",
            sanction_limit=18.0,
            with_ifa=True,
            is_pac=False,
            pac_limit=0.0,
            formatted_answer="Under DFPDS-2026 Schedule 07 (Major Repairs), Fleet Commander (Tier 3) may sanction up to Rs 18.00 Crore with IFA concurrence.",
            notes="Statutory note",
        )

        citations = anchorer.anchor_structured_record(record)
        assert len(citations) == 1
        assert citations[0].document == "DFPDS-2026/NAVY/SCH-07"
        assert citations[0].page == 7
        assert citations[0].sha256 == compute_sha256(record.formatted_answer)
        assert "Fleet Commander (Tier 3)" in citations[0].text_snippet
