"""
InfraGuard AI — Risk Assessment Schemas

Pydantic v2 models for the CV-based inspection risk assessment layer.
No scoring logic lives here — only the data contract.

These models are imported by:
    backend/risk/scorer.py      (builds RiskAssessmentOut instances)
    backend/schemas/prediction.py  (embeds RiskAssessmentOut in PredictionResponse)
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Risk level enum
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    """
    Bucketed inspection-priority level derived from the continuous score.

    Using ``str`` as a mixin ensures JSON serialisation produces the
    string value (e.g. ``"HIGH"``) rather than the enum object, which
    is what FastAPI's JSON encoder and the Flutter client both expect.
    """

    LOW      = "LOW"
    MODERATE = "MODERATE"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Per-detection risk contribution
# ---------------------------------------------------------------------------

class DetectionRiskOut(BaseModel):
    """
    Risk contribution of a single YOLO detection.

    Included in :class:`RiskAssessmentOut` so consumers can trace
    exactly how each detection influenced the final score.
    """

    class_name: str = Field(
        ...,
        description="Damage class label (mirrors the parent DetectionOut)",
    )
    severity_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Heuristic damage-priority weight assigned to this class.  "
            "This is NOT a probability of structural failure."
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "YOLO model confidence used as a trust multiplier.  "
            "Higher confidence means the scorer trusts this detection more, "
            "not that the damage is physically more severe."
        ),
    )
    normalised_area: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Bounding-box area divided by image area, clamped to [0, 1].  "
            "0.0 when image dimensions are unavailable."
        ),
    )
    detection_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Per-detection score contribution (0–100) before aggregation.  "
            "Formula: severity_weight × confidence × (1 + AREA_BOOST × "
            "normalised_area) × 100, clamped to [0, 100]."
        ),
    )


# ---------------------------------------------------------------------------
# Inspection-level risk assessment
# ---------------------------------------------------------------------------

class RiskAssessmentOut(BaseModel):
    """
    Aggregated risk assessment for one inspection run.

    Appended to :class:`~backend.schemas.prediction.PredictionResponse`
    as an additional field so the existing API contract is unchanged and
    clients that do not yet consume this block are unaffected.
    """

    score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Continuous inspection-priority score (0–100).  "
            "Higher values indicate higher maintenance urgency.  "
            "See methodology_note for interpretation guidance."
        ),
    )
    level: RiskLevel = Field(
        ...,
        description="Bucketed risk level derived from the score.",
    )
    detection_risks: list[DetectionRiskOut] = Field(
        default_factory=list,
        description=(
            "Per-detection risk breakdown, one entry per YOLO detection, "
            "ordered by detection_score descending."
        ),
    )
    dominant_damage: str | None = Field(
        default=None,
        description=(
            "Class name of the detection that contributed the highest "
            "individual score.  None when no detections are present."
        ),
    )
    score_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Named contributions to the final score for explainability.  "
            "Keys: anchor_score, breadth_bonus, final_score, detection_count."
        ),
    )
    recommendation: str = Field(
        ...,
        description=(
            "Maintenance-priority action text for this risk level.  "
            "Does NOT recommend automatic road closure."
        ),
    )
    methodology_note: str = Field(
        ...,
        description=(
            "Fixed caveat string explaining the scoring limitations.  "
            "Must be displayed alongside the score in any user-facing UI."
        ),
    )
