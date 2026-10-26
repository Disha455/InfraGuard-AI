class InspectionLocation {
  final double latitude;
  final double longitude;
  final double? accuracy;

  const InspectionLocation({
    required this.latitude,
    required this.longitude,
    this.accuracy,
  });

  factory InspectionLocation.fromJson(Map<String, dynamic> json) {
    return InspectionLocation(
      latitude: (json['latitude'] as num?)?.toDouble() ?? 0.0,
      longitude: (json['longitude'] as num?)?.toDouble() ?? 0.0,
      accuracy: json['accuracy'] != null
          ? (json['accuracy'] as num).toDouble()
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
    'latitude': latitude,
    'longitude': longitude,
    if (accuracy != null) 'accuracy': accuracy,
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is InspectionLocation &&
          runtimeType == other.runtimeType &&
          latitude == other.latitude &&
          longitude == other.longitude &&
          accuracy == other.accuracy;

  @override
  int get hashCode => Object.hash(latitude, longitude, accuracy);

  @override
  String toString() =>
      'InspectionLocation(lat: $latitude, lng: $longitude${accuracy != null ? ', acc: $accuracy' : ''})';
}
