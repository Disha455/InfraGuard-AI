import 'api_service.dart';
import '../../features/prediction/data/models/bounding_box_model.dart';
import '../../features/prediction/data/models/detection_model.dart';
import '../../features/prediction/data/models/inspection_history_item.dart';
import '../../features/prediction/data/models/inspection_location.dart';
import '../../features/prediction/data/models/prediction_response_model.dart';
import '../../features/prediction/data/models/risk_assessment_model.dart';

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
/// service.addInspection(result, originalImagePath: path, location: loc);
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
  /// [location] is the GPS fix captured when the inspection was submitted.
  /// May be null when location services are unavailable or denied — a null
  /// location never prevents the entry from being recorded.
  void addInspection(
    PredictionResponseModel result, {
    required String originalImagePath,
    DateTime? inspectionDate,
    InspectionLocation? location,
  }) {
    final item = InspectionHistoryItem(
      predictionResult: result,
      inspectionDate: inspectionDate ?? DateTime.now(),
      originalImagePath: originalImagePath,
      location: location,
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

  /// Synchronizes inspection history with the persistent SQLite database on the backend.
  ///
  /// Ensures that when the user completely closes and re-opens the app,
  /// all inspections recorded in the database are recovered and displayed.
  Future<void> syncWithBackend({ApiService? apiService}) async {
    try {
      final client = apiService ?? ApiService();
      final list = await client.fetchInspectionsList(limit: 100);

      for (final raw in list) {
        final runId = raw['run_id'] as String? ?? '';
        if (runId.isEmpty) continue;

        // Skip if this inspection is already in our list
        final alreadyPresent = _items.any((item) => item.runId == runId);
        if (alreadyPresent) continue;

        final lat = (raw['latitude'] as num?)?.toDouble();
        final lon = (raw['longitude'] as num?)?.toDouble();
        InspectionLocation? loc;
        if (lat != null && lon != null) {
          loc = InspectionLocation(latitude: lat, longitude: lon);
        }

        final rawDets = raw['detections'] as List<dynamic>? ?? [];
        final detections = rawDets.map((d) {
          final m = d as Map<String, dynamic>;
          return DetectionModel(
            classId: 0,
            className: m['class_name'] as String? ?? 'pothole',
            confidence: (m['confidence'] as num?)?.toDouble() ?? 0.85,
            boundingBox: const BoundingBoxModel(x1: 0, y1: 0, x2: 0, y2: 0),
          );
        }).toList();

        final prediction = PredictionResponseModel(
          status: 'ok',
          runId: runId,
          annotatedImage: raw['image_url'] as String? ?? '',
          detectionsFile: '',
          summaryFile: '',
          detections: detections,
          totalDetections: raw['total_detections'] as int? ?? detections.length,
          riskAssessment: RiskAssessmentModel(
            score: (raw['risk_score'] as num?)?.toDouble() ?? 50.0,
            level: RiskLevel.fromString(raw['risk_level'] as String? ?? 'MODERATE'),
            dominantDamage: raw['dominant_damage'] as String?,
            recommendation: 'Municipal survey record restored from database',
            detectionRisks: [],
            scoreBreakdown: {},
            methodologyNote: 'Synced from municipal survey database',
          ),
          severity: raw['risk_level'] as String? ?? 'Moderate',
          severityProbability: 0.85,
          contextualFactors: {
            'weather': {'condition': raw['weather_summary']},
            'traffic': {'road_name': raw['location_name'], 'traffic_volume': raw['traffic_level']},
            'maintenance': {'maintenance_status': raw['maintenance_status']},
            'risk_multiplier_summary': 'Synced from persistent database',
            'maintenance_note': raw['maintenance_status'] ?? '',
          },
        );

        DateTime dt;
        try {
          dt = DateTime.parse(raw['timestamp'] as String? ?? '');
        } catch (_) {
          dt = DateTime.now();
        }

        _items.add(InspectionHistoryItem(
          predictionResult: prediction,
          inspectionDate: dt,
          originalImagePath: '',
          location: loc,
        ));
      }

      // Sort newest-first by inspectionDate
      _items.sort((a, b) => b.inspectionDate.compareTo(a.inspectionDate));
    } catch (_) {
      // Offline fallback: keep in-memory items intact
    }
  }
}
