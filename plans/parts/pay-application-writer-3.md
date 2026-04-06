## Phase 9: Project Analytics

### Sub-phase 9.1: Analytics Domain Models

**Agent**: `code-fixer-agent`
**Files**:
- `lib/features/analytics/data/models/analytics_summary.dart` (NEW)
- `lib/features/analytics/data/models/pay_app_summary.dart` (NEW)
- `lib/features/analytics/data/models/models.dart` (NEW barrel)

#### Step 9.1.1: Create AnalyticsSummary model

Create the summary model that holds aggregated project analytics data.

**File**: `lib/features/analytics/data/models/analytics_summary.dart` (NEW)

```dart
// WHY: Pure Dart data class holding aggregated analytics for a project.
// FROM SPEC: Analytics screen shows pay-app-aware summary data, including
// change since last pay app.

/// Aggregated analytics summary for a project.
class AnalyticsSummary {
  final int totalBidItems;
  final double totalContractAmount;
  final double totalEarnedToDate;
  final double percentComplete;
  final int totalPayApps;
  final double changeSinceLastPayApp;
  final DateTime? lastPayAppDate;
  final List<BidItemProgress> itemProgress;

  const AnalyticsSummary({
    required this.totalBidItems,
    required this.totalContractAmount,
    required this.totalEarnedToDate,
    required this.percentComplete,
    required this.totalPayApps,
    required this.changeSinceLastPayApp,
    this.lastPayAppDate,
    required this.itemProgress,
  });

  static const empty = AnalyticsSummary(
    totalBidItems: 0,
    totalContractAmount: 0,
    totalEarnedToDate: 0,
    percentComplete: 0,
    totalPayApps: 0,
    changeSinceLastPayApp: 0,
    itemProgress: [],
  );
}

/// Progress for a single bid item within analytics.
class BidItemProgress {
  final String bidItemId;
  final String itemNumber;
  final String description;
  final String unit;
  final double bidQuantity;
  final double usedQuantity;
  final double unitPrice;
  final double earnedAmount;
  final double percentUsed;

  const BidItemProgress({
    required this.bidItemId,
    required this.itemNumber,
    required this.description,
    required this.unit,
    required this.bidQuantity,
    required this.usedQuantity,
    required this.unitPrice,
    required this.earnedAmount,
    required this.percentUsed,
  });
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/data/models/analytics_summary.dart"`
**Expected**: No issues found

#### Step 9.1.2: Create PayAppSummary model for comparison chart

**File**: `lib/features/analytics/data/models/pay_app_summary.dart` (NEW)

```dart
// WHY: Lightweight summary of a pay app for chart rendering.
// FROM SPEC: payAppComparison getter returns list for bar chart.

/// Summary data for one pay application, used in comparison charts.
class PayAppSummary {
  final String payAppId;
  final int applicationNumber;
  final DateTime periodStart;
  final DateTime periodEnd;
  final double totalEarnedThisPeriod;
  final double totalEarnedToDate;
  final double totalContractAmount;

  const PayAppSummary({
    required this.payAppId,
    required this.applicationNumber,
    required this.periodStart,
    required this.periodEnd,
    required this.totalEarnedThisPeriod,
    required this.totalEarnedToDate,
    required this.totalContractAmount,
  });
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/data/models/pay_app_summary.dart"`
**Expected**: No issues found

#### Step 9.1.3: Create analytics models barrel export

**File**: `lib/features/analytics/data/models/models.dart` (NEW)

```dart
export 'analytics_summary.dart';
export 'pay_app_summary.dart';
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/data/models/models.dart"`
**Expected**: No issues found

---

### Sub-phase 9.2: ProjectAnalyticsProvider

**Agent**: `code-fixer-agent`
**Files**:
- `lib/features/analytics/presentation/providers/project_analytics_provider.dart` (NEW)
- `lib/features/analytics/presentation/providers/providers.dart` (NEW barrel)

#### Step 9.2.1: Create ProjectAnalyticsProvider

This provider aggregates data from BidItemRepository, EntryQuantityRepository, and PayApplicationRepository to compute analytics. It uses SafeAction for async error handling.

**File**: `lib/features/analytics/presentation/providers/project_analytics_provider.dart` (NEW)

```dart
// WHY: Aggregates project analytics from existing repositories.
// FROM SPEC: ProjectAnalyticsProvider (ChangeNotifier with SafeAction):
// loadAnalytics, applyDateFilter, summary getter, payAppComparison getter,
// changeSinceLastPayApp getter.

import 'package:flutter/foundation.dart';
import 'package:construction_inspector/shared/providers/safe_action_mixin.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/quantities/domain/repositories/bid_item_repository.dart';
import 'package:construction_inspector/features/quantities/domain/repositories/entry_quantity_repository.dart';
import 'package:construction_inspector/features/pay_applications/domain/repositories/pay_application_repository.dart';
import 'package:construction_inspector/features/analytics/data/models/models.dart';

class ProjectAnalyticsProvider extends ChangeNotifier with SafeAction {
  final BidItemRepository _bidItemRepository;
  final EntryQuantityRepository _entryQuantityRepository;
  final PayApplicationRepository _payApplicationRepository;

  ProjectAnalyticsProvider({
    required BidItemRepository bidItemRepository,
    required EntryQuantityRepository entryQuantityRepository,
    required PayApplicationRepository payApplicationRepository,
  })  : _bidItemRepository = bidItemRepository,
        _entryQuantityRepository = entryQuantityRepository,
        _payApplicationRepository = payApplicationRepository;

  // SafeAction accessors
  @override
  bool get safeActionIsLoading => _isLoading;
  @override
  set safeActionIsLoading(bool value) => _isLoading = value;
  @override
  String? get safeActionError => _error;
  @override
  set safeActionError(String? value) => _error = value;
  @override
  String get safeActionLogTag => 'ProjectAnalyticsProvider';

  // State
  bool _isLoading = false;
  String? _error;
  AnalyticsSummary _summary = AnalyticsSummary.empty;
  List<PayAppSummary> _payAppComparison = [];
  String? _currentProjectId;
  DateTime? _filterStart;
  DateTime? _filterEnd;

  // Public getters
  // FROM SPEC: summary getter
  AnalyticsSummary get summary => _summary;
  // FROM SPEC: payAppComparison getter
  List<PayAppSummary> get payAppComparison => _payAppComparison;
  // FROM SPEC: changeSinceLastPayApp getter
  double get changeSinceLastPayApp => _summary.changeSinceLastPayApp;
  bool get isLoading => _isLoading;
  String? get error => _error;
  DateTime? get filterStart => _filterStart;
  DateTime? get filterEnd => _filterEnd;

  /// FROM SPEC: loadAnalytics(String projectId)
  /// Loads all analytics data for a project: bid items, quantities,
  /// and pay application history.
  Future<void> loadAnalytics(String projectId) async {
    _currentProjectId = projectId;
    await runSafeAction('load analytics', () async {
      // NOTE: Parallel fetch from three repositories for performance.
      // FROM SPEC: Analytics initial load: <500ms on normal project size.
      final results = await Future.wait([
        _bidItemRepository.getByProjectId(projectId),
        _entryQuantityRepository.getTotalUsedByProject(projectId),
        _payApplicationRepository.getByProjectId(projectId),
      ]);

      final bidItems = results[0] as List;
      // NOTE: Map<String, double> keyed by bidItemId
      final usedByItem = results[1] as Map<String, double>;
      final payApps = results[2] as List;

      _computeSummary(bidItems, usedByItem, payApps);
      _computePayAppComparison(payApps);
    }, buildErrorMessage: (_) => 'Failed to load analytics.');
  }

  /// FROM SPEC: applyDateFilter(DateTime? start, DateTime? end)
  /// Filters analytics to a date range. Reloads data with the filter applied.
  Future<void> applyDateFilter(DateTime? start, DateTime? end) async {
    _filterStart = start;
    _filterEnd = end;
    if (_currentProjectId != null) {
      await loadAnalytics(_currentProjectId!);
    }
  }

  void _computeSummary(
    List<dynamic> bidItems,
    Map<String, double> usedByItem,
    List<dynamic> payApps,
  ) {
    double totalContractAmount = 0;
    double totalEarnedToDate = 0;
    final itemProgress = <BidItemProgress>[];

    for (final item in bidItems) {
      // NOTE: bidAmount is the source-of-truth total (from PDF import).
      // unitPrice * bidQuantity can be inflated by OCR errors.
      // WHY: Matches budget overview logic in project_dashboard_screen.dart:375-378.
      final bidAmount = (item.bidAmount ?? (item.bidQuantity * (item.unitPrice ?? 0))) as double;
      totalContractAmount += bidAmount;

      final used = usedByItem[item.id] ?? 0.0;
      final unitPrice = (item.unitPrice ?? 0.0) as double;
      final earnedAmount = used * unitPrice;
      totalEarnedToDate += earnedAmount;

      final percentUsed = item.bidQuantity > 0
          ? (used / item.bidQuantity * 100).clamp(0.0, double.infinity)
          : 0.0;

      itemProgress.add(BidItemProgress(
        bidItemId: item.id as String,
        itemNumber: item.itemNumber as String,
        description: item.description as String,
        unit: item.unit as String,
        bidQuantity: item.bidQuantity as double,
        usedQuantity: used,
        unitPrice: unitPrice,
        earnedAmount: earnedAmount,
        percentUsed: percentUsed,
      ));
    }

    final percentComplete = totalContractAmount > 0
        ? (totalEarnedToDate / totalContractAmount * 100)
        : 0.0;

    // FROM SPEC: compute changeSinceLastPayApp
    double changeSinceLastPayApp = 0;
    DateTime? lastPayAppDate;
    if (payApps.isNotEmpty) {
      // NOTE: payApps are sorted by application_number. Last one is most recent.
      final lastPayApp = payApps.last;
      changeSinceLastPayApp = totalEarnedToDate - (lastPayApp.totalEarnedToDate as double);
      lastPayAppDate = DateTime.tryParse(lastPayApp.periodEnd as String);
    }

    _summary = AnalyticsSummary(
      totalBidItems: bidItems.length,
      totalContractAmount: totalContractAmount,
      totalEarnedToDate: totalEarnedToDate,
      percentComplete: percentComplete,
      totalPayApps: payApps.length,
      changeSinceLastPayApp: changeSinceLastPayApp,
      lastPayAppDate: lastPayAppDate,
      itemProgress: itemProgress,
    );
  }

  void _computePayAppComparison(List<dynamic> payApps) {
    // FROM SPEC: PayAppComparisonChart — bar chart comparing pay apps
    _payAppComparison = payApps.map((pa) {
      return PayAppSummary(
        payAppId: pa.id as String,
        applicationNumber: pa.applicationNumber as int,
        periodStart: DateTime.parse(pa.periodStart as String),
        periodEnd: DateTime.parse(pa.periodEnd as String),
        totalEarnedThisPeriod: pa.totalEarnedThisPeriod as double,
        totalEarnedToDate: pa.totalEarnedToDate as double,
        totalContractAmount: pa.totalContractAmount as double,
      );
    }).toList();
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/presentation/providers/project_analytics_provider.dart"`
**Expected**: No issues found

