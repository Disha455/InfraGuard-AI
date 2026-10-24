"""InfraGuard AI — Backend Schemas Package."""
from backend.schemas.prediction import (
    BoundingBoxOut,
    DetectionOut,
    PredictionResponse,
    ErrorResponse,
    HealthResponse,
)
from backend.schemas.risk import (
    RiskLevel,
    DetectionRiskOut,
    RiskAssessmentOut,
)

__all__ = [
    # prediction
    "BoundingBoxOut",
    "DetectionOut",
    "PredictionResponse",
    "ErrorResponse",
    "HealthResponse",
    # risk
    "RiskLevel",
    "DetectionRiskOut",
    "RiskAssessmentOut",
]
