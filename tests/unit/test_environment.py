"""
test_environment.py — Unit Tests for Python 3.12 Backend Dependencies & Tooling
"""

import sys
import pytest


def test_python_version():
    """Assert runtime is Python 3.12 for wheel binary compatibility."""
    assert sys.version_info.major == 3
    assert sys.version_info.minor == 12


def test_openvino_import():
    """Assert OpenVINO is available and detects CPU device."""
    import openvino as ov
    core = ov.Core()
    devices = core.available_devices
    assert "CPU" in devices


def test_spacy_model_loaded():
    """Assert spaCy en_core_web_sm model is installed and segments sentences."""
    import spacy
    nlp = spacy.load("en_core_web_sm")
    doc = nlp("DFPDS Schedule 7 governs financial sanctions. Fleet Commander L2 has powers up to 15 Crore.")
    sentences = [sent.text for sent in doc.sents]
    assert len(sentences) == 2


def test_lancedb_and_tantivy_imports():
    """Assert embedded vector and sparse lexical databases import without error."""
    import lancedb
    import tantivy
    assert lancedb is not None
    assert tantivy is not None


def test_pymupdf_and_pptx_imports():
    """Assert PDF layout and PowerPoint generation libraries import without error."""
    import fitz
    import pptx
    assert fitz is not None
    assert pptx is not None
