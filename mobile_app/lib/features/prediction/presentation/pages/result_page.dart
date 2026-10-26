import 'dart:io';
import 'package:flutter/material.dart';
import '../../../../core/constants/api_endpoints.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../routes/app_router.dart';
import '../../data/models/detection_model.dart';
import '../../data/models/inspection_location.dart';
import '../../data/models/prediction_response_model.dart';
import '../widgets/risk_assessment_card.dart';

class ResultPage extends StatelessWidget {
  final PredictionResponseModel result;
  final InspectionLocation? location;

  const ResultPage({
    super.key,
    required this.result,
    this.location,
  });

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        flexibleSpace: Container(
          decoration: const BoxDecoration(
            gradient: AppColors.appBarGradient,
          ),
        ),
        title: const Text('Road Damage Analysis'),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppColors.backgroundGradient,
        ),
        child: ListView(
        padding: const EdgeInsets.symmetric(vertical: 16),
        children: [
          // ── Annotated Image with Bounding Boxes ───────────────────────
          _AnnotatedImageCard(path: result.annotatedImage),

          const SizedBox(height: 10),

          // ── Single Unified Assessment Card ───────────────────────────
          if (result.riskAssessment != null)
            RiskAssessmentCard(assessment: result.riskAssessment!)
          else if (result.severity.isNotEmpty)
            _SeverityCard(
              severity: result.severity,
              probability: result.severityProbability,
            ),

          const SizedBox(height: 6),

          // ── Inspection GPS Location ───────────────────────────────────
          _LocationCard(location: location),

          const SizedBox(height: 6),

          // ── Contextual Risk Intelligence Card ─────────────────────────
          if (result.contextualFactors != null) ...[
            _ContextualFactorsCard(factors: result.contextualFactors!),
            const SizedBox(height: 6),
          ],

          // ── Detections Header with Count Badge ────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Detections',
                  style: textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                  decoration: BoxDecoration(
                    color: AppColors.primaryContainer,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '${result.totalDetections} ${result.totalDetections == 1 ? 'detected' : 'detected'}',
                    style: textTheme.labelSmall?.copyWith(
                      color: AppColors.onPrimaryContainer,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),

          if (result.detections.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(20),
                child: Center(child: Text('No road damage detected.')),
              ),
            )
          else
            ...result.detections.map(
              (detection) => _DetectionCard(detection: detection),
            ),

          // ── Action Button ─────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 20, 16, 8),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.camera_alt),
                label: const Text('Start New Inspection'),
                onPressed:
                    () => Navigator.pushNamedAndRemoveUntil(
                      context,
                      AppRouter.home,
                      (_) => false,
                    ),
              ),
            ),
          ),

          // ── Subtle Run ID Footer ──────────────────────────────────────
          if (result.runId.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4, bottom: 16),
              child: Center(
                child: Text(
                  'Run ID: ${result.runId}',
                  style: textTheme.labelSmall?.copyWith(
                    color: AppColors.textDisabled,
                    fontSize: 11,
                  ),
                ),
              ),
            ),
        ],
      ),
    ),
  );
}
}

// ── Location Card ─────────────────────────────────────────────────────────────

class _LocationCard extends StatelessWidget {
  final InspectionLocation? location;