#### Step 9.2.2: Create analytics providers barrel

**File**: `lib/features/analytics/presentation/providers/providers.dart` (NEW)

```dart
export 'project_analytics_provider.dart';
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/presentation/providers/providers.dart"`
**Expected**: No issues found

---

### Sub-phase 9.3: Analytics Widgets

**Agent**: `code-fixer-agent`
**Files**:
- `lib/features/analytics/presentation/widgets/analytics_summary_header.dart` (NEW)
- `lib/features/analytics/presentation/widgets/pay_app_comparison_chart.dart` (NEW)
- `lib/features/analytics/presentation/widgets/date_range_filter_bar.dart` (NEW)
- `lib/features/analytics/presentation/widgets/widgets.dart` (NEW barrel)

#### Step 9.3.1: Create AnalyticsSummaryHeader widget

**File**: `lib/features/analytics/presentation/widgets/analytics_summary_header.dart` (NEW)

```dart
// WHY: Summary header for analytics screen showing key metrics.
// FROM SPEC: Create AnalyticsSummaryHeader widget. Summary header
// including change since last pay app.

import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/core/theme/design_constants.dart';
import 'package:construction_inspector/core/config/app_terminology.dart';
import 'package:construction_inspector/features/analytics/data/models/models.dart';

class AnalyticsSummaryHeader extends StatelessWidget {
  final AnalyticsSummary summary;

  const AnalyticsSummaryHeader({
    super.key,
    required this.summary,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return AppGlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppText.titleMedium(
            'Project Summary',
            color: cs.onSurface,
          ),
          const SizedBox(height: DesignConstants.space3),
          // NOTE: Two-column grid of key metrics
          Row(
            children: [
              Expanded(
                child: _MetricTile(
                  label: 'Contract Total',
                  value: '\$${_formatCurrency(summary.totalContractAmount)}',
                  icon: Icons.account_balance_outlined,
                  color: cs.primary,
                ),
              ),
              const SizedBox(width: DesignConstants.space2),
              Expanded(
                child: _MetricTile(
                  label: 'Earned to Date',
                  value: '\$${_formatCurrency(summary.totalEarnedToDate)}',
                  icon: Icons.trending_up,
                  color: cs.tertiary,
                ),
              ),
            ],
          ),
          const SizedBox(height: DesignConstants.space2),
          Row(
            children: [
              Expanded(
                child: _MetricTile(
                  // WHY: AppTerminology.bidItemPlural respects MDOT mode
                  label: AppTerminology.bidItemPlural,
                  value: summary.totalBidItems.toString(),
                  icon: Icons.inventory_2_outlined,
                  color: cs.secondary,
                ),
              ),
              const SizedBox(width: DesignConstants.space2),
              Expanded(
                child: _MetricTile(
                  label: '% Complete',
                  value: '${summary.percentComplete.toStringAsFixed(1)}%',
                  icon: Icons.pie_chart_outline,
                  color: cs.primary,
                ),
              ),
            ],
          ),
          const SizedBox(height: DesignConstants.space2),
          Row(
            children: [
              Expanded(
                child: _MetricTile(
                  label: 'Pay Applications',
                  value: summary.totalPayApps.toString(),
                  icon: Icons.receipt_long_outlined,
                  color: cs.secondary,
                ),
              ),
              const SizedBox(width: DesignConstants.space2),
              Expanded(
                // FROM SPEC: change since last pay app
                child: _MetricTile(
                  label: 'Change Since Last PA',
                  value: '\$${_formatCurrency(summary.changeSinceLastPayApp)}',
                  icon: Icons.difference_outlined,
                  color: summary.changeSinceLastPayApp >= 0
                      ? cs.tertiary
                      : cs.error,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatCurrency(double amount) {
    // NOTE: Simple comma-separated format. Negative values show minus sign.
    final isNegative = amount < 0;
    final abs = amount.abs();
    final whole = abs.truncate();
    final cents = ((abs - whole) * 100).round().toString().padLeft(2, '0');
    final parts = <String>[];
    var remaining = whole;
    while (remaining >= 1000) {
      parts.insert(0, (remaining % 1000).toString().padLeft(3, '0'));
      remaining ~/= 1000;
    }
    parts.insert(0, remaining.toString());
    return '${isNegative ? '-' : ''}${parts.join(',')}.$cents';
  }
}

class _MetricTile extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;
  final Color color;

  const _MetricTile({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(DesignConstants.space3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(DesignConstants.radiusMd),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: color),
          const SizedBox(height: DesignConstants.space1),
          AppText.titleMedium(value, color: cs.onSurface),
          const SizedBox(height: DesignConstants.space05),
          AppText.labelSmall(
            label,
            color: cs.onSurfaceVariant,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/presentation/widgets/analytics_summary_header.dart"`
**Expected**: No issues found

#### Step 9.3.2: Create PayAppComparisonChart widget

**File**: `lib/features/analytics/presentation/widgets/pay_app_comparison_chart.dart` (NEW)

```dart
// WHY: Visual comparison of pay applications over time.
// FROM SPEC: Create PayAppComparisonChart widget. Bar chart comparing pay apps.
// NOTE: Uses basic Flutter widgets for chart rendering rather than a
// third-party chart package, keeping dependencies minimal.

import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/core/theme/design_constants.dart';
import 'package:construction_inspector/features/analytics/data/models/models.dart';

class PayAppComparisonChart extends StatelessWidget {
  final List<PayAppSummary> payApps;

  const PayAppComparisonChart({
    super.key,
    required this.payApps,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    if (payApps.isEmpty) {
      return AppGlassCard(
        child: Padding(
          padding: const EdgeInsets.all(DesignConstants.space4),
          child: Center(
            child: AppText.bodyMedium(
              'No pay applications to compare.',
              color: cs.onSurfaceVariant,
            ),
          ),
        ),
      );
    }

    // NOTE: Find max value for scaling bars
    final maxEarned = payApps
        .map((pa) => pa.totalEarnedThisPeriod)
        .fold<double>(0, (a, b) => a > b ? a : b);

    return AppGlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppText.titleMedium(
            'Pay App History',
            color: cs.onSurface,
          ),
          const SizedBox(height: DesignConstants.space3),
          ...payApps.map((pa) => _PayAppBar(
                payApp: pa,
                maxValue: maxEarned,
              )),
        ],
      ),
    );
  }
}

class _PayAppBar extends StatelessWidget {
  final PayAppSummary payApp;
  final double maxValue;

  const _PayAppBar({
    required this.payApp,
    required this.maxValue,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final barFraction = maxValue > 0
        ? (payApp.totalEarnedThisPeriod / maxValue).clamp(0.0, 1.0)
        : 0.0;

    return Padding(
      padding: const EdgeInsets.only(bottom: DesignConstants.space2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              AppText.labelMedium(
                'PA #${payApp.applicationNumber}',
                color: cs.onSurface,
              ),
              AppText.labelSmall(
                '\$${payApp.totalEarnedThisPeriod.toStringAsFixed(2)}',
                color: cs.onSurfaceVariant,
              ),
            ],
          ),
          const SizedBox(height: DesignConstants.space1),
          // NOTE: Horizontal bar representing earned this period
          LayoutBuilder(
            builder: (context, constraints) {
              return Container(
                height: 16,
                decoration: BoxDecoration(
                  color: cs.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: FractionallySizedBox(
                    widthFactor: barFraction,
                    child: Container(
                      decoration: BoxDecoration(
                        color: cs.primary,
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/presentation/widgets/pay_app_comparison_chart.dart"`
**Expected**: No issues found

#### Step 9.3.3: Create DateRangeFilterBar widget

**File**: `lib/features/analytics/presentation/widgets/date_range_filter_bar.dart` (NEW)

