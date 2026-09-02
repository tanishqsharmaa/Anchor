from pathlib import Path
import os
import pytest


def test_settings_import_and_defaults():
    from anchor.config import settings, Settings

    assert isinstance(settings, Settings)
    assert settings.APP_NAME == "PROJECT ANCHOR"
    assert settings.VERSION == "1.0.0"
    
    # Path resolution
    assert isinstance(settings.BASE_DIR, Path)
    assert settings.DATA_DIR.name == "data"
    assert settings.PDFS_DIR.name == "pdfs"
    assert settings.LANCEDB_DIR.name == "lancedb"
    assert settings.TANTIVY_DIR.name == "tantivy"
    assert settings.SQLITE_PATH.name == "anchor.db"
    assert settings.MODELS_DIR.name == "models"

    # Model paths
    assert settings.BGE_M3_PATH.name == "bge-m3"
    assert settings.BGE_RERANKER_PATH.name == "bge-reranker-large"
    assert settings.DEBERTA_NLI_PATH.name == "deberta-v3-nli"

    # Hyperparameters
    assert settings.RRF_K == 60
    assert settings.TOP_K_RETRIEVAL == 10
    assert settings.TOP_K_RERANK == 3

    # Quality thresholds
    assert settings.NLI_ENTAILMENT_THRESHOLD == 0.85
    assert settings.NLI_CONTRADICTION_THRESHOLD == 0.08

    # Ollama settings
    assert settings.OLLAMA_BASE_URL == "http://localhost:11434"
    assert "qwen2.5" in settings.OLLAMA_MODEL


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("ANCHOR_RRF_K", "45")
    monkeypatch.setenv("ANCHOR_NLI_ENTAILMENT_THRESHOLD", "0.90")
    
    from anchor.config import Settings
    custom_settings = Settings()
    
    assert custom_settings.RRF_K == 45
    assert custom_settings.NLI_ENTAILMENT_THRESHOLD == 0.90
