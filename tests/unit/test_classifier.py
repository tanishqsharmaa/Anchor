"""
test_classifier.py — Unit Tests for Two-Tier Question Classifier
"""

import pytest
from anchor.retrieve.classifier import QuestionClassifier, ClassificationResult


@pytest.fixture(scope="module")
def classifier():
    """Module-level fixture providing QuestionClassifier."""
    return QuestionClassifier()


# 10 Structured Benchmark Questions
STRUCTURED_BENCHMARK_QUESTIONS = [
    (
        "What is the financial limit for a Fleet Commander under Schedule 7 with IFA?",
        7,
        "Tier 3",
        True,
        False,
    ),
    (
        "Can Chief of Naval Staff sanction ₹100 Cr under Schedule 1 without IFA concurrence?",
        1,
        "Tier 1",
        False,
        False,
    ),
    (
        "Under Schedule 18, what can a CO Frigate approve with IFA?",
        18,
        "Tier 5",
        True,
        False,
    ),
    (
        "What is the L2 ceiling for DFPDS Schedule 32 with IFA?",
        32,
        "Tier 2",
        True,
        False,
    ),
    (
        "Tell me the sanction power of CSO under Schedule 4 without IFA.",
        4,
        "Tier 4",
        False,
        False,
    ),
    (
        "What is the PAC limit for Flag Officer Commanding Western Fleet under Schedule 12?",
        12,
        "Tier 3",
        True,
        True,
    ),
    (
        "What is the sanction threshold for CO Minor War Vessel under Schedule 21 without IFA?",
        21,
        "Tier 6",
        False,
        False,
    ),
    (
        "What power does FOC-in-C have under Schedule 10 with IFA?",
        10,
        "Tier 2",
        True,
        False,
    ),
    (
        "Under DFPDS Schedule VII, what is the sanction power for Tier 3 with IFA?",
        7,
        "Tier 3",
        True,
        False,
    ),
    (
        "What is the mandatory threshold for Open Tender Enquiry (OTE) under DPM 2025?",
        None,
        None,
        True,
        False,
    ),
]

# 5 Interpretive Policy Benchmark Questions
INTERPRETIVE_BENCHMARK_QUESTIONS = [
    "Can a CO Frigate invoke emergency powers to bypass GeM for critical propulsion repair at sea?",
    "Under what specific operational conditions can Single Tender Enquiry (STE) be justified for foreign OEM spares?",
    "Explain the statutory conflict between DFPDS-2026 and DPM-2025 regarding emergency procurement powers.",
    "What are the mandatory Make in India indigenisation guidelines for naval defense acquisitions under DPM?",
    "How does Navy Regulations Part 1 define the statutory duties of an Officer of the Watch during dry dock refits?",
]

# 5 Boundary / Edge-Case Benchmark Questions
EDGE_CASE_BENCHMARK_QUESTIONS = [
    (
        "Schedule 3 Tier 5 without IFA limit",
        "structured",
        3,
        "Tier 5",
        False,
    ),
    (
        "What is the Liquidated Damages (LD) maximum rate and penalty ceiling under DPM 2025 contracts?",
        "structured",
        None,
        None,
        True,
    ),
    (
        "Under Schedule IX, what can Admiral Superintendent Dockyard approve with IFA?",
        "structured",
        9,
        "Tier 3",
        True,
    ),
    (
        "Is Performance Bank Guarantee (PBG) required for contracts under 25 Lakhs?",
        "structured",
        None,
        None,
        True,
    ),
    (
        "Explain the procedure for obtaining Command IFA concurrence when Fleet Commander is deployed in international waters.",
        "interpretive",
        None,
        None,
        True,
    ),
]


@pytest.mark.parametrize(
    "question,expected_sch,expected_tier,expected_ifa,expected_pac",
    STRUCTURED_BENCHMARK_QUESTIONS,
)
def test_structured_query_classification(
    classifier, question, expected_sch, expected_tier, expected_ifa, expected_pac
):
    """Verify classifier correctly tags structured queries and extracts key entities."""
    res = classifier.classify(question)

    assert isinstance(res, ClassificationResult)
    assert res.query_type == "structured"

    if expected_sch is not None:
        assert res.schedule_no == expected_sch
    if expected_tier is not None:
        assert res.tier == expected_tier

    assert res.with_ifa == expected_ifa
    if expected_pac:
        assert res.is_pac is True


@pytest.mark.parametrize("question", INTERPRETIVE_BENCHMARK_QUESTIONS)
def test_interpretive_query_classification(classifier, question):
    """Verify classifier correctly tags complex interpretive / legal questions as Path B."""
    res = classifier.classify(question)

    assert isinstance(res, ClassificationResult)
    assert res.query_type == "interpretive"


@pytest.mark.parametrize(
    "question,expected_type,expected_sch,expected_tier,expected_ifa",
    EDGE_CASE_BENCHMARK_QUESTIONS,
)
def test_edge_case_query_classification(
    classifier, question, expected_type, expected_sch, expected_tier, expected_ifa
):
    """Verify classifier handles Roman numerals, shorthand syntax, and DPM terms."""
    res = classifier.classify(question)

    assert res.query_type == expected_type
    if expected_sch is not None:
        assert res.schedule_no == expected_sch
    if expected_tier is not None:
        assert res.tier == expected_tier
    assert res.with_ifa == expected_ifa


def test_classifier_benchmark_accuracy_above_95_percent(classifier):
    """Benchmark test: Evaluate 20 benchmark test questions and assert accuracy >= 95%."""
    total_questions = 20
    correct = 0

    # 1. 10 Structured
    for q, sch, tier, ifa, pac in STRUCTURED_BENCHMARK_QUESTIONS:
        res = classifier.classify(q)
        if res.query_type == "structured":
            if sch is not None and res.schedule_no != sch:
                continue
            if tier is not None and res.tier != tier:
                continue
            correct += 1

    # 2. 5 Interpretive
    for q in INTERPRETIVE_BENCHMARK_QUESTIONS:
        res = classifier.classify(q)
        if res.query_type == "interpretive":
            correct += 1

    # 3. 5 Edge Cases
    for q, exp_type, sch, tier, ifa in EDGE_CASE_BENCHMARK_QUESTIONS:
        res = classifier.classify(q)
        if res.query_type == exp_type:
            correct += 1

    accuracy = correct / total_questions
    assert accuracy >= 0.95, f"Classifier benchmark accuracy was {accuracy*100:.1f}%, below 95% threshold"
