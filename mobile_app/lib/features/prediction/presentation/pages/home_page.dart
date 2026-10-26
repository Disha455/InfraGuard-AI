import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/services/api_service.dart';
import '../../../../core/services/image_picker_service.dart';
import '../../../../core/services/inspection_history_service.dart';
import '../../../../core/services/location_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/image_validator.dart';
import '../../../../core/widgets/server_config_dialog.dart';
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
        action: isError
            ? SnackBarAction(
                label: 'Server IP',
                textColor: Colors.white,
                onPressed: () => ServerConfigDialog.show(context),
              )
            : null,
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
          ? 'Camera permission denied. Please enable it in device settings.'
          : 'Camera unavailable: ${e.message ?? e.code}';
      _showSnackBar(message, isError: true);
    }
  }

  // ---------------------------------------------------------------------------
  // Prediction upload
  // ---------------------------------------------------------------------------

  Future<void> _onAnalyzeImage() async {
    if (_selectedImage == null) {
      _showSnackBar('Please select an image first.', isError: true);
      return;
    }

    setState(() => _isLoading = true);

    try {
      final location = await _locationService.getCurrentLocation();
      final PredictionResponseModel result = await _apiService.uploadImage(
        _selectedImage!,
        latitude: location?.latitude,
        longitude: location?.longitude,
      );

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
      _showSnackBar('Network error: $e', isError: true);
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
        title: const Text('InfraGuard AI'),
        actions: [
          IconButton(
            icon: const Icon(Icons.wifi_rounded),
            tooltip: 'Server Connection IP',
            onPressed: () => ServerConfigDialog.show(context),
          ),
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
                      constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
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
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 520),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // ── Central Viewfinder Card ───────────────────────────
                      Card(
                        elevation: 1,
                        margin: EdgeInsets.zero,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                          side: const BorderSide(color: AppColors.outlineVariant),
                        ),
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
                                        height: 230,
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
                                          child: const Icon(Icons.close, size: 16, color: Colors.white),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ] else ...[
                                // Clean Viewfinder Frame
                                Container(
                                  width: double.infinity,
                                  height: 190,
                                  decoration: BoxDecoration(
                                    color: AppColors.surfaceVariant.withValues(alpha: 0.5),
                                    borderRadius: BorderRadius.circular(14),
                                    border: Border.all(color: AppColors.outlineVariant),
                                  ),
                                  child: Stack(
                                    alignment: Alignment.center,
                                    children: [
                                      Positioned(top: 10, left: 10, child: _corner(top: true, left: true)),
                                      Positioned(top: 10, right: 10, child: _corner(top: true, left: false)),
                                      Positioned(bottom: 10, left: 10, child: _corner(top: false, left: true)),
                                      Positioned(bottom: 10, right: 10, child: _corner(top: false, left: false)),
                                      Column(
                                        mainAxisAlignment: MainAxisAlignment.center,
                                        children: [
                                          Container(
                                            width: 54,
                                            height: 54,
                                            decoration: BoxDecoration(
                                              color: AppColors.primaryContainer,
                                              borderRadius: BorderRadius.circular(14),
                                            ),
                                            child: const Icon(
                                              Icons.camera_alt_outlined,
                                              size: 30,
                                              color: AppColors.primary,
                                            ),
                                          ),
                                          const SizedBox(height: 12),
                                          Text(
                                            'Road Damage Detection',
                                            style: textTheme.titleMedium?.copyWith(
                                              fontWeight: FontWeight.bold,
                                              color: AppColors.textPrimary,
                                            ),
                                          ),
                                          const SizedBox(height: 4),
                                          Text(
                                            'Point camera at pavement distress',
                                            style: textTheme.bodySmall?.copyWith(
                                              color: AppColors.textSecondary,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ],

                              const SizedBox(height: 18),

                              // ── Dual Source Buttons (Gallery & Camera) ───
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

                      const SizedBox(height: 18),

                      // ── Analyze Action Button ────────────────────────────
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primary,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 15),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        onPressed: _isLoading ? null : _onAnalyzeImage,
                        child: const Text(
                          'Analyze Image',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),

                      const SizedBox(height: 10),

                      // GPS status caption
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
                    ],
                  ),
                ),
              ),
            ),
          ),

          // ── Loading overlay ──────────────────────────────────────────────
          if (_isLoading)
            Container(
              color: Colors.black.withValues(alpha: 0.55),
              child: Center(
                child: Card(
                  color: AppColors.surface,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 22),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const CircularProgressIndicator(color: AppColors.primary),
                        const SizedBox(height: 18),
                        Text(
                          'Processing Road Inspection...',
                          style: textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  static Widget _corner({required bool top, required bool left}) {
    return Container(
      width: 14,
      height: 14,
      decoration: BoxDecoration(
        border: Border(
          top: top ? const BorderSide(color: AppColors.primary, width: 2.0) : BorderSide.none,
          bottom: !top ? const BorderSide(color: AppColors.primary, width: 2.0) : BorderSide.none,
          left: left ? const BorderSide(color: AppColors.primary, width: 2.0) : BorderSide.none,
          right: !left ? const BorderSide(color: AppColors.primary, width: 2.0) : BorderSide.none,
        ),
      ),
    );
  }
}
