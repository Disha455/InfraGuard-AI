import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/main.dart';
import 'package:mobile_app/core/services/inspection_history_service.dart';
import 'package:mobile_app/core/theme/app_theme.dart';
import 'package:mobile_app/features/prediction/data/models/detection_model.dart';
import 'package:mobile_app/features/prediction/data/models/bounding_box_model.dart';
import 'package:mobile_app/features/prediction/data/models/inspection_history_item.dart';
import 'package:mobile_app/features/prediction/data/models/inspection_location.dart';
import 'package:mobile_app/features/prediction/data/models/prediction_response_model.dart';
import 'package:mobile_app/features/prediction/data/models/risk_assessment_model.dart';
import 'package:mobile_app/features/prediction/presentation/pages/history_page.dart';

import 'package:mobile_app/features/prediction/presentation/pages/home_page.dart';

void main() {
  // ── Welcome & Role Selection smoke test ────────────────────────────────────
  testWidgets('Welcome / Role Selection page renders when app opens',
      (WidgetTester tester) async {
    await tester.pumpWidget(const InfraGuardApp());

    expect(find.text('InfraGuard-AI'), findsOneWidget);
    expect(find.text('Inspector Login'), findsOneWidget);
    expect(find.text('Admin Login'), findsOneWidget);
  });

  // ── Home page smoke test ────────────────────────────────────────────────────
  testWidgets('Home page renders correctly when loaded',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        theme: null,
        home: HomePage(),
      ),
    );

    expect(find.text('InfraGuard AI'), findsOneWidget);
    expect(find.text('Road Damage Detection'), findsOneWidget);
    expect(find.text('Gallery'), findsOneWidget);
    expect(find.text('Camera'), findsOneWidget);
    expect(find.text('Analyze Image'), findsOneWidget);
  });

  // ── Inspector Login flow test ──────────────────────────────────────────────
  testWidgets('Inspector flow navigates from Welcome to HomePage',
      (WidgetTester tester) async {
    await tester.pumpWidget(const InfraGuardApp());

    // Tap Inspector Login
    await tester.tap(find.text('Inspector Login'));
    await tester.pumpAndSettle();

    expect(find.text('Field Inspector Portal'), findsOneWidget);
    expect(find.text('Sign In as Inspector'), findsOneWidget);

    // Scroll to and tap Sign In
    final signInBtn = find.text('Sign In as Inspector');
    await tester.ensureVisible(signInBtn);
    await tester.pumpAndSettle();
    await tester.tap(signInBtn);
    await tester.pump(const Duration(milliseconds: 350));
    await tester.pump(const Duration(milliseconds: 400));

    // Reached the existing HomePage
    expect(find.text('Road Damage Detection'), findsOneWidget);
    expect(find.text('Gallery'), findsOneWidget);
    expect(find.text('Camera'), findsOneWidget);
  });

  // ── Admin Login flow test ──────────────────────────────────────────────────
  testWidgets('Admin flow navigates from Welcome to Admin Dashboard',
      (WidgetTester tester) async {
    await tester.pumpWidget(const InfraGuardApp());

    // Tap Admin Login
    await tester.tap(find.text('Admin Login'));
    await tester.pumpAndSettle();

    expect(find.text('Admin Analytics Portal'), findsOneWidget);
    expect(find.text('Sign In as Administrator'), findsOneWidget);

    // Scroll to and tap Sign In
    final adminBtn = find.text('Sign In as Administrator');
    await tester.ensureVisible(adminBtn);
    await tester.pumpAndSettle();
    await tester.tap(adminBtn);
    await tester.pump(const Duration(milliseconds: 350));
    await tester.pumpAndSettle();

    // Reached the Admin Dashboard
    expect(find.text('Administrator Analytics Dashboard'), findsOneWidget);
    expect(find.text('Total Inspections'), findsOneWidget);
    expect(find.text('Damaged Roads'), findsOneWidget);
    expect(find.text('High-Risk Roads'), findsOneWidget);
    expect(find.text('Pending Inspections'), findsOneWidget);
  });

  // ── RiskAssessmentModel parsing tests ──────────────────────────────────────

  group('RiskLevel.fromString', () {
    test('parses LOW', () {
      expect(RiskLevel.fromString('LOW'), RiskLevel.low);
    });

    test('parses MODERATE', () {
      expect(RiskLevel.fromString('MODERATE'), RiskLevel.moderate);
    });

    test('parses HIGH', () {
      expect(RiskLevel.fromString('HIGH'), RiskLevel.high);
    });

    test('parses CRITICAL', () {
      expect(RiskLevel.fromString('CRITICAL'), RiskLevel.critical);
    });

    test('unknown string returns unknown', () {
      expect(RiskLevel.fromString('EXTREME'), RiskLevel.unknown);
    });

    test('null returns unknown', () {
      expect(RiskLevel.fromString(null), RiskLevel.unknown);
    });

    test('case-insensitive — lowercase works', () {
      expect(RiskLevel.fromString('low'), RiskLevel.low);
      expect(RiskLevel.fromString('critical'), RiskLevel.critical);
    });
  });

  group('RiskAssessmentModel.fromJson', () {
    Map<String, dynamic> baseJson({
      double score = 25.1,
      String level = 'MODERATE',
      List<dynamic> detectionRisks = const [],
      Object? dominantDamage = 'longitudinal_crack',
      Map<String, dynamic>? scoreBreakdown,
      String recommendation = 'Schedule a review.',
      String methodologyNote = 'CV-based assessment v1.',
    }) =>
        {
          'score': score,
          'level': level,
          'detection_risks': detectionRisks,
          'dominant_damage': dominantDamage,
          'score_breakdown': scoreBreakdown ??
              {
                'anchor_score': 23.25,
                'breadth_bonus': 1.86,
                'final_score': 25.1,
                'detection_count': 2.0,
              },
          'recommendation': recommendation,
          'methodology_note': methodologyNote,
        };

    test('parses all fields correctly', () {
      final model = RiskAssessmentModel.fromJson(baseJson());

      expect(model.score, closeTo(25.1, 0.001));
      expect(model.level, RiskLevel.moderate);
      expect(model.dominantDamage, 'longitudinal_crack');
      expect(model.recommendation, 'Schedule a review.');
      expect(model.methodologyNote, 'CV-based assessment v1.');
    });

    test('dominant_damage null when backend sends null', () {
      final model = RiskAssessmentModel.fromJson(
        baseJson(dominantDamage: null),
      );
      expect(model.dominantDamage, isNull);
    });

    test('parses detection_risks list', () {
      final json = baseJson(
        detectionRisks: [
          {
            'class_name': 'pothole',
            'severity_weight': 1.0,
            'confidence': 0.85,
            'normalised_area': 0.25,
            'detection_score': 80.0,
          }
        ],
      );
      final model = RiskAssessmentModel.fromJson(json);
      expect(model.detectionRisks.length, 1);
      expect(model.detectionRisks[0].className, 'pothole');
      expect(model.detectionRisks[0].detectionScore, closeTo(80.0, 0.001));
    });

    test('parses score_breakdown correctly', () {
      final model = RiskAssessmentModel.fromJson(baseJson());
      expect(model.scoreBreakdown['anchor_score'], closeTo(23.25, 0.001));
      expect(model.scoreBreakdown['breadth_bonus'], closeTo(1.86, 0.001));
      expect(model.scoreBreakdown['detection_count'], closeTo(2.0, 0.001));
    });

    test('level LOW is parsed correctly', () {
      final model = RiskAssessmentModel.fromJson(baseJson(level: 'LOW'));
      expect(model.level, RiskLevel.low);
    });

    test('level HIGH is parsed correctly', () {
      final model = RiskAssessmentModel.fromJson(baseJson(level: 'HIGH'));
      expect(model.level, RiskLevel.high);
    });

    test('level CRITICAL is parsed correctly', () {
      final model = RiskAssessmentModel.fromJson(baseJson(level: 'CRITICAL'));
      expect(model.level, RiskLevel.critical);
    });
  });

  // ── PredictionResponseModel backward compatibility ──────────────────────────

  group('PredictionResponseModel backward compatibility', () {
    final legacyJson = <String, dynamic>{
      'status': 'success',
      'run_id': 'run_20260101_000000',
      'annotated_image': 'http://example.com/annotated.jpg',
      'detections_file': '/tmp/detections.json',
      'summary_file': '/tmp/summary.txt',
      'total_detections': 0,
      'detections': [],
      // NOTE: no 'risk_assessment' key — simulates a pre-risk-feature response
    };

    test('parses successfully without risk_assessment', () {
      final model = PredictionResponseModel.fromJson(legacyJson);
      expect(model.status, 'success');
      expect(model.riskAssessment, isNull);
    });

    test('parses successfully with null risk_assessment value', () {
      final json = Map<String, dynamic>.from(legacyJson)
        ..['risk_assessment'] = null;
      final model = PredictionResponseModel.fromJson(json);
      expect(model.riskAssessment, isNull);
    });

    test('parses risk_assessment when present', () {
      final json = Map<String, dynamic>.from(legacyJson)
        ..['risk_assessment'] = {
          'score': 0.0,
          'level': 'LOW',
          'detection_risks': [],
          'dominant_damage': null,
          'score_breakdown': {
            'anchor_score': 0.0,
            'breadth_bonus': 0.0,
            'final_score': 0.0,
            'detection_count': 0.0,
          },
          'recommendation': 'No damage detected.',
          'methodology_note': 'CV-based assessment v1.',
        };
      final model = PredictionResponseModel.fromJson(json);
      expect(model.riskAssessment, isNotNull);
      expect(model.riskAssessment!.level, RiskLevel.low);
      expect(model.riskAssessment!.score, closeTo(0.0, 0.001));
    });
  });

  // ── RiskAssessmentCard.formatClassName ─────────────────────────────────────

  group('RiskAssessmentCard.formatClassName', () {
    test('longitudinal_crack → Longitudinal Crack', () {
      expect(
        _formatClassName('longitudinal_crack'),
        'Longitudinal Crack',
      );
    });

    test('transverse_crack → Transverse Crack', () {
      expect(_formatClassName('transverse_crack'), 'Transverse Crack');
    });

    test('alligator_crack → Alligator Crack', () {
      expect(_formatClassName('alligator_crack'), 'Alligator Crack');
    });

    test('pothole → Pothole', () {
      expect(_formatClassName('pothole'), 'Pothole');
    });

    test('single word is capitalised', () {
      expect(_formatClassName('damage'), 'Damage');
    });
  });

  // ── InspectionHistoryItem — location field ──────────────────────────────────

  group('InspectionHistoryItem', () {
    final dummyResult = PredictionResponseModel(
      status: 'success',
      runId: 'run_test',
      annotatedImage: 'http://example.com/annotated.jpg',
      detectionsFile: '/tmp/detections.json',
      summaryFile: '/tmp/summary.txt',
      detections: const [],
      totalDetections: 0,
    );

    test('accepts a non-null location', () {
      const loc = InspectionLocation(latitude: 12.9716, longitude: 77.5946);
      final item = InspectionHistoryItem(
        predictionResult: dummyResult,
        inspectionDate: DateTime(2026, 8, 1),
        originalImagePath: '/img.jpg',
        location: loc,
      );
      expect(item.location, isNotNull);
      expect(item.location!.latitude, closeTo(12.9716, 1e-9));
      expect(item.location!.longitude, closeTo(77.5946, 1e-9));
    });

    test('location defaults to null when not provided', () {
      final item = InspectionHistoryItem(
        predictionResult: dummyResult,
        inspectionDate: DateTime(2026, 8, 1),
        originalImagePath: '/img.jpg',
      );
      expect(item.location, isNull);
    });

    test('existing accessors still work when location is null', () {
      final item = InspectionHistoryItem(
        predictionResult: dummyResult,
        inspectionDate: DateTime(2026, 8, 1),
        originalImagePath: '/img.jpg',
      );
      expect(item.runId, 'run_test');
      expect(item.totalDetections, 0);
      expect(item.status, 'success');
      expect(item.firstDamageType, isNull);
    });

    test('firstDamageType returns class name of first detection', () {
      final resultWithDetections = PredictionResponseModel(
        status: 'success',
        runId: 'run_det',
        annotatedImage: 'http://example.com/annotated.jpg',
        detectionsFile: '/tmp/d.json',
        summaryFile: '/tmp/s.txt',
        totalDetections: 1,
        detections: [
          DetectionModel(
            classId: 0,
            className: 'pothole',
            confidence: 0.85,
            boundingBox: const BoundingBoxModel(
                x1: 0, y1: 0, x2: 100, y2: 100),
          ),
        ],
      );
      final item = InspectionHistoryItem(
        predictionResult: resultWithDetections,
        inspectionDate: DateTime(2026, 8, 1),
        originalImagePath: '/img.jpg',
      );
      expect(item.firstDamageType, 'pothole');
    });
  });

  // ── InspectionHistoryService — location parameter ───────────────────────────

  group('InspectionHistoryService', () {
    final service = InspectionHistoryService.instance;

    final dummyResult = PredictionResponseModel(
      status: 'success',
      runId: 'run_svc_test',
      annotatedImage: 'http://example.com/annotated.jpg',
      detectionsFile: '/tmp/d.json',
      summaryFile: '/tmp/s.txt',
      detections: const [],
      totalDetections: 0,
    );

    setUp(() => service.clearHistory());

    test('stores location when provided', () {
      const loc = InspectionLocation(latitude: 51.5074, longitude: -0.1278);
      service.addInspection(
        dummyResult,
        originalImagePath: '/img.jpg',
        location: loc,
      );
      final items = service.getHistory();
      expect(items.length, 1);
      expect(items[0].location, isNotNull);
      expect(items[0].location!.latitude, closeTo(51.5074, 1e-9));
    });

    test('stores null location when location is unavailable', () {
      service.addInspection(
        dummyResult,
        originalImagePath: '/img.jpg',
        location: null,
      );
      final items = service.getHistory();
      expect(items.length, 1);
      expect(items[0].location, isNull);
    });

    test('stores null location when location param is omitted', () {
      service.addInspection(
        dummyResult,
        originalImagePath: '/img.jpg',
      );
      final items = service.getHistory();
      expect(items[0].location, isNull);
    });

    test('newest-first ordering is preserved with location', () {
      const locA = InspectionLocation(latitude: 1.0, longitude: 1.0);
      service.addInspection(dummyResult,
          originalImagePath: '/a.jpg', location: locA);
      service.addInspection(dummyResult,
          originalImagePath: '/b.jpg', location: null);

      final items = service.getHistory();
      // most recent (b, no location) is first
      expect(items[0].location, isNull);
      expect(items[1].location, isNotNull);
    });

    test('count and isEmpty reflect entries correctly', () {
      expect(service.isEmpty, isTrue);
      service.addInspection(dummyResult, originalImagePath: '/x.jpg');
      expect(service.count, 1);
      expect(service.isEmpty, isFalse);
    });

    test('clearHistory removes all entries', () {
      service.addInspection(dummyResult, originalImagePath: '/x.jpg');
      service.clearHistory();
      expect(service.isEmpty, isTrue);
    });
  });

  // ── HistoryPage location UI widget tests ────────────────────────────────────

  // Shared test fixtures
  final historyDummyResult = PredictionResponseModel(
    status: 'success',
    runId: 'run_ui_test',
    annotatedImage: 'http://10.0.2.2:8000/outputs/run_ui_test/annotated.jpg',
    detectionsFile: '/tmp/d.json',
    summaryFile: '/tmp/s.txt',
    detections: const [],
    totalDetections: 0,
  );

  Widget buildHistoryPage() => MaterialApp(
        theme: AppTheme.lightTheme,
        home: const HistoryPage(),
        routes: {
          '/result': (_) => const Scaffold(body: Text('ResultPage')),
        },
      );

  group('HistoryPage — location status row', () {
    final service = InspectionHistoryService.instance;

    setUp(() => service.clearHistory());

    testWidgets('shows "Location captured" when location is non-null',
        (tester) async {
      service.addInspection(
        historyDummyResult,
        originalImagePath: '/img.jpg',
        location: const InspectionLocation(
            latitude: 12.9716, longitude: 77.5946),
      );

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();

      expect(find.text('Location captured'), findsOneWidget);
    });

    testWidgets('shows "Location unavailable" when location is null',
        (tester) async {
      service.addInspection(
        historyDummyResult,
        originalImagePath: '/img.jpg',
        location: null,
      );

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();

      expect(find.text('Location unavailable'), findsOneWidget);
    });

    testWidgets(
        '"Location unavailable" row is NOT tappable (dialog does not open)',
        (tester) async {
      service.addInspection(
        historyDummyResult,
        originalImagePath: '/img.jpg',
        location: null,
      );

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();

      await tester.tap(find.text('Location unavailable'));
      await tester.pump();

      // No dialog should appear
      expect(find.text('Inspection Location'), findsNothing);
    });

    testWidgets(
        'tapping "Location captured" opens the location detail dialog',
        (tester) async {
      service.addInspection(
        historyDummyResult,
        originalImagePath: '/img.jpg',
        location: const InspectionLocation(
            latitude: 12.9716, longitude: 77.5946, accuracy: 8.0),
      );

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();

      await tester.tap(find.text('Location captured'));
      await tester.pumpAndSettle();

      expect(find.text('Inspection Location'), findsOneWidget);
    });

    testWidgets('location detail dialog shows latitude', (tester) async {
      service.addInspection(
        historyDummyResult,
        originalImagePath: '/img.jpg',
        location: const InspectionLocation(
            latitude: 12.9716, longitude: 77.5946),
      );

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();
      await tester.tap(find.text('Location captured'));
      await tester.pumpAndSettle();

      expect(find.text('Latitude'), findsOneWidget);
      expect(find.text('12.971600'), findsOneWidget);
    });

    testWidgets('location detail dialog shows longitude', (tester) async {
      service.addInspection(
        historyDummyResult,
        originalImagePath: '/img.jpg',
        location: const InspectionLocation(
            latitude: 12.9716, longitude: 77.5946),
      );

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();
      await tester.tap(find.text('Location captured'));
      await tester.pumpAndSettle();

      expect(find.text('Longitude'), findsOneWidget);
      expect(find.text('77.594600'), findsOneWidget);
    });

    testWidgets('accuracy row is shown when accuracy is non-null',
        (tester) async {
      service.addInspection(
        historyDummyResult,
        originalImagePath: '/img.jpg',
        location: const InspectionLocation(
            latitude: 12.9716, longitude: 77.5946, accuracy: 15.0),
      );

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();
      await tester.tap(find.text('Location captured'));
      await tester.pumpAndSettle();

      expect(find.text('Accuracy'), findsOneWidget);
      expect(find.text('±15 m'), findsOneWidget);
    });

    testWidgets('accuracy row is omitted when accuracy is null',
        (tester) async {
      service.addInspection(
        historyDummyResult,
        originalImagePath: '/img.jpg',
        location: const InspectionLocation(
            latitude: 12.9716, longitude: 77.5946),
      );

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();
      await tester.tap(find.text('Location captured'));
      await tester.pumpAndSettle();

      expect(find.text('Accuracy'), findsNothing);
    });

    testWidgets('Close button dismisses the location detail dialog',
        (tester) async {
      service.addInspection(
        historyDummyResult,
        originalImagePath: '/img.jpg',
        location: const InspectionLocation(
            latitude: 12.9716, longitude: 77.5946),
      );

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();
      await tester.tap(find.text('Location captured'));
      await tester.pumpAndSettle();

      expect(find.text('Inspection Location'), findsOneWidget);

      await tester.tap(find.text('Close'));
      await tester.pumpAndSettle();

      expect(find.text('Inspection Location'), findsNothing);
    });
  });

  group('HistoryPage — existing behavior unchanged', () {
    final service = InspectionHistoryService.instance;

    setUp(() => service.clearHistory());

    testWidgets('empty state shows "No inspections yet"', (tester) async {
      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();

      expect(find.text('No inspections yet'), findsOneWidget);
      expect(
          find.text('Run your first road inspection to see it here.'),
          findsOneWidget);
    });

    testWidgets('delete all button appears when history is non-empty',
        (tester) async {
      service.addInspection(
        historyDummyResult,
        originalImagePath: '/img.jpg',
      );

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();

      expect(find.byIcon(Icons.delete_outline), findsOneWidget);
    });

    testWidgets('delete all clears history and shows empty state',
        (tester) async {
      service.addInspection(
        historyDummyResult,
        originalImagePath: '/img.jpg',
      );

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();

      await tester.tap(find.byIcon(Icons.delete_outline));
      await tester.pumpAndSettle();

      // Confirm dialog
      await tester.tap(find.text('Delete All'));
      await tester.pumpAndSettle();

      expect(find.text('No inspections yet'), findsOneWidget);
    });

    testWidgets('tapping a history card navigates to ResultPage',
        (tester) async {
      // Use a local (non-http) path so the thumbnail widget does not
      // attempt a real network request in the test environment.
      final localResult = PredictionResponseModel(
        status: 'success',
        runId: 'run_nav_test',
        annotatedImage: '/tmp/annotated.jpg',   // local path → no network call
        detectionsFile: '/tmp/d.json',
        summaryFile: '/tmp/s.txt',
        detections: const [],
        totalDetections: 0,
      );
      service.addInspection(localResult, originalImagePath: '/img.jpg');

      await tester.pumpWidget(buildHistoryPage());
      await tester.pump();

      await tester.tap(find.text('run_nav_test'));
      await tester.pumpAndSettle();

      expect(find.text('ResultPage'), findsOneWidget);
    });
  });
}

// Test helper — mirrors the static method on RiskAssessmentCard without
// importing the widget (avoids needing a full Flutter environment).
String _formatClassName(String raw) => raw
    .split('_')
    .map((w) => w.isEmpty ? '' : '${w[0].toUpperCase()}${w.substring(1)}')
    .join(' ');
