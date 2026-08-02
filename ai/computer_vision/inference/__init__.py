"""
InfraGuard AI
Computer Vision — Inference Package

Public API:

    from inference.predictor import load_predictor
    from inference.predictor import Predictor, Detection, BoundingBox, PredictResult

Typical usage:

    # Load once (e.g. FastAPI startup)
    predictor = load_predictor(warmup=True)

    # Run per request — in-memory result, files saved as side-effect
    result = predictor.predict_and_save("road.jpg")
    print(result.total_detections)
    print(result.annotated_image_path)
"""

from inference.predictor import (
    BoundingBox,
    Detection,
    PredictResult,
    Predictor,
    load_predictor,
)

__all__ = [
    "BoundingBox",
    "Detection",
    "PredictResult",
    "Predictor",
    "load_predictor",
]
