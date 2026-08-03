import 'dart:io';
import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../routes/app_router.dart';
import '../../data/models/detection_model.dart';
import '../../data/models/prediction_response_model.dart';

// ── ResultPage ────────────────────────────────────────────────────────────────

class ResultPage extends StatelessWidget {
  final PredictionResponseModel result;

  const ResultPage({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Road Damage Analysis'),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(vertical: 16),
        children: [
          // ── Annotated image ───────────────────────────────────────────────
          _AnnotatedImageCard(path: result.annotatedImage),

          const SizedBox(height: 4),

          // ── Info cards ────────────────────────────────────────────────────
          _InfoCard(
            icon: Icons.tag,
            title: 'Run ID',
            value: result.runId,
          ),
          _InfoCard(
            icon: Icons.check_circle_outline,
            title: 'Status',
            value: result.status,
          ),
          _InfoCard(
            icon: Icons.analytics_outlined,
            title: 'Total Detections',
            value: result.totalDetections.toString(),
          ),

          const SizedBox(height: 4),

          // ── Section header ────────────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: Text('Detections', style: textTheme.titleMedium),
          ),

          // ── Detection cards or empty state ────────────────────────────────
          if (result.detections.isEmpty)
            Card(
              child: const Padding(
                padding: EdgeInsets.all(20),
                child: Center(child: Text('No road damage detected.')),
              ),
            )
          else
            ...result.detections.map(
              (detection) => _DetectionCard(detection: detection),
            ),

          // ── Start New Inspection button ───────────────────────────────────
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
            child: SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.camera_alt),
                label: const Text('Start New Inspection'),
                onPressed: () => Navigator.pushNamedAndRemoveUntil(
                  context,
                  AppRouter.home,
                  (_) => false,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── _InfoCard ─────────────────────────────────────────────────────────────────

class _InfoCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;

  const _InfoCard({
    required this.icon,
    required this.title,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: AppColors.primaryContainer,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                icon,
                size: 22,
                color: AppColors.onPrimaryContainer,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: textTheme.labelMedium),
                  const SizedBox(height: 2),
                  Text(value, style: textTheme.bodyMedium),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── _ConfidenceBadge ──────────────────────────────────────────────────────────

class _ConfidenceBadge extends StatelessWidget {
  final double confidence;

  const _ConfidenceBadge({required this.confidence});

  Color get _badgeColor {
    if (confidence >= 0.80) return AppColors.success;
    if (confidence >= 0.50) return AppColors.warning;
    return AppColors.error;
  }

  @override
  Widget build(BuildContext context) {
    final label = '${(confidence * 100).toStringAsFixed(1)}%';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _badgeColor,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.2,
        ),
      ),
    );
  }
}

// ── _DetectionCard ────────────────────────────────────────────────────────────

class _DetectionCard extends StatelessWidget {
  final DetectionModel detection;

  const _DetectionCard({required this.detection});

  IconData get _damageIcon {
    final name = detection.className.toLowerCase();
    if (name.contains('pothole')) return Icons.warning_amber_rounded;
    return Icons.timeline;
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final bb = detection.boundingBox;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Damage type row ─────────────────────────────────────────────
            Row(
              children: [
                Icon(
                  _damageIcon,
                  size: 20,
                  color: AppColors.secondary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    detection.className,
                    style: textTheme.titleSmall,
                  ),
                ),
                _ConfidenceBadge(confidence: detection.confidence),
              ],
            ),

            const Divider(height: 20),

            // ── Bounding box ────────────────────────────────────────────────
            Text('Bounding Box', style: textTheme.labelMedium),
            const SizedBox(height: 8),
            Row(
              children: [
                _BboxField(label: 'X1', value: bb.x1),
                _BboxField(label: 'Y1', value: bb.y1),
                _BboxField(label: 'X2', value: bb.x2),
                _BboxField(label: 'Y2', value: bb.y2),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ── _BboxField ────────────────────────────────────────────────────────────────

class _BboxField extends StatelessWidget {
  final String label;
  final double value;

  const _BboxField({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Expanded(
      child: Container(
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.surfaceVariant,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(label, style: textTheme.labelSmall),
            const SizedBox(height: 2),
            Text(
              value.toStringAsFixed(1),
              style: textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

// ── _AnnotatedImageCard ───────────────────────────────────────────────────────

class _AnnotatedImageCard extends StatelessWidget {
  final String path;

  const _AnnotatedImageCard({required this.path});

  @override
  Widget build(BuildContext context) {
    final file = File(path);
    final fileExists = file.existsSync();

    return Card(
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      child: fileExists
          ? ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 300),
              child: Image.file(
                file,
                fit: BoxFit.contain,
                width: double.infinity,
              ),
            )
          : const Padding(
              padding: EdgeInsets.all(20),
              child: Center(child: Text('Annotated image not available.')),
            ),
    );
  }
}
