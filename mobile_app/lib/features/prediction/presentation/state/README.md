# presentation/state

State management for the prediction feature.
State lives here — not in pages — so the same state can be consumed
by multiple widgets and so pages stay focused on layout.

The chosen state manager (flutter_bloc / riverpod / provider) will be
added to pubspec.yaml and implemented here.

## Planned files (flutter_bloc / cubit pattern)

### `prediction_state.dart`
Sealed class hierarchy for all possible states of the prediction flow.

```dart
sealed class PredictionState {}

final class PredictionInitial   extends PredictionState {}
final class PredictionLoading   extends PredictionState {}
final class PredictionSuccess   extends PredictionState {
  final PredictionResult result;
}
final class PredictionFailure   extends PredictionState {
  final String message;
}
```

### `prediction_cubit.dart`
Thin orchestration between the UI and the domain use-case.

```dart
class PredictionCubit extends Cubit<PredictionState> {
  final SubmitPrediction submitPrediction;

  PredictionCubit(this.submitPrediction) : super(PredictionInitial());

  Future<void> submitImage(File image, {double? conf, double? iou}) async {
    emit(PredictionLoading());
    try {
      final result = await submitPrediction(image, conf: conf, iou: iou);
      emit(PredictionSuccess(result));
    } catch (e) {
      emit(PredictionFailure(e.toString()));
    }
  }
}
```

The cubit never imports `http`, `dio`, or any data-layer class.
