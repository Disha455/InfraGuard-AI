# presentation/pages

Full-screen route destinations for the prediction feature.
Each page is registered as a named route in `routes/app_router.dart`
and knows nothing about HTTP or domain logic — it reads from state
and dispatches events/calls to the cubit/notifier.

## Planned files

### `prediction_page.dart`
The primary screen — entry point for a new prediction.

Responsibilities:
- Display an image picker (camera or gallery).
- Show a preview of the selected image.
- Provide optional confidence / IoU threshold sliders.
- Trigger `PredictionCubit.submitImage()` on form submit.
- Navigate to `ResultPage` when the cubit emits a success state.
- Show `ErrorBanner` (from shared/widgets) on failure.

Route: `/`  or  `/predict`

### `result_page.dart`
Displays the completed prediction result.

Responsibilities:
- Show the annotated image returned by the backend.
- List each `Detection` using `DetectionCard` widgets.
- Display run metadata: run_id, total_detections, thresholds used.
- Provide a share / save button for the annotated image.
- Handle the "no detections" empty state gracefully.

Route: `/result`
Receives a `PredictionResult` entity as a route argument.
