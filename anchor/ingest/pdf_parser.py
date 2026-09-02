"""
pdf_parser.py — Layout-Aware PyMuPDF Parser with Exact Bounding Box Extraction & OCR Gate
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union
import fitz  # PyMuPDF


@dataclass
class TextSpan:
    """Represents a single text span with typography and exact coordinates."""
    text: str
    bbox: tuple[float, float, float, float]  # (x0, y0, x1, y1)
    font_name: str = ""
    font_size: float = 0.0
    flags: int = 0  # 1=superscript, 2=italic, 4=serif, 8=monospaced, 16=bold


@dataclass
class TextBlock:
    """Represents a structural block of text spans with aggregated coordinates."""
    block_id: int
    text: str
    bbox: tuple[float, float, float, float]
    spans: list[TextSpan] = field(default_factory=list)
    is_heading: bool = False
    max_font_size: float = 0.0


@dataclass
class PageLayout:
    """Represents a parsed PDF page layout."""
    page_no: int  # 1-indexed
    width: float
    height: float
    blocks: list[TextBlock] = field(default_factory=list)
    ocr_applied: bool = False

    @property
    def full_text(self) -> str:
        return "\n".join(b.text for b in self.blocks if b.text.strip())


@dataclass
class DocumentLayout:
    """Represents the complete parsed document layout across all pages."""
    doc_id: str
    pdf_path: Path
    pages: list[PageLayout] = field(default_factory=list)
    total_pages: int = 0

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.full_text for p in self.pages if p.full_text.strip())


def parse_pdf_layout(
    pdf_path: Union[Path, str],
    ocr_confidence_threshold: float = 80.0,
) -> DocumentLayout:
    """
    Parse a regulatory PDF document using PyMuPDF to extract text blocks, typography,
    and exact bounding box coordinates [x0, y0, x1, y1].

    Args:
        pdf_path: Path to the input PDF file.
        ocr_confidence_threshold: Minimum character confidence threshold for OCR fallback.

    Returns:
        DocumentLayout containing structured pages, blocks, and spans.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF document not found: {path}")

    doc_id = path.stem
    doc = fitz.open(str(path))
    pages: list[PageLayout] = []

    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_no = page_idx + 1
            page_rect = page.rect
            page_dict = page.get_text("dict")

            blocks: list[TextBlock] = []
            raw_blocks = page_dict.get("blocks", [])

            for b_idx, block in enumerate(raw_blocks):
                # Type 0 is text block, Type 1 is image block
                if block.get("type", 0) != 0:
                    continue

                block_bbox = tuple(float(x) for x in block.get("bbox", (0, 0, 0, 0)))
                spans: list[TextSpan] = []
                block_text_parts: list[str] = []
                max_font_size = 0.0
                has_bold = False

                for line in block.get("lines", []):
                    line_text_parts: list[str] = []
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if not span_text:
                            continue
                        span_bbox = tuple(float(x) for x in span.get("bbox", (0, 0, 0, 0)))
                        font_name = str(span.get("font", ""))
                        font_size = float(span.get("size", 0.0))
                        flags = int(span.get("flags", 0))

                        if font_size > max_font_size:
                            max_font_size = font_size
                        if (flags & 16) or ("bold" in font_name.lower()) or ("heavy" in font_name.lower()):
                            has_bold = True

                        span_obj = TextSpan(
                            text=span_text,
                            bbox=span_bbox,
                            font_name=font_name,
                            font_size=font_size,
                            flags=flags,
                        )
                        spans.append(span_obj)
                        line_text_parts.append(span_text)

                    if line_text_parts:
                        block_text_parts.append(" ".join(line_text_parts))

                block_text = "\n".join(block_text_parts).strip()
                if block_text:
                    is_heading = max_font_size >= 12.0 or (has_bold and max_font_size >= 10.5)
                    blocks.append(
                        TextBlock(
                            block_id=b_idx,
                            text=block_text,
                            bbox=block_bbox,
                            spans=spans,
                            is_heading=is_heading,
                            max_font_size=max_font_size,
                        )
                    )

            ocr_applied = False
            # OCR Fallback Gate: Scanned or empty page fallback
            if len(blocks) == 0:
                # Attempt OCR via PyMuPDF native OCR if available or text fallback
                try:
                    ocr_page = page.get_textpage_ocr(language="eng", dpi=150)
                    ocr_dict = page.get_text("dict", textpage=ocr_page)
                    ocr_blocks = ocr_dict.get("blocks", [])
                    for b_idx, block in enumerate(ocr_blocks):
                        if block.get("type", 0) != 0:
                            continue
                        block_bbox = tuple(float(x) for x in block.get("bbox", (0, 0, 0, 0)))
                        block_text = "".join(
                            span.get("text", "")
                            for line in block.get("lines", [])
                            for span in line.get("spans", [])
                        ).strip()
                        if block_text:
                            blocks.append(
                                TextBlock(
                                    block_id=b_idx,
                                    text=block_text,
                                    bbox=block_bbox,
                                    is_heading=False,
                                    max_font_size=10.0,
                                )
                            )
                    ocr_applied = len(blocks) > 0
                except Exception:
                    ocr_applied = False

            pages.append(
                PageLayout(
                    page_no=page_no,
                    width=float(page_rect.width),
                    height=float(page_rect.height),
                    blocks=blocks,
                    ocr_applied=ocr_applied,
                )
            )
    finally:
        doc.close()

    return DocumentLayout(
        doc_id=doc_id,
        pdf_path=path,
        pages=pages,
        total_pages=len(pages),
    )
