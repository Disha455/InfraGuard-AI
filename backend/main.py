"""
InfraGuard AI — FastAPI Application Entry Point

This is the single entry point for the inference API.

Architecture
------------
All routing, service, dependency, and schema logic lives in dedicated
sub-modules.  This file is a thin composition root — its only jobs are:
    1. Configure sys.path so project modules are importable.
    2. Run the lifespan (load model once at startup, log shutdown).
    3. Create the ``FastAPI`` instance, attach CORS, and mount routers.
    4. Expose the lightweight ``GET /`` health endpoint.

Layer map
---------
    main.py                         ← you are here
    ├── backend/routers/prediction.py   POST /predict route handler
    ├── backend/dependencies.py         get_predictor_service() Depends()
    ├── backend/services/               PredictorService orchestration
    │   └── predictor_service.py
    └── backend/schemas/                Pydantic v2 response models
        └── prediction.py

Running the server
------------------
    # From the project root (InfraGuard-AI/)
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

    # From InfraGuard-AI/backend/
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Environment variables (all optional)
-------------------------------------
    INFRAGUARD_WEIGHTS  — path to a .pt weights file
    INFRAGUARD_CONF     — confidence threshold float (e.g. "0.35")
    INFRAGUARD_IOU      — IoU threshold float (e.g. "0.6")

API documentation (when running)
----------------------------------
    http://localhost:8000/docs    — Swagger UI
    http://localhost:8000/redoc  — ReDoc

Example curl request
---------------------
    curl -X POST "http://localhost:8000/predict" \\
         -F "file=@road.jpg" \\
         -F "conf=0.3"
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# sys.path — must run before any project import
# Supports both launch contexts:
#   uvicorn backend.main:app   (cwd = InfraGuard-AI/)
#   uvicorn main:app           (cwd = InfraGuard-AI/backend/)
# ---------------------------------------------------------------------------

_BACKEND_DIR  = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_AI_ROOT      = _PROJECT_ROOT / "ai" / "computer_vision"
_OUTPUTS_ROOT = _PROJECT_ROOT / "outputs"

if str(_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ROOT))

# ---------------------------------------------------------------------------
# Project imports — after sys.path
# ---------------------------------------------------------------------------

from configs.config import CLASS_NAMES, PRODUCTION_WEIGHTS, TRAINING_CONFIG  # noqa: E402
from inference.predictor import load_predictor                                 # noqa: E402

from backend.routers import prediction as prediction_router                    # noqa: E402
from backend.schemas.prediction import HealthResponse                          # noqa: E402
from backend.services.predictor_service import PredictorService                # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("infraguard.main")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APP_VERSION = "2.0.0"
APP_TITLE   = "InfraGuard AI — Road Damage Detection API"
APP_DESC    = (
    "YOLOv8 inference service that detects **potholes**, "
    "**longitudinal cracks**, **transverse cracks**, and **alligator cracks** "
    "in road surface images.\n\n"
    "Each prediction produces:\n"
    "- Structured JSON detections (class, confidence, bounding box)\n"
    "- Annotated image rendered by Ultralytics\n"
    "- Human-readable summary text file\n\n"
    "All artefacts are persisted in a timestamped run directory."
)

# ---------------------------------------------------------------------------
# Env-var helpers
# ---------------------------------------------------------------------------

def _weights_path() -> Path:
    v = os.getenv("INFRAGUARD_WEIGHTS")
    return Path(v) if v else PRODUCTION_WEIGHTS


# ===========================================================================
# Lifespan — model loaded ONCE
# ===========================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load the YOLO model and wrap it in PredictorService before the first
    request.  Store the service in ``app.state`` so the dependency system
    can inject it into route handlers.

    If loading fails the app starts in degraded mode: ``GET /`` reports
    ``model_loaded: false`` and ``POST /predict`` returns HTTP 503.
    """
    weights = _weights_path()
    logger.info("InfraGuard AI  v%s  starting up …", APP_VERSION)
    logger.info("Weights : %s", weights)

    try:
        predictor = load_predictor(
            weights_path=weights,
            config_path=TRAINING_CONFIG,
            class_names=CLASS_NAMES,
            warmup=True,
        )
        app.state.predictor_service = PredictorService(predictor)
        app.state.model_loaded      = True
        app.state.model_name        = weights.name

        logger.info(
            "Model ready  |  device: %s  |  conf: %.2f  |  iou: %.2f",
            predictor._device,
            predictor.default_conf,
            predictor.default_iou,
        )
        logger.info("Service READY — accepting requests.")

    except (FileNotFoundError, ImportError, RuntimeError) as exc:
        logger.error("Model failed to load: %s", exc)
        logger.warning(
            "Starting in DEGRADED mode.  "
            "GET / → model_loaded=false  |  POST /predict → HTTP 503."
        )
        app.state.predictor_service = None
        app.state.model_loaded      = False
        app.state.model_name        = weights.name

    yield

    logger.info("InfraGuard AI shutting down.")


# ===========================================================================
# Application instance
# ===========================================================================

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESC,
    version=APP_VERSION,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # tighten when Flutter origin is known
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static files — outputs directory served at /outputs
#
# Allows clients (Flutter app, browser) to fetch annotated images and
# other run artefacts over HTTP.
# The directory is created at runtime by the predictor; mount is safe to
# register at startup even if the directory is initially empty.
# ---------------------------------------------------------------------------

_OUTPUTS_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(_OUTPUTS_ROOT)), name="outputs")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(prediction_router.router)


# ===========================================================================
# Health endpoint
# ===========================================================================

@app.get(
    "/",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Returns service status and model metadata.  "
        "Always responds — even in degraded mode — so monitoring tools "
        "can detect a failed startup."
    ),
    tags=["Health"],
)
async def health_check(request: Request) -> HealthResponse:
    """
    Return service health and model status.

    Does not require the model to be loaded.

    Args:
        request: Injected by FastAPI.

    Returns:
        :class:`~backend.schemas.prediction.HealthResponse`
    """
    model_loaded: bool = getattr(request.app.state, "model_loaded", False)
    model_name:   str  = getattr(request.app.state, "model_name",   "unknown")
    service: PredictorService | None = getattr(
        request.app.state, "predictor_service", None
    )
    class_names = (
        service._predictor.class_names if service is not None else CLASS_NAMES
    )

    return HealthResponse(
        status="ok" if model_loaded else "degraded",
        model_loaded=model_loaded,
        model_name=model_name,
        version=APP_VERSION,
        class_names=class_names,
    )
