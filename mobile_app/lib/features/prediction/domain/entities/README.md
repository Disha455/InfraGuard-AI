# domain/entities

Pure Dart value objects with no framework, HTTP, or JSON dependencies.
These are the core business objects that every other layer (data,
presentation, state management) depends on.

Entities are never created from JSON directly — that is the data
layer's responsibility.  Domain entities hold behaviour and enforce
invariants; models handle serialisation.

## Planned files

### `bounding_box.dart`
Immutable value object representing a detected region.

```dart
class BoundingBox {
  final double x1; // left edge (pixels)
  final double y1; // top edge (pixels)
  final double x2; // right edge (pixels)
  final double y2; // bottom edge (pixels)

  double get width  => x2 - x1;
  double get height => y2 - y1;
}
```

### `detection.dart`
One detected road damage instance.

```dart
class Detection {
  final int         classId;
  final String      className;   // e.g. "longitudinal_crack"
  final double      confidence;  // 0.0 – 1.0
  final BoundingBox boundingBox;
}
```

Class names match the four InfraGuard classes:
  pothole | longitudinal_crack | transverse_crack | alligator_crack

### `prediction_result.dart`
Top-level result returned by `SubmitPrediction` use-case.

```dart
class PredictionResult {
  final String           runId;             // "run_20260802_125021"
  final String           annotatedImagePath;
  final String           detectionsFilePath;
  final String           summaryFilePath;
  final List<Detection>  detections;
  final int              totalDetections;
}
```
