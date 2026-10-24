import 'dart:io';
import 'package:flutter/material.dart';
import '../../../../core/services/inspection_history_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../routes/app_router.dart';
import '../../data/models/inspection_history_item.dart';
import '../../data/models/inspection_location.dart';

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
          arguments: ResultPageArgs(
            result: item.predictionResult,
            location: item.location,
          ),
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

                    const SizedBox(height: 2),

                    // ── Location status row ────────────────────────────────
                    _LocationStatusRow(location: item.location),

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

// ── _LocationStatusRow ────────────────────────────────────────────────────────

/// Compact one-line location status shown on each history card.
///
/// When [location] is non-null: green icon + "Location captured" — tappable,
/// opens [_LocationDetailDialog].
/// When [location] is null: disabled icon + "Location unavailable" — not
/// tappable, no fake coordinates shown.
class _LocationStatusRow extends StatelessWidget {
  final InspectionLocation? location;

  const _LocationStatusRow({required this.location});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final hasLocation = location != null;

    final icon = hasLocation
        ? Icons.location_on_outlined
        : Icons.location_off_outlined;
    final iconColor =
        hasLocation ? AppColors.success : AppColors.textDisabled;
    final label =
        hasLocation ? 'Location captured' : 'Location unavailable';
    final labelColor =
        hasLocation ? AppColors.success : AppColors.textDisabled;

    final row = Row(
      children: [
        Icon(icon, size: 13, color: iconColor),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            label,
            style: textTheme.bodySmall?.copyWith(color: labelColor),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        // Chevron hint is shown only when the row is tappable.
        if (hasLocation)
          Icon(
            Icons.chevron_right,
            size: 13,
            color: AppColors.textSecondary,
          ),
      ],
    );

    if (!hasLocation) return row;

    // Wrap in InkWell only when a location is available to show.
    return InkWell(
      borderRadius: BorderRadius.circular(4),
      onTap: () => _showLocationDetail(context, location!),
      child: row,
    );
  }

  void _showLocationDetail(BuildContext context, InspectionLocation loc) {
    showDialog<void>(
      context: context,
      builder: (ctx) => _LocationDetailDialog(location: loc),
    );
  }
}

// ── _LocationDetailDialog ─────────────────────────────────────────────────────

/// Full-detail dialog for a captured inspection location.
///
/// Shows latitude, longitude, and accuracy (when available).
/// "Open in Maps" requires the `url_launcher` package which is not yet
/// in this project — that button is omitted until the package is added.
class _LocationDetailDialog extends StatelessWidget {
  final InspectionLocation location;

  const _LocationDetailDialog({required this.location});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return AlertDialog(
      title: Row(
        children: [
          const Icon(
            Icons.location_on_outlined,
            size: 20,
            color: AppColors.primary,
          ),
          const SizedBox(width: 8),
          Text('Inspection Location', style: textTheme.titleMedium),
        ],
      ),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _CoordRow(
            label: 'Latitude',
            value: location.latitude.toStringAsFixed(6),
          ),
          const SizedBox(height: 12),
          _CoordRow(
            label: 'Longitude',
            value: location.longitude.toStringAsFixed(6),
          ),
          if (location.accuracy != null) ...[
            const SizedBox(height: 12),
            _CoordRow(
              label: 'Accuracy',
              value: '±${location.accuracy!.toStringAsFixed(0)} m',
            ),
          ],
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Close'),
        ),
      ],
    );
  }
}

// ── _CoordRow ─────────────────────────────────────────────────────────────────

/// A labelled coordinate value row inside [_LocationDetailDialog].
class _CoordRow extends StatelessWidget {
  final String label;
  final String value;

  const _CoordRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: textTheme.labelMedium),
        const SizedBox(width: 16),
        Flexible(
          child: Text(
            value,
            style: textTheme.bodyMedium,
            textAlign: TextAlign.end,
          ),
        ),
      ],
    );
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
