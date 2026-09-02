"""
test_model_smoke.py — Unit Tests for OpenVINO INT8 Neural Model Inference
"""

from pathlib import Path
import pytest
import torch
from optimum.intel.openvino import OVModelForFeatureExtraction, OVModelForSequenceClassification
from transformers import AutoTokenizer


def test_deberta_nli_inference(deberta_model_path: Path):
    """Assert DeBERTa-v3-NLI evaluates premise-hypothesis pairs with correct logits."""
    tokenizer = AutoTokenizer.from_pretrained(str(deberta_model_path))
    model = OVModelForSequenceClassification.from_pretrained(str(deberta_model_path), device="CPU")

    premise = "Under DFPDS-2026 Schedule 7, Fleet Commander L2 has financial powers up to 15 Crore with IFA concurrence."
    hypothesis_contra = "A Fleet Commander can sanction 50 Crore without any IFA approval."

    inputs = tokenizer(premise, hypothesis_contra, return_tensors="pt", truncation=True)
    outputs = model(**inputs)
    probs = torch.softmax(outputs.logits, dim=-1).detach().numpy()[0]

    # Index 0 is contradiction for cross-encoder/nli-deberta-v3-base
    assert probs[0] > 0.90, f"Expected contradiction probability > 0.90, got {probs[0]:.4f}"

    del model, tokenizer


def test_bge_reranker_inference(bge_reranker_model_path: Path):
    """Assert BGE-Reranker-Large ranks relevant passages higher than irrelevant ones."""
    tokenizer = AutoTokenizer.from_pretrained(str(bge_reranker_model_path))
    model = OVModelForSequenceClassification.from_pretrained(str(bge_reranker_model_path), device="CPU")

    pairs = [
        ["What is the financial limit for L2 under Schedule 7?", "Under Schedule 7, Fleet Commander L2 may sanction up to 15.0 Crore."],
        ["What is the financial limit for L2 under Schedule 7?", "The capital ship refit procedures are governed by Chapter 4."]
    ]
    inputs = tokenizer(pairs, padding=True, truncation=True, return_tensors="pt", max_length=512)
    outputs = model(**inputs)
    scores = outputs.logits.detach().numpy().flatten()

    assert scores[0] > scores[1], f"Expected score[0] ({scores[0]:.3f}) > score[1] ({scores[1]:.3f})"

    del model, tokenizer


def test_bge_m3_embedding_dimension(bge_m3_model_path: Path):
    """Assert BGE-M3 produces a 1024-dimensional dense embedding vector."""
    tokenizer = AutoTokenizer.from_pretrained(str(bge_m3_model_path))
    model = OVModelForFeatureExtraction.from_pretrained(str(bge_m3_model_path), device="CPU")

    text = "Delegation of Financial Powers to Defence Services Navy 2026 Schedule 7"
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    outputs = model(**inputs)
    embeddings = outputs.last_hidden_state[:, 0].detach().numpy()

    assert embeddings.shape == (1, 1024), f"Expected shape (1, 1024), got {embeddings.shape}"

    del model, tokenizer
