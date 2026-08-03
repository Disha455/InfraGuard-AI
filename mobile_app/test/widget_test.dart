import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/main.dart';

void main() {
  testWidgets('Home page renders correctly', (WidgetTester tester) async {
    await tester.pumpWidget(const InfraGuardApp());

    expect(find.text('InfraGuard AI'), findsOneWidget);
    expect(find.text('Road Damage Detection'), findsOneWidget);
    expect(find.text('Select Image'), findsOneWidget);
  });
}
