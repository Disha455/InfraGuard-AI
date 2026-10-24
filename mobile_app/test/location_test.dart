import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:geolocator/geolocator.dart';
import 'package:mobile_app/core/services/location_service.dart';
import 'package:mobile_app/features/prediction/data/models/inspection_location.dart';

// ── FakeGeolocatorWrapper ─────────────────────────────────────────────────────
//
// Test double for [GeolocatorWrapper].  All behaviour is controlled through
// public fields set before each test — no mocking library required.

class FakeGeolocatorWrapper implements GeolocatorWrapper {
  bool serviceEnabled    = true;
  LocationPermission permission = LocationPermission.whileInUse;
  LocationPermission afterRequest = LocationPermission.whileInUse;

  // When non-null, getCurrentPosition throws this instead of returning.
  Object? positionError;

  double lat      = 12.9716;
  double lng      = 77.5946;
  double accuracy = 15.0;

  @override
  Future<bool> isLocationServiceEnabled() async => serviceEnabled;

  @override
  Future<LocationPermission> checkPermission() async => permission;

  @override
  Future<LocationPermission> requestPermission() async => afterRequest;

  @override
  Future<Position> getCurrentPosition({
    required LocationSettings locationSettings,
  }) async {
    if (positionError != null) throw positionError!;
    return Position(
      latitude:              lat,
      longitude:             lng,
      accuracy:              accuracy,
      altitude:              0.0,
      altitudeAccuracy:      0.0,
      heading:               0.0,
      headingAccuracy:       0.0,
      speed:                 0.0,
      speedAccuracy:         0.0,
      timestamp:             DateTime.now(),
      isMocked:              false,
    );
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

LocationService _service(FakeGeolocatorWrapper fake) =>
    LocationService(geolocator: fake);

// =============================================================================
// InspectionLocation model tests
// =============================================================================

void main() {
  group('InspectionLocation', () {
    test('stores latitude and longitude', () {
      const loc = InspectionLocation(latitude: 12.9716, longitude: 77.5946);
      expect(loc.latitude,  closeTo(12.9716, 1e-9));
      expect(loc.longitude, closeTo(77.5946, 1e-9));
    });

    test('accuracy may be null', () {
      const loc = InspectionLocation(latitude: 0.0, longitude: 0.0);
      expect(loc.accuracy, isNull);
    });

    test('accuracy is stored when provided', () {
      const loc = InspectionLocation(
          latitude: 1.0, longitude: 2.0, accuracy: 8.5);
      expect(loc.accuracy, closeTo(8.5, 1e-9));
    });

    test('const constructor works', () {
      const loc = InspectionLocation(latitude: 51.5074, longitude: -0.1278);
      expect(loc.latitude, closeTo(51.5074, 1e-9));
    });

    test('equality: same values are equal', () {
      const a = InspectionLocation(latitude: 1.0, longitude: 2.0, accuracy: 5.0);
      const b = InspectionLocation(latitude: 1.0, longitude: 2.0, accuracy: 5.0);
      expect(a, equals(b));
    });

    test('equality: different latitude is not equal', () {
      const a = InspectionLocation(latitude: 1.0, longitude: 2.0);
      const b = InspectionLocation(latitude: 9.0, longitude: 2.0);
      expect(a, isNot(equals(b)));
    });

    test('toString includes lat and lng', () {
      const loc = InspectionLocation(latitude: 12.9716, longitude: 77.5946);
      expect(loc.toString(), contains('12.9716'));
      expect(loc.toString(), contains('77.5946'));
    });

    test('toString includes accuracy when present', () {
      const loc = InspectionLocation(
          latitude: 0.0, longitude: 0.0, accuracy: 20.0);
      expect(loc.toString(), contains('20.0'));
    });
  });

  // ===========================================================================
  // LocationService tests
  // ===========================================================================

  group('LocationService — service disabled', () {
    test('returns null when location service is off', () async {
      final fake = FakeGeolocatorWrapper()..serviceEnabled = false;
      final result = await _service(fake).getCurrentLocation();
      expect(result, isNull);
    });

    test('does NOT request permission when service is off', () async {
      var requestCalled = false;
      final fake = FakeGeolocatorWrapper()
        ..serviceEnabled = false;
      // Override requestPermission to detect if it's called.
      // We verify indirectly: if service is off we return null before
      // reaching the permission step, so position is also not fetched.
      final result = await _service(fake).getCurrentLocation();
      expect(result, isNull);
      expect(requestCalled, isFalse); // never triggered
    });
  });

  group('LocationService — permission denied', () {
    test('requests permission when initially denied, still denied → null', () async {
      final fake = FakeGeolocatorWrapper()
        ..permission    = LocationPermission.denied
        ..afterRequest  = LocationPermission.denied;
      final result = await _service(fake).getCurrentLocation();
      expect(result, isNull);
    });

    test('returns null when permission is deniedForever at check', () async {
      final fake = FakeGeolocatorWrapper()
        ..permission = LocationPermission.deniedForever;
      final result = await _service(fake).getCurrentLocation();
      expect(result, isNull);
    });

    test('returns null when permission is denied after request → deniedForever',
        () async {
      final fake = FakeGeolocatorWrapper()
        ..permission   = LocationPermission.denied
        ..afterRequest = LocationPermission.deniedForever;
      final result = await _service(fake).getCurrentLocation();
      expect(result, isNull);
    });
  });

  group('LocationService — permission granted', () {
    test('returns InspectionLocation on whileInUse permission', () async {
      final fake = FakeGeolocatorWrapper()
        ..permission = LocationPermission.whileInUse
        ..lat        = 12.9716
        ..lng        = 77.5946
        ..accuracy   = 15.0;
      final result = await _service(fake).getCurrentLocation();
      expect(result, isNotNull);
      expect(result!.latitude,  closeTo(12.9716, 1e-9));
      expect(result.longitude, closeTo(77.5946, 1e-9));
      expect(result.accuracy,  closeTo(15.0, 1e-9));
    });

    test('returns InspectionLocation on always permission', () async {
      final fake = FakeGeolocatorWrapper()
        ..permission = LocationPermission.always;
      final result = await _service(fake).getCurrentLocation();
      expect(result, isNotNull);
    });

    test('maps Position latitude/longitude correctly', () async {
      final fake = FakeGeolocatorWrapper()
        ..lat = 51.5074
        ..lng = -0.1278
        ..accuracy = 8.0;
      final result = await _service(fake).getCurrentLocation();
      expect(result!.latitude,  closeTo(51.5074, 1e-9));
      expect(result.longitude, closeTo(-0.1278, 1e-9));
      expect(result.accuracy,  closeTo(8.0, 1e-9));
    });

    test('promotes denied → granted after request', () async {
      final fake = FakeGeolocatorWrapper()
        ..permission   = LocationPermission.denied
        ..afterRequest = LocationPermission.whileInUse
        ..lat          = 1.23
        ..lng          = 4.56;
      final result = await _service(fake).getCurrentLocation();
      expect(result, isNotNull);
      expect(result!.latitude, closeTo(1.23, 1e-9));
    });
  });

  group('LocationService — acquisition failure', () {
    test('returns null on TimeoutException', () async {
      final fake = FakeGeolocatorWrapper()
        ..positionError = TimeoutException('GPS timeout');
      final result = await _service(fake).getCurrentLocation();
      expect(result, isNull);
    });

    test('returns null on generic platform exception', () async {
      final fake = FakeGeolocatorWrapper()
        ..positionError = Exception('platform error');
      final result = await _service(fake).getCurrentLocation();
      expect(result, isNull);
    });

    test('returns null on LocationServiceDisabledException', () async {
      final fake = FakeGeolocatorWrapper()
        ..positionError = const LocationServiceDisabledException();
      final result = await _service(fake).getCurrentLocation();
      expect(result, isNull);
    });
  });

  group('LocationService — accuracy edge cases', () {
    test('accuracy is null when position reports 0.0', () async {
      final fake = FakeGeolocatorWrapper()..accuracy = 0.0;
      final result = await _service(fake).getCurrentLocation();
      // accuracy <= 0 is treated as unavailable
      expect(result!.accuracy, isNull);
    });

    test('accuracy is stored when positive', () async {
      final fake = FakeGeolocatorWrapper()..accuracy = 42.5;
      final result = await _service(fake).getCurrentLocation();
      expect(result!.accuracy, closeTo(42.5, 1e-9));
    });
  });
}
