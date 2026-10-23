"""
InfraGuard AI — Predictor Service

The single point of contact between FastAPI routes and the ML inference
layer.  Routes never call the Predictor directly — they go through this
service.

Responsibilities:
    1. Accept raw image bytes + filename from the router.
    2. Persist the bytes to a temporary file so ``predict_and_save()``
       receives a real Path (Ultralytics requires a file on disk).
    3. Call ``predictor.predict_and_save()`` with optional threshold overrides.
    4. Use the returned :class:`~inference.predictor.PredictResult` directly
       to build the API response — no file is read back from disk.
    5. Remove the temporary file in all exit paths.
    6. Extract image dimensions from the raw bytes (via PIL) and pass them
       to :class:`~backend.risk.scorer.RiskScorer` to enable the normalised
       bounding-box area contribution.

The service does NOT know about HTTP status codes, FastAPI dependencies,
or request/response life cycles — those live in the router layer.
"""

import io
import logging
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Ensure ai/computer_vision is on sys.path so inference.predictor is importable
# regardless of where uvicorn is launched from.
# ---------------------------------------------------------------------------

_BACKEND_DIR  = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_AI_ROOT      = _PROJECT_ROOT / "ai" / "computer_vision"

if str(_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ROOT))

from inference.predictor import PredictResult                                # noqa: E402

from backend.config import SERVER_BASE_URL                                    # noqa: E402
from backend.risk.scorer import DetectionInput, RiskScorer                   # noqa: E402
from backend.schemas.prediction import (                                      # noqa: E402
    BoundingBoxOut,
    DetectionOut,
    PredictionResponse,
)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

logger = logging.getLogger("infraguard.service")

# ---------------------------------------------------------------------------
# Outputs root — absolute, consistent regardless of launch directory
# ---------------------------------------------------------------------------

_OUTPUTS_ROOT = _PROJECT_ROOT / "outputs"

# ---------------------------------------------------------------------------
# Module-level scorer instance — stateless, safe to share across requests
# ---------------------------------------------------------------------------

_scorer = RiskScorer()


# ---------------------------------------------------------------------------
# Image dimension helper
# ---------------------------------------------------------------------------

def _image_dims_from_bytes(
    image_bytes: bytes,
) -> tuple[int, int] | None:
    """
    Return ``(height, width)`` in pixels for the image encoded in
    *image_bytes*, or ``None`` when the bytes cannot be decoded.

    Uses PIL (already a project dependency via Ultralytics) so no new
    package is required.  Matches the ``(height, width)`` convention of
    Ultralytics ``result.orig_shape``.

    Failure is non-fatal: the scorer falls back to ``normalised_area = 0``
    and skips the area-boost term without breaking the prediction.

    Args:
        image_bytes: Raw bytes of the uploaded image.

    Returns:
        ``(height, width)`` tuple, or ``None`` on any error.
    """
    try:
        from PIL import Image as _PILImage  # type: ignore
        with _PILImage.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size     # PIL gives (width, height)
            return (height, width)       # return as (height, width) to match orig_shape
    except Exception as exc:            # noqa: BLE001
        logger.warning(
            "Service: could not read image dimensions — area boost disabled: %s", exc
        )
        return None


