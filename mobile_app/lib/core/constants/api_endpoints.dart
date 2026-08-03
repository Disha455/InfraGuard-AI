// InfraGuard AI — FastAPI endpoint definitions.
//
// All paths that the app calls on the backend are declared here so that
// a base-URL or versioning change requires editing only this file.

abstract final class ApiEndpoints {
  /// Base URL of the FastAPI inference server.
  ///
  /// Change this to your machine's LAN IP when running on a physical
  /// device, or to the deployed server URL in production.
  /// 10.0.2.2 is the Android emulator alias for the host's localhost.
  static const String baseUrl = 'http://192.168.29.107:8000';

  /// POST — accepts multipart/form-data with field "file".
  /// Returns a PredictionResponse JSON object.
  static const String predict = '/predict';
}
