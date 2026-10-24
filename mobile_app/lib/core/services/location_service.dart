import 'dart:async';

import 'package:geolocator/geolocator.dart';
import '../../features/prediction/data/models/inspection_location.dart';

// ── GeolocatorWrapper ─────────────────────────────────────────────────────────

/// Thin abstraction over [Geolocator]'s static API.
///
/// Exists solely to make [LocationService] testable without a real device
/// or platform channel.  Production code uses [DefaultGeolocatorWrapper];
/// tests inject a [FakeGeolocatorWrapper] or any other implementation.
///
/// Only the three calls that [LocationService] actually needs are declared
/// here — no attempt to wrap the entire Geolocator API.
abstract class GeolocatorWrapper {
  /// Delegates to [Geolocator.isLocationServiceEnabled].
  Future<bool> isLocationServiceEnabled();

  /// Delegates to [Geolocator.checkPermission].
  Future<LocationPermission> checkPermission();

  /// Delegates to [Geolocator.requestPermission].
  Future<LocationPermission> requestPermission();

  /// Delegates to [Geolocator.getCurrentPosition].
  Future<Position> getCurrentPosition({
    required LocationSettings locationSettings,
  });
}

// ── DefaultGeolocatorWrapper ──────────────────────────────────────────────────

/// Production implementation — passes every call through to the real
/// [Geolocator] static API.
class DefaultGeolocatorWrapper implements GeolocatorWrapper {
  const DefaultGeolocatorWrapper();

  @override
  Future<bool> isLocationServiceEnabled() =>
      Geolocator.isLocationServiceEnabled();

  @override
  Future<LocationPermission> checkPermission() =>
      Geolocator.checkPermission();

  @override
  Future<LocationPermission> requestPermission() =>
      Geolocator.requestPermission();

  @override
  Future<Position> getCurrentPosition({
    required LocationSettings locationSettings,
  }) =>
      Geolocator.getCurrentPosition(
        locationSettings: locationSettings,
      );
}

// ── LocationService ───────────────────────────────────────────────────────────

/// Obtains the device's current foreground GPS location.
///
/// Responsibilities:
///   - Check whether the device's location service is enabled.
///   - Request location permission when needed.
///   - Acquire a single GPS fix with high accuracy.
///   - Return an [InspectionLocation] on success, or [null] on any
///     expected failure (service off, permission denied, timeout, error).
///
/// Non-responsibilities:
///   - No UI (no SnackBars, dialogs, or navigation).
///   - No knowledge of inspections, predictions, or history.
///   - No background or continuous location tracking.
///
/// Usage:
/// ```dart
/// final service = LocationService();
/// final location = await service.getCurrentLocation();
/// // location is null when GPS is unavailable or denied — always safe.
/// ```
class LocationService {
  final GeolocatorWrapper _geolocator;

  /// Creates a [LocationService].
  ///
  /// [geolocator] defaults to [DefaultGeolocatorWrapper] for production use.
  /// Pass a custom implementation in tests to avoid platform channel calls.
  LocationService({GeolocatorWrapper? geolocator})
      : _geolocator = geolocator ?? const DefaultGeolocatorWrapper();

  // ── Location settings ───────────────────────────────────────────────────────

  /// High-accuracy location settings used for all acquisition calls.
  ///
  /// [timeLimit] of 10 seconds prevents hanging the loading overlay
  /// indefinitely if the GPS cannot get a fix (e.g. indoors).
  static const LocationSettings _locationSettings = LocationSettings(
    accuracy: LocationAccuracy.high,
    timeLimit: Duration(seconds: 10),
  );

  // ── Public API ──────────────────────────────────────────────────────────────

  /// Returns the current GPS location, or [null] when unavailable.
  ///
  /// Returns [null] without throwing for:
  ///   - Location service disabled (GPS radio off).
  ///   - Permission denied (user tapped "Don't allow").
  ///   - Permission permanently denied.
  ///   - Acquisition timeout (no fix within 10 seconds).
  ///   - Any other platform exception during acquisition.
  ///
  /// The caller (typically [HomePage._onAnalyzeImage]) treats [null] as
  /// "location unavailable" and proceeds with the inspection regardless.
  Future<InspectionLocation?> getCurrentLocation() async {
    // ── Step A: service enabled? ──────────────────────────────────────────
    // Check before asking for permission — if the GPS radio is off,
    // showing a permission dialog would confuse the user.
    final serviceEnabled = await _geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      return null;
    }

    // ── Step B: permission ────────────────────────────────────────────────
    LocationPermission permission = await _geolocator.checkPermission();

    if (permission == LocationPermission.denied) {
      permission = await _geolocator.requestPermission();
    }

    // deniedForever means the OS will not show the dialog again — bail out.
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      return null;
    }

    // ── Step C: acquire position ──────────────────────────────────────────
    try {
      final position = await _geolocator.getCurrentPosition(
        locationSettings: _locationSettings,
      );

      // ── Step D: convert to domain model ──────────────────────────────
      return InspectionLocation(
        latitude:  position.latitude,
        longitude: position.longitude,
        accuracy:  position.accuracy > 0 ? position.accuracy : null,
      );
    } on TimeoutException {
      // GPS could not get a fix within the time limit — non-fatal.
      return null;
    } catch (_) {
      // Any other platform/OS exception — treat as unavailable.
      return null;
    }
  }
}
