"""
schemas.py — Pydantic AST Schemas for AutoDeck AI Briefing Presentation Engine
"""

from enum import Enum
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


class SlideType(str, Enum):
    """Supported naval briefing slide archetypes."""
    HERO_SLIDE = "HERO_SLIDE"
    BLUF_EXECUTIVE = "BLUF_EXECUTIVE"
    POLICY_MATRIX = "POLICY_MATRIX"
    FINANCIAL_DELEGATION = "FINANCIAL_DELEGATION"


class ClassificationMarking(str, Enum):
    """Standard security classification markings."""
    UNCLASSIFIED = "UNCLASSIFIED"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"
    SECRET = "SECRET"
    RESTRICTED_OFFICIAL = "RESTRICTED // FOR OFFICIAL USE ONLY"


class UrgencyTier(str, Enum):
    """Operational urgency tiers for naval BLUF briefings."""
    ROUTINE = "ROUTINE"
    PRIORITY = "PRIORITY"
    OPERATIONAL_IMMEDIATE = "OPERATIONAL_IMMEDIATE"


class HeroSlideContent(BaseModel):
    """
    Title and metadata slide content adhering to Indian Naval Staff briefing standards.
    """
    title: str = Field(..., max_length=100, description="Main briefing title (<= 100 chars)")
    subtitle: Optional[str] = Field(None, max_length=160, description="Briefing subtitle or operation name")
    dtg: Optional[str] = Field(None, max_length=40, description="Date-Time Group (e.g. 310300Z AUG 2026)")
    classification: str = Field(
        default=ClassificationMarking.RESTRICTED_OFFICIAL.value,
        max_length=60,
        description="Slide classification marking",
    )
    officer: Optional[str] = Field(None, max_length=100, description="Presenter rank, name, and appointment")
    unit: Optional[str] = Field(None, max_length=100, description="Command / Directorate / Ship name")


class BLUFSlideContent(BaseModel):
    """
    Bottom Line Up Front executive summary slide content.
    """
    bluf_headline: str = Field(..., max_length=200, description="Core executive decision / finding summary")
    key_takeaways: List[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="1 to 5 concise takeaways (<= 180 chars each)",
    )
    decision_requested: str = Field(..., max_length=200, description="Specific CFA sanction or decision sought")
    risk_summary: Optional[str] = Field(None, max_length=180, description="Operational or financial risk synthesis")
    urgency: UrgencyTier = Field(default=UrgencyTier.PRIORITY, description="Urgency tier")

    @field_validator("key_takeaways")
    @classmethod
    def validate_takeaway_lengths(cls, v: List[str]) -> List[str]:
        for idx, item in enumerate(v):
            if len(item) > 180:
                raise ValueError(f"Takeaway [{idx}] exceeds 180 character limit (length={len(item)})")
        return v


class MatrixRow(BaseModel):
    """Row in a regulatory comparison matrix."""
    row_title: str = Field(..., max_length=80, description="Row subject or clause title")
    cells: List[str] = Field(..., min_length=1, max_length=5, description="Cell values for columns")

    @field_validator("cells")
    @classmethod
    def validate_cell_lengths(cls, v: List[str]) -> List[str]:
        for idx, cell in enumerate(v):
            if len(cell) > 120:
                raise ValueError(f"Matrix cell [{idx}] exceeds 120 character budget (length={len(cell)})")
        return v


class PolicyMatrixSlideContent(BaseModel):
    """
    Comparative policy matrix contrasting statutory rules, delegations, or procedures.
    """
    matrix_title: str = Field(..., max_length=120, description="Title of the policy comparison")
    headers: List[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="2 to 5 column header names (<= 50 chars each)",
    )
    rows: List[MatrixRow] = Field(..., min_length=1, max_length=6, description="1 to 6 comparison rows")
    statutory_precedence_note: Optional[str] = Field(
        None,
        max_length=200,
        description="Precedence hierarchy note (e.g. DFPDS-2026 > DPM-2025 > Navy Regs)",
    )

    @field_validator("headers")
    @classmethod
    def validate_header_lengths(cls, v: List[str]) -> List[str]:
        for idx, h in enumerate(v):
            if len(h) > 50:
                raise ValueError(f"Header [{idx}] exceeds 50 character limit (length={len(h)})")
        return v

    @model_validator(mode="after")
    def validate_cell_counts_match_headers(self) -> "PolicyMatrixSlideContent":
        expected_cols = len(self.headers)
        for idx, row in enumerate(self.rows):
            valid = (len(row.cells) == expected_cols) or (len(row.cells) + 1 == expected_cols)
            if not valid:
                raise ValueError(
                    f"Row [{idx}] ('{row.row_title}') has {len(row.cells)} cells, incompatible with {expected_cols} headers"
                )
        return self


