"""
test_embedder.py — Unit Tests for BGE-M3 OpenVINO INT8 Embedder Wrapper
"""

from pathlib import Path
import numpy as np
import pytest
from anchor.models.embedder import BGEEmbedder


def test_embedder_initialization(bge_m3_model_path: Path):
    """Assert embedder loads successfully from specified model path."""
    embedder = BGEEmbedder(model_path=bge_m3_model_path)
    assert embedder.model is not None
    assert embedder.tokenizer is not None


def test_embedder_encode_single_string(bge_m3_model_path: Path):
    """Assert single string input produces (1, 1024) normalized vector."""
    embedder = BGEEmbedder(model_path=bge_m3_model_path)
    text = "Delegation of Financial Powers to Defence Services Navy 2026 Schedule 7"
    vec = embedder.encode(text)

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (1, 1024)
    assert vec.dtype == np.float32

    norm = np.linalg.norm(vec[0])
    assert abs(norm - 1.0) < 1e-4, f"Expected unit norm, got {norm}"


def test_embedder_encode_batch(bge_m3_model_path: Path):
    """Assert batch input produces (N, 1024) normalized vectors."""
    embedder = BGEEmbedder(model_path=bge_m3_model_path)
    texts = [
        "Schedule 7 Tactical Drones procurement delegation",
        "DPM 2025 Chapter 3 Single Tender Enquiry procedure",
        "Navy Regulations Part 1 Command and statutory authorities",
    ]
    vecs = embedder.encode(texts, batch_size=2)

    assert vecs.shape == (3, 1024)
    for i in range(3):
        norm = np.linalg.norm(vecs[i])
        assert abs(norm - 1.0) < 1e-4


def test_embedder_semantic_similarity(bge_m3_model_path: Path):
    """Assert semantically related sentences have higher cosine similarity than unrelated ones."""
    embedder = BGEEmbedder(model_path=bge_m3_model_path)
    query = "What is the financial sanction limit for Fleet Commander under Schedule 7?"
    relevant_doc = "Under Schedule 07, Fleet Commander Tier 3 has financial power of 18 Crore with IFA concurrence."
    irrelevant_doc = "The naval uniform regulations specify shoulder rank insignias for executive officers."

    vec_q = embedder.encode(query)[0]
    vec_rel = embedder.encode(relevant_doc)[0]
    vec_irrel = embedder.encode(irrelevant_doc)[0]

    sim_rel = embedder.compute_similarity(vec_q, vec_rel)
    sim_irrel = embedder.compute_similarity(vec_q, vec_irrel)

    assert sim_rel > sim_irrel, f"Expected relevant similarity ({sim_rel:.3f}) > irrelevant similarity ({sim_irrel:.3f})"
    assert sim_rel > 0.60


def test_embedder_empty_input(bge_m3_model_path: Path):
    """Assert empty list input returns (0, 1024) array without error."""
    embedder = BGEEmbedder(model_path=bge_m3_model_path)
    vecs = embedder.encode([])
    assert vecs.shape == (0, 1024)


def test_embedder_whitespace_input(bge_m3_model_path: Path):
    """Assert whitespace input is encoded gracefully without error."""
    embedder = BGEEmbedder(model_path=bge_m3_model_path)
    vecs = embedder.encode(["   ", ""])
    assert vecs.shape == (2, 1024)


def test_embedder_invalid_path():
    """Assert FileNotFoundError is raised for non-existent model path."""
    with pytest.raises(FileNotFoundError):
        BGEEmbedder(model_path=Path("non_existent_model_dir_xyz"))
