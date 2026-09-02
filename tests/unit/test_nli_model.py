"""
test_nli_model.py — Unit Tests for OpenVINO INT8 DeBERTa-v3 NLI Model Wrapper
"""

import time
import pytest
from anchor.models.nli_model import DeBERTaNLI


@pytest.fixture(scope="module")
def nli_model():
    """Module-level fixture providing compiled DeBERTa-v3 OpenVINO NLI model."""
    return DeBERTaNLI()


def test_nli_model_initialization(nli_model):
    """Verify DeBERTa-v3 NLI model loads cleanly and resolves tokenizer."""
    assert nli_model is not None
    assert nli_model.model is not None
    assert nli_model.tokenizer is not None


def test_nli_single_pair_prediction_probabilities(nli_model):
    """Verify single-pair prediction returns normalized 3-way probability simplex."""
    premise = "Under DFPDS-2026 Schedule 7, a Fleet Commander (Tier 3) may sanction up to ₹18.00 Crore with IFA."
    hypothesis = "A Fleet Commander has financial delegation powers up to ₹18.00 Crore with IFA concurrence."

    scores = nli_model.predict(premise, hypothesis)

    assert isinstance(scores, dict)
    assert set(scores.keys()) == {"entailment", "neutral", "contradiction"}

    for key, val in scores.items():
        assert 0.0 <= val <= 1.0, f"Probability for {key} out of range [0, 1]: {val}"

    total_prob = sum(scores.values())
    assert pytest.approx(total_prob, abs=1e-4) == 1.0


def test_nli_entailment_classification(nli_model):
    """Verify that clearly entailed statement receives dominant entailment score."""
    premise = "Under DFPDS-2026 Schedule 07, a Fleet Commander (Tier 3) may sanction up to ₹18.00 Crore with IFA."
    hypothesis = "The Fleet Commander has delegated authority to sanction 18 Crore with IFA."

    scores = nli_model.predict(premise, hypothesis)
    assert scores["entailment"] > 0.70
    assert scores["entailment"] > scores["contradiction"]
    assert scores["entailment"] > scores["neutral"]


def test_nli_contradiction_classification(nli_model):
    """Verify that clearly contradictory statement receives dominant contradiction score."""
    premise = "Under DFPDS-2026 Schedule 07, a Fleet Commander (Tier 3) may sanction up to ₹18.00 Crore with IFA."
    hypothesis = "A Fleet Commander is strictly forbidden from sanctioning any amount above 10 Lakhs."

    scores = nli_model.predict(premise, hypothesis)
    assert scores["contradiction"] > 0.70
    assert scores["contradiction"] > scores["entailment"]


def test_nli_batch_prediction(nli_model):
    """Verify batched inference processes multiple pairs and preserves ordering."""
    pairs = [
        (
            "DFPDS Schedule 1 covers Dry Docking and Ship Repairs in Naval Dockyards.",
            "Schedule 1 pertains to dry docking and naval vessel repairs.",
        ),
        (
            "Open Tender Enquiry (OTE) is mandatory for procurements valued above INR 25 Lakhs.",
            "OTE is never required for goods exceeding 25 Lakhs.",
        ),
        (
            "Performance Bank Guarantee shall be furnished between 3% to 5% of contract value.",
            "PBG is between 3 percent and 5 percent of contract value.",
        ),
    ]

    batch_results = nli_model.predict_batch(pairs)

    assert len(batch_results) == 3
    # Pair 0: Entailment
    assert batch_results[0]["entailment"] > 0.60
    # Pair 1: Contradiction
    assert batch_results[1]["contradiction"] > 0.60
    # Pair 2: Entailment
    assert batch_results[2]["entailment"] > 0.60


def test_nli_inference_latency_budget(nli_model):
    """Verify inference latency is within the real-time operational budget."""
    premise = "Under DFPDS-2026 Schedule 18, a Commanding Officer may sanction local purchases up to ₹2.00 Lakhs without IFA."
    hypothesis = "A CO may approve 2 Lakhs without IFA under Schedule 18."

    # Warmup
    for _ in range(3):
        _ = nli_model.predict(premise, hypothesis)

    # Average over 5 runs
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        _ = nli_model.predict(premise, hypothesis)
        times.append((time.perf_counter() - t0) * 1000)

    avg_ms = sum(times) / len(times)
    assert avg_ms < 250.0, f"Average inference took {avg_ms:.2f}ms, exceeding budget"