class FinancialTierItem(BaseModel):
    """CFA delegation limit entry for a financial schedule slide."""
    tier: str = Field(..., max_length=40, description="Tier identifier (e.g. 'Tier 1', 'Tier 2')")
    tier_name: str = Field(..., max_length=100, description="CFA appointment name")
    with_ifa_limit: float = Field(..., ge=0.0, description="Sanction limit in INR Crore with IFA")
    without_ifa_limit: float = Field(..., ge=0.0, description="Sanction limit in INR Crore without IFA")
    pac_limit: Optional[float] = Field(None, ge=0.0, description="PAC / Sole source limit in INR Crore")
    unit_str: str = Field(default="₹ Crore", max_length=20, description="Currency denomination")


class FinancialDelegationSlideContent(BaseModel):
    """
    Financial delegation and CFA limit schedule breakdown.
    """
    schedule_title: str = Field(..., max_length=150, description="Schedule heading and description")
    schedule_no: int = Field(..., ge=1, le=32, description="DFPDS-2026 Schedule number (1 to 32)")
    head_of_account: Optional[str] = Field(None, max_length=100, description="Budget head code or description")
    tiers: List[FinancialTierItem] = Field(
        ...,
        min_length=1,
        max_length=6,
        description="1 to 6 CFA tier entries",
    )
    indigenisation_percentage: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Minimum mandatory indigenisation percentage (e.g. 50.0%)",
    )
    notes: Optional[str] = Field(None, max_length=200, description="Statutory notes or PAC provisos")


SlideContentUnion = Union[
    HeroSlideContent,
    BLUFSlideContent,
    PolicyMatrixSlideContent,
    FinancialDelegationSlideContent,
]


class SlideItem(BaseModel):
    """
    Individual slide container holding archetype metadata, content block, and NLI verification annotations.
    """
    slide_id: str = Field(..., max_length=40, description="Unique slide identifier")
    type: SlideType = Field(..., description="Slide archetype")
    title: str = Field(..., max_length=120, description="Slide heading banner")
    content: SlideContentUnion = Field(..., description="Structured content payload")
    classification: str = Field(
        default=ClassificationMarking.RESTRICTED_OFFICIAL.value,
        max_length=60,
        description="Slide-level classification banner",
    )
    is_verified: bool = Field(default=False, description="Whether claims are verified by DeBERTa NLI")
    nli_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum entailment score across slide claims")
    source_citation: Optional[str] = Field(None, max_length=150, description="Source regulatory reference")

    @model_validator(mode="after")
    def validate_content_matches_type(self) -> "SlideItem":
        type_mapping = {
            SlideType.HERO_SLIDE: HeroSlideContent,
            SlideType.BLUF_EXECUTIVE: BLUFSlideContent,
            SlideType.POLICY_MATRIX: PolicyMatrixSlideContent,
            SlideType.FINANCIAL_DELEGATION: FinancialDelegationSlideContent,
        }
        expected_cls = type_mapping.get(self.type)
        if expected_cls and not isinstance(self.content, expected_cls):
            if isinstance(self.content, dict):
                try:
                    self.content = expected_cls.model_validate(self.content)
                except Exception as e:
                    raise ValueError(f"Content for slide type {self.type.value} does not conform to {expected_cls.__name__}: {e}") from e
            else:
                raise ValueError(
                    f"Content type {type(self.content).__name__} does not match slide type {self.type.value}"
                )
        return self


# Type alias for external AST consumers
SlideASTItem = SlideItem


class SlideDeckAST(BaseModel):
    """
    Complete Abstract Syntax Tree (AST) representing a multi-slide briefing deck.
    """
    deck_id: str = Field(..., max_length=60, description="Unique deck identifier")
    title: str = Field(..., max_length=140, description="Briefing deck main title")
    topic: str = Field(..., max_length=200, description="Query / topic prompt initiating the deck")
    classification: str = Field(
        default=ClassificationMarking.RESTRICTED_OFFICIAL.value,
        max_length=60,
        description="Deck-wide classification marking",
    )
    dtg: Optional[str] = Field(None, max_length=40, description="Date-Time Group timestamp")
    slides: List[SlideItem] = Field(..., min_length=1, max_length=12, description="Ordered list of slides")
    total_slides: int = Field(default=0, description="Total slide count")
    generation_time_ms: Optional[int] = Field(None, ge=0, description="Total generation latency in milliseconds")

    @model_validator(mode="after")
    def compute_total_slides(self) -> "SlideDeckAST":
        self.total_slides = len(self.slides)
        return self


class DeckVerificationResult(BaseModel):
    """
    Verification report assessing factuality of all slide claims.
    """
    deck_id: str
    all_claims_verified: bool
    lowest_nli_score: float = Field(..., ge=0.0, le=1.0)
    total_claims: int = Field(default=0, ge=0)
    verified_claims_count: int = Field(default=0, ge=0)
    flagged_claims: List[dict[str, Any]] = Field(default_factory=list)
