"""
conftest.py — Pytest Configuration and Shared Test Fixtures for PROJECT ANCHOR
"""

import os
import sys
from pathlib import Path
import pytest

# Ensure Build directory is in sys.path
BUILD_DIR = Path(__file__).resolve().parent.parent
if str(BUILD_DIR) not in sys.path:
    sys.path.insert(0, str(BUILD_DIR))

MODELS_DIR = BUILD_DIR / "models"


@pytest.fixture(scope="session")
def models_dir() -> Path:
    return MODELS_DIR


@pytest.fixture(scope="session")
def deberta_model_path(models_dir: Path) -> Path:
    path = models_dir / "deberta-v3-nli-int8-ov"
    assert path.exists(), f"DeBERTa model directory does not exist: {path}"
    return path


@pytest.fixture(scope="session")
def bge_reranker_model_path(models_dir: Path) -> Path:
    path = models_dir / "bge-reranker-large-int8-ov"
    assert path.exists(), f"BGE-Reranker model directory does not exist: {path}"
    return path


@pytest.fixture(scope="session")
def bge_m3_model_path(models_dir: Path) -> Path:
    path = models_dir / "bge-m3-int8-ov"
    assert path.exists(), f"BGE-M3 model directory does not exist: {path}"
    return path
