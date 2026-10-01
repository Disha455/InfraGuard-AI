"""
InfraGuard AI — Predictor Service

The single point of contact between FastAPI routes and the ML inference
layer. Routes never call the Predictor directly — they go through this
service.

Responsibilities:
    1. Accept raw image bytes + filename from the router.
    2. Persist the bytes to a temporary file.
    3. Run the 9-class YOLO road-damage detector.
    4. Run the legacy 4-class YOLO model as a pothole specialist.
    5. Combine the pothole detections with the 9-class detections.
    6. Run XGBoost severity prediction using the combined detections.
    7. Build the API response from in-memory results.
    8. Remove the temporary file in all exit paths.
"""

import logging
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from PIL import Image

# ---------------------------------------------------------------------------
# Ensure ai/computer_vision is on sys.path so inference.predictor is importable
# ---------------------------------------------------------------------------

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_AI_ROOT = _PROJECT_ROOT / "ai" / "computer_vision"

if str(_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ROOT))

from inference.predictor import PredictResult  # noqa: E402
from backend.services.severity_service import SeverityService  # noqa: E402
from backend.services.pothole_service import PotholeService  # noqa: E402
from backend.config import SERVER_BASE_URL  # noqa: E402
from backend.schemas.prediction import (  # noqa: E402
    BoundingBoxOut,
    DetectionOut,
    PredictionResponse,
)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

logger = logging.getLogger("infraguard.service")

# ---------------------------------------------------------------------------
# Outputs root
# ---------------------------------------------------------------------------

_OUTPUTS_ROOT = _PROJECT_ROOT / "outputs"