class PredictorService:
    """
    Thin orchestration layer wrapping :class:`inference.predictor.Predictor`.

    Args:
        predictor: A fully initialised, warmed-up ``Predictor`` instance
                   created once during application startup.

    Example::

        service = PredictorService(predictor)
        response = service.run(image_bytes, "road.jpg")
        print(response.run_id, response.total_detections)
    """

    def __init__(self, predictor: Any) -> None:
        self._predictor = predictor

    def run(
        self,
        image_bytes: bytes,
        filename: str,
        *,
        conf: float | None = None,
        iou: float | None = None,
    ) -> PredictionResponse:
        """
        Run inference on *image_bytes* and return a structured response.

        Writes the bytes to a temporary file, calls ``predict_and_save()``,
        assembles the :class:`~backend.schemas.prediction.PredictionResponse`
        from the in-memory :class:`~inference.predictor.PredictResult`, and
        attaches a :class:`~backend.schemas.risk.RiskAssessmentOut` computed
        by :class:`~backend.risk.scorer.RiskScorer`.

        The temporary file is removed in a ``finally`` block on all paths.

        Risk assessment failures are caught and logged but do NOT propagate
        — the prediction response is always returned even if scoring fails.
        Only unexpected programming errors (AttributeError, etc.) are allowed
        to surface so they are visible during development.

        Args:
            image_bytes: Raw bytes of the uploaded image.
            filename:    Original filename; its suffix is used for the temp
                         file so Ultralytics infers the correct image format.
            conf:        Confidence threshold override (``None`` → predictor
                         default from training_config.yaml).
            iou:         IoU (NMS) threshold override (``None`` → predictor
                         default).

        Returns:
            Populated :class:`~backend.schemas.prediction.PredictionResponse`.

        Raises:
            RuntimeError: Propagated from ``predict_and_save()`` on inference
                          or I/O failure.  The router converts this to HTTP 500.
        """
        suffix   = Path(filename).suffix or ".jpg"
        tmp_path: Path | None = None
        t_start  = time.perf_counter()

        try:
            # ----------------------------------------------------------
            # 1. Persist bytes to a named temp file
            # ----------------------------------------------------------
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = Path(tmp.name)

            logger.info(
                "Service.run  file='%s'  bytes=%d  tmp='%s'",
                filename, len(image_bytes), tmp_path,
            )
            logger.info("Service.run  starting inference …")

            # ----------------------------------------------------------
            # 2. Extract image dimensions before handing off to inference.
            #    Done here — not inside the predictor — so the predictor
            #    stays unmodified.  PIL is already a transitive dependency
            #    of Ultralytics.
            # ----------------------------------------------------------
            image_dims = _image_dims_from_bytes(image_bytes)
            if image_dims is not None:
                logger.debug(
                    "Service.run  image_dims=(h=%d, w=%d)", *image_dims
                )
            else:
                logger.debug(
                    "Service.run  image_dims unavailable — area boost skipped"
                )

            # ----------------------------------------------------------
            # 3. Run inference — all ML work stays inside the predictor
            # ----------------------------------------------------------
            result: PredictResult = self._predictor.predict_and_save(
                image_path=tmp_path,
                output_root=_OUTPUTS_ROOT,
                conf=conf,
                iou=iou,
            )

            elapsed_ms = (time.perf_counter() - t_start) * 1000
            logger.info(
                "Service.run  complete  run_id='%s'  detections=%d  %.1f ms",
                result.run_dir.name,
                result.total_detections,
                elapsed_ms,
            )
            logger.info(
                "Service.run  output_dir='%s'", result.run_dir,
            )

            # ----------------------------------------------------------
            # 4. Build response from in-memory PredictResult — no disk reads
            # ----------------------------------------------------------
            detection_out_list: list[DetectionOut] = [
                DetectionOut(
                    class_id=d.class_id,
                    class_name=d.class_name,
                    confidence=d.confidence,
                    bounding_box=BoundingBoxOut(
                        x1=d.bounding_box.x1,
                        y1=d.bounding_box.y1,
                        x2=d.bounding_box.x2,
                        y2=d.bounding_box.y2,
                    ),
                )
                for d in result.detections
            ]

            # Build an HTTP URL for the annotated image so any network
            # client (Flutter on Android, browser, etc.) can fetch it
            # directly.  The /outputs static mount in main.py serves this
            # directory, so the relative sub-path is all that's needed.
            annotated_rel = result.annotated_image_path.relative_to(
                _OUTPUTS_ROOT
            ).as_posix()   # forward slashes required in URLs on all platforms
            annotated_url = f"{SERVER_BASE_URL}/outputs/{annotated_rel}"

            # ----------------------------------------------------------
            # 5. Risk assessment — additive, never breaks the prediction
            # ----------------------------------------------------------
            scorer_inputs: list[DetectionInput] = [
                DetectionInput(
                    class_name=d.class_name,
                    confidence=d.confidence,
                    bbox_x1=d.bounding_box.x1,
                    bbox_y1=d.bounding_box.y1,
                    bbox_x2=d.bounding_box.x2,
                    bbox_y2=d.bounding_box.y2,
                )
                for d in result.detections
            ]

            # ValueError / TypeError from bad data are treated as expected
            # edge cases and handled gracefully.  Any other exception is
            # intentionally not caught here so programming errors surface.
            try:
                risk_assessment = _scorer.score_inspection(
                    scorer_inputs, image_dims
                )
                logger.info(
                    "Service.run  risk  score=%.1f  level=%s  dominant=%s",
                    risk_assessment.score,
                    risk_assessment.level.value,
                    risk_assessment.dominant_damage,
                )
            except (ValueError, TypeError) as exc:
                # Unexpected data shape — fall back to zero-risk so the
                # prediction response is always complete and valid.
                logger.warning(
                    "Service.run  risk scoring failed (data error) — "
                    "using zero-risk fallback: %s",
                    exc,
                )
                risk_assessment = _scorer.score_inspection([], None)

            return PredictionResponse(
                status="success",
                run_id=result.run_dir.name,
                annotated_image=annotated_url,
                detections_file=str(result.detections_file_path),
                summary_file=str(result.summary_file_path),
                detections=detection_out_list,
                total_detections=result.total_detections,
                risk_assessment=risk_assessment,
            )

        finally:
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError as exc:
                    logger.warning(
                        "Service.run  could not remove temp file '%s': %s",
                        tmp_path, exc,
                    )
