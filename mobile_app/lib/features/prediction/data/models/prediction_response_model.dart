import 'detection_model.dart';
import 'risk_assessment_model.dart';

class PredictionResponseModel {
  final String status;
  final String runId;
  final String annotatedImage;
  final String detectionsFile;
  final String summaryFile;
  final List<DetectionModel> detections;
  final int totalDetections;
  final RiskAssessmentModel? riskAssessment;
  final String severity;
  final double severityProbability;
  final Map<String, dynamic>? contextualFactors;

  const PredictionResponseModel({
    required this.status,
    required this.runId,
    required this.annotatedImage,
    required this.detectionsFile,
    required this.summaryFile,
    required this.detections,
    required this.totalDetections,
    this.riskAssessment,
    this.severity = '',
    this.severityProbability = 0.0,
    this.contextualFactors,
  });

  factory PredictionResponseModel.fromJson(Map<String, dynamic> json) {
    final detList = json['detections'] as List<dynamic>? ?? [];
    return PredictionResponseModel(
      status: json['status'] as String? ?? '',
      runId: json['run_id'] as String? ?? '',
      annotatedImage: json['annotated_image'] as String? ?? '',
      detectionsFile: json['detections_file'] as String? ?? '',
      summaryFile: json['summary_file'] as String? ?? '',
      detections: detList
          .map((e) => DetectionModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      totalDetections: json['total_detections'] as int? ?? detList.length,
      riskAssessment: json['risk_assessment'] != null
          ? RiskAssessmentModel.fromJson(
              json['risk_assessment'] as Map<String, dynamic>,
            )
          : null,
      severity: json['severity'] as String? ?? '',
      severityProbability:
          (json['severity_probability'] as num?)?.toDouble() ?? 0.0,
      contextualFactors: json['contextual_factors'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() => {
    'status': status,
    'run_id': runId,
    'annotated_image': annotatedImage,
    'detections_file': detectionsFile,
    'summary_file': summaryFile,
    'detections': detections.map((e) => e.toJson()).toList(),
    'total_detections': totalDetections,
    if (riskAssessment != null) 'risk_assessment': riskAssessment!.toJson(),
    'severity': severity,
    'severity_probability': severityProbability,
    if (contextualFactors != null) 'contextual_factors': contextualFactors,
  };
}
