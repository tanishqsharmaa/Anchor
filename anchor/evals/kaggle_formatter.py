import csv
from pathlib import Path
from typing import Any, Union
from pydantic import BaseModel, ConfigDict, Field

from anchor.retrieve.resolver import ResolverResult


class KaggleRow(BaseModel):
    """Model representing a single row in the competition submission.csv."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(..., min_length=1, description="Unique query identifier (e.g., Q001)")
    prediction: str = Field(..., min_length=1, description="Resolved or generated answer text")
    pred_source: str = Field(..., min_length=1, description="Cited statutory document reference")
    pred_section: str = Field(..., min_length=1, description="Cited clause or table tier reference")


def format_kaggle_row(
    query_id: str, resolver_result: ResolverResult
) -> dict[str, str]:
    """Format a ResolverResult into a standardized Kaggle submission row dictionary."""
    tier_section = f"{resolver_result.tier} ({resolver_result.tier_name})" if resolver_result.tier_name else resolver_result.tier

    row = KaggleRow(
        id=str(query_id),
        prediction=resolver_result.formatted_answer,
        pred_source=resolver_result.reference,
        pred_section=tier_section,
    )
    return row.model_dump()


def export_kaggle_submission_csv(
    results: list[Union[dict[str, Any], KaggleRow]], output_path: Union[str, Path]
) -> Path:
    """Export a list of KaggleRow models or row dicts to standard submission.csv.

    Enforces column order [id, prediction, pred_source, pred_section],
    validates non-null / non-NaN entries, and saves with UTF-8 encoding.
    """
    if not results:
        raise ValueError("Cannot export empty results to Kaggle submission CSV.")

    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["id", "prediction", "pred_source", "pred_section"]
    validated_rows: list[dict[str, str]] = []

    for item in results:
        if isinstance(item, KaggleRow):
            row_dict = item.model_dump()
        elif isinstance(item, dict):
            row_model = KaggleRow.model_validate(item)
            row_dict = row_model.model_dump()
        else:
            raise TypeError(f"Expected dict or KaggleRow, got {type(item).__name__}")
        validated_rows.append(row_dict)

    with open(target_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in validated_rows:
            writer.writerow(row)

    return target_path
