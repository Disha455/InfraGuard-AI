# domain/usecases

Single-responsibility use-case classes.  Each use-case encapsulates
exactly one business operation and depends only on a repository
interface — never on HTTP, Flutter widgets, or state managers.

Use-cases are the entry point into the domain for the presentation
layer.  Cubits/notifiers call use-cases; use-cases call repositories.

## Planned files

### `submit_prediction.dart`
Coordinates the full prediction workflow.

```dart
class SubmitPrediction {
  final PredictionRepository repository;

  SubmitPrediction(this.repository);

  Future<PredictionResult> call(
    File image, {
    double? conf,
    double? iou,
  }) {
    return repository.submitImage(image, conf: conf, iou: iou);
  }
}
```

Using `call()` lets the cubit invoke the use-case as a function:
```dart
final result = await submitPrediction(image, conf: 0.35);
```

Additional use-cases to add as the feature grows:
- `GetPredictionHistory` — retrieve previously saved run directories.
- `ExportPredictionResult` — share/save the annotated image.