  const _LocationCard({required this.location});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final hasLoc = location != null;

    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: hasLoc
                    ? AppColors.primaryContainer
                    : AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                hasLoc ? Icons.location_on : Icons.location_off_outlined,
                size: 20,
                color: hasLoc
                    ? AppColors.onPrimaryContainer
                    : AppColors.textDisabled,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Inspection Location', style: textTheme.labelMedium),
                  const SizedBox(height: 2),
                  if (hasLoc) ...[
                    Text(
                      '${location!.latitude.toStringAsFixed(6)}°,  ${location!.longitude.toStringAsFixed(6)}°',
                      style: textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (location!.accuracy != null) ...[
                      const SizedBox(height: 1),
                      Text(
                        'GPS Accuracy: ±${location!.accuracy!.toStringAsFixed(0)} m',
                        style: textTheme.labelSmall?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ] else
                    Text(
                      'Location unavailable (GPS disabled or permission denied)',
                      style: textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Contextual Risk Intelligence Card ─────────────────────────────────────────

class _ContextualFactorsCard extends StatelessWidget {
  final Map<String, dynamic> factors;

  const _ContextualFactorsCard({required this.factors});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    final weather = factors['weather'] as Map<String, dynamic>?;
    final traffic = factors['traffic'] as Map<String, dynamic>?;
    final maintenance = factors['maintenance'] as Map<String, dynamic>?;
    final riskMultiplierSummary =
        factors['risk_multiplier_summary'] as String? ?? '1.0x baseline';
    final maintenanceNote =
        factors['maintenance_note'] as String? ?? 'Standard municipal survey criteria';

    final temp = (weather?['temperature_c'] as num?)?.toDouble();
    final condition = weather?['condition'] as String? ?? 'Clear';
    final isWet = weather?['is_wet_pavement'] as bool? ?? false;
    final weatherSummary = weather?['summary'] as String? ??
        (isWet ? 'Wet pavement hazard (+22% risk)' : 'Dry pavement (No risk penalty)');

    final roadName = traffic?['road_name'] as String? ?? 'Local Sector Corridor';
    final roadClass = traffic?['road_classification'] as String? ?? 'Local Road';
    final trafficLevel = traffic?['estimated_traffic_level'] as String? ?? 'Moderate';
    final trafficMult = (traffic?['traffic_risk_multiplier'] as num?)?.toDouble() ?? 1.0;

    final hasMaintenance = maintenance != null;
    final corridorName = maintenance?['corridor_name'] as String? ?? 'Surveyed Corridor';
    final pci = maintenance?['pavement_condition_index'] as int? ?? 70;
    final lastResurface = maintenance?['last_resurface_date'] as String? ?? '2023-01-01';
    final daysSince = maintenance?['days_since_resurfacing'] as int? ?? 365;
    final maintenanceStatus = maintenance?['maintenance_status'] as String? ?? 'Routine';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AppColors.primaryContainer,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.alt_route_rounded,
                    size: 20,
                    color: AppColors.primary,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Environmental & Municipal Context',
                        style: textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        'Live Weather (Open-Meteo) • Traffic • Survey History',
                        style: textTheme.labelSmall?.copyWith(
                          color: AppColors.textSecondary,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            const Divider(height: 1),
            const SizedBox(height: 12),

            // Weather Factor Row
            _buildFactorRow(
              icon: isWet ? Icons.water_drop : Icons.wb_sunny_outlined,
              iconColor: isWet ? const Color(0xFF1976D2) : const Color(0xFFF57C00),
              label: 'Real-time Weather (Open-Meteo)',
              title: temp != null ? '${temp.toStringAsFixed(1)}°C • $condition' : 'Clear (Dry)',
              subtitle: weatherSummary,
            ),

            const SizedBox(height: 10),

            // Traffic / Road Hierarchy Row
            _buildFactorRow(
              icon: Icons.traffic_rounded,
              iconColor: const Color(0xFF673AB7),
              label: 'Road Classification & Traffic (OpenStreetMap)',
              title: '$roadName ($roadClass)',
              subtitle: 'Traffic: $trafficLevel • Multiplier: ${trafficMult.toStringAsFixed(2)}x',
            ),

            const SizedBox(height: 10),

            // Municipal Maintenance Survey Row
            _buildFactorRow(
              icon: Icons.history_edu_rounded,
              iconColor: const Color(0xFF00796B),
              label: 'Municipal Survey & Maintenance Record',
              title: hasMaintenance
                  ? '$corridorName (PCI: $pci/100)'
                  : 'No municipal corridor match (Standard baseline)',
              subtitle: hasMaintenance
                  ? 'Last resurfacing: $lastResurface ($daysSince days ago) • Status: $maintenanceStatus'
                  : 'Municipal records checked; standard baseline wear rate applied.',
            ),

            const SizedBox(height: 12),

            // Summary Impact Chip
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.surfaceVariant,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.outlineVariant),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.speed_rounded,
                    size: 16,
                    color: AppColors.primary,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '$riskMultiplierSummary • $maintenanceNote',
                      style: textTheme.labelSmall?.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFactorRow({
    required IconData icon,
    required Color iconColor,
    required String label,
    required String title,
    required String subtitle,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Icon(icon, size: 18, color: iconColor),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 1),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              if (subtitle.isNotEmpty) ...[
                const SizedBox(height: 1),
                Text(
                  subtitle,
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

// ── Fallback Severity Card (Used only if RiskAssessment is absent) ─────────────

class _SeverityCard extends StatelessWidget {
  final String severity;
  final double probability;

  const _SeverityCard({required this.severity, required this.probability});

  Color get _severityColor {
    final s = severity.toLowerCase();
    if (s.contains('high') || s.contains('severe') || s.contains('critical')) {
      return AppColors.error;
    }
    if (s.contains('medium') || s.contains('moderate')) return AppColors.warning;
    return AppColors.success;
  }

  IconData get _severityIcon {
    final s = severity.toLowerCase();
    if (s.contains('high') || s.contains('severe') || s.contains('critical')) {
      return Icons.warning_amber_rounded;
    }
    return Icons.check_circle_outline;
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final percentage = (probability * 100).toStringAsFixed(1);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: _severityColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(_severityIcon, size: 24, color: _severityColor),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Road Severity Level',
                        style: textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        severity.toUpperCase(),
                        style: textTheme.titleLarge?.copyWith(
                          color: _severityColor,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: probability.clamp(0.0, 1.0),
                minHeight: 8,
                backgroundColor: AppColors.surfaceVariant,
                valueColor: AlwaysStoppedAnimation<Color>(_severityColor),
              ),
            ),
            const SizedBox(height: 6),
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                'Confidence: $percentage%',
                style: textTheme.labelSmall?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Clean Detection Card ──────────────────────────────────────────────────────

class _DetectionCard extends StatelessWidget {
  final DetectionModel detection;

  const _DetectionCard({required this.detection});

  IconData get _damageIcon {
    final name = detection.className.toLowerCase();
    if (name.contains('pothole')) return Icons.warning_amber_rounded;
    if (name.contains('alligator')) return Icons.grid_view_rounded;
    return Icons.timeline;
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: AppColors.secondaryContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(_damageIcon, size: 20, color: AppColors.secondary),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                RiskAssessmentCard.formatClassName(detection.className),
                style: textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            _ConfidenceBadge(confidence: detection.confidence),
          ],
        ),
      ),
    );
  }
}

// ── Confidence Badge ──────────────────────────────────────────────────────────

class _ConfidenceBadge extends StatelessWidget {
  final double confidence;

  const _ConfidenceBadge({required this.confidence});

  Color get _badgeColor {
    if (confidence >= 0.70) return AppColors.success;
    if (confidence >= 0.40) return AppColors.warning;
    return AppColors.error;
  }

  @override
  Widget build(BuildContext context) {
    final pct = (confidence * 100).toStringAsFixed(1);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _badgeColor.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _badgeColor.withValues(alpha: 0.40)),
      ),
      child: Text(
        '$pct%',
        style: TextStyle(
          color: _badgeColor,
          fontWeight: FontWeight.w700,
          fontSize: 12,
        ),
      ),
    );
  }
}

// ── Annotated Image Card ──────────────────────────────────────────────────────

class _AnnotatedImageCard extends StatelessWidget {
  final String path;

  const _AnnotatedImageCard({required this.path});

  /// Normalizes any server-returned URL or relative path so that it
  /// reliably resolves against the client's configured [ApiEndpoints.baseUrl].
  String get _resolvedUrl {
    if (path.isEmpty) return '';

    if (path.startsWith('http://') || path.startsWith('https://')) {
      final uri = Uri.tryParse(path);
      if (uri != null && uri.path.contains('outputs')) {
        final serverBase = ApiEndpoints.baseUrl.replaceAll(RegExp(r'/+$'), '');
        final outputIdx = uri.path.indexOf('/outputs');
        if (outputIdx != -1) {
          final rel = uri.path.substring(outputIdx);
          return '$serverBase$rel';
        }
      }
      return path;
    }

    if (path.contains('outputs')) {
      final serverBase = ApiEndpoints.baseUrl.replaceAll(RegExp(r'/+$'), '');
      final p = path.startsWith('/') ? path : '/$path';
      return '$serverBase$p';
    }

    return path;
  }

  bool get _isUrl {
    final resolved = _resolvedUrl;
    return resolved.startsWith('http://') || resolved.startsWith('https://');
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              children: [
                const Icon(Icons.image_outlined, size: 20, color: AppColors.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Annotated Detections',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
          _isUrl ? _buildNetworkImage(_resolvedUrl) : _buildFileImage(),
        ],
      ),
    );
  }

  Widget _buildNetworkImage(String imageUrl) {
    return ConstrainedBox(
      constraints: const BoxConstraints(maxHeight: 320),
      child: Image.network(
        imageUrl,
        fit: BoxFit.contain,
        width: double.infinity,
        loadingBuilder: (context, child, loadingProgress) {
          if (loadingProgress == null) return child;
          return const SizedBox(
            height: 180,
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 12),
                  Text('Loading annotated image with bounding boxes...'),
                ],
              ),
            ),
          );
        },
        errorBuilder: (context, error, stackTrace) {
          return Padding(
            padding: const EdgeInsets.all(24),
            child: Center(
              child: Column(
                children: [
                  const Icon(Icons.broken_image_outlined, size: 40, color: Colors.grey),
                  const SizedBox(height: 8),
                  const Text('Annotated image not available from server.'),
                  const SizedBox(height: 4),
                  Text(
                    imageUrl,
                    style: const TextStyle(fontSize: 10, color: Colors.grey),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildFileImage() {
    final file = File(path);
    final fileExists = file.existsSync();

    return fileExists
        ? ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 320),
            child: Image.file(file, fit: BoxFit.contain, width: double.infinity),
          )
        : const Padding(
            padding: EdgeInsets.all(24),
            child: Center(child: Text('Annotated image not available.')),
          );
  }
}
