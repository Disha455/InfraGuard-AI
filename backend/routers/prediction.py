"""
InfraGuard AI — Prediction Router

Handles all HTTP concerns for the ``/predict`` endpoint:
    - receiving the multipart upload
    - validating file type and size
    - delegating all ML work to ``PredictorService``
    - mapping service results to HTTP responses
    - mapping service errors to HTTP errors

This module contains zero ML logic.  The only object from the inference
layer it uses is the Pydantic response schema.
"""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status

from backend.dependencies import PredictorServiceDep
from backend.schemas.prediction import ErrorResponse, PredictionResponse

# ---------------------------------------------------------------------------
# Router logger
# ---------------------------------------------------------------------------

logger = logging.getLogger("infraguard.router.prediction")

# ---------------------------------------------------------------------------
# Accepted image types
# ---------------------------------------------------------------------------

_ACCEPTED_MIME: frozenset[str] = frozenset({
    "image/jpeg", "image/jpg", "image/png",
    "image/bmp", "image/tiff", "image/webp",
})
_ACCEPTED_EXT: frozenset[str] = frozenset({
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp",
})
_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/predict", tags=["Inference"])


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_upload(file: UploadFile) -> None:
    """
    Validate the uploaded file is a supported image format.

    Checks the MIME type first; falls back to extension check when the
    client sends ``application/octet-stream`` or omits the content-type.

    Args:
        file: Uploaded file from FastAPI.

    Raises:
        :class:`fastapi.HTTPException` 400: No file provided.
        :class:`fastapi.HTTPException` 415: Unsupported file type.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file was provided.",
        )

    mime = (file.content_type or "").lower()
    ext  = Path(file.filename).suffix.lower()

    if mime not in _ACCEPTED_MIME and ext not in _ACCEPTED_EXT:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{mime or ext}'.  "
                "Accepted formats: JPEG, PNG, BMP, TIFF, WebP."
            ),
        )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=PredictionResponse,
    summary="Detect road damage",
    description=(
        "Upload a road surface image and receive structured detections.\n\n"
        "The server runs inference via the loaded YOLOv8 model and returns:\n"
        "- a unique run identifier\n"
        "- paths to the annotated image, detections JSON, and summary text\n"
        "- the full structured detection list\n\n"
        "Optional ``conf`` and ``iou`` query parameters allow per-request "
        "threshold overrides without restarting the server."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Missing, oversized, or undecodable image",
        },
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
            "model": ErrorResponse,
            "description": "Unsupported file format",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Inference or I/O failure",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "Model not loaded at startup",
        },
    },
)
async def predict(
    service: PredictorServiceDep,
    file: UploadFile = File(
        ...,
        description="Road surface image (JPEG, PNG, BMP, TIFF, or WebP)",
    ),
    conf: float | None = Query(
        default=None,
        ge=0.01,
        le=1.0,
        description=(
            "Confidence threshold override.  "
            "Defaults to the value in training_config.yaml."
        ),
    ),
    iou: float | None = Query(
        default=None,
        ge=0.01,
        le=1.0,
        description=(
            "IoU (NMS) threshold override.  "
            "Defaults to the value in training_config.yaml."
        ),
    ),
) -> PredictionResponse:
    """
    Detect road damage in the uploaded image.

    Delegates all inference work to :class:`~backend.services.predictor_service.PredictorService`.
    This handler is responsible only for HTTP validation and response mapping.

    Args:
        service: Injected ``PredictorService`` (raises 503 if unavailable).
        file:    Uploaded image file.
        conf:    Per-request confidence threshold override.
        iou:     Per-request IoU threshold override.

    Returns:
        :class:`~backend.schemas.prediction.PredictionResponse` with run
        metadata and structured detections.

    Raises:
        :class:`fastapi.HTTPException` 400: Bad image.
        :class:`fastapi.HTTPException` 415: Unsupported format.
        :class:`fastapi.HTTPException` 500: Inference failure.
        :class:`fastapi.HTTPException` 503: Model not loaded.
    """
    # ------------------------------------------------------------------
    # 1. Validate format
    # ------------------------------------------------------------------
    _validate_upload(file)

    # ------------------------------------------------------------------
    # 2. Read bytes and enforce size limit
    # ------------------------------------------------------------------
    raw_bytes = await file.read()
    if len(raw_bytes) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Image is too large ({len(raw_bytes) / 1_048_576:.1f} MB).  "
                f"Maximum allowed: {_MAX_BYTES // 1_048_576} MB."
            ),
        )

    filename = file.filename or "upload.jpg"
    logger.info(
        "POST /predict  file='%s'  size=%d bytes  conf=%s  iou=%s",
        filename, len(raw_bytes), conf, iou,
    )

    # ------------------------------------------------------------------
    # 3. Delegate to service — all inference happens here
    # ------------------------------------------------------------------
    try:
        response = service.run(raw_bytes, filename, conf=conf, iou=iou)
    except RuntimeError as exc:
        logger.error(
            "POST /predict  inference error for '%s': %s",
            filename, exc, exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "An error occurred during inference.  "
                "The image was received but the model failed to process it.  "
                "Check server logs for details."
            ),
        ) from exc

    logger.info(
        "POST /predict  run_id='%s'  detections=%d",
        response.run_id, response.total_detections,
    )
    return response
