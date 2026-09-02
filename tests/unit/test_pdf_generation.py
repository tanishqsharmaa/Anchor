from pathlib import Path
import fitz  # PyMuPDF
import pytest
from anchor.config import settings


def test_pdf_directory_and_count():
    pdfs_dir = settings.PDFS_DIR
    assert pdfs_dir.exists(), f"PDFs directory {pdfs_dir} does not exist"

    # Check 32 DFPDS schedules
    for i in range(1, 33):
        pdf_path = pdfs_dir / f"DFPDS_2026_Schedule_{i:02d}.pdf"
        assert pdf_path.exists(), f"Missing {pdf_path.name}"

    # Check 6 DPM chapters
    for i in range(1, 7):
        pdf_path = pdfs_dir / f"DPM_2025_Chapter_{i:02d}.pdf"
        assert pdf_path.exists(), f"Missing {pdf_path.name}"

    # Check 4 Navy Regs parts
    roman_numerals = ["I", "II", "III", "IV"]
    for num in roman_numerals:
        pdf_path = pdfs_dir / f"Navy_Regs_Part_{num}.pdf"
        assert pdf_path.exists(), f"Missing {pdf_path.name}"

    all_pdfs = list(pdfs_dir.glob("*.pdf"))
    assert len(all_pdfs) >= 42, f"Expected at least 42 PDFs, found {len(all_pdfs)}"


def test_dfpds_pdf_structure_and_bboxes():
    pdfs_dir = settings.PDFS_DIR
    sample_pdf = pdfs_dir / "DFPDS_2026_Schedule_01.pdf"
    assert sample_pdf.exists()

    doc = fitz.open(sample_pdf)
    assert len(doc) >= 1

    page = doc[0]
    text = page.get_text("text")
    assert "THE GAZETTE OF INDIA" in text
    assert "Schedule 01" in text or "SCHEDULE 01" in text.upper()
    assert "Chief of the Naval Staff" in text
    assert "120" in text  # ₹120 Cr with IFA

    # Verify bounding boxes
    blocks = page.get_text("blocks")
    assert len(blocks) > 0
    for block in blocks:
        x0, y0, x1, y1, b_text, block_no, block_type = block[:7]
        assert 0 <= x0 <= 600
        assert 0 <= y0 <= 850
        assert x1 > x0
        assert y1 > y0

    doc.close()


def test_dpm_and_navy_regs_pdf_structure():
    pdfs_dir = settings.PDFS_DIR
    
    # Test DPM Chapter 1
    dpm_pdf = pdfs_dir / "DPM_2025_Chapter_01.pdf"
    assert dpm_pdf.exists()
    doc_dpm = fitz.open(dpm_pdf)
    assert len(doc_dpm) >= 1
    text_dpm = doc_dpm[0].get_text("text")
    assert "DEFENCE PROCUREMENT MANUAL 2025" in text_dpm or "DPM-2025" in text_dpm
    doc_dpm.close()

    # Test Navy Regs Part I
    regs_pdf = pdfs_dir / "Navy_Regs_Part_I.pdf"
    assert regs_pdf.exists()
    doc_regs = fitz.open(regs_pdf)
    assert len(doc_regs) >= 1
    text_regs = doc_regs[0].get_text("text")
    assert "NAVY REGULATIONS" in text_regs.upper()
    assert "Article 0101" in text_regs
    doc_regs.close()


def test_deck_pdf_renderer(tmp_path):
    from anchor.deck.ast_compiler import ASTCompiler
    from anchor.deck.pdf_renderer import PDFRenderer

    compiler = ASTCompiler()
    deck_ast = compiler.compile_deterministic_schedule(schedule_no=7)

    renderer = PDFRenderer(output_dir=tmp_path)
    pdf_path = renderer.render(deck_ast)

    assert pdf_path.exists()
    assert pdf_path.is_file()
    assert pdf_path.stat().st_size > 0

    # Verify with fitz
    doc = fitz.open(str(pdf_path))
    assert len(doc) == 4
    doc.close()