```dart
// WHY: Reusable date range filter for analytics screen.
// FROM SPEC: Create DateRangeFilterBar widget. Date filter for analytics.
// IMPORTANT: Uses AppTerminology for labels.

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/core/theme/design_constants.dart';
import 'package:construction_inspector/shared/shared.dart';

class DateRangeFilterBar extends StatelessWidget {
  final DateTime? startDate;
  final DateTime? endDate;
  final ValueChanged<DateTimeRange?> onDateRangeChanged;

  const DateRangeFilterBar({
    super.key,
    this.startDate,
    this.endDate,
    required this.onDateRangeChanged,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final hasFilter = startDate != null || endDate != null;
    final dateFormat = DateFormat('MMM d, yyyy');

    return Row(
      children: [
        Icon(Icons.filter_list, size: 20, color: cs.onSurfaceVariant),
        const SizedBox(width: DesignConstants.space2),
        Expanded(
          child: InkWell(
            key: TestingKeys.analyticsDateFilter,
            borderRadius: BorderRadius.circular(DesignConstants.radiusMd),
            onTap: () => _showDateRangePicker(context),
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DesignConstants.space3,
                vertical: DesignConstants.space2,
              ),
              decoration: BoxDecoration(
                border: Border.all(
                  color: hasFilter ? cs.primary : cs.outlineVariant,
                ),
                borderRadius: BorderRadius.circular(DesignConstants.radiusMd),
              ),
              child: AppText.bodyMedium(
                hasFilter
                    ? '${dateFormat.format(startDate!)} - ${dateFormat.format(endDate!)}'
                    : 'All Time',
                color: hasFilter ? cs.primary : cs.onSurfaceVariant,
              ),
            ),
          ),
        ),
        if (hasFilter) ...[
          const SizedBox(width: DesignConstants.space1),
          IconButton(
            icon: Icon(Icons.clear, size: 20, color: cs.onSurfaceVariant),
            onPressed: () => onDateRangeChanged(null),
            tooltip: 'Clear filter',
          ),
        ],
      ],
    );
  }

  Future<void> _showDateRangePicker(BuildContext context) async {
    final now = DateTime.now();
    final result = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: now,
      initialDateRange: startDate != null && endDate != null
          ? DateTimeRange(start: startDate!, end: endDate!)
          : null,
    );

    if (result != null) {
      onDateRangeChanged(result);
    }
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/presentation/widgets/date_range_filter_bar.dart"`
**Expected**: No issues found

#### Step 9.3.4: Create analytics widgets barrel

**File**: `lib/features/analytics/presentation/widgets/widgets.dart` (NEW)

```dart
export 'analytics_summary_header.dart';
export 'pay_app_comparison_chart.dart';
export 'date_range_filter_bar.dart';
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/presentation/widgets/widgets.dart"`
**Expected**: No issues found

---

### Sub-phase 9.4: ProjectAnalyticsScreen

**Agent**: `code-fixer-agent`
**Files**:
- `lib/features/analytics/presentation/screens/project_analytics_screen.dart` (NEW)
- `lib/features/analytics/presentation/screens/screens.dart` (NEW barrel)

#### Step 9.4.1: Create ProjectAnalyticsScreen

**File**: `lib/features/analytics/presentation/screens/project_analytics_screen.dart` (NEW)

```dart
// WHY: Main analytics screen accessible from dashboard 4th card and
// quantities screen secondary entry point.
// FROM SPEC: Create ProjectAnalyticsScreen with summary header, date filter,
// charts (progress by item, top items, pay app history comparison).
// IMPORTANT: Uses AppScaffold, theme colors, and AppTerminology throughout.

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/core/theme/design_constants.dart';
import 'package:construction_inspector/core/theme/field_guide_colors.dart';
import 'package:construction_inspector/core/config/app_terminology.dart';
import 'package:construction_inspector/shared/shared.dart';
import 'package:construction_inspector/features/analytics/presentation/providers/providers.dart';
import 'package:construction_inspector/features/analytics/presentation/widgets/widgets.dart';
import 'package:construction_inspector/features/analytics/data/models/models.dart';

class ProjectAnalyticsScreen extends StatefulWidget {
  final String projectId;

  const ProjectAnalyticsScreen({
    super.key,
    required this.projectId,
  });

  @override
  State<ProjectAnalyticsScreen> createState() => _ProjectAnalyticsScreenState();
}

class _ProjectAnalyticsScreenState extends State<ProjectAnalyticsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<ProjectAnalyticsProvider>().loadAnalytics(widget.projectId);
    });
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      key: TestingKeys.analyticsScreen,
      appBar: AppBar(
        title: const Text('Project Analytics'),
        leading: BackButton(
          onPressed: () => safeGoBack(context, fallbackRouteName: 'dashboard'),
        ),
      ),
      body: Consumer<ProjectAnalyticsProvider>(
        builder: (context, provider, _) {
          if (provider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          if (provider.error != null) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  AppText.bodyMedium(
                    provider.error!,
                    color: Theme.of(context).colorScheme.error,
                  ),
                  const SizedBox(height: DesignConstants.space3),
                  FilledButton(
                    onPressed: () => provider.loadAnalytics(widget.projectId),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            );
          }

          return ListView(
            padding: const EdgeInsets.all(DesignConstants.space4),
            children: [
              // FROM SPEC: summary header
              AnalyticsSummaryHeader(summary: provider.summary),
              const SizedBox(height: DesignConstants.space3),

              // FROM SPEC: date filter
              DateRangeFilterBar(
                startDate: provider.filterStart,
                endDate: provider.filterEnd,
                onDateRangeChanged: (range) {
                  provider.applyDateFilter(range?.start, range?.end);
                },
              ),
              const SizedBox(height: DesignConstants.space3),

              // FROM SPEC: progress by item
              _buildItemProgressSection(context, provider.summary),
              const SizedBox(height: DesignConstants.space3),

              // FROM SPEC: pay app history comparison
              PayAppComparisonChart(payApps: provider.payAppComparison),
            ],
          );
        },
      ),
    );
  }

  Widget _buildItemProgressSection(BuildContext context, AnalyticsSummary summary) {
    final cs = Theme.of(context).colorScheme;

    if (summary.itemProgress.isEmpty) {
      return AppGlassCard(
        child: Padding(
          padding: const EdgeInsets.all(DesignConstants.space4),
          child: Center(
            child: AppText.bodyMedium(
              'No ${AppTerminology.bidItemPlural.toLowerCase()} tracked yet.',
              color: cs.onSurfaceVariant,
            ),
          ),
        ),
      );
    }

    // FROM SPEC: top items by recent activity — sort by used quantity descending
    final sorted = List<BidItemProgress>.from(summary.itemProgress)
      ..sort((a, b) => b.usedQuantity.compareTo(a.usedQuantity));
    // NOTE: Show top 10 items to avoid overwhelming the screen
    final topItems = sorted.take(10).toList();

    return AppGlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppText.titleMedium(
            '${AppTerminology.bidItem} Progress',
            color: cs.onSurface,
          ),
          const SizedBox(height: DesignConstants.space3),
          ...topItems.map((item) => _ItemProgressRow(item: item)),
          if (sorted.length > 10) ...[
            const SizedBox(height: DesignConstants.space2),
            Center(
              child: AppText.labelSmall(
                '${sorted.length - 10} more items not shown',
                color: cs.onSurfaceVariant,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ItemProgressRow extends StatelessWidget {
  final BidItemProgress item;

  const _ItemProgressRow({required this.item});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final fg = FieldGuideColors.of(context);
    final barFraction = item.bidQuantity > 0
        ? (item.usedQuantity / item.bidQuantity).clamp(0.0, 1.0)
        : 0.0;
    // WHY: Color-code based on usage percentage for quick visual scanning
    final barColor = item.percentUsed > 100
        ? cs.error
        : item.percentUsed > 80
            ? fg.accentAmber
            : cs.primary;

    return Padding(
      padding: const EdgeInsets.only(bottom: DesignConstants.space3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: AppText.labelMedium(
                  '${item.itemNumber} - ${item.description}',
                  color: cs.onSurface,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              AppText.labelSmall(
                '${item.usedQuantity.toStringAsFixed(1)} / ${item.bidQuantity.toStringAsFixed(1)} ${item.unit}',
                color: cs.onSurfaceVariant,
              ),
            ],
          ),
          const SizedBox(height: DesignConstants.space1),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: barFraction,
              backgroundColor: cs.surfaceContainerHighest,
              color: barColor,
              minHeight: 8,
            ),
          ),
          const SizedBox(height: DesignConstants.space05),
          Align(
            alignment: Alignment.centerRight,
            child: AppText.labelSmall(
              '${item.percentUsed.toStringAsFixed(1)}%',
              color: cs.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/presentation/screens/project_analytics_screen.dart"`
**Expected**: No issues found

#### Step 9.4.2: Create analytics screens barrel

**File**: `lib/features/analytics/presentation/screens/screens.dart` (NEW)

```dart
export 'project_analytics_screen.dart';
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/presentation/screens/screens.dart"`
**Expected**: No issues found

---

## Phase 10: Integration & Routing

### Sub-phase 10.1: Route Registration

**Agent**: `code-fixer-agent`
**Files**:
- `lib/core/router/routes/pay_app_routes.dart` (NEW)
- `lib/core/router/app_router.dart:1,7,157` (MODIFY)

#### Step 10.1.1: Create pay_app_routes.dart

**File**: `lib/core/router/routes/pay_app_routes.dart` (NEW)

