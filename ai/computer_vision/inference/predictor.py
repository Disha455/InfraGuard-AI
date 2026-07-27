"""
InfraGuard AI
Computer Vision — Inference Predictor

Purpose:
    Provide a reusable, FastAPI-ready inference interface for the production
    YOLOv8 road damage detection model.  This module is intentionally
    independent of FastAPI — it is a plain Python module that any caller
    can import.

Input:
    weights/best.pt              — production model (PRODUCTION_WEIGHTS)
    configs/training_config.yaml — default confidence / IoU / device settings

Output:
    list[Detection]  — structured detections for a single image
    list[list[Detection]]  — structured detections for a batch of images

    Each Detection contains:
        class_id      : int
        class_name    : str
        confidence    : float  (0.0 – 1.0)
        bounding_box  : BoundingBox(x1, y1, x2, y2)  — absolute pixel coords

Responsibilities:
    1. Load and validate the production model exactly once.
    2. Accept images as file paths, URL strings, or numpy / PIL objects.
    3. Run inference with configurable confidence / IoU / device thresholds.
    4. Convert raw Ultralytics results into project-friendly Python structures.
    5. Never expose Ultralytics objects to callers.

Execution:
    # From ai/computer_vision/
    python inference/predictor.py --image path/to/image.jpg

    # Programmatic usage:
    from inference.predictor import load_predictor
    predictor = load_predictor()
    detections = predictor.predict_image("road.jpg")
    for d in detections:
        print(d.to_dict())
"""

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

import yaml

from configs.config import CLASS_NAMES, PRODUCTION_WEIGHTS, TRAINING_CONFIG
from utils.utils import IMAGE_EXTENSIONS, get_logger

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Input type alias — everything predict_image() will accept
# ---------------------------------------------------------------------------

# Acceptable image inputs: file path (str or Path), numpy array, or PIL Image.
# The type is kept broad so type checkers don't require numpy/PIL imports at
# the module level (both are optional runtime dependencies for callers).
ImageInput = Union[str, Path, Any]


# ===========================================================================
# Prediction data structures
# ===========================================================================

@dataclass
class BoundingBox:
    """
    Axis-aligned bounding box in absolute pixel coordinates.

    Origin is the top-left corner of the image (standard image convention).

    Attributes:
        x1: Left edge (pixels).
        y1: Top edge (pixels).
        x2: Right edge (pixels).
        y2: Bottom edge (pixels).
    """
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        """Bounding box width in pixels."""
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        """Bounding box height in pixels."""
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        """Bounding box area in square pixels."""
        return self.width * self.height

    @property
    def centre(self) -> tuple[float, float]:
        """Centre point (cx, cy) in pixels."""
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def to_dict(self) -> dict[str, float]:
        """
        Serialise to a plain dict suitable for JSON responses.

        Returns:
            ``{"x1": ..., "y1": ..., "x2": ..., "y2": ...}``
        """
        return {
            "x1": round(self.x1, 2),
            "y1": round(self.y1, 2),
            "x2": round(self.x2, 2),
            "y2": round(self.y2, 2),
        }


@dataclass
class Detection:
    """
    A single object detection result.

    Attributes:
        class_id:     Integer class index (matches CLASS_NAMES in config.py).
        class_name:   Human-readable class label.
        confidence:   Detection confidence score in [0.0, 1.0].
        bounding_box: Predicted bounding box in absolute pixel coordinates.
    """
    class_id:     int
    class_name:   str
    confidence:   float
    bounding_box: BoundingBox

    def to_dict(self) -> dict[str, Any]:
        """
        Serialise to a plain dict suitable for JSON responses.

        Returns::

            {
                "class_id":    0,
                "class_name":  "pothole",
                "confidence":  0.8734,
                "bounding_box": {"x1": 120.5, "y1": 88.0,
                                 "x2": 340.2, "y2": 210.7}
            }
        """
        return {
            "class_id":    self.class_id,
            "class_name":  self.class_name,
            "confidence":  round(self.confidence, 6),
            "bounding_box": self.bounding_box.to_dict(),
        }


# ===========================================================================
# Configuration helpers
# ===========================================================================

