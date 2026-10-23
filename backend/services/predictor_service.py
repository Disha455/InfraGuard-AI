"""
InfraGuard AI — Predictor Service

The single point of contact between FastAPI routes and the ML inference
layer. Routes never call the Predictor directly — they go through this
service.

Responsibilities:
    1. Accept raw image bytes + filename from the router.
    2. Persist the bytes to a temporary file for Ultralytics inference.
    3. Run the primary YOLO road-damage detector.
    4. Run the optional pothole specialist if weights are present.
    5. Run XGBoost severity prediction using combined detections.
    6. Compute CV-based risk assessment (0-100 score and risk level).
    7. Build the API response with reachable annotated image URL.
    8. Remove the temporary file in all exit paths.
"""

import io
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

from inference.predictor import PredictResult                                # noqa: E402
from backend.services.severity_service import SeverityService                # noqa: E402
from backend.services.pothole_service import PotholeService                  # noqa: E402
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
# Outputs root
# ---------------------------------------------------------------------------

_OUTPUTS_ROOT = _PROJECT_ROOT / "outputs"


def _image_dims_from_bytes(
    image_bytes: bytes,
) -> tuple[int, int] | None:
    """Return (height, width) in pixels for the image encoded in image_bytes."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
            return (height, width)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Service: could not read image dimensions from bytes: %s", exc
        )
        return None


class PredictorService:
    """
    Orchestration layer wrapping:
        - Primary YOLO predictor (damage detection & bounding boxes)
        - Legacy pothole specialist (optional if backup weights available)
        - XGBoost severity prediction
        - CV-based risk assessment scorer
    """

    def __init__(self, predictor: Any) -> None:
        self._predictor = predictor
        self._scorer = RiskScorer()

        # Severity model (XGBoost)
        try:
            self._severity_service: SeverityService | None = SeverityService()
            logger.info("SeverityService successfully initialized.")
        except Exception as exc:
            logger.warning("SeverityService initialization skipped: %s", exc)
            self._severity_service = None

        # Pothole specialist (optional fallback)
        pothole_weights = (
            _PROJECT_ROOT
            / "ai"
            / "computer_vision"
            / "weights"
            / "best_4class_backup.pt"
        )
        if pothole_weights.exists():
            try:
                self._pothole_service: PotholeService | None = PotholeService(pothole_weights)
                logger.info("Pothole specialist loaded from '%s'", pothole_weights)
            except Exception as exc:
                logger.warning(
                    "Could not load pothole specialist from '%s': %s",
                    pothole_weights,
                    exc,
                )
                self._pothole_service = None
        else:
            logger.info(
                "Pothole specialist weights not found ('%s') — using primary detector for all classes.",
                pothole_weights,
            )
            self._pothole_service = None

    def run(
        self,
        image_bytes: bytes,
        filename: str,
        *,
        base_url: str | None = None,
        conf: float | None = None,
        iou: float | None = None,
    ) -> PredictionResponse:
        """
        Run YOLO detection, evaluate severity & risk, and return a structured response.
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
            # 2. Get actual uploaded image dimensions
            # ----------------------------------------------------------
            dims = _image_dims_from_bytes(image_bytes)
            if dims is not None:
                image_height, image_width = dims
            else:
                image_height, image_width = (640, 640)

            # ----------------------------------------------------------
            # 3. Run primary YOLO inference (generates annotated image)
            # ----------------------------------------------------------
            logger.info("Service.run  starting primary YOLO inference...")
            result: PredictResult = self._predictor.predict_and_save(
                image_path=tmp_path,
                output_root=_OUTPUTS_ROOT,
                conf=conf,
                iou=iou,
            )

            # ----------------------------------------------------------
            # 4. Run pothole specialist if configured
            # ----------------------------------------------------------
            combined_detections = list(result.detections)

            if self._pothole_service is not None:
                try:
                    pothole_detections = self._pothole_service.predict(
                        image_path=tmp_path,
                        conf=0.15,
                        iou=iou if iou is not None else 0.70,
                    )
                    logger.info(
                        "Service.run  pothole specialist found %d potholes",
                        len(pothole_detections),
                    )
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
                except Exception as exc:
                    logger.warning("Pothole specialist failed: %s", exc)

            # ----------------------------------------------------------
            # 5. Run XGBoost severity prediction
            # ----------------------------------------------------------
            severity = "Low"
            severity_probability = 0.0

            if self._severity_service is not None:
                try:
                    severity_result = self._severity_service.predict(
                        detections=combined_detections,
                        image_width=image_width,
                        image_height=image_height,
                    )
                    severity = severity_result.get("severity", "Low")
                    severity_probability = float(
                        severity_result.get("severity_probability", 0.0)
                    )
                    logger.info(
                        "Service.run  severity='%s'  prob=%.4f",
                        severity,
                        severity_probability,
                    )
                except Exception as exc:
                    logger.warning("Severity prediction error: %s", exc)

            # ----------------------------------------------------------
            # 6. Run RiskScorer assessment
            # ----------------------------------------------------------
            scorer_inputs = [
                DetectionInput(
                    class_name=d.class_name,
                    confidence=d.confidence,
                    bbox_x1=d.bounding_box.x1,
                    bbox_y1=d.bounding_box.y1,
                    bbox_x2=d.bounding_box.x2,
                    bbox_y2=d.bounding_box.y2,
                )
                for d in combined_detections
            ]

            try:
                risk_assessment = self._scorer.score_inspection(
                    scorer_inputs, (image_height, image_width)
                )
            except Exception as exc:
                logger.warning("Risk assessment error: %s", exc)
                risk_assessment = self._scorer.score_inspection([], None)

            # If severity was not provided by XGBoost, sync with risk score
            if self._severity_service is None and risk_assessment.score >= 50.0:
                severity = "High"
                severity_probability = min(1.0, risk_assessment.score / 100.0)

            # ----------------------------------------------------------
            # 7. Convert detections to API response models
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
            # 8. Build URL for annotated image
            # ----------------------------------------------------------
            effective_base_url = (base_url or SERVER_BASE_URL).rstrip("/")
            annotated_rel = (
                result.annotated_image_path
                .relative_to(_OUTPUTS_ROOT)
                .as_posix()
            )
            annotated_url = f"{effective_base_url}/outputs/{annotated_rel}"

            elapsed_ms = (time.perf_counter() - t_start) * 1000
            logger.info(
                "Service.run complete  run_id='%s'  detections=%d  %.1f ms",
                result.run_dir.name,
                len(combined_detections),
                elapsed_ms,
            )

            return PredictionResponse(
                status="success",
                run_id=result.run_dir.name,
                annotated_image=annotated_url,
                detections_file=str(result.detections_file_path),
                summary_file=str(result.summary_file_path),
                detections=detection_out_list,
                total_detections=len(combined_detections),
                risk_assessment=risk_assessment,
                severity=severity,
                severity_probability=severity_probability,
            )

        finally:
            if tmp_path is not None and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError as exc:
                    logger.warning(
                        "Service.run could not remove temp file '%s': %s",
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
    """Create a Detection object compatible with inference.predictor.PredictResult."""
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