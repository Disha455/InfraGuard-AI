# data/repositories

Concrete implementations of the abstract repository interfaces declared
in `domain/repositories/`.

The repository is the bridge between the data and domain layers:
- It delegates network calls to the data source.
- It converts data models into domain entities using the model mappers.
- It catches data-layer exceptions and converts them to domain-layer
  failures so the domain remains free of network-specific error types.

## Planned files

### `prediction_repository_impl.dart`
Implements `PredictionRepository` (declared in domain/repositories/).

```dart
class PredictionRepositoryImpl implements PredictionRepository {
  final PredictionRemoteDataSource remoteDataSource;
  // ...
}
```

Responsibilities:
1. Call `remoteDataSource.submitImage(image, conf: conf, iou: iou)`.
2. Pass the raw map to `PredictionResultModel.fromJson()`.
3. Map the model to a `PredictionResult` domain entity.
4. Wrap any thrown exception in a domain-layer failure type.
5. Return `Either<Failure, PredictionResult>` (if using functional error
   handling) or rethrow a typed domain exception.
