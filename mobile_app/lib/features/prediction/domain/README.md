# features/prediction/domain

Domain layer for the prediction feature — pure Dart, zero framework
or network dependencies.

Planned implementations:
- `entities/detection.dart`
    Maps directly to one element of the backend detections array:
      class_id, class_name, confidence, bounding_box (x1,y1,x2,y2)

- `entities/bounding_box.dart`
    Value object holding x1, y1, x2, y2 as doubles.

- `entities/prediction_result.dart`
    Top-level result from one /predict call:
      run_id, annotated_image path, detections_file path,
      summary_file path, List<Detection>, total_detections.

- `repositories/prediction_repository.dart`
    Abstract interface — decouples domain from HTTP implementation.

- `usecases/submit_prediction.dart`
    Single use-case: receives an image File, delegates to the
    repository, returns a PredictionResult.
