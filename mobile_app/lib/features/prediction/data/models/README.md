# data/models

JSON serialisation layer — converts raw Map<String, dynamic> from the
HTTP response into typed Dart objects, and vice versa.

Models live in the data layer because they are tightly coupled to the
backend contract.  Domain entities are kept clean of JSON logic.

## Backend response shape (confirmed from detections.json)

```json
{
  "status": "success",
  "run_id": "run_20260802_125021",
  "annotated_image": "/outputs/run_.../annotated.jpg",
  "detections_file": "/outputs/run_.../detections.json",
  "summary_file":    "/outputs/run_.../summary.txt",
  "total_detections": 2,
  "detections": [
    {
      "class_id": 1,
      "class_name": "longitudinal_crack",
      "confidence": 0.630561,
      "bounding_box": { "x1": 210.11, "y1": 2.4, "x2": 240.32, "y2": 206.48 }
    }
  ]
}
```

## Planned files

### `bounding_box_model.dart`
Parses the `bounding_box` object.  Four fields: x1, y1, x2, y2 (all
double).  Provides `fromJson`, `toJson`, and a mapper to the
`BoundingBox` domain entity.

### `detection_model.dart`
Parses one element of the `detections` array.  Fields: class_id (int),
class_name (String), confidence (double), bounding_box
(BoundingBoxModel).  Provides `fromJson` and a mapper to the `Detection`
domain entity.

### `prediction_result_model.dart`
Parses the full `/predict` response envelope.  Fields: status, run_id,
annotated_image, detections_file, summary_file, total_detections,
detections (List<DetectionModel>).  Provides `fromJson` and a mapper to
the `PredictionResult` domain entity.
