# core/services

Application-level services that are not tied to a single feature.

Planned implementations:
- `api_service.dart`     — low-level HTTP client wrapper (multipart upload,
                           JSON decode, timeout handling)
- `storage_service.dart` — local file / cache management for prediction
                           run artefacts
