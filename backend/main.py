"""
InfraGuard AI — FastAPI Inference Service

Exposes the YOLOv8 road damage detector as an HTTP API.

Endpoints:
    GET  /          — health check (model loaded status, class names)
    POST /predict   — upload an image, receive structured detections

The Predictor (YOLO model) is loaded ONCE during application startup via
the lifespan context manager and stored in app.state.  Every request
handler accesses it through the get_predictor() dependency — the model
is never reloaded between requests.

Running the server:
    # From the project root (InfraGuard-AI/)
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

    # Or directly from backend/
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Environment variables (all optional, override config.py defaults):
    INFRAGUARD_WEIGHTS   — path to a .pt weights file
    INFRAGUARD_CONF      — confidence threshold (float, e.g. "0.4")
    INFRAGUARD_IOU       — IoU threshold (float, e.g. "0.5")
    INFRAGUARD_DEVICE    — device ("0", "cpu")
"""

import io
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Resolve paths so both `uvicorn backend.main:app` (from project root) and
# `uvicorn main:app` (from backend/) work correctly.
# ---------------------------------------------------------------------------

_BACKEND_DIR  = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_AI_ROOT      = _PROJECT_ROOT / "ai" / "computer_vision"

# Add ai/computer_vision to sys.path so `from configs.config import …`
# and `from inference.predictor import …` resolve correctly.
if str(_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ROOT))

# ---------------------------------------------------------------------------
# Project imports — must come AFTER sys.path adjustment
# ---------------------------------------------------------------------------

