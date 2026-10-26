import 'package:flutter/material.dart';

/// Centralised colour palette for InfraGuard AI.
///
/// Every colour used in the application is declared here as a static const.
/// No widget or theme file may use a hardcoded colour value.
abstract final class AppColors {
  // ---------------------------------------------------------------------------
  // Brand — professional navy blue suited to infrastructure / inspection tooling
  // ---------------------------------------------------------------------------

  /// Primary brand colour — navy blue used for key actions, app bars, buttons.
  static const Color primary = Color(0xFF0F2B48); // deep navy-blue

  /// Lighter tonal variant — hover states, containers, chips.
  static const Color primaryContainer = Color(0xFFE2EBF5); // light navy ice

  /// On-primary — text / icons rendered on top of [primary].
  static const Color onPrimary = Color(0xFFFFFFFF);

  /// On-primary container — text / icons on [primaryContainer].
  static const Color onPrimaryContainer = Color(0xFF07192D);

  // ---------------------------------------------------------------------------
  // Secondary — amber accent, conveys caution/inspection context
  // ---------------------------------------------------------------------------

  /// Secondary brand colour — badges, secondary actions, tab indicators.
  static const Color secondary = Color(0xFFF57F17); // amber-900

  /// Lighter tonal variant of [secondary].
  static const Color secondaryContainer = Color(0xFFFFECB3); // amber-100

  /// On-secondary — text / icons rendered on top of [secondary].
  static const Color onSecondary = Color(0xFFFFFFFF);

  /// On-secondary container — text / icons on [secondaryContainer].
  static const Color onSecondaryContainer = Color(0xFF4E2600);

  // ---------------------------------------------------------------------------
  // Surfaces & backgrounds — soft pastel tones for eye comfort & clean contrast
  // ---------------------------------------------------------------------------

  /// Page / scaffold background — soft pastel ice-slate tone.
  static const Color background = Color(0xFFEAF0F6);

  /// Card, dialog, bottom-sheet surface.
  static const Color surface = Color(0xFFFFFFFF);

  /// Slightly elevated surface variant (input fill, chips, badge containers).
  static const Color surfaceVariant = Color(0xFFDFE8F1);

  /// On-surface — default text / icon colour.
  static const Color onSurface = Color(0xFF1E293B);

  /// On-surface variant — secondary icons, dividers.
  static const Color onSurfaceVariant = Color(0xFF5B6E83);

  // ---------------------------------------------------------------------------
  // Semantic — status indicators
  // ---------------------------------------------------------------------------

  /// Error — destructive actions, form validation, inference failures.
  static const Color error = Color(0xFFDC2626);

  /// On-error — text / icons on top of [error].
  static const Color onError = Color(0xFFFFFFFF);

  /// Error container — subtle error background (banners, chips).
  static const Color errorContainer = Color(0xFFFEE2E2);

  /// Success — passed checks, confidence above threshold.
  static const Color success = Color(0xFF059669);

  /// Success container — subtle success background.
  static const Color successContainer = Color(0xFFD1FAE5);

  /// Warning — medium-confidence detections, non-critical alerts.
  static const Color warning = Color(0xFFD97706);

  /// Warning container — subtle warning background.
  static const Color warningContainer = Color(0xFFFEF3C7);

  // ---------------------------------------------------------------------------
  // Text
  // ---------------------------------------------------------------------------

  /// Primary text — headings, body copy, labels.
  static const Color textPrimary = Color(0xFF1E293B);

  /// Secondary text — captions, hints, metadata.
  static const Color textSecondary = Color(0xFF5B6E83);

  /// Disabled text / icon state.
  static const Color textDisabled = Color(0xFF94A3B8);

  // ---------------------------------------------------------------------------
  // Outline & divider
  // ---------------------------------------------------------------------------

  /// Border, outline, divider lines.
  static const Color outline = Color(0xFFBAC9D8);

  /// Subtle divider (lower contrast than [outline]).
  static const Color outlineVariant = Color(0xFFD0DCE7);

  // ---------------------------------------------------------------------------
  // Gradients — sophisticated, non-boring multi-tone transitions
  // ---------------------------------------------------------------------------

  /// Ambient background pastel mesh gradient (slate-blue -> pearl -> soft lavender).
  static const LinearGradient backgroundGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFFE8EEF5), // soft ice blue
      Color(0xFFF1F5F9), // crisp misty pearl
      Color(0xFFEDE8F5), // subtle lilac mist
    ],
    stops: [0.0, 0.55, 1.0],
  );

  /// Executive brand gradient for AppBars and hero headers.
  static const LinearGradient appBarGradient = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: [
      Color(0xFF0A2239), // deep midnight navy
      Color(0xFF133E68), // royal steel sapphire
      Color(0xFF1D5A8F), // vibrant slate cerulean
    ],
  );

  /// Primary action button gradient.
  static const LinearGradient buttonGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF145388),
      Color(0xFF0D3256),
    ],
  );

  /// Accent cyan-teal gradient for telemetry highlights, icons, active chips.
  static const LinearGradient accentGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF0284C7), // sky-600
      Color(0xFF0D9488), // teal-600
    ],
  );

  /// Soft card gradient for hero containers and status banners.
  static const LinearGradient cardHeaderGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFFFFFFFF),
      Color(0xFFF0F5FA),
    ],
  );

  /// Status: Low risk gradient.
  static const LinearGradient lowRiskGradient = LinearGradient(
    colors: [Color(0xFF059669), Color(0xFF10B981)],
  );

  /// Status: Moderate risk gradient.
  static const LinearGradient moderateRiskGradient = LinearGradient(
    colors: [Color(0xFFD97706), Color(0xFFF59E0B)],
  );

  /// Status: High/Critical risk gradient.
  static const LinearGradient highRiskGradient = LinearGradient(
    colors: [Color(0xFFDC2626), Color(0xFFE11D48)],
  );
}
