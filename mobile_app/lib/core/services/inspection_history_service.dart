import '../../features/prediction/data/models/inspection_history_item.dart';
import '../../features/prediction/data/models/prediction_response_model.dart';

/// In-memory repository for completed road damage inspections.
///
/// Implemented as a singleton so the same list is shared across
/// [HomePage], [HistoryPage], and any other widget that needs it —
/// without a state-management library or dependency injection framework.
///
/// Lifetime: the list lives for the duration of the app process.
/// It is intentionally not persisted to disk or a database.
///
/// Usage:
/// ```dart
/// final service = InspectionHistoryService.instance;
/// service.addInspection(result, originalImagePath: path);
/// final items = service.getHistory();
/// service.clearHistory();
/// ```
class InspectionHistoryService {
  InspectionHistoryService._();

  /// The single shared instance.
  static final InspectionHistoryService instance =
      InspectionHistoryService._();

  // Internal store — newest items are prepended so [getHistory] returns
  // them in reverse chronological order without an extra sort.
  final List<InspectionHistoryItem> _items = [];

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /// Records a completed inspection.
  ///
  /// [result] is the full API response returned by POST /predict.
  /// [originalImagePath] is the local path of the image the user selected
  /// (may be empty if the path is unavailable).
  /// [inspectionDate] defaults to [DateTime.now()] when omitted.
  void addInspection(
    PredictionResponseModel result, {
    required String originalImagePath,
    DateTime? inspectionDate,
  }) {
    final item = InspectionHistoryItem(
      predictionResult: result,
      inspectionDate: inspectionDate ?? DateTime.now(),
      originalImagePath: originalImagePath,
    );
    // Prepend so index 0 is always the most recent inspection.
    _items.insert(0, item);
  }

  /// Returns all inspections, newest first.
  ///
  /// Returns an unmodifiable view so callers cannot mutate the internal
  /// list directly.
  List<InspectionHistoryItem> getHistory() =>
      List.unmodifiable(_items);

  /// Removes all inspections from the in-memory store.
  void clearHistory() => _items.clear();

  /// The number of stored inspections.
  int get count => _items.length;

  /// `true` when no inspections have been recorded yet.
  bool get isEmpty => _items.isEmpty;
}