from configs.config import CLASS_NAMES, PRODUCTION_WEIGHTS, TRAINING_CONFIG  # noqa: E402
from inference.predictor import Predictor, load_predictor                      # noqa: E402
from backend.schemas import (                                                   # noqa: E402
    BoundingBoxSchema,
    DetectionSchema,
    ErrorResponse,
    HealthResponse,
    ImageSizeSchema,
    PredictResponse,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("infraguard.api")

# ---------------------------------------------------------------------------
# Application constants
# ---------------------------------------------------------------------------

APP_VERSION = "1.0.0"
APP_TITLE   = "InfraGuard AI — Road Damage Detection API"
APP_DESC    = (
    "YOLOv8-powered inference service that detects potholes, longitudinal "
    "cracks, transverse cracks, and alligator cracks in road surface images."
)

# Accepted MIME types for uploaded images
_ACCEPTED_MIME_TYPES: frozenset[str] = frozenset({
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/bmp",
    "image/tiff",
    "image/webp",
})

# Accepted file extensions (checked when MIME type is octet-stream / absent)
_ACCEPTED_EXTENSIONS: frozenset[str] = frozenset({
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp",
})

# Maximum upload size in bytes (10 MB)
_MAX_IMAGE_BYTES: int = 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# Environment-variable overrides
# ---------------------------------------------------------------------------

def _resolve_weights() -> Path:
    """Return the weights path from env var or config.py default."""
    env_val = os.getenv("INFRAGUARD_WEIGHTS")
    return Path(env_val) if env_val else PRODUCTION_WEIGHTS


def _resolve_conf() -> float:
    """Return the confidence threshold from env var or config default (0.25)."""
    env_val = os.getenv("INFRAGUARD_CONF")
    return float(env_val) if env_val else 0.25


def _resolve_iou() -> float:
    """Return the IoU threshold from env var or config default (0.7)."""
    env_val = os.getenv("INFRAGUARD_IOU")
    return float(env_val) if env_val else 0.7


def _resolve_device() -> Any:
    """Return the device from env var or config default (0 = first GPU)."""
    env_val = os.getenv("INFRAGUARD_DEVICE")
    return env_val if env_val else 0


# ===========================================================================
# Application lifespan — model loaded ONCE here
# ===========================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan handler.

    Everything before ``yield`` runs at startup; everything after runs
    at shutdown.  The Predictor is stored in ``app.state.predictor`` so
    it is accessible from any request handler via the dependency system.
    """
    weights = _resolve_weights()
    logger.info("Starting InfraGuard AI inference service  v%s", APP_VERSION)
    logger.info("Loading model from: %s", weights)

    try:
        predictor = load_predictor(
            weights_path=weights,
            config_path=TRAINING_CONFIG,
            class_names=CLASS_NAMES,
            warmup=True,
        )
        app.state.predictor     = predictor
        app.state.model_loaded  = True
        app.state.model_name    = weights.name
        logger.info(
            "Model ready — classes: %s  conf: %.2f  iou: %.2f",
            predictor.class_names,
            predictor.default_conf,
            predictor.default_iou,
        )
    except (FileNotFoundError, ImportError, RuntimeError) as exc:
        # Log the error but allow the app to start in a degraded state so
        # GET / can still respond with model_loaded=false instead of refusing
        # all connections.
        logger.error("Failed to load model: %s", exc)
        app.state.predictor    = None
        app.state.model_loaded = False
        app.state.model_name   = weights.name

    yield  # ← application serves requests here

    logger.info("InfraGuard AI inference service shutting down.")


# ===========================================================================
# Application instance
# ===========================================================================

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESC,
    version=APP_VERSION,
    lifespan=lifespan,
    responses={
        status.HTTP_400_BAD_REQUEST:           {"model": ErrorResponse},
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"model": ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE:   {"model": ErrorResponse},
    },
)

# ---------------------------------------------------------------------------
# CORS — allow all origins for now; tighten when Flutter origin is known
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ===========================================================================
# Dependency — Predictor access
# ===========================================================================

def get_predictor(request: Request) -> Predictor:
    """
    FastAPI dependency that returns the loaded Predictor.

    Raises HTTP 503 if the model failed to load at startup so that every
    endpoint that needs inference gets a consistent error without
    duplicating the check.

    Args:
        request: Injected by FastAPI.

    Returns:
        The application-scoped :class:`~inference.predictor.Predictor`.

    Raises:
        HTTPException 503: If the model is not loaded.
    """
    predictor: Predictor | None = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Model is not available.  The service started in degraded mode "
                "because weights/best.pt could not be loaded.  "
                "Check server logs for details."
            ),
        )
    return predictor


# Annotated shorthand for use in endpoint signatures
PredictorDep = Annotated[Predictor, Depends(get_predictor)]


# ===========================================================================
# Helper — image decoding
# ===========================================================================

def _decode_image_bytes(raw: bytes, filename: str) -> "tuple[Any, int, int]":
    """
    Decode raw image bytes into a numpy array.

    Uses PIL for decoding (no OpenCV dependency required) and converts to
    RGB numpy array that Ultralytics accepts.

    Args:
        raw:      Raw bytes from the uploaded file.
        filename: Original filename (used for error messages only).

    Returns:
        Tuple of ``(numpy_array, width, height)``.

    Raises:
        HTTPException 400: If the bytes cannot be decoded as an image.
    """
    try:
        from PIL import Image  # type: ignore
        import numpy as np     # type: ignore

        pil_img = Image.open(io.BytesIO(raw)).convert("RGB")
        width, height = pil_img.size
        np_array = np.array(pil_img)
        return np_array, width, height
    except Exception as exc:
        logger.warning("Image decode failed for '%s': %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not decode image '{filename}'. "
                   "Ensure the file is a valid, uncorrupted image.",
        ) from exc


def _validate_upload(file: UploadFile) -> None:
    """
    Validate that the uploaded file is an accepted image type.

    Checks the MIME type reported by the client, then falls back to the
    file extension if the MIME type is generic or absent.

    Args:
        file: Uploaded file from FastAPI.

    Raises:
        HTTPException 415: If the file type is not accepted.
        HTTPException 400: If no file was provided.
    """
    if file is None or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file was provided.",
        )

    content_type = (file.content_type or "").lower()
    extension    = Path(file.filename).suffix.lower()

    mime_ok = content_type in _ACCEPTED_MIME_TYPES
    ext_ok  = extension in _ACCEPTED_EXTENSIONS

    if not mime_ok and not ext_ok:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{content_type or extension}'.  "
                f"Accepted formats: JPEG, PNG, BMP, TIFF, WebP."
            ),
        )


# ===========================================================================
# Endpoints
# ===========================================================================

@app.get(
    "/",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Returns the service status and model metadata.  "
        "Use this endpoint to verify the server is running and the "
        "model loaded successfully before submitting predictions."
    ),
    tags=["Health"],
)
async def health_check(request: Request) -> HealthResponse:
    """
    Return service health and model status.

    Does not require the model to be loaded — always responds with the
    current state so monitoring tools can detect a degraded deployment.
    """
    model_loaded: bool = getattr(request.app.state, "model_loaded", False)
    model_name:   str  = getattr(request.app.state, "model_name",   "unknown")
    predictor: Predictor | None = getattr(request.app.state, "predictor", None)

    class_names = predictor.class_names if predictor is not None else CLASS_NAMES

    return HealthResponse(
        status="ok" if model_loaded else "degraded",
        model_loaded=model_loaded,
        model_name=model_name,
        version=APP_VERSION,
        class_names=class_names,
    )


@app.post(
    "/predict",
    response_model=PredictResponse,
    summary="Run road damage detection",
    description=(
        "Upload a road surface image (JPEG, PNG, BMP, TIFF, or WebP) and "
        "receive a list of detected road damage instances.  "
        "Each detection includes class name, confidence score, and a "
        "bounding box in absolute pixel coordinates.\n\n"
        "**conf** and **iou** query parameters allow per-request threshold "
        "overrides without restarting the server."
    ),
    tags=["Inference"],
    responses={
        status.HTTP_400_BAD_REQUEST:           {"model": ErrorResponse,
                                                "description": "Invalid or undecodable image"},
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {"model": ErrorResponse,
                                                 "description": "Unsupported file type"},
        status.HTTP_503_SERVICE_UNAVAILABLE:   {"model": ErrorResponse,
                                                "description": "Model not loaded"},
    },
)
async def predict(
    predictor: PredictorDep,
    file: UploadFile = File(
        ...,
        description="Road surface image file (JPEG, PNG, BMP, TIFF, WebP)",
    ),
    conf: float | None = Query(
        default=None,
        ge=0.01,
        le=1.0,
        description=(
            "Confidence threshold override for this request.  "
            "Lower values return more detections; higher values increase precision.  "
            "Defaults to the value in training_config.yaml (0.25)."
        ),
    ),
    iou: float | None = Query(
        default=None,
        ge=0.01,
        le=1.0,
        description=(
            "IoU (NMS) threshold override for this request.  "
            "Lower values suppress more overlapping boxes.  "
            "Defaults to the value in training_config.yaml (0.7)."
        ),
    ),
) -> PredictResponse:
    """
    Detect road damage in the uploaded image.

    The YOLO model runs in the same thread as the request handler.  For
    production deployments with high request volume, run uvicorn with
    multiple workers (--workers N) or move inference to a background
    thread pool with ``run_in_threadpool``.
    """
    # ------------------------------------------------------------------
    # 1. Validate file type
    # ------------------------------------------------------------------
    _validate_upload(file)

    # ------------------------------------------------------------------
    # 2. Read bytes (enforce size limit)
    # ------------------------------------------------------------------
    raw = await file.read()
    if len(raw) > _MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Image file is too large ({len(raw) / 1_048_576:.1f} MB).  "
                f"Maximum allowed size is {_MAX_IMAGE_BYTES // 1_048_576} MB."
            ),
        )

    # ------------------------------------------------------------------
    # 3. Decode image
    # ------------------------------------------------------------------
    np_array, img_width, img_height = _decode_image_bytes(
        raw, file.filename or "upload"
    )

    # ------------------------------------------------------------------
    # 4. Run inference
    # ------------------------------------------------------------------
    t_start = time.perf_counter()
    try:
        detections = predictor.predict_image(
            np_array,
            conf=conf,
            iou=iou,
        )
    except RuntimeError as exc:
        # Log the full exception server-side; return a sanitised message
        logger.error(
            "Inference error for '%s': %s", file.filename, exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during inference.  "
                   "The image was received but the model failed to process it.  "
                   "Check server logs for details.",
        ) from exc
    finally:
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.info(
            "POST /predict  file='%s'  size=%dx%d  detections=%d  %.1f ms",
            file.filename,
            img_width,
            img_height,
            len(detections) if "detections" in dir() else -1,
            elapsed_ms,
        )

    # ------------------------------------------------------------------
    # 5. Build response
    # ------------------------------------------------------------------
    detection_schemas = [
        DetectionSchema(
            class_id=d.class_id,
            class_name=d.class_name,
            confidence=d.confidence,
            bounding_box=BoundingBoxSchema(
                x1=d.bounding_box.x1,
                y1=d.bounding_box.y1,
                x2=d.bounding_box.x2,
                y2=d.bounding_box.y2,
            ),
        )
        for d in detections
    ]

    effective_conf = conf if conf is not None else predictor.default_conf
    effective_iou  = iou  if iou  is not None else predictor.default_iou

    return PredictResponse(
        filename=file.filename or "upload",
        image_size=ImageSizeSchema(width=img_width, height=img_height),
        detections=detection_schemas,
        detection_count=len(detection_schemas),
        conf_threshold=effective_conf,
        iou_threshold=effective_iou,
    )
