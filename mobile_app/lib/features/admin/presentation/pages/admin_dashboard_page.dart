import 'package:flutter/material.dart';
import '../../../../core/services/api_service.dart';
import '../../../../core/services/inspection_history_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/server_config_dialog.dart';
import '../../../../routes/app_router.dart';
import '../../data/models/admin_analytics_data.dart';
import '../widgets/damage_pie_chart.dart';
import '../widgets/recent_inspections_list.dart';
import '../widgets/severity_bar_chart.dart';
import '../widgets/summary_card.dart';

class AdminDashboardPage extends StatefulWidget {
  const AdminDashboardPage({super.key});

  @override
  State<AdminDashboardPage> createState() => _AdminDashboardPageState();
}

class _AdminDashboardPageState extends State<AdminDashboardPage> {
  late AdminAnalyticsData _data;
  final ApiService _apiService = ApiService();
  bool _isLoading = false;
  bool _isLiveBackendConnected = false;

  @override
  void initState() {
    super.initState();
    final liveHistory = InspectionHistoryService.instance.getHistory();
    _data = AdminAnalyticsData.compute(liveHistory: liveHistory);
    if (!WidgetsBinding.instance.runtimeType.toString().contains('Test')) {
      _fetchLiveAnalytics();
    }
  }

  Future<void> _fetchLiveAnalytics() async {
    setState(() => _isLoading = true);
    try {
      final json = await _apiService.fetchAdminAnalytics();
      if (!mounted) return;
      setState(() {
        _data = AdminAnalyticsData.fromJson(json);
        _isLiveBackendConnected = true;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      final liveHistory = InspectionHistoryService.instance.getHistory();
      setState(() {
        _data = AdminAnalyticsData.compute(liveHistory: liveHistory);
        _isLiveBackendConnected = false;
        _isLoading = false;
      });
    }
  }

  void _handleLogout() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Log Out'),
        content: const Text('Are you sure you want to end your admin session?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              Navigator.pushNamedAndRemoveUntil(
                context,
                AppRouter.welcome,
                (_) => false,
              );
            },
            child: const Text('Log Out'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'InfraGuard-AI',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            Text(
              'Administrator Analytics Dashboard',
              style: TextStyle(
                fontSize: 12,
                color: AppColors.onPrimary.withValues(alpha: 0.85),
                fontWeight: FontWeight.normal,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.wifi_rounded),
            tooltip: 'Server Connection',
            onPressed: () => ServerConfigDialog.show(
              context,
              onSaved: () => _fetchLiveAnalytics(),
            ),
          ),
          IconButton(
            icon: _isLoading
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Icon(Icons.refresh),
            tooltip: 'Refresh Real-time Data',
            onPressed: _isLoading
                ? null
                : () async {
                    await _fetchLiveAnalytics();
                    if (!context.mounted) return;
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(_isLiveBackendConnected
                            ? 'Real-time telemetry updated from server.'
                            : 'Offline cache refreshed.'),
                        duration: const Duration(seconds: 2),
                      ),
                    );
                  },
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Log Out',
            onPressed: _handleLogout,
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _fetchLiveAnalytics,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1080),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // ── Overview Banner ───────────────────────────────────────
                    Container(
                      padding: const EdgeInsets.all(14),
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
                      child: Column(
                        children: [
                          Row(
                            children: [
                              Container(
                                width: 40,
                                height: 40,
                                decoration: BoxDecoration(
                                  color: AppColors.primaryContainer,
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: const Icon(
                                  Icons.insights_rounded,
                                  color: AppColors.primary,
                                  size: 22,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            'Infrastructure Health & Analytics',
                                            style: textTheme.titleSmall?.copyWith(
                                              fontWeight: FontWeight.w700,
                                              color: AppColors.textPrimary,
                                            ),
                                          ),
                                        ),
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 8, vertical: 3),
                                          decoration: BoxDecoration(
                                            color: _isLiveBackendConnected
                                                ? const Color(0xFFE6F4EA)
                                                : AppColors.primaryContainer,
                                            borderRadius:
                                                BorderRadius.circular(12),
                                            border: Border.all(
                                              color: _isLiveBackendConnected
                                                  ? const Color(0xFF137333)
                                                  : AppColors.primary,
                                              width: 0.8,
                                            ),
                                          ),
                                          child: Row(
                                            mainAxisSize: MainAxisSize.min,
                                            children: [
                                              Container(
                                                width: 6,
                                                height: 6,
                                                decoration: BoxDecoration(
                                                  color: _isLiveBackendConnected
                                                      ? const Color(0xFF137333)
                                                      : AppColors.primary,
                                                  shape: BoxShape.circle,
                                                ),
                                              ),
                                              const SizedBox(width: 5),
                                              Text(
                                                _isLiveBackendConnected
                                                    ? 'LIVE REAL-TIME'
                                                    : 'LOCAL CACHE',
                                                style: TextStyle(
                                                  fontSize: 10,
                                                  fontWeight: FontWeight.bold,
                                                  color: _isLiveBackendConnected
                                                      ? const Color(0xFF137333)
                                                      : AppColors.primary,
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      _isLiveBackendConnected
                                          ? 'Central database connected. Live uploads & GIS records active.'
                                          : 'Offline mode (cached). Tap Wi-Fi icon to configure backend.',
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
                          if (_isLoading) ...[
                            const SizedBox(height: 10),
                            const LinearProgressIndicator(minHeight: 2),
                          ],
                        ],
                      ),
                    ),

                  const SizedBox(height: 18),

                  // ── KPI Summary Cards ─────────────────────────────────────
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final isWide = constraints.maxWidth > 650;
                      if (isWide) {
                        return Row(
                          children: [
                            Expanded(
                              child: SummaryCard(
                                title: 'Total Inspections',
                                value: '${_data.totalInspections}',
                                subtitle: '${_data.totalInspections} database records',
                                icon: Icons.assignment_outlined,
                                accentColor: AppColors.primary,
                                containerColor: AppColors.primaryContainer,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: SummaryCard(
                                title: 'Damaged Roads',
                                value: '${_data.damagedRoads}',
                                subtitle: _data.totalInspections > 0
                                    ? '${((_data.damagedRoads / _data.totalInspections) * 100).toStringAsFixed(1)}% defect rate'
                                    : '0% defect rate',
                                icon: Icons.warning_amber_rounded,
                                accentColor: AppColors.warning,
                                containerColor: AppColors.warningContainer,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: SummaryCard(
                                title: 'High-Risk Roads',
                                value: '${_data.highRiskRoads}',
                                subtitle: '${_data.highRiskRoads} critical hotspots',
                                icon: Icons.dangerous_outlined,
                                accentColor: AppColors.error,
                                containerColor: AppColors.errorContainer,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: SummaryCard(
                                title: 'Pending Inspections',
                                value: '${_data.pendingInspections}',
                                subtitle: '${_data.pendingInspections} awaiting repair',
                                icon: Icons.pending_actions_outlined,
                                accentColor: const Color(0xFF1D4ED8),
                                containerColor: const Color(0xFFE0E7FF),
                              ),
                            ),
                          ],
                        );
                      } else {
                        // 2x2 grid on mobile/tablet
                        return Column(
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: SummaryCard(
                                    title: 'Total Inspections',
                                    value: '${_data.totalInspections}',
                                    subtitle: '${_data.totalInspections} in database',
                                    icon: Icons.assignment_outlined,
                                    accentColor: AppColors.primary,
                                    containerColor: AppColors.primaryContainer,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: SummaryCard(
                                    title: 'Damaged Roads',
                                    value: '${_data.damagedRoads}',
                                    subtitle: _data.totalInspections > 0
                                        ? '${((_data.damagedRoads / _data.totalInspections) * 100).toStringAsFixed(0)}% defect rate'
                                        : '0% defect rate',
                                    icon: Icons.warning_amber_rounded,
                                    accentColor: AppColors.warning,
                                    containerColor: AppColors.warningContainer,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                Expanded(
                                  child: SummaryCard(
                                    title: 'High-Risk Roads',
                                    value: '${_data.highRiskRoads}',
                                    subtitle: '${_data.highRiskRoads} high risk',
                                    icon: Icons.dangerous_outlined,
                                    accentColor: AppColors.error,
                                    containerColor: AppColors.errorContainer,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: SummaryCard(
                                    title: 'Pending Inspections',
                                    value: '${_data.pendingInspections}',
                                    subtitle: '${_data.pendingInspections} to action',
                                    icon: Icons.pending_actions_outlined,
                                    accentColor: const Color(0xFF1D4ED8),
                                    containerColor: const Color(0xFFE0E7FF),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        );
                      }
                    },
                  ),

                  const SizedBox(height: 18),

                  // ── Visual Charts: Pie Chart & Bar Chart ───────────────────
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final isWide = constraints.maxWidth > 780;
                      if (isWide) {
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: DamagePieChart(
                                categoryCounts: _data.damageCategoryCounts,
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: SeverityBarChart(
                                severityCounts: _data.severityCounts,
                              ),
                            ),
                          ],
                        );
                      } else {
                        return Column(
                          children: [
                            DamagePieChart(
                              categoryCounts: _data.damageCategoryCounts,
                            ),
                            const SizedBox(height: 16),
                            SeverityBarChart(
                              severityCounts: _data.severityCounts,
                            ),
                          ],
                        );
                      }
                    },
                  ),

                  const SizedBox(height: 18),

                  // ── Recent Inspections List ───────────────────────────────
                  RecentInspectionsList(
                    inspections: _data.recentInspections,
                  ),

                  const SizedBox(height: 24),

                  // ── Subtle Footer ─────────────────────────────────────────
                  Center(
                    child: Text(
                      'InfraGuard-AI Executive Suite • Road Safety Intelligence',
                      style: textTheme.labelSmall?.copyWith(
                        color: AppColors.textDisabled,
                        fontSize: 11,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    ),
  );
}
}
