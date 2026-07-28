import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/main.dart';

void main() {
  testWidgets('App shows auth gate', (WidgetTester tester) async {
    await tester.pumpWidget(const YatraSathiApp());
    await tester.pumpAndSettle();

    expect(find.text('Yatra Sathi'), findsWidgets);
    expect(find.text('Continue as Guest'), findsOneWidget);
  });
}
