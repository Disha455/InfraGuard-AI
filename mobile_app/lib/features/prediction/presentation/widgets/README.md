# presentation/widgets

Feature-scoped reusable widgets for the prediction flow.
Unlike `shared/widgets/`, these are specific to the prediction feature
and must not be imported by other features.

## Planned files

### `detection_card.dart`
Displays a single `Detection` entity as a styled card.

Planned content:
- Colour-coded class label chip (pothole = red, cracks = amber/orange).
- Confidence score formatted as a percentage.
- Bounding box coordinates (x1, y1) → (x2, y2) in small print.

### `bounding_box_overlay.dart`
Draws bounding boxes on top of the annotated image using a
`CustomPainter`.  Receives the image dimensions and a
`List<Detection>` and scales each `BoundingBox` to the rendered
image size.  This is the alternative/supplement to the backend's
Ultralytics-rendered `annotated.jpg` — allows interactive highlighting.

### `image_upload_area.dart`
Tappable region that triggers the image picker.  Shows:
- A placeholder illustration when no image is selected.
- The selected image preview once an image is chosen.
- A loading overlay while inference is in progress.

### `threshold_controls.dart`
Optional row of sliders/chips for confidence and IoU overrides.
Passes values up to the cubit before submit.
