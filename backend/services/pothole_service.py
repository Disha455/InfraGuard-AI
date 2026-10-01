from pathlib import Path
from typing import Any

from ultralytics import YOLO


class PotholeService:
    """
    Uses the previously trained 4-class YOLO model as a pothole specialist.

    The model contains:
        0 = pothole
        1 = longitudinal_crack
        2 = transverse_crack
        3 = alligator_crack

    Only pothole detections are returned.
    """

    def __init__(self, weights_path: Path) -> None:
        self._model = YOLO(str(weights_path))

    def predict(
        self,
        image_path: Path,
        conf: float = 0.15,
        iou: float = 0.70,
    ) -> list[dict[str, Any]]:
        result = self._model.predict(
            source=str(image_path),
            conf=conf,
            iou=iou,
            verbose=False,
            device="cpu",
        )[0]

        detections: list[dict[str, Any]] = []

        if result.boxes is None:
            return detections

        for box in result.boxes:
            class_id = int(box.cls.item())
            confidence = float(box.conf.item())

            if class_id != 0:
                continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()

            detections.append(
                {
                    "class_id": 3,
                    "class_name": "pothole",
                    "confidence": confidence,
                    "x1": float(x1),
                    "y1": float(y1),
                    "x2": float(x2),
                    "y2": float(y2),
                }
            )

        return detections