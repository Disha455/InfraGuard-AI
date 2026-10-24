import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../../data/models/risk_assessment_model.dart';

/// Clean, executive road risk assessment card.
///
/// Displays:
///   1. Overall Risk Level badge (CRITICAL / HIGH / MODERATE / LOW)
///   2. Unified Risk Score (0–100) with visual indicator bar
///   3. Primary damage type detected
///   4. Actionable maintenance recommendation
class RiskAssessmentCard extends StatelessWidget {
  final RiskAssessmentModel assessment;

  const RiskAssessmentCard({super.key, required this.assessment});

  Color _levelColor(RiskLevel level) {
    switch (level) {
      case RiskLevel.low:
        return AppColors.success;
      case RiskLevel.moderate:
        return AppColors.warning;
      case RiskLevel.high:
      case RiskLevel.critical:
      case RiskLevel.unknown:
        return AppColors.error;
    }
  }

  Color _levelContainerColor(RiskLevel level) {
    switch (level) {
      case RiskLevel.low:
        return AppColors.successContainer;
      case RiskLevel.moderate:
        return AppColors.warningContainer;
      case RiskLevel.high:
      case RiskLevel.critical:
      case RiskLevel.unknown:
        return AppColors.errorContainer;
    }
  }

  IconData _levelIcon(RiskLevel level) {
    switch (level) {
      case RiskLevel.low:
        return Icons.check_circle_outline;
      case RiskLevel.moderate:
        return Icons.info_outline;
      case RiskLevel.high:
        return Icons.warning_amber_rounded;
      case RiskLevel.critical:
        return Icons.dangerous_outlined;
      case RiskLevel.unknown:
        return Icons.help_outline;
    }
  }

  /// Converts a snake_case damage class name to Title Case for display.
  static String formatClassName(String raw) {
    return raw
        .split('_')
        .map((word) => word.isEmpty
            ? ''
            : '${word[0].toUpperCase()}${word.substring(1)}')
        .join(' ');
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final level = assessment.level;
    final levelColor = _levelColor(level);
    final levelContainer = _levelContainerColor(level);
    final progressValue = (assessment.score / 100.0).clamp(0.0, 1.0);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Title ───────────────────────────────────────────────────────
            Text(
              'Road Condition & Risk Assessment',
              style: textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 14),

            // ── Level Badge & Score ─────────────────────────────────────────
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: levelContainer,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: levelColor.withValues(alpha: 0.4)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(_levelIcon(level), size: 18, color: levelColor),
                      const SizedBox(width: 6),
                      Text(
                        level.label,
                        style: textTheme.labelLarge?.copyWith(
                          color: levelColor,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                ),
                const Spacer(),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('Risk Score', style: textTheme.labelSmall),
                    Text(
                      '${assessment.score.toStringAsFixed(1)} / 100',
                      style: textTheme.titleMedium?.copyWith(
                        color: levelColor,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),

            // ── Score Bar ───────────────────────────────────────────────────
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: progressValue,
                minHeight: 8,
                backgroundColor: levelContainer,
                valueColor: AlwaysStoppedAnimation<Color>(levelColor),
              ),
            ),

            // ── Primary Damage Identified ───────────────────────────────────
            if (assessment.dominantDamage != null &&
                assessment.dominantDamage!.isNotEmpty) ...[
              const SizedBox(height: 14),
              Row(
                children: [
                  const Icon(
                    Icons.warning_amber_rounded,
                    size: 16,
                    color: AppColors.secondary,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Primary Damage: ',
                    style: textTheme.labelMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      formatClassName(assessment.dominantDamage!),
                      style: textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],

            const Divider(height: 20),

            // ── Maintenance Recommendation ──────────────────────────────────
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.build_circle_outlined,
                  size: 18,
                  color: AppColors.primary,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Recommendation',
                        style: textTheme.labelMedium?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        assessment.recommendation,
                        style: textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
