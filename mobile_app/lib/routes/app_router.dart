import 'package:flutter/material.dart';
import '../features/admin/presentation/pages/admin_dashboard_page.dart';
import '../features/auth/presentation/pages/admin_login_page.dart';
import '../features/auth/presentation/pages/inspector_login_page.dart';
import '../features/auth/presentation/pages/welcome_page.dart';
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
  static const String welcome = '/';
  static const String inspectorLogin = '/inspector-login';
  static const String adminLogin = '/admin-login';
  static const String home = '/home';
  static const String adminDashboard = '/admin-dashboard';
  static const String result = '/result';
  static const String history = '/history';

  static Route<dynamic> onGenerateRoute(RouteSettings settings) {
    switch (settings.name) {
      case welcome:
        return MaterialPageRoute(
          builder: (_) => const WelcomePage(),
          settings: settings,
        );

      case inspectorLogin:
        return MaterialPageRoute(
          builder: (_) => const InspectorLoginPage(),
          settings: settings,
        );

      case adminLogin:
        return MaterialPageRoute(
          builder: (_) => const AdminLoginPage(),
          settings: settings,
        );

      case home:
        return MaterialPageRoute(
          builder: (_) => const HomePage(),
          settings: settings,
        );

      case adminDashboard:
        return MaterialPageRoute(
          builder: (_) => const AdminDashboardPage(),
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
          builder: (_) => const WelcomePage(),
          settings: settings,
        );
    }
  }
}
