import 'dart:io';
import 'package:flutter/material.dart';
import '../../../../core/services/inspection_history_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../routes/app_router.dart';
import '../../data/models/inspection_history_item.dart';

// ── HistoryPage ───────────────────────────────────────────────────────────────

/// Displays all completed inspections stored in [InspectionHistoryService].
///
/// Uses [StatefulWidget] so [setState] can rebuild the list after
/// "Delete All" is confirmed.
class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  final InspectionHistoryService _service = InspectionHistoryService.instance;

  // ---------------------------------------------------------------------------
  // Delete-all confirmation dialog
  // ---------------------------------------------------------------------------

  Future<void> _onDeleteAll() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Clear History'),
        content: const Text(
          'This will permanently remove all inspection records '
          'from this session. This cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(
              foregroundColor: AppColors.error,
            ),
            child: const Text('Delete All'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      _service.clearHistory();
      setState(() {});
    }
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final items = _service.getHistory();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Inspection History'),
        actions: [
          if (items.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Delete All',
              onPressed: _onDeleteAll,
            ),
        ],
      ),
      body: items.isEmpty ? _EmptyState() : _HistoryList(items: items),
    );
  }
}

// ── _HistoryList ──────────────────────────────────────────────────────────────

class _HistoryList extends StatelessWidget {
  final List<InspectionHistoryItem> items;

  const _HistoryList({required this.items});

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: items.length,
      itemBuilder: (context, index) => _HistoryCard(item: items[index]),
    );
  }
}

// ── _HistoryCard ──────────────────────────────────────────────────────────────

class _HistoryCard extends StatelessWidget {
  final InspectionHistoryItem item;

  const _HistoryCard({required this.item});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.pushNamed(
          context,
          AppRouter.result,
          arguments: item.predictionResult,
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Thumbnail ───────────────────────────────────────────────
              _Thumbnail(path: item.annotatedImagePath),

              const SizedBox(width: 12),

              // ── Details ─────────────────────────────────────────────────
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Run ID
                    Text(
                      item.runId,
                      style: textTheme.titleSmall,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),

                    const SizedBox(height: 4),

                    // Date & time
                    _MetaRow(
                      icon: Icons.calendar_today_outlined,
                      label: _formatDate(item.inspectionDate),
                    ),

                    const SizedBox(height: 2),

                    // Status
                    _MetaRow(
                      icon: Icons.check_circle_outline,
                      label: item.status,
                    ),

                    const SizedBox(height: 2),

                    // Total detections
                    _MetaRow(
                      icon: Icons.analytics_outlined,
                      label: '${item.totalDetections} detection'
                          '${item.totalDetections == 1 ? '' : 's'}',
                    ),

                    const SizedBox(height: 6),

                    // First damage type badge
                    _DamageBadge(
                      label: item.firstDamageType ?? 'No Damage Detected',
                      hasDamage: item.firstDamageType != null,
                    ),
                  ],
                ),
              ),

              // ── Chevron ─────────────────────────────────────────────────
              const Icon(
                Icons.chevron_right,
                color: AppColors.textSecondary,
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatDate(DateTime dt) {
    final date =
        '${dt.day.toString().padLeft(2, '0')}/'
        '${dt.month.toString().padLeft(2, '0')}/'
        '${dt.year}';
    final time =
        '${dt.hour.toString().padLeft(2, '0')}:'
        '${dt.minute.toString().padLeft(2, '0')}';
    return '$date  $time';
  }
}

// ── _MetaRow ──────────────────────────────────────────────────────────────────

class _MetaRow extends StatelessWidget {
  final IconData icon;
  final String label;

  const _MetaRow({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Row(
      children: [
        Icon(icon, size: 13, color: AppColors.textSecondary),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            label,
            style: textTheme.bodySmall,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

// ── _DamageBadge ──────────────────────────────────────────────────────────────

class _DamageBadge extends StatelessWidget {
  final String label;
  final bool hasDamage;

  const _DamageBadge({required this.label, required this.hasDamage});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: hasDamage
            ? AppColors.secondaryContainer
            : AppColors.successContainer,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: textTheme.labelSmall?.copyWith(
          color: hasDamage
              ? AppColors.onSecondaryContainer
              : AppColors.success,
        ),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}

// ── _Thumbnail ────────────────────────────────────────────────────────────────

class _Thumbnail extends StatelessWidget {
  final String path;

  const _Thumbnail({required this.path});

  bool get _isUrl =>
      path.startsWith('http://') || path.startsWith('https://');

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: SizedBox(
        width: 80,
        height: 80,
        child: _isUrl ? _networkThumb() : _fileThumb(),
      ),
    );
  }

  Widget _networkThumb() {
    return Image.network(
      path,
      fit: BoxFit.cover,
      loadingBuilder: (context, child, progress) {
        if (progress == null) return child;
        return const ColoredBox(
          color: AppColors.surfaceVariant,
          child: Center(
            child: SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          ),
        );
      },
      errorBuilder: (context, error, stack) => _placeholder(),
    );
  }

  Widget _fileThumb() {
    final file = File(path);
    if (file.existsSync()) {
      return Image.file(file, fit: BoxFit.cover);
    }
    return _placeholder();
  }

  Widget _placeholder() {
    return const ColoredBox(
      color: AppColors.surfaceVariant,
      child: Center(
        child: Icon(
          Icons.image_not_supported_outlined,
          color: AppColors.textSecondary,
          size: 28,
        ),
      ),
    );
  }
}

// ── _EmptyState ───────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.history,
              size: 72,
              color: AppColors.textDisabled,
            ),
            const SizedBox(height: 20),
            Text(
              'No inspections yet',
              style: textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Run your first road inspection to see it here.',
              style: textTheme.bodyMedium?.copyWith(
                color: AppColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
