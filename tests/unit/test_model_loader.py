"""
test_model_loader.py — Unit Tests for Serialized Model Residency Manager
"""

import threading
import pytest
from anchor.models.loader import ModelOrchestrator, model_orchestrator
from anchor.models.embedder import BGEEmbedder
from anchor.models.reranker_model import BGEReranker
from anchor.models.nli_model import DeBERTaNLI


@pytest.fixture(scope="function")
def orchestrator():
    # Fresh instance for testing
    orch = ModelOrchestrator()
    yield orch
    orch.unload_all()


def test_model_orchestrator_initialization(orchestrator):
    """Verify orchestrator initializes with empty cache and clean state."""
    assert orchestrator is not None
    assert orchestrator.loaded_models == []


def test_model_orchestrator_get_models(orchestrator):
    """Verify orchestrator loads embedder, reranker, and nli instances."""
    embedder = orchestrator.get_embedder()
    assert isinstance(embedder, BGEEmbedder)
    assert "embed" in orchestrator.loaded_models

    nli = orchestrator.get_nli()
    assert isinstance(nli, DeBERTaNLI)
    assert "nli" in orchestrator.loaded_models


def test_model_orchestrator_coresidency_and_unloading(orchestrator):
    """Verify heavy model transitions and explicit unloading."""
    # Load embedder
    _ = orchestrator.get_embedder()
    assert "embed" in orchestrator.loaded_models

    # Load reranker with unload_conflicting=True (should unload embedder)
    _ = orchestrator.get_reranker(unload_conflicting=True)
    assert "rerank" in orchestrator.loaded_models
    assert "embed" not in orchestrator.loaded_models

    # NLI can co-reside with reranker
    _ = orchestrator.get_nli()
    assert "rerank" in orchestrator.loaded_models
    assert "nli" in orchestrator.loaded_models

    # Explicit unload
    orchestrator.unload("rerank")
    assert "rerank" not in orchestrator.loaded_models
    assert "nli" in orchestrator.loaded_models


def test_model_orchestrator_memory_tracking(orchestrator):
    """Verify psutil memory tracking reports valid statistics and respects 12.5 GB ceiling."""
    stats = orchestrator.get_memory_stats()

    assert "process_rss_gb" in stats
    assert "system_used_gb" in stats
    assert "system_total_gb" in stats
    assert "system_free_gb" in stats
    assert "peak_ram_within_budget" in stats

    assert stats["process_rss_gb"] > 0.0
    # Process RSS should be well below 12.5 GB
    assert stats["process_rss_gb"] < 12.5
    assert stats["peak_ram_within_budget"] is True

    # Memory budget enforcement check
    assert orchestrator.enforce_memory_budget(max_ram_gb=12.5) is True


def test_model_orchestrator_thread_safety(orchestrator):
    """Verify concurrent model acquisition requests are thread-safe without race conditions."""
    results = []

    def worker(group_name: str):
        if group_name == "nli":
            m = orchestrator.get_nli()
        elif group_name == "rerank":
            m = orchestrator.get_reranker()
        else:
            m = orchestrator.get_embedder()
        results.append(m is not None)

    threads = [
        threading.Thread(target=worker, args=("nli",)),
        threading.Thread(target=worker, args=("rerank",)),
        threading.Thread(target=worker, args=("nli",)),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 3
    assert all(results)