def load_inference_config(config_path: Path) -> dict[str, Any]:
    """
    Load inference-relevant thresholds from training_config.yaml.

    Reads only the ``validation`` and ``training`` sections.  Returns
    sensible defaults when the file is absent so the predictor works
    standalone without a config file.

    Args:
        config_path: Path to training_config.yaml.

    Returns:
        Dict with keys: ``conf_threshold``, ``iou_threshold``,
        ``image_size``, ``device``.
    """
    defaults: dict[str, Any] = {
        "conf_threshold": 0.25,
        "iou_threshold":  0.7,
        "image_size":     640,
        "device":         0,
    }

    if not config_path.exists():
        logger.debug(
            "Config not found at '%s' — using inference defaults.", config_path
        )
        return defaults

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        logger.warning(
            "Could not parse config '%s': %s — using defaults.", config_path, exc
        )
        return defaults

    v = cfg.get("validation", {})
    t = cfg.get("training", {})

    return {
        "conf_threshold": float(v.get("conf_threshold", defaults["conf_threshold"])),
        "iou_threshold":  float(v.get("iou_threshold",  defaults["iou_threshold"])),
        "image_size":     int(t.get("image_size",       defaults["image_size"])),
        "device":         t.get("device",               defaults["device"]),
    }


# ===========================================================================
# Model loading helpers
# ===========================================================================

def _validate_weights(weights_path: Path) -> None:
    """
    Confirm the weights file exists before attempting to load it.

    Args:
        weights_path: Path to the ``.pt`` weights file.

    Raises:
        FileNotFoundError: With a clear, actionable message if absent.
    """
    if not weights_path.exists():
        raise FileNotFoundError(
            f"Model weights not found: '{weights_path}'\n"
            "  → Run training/train.py first to produce weights/best.pt."
        )
    logger.info(
        "Weights validated: %s  (%.1f MB)",
        weights_path.name,
        weights_path.stat().st_size / 1_048_576,
    )


def _load_yolo_model(weights_path: Path) -> Any:
    """
    Instantiate a YOLO model from *weights_path*.

    Args:
        weights_path: Path to a trained ``.pt`` file.

    Returns:
        Ultralytics ``YOLO`` model instance.

    Raises:
        ImportError: If ``ultralytics`` is not installed.
        RuntimeError: If the model cannot be loaded.
    """
    try:
        from ultralytics import YOLO  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "The 'ultralytics' package is not installed.\n"
            "Run: pip install ultralytics"
        ) from exc

    try:
        model = YOLO(str(weights_path))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to load YOLO model from '{weights_path}': {exc}"
        ) from exc

    logger.info("YOLO model loaded: %s", weights_path.name)
    return model


# ===========================================================================
# Result parsing
# ===========================================================================

def _parse_single_result(
    result: Any,
    class_names: list[str],
) -> list[Detection]:
    """
    Convert one Ultralytics ``Results`` object into a list of
    :class:`Detection` instances.

    Ultralytics stores per-image detections in ``result.boxes``:
        - ``result.boxes.xyxy``   — absolute pixel coords, shape (N, 4)
        - ``result.boxes.conf``   — confidence scores, shape (N,)
        - ``result.boxes.cls``    — integer class IDs, shape (N,)

    Args:
        result:       Single Ultralytics Results object (one image).
        class_names:  Ordered class name list from config.py.

    Returns:
        List of :class:`Detection` objects, one per detected box.
        Empty list if no detections were made.
    """
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    detections: list[Detection] = []

    try:
        # .xyxy returns a tensor/array of shape (N, 4) — absolute pixel coords
        xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, "cpu") else boxes.xyxy
        confs = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else boxes.conf
        clses = boxes.cls.cpu().numpy()  if hasattr(boxes.cls,  "cpu") else boxes.cls

        for i in range(len(xyxy)):
            x1, y1, x2, y2 = float(xyxy[i][0]), float(xyxy[i][1]), \
                              float(xyxy[i][2]), float(xyxy[i][3])
            conf    = float(confs[i])
            cls_id  = int(clses[i])

            try:
                cls_name = class_names[cls_id]
            except IndexError:
                cls_name = f"class_{cls_id}"

            detections.append(
                Detection(
                    class_id=cls_id,
                    class_name=cls_name,
                    confidence=round(conf, 6),
                    bounding_box=BoundingBox(
                        x1=round(x1, 2),
                        y1=round(y1, 2),
                        x2=round(x2, 2),
                        y2=round(y2, 2),
                    ),
                )
            )

    except Exception as exc:
        logger.warning("Failed to parse detection boxes: %s", exc)

    return detections


# ===========================================================================
# Predictor class
# ===========================================================================

