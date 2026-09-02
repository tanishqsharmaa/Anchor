"""
routes_deck.py — AutoDeck AI Presentation Generation & Download Endpoints
"""

import logging
import re
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from anchor.config import settings
from anchor.deck.ast_compiler import ASTCompiler
from anchor.deck.html_renderer import HTMLRenderer
from anchor.deck.pdf_renderer import pdf_renderer
from anchor.deck.pptx_renderer import PPTXRenderer
from anchor.deck.slide_verifier import SlideVerifier
from anchor.retrieve.hybrid import HybridRetriever

logger = logging.getLogger(__name__)

router = APIRouter(tags=["deck"])

# Lazy singletons
_compiler: Optional[ASTCompiler] = None
_pptx_renderer: Optional[PPTXRenderer] = None
_html_renderer: Optional[HTMLRenderer] = None
_verifier: Optional[SlideVerifier] = None
_retriever: Optional[HybridRetriever] = None


def get_compiler() -> ASTCompiler:
    global _compiler
    if _compiler is None:
        _compiler = ASTCompiler()
    return _compiler


def get_pptx_renderer() -> PPTXRenderer:
    global _pptx_renderer
    if _pptx_renderer is None:
        _pptx_renderer = PPTXRenderer()
    return _pptx_renderer


def get_html_renderer() -> HTMLRenderer:
    global _html_renderer
    if _html_renderer is None:
        _html_renderer = HTMLRenderer()
    return _html_renderer


def get_verifier() -> SlideVerifier:
    global _verifier
    if _verifier is None:
        _verifier = SlideVerifier()
    return _verifier


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


class DeckRequest(BaseModel):
    """Request payload for AutoDeck presentation generation."""
    topic: str = Field(..., min_length=3, max_length=2000, description="Briefing topic or query")
    context: Optional[str] = Field(None, max_length=5000, description="Optional extra regulatory context")
    schedule_no: Optional[int] = Field(None, ge=1, le=32, description="Optional DFPDS Schedule number (1-32)")
    num_slides: int = Field(default=4, ge=1, le=12, description="Target slide count")


@router.post("/deck", status_code=status.HTTP_200_OK)
async def generate_deck(req: DeckRequest) -> dict[str, Any]:
    """
    Generate a complete tactical briefing deck:
    1. Compiles topic/context into validated SlideDeckAST (with repair loop / SQL fallback).
    2. Runs DeBERTa NLI Slide Verifier against source regulatory chunks.
    3. Renders 16:9 widescreen PPTX file.
    4. Renders responsive HTML5 slide previews for Next.js Slide Studio.
    """
    start_time = time.perf_counter()

    # Input sanitization
    sanitized_topic = req.topic.strip()
    if not sanitized_topic:
        return {
            "success": False,
            "error": {
                "code": "EMPTY_TOPIC",
                "message": "Topic cannot be empty or whitespace.",
            },
        }

    compiler = get_compiler()
    pptx_renderer = get_pptx_renderer()
    html_renderer = get_html_renderer()
    verifier = get_verifier()

    # Retrieve context chunks if not provided and not a direct schedule request
    context_chunks = []
    effective_context = req.context

    if not effective_context and req.schedule_no is None:
        try:
            retriever = get_retriever()
            context_chunks = retriever.retrieve(sanitized_topic, top_k=3)
            if context_chunks:
                effective_context = "\n\n".join([f"[{c.breadcrumb}] {c.text}" for c in context_chunks])
        except Exception as e:
            logger.warning(f"[routes_deck] Context retrieval failed: {e}")

    try:
        # Step 1: Compile AST
        deck_ast = compiler.compile_with_repair(
            topic=sanitized_topic,
            context=effective_context,
            schedule_no=req.schedule_no,
            num_slides=req.num_slides,
        )

        # Step 2: NLI Slide Verification
        verified_ast, verification_report = verifier.verify_deck(
            deck_ast=deck_ast,
            context_chunks=context_chunks,
        )

        # Step 3: Render PPTX & PDF (ENH-010)
        pptx_path = pptx_renderer.render(deck_ast=verified_ast)
        pdf_url = None
        try:
            pdf_path = pdf_renderer.render(deck_ast=verified_ast)
            if pdf_path and Path(pdf_path).is_file():
                pdf_url = f"/deck/{verified_ast.deck_id}/download/pdf"
        except Exception as pdf_err:
            logger.warning(f"[routes_deck] PDF rendering failed: {pdf_err}")

        # Step 4: Render HTML5
        html_slides = html_renderer.render_deck(deck_ast=verified_ast)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        verified_ast.generation_time_ms = elapsed_ms

        return {
            "success": True,
            "data": {
                "deck_id": verified_ast.deck_id,
                "title": verified_ast.title,
                "ast": verified_ast.model_dump(),
                "html_slides": html_slides,
                "pptx_url": f"/deck/{verified_ast.deck_id}/download",
                "pdf_url": pdf_url,
                "verification_report": verification_report.model_dump(),
                "generation_time_ms": elapsed_ms,
            },
        }
    except Exception as e:
        logger.error(f"[routes_deck] Deck generation failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": {
                "code": "DECK_GENERATION_FAILED",
                "message": f"Failed to generate briefing deck: {str(e)}",
            },
        }


@router.get("/deck/{deck_id}/download")
@router.get("/api/deck/{deck_id}/download")
async def download_deck(deck_id: str):
    """
    Stream generated .pptx binary presentation file for download.
    Includes strict path traversal prevention.
    """
    # 1. Path traversal security sanitization
    if (
        ".." in deck_id
        or "/" in deck_id
        or "\\" in deck_id
        or ":" in deck_id
        or "\x00" in deck_id
        or not re.match(r"^[a-zA-Z0-9_\-]+$", deck_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck identifier format.",
        )

    decks_dir = settings.DATA_DIR / "decks"
    target_file = decks_dir / f"{deck_id}.pptx"

    if not target_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Briefing deck presentation '{deck_id}' was not found.",
        )

    return FileResponse(
        path=str(target_file),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"{deck_id}.pptx",
    )


@router.get("/deck/{deck_id}/download/pdf")
@router.get("/api/deck/{deck_id}/download/pdf")
async def download_deck_pdf(deck_id: str):
    """
    Stream generated 16:9 .pdf presentation file for download (ENH-010).
    Includes strict path traversal prevention.
    """
    if (
        ".." in deck_id
        or "/" in deck_id
        or "\\" in deck_id
        or ":" in deck_id
        or "\x00" in deck_id
        or not re.match(r"^[a-zA-Z0-9_\-]+$", deck_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid deck identifier format.",
        )

    decks_dir = settings.DATA_DIR / "decks"
    target_file = decks_dir / f"{deck_id}.pdf"

    if not target_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Briefing deck PDF '{deck_id}' was not found.",
        )

    return FileResponse(
        path=str(target_file),
        media_type="application/pdf",
        filename=f"{deck_id}.pdf",
    )