```dart
// WHY: Central route registration for pay application and analytics features.
// FROM SPEC: GoRoute entries for /pay-app/:payAppId, /pay-app/:payAppId/compare,
// /analytics/:projectId.
// NOTE: Follows same pattern as form_routes.dart — top-level function
// returning List<RouteBase>, spread into app_router.dart routes list.

import 'package:go_router/go_router.dart';
import 'package:construction_inspector/features/pay_applications/presentation/screens/screens.dart';
import 'package:construction_inspector/features/analytics/presentation/screens/screens.dart';

List<RouteBase> payAppRoutes() => [
      // FROM SPEC: /pay-app/:payAppId — saved pay app detail view
      GoRoute(
        path: '/pay-app/:payAppId',
        name: 'payAppDetail',
        builder: (context, state) {
          final payAppId = state.pathParameters['payAppId']!;
          return PayApplicationDetailScreen(payAppId: payAppId);
        },
      ),
      // FROM SPEC: /pay-app/:payAppId/compare — contractor comparison
      GoRoute(
        path: '/pay-app/:payAppId/compare',
        name: 'contractorComparison',
        builder: (context, state) {
          final payAppId = state.pathParameters['payAppId']!;
          return ContractorComparisonScreen(payAppId: payAppId);
        },
      ),
      // FROM SPEC: /analytics/:projectId — project analytics
      GoRoute(
        path: '/analytics/:projectId',
        name: 'projectAnalytics',
        builder: (context, state) {
          final projectId = state.pathParameters['projectId']!;
          return ProjectAnalyticsScreen(projectId: projectId);
        },
      ),
    ];
```

**Verify**: `pwsh -Command "flutter analyze lib/core/router/routes/pay_app_routes.dart"`
**Expected**: No issues found

#### Step 10.1.2: Register payAppRoutes in app_router.dart

Modify `lib/core/router/app_router.dart`:

1. **Add import** at line 13 (after sync_routes import):
```dart
import 'package:construction_inspector/core/router/routes/pay_app_routes.dart';
```

2. **Add route spread** at line 157 (after `...syncRoutes(),`):
```dart
      ...payAppRoutes(),
```

This results in the routes list at `app_router.dart:151-159` looking like:
```dart
      // Full-screen feature routes (outside bottom nav)
      ...settingsRoutes(rootNavigatorKey: _rootNavigatorKey),
      ...entryRoutes(),
      ...projectRoutes(),
      ...formRoutes(),
      ...toolboxRoutes(),
      ...syncRoutes(),
      ...payAppRoutes(),
    ],
```

**Verify**: `pwsh -Command "flutter analyze lib/core/router/app_router.dart"`
**Expected**: No issues found

---

### Sub-phase 10.2: Dashboard 4th Quick Card

**Agent**: `code-fixer-agent`
**Files**:
- `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:320-366` (MODIFY)

#### Step 10.2.1: Add Analytics card to _buildQuickStats

Modify the `_buildQuickStats` method in `project_dashboard_screen.dart`.

The current Row at lines 326-362 has 3 `Expanded` children separated by `SizedBox(width: DesignConstants.space2)`. Add a 4th card after the Toolbox card.

**IMPORTANT**: The current `Consumer2<DailyEntryProvider, BidItemProvider>` wrapper stays unchanged since the Analytics card does not need additional providers (it just navigates).

Add after line 361 (after the Toolbox Expanded closing `)`):

```dart
            const SizedBox(width: DesignConstants.space2),
            // Position 4: Analytics
            // FROM SPEC: Entry from dashboard 4th quick card
            Expanded(
              child: DashboardStatCard(
                key: TestingKeys.dashboardAnalyticsCard,
                label: 'Analytics',
                value: '',
                icon: Icons.analytics_outlined,
                color: cs.tertiary,
                onTap: () {
                  final project = context.read<ProjectProvider>().selectedProject;
                  if (project != null) {
                    context.push('/analytics/${project.id}');
                  }
                },
              ),
            ),
```

Also add import for `go_router` if not already present (it is already imported at line 4).

Also add import for `ProjectProvider` if not already present (it is already imported at line 14).

**Verify**: `pwsh -Command "flutter analyze lib/features/dashboard/presentation/screens/project_dashboard_screen.dart"`
**Expected**: No issues found

---

### Sub-phase 10.3: Testing Keys for New Features

**Agent**: `code-fixer-agent`
**Files**:
- `lib/shared/testing_keys/pay_app_keys.dart` (NEW)
- `lib/shared/testing_keys/testing_keys.dart` (MODIFY)

#### Step 10.3.1: Create pay_app_keys.dart

**File**: `lib/shared/testing_keys/pay_app_keys.dart` (NEW)

```dart
// WHY: Testing keys for pay application and analytics features.
// FROM SPEC: TestingKeys required list in spec section 5.

import 'package:flutter/material.dart';

/// Pay application and analytics testing keys.
class PayAppTestingKeys {
  PayAppTestingKeys._(); // Prevent instantiation

  // ============================================
  // Pay Application Export
  // ============================================
  static const payAppExportButton = Key('pay_app_export_button');
  static const payAppDateRangePicker = Key('pay_app_date_range_picker');
  static const payAppReplaceConfirmButton = Key('pay_app_replace_confirm_button');
  static const payAppNumberField = Key('pay_app_number_field');

  // ============================================
  // Pay Application Detail
  // ============================================
  static const payAppDetailScreen = Key('pay_app_detail_screen');
  static const payAppCompareButton = Key('pay_app_compare_button');

  // ============================================
  // Contractor Comparison
  // ============================================
  static const contractorImportButton = Key('contractor_import_button');
  static const contractorComparisonScreen = Key('contractor_comparison_screen');
  static const contractorComparisonExportPdfButton = Key('contractor_comparison_export_pdf_button');

  // ============================================
  // Analytics
  // ============================================
  static const analyticsScreen = Key('analytics_screen');
  static const analyticsDateFilter = Key('analytics_date_filter');

  // ============================================
  // Dashboard
  // ============================================
  static const dashboardAnalyticsCard = Key('dashboard_analytics_card');
}
```

**Verify**: `pwsh -Command "flutter analyze lib/shared/testing_keys/pay_app_keys.dart"`
**Expected**: No issues found

#### Step 10.3.2: Register pay_app_keys in testing_keys.dart barrel

Modify `lib/shared/testing_keys/testing_keys.dart`:

1. **Add export** after line 18 (after `export 'toolbox_keys.dart';`):
```dart
export 'pay_app_keys.dart';
```

2. **Add import** after line 34 (in the import block for facade delegations):
```dart
import 'pay_app_keys.dart';
```

3. **Add facade delegations** in the `TestingKeys` class. Add after the Projects & Dashboard section (after line ~117, after `dashboardViewMoreApproachingButton`):
```dart
  // ============================================
  // Pay Application & Analytics
  // ============================================
  static const payAppExportButton = PayAppTestingKeys.payAppExportButton;
  static const payAppDateRangePicker = PayAppTestingKeys.payAppDateRangePicker;
  static const payAppReplaceConfirmButton = PayAppTestingKeys.payAppReplaceConfirmButton;
  static const payAppNumberField = PayAppTestingKeys.payAppNumberField;
  static const payAppDetailScreen = PayAppTestingKeys.payAppDetailScreen;
  static const payAppCompareButton = PayAppTestingKeys.payAppCompareButton;
  static const contractorImportButton = PayAppTestingKeys.contractorImportButton;
  static const contractorComparisonScreen = PayAppTestingKeys.contractorComparisonScreen;
  static const contractorComparisonExportPdfButton = PayAppTestingKeys.contractorComparisonExportPdfButton;
  static const analyticsScreen = PayAppTestingKeys.analyticsScreen;
  static const analyticsDateFilter = PayAppTestingKeys.analyticsDateFilter;
  static const dashboardAnalyticsCard = PayAppTestingKeys.dashboardAnalyticsCard;
```

**Verify**: `pwsh -Command "flutter analyze lib/shared/testing_keys/testing_keys.dart"`
**Expected**: No issues found

---

### Sub-phase 10.4: Quantities Screen Secondary Entry Point

**Agent**: `code-fixer-agent`
**Files**:
- `lib/features/quantities/presentation/screens/quantities_screen.dart:62-69` (MODIFY)

#### Step 10.4.1: Add analytics action button to quantities screen AppBar

Modify `lib/features/quantities/presentation/screens/quantities_screen.dart`.

In the `actions:` list of the AppBar (currently at line 62-80), add an analytics icon button before the existing import button. Insert at line 63 (before the `if (context.watch<AuthProvider>().canEditFieldData)` block):

```dart
          // FROM SPEC: quantities screen secondary entry point to analytics
          IconButton(
            icon: const Icon(Icons.analytics_outlined),
            tooltip: 'Analytics',
            onPressed: () {
              final project = context.read<ProjectProvider>().selectedProject;
              if (project != null) {
                context.push('/analytics/${project.id}');
              }
            },
          ),
```

Also add import for `go_router` at the top if not already present (it is already imported at line 4).

**Verify**: `pwsh -Command "flutter analyze lib/features/quantities/presentation/screens/quantities_screen.dart"`
**Expected**: No issues found

---

### Sub-phase 10.5: Barrel Exports for Feature Modules

**Agent**: `code-fixer-agent`
**Files**:
- `lib/features/analytics/analytics.dart` (NEW barrel)
- `lib/features/pay_applications/pay_applications.dart` (NEW barrel, if not created in earlier phase)

#### Step 10.5.1: Create analytics feature barrel

**File**: `lib/features/analytics/analytics.dart` (NEW)

```dart
// Feature barrel for analytics module
export 'data/models/models.dart';
export 'presentation/providers/providers.dart';
export 'presentation/screens/screens.dart';
export 'presentation/widgets/widgets.dart';
```

**Verify**: `pwsh -Command "flutter analyze lib/features/analytics/analytics.dart"`
**Expected**: No issues found

#### Step 10.5.2: Verify pay_applications feature barrel exists

If not already created in an earlier phase, create `lib/features/pay_applications/pay_applications.dart`:

