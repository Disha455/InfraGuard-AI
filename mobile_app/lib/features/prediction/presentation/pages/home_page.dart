import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/services/api_service.dart';
import '../../../../core/services/image_picker_service.dart';
import '../../../../core/services/inspection_history_service.dart';
import '../../../../core/services/location_service.dart';
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
  final InspectionHistoryService _historyService =
      InspectionHistoryService.instance;
  final LocationService _locationService = LocationService();

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
  // Shared image-selection pipeline
  //
  // Both Gallery and Camera call this after obtaining a File? from the picker.
  // Validation runs once here — no duplication between the two flows.
  // ---------------------------------------------------------------------------

  Future<void> _handleSelectedImage(File? image) async {
    if (image == null) return; // user cancelled — do nothing

    final String? error = await _imageValidator.validate(image);
    if (error != null) {
      setState(() => _selectedImage = null);
      _showSnackBar(error, isError: true);
      return;
    }

    setState(() => _selectedImage = image);
  }

  // ---------------------------------------------------------------------------
  // Image selection — Gallery
  // ---------------------------------------------------------------------------

  Future<void> _onGallery() async {
    final File? picked = await _imagePickerService.pickImageFromGallery();
    await _handleSelectedImage(picked);
  }

  // ---------------------------------------------------------------------------
  // Image selection — Camera
  // ---------------------------------------------------------------------------

  Future<void> _onCamera() async {
    try {
      final File? captured = await _imagePickerService.pickImageFromCamera();
      await _handleSelectedImage(captured);
    } on PlatformException catch (e) {
      // Covers camera_access_denied (iOS) and equivalent Android codes.
      final message = (e.code == 'camera_access_denied' ||
              e.code == 'photo_access_denied')
          ? 'Camera permission denied. '
              'Please enable it in your device settings.'
          : 'Camera unavailable: ${e.message ?? e.code}';
      _showSnackBar(message, isError: true);
    }
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
      // ── Start upload and GPS acquisition concurrently ─────────────────
      //
      // Both futures are launched here — immediately when Analyze Image is
      // tapped — so GPS acquisition never happens during image selection.
      //
      // Using explicit Future variables (rather than Future.wait) preserves
      // the full static types of each result without casting.  The loading
      // overlay stays active until BOTH operations complete.
      final uploadFuture   = _apiService.uploadImage(_selectedImage!);
      final locationFuture = _locationService.getCurrentLocation();

      final PredictionResponseModel result   = await uploadFuture;
      final location                          = await locationFuture;

      debugPrint('run_id: ${result.runId}');
      debugPrint('total_detections: ${result.totalDetections}');
      debugPrint('annotated_image: ${result.annotatedImage}');
      debugPrint('location: $location');

      // Save to in-memory history before navigating.
      // location may be null — that is expected and never blocks saving.
      _historyService.addInspection(
        result,
        originalImagePath: _selectedImage?.path ?? '',
        location: location,
      );

      if (mounted) {
        Navigator.pushNamed(
          context,
          AppRouter.result,
          arguments: ResultPageArgs(
            result: result,
            location: location,
          ),
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
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: 'Inspection History',
            onPressed: () => Navigator.pushNamed(context, AppRouter.history),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Log Out',
            onPressed: () => Navigator.pushNamedAndRemoveUntil(
              context,
              AppRouter.welcome,
              (_) => false,
            ),
          ),
        ],
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

                // ── Gallery / Camera buttons ──────────────────────────────
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 32),
                  child: Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.photo_library),
                          label: const Text('Gallery'),
                          onPressed: _isLoading ? null : _onGallery,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.camera_alt),
                          label: const Text('Camera'),
                          onPressed: _isLoading ? null : _onCamera,
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 12),

                ElevatedButton(
                  onPressed: _isLoading ? null : _onAnalyzeImage,
                  child: const Text('Analyze Image'),
                ),

                const SizedBox(height: 12),

                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(
                      Icons.location_on_outlined,
                      size: 14,
                      color: AppColors.textSecondary,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      'GPS location auto-acquired on analysis',
                      style: textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
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
                    'Analyzing road image & capturing GPS...',
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
