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

The service does NOT know about HTTP status codes, FastAPI dependencies,
or request/response life cycles — those live in the router layer.
"""

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
        and assembles the :class:`~backend.schemas.prediction.PredictionResponse`
        entirely from the in-memory :class:`~inference.predictor.PredictResult`
        returned by the predictor.  No file is read back from disk.

        The temporary file is removed in a ``finally`` block on all paths.

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
            # 2. Run inference — all ML work stays inside the predictor
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
            # 3. Build response from in-memory PredictResult — no disk reads
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

            return PredictionResponse(
                status="success",
                run_id=result.run_dir.name,
                annotated_image=str(result.annotated_image_path),
                detections_file=str(result.detections_file_path),
                summary_file=str(result.summary_file_path),
                detections=detection_out_list,
                total_detections=result.total_detections,
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