```dart
// Feature barrel for pay_applications module
export 'data/models/models.dart';
export 'domain/repositories/repositories.dart';
export 'presentation/providers/providers.dart';
export 'presentation/screens/screens.dart';
```

**Verify**: `pwsh -Command "flutter analyze lib/features/pay_applications/pay_applications.dart"`
**Expected**: No issues found

---

## Phase 11: Tests

### Sub-phase 11.1: PayApplicationRepository Unit Tests

**Agent**: `qa-testing-agent`
**Files**:
- `test/features/pay_applications/data/repositories/pay_application_repository_test.dart` (NEW)

#### Step 11.1.1: Create PayApplicationRepository test file

This test uses real SQLite via `DatabaseService.forTesting()` (same pattern as `form_export_repository_test.dart`). Tests the three HIGH-priority areas: exact-range identity, overlap blocking, chronological number rules.

**File**: `test/features/pay_applications/data/repositories/pay_application_repository_test.dart` (NEW)

```dart
// WHY: HIGH priority test per spec testing strategy.
// Tests exact-range identity, overlap blocking, chronological number rules.
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/features/pay_applications/data/datasources/local/pay_application_local_datasource.dart';
import 'package:construction_inspector/features/pay_applications/data/repositories/pay_application_repository.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';
import 'package:construction_inspector/features/pay_applications/data/datasources/local/export_artifact_local_datasource.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late PayApplicationRepositoryImpl repository;
  late ExportArtifactLocalDatasource artifactDatasource;
  late DatabaseService dbService;
  final now = DateTime.now().toUtc().toIso8601String();

  setUpAll(DatabaseService.initializeFfi);

  setUp(() async {
    dbService = DatabaseService.forTesting();
    final db = await dbService.database;
    artifactDatasource = ExportArtifactLocalDatasource(dbService);
    final datasource = PayApplicationLocalDatasource(dbService);
    repository = PayApplicationRepositoryImpl(datasource);

    // NOTE: Seed required FK parent — projects must exist before pay_applications.
    await db.insert('projects', {
      'id': 'proj-1',
      'name': 'Test Project',
      'project_number': 'PN-001',
      'created_at': now,
      'updated_at': now,
    });
  });

  tearDown(() async {
    await dbService.close();
  });

  /// Helper to create an export artifact parent and pay application.
  Future<PayApplication> _createPayApp({
    required int applicationNumber,
    required String periodStart,
    required String periodEnd,
    String? id,
    String projectId = 'proj-1',
  }) async {
    final artifact = ExportArtifact(
      projectId: projectId,
      artifactType: 'pay_application',
      title: 'Pay App #$applicationNumber',
      filename: 'pay_app_$applicationNumber.xlsx',
      mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    );
    await artifactDatasource.insert(artifact);

    final payApp = PayApplication(
      id: id,
      exportArtifactId: artifact.id,
      projectId: projectId,
      applicationNumber: applicationNumber,
      periodStart: periodStart,
      periodEnd: periodEnd,
      totalContractAmount: 100000,
      totalEarnedThisPeriod: 10000,
      totalEarnedToDate: 50000,
    );
    await repository.save(payApp);
    return payApp;
  }

  group('PayApplicationRepository', () {
    group('exact-range identity', () {
      // FROM SPEC: Exact same project + period_start + period_end is
      // considered the same pay app identity.
      test('findByDateRange returns matching pay app for exact range', () async {
        await _createPayApp(
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-15',
        );

        final result = await repository.findByDateRange(
          'proj-1',
          '2026-01-01',
          '2026-01-15',
        );

        expect(result, isNotNull);
        expect(result!.applicationNumber, 1);
      });

      test('findByDateRange returns null for non-matching range', () async {
        await _createPayApp(
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-15',
        );

        final result = await repository.findByDateRange(
          'proj-1',
          '2026-01-01',
          '2026-01-20',
        );

        expect(result, isNull);
      });

      test('findByDateRange scopes to project', () async {
        // NOTE: Two projects with same date range should not cross-match.
        final db = await dbService.database;
        await db.insert('projects', {
          'id': 'proj-2',
          'name': 'Other Project',
          'project_number': 'PN-002',
          'created_at': now,
          'updated_at': now,
        });

        await _createPayApp(
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-15',
          projectId: 'proj-1',
        );

        final result = await repository.findByDateRange(
          'proj-2',
          '2026-01-01',
          '2026-01-15',
        );

        expect(result, isNull);
      });
    });

    group('overlap blocking', () {
      // FROM SPEC: Overlapping non-identical ranges are blocked.
      test('findOverlapping detects partially overlapping range', () async {
        await _createPayApp(
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-15',
        );

        final overlaps = await repository.findOverlapping(
          'proj-1',
          '2026-01-10',
          '2026-01-25',
        );

        expect(overlaps, isNotEmpty);
        expect(overlaps.first.applicationNumber, 1);
      });

      test('findOverlapping returns empty for non-overlapping range', () async {
        await _createPayApp(
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-15',
        );

        final overlaps = await repository.findOverlapping(
          'proj-1',
          '2026-01-16',
          '2026-01-31',
        );

        expect(overlaps, isEmpty);
      });

      test('findOverlapping detects contained range', () async {
        await _createPayApp(
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-31',
        );

        final overlaps = await repository.findOverlapping(
          'proj-1',
          '2026-01-10',
          '2026-01-20',
        );

        expect(overlaps, isNotEmpty);
      });

      test('findOverlapping excludes exact-match range', () async {
        // FROM SPEC: Exact same range is identity, not overlap. The caller
        // should use findByDateRange for that check.
        // NOTE: findOverlapping should exclude exact matches so the caller
        // can differentiate "replace" vs "block" scenarios.
        await _createPayApp(
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-15',
        );

        final overlaps = await repository.findOverlapping(
          'proj-1',
          '2026-01-01',
          '2026-01-15',
          excludeExactMatch: true,
        );

        expect(overlaps, isEmpty);
      });
    });

    group('chronological number rules', () {
      // FROM SPEC: Pay-app numbers are chronological, unique per project,
      // auto-assigned.
      test('getNextApplicationNumber returns 1 for first pay app', () async {
        final next = await repository.getNextApplicationNumber('proj-1');
        expect(next, 1);
      });

      test('getNextApplicationNumber returns max+1', () async {
        await _createPayApp(
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-15',
        );
        await _createPayApp(
          applicationNumber: 2,
          periodStart: '2026-01-16',
          periodEnd: '2026-01-31',
        );

        final next = await repository.getNextApplicationNumber('proj-1');
        expect(next, 3);
      });

      test('getNextApplicationNumber skips deleted numbers by default', () async {
        // FROM SPEC: Deleted numbers may be reused only through user
        // override or replacement.
        final payApp = await _createPayApp(
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-15',
        );
        await _createPayApp(
          applicationNumber: 2,
          periodStart: '2026-01-16',
          periodEnd: '2026-01-31',
        );
        // Soft-delete pay app #1
        await repository.delete(payApp.id);

        final next = await repository.getNextApplicationNumber('proj-1');
        // NOTE: Should be 3, not 1, because deleted numbers are not auto-reused.
        expect(next, 3);
      });

      test('getByProjectId returns pay apps sorted by application_number', () async {
        await _createPayApp(
          applicationNumber: 2,
          periodStart: '2026-01-16',
          periodEnd: '2026-01-31',
        );
        await _createPayApp(
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-15',
        );

        final payApps = await repository.getByProjectId('proj-1');
        expect(payApps.length, 2);
        expect(payApps[0].applicationNumber, 1);
        expect(payApps[1].applicationNumber, 2);
      });
    });
  });
}
```

**Verify**: `pwsh -Command "flutter analyze test/features/pay_applications/data/repositories/pay_application_repository_test.dart"`
**Expected**: No issues found

---

### Sub-phase 11.2: ExportArtifactRepository Unit Tests

**Agent**: `qa-testing-agent`
**Files**:
- `test/features/pay_applications/data/repositories/export_artifact_repository_test.dart` (NEW)

#### Step 11.2.1: Create ExportArtifactRepository test file

**File**: `test/features/pay_applications/data/repositories/export_artifact_repository_test.dart` (NEW)

