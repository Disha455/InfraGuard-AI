// InfraGuard AI — FastAPI endpoint definitions.
//
// All paths that the app calls on the backend are declared here so that
// a base-URL or versioning change requires editing only this file.

abstract final class ApiEndpoints {
  static String _baseUrl = 'http://192.168.29.107:8000';

  /// Base URL of the FastAPI inference server.
  static String get baseUrl => _baseUrl;

  /// Dynamically updates the base URL across the app session.
  static void setBaseUrl(String newUrl) {
    var trimmed = newUrl.trim();
    if (trimmed.endsWith('/')) {
      trimmed = trimmed.substring(0, trimmed.length - 1);
    }
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      trimmed = 'http://$trimmed';
    }
    _baseUrl = trimmed;
  }

  /// POST — accepts multipart/form-data with field "file".
  /// Returns a PredictionResponse JSON object.
  static const String predict = '/predict';

  /// GET — returns real-time admin analytics and inspection metrics.
  static const String adminAnalytics = '/admin/analytics';

  /// GET — returns all recorded historical inspections from the database.
  static const String adminInspections = '/admin/inspections';
}