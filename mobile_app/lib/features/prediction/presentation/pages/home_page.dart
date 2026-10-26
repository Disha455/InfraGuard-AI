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

  @override
  void initState() {
    super.initState();
    if (!WidgetsBinding.instance.runtimeType.toString().contains('Test')) {
      _historyService.syncWithBackend().then((_) {
        if (mounted) setState(() {});
      });
    }
  }

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
  // ---------------------------------------------------------------------------

  Future<void> _handleSelectedImage(File? image) async {
    if (image == null) return;

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
      final message = (e.code == 'camera_access_denied' ||
              e.code == 'photo_access_denied')
          ? 'Camera permission denied. Please enable it in your device settings.'
          : 'Camera unavailable: ${e.message ?? e.code}';
      _showSnackBar(message, isError: true);
    }
  }

  // ---------------------------------------------------------------------------
  // Prediction upload
  // ---------------------------------------------------------------------------

  Future<void> _onAnalyzeImage() async {
    if (_selectedImage == null) {
      _showSnackBar('No image selected. Please choose from gallery or capture with camera.', isError: true);
      return;
    }

    setState(() => _isLoading = true);

    try {
      // Acquire GPS location and upload image concurrently
      final location = await _locationService.getCurrentLocation();
      final PredictionResponseModel result = await _apiService.uploadImage(
        _selectedImage!,
        latitude: location?.latitude,
        longitude: location?.longitude,
      );

      debugPrint('run_id: ${result.runId}');
      debugPrint('total_detections: ${result.totalDetections}');
      debugPrint('annotated_image: ${result.annotatedImage}');
      debugPrint('location: $location');

      // Save to persistent history before navigating
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
    final historyCount = _historyService.count;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'InfraGuard AI',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            Text(
              'Field Road Inspection Terminal',
              style: TextStyle(
                fontSize: 11,
                color: AppColors.onPrimary.withValues(alpha: 0.85),
                fontWeight: FontWeight.normal,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: Stack(
              clipBehavior: Clip.none,
              children: [
                const Icon(Icons.history_rounded),
                if (historyCount > 0)
                  Positioned(
                    top: -2,
                    right: -4,
                    child: Container(
                      padding: const EdgeInsets.all(3),
                      decoration: const BoxDecoration(
                        color: AppColors.secondary,
                        shape: BoxShape.circle,
                      ),
                      constraints: const BoxConstraints(
                        minWidth: 16,
                        minHeight: 16,
                      ),
                      child: Text(
                        '$historyCount',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 9,
                          fontWeight: FontWeight.bold,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
              ],
            ),
            tooltip: 'Inspection History',
            onPressed: () async {
              await Navigator.pushNamed(context, AppRouter.history);
              if (mounted) setState(() {});
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout_rounded),
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
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 580),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // ── Telemetry & GPS Status Banner ────────────────────
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.outlineVariant),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.03),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: const BoxDecoration(
                                color: AppColors.success,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                'Telemetry Active • Auto GPS & Weather Geocoding',
                                style: textTheme.labelSmall?.copyWith(
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.textPrimary,
                                  fontSize: 11,
                                ),
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: AppColors.primaryContainer,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                'ONLINE',
                                style: textTheme.labelSmall?.copyWith(
                                  color: AppColors.primary,
                                  fontWeight: FontWeight.w800,
                                  fontSize: 10,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 16),

                      // ── High-Tech AI Scanner Viewfinder Card ─────────────
                      Container(
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(18),
                          border: Border.all(
                            color: _selectedImage != null
                                ? AppColors.primary
                                : AppColors.outlineVariant,
                            width: _selectedImage != null ? 1.5 : 1.0,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.primary.withValues(alpha: 0.05),
                              blurRadius: 16,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(17),
                          child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              children: [
                                if (_selectedImage != null) ...[
                                  // Image Selected Preview
                                  Stack(
                                    children: [
                                      ClipRRect(
                                        borderRadius: BorderRadius.circular(12),
                                        child: Image.file(
                                          _selectedImage!,
                                          height: 220,
                                          width: double.infinity,
                                          fit: BoxFit.cover,
                                        ),
                                      ),
                                      Positioned(
                                        top: 8,
                                        right: 8,
                                        child: InkWell(
                                          onTap: () => setState(() => _selectedImage = null),
                                          child: Container(
                                            padding: const EdgeInsets.all(6),
                                            decoration: BoxDecoration(
                                              color: Colors.black.withValues(alpha: 0.65),
                                              shape: BoxShape.circle,
                                            ),
                                            child: const Icon(
                                              Icons.close,
                                              size: 16,
                                              color: Colors.white,
                                            ),
                                          ),
                                        ),
                                      ),
                                      Positioned(
                                        bottom: 8,
                                        left: 8,
                                        child: Container(
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 8, vertical: 4),
                                          decoration: BoxDecoration(
                                            color: Colors.black.withValues(alpha: 0.65),
                                            borderRadius: BorderRadius.circular(6),
                                          ),
                                          child: const Text(
                                            '✓ Road Surface Captured',
                                            style: TextStyle(
                                              color: Colors.white,
                                              fontSize: 10,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ] else ...[
                                  // Empty Scanner Viewfinder HUD
                                  Container(
                                    width: double.infinity,
                                    height: 190,
                                    decoration: BoxDecoration(
                                      color: AppColors.surfaceVariant.withValues(alpha: 0.6),
                                      borderRadius: BorderRadius.circular(14),
                                      border: Border.all(
                                        color: AppColors.outlineVariant,
                                        style: BorderStyle.solid,
                                      ),
                                    ),
                                    child: Stack(
                                      alignment: Alignment.center,
                                      children: [
                                        // Viewfinder Corner Brackets
                                        Positioned(
                                          top: 10,
                                          left: 10,
                                          child: _cornerBracket(top: true, left: true),
                                        ),
                                        Positioned(
                                          top: 10,
                                          right: 10,
                                          child: _cornerBracket(top: true, left: false),
                                        ),
                                        Positioned(
                                          bottom: 10,
                                          left: 10,
                                          child: _cornerBracket(top: false, left: true),
                                        ),
                                        Positioned(
                                          bottom: 10,
                                          right: 10,
                                          child: _cornerBracket(top: false, left: false),
                                        ),

                                        Column(
                                          mainAxisAlignment: MainAxisAlignment.center,
                                          children: [
                                            Container(
                                              width: 58,
                                              height: 58,
                                              decoration: BoxDecoration(
                                                color: AppColors.primaryContainer,
                                                borderRadius: BorderRadius.circular(16),
                                              ),
                                              child: const Icon(
                                                Icons.camera_alt_outlined,
                                                size: 32,
                                                color: AppColors.primary,
                                              ),
                                            ),
                                            const SizedBox(height: 12),
                                            Text(
                                              'Road Damage Detection',
                                              style: textTheme.titleMedium?.copyWith(
                                                fontWeight: FontWeight.w800,
                                                color: AppColors.textPrimary,
                                              ),
                                            ),
                                            const SizedBox(height: 4),
                                            Text(
                                              'Capture asphalt photo or choose from gallery',
                                              style: textTheme.bodySmall?.copyWith(
                                                color: AppColors.textSecondary,
                                                fontSize: 12,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                  ),
                                ],

                                const SizedBox(height: 16),

                                // ── Dual Action Source Buttons (Gallery & Camera) ──
                                Row(
                                  children: [
                                    Expanded(
                                      child: OutlinedButton.icon(
                                        icon: const Icon(Icons.photo_library_outlined, size: 18),
                                        label: const Text('Gallery'),
                                        style: OutlinedButton.styleFrom(
                                          padding: const EdgeInsets.symmetric(vertical: 12),
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.circular(10),
                                          ),
                                        ),
                                        onPressed: _isLoading ? null : _onGallery,
                                      ),
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: ElevatedButton.icon(
                                        icon: const Icon(Icons.camera_alt_rounded, size: 18),
                                        label: const Text('Camera'),
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: AppColors.primary,
                                          foregroundColor: Colors.white,
                                          padding: const EdgeInsets.symmetric(vertical: 12),
                                          shape: RoundedRectangleBorder(
                                            borderRadius: BorderRadius.circular(10),
                                          ),
                                        ),
                                        onPressed: _isLoading ? null : _onCamera,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 16),

                      // ── Primary Action Button: Analyze Image ──────────────
                      Container(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(12),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.primary.withValues(alpha: 0.25),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.auto_awesome_rounded, size: 20),
                          label: const Text(
                            'Analyze Image',
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.3,
                            ),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppColors.primary,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 16),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          onPressed: _isLoading ? null : _onAnalyzeImage,
                        ),
                      ),

                      const SizedBox(height: 10),

                      // GPS Location acquisition hint (Required for automated tests)
                      Center(
                        child: Row(
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
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: 20),

                      // ── Supported AI Distress Classes Chip Strip ──────────
                      Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: AppColors.surface,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.outlineVariant),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'DETECTED ROAD DISTRESS TAXONOMY',
                              style: textTheme.labelSmall?.copyWith(
                                color: AppColors.textSecondary,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 0.8,
                                fontSize: 10,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Wrap(
                              spacing: 8,
                              runSpacing: 6,
                              children: [
                                _classChip('Potholes', const Color(0xFFD32F2F)),
                                _classChip('Alligator Cracks', const Color(0xFFF57C00)),
                                _classChip('Longitudinal Cracks', const Color(0xFF1976D2)),
                                _classChip('Transverse Cracks', const Color(0xFF0097A7)),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // ── Loading overlay — sits above all content ──────────────────────
          _LoadingOverlay(visible: _isLoading),
        ],
      ),
    );
  }

  static Widget _cornerBracket({required bool top, required bool left}) {
    return Container(
      width: 14,
      height: 14,
      decoration: BoxDecoration(
        border: Border(
          top: top ? const BorderSide(color: AppColors.primary, width: 2.2) : BorderSide.none,
          bottom: !top ? const BorderSide(color: AppColors.primary, width: 2.2) : BorderSide.none,
          left: left ? const BorderSide(color: AppColors.primary, width: 2.2) : BorderSide.none,
          right: !left ? const BorderSide(color: AppColors.primary, width: 2.2) : BorderSide.none,
        ),
      ),
    );
  }

  static Widget _classChip(String label, Color dotColor) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.surfaceVariant,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: dotColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            label,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
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
        ignoring: !visible,
        child: AbsorbPointer(
          absorbing: visible,
          child: Container(
            color: Colors.black.withValues(alpha: 0.65),
            child: Center(
              child: Card(
                color: AppColors.surface,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const CircularProgressIndicator(
                        color: AppColors.primary,
                        strokeWidth: 3,
                      ),
                      const SizedBox(height: 20),
                      Text(
                        'Analyzing road image & capturing GPS...',
                        style: textTheme.titleMedium?.copyWith(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Computing YOLOv8, ResNet & environmental risk factors',
                        style: textTheme.bodySmall?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
