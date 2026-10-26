# shared/models

Serialisation helpers (fromJson / toJson) for structures that are used
across more than one feature.

These are distinct from domain entities: models handle JSON ↔ Dart
conversion; entities hold business logic and are network-agnostic.

Planned implementations:
- `detection_model.dart`         — fromJson for one detection object
- `bounding_box_model.dart`      — fromJson for the bounding_box field
- `prediction_result_model.dart` — fromJson for the full /predict response
