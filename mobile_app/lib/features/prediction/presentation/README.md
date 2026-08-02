# features/prediction/presentation

Presentation layer for the prediction feature — screens, state
management, and widgets that are specific to the prediction workflow.

Planned sub-structure:
  pages/
    prediction_page.dart    — image picker + submit button
    result_page.dart        — annotated image + detections list
  widgets/
    detection_card.dart     — single Detection displayed as a card
    bounding_box_overlay.dart — draws boxes on the annotated image
  state/ (or bloc/ / cubit/ depending on chosen state manager)
    prediction_state.dart
    prediction_cubit.dart
