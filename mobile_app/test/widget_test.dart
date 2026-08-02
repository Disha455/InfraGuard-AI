import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/main.dart';

void main() {
  testWidgets('InfraGuard AI app renders setup screen', (WidgetTester tester) async {
    await tester.pumpWidget(const InfraGuardApp());

    expect(find.text('InfraGuard AI'), findsOneWidget);
    expect(find.text('Mobile App Setup Complete'), findsOneWidget);
  });
}
