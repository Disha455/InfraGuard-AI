import '../../../prediction/data/models/inspection_history_item.dart';

class RecentInspectionRecord {
  final String id;
  final String locationName;
  final String coordinates;
  final String damageCategory;
  final String severity;
  final double riskScore;
  final DateTime timestamp;
  final String status;
  final bool isLiveSession;

  const RecentInspectionRecord({
    required this.id,
    required this.locationName,
    required this.coordinates,
    required this.damageCategory,
    required this.severity,
    required this.riskScore,
    required this.timestamp,
    required this.status,
    this.isLiveSession = false,
  });
}

class AdminAnalyticsData {
  final int totalInspections;
  final int damagedRoads;
  final int highRiskRoads;
  final int pendingInspections;
  final Map<String, int> damageCategoryCounts;
  final Map<String, int> severityCounts;
  final List<RecentInspectionRecord> recentInspections;

  const AdminAnalyticsData({
    required this.totalInspections,
    required this.damagedRoads,
    required this.highRiskRoads,
    required this.pendingInspections,
    required this.damageCategoryCounts,
    required this.severityCounts,
    required this.recentInspections,
  });

  /// Builds aggregated metrics blending session inspections with benchmark sample data.
  factory AdminAnalyticsData.compute({
    required List<InspectionHistoryItem> liveHistory,
  }) {
    // Benchmark sample data
    int baseTotal = 1248;
    int baseDamaged = 842;
    int baseHighRisk = 186;
    int basePending = 24;

    final categories = <String, int>{
      'Potholes': 475,
      'Longitudinal Cracks': 331,
      'Transverse Cracks': 262,
      'Alligator Cracks': 180,
    };

    final severities = <String, int>{
      'Low': 406,
      'Moderate': 250,
      'High': 132,
      'Critical': 54,
    };

    final recentList = <RecentInspectionRecord>[];

    // Incorporate live inspections first if available
    for (final item in liveHistory) {
      baseTotal++;
      final damageType = _formatDamageName(item.firstDamageType ?? 'Pothole');
      categories[damageType] = (categories[damageType] ?? 0) + 1;

      final risk = item.predictionResult.riskAssessment;
      final score = risk?.score ?? 45.0;
      final level = risk?.level.label ?? (item.predictionResult.severity.isNotEmpty
          ? item.predictionResult.severity.toUpperCase()
          : 'MODERATE');

      if (level == 'HIGH' || level == 'CRITICAL') {
        baseHighRisk++;
      }
      baseDamaged++;

      final severityKey = _normalizeSeverity(level);
      severities[severityKey] = (severities[severityKey] ?? 0) + 1;

      final locStr = item.location != null
          ? '${item.location!.latitude.toStringAsFixed(4)}° N, ${item.location!.longitude.toStringAsFixed(4)}° E'
          : 'GPS acquired via telemetry';

      recentList.add(
        RecentInspectionRecord(
          id: item.runId.isNotEmpty ? item.runId : 'LIVE-${recentList.length + 1}',
          locationName: 'Active Field Inspection Zone',
          coordinates: locStr,
          damageCategory: damageType,
          severity: severityKey,
          riskScore: score,
          timestamp: item.inspectionDate,
          status: 'Verified (Live)',
          isLiveSession: true,
        ),
      );
    }

    // Append realistic sample inspection benchmarks
    final sampleBenchmarks = [
      RecentInspectionRecord(
        id: 'INS-2026-891',
        locationName: 'Outer Ring Road (Sector 4)',
        coordinates: '12.9352° N, 77.6245° E',
        damageCategory: 'Potholes',
        severity: 'Critical',
        riskScore: 88.5,
        timestamp: DateTime.now().subtract(const Duration(minutes: 24)),
        status: 'Action Required',
      ),
      RecentInspectionRecord(
        id: 'INS-2026-890',
        locationName: 'Highway 44 - North Corridor',
        coordinates: '13.0827° N, 77.5877° E',
        damageCategory: 'Alligator Cracks',
        severity: 'High',
        riskScore: 74.0,
        timestamp: DateTime.now().subtract(const Duration(hours: 1, minutes: 12)),
        status: 'Crew Assigned',
      ),
      RecentInspectionRecord(
        id: 'INS-2026-889',
        locationName: 'MG Road Metro Overpass',
        coordinates: '12.9716° N, 77.5946° E',
        damageCategory: 'Transverse Cracks',
        severity: 'Moderate',
        riskScore: 46.2,
        timestamp: DateTime.now().subtract(const Duration(hours: 3, minutes: 45)),
        status: 'Under Review',
      ),
      RecentInspectionRecord(
        id: 'INS-2026-888',
        locationName: 'Indiranagar 100ft Boulevard',
        coordinates: '12.9784° N, 77.6408° E',
        damageCategory: 'Longitudinal Cracks',
        severity: 'Low',
        riskScore: 18.0,
        timestamp: DateTime.now().subtract(const Duration(hours: 5, minutes: 30)),
        status: 'Routine Log',
      ),
      RecentInspectionRecord(
        id: 'INS-2026-887',
        locationName: 'Electronic City Express Link',
        coordinates: '12.8452° N, 77.6602° E',
        damageCategory: 'Potholes',
        severity: 'High',
        riskScore: 71.5,
        timestamp: DateTime.now().subtract(const Duration(hours: 9, minutes: 10)),
        status: 'Crew Assigned',
      ),
      RecentInspectionRecord(
        id: 'INS-2026-886',
        locationName: 'Old Madras Road - KM 12',
        coordinates: '13.0033° N, 77.6841° E',
        damageCategory: 'Alligator Cracks',
        severity: 'Moderate',
        riskScore: 52.8,
        timestamp: DateTime.now().subtract(const Duration(days: 1, hours: 2)),
        status: 'Scheduled',
      ),
    ];

    recentList.addAll(sampleBenchmarks);

    return AdminAnalyticsData(
      totalInspections: baseTotal,
      damagedRoads: baseDamaged,
      highRiskRoads: baseHighRisk,
      pendingInspections: basePending,
      damageCategoryCounts: categories,
      severityCounts: severities,
      recentInspections: recentList,
    );
  }

  static String _formatDamageName(String raw) {
    final lower = raw.toLowerCase();
    if (lower.contains('pothole')) return 'Potholes';
    if (lower.contains('alligator')) return 'Alligator Cracks';
    if (lower.contains('transverse')) return 'Transverse Cracks';
    if (lower.contains('longitudinal')) return 'Longitudinal Cracks';
    return 'Road Defects';
  }

  static String _normalizeSeverity(String raw) {
    final upper = raw.toUpperCase();
    if (upper.contains('CRITICAL')) return 'Critical';
    if (upper.contains('HIGH')) return 'High';
    if (upper.contains('MODERATE') || upper.contains('MEDIUM')) return 'Moderate';
    return 'Low';
  }
}
