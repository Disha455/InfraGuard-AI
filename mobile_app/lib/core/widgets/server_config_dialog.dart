import 'package:flutter/material.dart';
import '../constants/api_endpoints.dart';
import '../services/api_service.dart';
import '../theme/app_colors.dart';

class ServerConfigDialog extends StatefulWidget {
  final VoidCallback? onSaved;

  const ServerConfigDialog({super.key, this.onSaved});

  static Future<void> show(BuildContext context, {VoidCallback? onSaved}) {
    return showDialog(
      context: context,
      builder: (ctx) => ServerConfigDialog(onSaved: onSaved),
    );
  }

  @override
  State<ServerConfigDialog> createState() => _ServerConfigDialogState();
}

class _ServerConfigDialogState extends State<ServerConfigDialog> {
  late final TextEditingController _controller;
  final ApiService _apiService = ApiService();
  bool _isTesting = false;
  bool? _testResult;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: ApiEndpoints.baseUrl);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    setState(() {
      _isTesting = true;
      _testResult = null;
    });

    final target = _controller.text.trim();
    final ok = await _apiService.testConnection(targetUrl: target);

    if (!mounted) return;
    setState(() {
      _isTesting = false;
      _testResult = ok;
    });
  }

  void _save() {
    final target = _controller.text.trim();
    if (target.isNotEmpty) {
      _apiService.updateBaseUrl(target);
      widget.onSaved?.call();
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Server address updated to: ${ApiEndpoints.baseUrl}'),
          backgroundColor: AppColors.primary,
          duration: const Duration(seconds: 2),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppColors.primaryContainer,
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.wifi_rounded, size: 20, color: AppColors.primary),
          ),
          const SizedBox(width: 12),
          Text(
            'Server Connection IP',
            style: textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
          ),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Configure your laptop LAN IP or Cloud URL. Allows normal wireless operation without USB cables.',
            style: textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _controller,
            decoration: InputDecoration(
              labelText: 'Backend Base URL',
              hintText: 'http://192.168.xx.xx:8000',
              prefixIcon: const Icon(Icons.dns_outlined, size: 20),
              filled: true,
              fillColor: AppColors.surfaceVariant,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(10),
                borderSide: const BorderSide(color: AppColors.outlineVariant),
              ),
            ),
            keyboardType: TextInputType.url,
          ),
          const SizedBox(height: 12),
          if (_testResult != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: _testResult! ? AppColors.successContainer : AppColors.errorContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(
                    _testResult! ? Icons.check_circle : Icons.error_outline,
                    size: 16,
                    color: _testResult! ? AppColors.success : AppColors.error,
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      _testResult!
                          ? 'Server connected successfully!'
                          : 'Cannot reach server. Verify IP and backend port.',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: _testResult! ? AppColors.success : AppColors.error,
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: _isTesting ? null : _testConnection,
          child: _isTesting
              ? const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Test Connection'),
        ),
        ElevatedButton(
          onPressed: _save,
          child: const Text('Save & Apply'),
        ),
      ],
    );
  }
}
