import 'package:flutter/material.dart';
import '../features/prediction/data/models/prediction_response_model.dart';
import '../features/prediction/presentation/pages/history_page.dart';
import '../features/prediction/presentation/pages/home_page.dart';
import '../features/prediction/presentation/pages/result_page.dart';

class AppRouter {
  static const String home = '/';
  static const String result = '/result';
  static const String history = '/history';

  static Route<dynamic> onGenerateRoute(RouteSettings settings) {
    switch (settings.name) {
      case home:
        return MaterialPageRoute(
          builder: (_) => const HomePage(),
          settings: settings,
        );

      case result:
        final predictionResult =
            settings.arguments as PredictionResponseModel;
        return MaterialPageRoute(
          builder: (_) => ResultPage(result: predictionResult),
          settings: settings,
        );

      case history:
        return MaterialPageRoute(
          builder: (_) => const HistoryPage(),
          settings: settings,
        );

      default:
        return MaterialPageRoute(
          builder: (_) => const HomePage(),
          settings: settings,
        );
    }
  }
}
