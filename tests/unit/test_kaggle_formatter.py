import csv
from pathlib import Path
import pytest
from pydantic import ValidationError

from anchor.retrieve.resolver import resolve_dfpds_delegation
from anchor.evals.kaggle_formatter import (
    KaggleRow,
    format_kaggle_row,
    export_kaggle_submission_csv,
)

def test_kaggle_row_model_validation_valid():
    """Test that KaggleRow validates compliant records."""
    row = KaggleRow(
        id="Q001",
        prediction="Under DFPDS-2026 Schedule 07, CNS may sanction up to ₹100.00 Cr.",
        pred_source="DFPDS-2026/NAVY/SCH-07",
        pred_section="Tier 1 (Chief of the Naval Staff)",
    )
    assert row.id == "Q001"
    assert "₹100.00" in row.prediction
    assert row.pred_source == "DFPDS-2026/NAVY/SCH-07"
    assert row.pred_section == "Tier 1 (Chief of the Naval Staff)"

def test_kaggle_row_model_validation_rejects_empty_or_none():
    """Test that KaggleRow rejects empty strings, None, or missing fields."""
    with pytest.raises(ValidationError):
        KaggleRow(id="", prediction="Valid", pred_source="Src", pred_section="Sec")
    with pytest.raises(ValidationError):
        KaggleRow(id="Q001", prediction="", pred_source="Src", pred_section="Sec")
    with pytest.raises(ValidationError):
        KaggleRow(id="Q001", prediction="Valid", pred_source="", pred_section="Sec")
    with pytest.raises(ValidationError):
        KaggleRow(id="Q001", prediction="Valid", pred_source="Src", pred_section="")

def test_format_kaggle_row_from_resolver_result():
    """Test format_kaggle_row converts a ResolverResult to competition row dict."""
    result = resolve_dfpds_delegation(schedule_no=7, tier="Tier 3", ifa_concurrence=True)
    assert result is not None
    row_dict = format_kaggle_row("Q042", result)
    assert isinstance(row_dict, dict)
    assert row_dict["id"] == "Q042"
    assert row_dict["prediction"] == result.formatted_answer
    assert row_dict["pred_source"] == "DFPDS-2026/NAVY/SCH-07"
    assert "Tier 3" in row_dict["pred_section"]
    validated = KaggleRow.model_validate(row_dict)
    assert validated.id == "Q042"

def test_export_kaggle_submission_csv_structure_and_types(tmp_path: Path):
    """Test CSV serialization matches exact competition schema and UTF-8 encoding."""
    rows = []
    for sched in [1, 7, 32]:
        res = resolve_dfpds_delegation(schedule_no=sched, tier="Tier 1", ifa_concurrence=True)
        assert res is not None
        rows.append(format_kaggle_row(f"Q_{sched:03d}", res))
    out_csv = tmp_path / "submission.csv"
    exported_path = export_kaggle_submission_csv(rows, out_csv)
    assert exported_path.exists()
    with open(exported_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ["id", "prediction", "pred_source", "pred_section"]
        data_rows = list(reader)
        assert len(data_rows) == 3
        for r in data_rows:
            assert len(r) == 4
            # Assert no empty strings or standalone NaN/None representations
            for col in r:
                assert col.strip() != ""
                assert col.strip().lower() not in ["nan", "none", "null"]
            # Assert Rupee symbol is intact in UTF-8
            assert "₹" in r[1]

def test_export_kaggle_submission_csv_rejects_empty_or_invalid(tmp_path: Path):
    """Test that CSV exporter raises ValueError on empty or invalid input list."""
    out_csv = tmp_path / "empty_submission.csv"
    with pytest.raises(ValueError, match="Cannot export empty results"):
        export_kaggle_submission_csv([], out_csv)

def test_precomputed_resolver_json_completeness():
    """Verify precomputed resolver JSON exists and has all 384 statutory entries."""
    import json
    from anchor.config import settings

    precomputed_file = settings.BASE_DIR / "kaggle" / "precomputed" / "resolver_outputs.json"
    assert precomputed_file.exists(), f"Missing {precomputed_file}"

    with open(precomputed_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 384
    # Test random sample
    sample_key = "SCH-07_Tier_3_with_ifa"
    assert sample_key in data
    entry = data[sample_key]
    assert entry["schedule_no"] == 7
    assert entry["tier"] == "Tier 3"
    assert entry["sanction_limit"] == 21.0
    assert "pred_source" in entry
    assert "pred_section" in entry
    assert "formatted_answer" in entry

    # Assert all entries validate against KaggleRow
    for k, v in data.items():
        row_model = KaggleRow(
            id=k,
            prediction=v["formatted_answer"],
            pred_source=v["pred_source"],
            pred_section=v["pred_section"],
        )
        assert row_model.id == k