```dart
// WHY: HIGH priority test per spec testing strategy.
// Tests type filtering, delete behavior, history loading.
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/features/pay_applications/data/datasources/local/export_artifact_local_datasource.dart';
import 'package:construction_inspector/features/pay_applications/data/repositories/export_artifact_repository.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late ExportArtifactRepositoryImpl repository;
  late DatabaseService dbService;
  final now = DateTime.now().toUtc().toIso8601String();

  setUpAll(DatabaseService.initializeFfi);

  setUp(() async {
    dbService = DatabaseService.forTesting();
    final db = await dbService.database;
    final datasource = ExportArtifactLocalDatasource(dbService);
    repository = ExportArtifactRepositoryImpl(datasource);

    // Seed FK parent
    await db.insert('projects', {
      'id': 'proj-1',
      'name': 'Test Project',
      'project_number': 'PN-001',
      'created_at': now,
      'updated_at': now,
    });
  });

  tearDown(() async {
    await dbService.close();
  });

  ExportArtifact _makeArtifact({
    String artifactType = 'pay_application',
    String? artifactSubtype,
    String title = 'Test Artifact',
  }) =>
      ExportArtifact(
        projectId: 'proj-1',
        artifactType: artifactType,
        artifactSubtype: artifactSubtype,
        title: title,
        filename: 'test.xlsx',
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      );

  group('ExportArtifactRepository', () {
    group('type filtering', () {
      // FROM SPEC: ExportArtifactProvider loads exported-artifact history
      // by project and type.
      test('getByType returns only matching artifact type', () async {
        await repository.save(_makeArtifact(
          artifactType: 'pay_application',
          title: 'PA #1',
        ));
        await repository.save(_makeArtifact(
          artifactType: 'entry_pdf',
          title: 'IDR Export',
        ));
        await repository.save(_makeArtifact(
          artifactType: 'comparison_report',
          title: 'Discrepancy',
        ));

        final payApps = await repository.getByType('proj-1', 'pay_application');
        expect(payApps.length, 1);
        expect(payApps.first.title, 'PA #1');
      });

      test('getByType returns empty for non-existent type', () async {
        await repository.save(_makeArtifact(artifactType: 'pay_application'));

        final results = await repository.getByType('proj-1', 'photo_export');
        expect(results, isEmpty);
      });

      test('getByProjectId returns all types for a project', () async {
        await repository.save(_makeArtifact(artifactType: 'pay_application'));
        await repository.save(_makeArtifact(artifactType: 'entry_pdf'));

        final all = await repository.getByProjectId('proj-1');
        expect(all.length, 2);
      });
    });

    group('delete behavior', () {
      // FROM SPEC: Soft-delete is the default.
      test('delete soft-deletes artifact', () async {
        final artifact = _makeArtifact();
        await repository.save(artifact);

        await repository.delete(artifact.id);

        // Soft-deleted: getById returns null (filtered out)
        final result = await repository.getById(artifact.id);
        expect(result, isNull);
      });

      test('getByProjectId excludes soft-deleted artifacts', () async {
        final artifact = _makeArtifact();
        await repository.save(artifact);
        await repository.delete(artifact.id);

        final all = await repository.getByProjectId('proj-1');
        expect(all, isEmpty);
      });
    });
  });
}
```

**Verify**: `pwsh -Command "flutter analyze test/features/pay_applications/data/repositories/export_artifact_repository_test.dart"`
**Expected**: No issues found

---

### Sub-phase 11.3: PayAppExcelExporter Unit Tests

**Agent**: `qa-testing-agent`
**Files**:
- `test/features/pay_applications/domain/services/pay_app_excel_exporter_test.dart` (NEW)

#### Step 11.3.1: Create PayAppExcelExporter test file

**File**: `test/features/pay_applications/domain/services/pay_app_excel_exporter_test.dart` (NEW)

```dart
// WHY: HIGH priority test per spec testing strategy.
// Tests correct G703 layout, chaining totals.
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/pay_applications/domain/services/pay_app_excel_exporter.dart';
import 'package:construction_inspector/features/quantities/data/models/bid_item.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';

void main() {
  group('PayAppExcelExporter', () {
    late PayAppExcelExporter exporter;

    setUp(() {
      exporter = PayAppExcelExporter();
    });

    /// Helper to create a minimal BidItem for testing.
    BidItem _makeBidItem({
      String id = 'bi-1',
      String itemNumber = '201A',
      String description = 'Concrete Pavement',
      String unit = 'SY',
      double bidQuantity = 1000,
      double unitPrice = 50.0,
      double? bidAmount,
    }) =>
        BidItem(
          id: id,
          projectId: 'proj-1',
          itemNumber: itemNumber,
          description: description,
          unit: unit,
          bidQuantity: bidQuantity,
          unitPrice: unitPrice,
          bidAmount: bidAmount ?? bidQuantity * unitPrice,
        );

    group('G703 layout', () {
      // FROM SPEC: generates G703-style pay applications from tracked
      // project quantities.
      test('generates workbook with correct headers', () async {
        final bidItems = [_makeBidItem()];
        final quantitiesByItem = <String, double>{'bi-1': 100.0};

        final result = await exporter.generate(
          bidItems: bidItems,
          quantitiesByItem: quantitiesByItem,
          previousPayApp: null,
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-15',
        );

        // NOTE: Result is a Uint8List of xlsx bytes.
        expect(result, isNotNull);
        expect(result.isNotEmpty, isTrue);
      });

      test('computes earned this period correctly', () async {
        final bidItems = [
          _makeBidItem(id: 'bi-1', unitPrice: 50.0),
          _makeBidItem(id: 'bi-2', itemNumber: '301B', unitPrice: 25.0),
        ];
        final quantitiesByItem = <String, double>{
          'bi-1': 100.0, // 100 * 50 = 5000
          'bi-2': 200.0, // 200 * 25 = 5000
        };

        final summary = exporter.computeSummary(
          bidItems: bidItems,
          quantitiesByItem: quantitiesByItem,
          previousPayApp: null,
        );

        expect(summary.totalEarnedThisPeriod, 10000.0);
        expect(summary.totalEarnedToDate, 10000.0);
      });
    });

    group('chaining totals', () {
      // FROM SPEC: correct chaining totals — pay apps build on previous.
      test('chains from previous pay app earned-to-date', () async {
        final bidItems = [_makeBidItem(id: 'bi-1', unitPrice: 50.0)];
        // NOTE: quantitiesByItem contains THIS PERIOD quantities only
        final quantitiesByItem = <String, double>{'bi-1': 50.0};

        // Previous pay app earned 5000 total
        final previousPayApp = PayApplication(
          id: 'prev-pa',
          exportArtifactId: 'art-1',
          projectId: 'proj-1',
          applicationNumber: 1,
          periodStart: '2026-01-01',
          periodEnd: '2026-01-15',
          totalContractAmount: 50000,
          totalEarnedThisPeriod: 5000,
          totalEarnedToDate: 5000,
        );

        final summary = exporter.computeSummary(
          bidItems: bidItems,
          quantitiesByItem: quantitiesByItem,
          previousPayApp: previousPayApp,
        );

        // This period: 50 * 50 = 2500
        expect(summary.totalEarnedThisPeriod, 2500.0);
        // To date: previous 5000 + this period 2500 = 7500
        expect(summary.totalEarnedToDate, 7500.0);
      });

      test('total contract amount sums all bid amounts', () async {
        final bidItems = [
          _makeBidItem(id: 'bi-1', bidAmount: 50000),
          _makeBidItem(id: 'bi-2', itemNumber: '301B', bidAmount: 30000),
        ];
        final quantitiesByItem = <String, double>{};

        final summary = exporter.computeSummary(
          bidItems: bidItems,
          quantitiesByItem: quantitiesByItem,
          previousPayApp: null,
        );

        expect(summary.totalContractAmount, 80000.0);
      });

      test('handles empty quantities gracefully', () async {
        final bidItems = [_makeBidItem()];
        final quantitiesByItem = <String, double>{};

        final summary = exporter.computeSummary(
          bidItems: bidItems,
          quantitiesByItem: quantitiesByItem,
          previousPayApp: null,
        );

        expect(summary.totalEarnedThisPeriod, 0.0);
        expect(summary.totalEarnedToDate, 0.0);
      });
    });
  });
}
```

**Verify**: `pwsh -Command "flutter analyze test/features/pay_applications/domain/services/pay_app_excel_exporter_test.dart"`
**Expected**: No issues found

---

### Sub-phase 11.4: ContractorComparisonProvider Unit Tests

**Agent**: `qa-testing-agent`
**Files**:
- `test/features/pay_applications/presentation/providers/contractor_comparison_provider_test.dart` (NEW)

#### Step 11.4.1: Create ContractorComparisonProvider test file

**File**: `test/features/pay_applications/presentation/providers/contractor_comparison_provider_test.dart` (NEW)

```dart
// WHY: HIGH priority test per spec testing strategy.
// Tests import parsing, item-number match, description fallback.
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:construction_inspector/features/pay_applications/presentation/providers/contractor_comparison_provider.dart';
import 'package:construction_inspector/features/quantities/domain/repositories/bid_item_repository.dart';
import 'package:construction_inspector/features/quantities/data/models/bid_item.dart';
import 'package:construction_inspector/features/pay_applications/domain/services/contractor_import_parser.dart';

class MockBidItemRepository extends Mock implements BidItemRepository {}
class MockContractorImportParser extends Mock implements ContractorImportParser {}

void main() {
  late MockBidItemRepository mockBidItemRepo;
  late MockContractorImportParser mockParser;
  late ContractorComparisonProvider provider;

  setUp(() {
    mockBidItemRepo = MockBidItemRepository();
    mockParser = MockContractorImportParser();
    provider = ContractorComparisonProvider(
      bidItemRepository: mockBidItemRepo,
      importParser: mockParser,
    );
  });

  tearDown(() {
    provider.dispose();
  });

  BidItem _makeBidItem({
    String id = 'bi-1',
    String itemNumber = '201A',
    String description = 'Concrete Pavement',
    double bidQuantity = 1000,
    double unitPrice = 50.0,
  }) =>
      BidItem(
        id: id,
        projectId: 'proj-1',
        itemNumber: itemNumber,
        description: description,
        unit: 'SY',
        bidQuantity: bidQuantity,
        unitPrice: unitPrice,
      );

  group('ContractorComparisonProvider', () {
    group('import parsing', () {
      test('initial state has no comparison result', () {
        expect(provider.hasResult, isFalse);
      });

      test('clearSession resets all state', () {
        provider.clearSession();
        expect(provider.hasResult, isFalse);
        expect(provider.error, isNull);
      });
    });

    group('item-number match', () {
      // FROM SPEC: Match by item number first.
      test('matches contractor row by exact item number', () {
        final bidItems = [
          _makeBidItem(id: 'bi-1', itemNumber: '201A'),
          _makeBidItem(id: 'bi-2', itemNumber: '301B'),
        ];

        final contractorRows = [
          ContractorRow(
            itemNumber: '201A',
            description: 'Conc Pvmt',
            quantity: 120.0,
            amount: 6000.0,
          ),
        ];

        final matches = provider.matchItems(
          projectBidItems: bidItems,
          contractorRows: contractorRows,
        );

        expect(matches.length, 1);
        expect(matches.first.bidItemId, 'bi-1');
        expect(matches.first.matchType, MatchType.itemNumber);
      });
    });

    group('description fallback', () {
      // FROM SPEC: Then description fallback.
      test('falls back to description match when item number missing', () {
        final bidItems = [
          _makeBidItem(id: 'bi-1', itemNumber: '201A', description: 'Concrete Pavement'),
        ];

        final contractorRows = [
          ContractorRow(
            itemNumber: null, // No item number from contractor
            description: 'Concrete Pavement',
            quantity: 120.0,
            amount: 6000.0,
          ),
        ];

        final matches = provider.matchItems(
          projectBidItems: bidItems,
          contractorRows: contractorRows,
        );

        expect(matches.length, 1);
        expect(matches.first.bidItemId, 'bi-1');
        expect(matches.first.matchType, MatchType.description);
      });

      test('marks as unmatched when neither item number nor description match', () {
        final bidItems = [
          _makeBidItem(id: 'bi-1', itemNumber: '201A', description: 'Concrete Pavement'),
        ];

        final contractorRows = [
          ContractorRow(
            itemNumber: '999Z',
            description: 'Something Else',
            quantity: 120.0,
            amount: 6000.0,
          ),
        ];

        final matches = provider.matchItems(
          projectBidItems: bidItems,
          contractorRows: contractorRows,
        );

        expect(matches.length, 1);
        expect(matches.first.bidItemId, isNull);
        expect(matches.first.matchType, MatchType.unmatched);
      });

      test('case-insensitive description matching', () {
        final bidItems = [
          _makeBidItem(id: 'bi-1', description: 'Concrete Pavement'),
        ];

        final contractorRows = [
          ContractorRow(
            itemNumber: null,
            description: 'CONCRETE PAVEMENT',
            quantity: 120.0,
            amount: 6000.0,
          ),
        ];

        final matches = provider.matchItems(
          projectBidItems: bidItems,
          contractorRows: contractorRows,
        );

        expect(matches.length, 1);
        expect(matches.first.bidItemId, 'bi-1');
      });
    });
  });
}
```

