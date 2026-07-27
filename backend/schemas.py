"""
InfraGuard AI — Backend API Schemas

Pydantic v2 models that define every request and response shape for the
inference API.  No business logic lives here — only data contracts.

These models are imported by main.py and can be imported by the Flutter
client team to generate type-safe API code.
"""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class BoundingBoxSchema(BaseModel):
    """
    Axis-aligned bounding box in absolute pixel coordinates.

    Origin is the top-left corner of the image.
    """
    x1: float = Field(..., description="Left edge in pixels")
    y1: float = Field(..., description="Top edge in pixels")
    x2: float = Field(..., description="Right edge in pixels")
    y2: float = Field(..., description="Bottom edge in pixels")


class DetectionSchema(BaseModel):
    """A single object detection result."""
    class_id:     int   = Field(..., description="Integer class index (0-based)")
    class_name:   str   = Field(..., description="Human-readable class label")
    confidence:   float = Field(..., ge=0.0, le=1.0,
                                description="Detection confidence score")
    bounding_box: BoundingBoxSchema = Field(
        ..., description="Bounding box in absolute pixel coordinates"
    )


class ImageSizeSchema(BaseModel):
    """Width and height of the submitted image."""
    width:  int = Field(..., gt=0, description="Image width in pixels")
    height: int = Field(..., gt=0, description="Image height in pixels")


# ---------------------------------------------------------------------------
# Endpoint response models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """
    Response body for GET /.

    Indicates whether the service is running and the model is loaded.
    """
    status:       str       = Field(..., description="'ok' or 'degraded'")
    model_loaded: bool      = Field(..., description="True if YOLO model is ready")
    model_name:   str       = Field(..., description="Weights filename")
    version:      str       = Field(..., description="Application version string")
    class_names:  list[str] = Field(..., description="Ordered detection class names")


class PredictResponse(BaseModel):
    """
    Response body for POST /predict.

    Contains every detection found in the submitted image along with
    metadata about the request.
    """
    filename:        str                  = Field(
        ..., description="Original uploaded filename"
    )
    image_size:      ImageSizeSchema      = Field(
        ..., description="Dimensions of the submitted image"
    )
    detections:      list[DetectionSchema] = Field(
        default_factory=list,
        description="All detections above the confidence threshold, "
                    "sorted by confidence descending",
    )
    detection_count: int   = Field(
        ..., ge=0, description="Number of detections returned"
    )
    conf_threshold:  float = Field(
        ..., description="Confidence threshold used for this request"
    )
    iou_threshold:   float = Field(
        ..., description="IoU (NMS) threshold used for this request"
    )


# ---------------------------------------------------------------------------
# Error response model (used for OpenAPI documentation only)
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """
    Standard error response shape.

    FastAPI produces this automatically for HTTPExceptions.
    Documented here so the OpenAPI schema is explicit.
    """
    detail: str = Field(..., description="Human-readable error description")
