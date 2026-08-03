import 'dart:io';
import 'package:dio/dio.dart';
import '../constants/api_endpoints.dart';
import '../../features/prediction/data/models/prediction_response_model.dart';

/// Thrown when the server returns a non-2xx status code.
class ApiException implements Exception {
  final int statusCode;
  final String message;

  const ApiException({required this.statusCode, required this.message});

  @override
  String toString() => 'ApiException($statusCode): $message';
}

/// Low-level HTTP client for the InfraGuard AI FastAPI backend.
///
/// Uses [Dio] for multipart uploads with timeout and error handling.
/// All methods return decoded JSON maps so the caller never depends on
/// Dio types directly.
class ApiService {
  late final Dio _dio;

  ApiService() {
    _dio = Dio(
      BaseOptions(
        baseUrl: ApiEndpoints.baseUrl,
        connectTimeout: const Duration(seconds: 30),
        receiveTimeout: const Duration(seconds: 60),
        headers: {'Accept': 'application/json'},
      ),
    );
  }

  /// Uploads [image] to [ApiEndpoints.predict] as a multipart request.
  ///
  /// The field name expected by the backend is `file`.
  ///
  /// Returns a parsed [PredictionResponseModel] on success.
  ///
  /// Throws:
  ///   - [ApiException] when the server returns a non-2xx status code.
  ///   - [ApiException] wrapping a connection or timeout error.
  Future<PredictionResponseModel> uploadImage(File image) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        image.path,
        filename: image.path.split(Platform.pathSeparator).last,
      ),
    });

    try {
      final response = await _dio.post<Map<String, dynamic>>(
        ApiEndpoints.predict,
        data: formData,
        options: Options(contentType: 'multipart/form-data'),
      );

      if (response.statusCode != null &&
          response.statusCode! >= 200 &&
          response.statusCode! < 300) {
        return PredictionResponseModel.fromJson(response.data ?? {});
      }

      throw ApiException(
        statusCode: response.statusCode ?? 0,
        message: 'Unexpected status ${response.statusCode}.',
      );
    } on DioException catch (e) {
      throw ApiException(
        statusCode: e.response?.statusCode ?? 0,
        message: _dioErrorMessage(e),
      );
    }
  }

  // Converts a [DioException] into a user-readable message.
  String _dioErrorMessage(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'Request timed out. Check your connection and try again.';
      case DioExceptionType.connectionError:
        return 'Could not reach the server. '
            'Make sure the backend is running on ${ApiEndpoints.baseUrl}.';
      case DioExceptionType.badResponse:
        final status = e.response?.statusCode ?? '?';
        final body = e.response?.data?.toString() ?? 'No response body.';
        return 'Server error $status: $body';
      default:
        return e.message ?? 'An unexpected network error occurred.';
    }
  }
}
