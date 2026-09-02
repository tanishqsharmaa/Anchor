"""
pdf_renderer.py — AutoDeck AI 16:9 PDF Presentation Renderer
Renders validated SlideDeckAST objects into multi-page 16:9 widescreen PDFs
with sovereign Indian Naval Staff C4ISR dark tactical styling.
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.pdfgen import canvas

from anchor.config import settings
from anchor.deck.schemas import SlideASTItem, SlideDeckAST

logger = logging.getLogger(__name__)

# 16:9 Widescreen standard in points (13.333 in x 7.5 in @ 72 DPI)
SLIDE_WIDTH = 960.0
SLIDE_HEIGHT = 540.0

# C4ISR Dark Tactical Color Palette
COLOR_BG = colors.HexColor("#0B0F19")
COLOR_PANEL_BG = colors.HexColor("#111C2E")
COLOR_SURFACE_BG = colors.HexColor("#162032")
COLOR_CYAN = colors.HexColor("#00E5FF")
COLOR_GOLD = colors.HexColor("#FFD700")
COLOR_GREEN = colors.HexColor("#10B981")
COLOR_WHITE = colors.HexColor("#FFFFFF")
COLOR_BODY = colors.HexColor("#CCD6F6")
COLOR_MUTED = colors.HexColor("#94A3B8")
COLOR_BORDER = colors.HexColor("#233554")


class PDFRenderer:
    """
    AutoDeck AI PDF Presentation Renderer.
    Translates SlideDeckAST objects into multi-page 16:9 PDF documents with
    tactical layout coordinates, header banners, bullet points, and citation badges.
    """

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = output_dir or (settings.DATA_DIR / "decks")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(self, deck_ast: SlideDeckAST, output_path: Optional[Path] = None) -> Path:
        """
        Render a SlideDeckAST into a 16:9 PDF presentation file.

        Args:
            deck_ast: Validated slide deck AST model.
            output_path: Optional custom output filepath.

        Returns:
            Path to the compiled .pdf presentation file.
        """
        target_path = output_path or (self.output_dir / f"{deck_ast.deck_id}.pdf")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        c = canvas.Canvas(str(target_path), pagesize=(SLIDE_WIDTH, SLIDE_HEIGHT))
        total_slides = len(deck_ast.slides)

        for idx, slide in enumerate(deck_ast.slides, start=1):
            self._render_slide(c, slide, slide_idx=idx, total_slides=total_slides, deck_title=deck_ast.title)
            c.showPage()

        c.save()
        logger.info(f"[PDFRenderer] Rendered {total_slides}-slide deck to {target_path}")
        return target_path

    def _render_slide(
        self,
        c: canvas.Canvas,
        slide: SlideASTItem,
        slide_idx: int,
        total_slides: int,
        deck_title: str,
    ) -> None:
        """Render a single 16:9 tactical slide canvas."""
        # 1. Background fill
        c.setFillColor(COLOR_BG)
        c.rect(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT, fill=1, stroke=0)

        # 2. Header Panel Top Banner
        c.setFillColor(COLOR_PANEL_BG)
        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(1)
        c.rect(30, SLIDE_HEIGHT - 85, SLIDE_WIDTH - 60, 65, fill=1, stroke=1)

        # Top classification bar
        c.setFillColor(COLOR_CYAN)
        c.rect(30, SLIDE_HEIGHT - 24, SLIDE_WIDTH - 60, 4, fill=1, stroke=0)

        # Slide Type Tag Pill
        c.setFillColor(COLOR_CYAN)
        c.setFont("Helvetica-Bold", 8)
        slide_type_str = f"[{slide.type.upper()}]"
        c.drawString(45, SLIDE_HEIGHT - 42, slide_type_str)

        # Slide Title
        c.setFillColor(COLOR_WHITE)
        c.setFont("Helvetica-Bold", 16)
        title_text = slide.title or f"Briefing Section {slide_idx}"
        c.drawString(45, SLIDE_HEIGHT - 65, title_text[:75])

        # Extract content dynamically based on slide type
        content = slide.content
        slide_type = str(slide.type.value if hasattr(slide.type, "value") else slide.type).upper()
        
        subtitle = ""
        bullets = []
        takeaway = ""

        if hasattr(content, "subtitle") and content.subtitle:
            subtitle = content.subtitle
        elif hasattr(content, "matrix_title") and content.matrix_title:
            subtitle = content.matrix_title
        elif hasattr(content, "schedule_title") and content.schedule_title:
            subtitle = content.schedule_title

        if "HERO" in slide_type:
            if hasattr(content, "officer") and content.officer:
                bullets.append(f"Presenter: {content.officer}")
            if hasattr(content, "unit") and content.unit:
                bullets.append(f"Command: {content.unit}")
            if hasattr(content, "classification") and content.classification:
                bullets.append(f"Security: {content.classification}")
            if hasattr(content, "dtg") and content.dtg:
                takeaway = f"DTG: {content.dtg}"
        elif "BLUF" in slide_type:
            if hasattr(content, "bluf_headline") and content.bluf_headline:
                bullets.append(f"BLUF: {content.bluf_headline}")
            if hasattr(content, "key_takeaways") and content.key_takeaways:
                for t in content.key_takeaways:
                    bullets.append(f"• {t}")
            if hasattr(content, "risk_summary") and content.risk_summary:
                bullets.append(f"Risk: {content.risk_summary}")
            if hasattr(content, "decision_requested") and content.decision_requested:
                takeaway = content.decision_requested
        elif "POLICY" in slide_type:
            if hasattr(content, "rows") and content.rows:
                for r in content.rows:
                    row_title = getattr(r, "row_title", "")
                    cells = getattr(r, "cells", [])
                    bullets.append(f"{row_title}: {', '.join(cells)}")
            if hasattr(content, "statutory_precedence_note") and content.statutory_precedence_note:
                takeaway = content.statutory_precedence_note
        elif "FINANCIAL" in slide_type:
            if hasattr(content, "tiers") and content.tiers:
                for t in content.tiers:
                    tier_str = getattr(t, "tier", "")
                    tier_name = getattr(t, "tier_name", "")
                    with_ifa = getattr(t, "with_ifa_limit", 0.0)
                    without_ifa = getattr(t, "without_ifa_limit", 0.0)
                    pac_lim = getattr(t, "pac_limit", None)
                    pac_str = f" / PAC: ₹{pac_lim:.2f} Cr" if pac_lim is not None else ""
                    bullets.append(f"{tier_str} ({tier_name}): ₹{with_ifa:.2f} Cr (with IFA) / ₹{without_ifa:.2f} Cr (without IFA){pac_str}")
            if hasattr(content, "notes") and content.notes:
                takeaway = content.notes
            elif hasattr(content, "schedule_no"):
                takeaway = f"DFPDS-2026 Schedule {content.schedule_no:02d} Statutory Delegation Authority"
        else:
            bullets.append(str(content)[:100])

        # Subtitle / Reference if present
        if subtitle:
            c.setFillColor(COLOR_GOLD)
            c.setFont("Helvetica", 9)
            c.drawRightString(SLIDE_WIDTH - 45, SLIDE_HEIGHT - 45, subtitle[:60])

        # 3. Main Content Area Box
        content_top = SLIDE_HEIGHT - 105
        content_bottom = 50
        content_height = content_top - content_bottom

        c.setFillColor(COLOR_SURFACE_BG)
        c.setStrokeColor(COLOR_BORDER)
        c.rect(30, content_bottom, SLIDE_WIDTH - 60, content_height, fill=1, stroke=1)

        # Draw bullets / key points
        curr_y = content_top - 30

        if bullets:
            c.setFont("Helvetica", 11)
            for bullet in bullets[:6]:
                # Bullet diamond marker
                c.setFillColor(COLOR_CYAN)
                c.rect(50, curr_y + 2, 6, 6, fill=1, stroke=0)

                # Bullet text
                c.setFillColor(COLOR_BODY)
                c.drawString(65, curr_y, bullet[:110])
                curr_y -= 32

        # Draw Takeaway / BLUF box at bottom if available
        if takeaway:
            box_y = content_bottom + 15
            c.setFillColor(COLOR_PANEL_BG)
            c.setStrokeColor(COLOR_GOLD)
            c.rect(45, box_y, SLIDE_WIDTH - 90, 36, fill=1, stroke=1)

            c.setFillColor(COLOR_GOLD)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(55, box_y + 20, "KEY TAKEAWAY / BLUF:")

            c.setFillColor(COLOR_WHITE)
            c.setFont("Helvetica", 9)
            c.drawString(195, box_y + 20, takeaway[:95])

        # 4. Footer Bar
        c.setFillColor(COLOR_MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(30, 25, "IN RESTRICTED // NAVAL PROCUREMENT REGULATORY COMPLIANCE // PROJECT ANCHOR")
        c.drawRightString(SLIDE_WIDTH - 30, 25, f"Slide {slide_idx} of {total_slides}")


pdf_renderer = PDFRenderer()
