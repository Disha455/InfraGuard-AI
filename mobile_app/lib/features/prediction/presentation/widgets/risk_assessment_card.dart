import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../../data/models/risk_assessment_model.dart';

// ── RiskAssessmentCard ────────────────────────────────────────────────────────

/// Displays the CV-based inspection risk assessment returned by POST /predict.
///
/// Sections (top to bottom):
///   1. Level badge + score headline   — risk level text/icon + "25.1 / 100"
///   2. Score bar                      — LinearProgressIndicator, score / 100
///   3. Dominant damage                — formatted class name (when non-null)
///   4. Recommendation                 — verbatim backend text
///   5. Score breakdown                — anchor / breadth / count detail rows
///   6. Methodology disclaimer         — verbatim backend note, subdued style
///
/// All colours come from [AppColors].  No hardcoded colour values.
/// The card uses the global [CardTheme] from [AppTheme] so margin, elevation,
/// border-radius, and surface colour are all consistent with the rest of
/// [ResultPage].
class RiskAssessmentCard extends StatelessWidget {
  final RiskAssessmentModel assessment;

  const RiskAssessmentCard({super.key, required this.assessment});

  // ── Colour helpers ──────────────────────────────────────────────────────────

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

  // ── Class name formatter ────────────────────────────────────────────────────

  /// Converts a snake_case damage class name to Title Case for display.
  ///
  /// Examples:
  ///   longitudinal_crack → Longitudinal Crack
  ///   pothole            → Pothole
  static String formatClassName(String raw) {
    return raw
        .split('_')
        .map((word) => word.isEmpty
            ? ''
            : '${word[0].toUpperCase()}${word.substring(1)}')
        .join(' ');
  }

  // ── Build ───────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final level     = assessment.level;
    final levelColor     = _levelColor(level);
    final levelContainer = _levelContainerColor(level);

    // Clamp score defensively to [0, 1] for the progress bar.
    final progressValue = (assessment.score / 100.0).clamp(0.0, 1.0);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            // ── 1. Card header: section title ─────────────────────────────
            Text('Inspection Risk Assessment', style: textTheme.titleSmall),
            const SizedBox(height: 12),

            // ── 2. Level badge + score headline ──────────────────────────
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                // Level badge (colour + icon + text — not colour alone)
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: levelContainer,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: levelColor.withValues(alpha: 0.4)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(_levelIcon(level), size: 16, color: levelColor),
                      const SizedBox(width: 6),
                      Text(
                        level.label,
                        style: textTheme.labelMedium?.copyWith(
                          color: levelColor,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),

                const Spacer(),

                // Score headline — explicit framing avoids misreading as %
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'Risk Score',
                      style: textTheme.labelSmall,
                    ),
                    Text(
                      '${assessment.score.toStringAsFixed(1)} / 100',
                      style: textTheme.titleMedium?.copyWith(
                        color: levelColor,
                      ),
                    ),
                  ],
                ),
              ],
            ),

            const SizedBox(height: 10),

            // ── 3. Score bar ──────────────────────────────────────────────
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: progressValue,
                minHeight: 8,
                backgroundColor: levelContainer,
                valueColor: AlwaysStoppedAnimation<Color>(levelColor),
              ),
            ),

            // ── 4. Dominant damage ────────────────────────────────────────
            if (assessment.dominantDamage != null) ...[
              const SizedBox(height: 12),
              Row(
                children: [
                  Icon(Icons.location_on_outlined,
                      size: 15, color: AppColors.textSecondary),
                  const SizedBox(width: 6),
                  Text('Primary damage type: ', style: textTheme.labelMedium),
                  Expanded(
                    child: Text(
                      formatClassName(assessment.dominantDamage!),
                      style: textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],

            const Divider(height: 24),

            // ── 5. Recommendation ─────────────────────────────────────────
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.assignment_outlined,
                    size: 16, color: AppColors.textSecondary),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Recommendation', style: textTheme.labelMedium),
                      const SizedBox(height: 4),
                      Text(
                        assessment.recommendation,
                        style: textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              ],
            ),

            const SizedBox(height: 16),

            // ── 6. Score breakdown ────────────────────────────────────────
            Text('Score Breakdown', style: textTheme.labelMedium),
            const SizedBox(height: 8),
            _BreakdownGrid(breakdown: assessment.scoreBreakdown),

            const Divider(height: 24),

            // ── 7. Methodology disclaimer ─────────────────────────────────
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.info_outline,
                    size: 14, color: AppColors.textDisabled),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    assessment.methodologyNote,
                    style: textTheme.bodySmall?.copyWith(
                      color: AppColors.textDisabled,
                      fontStyle: FontStyle.italic,
                    ),
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

// ── _BreakdownGrid ────────────────────────────────────────────────────────────

/// Renders the score_breakdown map as a 2×2 grid of labelled value chips.
///
/// Two rows of two chips each so labels never wrap on a phone screen.
/// Uses the same surfaceVariant chip style as [_BboxField] in the existing
/// detection cards for visual consistency.
///
/// Layout:
///   Anchor Score  | Breadth Bonus
///   Final Score   | Detections
class _BreakdownGrid extends StatelessWidget {
  final Map<String, double> breakdown;

  const _BreakdownGrid({required this.breakdown});

  @override
  Widget build(BuildContext context) {
    final topRow = [
      _BreakdownItem(
        label: 'Anchor Score',
        value: _fmt(breakdown['anchor_score']),
      ),
      _BreakdownItem(
        label: 'Breadth Bonus',
        value: _fmt(breakdown['breadth_bonus']),
      ),
    ];

    final bottomRow = [
      _BreakdownItem(
        label: 'Final Score',
        value: _fmt(breakdown['final_score']),
      ),
      _BreakdownItem(
        label: 'Detections',
        value: (breakdown['detection_count']?.toInt() ?? 0).toString(),
      ),
    ];

    return Column(
      children: [
        // Top row
        Row(
          children: topRow
              .map((item) => Expanded(child: _BreakdownChip(item: item)))
              .toList(),
        ),
        const SizedBox(height: 6),
        // Bottom row
        Row(
          children: bottomRow
              .map((item) => Expanded(child: _BreakdownChip(item: item)))
              .toList(),
        ),
      ],
    );
  }

  String _fmt(double? v) => v != null ? v.toStringAsFixed(1) : '–';
}

class _BreakdownItem {
  final String label;
  final String value;
  const _BreakdownItem({required this.label, required this.value});
}

class _BreakdownChip extends StatelessWidget {
  final _BreakdownItem item;
  const _BreakdownChip({required this.item});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Container(
      margin: const EdgeInsets.only(right: 6),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Text(item.label, style: textTheme.labelSmall, textAlign: TextAlign.center),
          const SizedBox(height: 2),
          Text(item.value, style: textTheme.bodySmall, textAlign: TextAlign.center),
        ],
      ),
    );
  }
}
