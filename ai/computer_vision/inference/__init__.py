"""
InfraGuard AI
Computer Vision — Inference Package

Exposes the public inference API so callers can import with a single line:

    from inference.predictor import load_predictor
    from inference.predictor import Predictor, Detection, BoundingBox

Typical usage:

    # Load once (e.g. FastAPI startup)
    predictor = load_predictor(warmup=True)

    # Run per request
    detections = predictor.predict_image("road.jpg")
    payload    = predictor.format_predictions(detections)
"""

from inference.predictor import (
    BoundingBox,
    Detection,
    Predictor,
    load_predictor,
)

__all__ = [
    "BoundingBox",
    "Detection",
    "Predictor",
    "load_predictor",
]
