import 'package:flutter/material.dart';
import 'core/theme/app_theme.dart';

void main() {
  runApp(const InfraGuardApp());
}

class InfraGuardApp extends StatelessWidget {
  const InfraGuardApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'InfraGuard AI',
      theme: AppTheme.lightTheme,
      home: Scaffold(
        appBar: AppBar(
          title: const Text('InfraGuard AI'),
        ),
        body: const Center(
          child: Text('Mobile App Setup Complete'),
        ),
      ),
    );
  }
}
