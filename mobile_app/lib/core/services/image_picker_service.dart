import 'dart:io';
import 'package:image_picker/image_picker.dart';

/// Wraps [ImagePicker] and exposes a single gallery-pick operation.
///
/// Returns `null` when the user cancels without selecting an image.
/// Callers receive a plain [File] so no image_picker types leak outside
/// this service.
class ImagePickerService {
  final ImagePicker _picker = ImagePicker();

  /// Opens the device gallery and returns the selected image as a [File].
  ///
  /// Returns `null` if the user cancels the picker.
  Future<File?> pickImageFromGallery() async {
    final XFile? picked = await _picker.pickImage(
      source: ImageSource.gallery,
    );

    if (picked == null) return null;
    return File(picked.path);
  }
}
