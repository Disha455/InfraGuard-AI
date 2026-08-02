# features/prediction/data

Data layer for the prediction feature.

Planned implementations:
- `prediction_remote_data_source.dart`
    Calls POST /predict on the FastAPI backend.
    Accepts an image File, optional conf/iou overrides.
    Returns a raw Map<String, dynamic> from the JSON response.

- `prediction_repository_impl.dart`
    Implements the domain PredictionRepository interface.
    Converts raw maps to domain entities and handles network errors.
