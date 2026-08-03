import 'dart:io';
import 'dart:ui' as ui;

/// Validates a [File] before it is used for inference.
///
/// Call [validate] for the full pipeline. Individual checks are also
/// exposed so callers can run them independently if needed.
class ImageValidator {
  static const int _bytesPerMB = 1024 * 1024;

  static const Set<String> _supportedExtensions = {
    'jpg',
    'jpeg',
    'png',
    'bmp',
    'webp',
    'tif',
    'tiff',
  };

  /// Returns `true` when [file] has a supported image extension.
  ///
  /// The check is case-insensitive and inspects only the path suffix.
  bool isSupportedExtension(File file) {
    final ext = file.path.split('.').last.toLowerCase();
    return _supportedExtensions.contains(ext);
  }

  /// Returns `true` when [file] is at most [maxSizeMB] megabytes.
  bool isFileSizeAllowed(File file, {int maxSizeMB = 10}) {
    final bytes = file.lengthSync();
    return bytes <= maxSizeMB * _bytesPerMB;
  }

  /// Returns `true` when Flutter's image engine can decode [file].
  ///
  /// Reads the raw bytes and calls [ui.instantiateImageCodec]. Returns
  /// `false` when decoding fails (corrupted data, unsupported encoding).
  Future<bool> canDecode(File file) async {
    try {
      final bytes = await file.readAsBytes();
      final codec = await ui.instantiateImageCodec(bytes);
      await codec.getNextFrame();
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Runs all validation checks in order.
  ///
  /// Returns `null` when the file is valid, or an error message string
  /// describing the first failed check.
  ///
  /// Validation order:
  ///   1. File exists on disk.
  ///   2. Extension is supported (jpg/jpeg/png/bmp/webp/tif/tiff).
  ///   3. File size ≤ [maxSizeMB] MB (default 10).
  ///   4. Flutter can decode the image data.
  Future<String?> validate(File file, {int maxSizeMB = 10}) async {
    if (!file.existsSync()) {
      return 'File not found. Please select an image again.';
    }

    if (!isSupportedExtension(file)) {
      final ext = file.path.split('.').last.toLowerCase();
      return 'Unsupported file type ".$ext". '
          'Please choose a JPG, PNG, BMP, WebP, or TIFF image.';
    }

    if (!isFileSizeAllowed(file, maxSizeMB: maxSizeMB)) {
      final sizeMB = (file.lengthSync() / _bytesPerMB).toStringAsFixed(1);
      return 'Image is too large (${sizeMB}MB). '
          'Maximum allowed size is ${maxSizeMB}MB.';
    }

    if (!await canDecode(file)) {
      return 'Image could not be read. '
          'The file may be corrupted or in an unsupported format.';
    }

    return null;
  }
}