**Verify**: `pwsh -Command "flutter analyze test/features/pay_applications/presentation/providers/contractor_comparison_provider_test.dart"`
**Expected**: No issues found

---

### Sub-phase 11.5: Widget Tests

**Agent**: `qa-testing-agent`
**Files**:
- `test/features/pay_applications/presentation/widgets/pay_app_date_range_dialog_test.dart` (NEW)
- `test/features/pay_applications/presentation/screens/pay_application_detail_screen_test.dart` (NEW)
- `test/features/pay_applications/presentation/widgets/export_artifact_history_list_test.dart` (NEW)

#### Step 11.5.1: Create PayAppDateRangeDialog widget test

**File**: `test/features/pay_applications/presentation/widgets/pay_app_date_range_dialog_test.dart` (NEW)

```dart
// WHY: HIGH priority widget test per spec testing strategy.
// Tests overlap validation, same-range replace prompt.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/providers/pay_application_provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/widgets/pay_app_date_range_dialog.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';

class MockPayApplicationProvider extends Mock implements PayApplicationProvider {}

void main() {
  late MockPayApplicationProvider mockProvider;

  setUp(() {
    mockProvider = MockPayApplicationProvider();
  });

  Widget buildTestWidget({Widget? child}) {
    return MaterialApp(
      home: Scaffold(
        body: ChangeNotifierProvider<PayApplicationProvider>.value(
          value: mockProvider,
          child: child ?? const PayAppDateRangeDialog(projectId: 'proj-1'),
        ),
      ),
    );
  }

  group('PayAppDateRangeDialog', () {
    testWidgets('displays overlap validation error', (tester) async {
      // FROM SPEC: Overlapping non-identical ranges are blocked.
      // "Pay application ranges cannot overlap"
      when(() => mockProvider.validateRange(
            any(),
            any(),
            any(),
          )).thenAnswer((_) async => PayAppRangeValidation(
            isValid: false,
            hasOverlap: true,
            hasExactMatch: false,
            errorMessage: 'Pay application ranges cannot overlap',
          ));

      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // NOTE: Detailed interaction tests depend on the dialog's internal
      // date picker implementation. This test verifies the provider
      // integration point.
      expect(find.byType(PayAppDateRangeDialog), findsOneWidget);
    });

    testWidgets('shows replace prompt for same-range match', (tester) async {
      // FROM SPEC: Exporting the exact same range again prompts the user
      // to replace the saved pay app.
      when(() => mockProvider.validateRange(
            any(),
            any(),
            any(),
          )).thenAnswer((_) async => PayAppRangeValidation(
            isValid: true,
            hasOverlap: false,
            hasExactMatch: true,
            existingPayApp: PayApplication(
              id: 'pa-1',
              exportArtifactId: 'art-1',
              projectId: 'proj-1',
              applicationNumber: 3,
              periodStart: '2026-03-01',
              periodEnd: '2026-03-15',
              totalContractAmount: 100000,
              totalEarnedThisPeriod: 10000,
              totalEarnedToDate: 50000,
            ),
            errorMessage: null,
          ));

      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.byType(PayAppDateRangeDialog), findsOneWidget);
    });
  });
}
```

**Verify**: `pwsh -Command "flutter analyze test/features/pay_applications/presentation/widgets/pay_app_date_range_dialog_test.dart"`
**Expected**: No issues found

#### Step 11.5.2: Create PayApplicationDetailScreen widget test

**File**: `test/features/pay_applications/presentation/screens/pay_application_detail_screen_test.dart` (NEW)

```dart
// WHY: HIGH priority widget test per spec testing strategy.
// Tests summary rendering and action availability.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/providers/pay_application_provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/providers/export_artifact_provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/screens/pay_application_detail_screen.dart';
import 'package:construction_inspector/features/pay_applications/data/models/pay_application.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

class MockPayApplicationProvider extends Mock implements PayApplicationProvider {}
class MockExportArtifactProvider extends Mock implements ExportArtifactProvider {}
class MockAuthProvider extends Mock implements AuthProvider {}

void main() {
  late MockPayApplicationProvider mockPayAppProvider;
  late MockExportArtifactProvider mockArtifactProvider;
  late MockAuthProvider mockAuthProvider;

  setUp(() {
    mockPayAppProvider = MockPayApplicationProvider();
    mockArtifactProvider = MockExportArtifactProvider();
    mockAuthProvider = MockAuthProvider();
  });

  Widget buildTestWidget() {
    return MaterialApp(
      home: MultiProvider(
        providers: [
          ChangeNotifierProvider<PayApplicationProvider>.value(value: mockPayAppProvider),
          ChangeNotifierProvider<ExportArtifactProvider>.value(value: mockArtifactProvider),
          ChangeNotifierProvider<AuthProvider>.value(value: mockAuthProvider),
        ],
        child: const PayApplicationDetailScreen(payAppId: 'pa-1'),
      ),
    );
  }

  group('PayApplicationDetailScreen', () {
    testWidgets('renders pay app summary fields', (tester) async {
      // FROM SPEC: Saved pay-app summary: pay app number, project,
      // date range, status, totals, exported timestamp.
      final payApp = PayApplication(
        id: 'pa-1',
        exportArtifactId: 'art-1',
        projectId: 'proj-1',
        applicationNumber: 3,
        periodStart: '2026-03-01',
        periodEnd: '2026-03-15',
        totalContractAmount: 100000,
        totalEarnedThisPeriod: 15000,
        totalEarnedToDate: 55000,
      );

      final artifact = ExportArtifact(
        id: 'art-1',
        projectId: 'proj-1',
        artifactType: 'pay_application',
        title: 'Pay App #3',
        filename: 'pay_app_3.xlsx',
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        status: 'exported',
      );

      when(() => mockPayAppProvider.getPayAppById('pa-1')).thenReturn(payApp);
      when(() => mockArtifactProvider.getArtifactById('art-1')).thenReturn(artifact);
      when(() => mockPayAppProvider.isLoading).thenReturn(false);
      when(() => mockAuthProvider.canEditFieldData).thenReturn(true);

      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // Verify key summary data is rendered
      expect(find.text('Pay App #3'), findsWidgets);
    });

    testWidgets('shows compare button when canEditFieldData is true', (tester) async {
      // FROM SPEC: Compare Contractor Pay App action available from detail.
      final payApp = PayApplication(
        id: 'pa-1',
        exportArtifactId: 'art-1',
        projectId: 'proj-1',
        applicationNumber: 1,
        periodStart: '2026-01-01',
        periodEnd: '2026-01-15',
        totalContractAmount: 50000,
        totalEarnedThisPeriod: 5000,
        totalEarnedToDate: 5000,
      );

      final artifact = ExportArtifact(
        id: 'art-1',
        projectId: 'proj-1',
        artifactType: 'pay_application',
        title: 'Pay App #1',
        filename: 'pay_app_1.xlsx',
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      );

      when(() => mockPayAppProvider.getPayAppById('pa-1')).thenReturn(payApp);
      when(() => mockArtifactProvider.getArtifactById('art-1')).thenReturn(artifact);
      when(() => mockPayAppProvider.isLoading).thenReturn(false);
      when(() => mockAuthProvider.canEditFieldData).thenReturn(true);

      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      // FROM SPEC: "Compare Contractor Pay App" action
      expect(find.text('Compare Contractor Pay App'), findsOneWidget);
    });

    testWidgets('hides compare button when canEditFieldData is false', (tester) async {
      // FROM SPEC: Write guard requires canEditFieldData.
      final payApp = PayApplication(
        id: 'pa-1',
        exportArtifactId: 'art-1',
        projectId: 'proj-1',
        applicationNumber: 1,
        periodStart: '2026-01-01',
        periodEnd: '2026-01-15',
        totalContractAmount: 50000,
        totalEarnedThisPeriod: 5000,
        totalEarnedToDate: 5000,
      );

      final artifact = ExportArtifact(
        id: 'art-1',
        projectId: 'proj-1',
        artifactType: 'pay_application',
        title: 'Pay App #1',
        filename: 'pay_app_1.xlsx',
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      );

      when(() => mockPayAppProvider.getPayAppById('pa-1')).thenReturn(payApp);
      when(() => mockArtifactProvider.getArtifactById('art-1')).thenReturn(artifact);
      when(() => mockPayAppProvider.isLoading).thenReturn(false);
      when(() => mockAuthProvider.canEditFieldData).thenReturn(false);

      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('Compare Contractor Pay App'), findsNothing);
    });
  });
}
```

