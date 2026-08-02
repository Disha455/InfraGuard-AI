# data/datasource

Responsible for all communication with external systems.

For the prediction feature this means the single FastAPI endpoint:

    POST /predict  (multipart/form-data)

## Planned files

### `prediction_remote_data_source.dart`
Abstract interface that declares the contract the concrete class must
fulfil.  The repository depends on this abstraction, not on the
concrete HTTP implementation.

```dart
abstract class PredictionRemoteDataSource {
  Future<Map<String, dynamic>> submitImage(
    File image, {
    double? conf,
    double? iou,
  });
}
```

### `prediction_remote_data_source_impl.dart`
Concrete implementation.  Responsibilities:
- Build the multipart request (image file + optional query params).
- Execute the HTTP POST via the shared ApiService.
- Return the raw decoded JSON map to the repository layer.
- Throw typed exceptions on network or server errors.

This class never creates domain entities — that conversion belongs to
the repository layer above it.
