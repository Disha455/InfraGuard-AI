"""
InfraGuard AI — Prediction Schemas

Pydantic v2 models for the layered prediction API.  No business logic
lives here — only the data contract between the router and the client.

These models are deliberately separate from the original ``backend/schemas.py``
so the existing simple API is not disturbed.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class BoundingBoxOut(BaseModel):
    """Bounding box in absolute pixel coordinates (top-left origin)."""

    x1: float = Field(..., description="Left edge (pixels)")
    y1: float = Field(..., description="Top edge (pixels)")
    x2: float = Field(..., description="Right edge (pixels)")
    y2: float = Field(..., description="Bottom edge (pixels)")


class DetectionOut(BaseModel):
    """A single object detection, serialised from :class:`inference.predictor.Detection`."""

    class_id:     int          = Field(..., description="Integer class index (0-based)")
    class_name:   str          = Field(..., description="Human-readable class label")
    confidence:   float        = Field(..., ge=0.0, le=1.0,
                                       description="Detection confidence score")
    bounding_box: BoundingBoxOut = Field(
        ..., description="Bounding box in absolute pixel coordinates"
    )


# ---------------------------------------------------------------------------
# Endpoint response models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Response body for ``GET /``."""

    status:       str       = Field(..., description="'ok' or 'degraded'")
    model_loaded: bool      = Field(..., description="True when YOLO model is ready")
    model_name:   str       = Field(..., description="Weights filename")
    version:      str       = Field(..., description="Application version string")
    class_names:  list[str] = Field(..., description="Ordered detection class names")


class PredictionResponse(BaseModel):
    """
    Response body for ``POST /predict``.

    In addition to the structured detections list, the response includes
    the paths to all four output files written by ``predict_and_save()``
    so the client can retrieve the annotated image or full JSON payload.
    """

    status:           str              = Field(
        ..., description="'success' or 'error'"
    )
    run_id:           str              = Field(
        ..., description="Timestamped run folder name (e.g. run_20260726_191422)"
    )
    annotated_image:  str              = Field(
        ..., description="Path to the annotated image written to disk"
    )
    detections_file:  str              = Field(
        ..., description="Path to detections.json written to disk"
    )
    summary_file:     str              = Field(
        ..., description="Path to summary.txt written to disk"
    )
    detections:       list[DetectionOut] = Field(
        default_factory=list,
        description="All detections above the confidence threshold, "
                    "sorted by confidence descending",
    )
    total_detections: int              = Field(
        ..., ge=0, description="Number of detections returned"
    )


# ---------------------------------------------------------------------------
# Error response model (for OpenAPI schema documentation)
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Standard FastAPI error envelope produced by HTTPException."""

    detail: str = Field(..., description="Human-readable error description")
