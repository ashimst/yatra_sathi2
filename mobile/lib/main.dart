import 'package:flutter/material.dart';
import 'package:mobile/constants.dart';
import 'package:mobile/services/user_session.dart';
import 'package:mobile/screens/auth_gate.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await UserSession.loadFromStorage();
  runApp(const YatraSathiApp());
}

class YatraSathiApp extends StatelessWidget {
  const YatraSathiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Yatra Sathi',
      debugShowCheckedModeBanner: false,
      theme: yatraSathiTheme(),
      home: const AuthGate(),
    );
  }
}