class PredictorService:
    """
    Orchestration layer wrapping:
        - 9-class YOLO predictor
        - legacy pothole specialist
        - XGBoost severity model
    """

    def __init__(self, predictor: Any) -> None:
        self._predictor = predictor
        self._severity_service = SeverityService()

        # Legacy 4-class model.
        # We use ONLY its pothole class (class 0).
        pothole_weights = (
            _PROJECT_ROOT
            / "ai"
            / "computer_vision"
            / "weights"
            / "best_4class_backup.pt"
        )

        self._pothole_service = PotholeService(pothole_weights)

        logger.info(
            "Pothole specialist loaded from '%s'",
            pothole_weights,
        )

    def run(
        self,
        image_bytes: bytes,
        filename: str,
        *,
        conf: float | None = None,
        iou: float | None = None,
    ) -> PredictionResponse:
        """
        Run 9-class YOLO detection, recover potholes using the legacy
        pothole specialist, then run XGBoost severity prediction.
        """

        suffix = Path(filename).suffix or ".jpg"
        tmp_path: Path | None = None
        t_start = time.perf_counter()

        try:
            # ----------------------------------------------------------
            # 1. Persist uploaded image to a temporary file
            # ----------------------------------------------------------
            with tempfile.NamedTemporaryFile(
                suffix=suffix,
                delete=False,
            ) as tmp:
                tmp.write(image_bytes)
                tmp_path = Path(tmp.name)

            logger.info(
                "Service.run  file='%s'  bytes=%d  tmp='%s'",
                filename,
                len(image_bytes),
                tmp_path,
            )

            # ----------------------------------------------------------
            # 2. Run the main 9-class YOLO inference
            # ----------------------------------------------------------
            logger.info("Service.run  starting 9-class YOLO inference...")

            result: PredictResult = self._predictor.predict_and_save(
                image_path=tmp_path,
                output_root=_OUTPUTS_ROOT,
                conf=conf,
                iou=iou,
            )

            # ----------------------------------------------------------
            # 3. Get actual uploaded image dimensions
            # ----------------------------------------------------------
            with Image.open(tmp_path) as image:
                image_width, image_height = image.size

            logger.info(
                "Service.run  image_size=%dx%d",
                image_width,
                image_height,
            )

            # ----------------------------------------------------------
            # 4. Run legacy pothole specialist
            # ----------------------------------------------------------
            logger.info(
                "Service.run  starting legacy pothole specialist..."
            )

            pothole_detections = self._pothole_service.predict(
                image_path=tmp_path,
                conf=0.15,
                iou=iou if iou is not None else 0.70,
            )

            logger.info(
                "Service.run  pothole specialist found %d potholes",
                len(pothole_detections),
            )

            # ----------------------------------------------------------
            # 5. Convert specialist detections into the same detection
            #    format used by PredictResult.
            #
            #    We intentionally keep this local rather than changing
            #    inference.predictor.py.
            # ----------------------------------------------------------
            combined_detections = list(result.detections)

            for pothole in pothole_detections:
                combined_detections.append(
                    _make_detection(
                        class_id=pothole["class_id"],
                        class_name=pothole["class_name"],
                        confidence=pothole["confidence"],
                        x1=pothole["x1"],
                        y1=pothole["y1"],
                        x2=pothole["x2"],
                        y2=pothole["y2"],
                    )
                )

            logger.info(
                "Service.run  main_detections=%d  pothole_detections=%d  "
                "combined=%d",
                len(result.detections),
                len(pothole_detections),
                len(combined_detections),
            )

            # ----------------------------------------------------------
            # 6. Run XGBoost severity prediction using COMBINED
            #    detections.
            # ----------------------------------------------------------
            severity_result = self._severity_service.predict(
                detections=combined_detections,
                image_width=image_width,
                image_height=image_height,
            )

            severity = severity_result["severity"]
            severity_probability = severity_result["severity_probability"]

            logger.info(
                "Service.run  severity='%s'  high_probability=%.4f",
                severity,
                severity_probability,
            )

            # ----------------------------------------------------------
            # 7. Timing / inference logging
            # ----------------------------------------------------------
            elapsed_ms = (time.perf_counter() - t_start) * 1000

            logger.info(
                "Service.run  complete  run_id='%s'  detections=%d  %.1f ms",
                result.run_dir.name,
                len(combined_detections),
                elapsed_ms,
            )

            logger.info(
                "Service.run  output_dir='%s'",
                result.run_dir,
            )

            # ----------------------------------------------------------
            # 8. Convert combined detections to API response objects
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
                for d in combined_detections
            ]

            # ----------------------------------------------------------
            # 9. Build URL for annotated image
            #
            # NOTE:
            # The annotated image is still generated by the main 9-class
            # predictor. Pothole specialist boxes are included in the API
            # detections and severity calculation, but are not yet drawn
            # onto the annotated image.
            # ----------------------------------------------------------
            annotated_rel = (
                result.annotated_image_path
                .relative_to(_OUTPUTS_ROOT)
                .as_posix()
            )

            annotated_url = (
                f"{SERVER_BASE_URL}/outputs/{annotated_rel}"
            )

            # ----------------------------------------------------------
            # 10. Return complete prediction response
            # ----------------------------------------------------------
            return PredictionResponse(
                status="success",
                run_id=result.run_dir.name,
                annotated_image=annotated_url,
                detections_file=str(result.detections_file_path),
                summary_file=str(result.summary_file_path),
                detections=detection_out_list,
                total_detections=len(combined_detections),
                severity=severity,
                severity_probability=severity_probability,
            )

        finally:
            # ----------------------------------------------------------
            # 11. Always remove temporary uploaded image
            # ----------------------------------------------------------
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError as exc:
                    logger.warning(
                        "Service.run  could not remove temp file '%s': %s",
                        tmp_path,
                        exc,
                    )


def _make_detection(
    *,
    class_id: int,
    class_name: str,
    confidence: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> Any:
    """
    Create a detection object compatible with the objects returned by
    inference.predictor.PredictResult.

    We import the concrete detection class dynamically so this service
    remains compatible with the existing predictor module.
    """

    from inference.predictor import BoundingBox, Detection

    return Detection(
        class_id=class_id,
        class_name=class_name,
        confidence=confidence,
        bounding_box=BoundingBox(
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
        ),
    )