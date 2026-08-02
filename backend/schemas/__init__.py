"""InfraGuard AI — Backend Schemas Package."""
from backend.schemas.prediction import (
    BoundingBoxOut,
    DetectionOut,
    PredictionResponse,
    ErrorResponse,
    HealthResponse,
)

__all__ = [
    "BoundingBoxOut",
    "DetectionOut",
    "PredictionResponse",
    "ErrorResponse",
    "HealthResponse",
]
