import 'dart:io';
import 'package:image_picker/image_picker.dart';

/// Wraps [ImagePicker] and exposes gallery-pick and camera-capture operations.
///
/// Returns `null` when the user cancels without selecting an image.
/// Callers receive a plain [File] so no image_picker types leak outside
/// this service.
class ImagePickerService {
  final ImagePicker _picker = ImagePicker();

  // ---------------------------------------------------------------------------
  // Private
  // ---------------------------------------------------------------------------

  /// Shared implementation — opens the picker with [source] and returns
  /// the result as a [File], or `null` if the user cancelled.
  ///
  /// Propagates any [PlatformException] (e.g. permission denied) to the
  /// caller so it can show a context-appropriate error message.
  Future<File?> _pickImage(ImageSource source) async {
    final XFile? picked = await _picker.pickImage(source: source);
    if (picked == null) return null;
    return File(picked.path);
  }

  // ---------------------------------------------------------------------------
  // Public
  // ---------------------------------------------------------------------------

  /// Opens the device gallery and returns the selected image as a [File].
  ///
  /// Returns `null` if the user cancels the picker.
  Future<File?> pickImageFromGallery() => _pickImage(ImageSource.gallery);

  /// Opens the device camera and returns the captured image as a [File].
  ///
  /// Returns `null` if the user cancels.
  /// Throws a [PlatformException] if camera permission is denied.
  Future<File?> pickImageFromCamera() => _pickImage(ImageSource.camera);
}
