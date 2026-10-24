"""
InfraGuard AI — Severity Prediction Service

Connects YOLO detections to the trained XGBoost severity model.
"""

from pathlib import Path
from typing import Any

import joblib
import pandas as pd


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_MODEL_PATH = (
    _PROJECT_ROOT
    / "ai"
    / "risk_prediction"
    / "models"
    / "severity_xgboost.pkl"
)


# ---------------------------------------------------------------------------
# Feature order — MUST match XGBoost training
# ---------------------------------------------------------------------------

FEATURE_COLUMNS = [
    "alligator_crack",
    "block_crack",
    "faded_marking",
    "lane_shoulder_dropoff",
    "linear_crack",
    "patch_utility_cut",
    "pothole",
    "raveling",
    "weathering",
    "total_damage_count",
    "damage_area_ratio",
]


class SeverityService:
    """Runs the trained XGBoost severity model."""

    def __init__(self, model_path: Path = _MODEL_PATH) -> None:
        self.model_path = model_path

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Severity model not found: {self.model_path}"
            )

        self.model: Any = joblib.load(self.model_path)

    def predict(
        self,
        detections: list[Any],
        image_width: int,
        image_height: int,
    ) -> dict[str, Any]:
        """
        Convert YOLO detections into the features expected by XGBoost
        and return the predicted severity.
        """

        if image_width <= 0 or image_height <= 0:
            raise ValueError("Image dimensions must be greater than zero.")

        # ---------------------------------------------------------------
        # Initialize the 9 damage-type features
        # ---------------------------------------------------------------

        features: dict[str, float] = {
            "alligator_crack": 0,
            "block_crack": 0,
            "faded_marking": 0,
            "lane_shoulder_dropoff": 0,
            "linear_crack": 0,
            "patch_utility_cut": 0,
            "pothole": 0,
            "raveling": 0,
            "weathering": 0,
        }

        # ---------------------------------------------------------------
        # Convert YOLO detections into feature values
        # ---------------------------------------------------------------

        total_damage_count = 0
        total_damage_area = 0.0

        for detection in detections:
            class_name = detection.class_name

            if class_name in features:
                features[class_name] += 1

            total_damage_count += 1

            box = detection.bounding_box

            box_width = max(0.0, box.x2 - box.x1)
            box_height = max(0.0, box.y2 - box.y1)

            total_damage_area += box_width * box_height

        # ---------------------------------------------------------------
        # Calculate image-level area ratio
        # ---------------------------------------------------------------

        image_area = float(image_width * image_height)

        damage_area_ratio = (
            total_damage_area / image_area
            if image_area > 0
            else 0.0
        )

        features["total_damage_count"] = total_damage_count
        features["damage_area_ratio"] = damage_area_ratio

        # ---------------------------------------------------------------
        # Create dataframe in EXACT training feature order
        # ---------------------------------------------------------------

        feature_df = pd.DataFrame(
            [[features[column] for column in FEATURE_COLUMNS]],
            columns=FEATURE_COLUMNS,
        )

        # ---------------------------------------------------------------
        # XGBoost prediction
        # ---------------------------------------------------------------

        prediction = int(self.model.predict(feature_df)[0])

        probabilities = self.model.predict_proba(feature_df)[0]

        severity = "High" if prediction == 1 else "Low"

        high_probability = float(probabilities[1])

        return {
            "severity": severity,
            "severity_probability": high_probability,
            "features": features,
        }