class Predictor:
    """
    Reusable inference interface for the InfraGuard AI road damage detector.

    The YOLO model is loaded **once** at construction time and reused for
    every subsequent call to :meth:`predict_image` or :meth:`predict_batch`.
    This makes the class safe for use as a long-lived application component
    (e.g. FastAPI application state).

    Args:
        weights_path:  Path to the ``.pt`` model weights.
        config_path:   Path to training_config.yaml for default thresholds.
        class_names:   Ordered class name list (defaults to CLASS_NAMES).

    Example::

        predictor = Predictor()
        detections = predictor.predict_image("road.jpg")
        for d in detections:
            print(d.class_name, d.confidence, d.bounding_box.to_dict())
    """

    def __init__(
        self,
        weights_path: Path = PRODUCTION_WEIGHTS,
        config_path: Path = TRAINING_CONFIG,
        class_names: list[str] = CLASS_NAMES,
    ) -> None:
        self._weights_path = weights_path
        self._class_names  = class_names

        # Load inference config for default thresholds
        self._inf_cfg = load_inference_config(config_path)

        # Validate + load model — raises immediately on failure
        _validate_weights(weights_path)
        self._model = _load_yolo_model(weights_path)

        logger.info(
            "Predictor ready — classes: %s  |  conf: %.2f  |  iou: %.2f  |  device: %s",
            class_names,
            self._inf_cfg["conf_threshold"],
            self._inf_cfg["iou_threshold"],
            self._inf_cfg["device"],
        )

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def class_names(self) -> list[str]:
        """Ordered list of class names this predictor recognises."""
        return list(self._class_names)

    @property
    def weights_path(self) -> Path:
        """Path to the loaded weights file."""
        return self._weights_path

    @property
    def default_conf(self) -> float:
        """Default confidence threshold from config."""
        return self._inf_cfg["conf_threshold"]

    @property
    def default_iou(self) -> float:
        """Default IoU threshold from config."""
        return self._inf_cfg["iou_threshold"]

    # ------------------------------------------------------------------
    # Warmup
    # ------------------------------------------------------------------

    def warmup(self) -> None:
        """
        Prime the model with a single dummy forward pass.

        On CUDA devices the first inference call is significantly slower
        due to kernel compilation.  Calling warmup() once at startup
        (e.g. in a FastAPI lifespan handler) eliminates this latency
        spike on the first real request.

        The dummy image is a 1×3×imgsz×imgsz zero tensor — it produces
        no meaningful detections and its output is discarded.
        """
        try:
            import numpy as np  # type: ignore
            imgsz: int = self._inf_cfg["image_size"]
            dummy = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
            self._model(dummy, verbose=False)
            logger.info("Predictor warmup complete.")
        except Exception as exc:
            logger.warning("Warmup failed (non-fatal): %s", exc)

    # ------------------------------------------------------------------
    # Core inference
    # ------------------------------------------------------------------

    def predict_image(
        self,
        image: ImageInput,
        *,
        conf: float | None = None,
        iou: float | None = None,
        device: Any = None,
    ) -> list[Detection]:
        """
        Run inference on a single image.

        Args:
            image:  Image to run inference on.  Accepted types:
                    - :class:`str` or :class:`~pathlib.Path` — file path or URL
                    - ``numpy.ndarray``  — HWC, BGR or RGB, uint8
                    - ``PIL.Image.Image``
            conf:   Confidence threshold override.  Uses config default if None.
            iou:    IoU (NMS) threshold override.  Uses config default if None.
            device: Device override (``0``, ``"cpu"``).  Uses config default
                    if None.

        Returns:
            List of :class:`Detection` objects sorted by confidence
            (highest first).  Empty list if no objects are detected above
            the confidence threshold.

        Raises:
            ValueError:  If *image* is not a recognised type.
            RuntimeError: If the Ultralytics forward pass fails.
        """
        _conf   = conf   if conf   is not None else self._inf_cfg["conf_threshold"]
        _iou    = iou    if iou    is not None else self._inf_cfg["iou_threshold"]
        _device = device if device is not None else self._inf_cfg["device"]

        # Resolve Path objects to strings so Ultralytics accepts them cleanly
        image_input: Any = str(image) if isinstance(image, Path) else image

        try:
            raw_results = self._model(
                image_input,
                conf=_conf,
                iou=_iou,
                device=_device,
                verbose=False,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Inference failed on image '{image}': {exc}"
            ) from exc

        # Ultralytics returns a list even for single-image input
        if not raw_results:
            return []

        detections = _parse_single_result(raw_results[0], self._class_names)

        # Sort by confidence descending for consistent output ordering
        detections.sort(key=lambda d: d.confidence, reverse=True)

        logger.debug(
            "predict_image: %d detection(s)  conf≥%.2f",
            len(detections), _conf,
        )
        return detections

    def predict_batch(
        self,
        images: list[ImageInput],
        *,
        conf: float | None = None,
        iou: float | None = None,
        device: Any = None,
    ) -> list[list[Detection]]:
        """
        Run inference on a list of images.

        Processes each image individually through :meth:`predict_image`.
        Failed images log a warning and return an empty detection list so
        a single bad image never aborts the entire batch.

        Args:
            images: List of image inputs (same types as :meth:`predict_image`).
            conf:   Confidence threshold override for all images.
            iou:    IoU threshold override for all images.
            device: Device override for all images.

        Returns:
            List of detection lists — one inner list per input image,
            in the same order as *images*.
        """
        results: list[list[Detection]] = []

        for idx, image in enumerate(images):
            try:
                detections = self.predict_image(
                    image, conf=conf, iou=iou, device=device
                )
            except RuntimeError as exc:
                logger.warning(
                    "predict_batch: image[%d] failed — returning empty list.\n"
                    "  Reason: %s",
                    idx, exc,
                )
                detections = []
            results.append(detections)

        logger.debug(
            "predict_batch: %d image(s), total detections: %d",
            len(images),
            sum(len(d) for d in results),
        )
        return results

    def format_predictions(
        self,
        detections: list[Detection],
    ) -> list[dict[str, Any]]:
        """
        Serialise a list of :class:`Detection` objects to plain dicts.

        Convenience wrapper around :meth:`Detection.to_dict` for callers
        that need a fully JSON-serialisable structure (e.g. FastAPI
        response models).

        Args:
            detections: List returned by :meth:`predict_image` or
                        :meth:`predict_batch`.

        Returns:
            List of dicts, one per detection.
        """
        return [d.to_dict() for d in detections]