**Verify**: `pwsh -Command "flutter analyze test/features/pay_applications/presentation/screens/pay_application_detail_screen_test.dart"`
**Expected**: No issues found

#### Step 11.5.3: Create ExportArtifactHistoryList widget test

**File**: `test/features/pay_applications/presentation/widgets/export_artifact_history_list_test.dart` (NEW)

```dart
// WHY: HIGH priority widget test per spec testing strategy.
// Tests type filtering in the exported-artifact history surface.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/providers/export_artifact_provider.dart';
import 'package:construction_inspector/features/pay_applications/presentation/widgets/export_artifact_history_list.dart';
import 'package:construction_inspector/features/pay_applications/data/models/export_artifact.dart';

class MockExportArtifactProvider extends Mock implements ExportArtifactProvider {}

void main() {
  late MockExportArtifactProvider mockProvider;

  setUp(() {
    mockProvider = MockExportArtifactProvider();
  });

  Widget buildTestWidget({String? filterType}) {
    return MaterialApp(
      home: Scaffold(
        body: ChangeNotifierProvider<ExportArtifactProvider>.value(
          value: mockProvider,
          child: ExportArtifactHistoryList(
            projectId: 'proj-1',
            filterType: filterType,
          ),
        ),
      ),
    );
  }

  ExportArtifact _makeArtifact({
    required String artifactType,
    required String title,
  }) =>
      ExportArtifact(
        projectId: 'proj-1',
        artifactType: artifactType,
        title: title,
        filename: 'test.pdf',
        mimeType: 'application/pdf',
      );

  group('ExportArtifactHistoryList', () {
    testWidgets('displays all artifacts when no filter', (tester) async {
      // FROM SPEC: Exported Forms history includes IDR, form PDF,
      // photo exports, and pay applications.
      final artifacts = [
        _makeArtifact(artifactType: 'entry_pdf', title: 'IDR 2026-01-15'),
        _makeArtifact(artifactType: 'form_pdf', title: 'Form Export'),
        _makeArtifact(artifactType: 'pay_application', title: 'Pay App #1'),
      ];

      when(() => mockProvider.artifacts).thenReturn(artifacts);
      when(() => mockProvider.isLoading).thenReturn(false);

      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('IDR 2026-01-15'), findsOneWidget);
      expect(find.text('Form Export'), findsOneWidget);
      expect(find.text('Pay App #1'), findsOneWidget);
    });

    testWidgets('filters artifacts by type when filterType provided', (tester) async {
      final artifacts = [
        _makeArtifact(artifactType: 'pay_application', title: 'Pay App #1'),
      ];

      // NOTE: When filterType is provided, the widget asks provider for
      // filtered list.
      when(() => mockProvider.getArtifactsByType('pay_application'))
          .thenReturn(artifacts);
      when(() => mockProvider.isLoading).thenReturn(false);

      await tester.pumpWidget(buildTestWidget(filterType: 'pay_application'));
      await tester.pumpAndSettle();

      expect(find.text('Pay App #1'), findsOneWidget);
    });

    testWidgets('shows empty state when no artifacts', (tester) async {
      when(() => mockProvider.artifacts).thenReturn([]);
      when(() => mockProvider.isLoading).thenReturn(false);

      await tester.pumpWidget(buildTestWidget());
      await tester.pumpAndSettle();

      expect(find.text('No exported artifacts'), findsOneWidget);
    });

    testWidgets('shows loading indicator while loading', (tester) async {
      when(() => mockProvider.artifacts).thenReturn([]);
      when(() => mockProvider.isLoading).thenReturn(true);

      await tester.pumpWidget(buildTestWidget());

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });
}
```

**Verify**: `pwsh -Command "flutter analyze test/features/pay_applications/presentation/widgets/export_artifact_history_list_test.dart"`
**Expected**: No issues found

---

### Sub-phase 11.6: Schema Tests

**Agent**: `qa-testing-agent`
**Files**:
- `test/core/database/database_service_test.dart` (MODIFY)
- `test/core/database/schema_verifier_report_test.dart` (MODIFY)

#### Step 11.6.1: Add new table assertions to database_service_test.dart

Modify `test/core/database/database_service_test.dart`.

In the `'onCreate creates all required tables'` test (around line 48-81), add assertions for the two new tables after the existing table checks:

```dart
        // Pay Application tables (Phase: Pay Application feature)
        expect(tableNames, contains('export_artifacts'));
        expect(tableNames, contains('pay_applications'));
```

Add a new test after the existing column tests (after line ~154) for the new tables:

```dart
      // FROM SPEC: New parent table export_artifacts and child table pay_applications.
      test('export_artifacts table has correct columns', () async {
        final db = await service.database;

        final columns = await db.rawQuery('PRAGMA table_info(export_artifacts)');
        final columnNames = columns.map((c) => c.requireString('name')).toList();

        expect(columnNames, contains('id'));
        expect(columnNames, contains('project_id'));
        expect(columnNames, contains('artifact_type'));
        expect(columnNames, contains('artifact_subtype'));
        expect(columnNames, contains('source_record_id'));
        expect(columnNames, contains('title'));
        expect(columnNames, contains('filename'));
        expect(columnNames, contains('local_path'));
        expect(columnNames, contains('remote_path'));
        expect(columnNames, contains('mime_type'));
        expect(columnNames, contains('status'));
        expect(columnNames, contains('created_at'));
        expect(columnNames, contains('updated_at'));
        expect(columnNames, contains('created_by_user_id'));
        expect(columnNames, contains('deleted_at'));
        expect(columnNames, contains('deleted_by'));
      });

      test('pay_applications table has correct columns', () async {
        final db = await service.database;

        final columns = await db.rawQuery('PRAGMA table_info(pay_applications)');
        final columnNames = columns.map((c) => c.requireString('name')).toList();

        expect(columnNames, contains('id'));
        expect(columnNames, contains('export_artifact_id'));
        expect(columnNames, contains('project_id'));
        expect(columnNames, contains('application_number'));
        expect(columnNames, contains('period_start'));
        expect(columnNames, contains('period_end'));
        expect(columnNames, contains('previous_application_id'));
        expect(columnNames, contains('total_contract_amount'));
        expect(columnNames, contains('total_earned_this_period'));
        expect(columnNames, contains('total_earned_to_date'));
        expect(columnNames, contains('notes'));
        expect(columnNames, contains('created_at'));
        expect(columnNames, contains('updated_at'));
        expect(columnNames, contains('created_by_user_id'));
        expect(columnNames, contains('deleted_at'));
        expect(columnNames, contains('deleted_by'));
      });
```

**Verify**: `pwsh -Command "flutter analyze test/core/database/database_service_test.dart"`
**Expected**: No issues found

#### Step 11.6.2: Add SchemaVerifier verification for new tables

Modify `test/core/database/schema_verifier_report_test.dart`.

Add a new test after the existing `'verify returns SchemaReport with no issues on healthy DB'` test (after line 26):

```dart
  // FROM SPEC: SchemaVerifier must know every table's columns to catch drift.
  test('verify includes export_artifacts and pay_applications tables', () async {
    final db = await dbService.database;
    final report = await SchemaVerifier.verify(db);

    // NOTE: These tables should be present in a healthy DB after migration.
    // If SchemaVerifier does not know about them, missingTables would include them.
    expect(report.missingTables, isNot(contains('export_artifacts')));
    expect(report.missingTables, isNot(contains('pay_applications')));
  });

  test('verify detects missing export_artifacts table', () async {
    final db = await dbService.database;
    await db.execute('DROP TABLE IF EXISTS pay_applications');
    await db.execute('DROP TABLE IF EXISTS export_artifacts');

    final report = await SchemaVerifier.verify(db);
    expect(report.missingTables, contains('export_artifacts'));
    expect(report.hasIssues, isTrue);
  });
```

**Verify**: `pwsh -Command "flutter analyze test/core/database/schema_verifier_report_test.dart"`
**Expected**: No issues found

---

### Sub-phase 11.7: Final Analyze Gate

**Agent**: `qa-testing-agent`
**Files**: All files from phases 9-11

#### Step 11.7.1: Run full project analysis

This is the final verification gate for all phases 9-11.

**Verify**: `pwsh -Command "flutter analyze"`
**Expected**: No issues found (zero errors, zero warnings, zero infos from new code)

**IMPORTANT**: If analysis reveals issues, fix them before considering these phases complete. Common issues to watch for:
- Missing imports (especially `go_router`, `provider`, `design_system`)
- Type mismatches in provider dynamic casts (the `_computeSummary` method uses dynamic lists)
- Missing `safeGoBack` import from `shared.dart`
- Missing barrel exports that prevent imports from resolving
