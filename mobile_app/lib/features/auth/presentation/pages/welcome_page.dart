import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../routes/app_router.dart';

class WelcomePage extends StatelessWidget {
  const WelcomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // ── Brand Header ──────────────────────────────────────────
                  Center(
                    child: Container(
                      width: 84,
                      height: 84,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [AppColors.primary, Color(0xFF1E3A8A)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(22),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.primary.withValues(alpha: 0.25),
                            blurRadius: 16,
                            offset: const Offset(0, 8),
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.shield_outlined,
                        size: 46,
                        color: AppColors.onPrimary,
                      ),
                    ),
                  ),

                  const SizedBox(height: 20),

                  Text(
                    'InfraGuard-AI',
                    textAlign: TextAlign.center,
                    style: textTheme.headlineMedium?.copyWith(
                      color: AppColors.primary,
                      fontWeight: FontWeight.w800,
                      letterSpacing: -0.5,
                    ),
                  ),

                  const SizedBox(height: 6),

                  Text(
                    'AI-Powered Road Infrastructure\nInspection & Risk Analytics',
                    textAlign: TextAlign.center,
                    style: textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                      height: 1.4,
                    ),
                  ),

                  const SizedBox(height: 36),

                  // ── Role Selection Prompt ─────────────────────────────────
                  Row(
                    children: [
                      const Expanded(
                        child: Divider(color: AppColors.outlineVariant),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        child: Text(
                          'SELECT YOUR ROLE',
                          style: textTheme.labelSmall?.copyWith(
                            color: AppColors.textSecondary,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.1,
                          ),
                        ),
                      ),
                      const Expanded(
                        child: Divider(color: AppColors.outlineVariant),
                      ),
                    ],
                  ),

                  const SizedBox(height: 20),

                  // ── Option 1: Inspector Login ─────────────────────────────
                  _RoleCard(
                    title: 'Inspector Login',
                    badge: 'FIELD INSPECTOR',
                    subtitle:
                        'Capture road distress with camera, upload gallery photos, auto-acquire GPS & run AI detection.',
                    icon: Icons.camera_alt_outlined,
                    iconBgColor: AppColors.primaryContainer,
                    iconColor: AppColors.primary,
                    onTap: () =>
                        Navigator.pushNamed(context, AppRouter.inspectorLogin),
                  ),

                  const SizedBox(height: 16),

                  // ── Option 2: Admin Login ─────────────────────────────────
                  _RoleCard(
                    title: 'Admin Login',
                    badge: 'ADMINISTRATOR',
                    subtitle:
                        'Executive analytics dashboard, damage distribution pie charts, severity breakdown & inspection history.',
                    icon: Icons.insights_rounded,
                    iconBgColor: const Color(0xFFE0E7FF),
                    iconColor: const Color(0xFF1E40AF),
                    onTap: () =>
                        Navigator.pushNamed(context, AppRouter.adminLogin),
                  ),

                  const SizedBox(height: 36),

                  // ── Prototype / Demo Disclaimer ───────────────────────────
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceVariant,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: AppColors.outlineVariant),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.info_outline,
                          size: 16,
                          color: AppColors.textSecondary,
                        ),
                        const SizedBox(width: 8),
                        Flexible(
                          child: Text(
                            'Prototype Mode: Pre-configured credentials available for testing.',
                            style: textTheme.bodySmall?.copyWith(
                              color: AppColors.textSecondary,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 16),

                  Text(
                    'InfraGuard-AI Platform • Build v1.0',
                    textAlign: TextAlign.center,
                    style: textTheme.labelSmall?.copyWith(
                      color: AppColors.textDisabled,
                      fontSize: 11,
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

class _RoleCard extends StatelessWidget {
  final String title;
  final String badge;
  final String subtitle;
  final IconData icon;
  final Color iconBgColor;
  final Color iconColor;
  final VoidCallback onTap;

  const _RoleCard({
    required this.title,
    required this.badge,
    required this.subtitle,
    required this.icon,
    required this.iconBgColor,
    required this.iconColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Material(
      color: AppColors.surface,
      elevation: 1,
      shadowColor: Colors.black.withValues(alpha: 0.06),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: AppColors.outlineVariant),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: iconBgColor,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, size: 26, color: iconColor),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            title,
                            style: textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.surfaceVariant,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            badge,
                            style: textTheme.labelSmall?.copyWith(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      subtitle,
                      style: textTheme.bodySmall?.copyWith(
                        color: AppColors.textSecondary,
                        height: 1.35,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              const Padding(
                padding: EdgeInsets.only(top: 14),
                child: Icon(
                  Icons.arrow_forward_ios_rounded,
                  size: 16,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