# ===========================================================================
# Module-level factory
# ===========================================================================

def load_predictor(
    weights_path: Path = PRODUCTION_WEIGHTS,
    config_path: Path = TRAINING_CONFIG,
    class_names: list[str] = CLASS_NAMES,
    *,
    warmup: bool = False,
) -> Predictor:
    """
    Create and return a ready-to-use :class:`Predictor` instance.

    This is the recommended entry-point for all callers — it encapsulates
    construction and optional warmup behind a single function call.

    Args:
        weights_path: Path to ``.pt`` weights.  Defaults to
                      ``PRODUCTION_WEIGHTS`` from config.py.
        config_path:  Path to training_config.yaml.  Defaults to
                      ``TRAINING_CONFIG`` from config.py.
        class_names:  Ordered class name list.  Defaults to
                      ``CLASS_NAMES`` from config.py.
        warmup:       If ``True``, run a dummy forward pass immediately
                      after loading to prime CUDA kernels.  Recommended
                      for server deployments; optional for scripts.

    Returns:
        Initialised :class:`Predictor` instance.

    Example (FastAPI startup)::

        @app.on_event("startup")
        async def startup():
            app.state.predictor = load_predictor(warmup=True)

    Example (script)::

        predictor = load_predictor()
        detections = predictor.predict_image("road.jpg")
    """
    predictor = Predictor(
        weights_path=weights_path,
        config_path=config_path,
        class_names=class_names,
    )
    if warmup:
        predictor.warmup()
    return predictor


# ===========================================================================
# CLI entry-point  (smoke-test / quick demo)
# ===========================================================================

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="InfraGuard AI — inference smoke-test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python inference/predictor.py --image road.jpg\n"
            "  python inference/predictor.py --image road.jpg --conf 0.4\n"
            "  python inference/predictor.py --image road.jpg"
            " --weights weights/archive/best_20260726.pt\n"
        ),
    )
    parser.add_argument(
        "--image",
        type=Path,
        required=True,
        help="Path to an image file to run inference on.",
    )
    parser.add_argument(
        "--weights",
        type=Path,
        default=PRODUCTION_WEIGHTS,
        help=f"Path to .pt model weights.  Default: {PRODUCTION_WEIGHTS}",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=TRAINING_CONFIG,
        help=f"Path to training_config.yaml.  Default: {TRAINING_CONFIG}",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=None,
        help="Confidence threshold override (e.g. 0.4).",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=None,
        help="IoU (NMS) threshold override (e.g. 0.5).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    import json as _json

    args = _parse_args()

    if not args.image.exists():
        logger.error("Image not found: '%s'", args.image)
        sys.exit(1)

    predictor = load_predictor(
        weights_path=args.weights,
        config_path=args.config,
    )

    detections = predictor.predict_image(
        args.image,
        conf=args.conf,
        iou=args.iou,
    )

    print(f"\nImage     : {args.image}")
    print(f"Detections: {len(detections)}\n")

    output = predictor.format_predictions(detections)
    print(_json.dumps(output, indent=2))
    sys.exit(0)
