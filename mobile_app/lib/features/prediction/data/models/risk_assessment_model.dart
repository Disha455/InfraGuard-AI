enum RiskLevel {
  low,
  moderate,
  high,
  critical,
  unknown;

  String get label {
    switch (this) {
      case RiskLevel.low:
        return 'LOW';
      case RiskLevel.moderate:
        return 'MODERATE';
      case RiskLevel.high:
        return 'HIGH';
      case RiskLevel.critical:
        return 'CRITICAL';
      case RiskLevel.unknown:
        return 'UNKNOWN';
    }
  }

  static RiskLevel fromString(String? val) {
    if (val == null) return RiskLevel.unknown;
    switch (val.trim().toUpperCase()) {
      case 'LOW':
        return RiskLevel.low;
      case 'MODERATE':
      case 'MEDIUM':
        return RiskLevel.moderate;
      case 'HIGH':
        return RiskLevel.high;
      case 'CRITICAL':
      case 'SEVERE':
        return RiskLevel.critical;
      default:
        return RiskLevel.unknown;
    }
  }
}

class DetectionRiskModel {
  final String className;
  final double severityWeight;
  final double confidence;
  final double normalisedArea;
  final double detectionScore;

  const DetectionRiskModel({
    required this.className,
    required this.severityWeight,
    required this.confidence,
    required this.normalisedArea,
    required this.detectionScore,
  });

  factory DetectionRiskModel.fromJson(Map<String, dynamic> json) {
    return DetectionRiskModel(
      className: json['class_name'] as String? ?? '',
      severityWeight: (json['severity_weight'] as num?)?.toDouble() ?? 0.0,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      normalisedArea: (json['normalised_area'] as num?)?.toDouble() ?? 0.0,
      detectionScore: (json['detection_score'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() => {
    'class_name': className,
    'severity_weight': severityWeight,
    'confidence': confidence,
    'normalised_area': normalisedArea,
    'detection_score': detectionScore,
  };
}

class RiskAssessmentModel {
  final double score;
  final RiskLevel level;
  final List<DetectionRiskModel> detectionRisks;
  final String? dominantDamage;
  final Map<String, dynamic> scoreBreakdown;
  final String recommendation;
  final String methodologyNote;

  const RiskAssessmentModel({
    required this.score,
    required this.level,
    required this.detectionRisks,
    this.dominantDamage,
    required this.scoreBreakdown,
    required this.recommendation,
    required this.methodologyNote,
  });

  factory RiskAssessmentModel.fromJson(Map<String, dynamic> json) {
    final risksList = json['detection_risks'] as List<dynamic>? ?? [];
    return RiskAssessmentModel(
      score: (json['score'] as num?)?.toDouble() ?? 0.0,
      level: RiskLevel.fromString(json['level'] as String?),
      detectionRisks: risksList
          .map((e) => DetectionRiskModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      dominantDamage: json['dominant_damage'] as String?,
      scoreBreakdown: (json['score_breakdown'] as Map<String, dynamic>?) ?? {},
      recommendation: json['recommendation'] as String? ?? '',
      methodologyNote: json['methodology_note'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'score': score,
    'level': level.label,
    'detection_risks': detectionRisks.map((e) => e.toJson()).toList(),
    'dominant_damage': dominantDamage,
    'score_breakdown': scoreBreakdown,
    'recommendation': recommendation,
    'methodology_note': methodologyNote,
  };
}
