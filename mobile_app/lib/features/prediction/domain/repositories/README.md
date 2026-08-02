# domain/repositories

Abstract repository interfaces.  The domain layer owns the contract;
the data layer provides the concrete implementation.

Keeping the interface in the domain layer means:
- Use-cases depend only on an abstraction — no import from data/.
- The concrete implementation can be swapped (real HTTP vs mock) without
  touching any domain or presentation code.
- Unit tests for use-cases inject a mock/stub of this interface.

## Planned files

### `prediction_repository.dart`
Declares the single operation the prediction feature requires.

```dart
abstract class PredictionRepository {
  Future<PredictionResult> submitImage(
    File image, {
    double? conf,
    double? iou,
  });
}
```

`PredictionResult` is the domain entity from `domain/entities/`.
The data layer's `PredictionRepositoryImpl` implements this interface.
