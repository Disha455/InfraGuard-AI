import 'dart:io';
import 'package:flutter/material.dart';
import '../../../../core/services/api_service.dart';
import '../../../../core/services/image_picker_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/image_validator.dart';
import '../../../prediction/data/models/prediction_response_model.dart';
import '../../../../routes/app_router.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final ImagePickerService _imagePickerService = ImagePickerService();
  final ImageValidator _imageValidator = ImageValidator();
  final ApiService _apiService = ApiService();

  File? _selectedImage;
  bool _isLoading = false;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  void _showSnackBar(String message, {bool isError = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
        backgroundColor: isError
            ? Theme.of(context).colorScheme.error
            : Theme.of(context).colorScheme.primary,
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Image selection
  // ---------------------------------------------------------------------------

  Future<void> _onSelectImage() async {
    final File? picked = await _imagePickerService.pickImageFromGallery();
    if (picked == null) return;

    final String? error = await _imageValidator.validate(picked);
    if (error != null) {
      setState(() => _selectedImage = null);
      _showSnackBar(error, isError: true);
      return;
    }

    setState(() => _selectedImage = picked);
  }

  // ---------------------------------------------------------------------------
  // Prediction upload
  // ---------------------------------------------------------------------------

  Future<void> _onAnalyzeImage() async {
    if (_selectedImage == null) {
      _showSnackBar('No image selected.', isError: true);
      return;
    }

    setState(() => _isLoading = true);

    try {
      final PredictionResponseModel result =
          await _apiService.uploadImage(_selectedImage!);

      debugPrint('run_id: ${result.runId}');
      debugPrint('total_detections: ${result.totalDetections}');
      debugPrint('annotated_image: ${result.annotatedImage}');

      if (mounted) {
        Navigator.pushNamed(
          context,
          AppRouter.result,
          arguments: result,
        );
      }
    } on ApiException catch (e) {
      _showSnackBar(e.message, isError: true);
    } catch (e) {
      _showSnackBar('Unexpected error: $e', isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('InfraGuard AI'),
      ),
      body: Stack(
        children: [
          // ── Main content ──────────────────────────────────────────────────
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Image preview or placeholder icon
                if (_selectedImage != null)
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxHeight: 220),
                    child: Image.file(
                      _selectedImage!,
                      fit: BoxFit.contain,
                    ),
                  )
                else
                  Icon(
                    Icons.camera_alt_outlined,
                    size: 80,
                    color: Theme.of(context).colorScheme.primary,
                  ),

                const SizedBox(height: 24),

                Text(
                  'Road Damage Detection',
                  style: textTheme.titleLarge,
                ),

                const SizedBox(height: 16),

                ElevatedButton(
                  onPressed: _isLoading ? null : _onSelectImage,
                  child: const Text('Select Image'),
                ),

                const SizedBox(height: 12),

                ElevatedButton(
                  onPressed: _isLoading ? null : _onAnalyzeImage,
                  child: const Text('Analyze Image'),
                ),
              ],
            ),
          ),

          // ── Loading overlay — sits above all content ──────────────────────
          _LoadingOverlay(visible: _isLoading),
        ],
      ),
    );
  }
}

// ── _LoadingOverlay ───────────────────────────────────────────────────────────

class _LoadingOverlay extends StatelessWidget {
  final bool visible;

  const _LoadingOverlay({required this.visible});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return AnimatedOpacity(
      opacity: visible ? 1.0 : 0.0,
      duration: const Duration(milliseconds: 250),
      child: IgnorePointer(
        // Pass touches through to content beneath when not visible
        ignoring: !visible,
        child: AbsorbPointer(
          // Block all touches when visible
          absorbing: visible,
          child: Container(
            color: Colors.black54,
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(
                    color: AppColors.onPrimary,
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Analyzing road image...',
                    style: textTheme.titleMedium?.copyWith(
                      color: AppColors.onPrimary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'This usually takes a few seconds',
                    style: textTheme.bodySmall?.copyWith(
                      color: AppColors.onPrimary.withValues(alpha: 0.8),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
