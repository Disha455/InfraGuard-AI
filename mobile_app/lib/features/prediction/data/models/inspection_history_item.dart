import 'inspection_location.dart';
import 'prediction_response_model.dart';

class InspectionHistoryItem {
  final PredictionResponseModel predictionResult;
  final DateTime inspectionDate;
  final String originalImagePath;
  final InspectionLocation? location;

  const InspectionHistoryItem({
    required this.predictionResult,
    required this.inspectionDate,
    required this.originalImagePath,
    this.location,
  });

  String get runId => predictionResult.runId;
  int get totalDetections => predictionResult.totalDetections;
  String get status => predictionResult.status;
  String get annotatedImagePath => predictionResult.annotatedImage;
  String? get firstDamageType =>
      predictionResult.detections.isNotEmpty
          ? predictionResult.detections.first.className
          : null;
}
