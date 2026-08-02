import 'package:flutter/material.dart';

/// Centralised colour palette for InfraGuard AI.
///
/// Every colour used in the application is declared here as a static const.
/// No widget or theme file may use a hardcoded colour value.
abstract final class AppColors {
  // ---------------------------------------------------------------------------
  // Brand — deep teal primary suited to infrastructure / inspection tooling
  // ---------------------------------------------------------------------------

  /// Primary brand colour — used for key actions, selected states, FABs.
  static const Color primary = Color(0xFF00695C); // teal-800

  /// Lighter tonal variant — hover states, containers, chips.
  static const Color primaryContainer = Color(0xFFB2DFDB); // teal-100

  /// On-primary — text / icons rendered on top of [primary].
  static const Color onPrimary = Color(0xFFFFFFFF);

  /// On-primary container — text / icons on [primaryContainer].
  static const Color onPrimaryContainer = Color(0xFF00251A);

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
  // Surfaces & backgrounds
  // ---------------------------------------------------------------------------

  /// Page / scaffold background.
  static const Color background = Color(0xFFF5F5F5); // grey-100

  /// Card, dialog, bottom-sheet surface.
  static const Color surface = Color(0xFFFFFFFF);

  /// Slightly elevated surface variant (e.g. sheet above background).
  static const Color surfaceVariant = Color(0xFFE8F5E9); // green-50

  /// On-surface — default text / icon colour.
  static const Color onSurface = Color(0xFF1C1B1F);

  /// On-surface variant — secondary icons, dividers.
  static const Color onSurfaceVariant = Color(0xFF49454F);

  // ---------------------------------------------------------------------------
  // Semantic — status indicators
  // ---------------------------------------------------------------------------

  /// Error — destructive actions, form validation, inference failures.
  static const Color error = Color(0xFFB00020);

  /// On-error — text / icons on top of [error].
  static const Color onError = Color(0xFFFFFFFF);

  /// Error container — subtle error background (banners, chips).
  static const Color errorContainer = Color(0xFFFFDAD6);

  /// Success — passed checks, confidence above threshold.
  static const Color success = Color(0xFF2E7D32); // green-800

  /// Success container — subtle success background.
  static const Color successContainer = Color(0xFFC8E6C9); // green-100

  /// Warning — medium-confidence detections, non-critical alerts.
  static const Color warning = Color(0xFFF57C00); // orange-800

  /// Warning container — subtle warning background.
  static const Color warningContainer = Color(0xFFFFE0B2); // orange-100

  // ---------------------------------------------------------------------------
  // Text
  // ---------------------------------------------------------------------------

  /// Primary text — headings, body copy, labels.
  static const Color textPrimary = Color(0xFF212121); // grey-900

  /// Secondary text — captions, hints, metadata.
  static const Color textSecondary = Color(0xFF757575); // grey-600

  /// Disabled text / icon state.
  static const Color textDisabled = Color(0xFFBDBDBD); // grey-400

  // ---------------------------------------------------------------------------
  // Outline & divider
  // ---------------------------------------------------------------------------

  /// Border, outline, divider lines.
  static const Color outline = Color(0xFFCAC4D0);

  /// Subtle divider (lower contrast than [outline]).
  static const Color outlineVariant = Color(0xFFE6E1E5);
}
