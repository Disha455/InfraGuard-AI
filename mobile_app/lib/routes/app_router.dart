import 'package:flutter/material.dart';
import '../features/prediction/data/models/inspection_location.dart';
import '../features/prediction/data/models/prediction_response_model.dart';
import '../features/prediction/presentation/pages/history_page.dart';
import '../features/prediction/presentation/pages/home_page.dart';
import '../features/prediction/presentation/pages/result_page.dart';

/// Arguments bundle passed to [ResultPage].
class ResultPageArgs {
  final PredictionResponseModel result;
  final InspectionLocation? location;

  const ResultPageArgs({required this.result, this.location});
}

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
        if (settings.arguments is ResultPageArgs) {
          final args = settings.arguments as ResultPageArgs;
          return MaterialPageRoute(
            builder: (_) => ResultPage(
              result: args.result,
              location: args.location,
            ),
            settings: settings,
          );
        } else if (settings.arguments is PredictionResponseModel) {
          final predictionResult =
              settings.arguments as PredictionResponseModel;
          return MaterialPageRoute(
            builder: (_) => ResultPage(result: predictionResult),
            settings: settings,
          );
        }
        return MaterialPageRoute(
          builder: (_) => const HomePage(),
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
