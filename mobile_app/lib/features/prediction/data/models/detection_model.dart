import 'bounding_box_model.dart';

class DetectionModel {
  final int classId;
  final String className;
  final double confidence;
  final BoundingBoxModel boundingBox;

  const DetectionModel({
    required this.classId,
    required this.className,
    required this.confidence,
    required this.boundingBox,
  });

  factory DetectionModel.fromJson(Map<String, dynamic> json) {
    return DetectionModel(
      classId: json['class_id'] as int? ?? 0,
      className: json['class_name'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      boundingBox: BoundingBoxModel.fromJson(
        json['bounding_box'] as Map<String, dynamic>? ?? {},
      ),
    );
  }

  Map<String, dynamic> toJson() => {
    'class_id': classId,
    'class_name': className,
    'confidence': confidence,
    'bounding_box': boundingBox.toJson(),
  };
}
