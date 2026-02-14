---
feature: dashboard
type: architecture
scope: Project Home & Overview Aggregation
updated: 2026-02-13
---

# Dashboard Feature Architecture

## Data Model

Dashboard has **no persistent data model**. It is a read-only aggregation of data from other features. All displayed data is sourced from repositories of dependent features.

### Displayed Metrics (Calculated)

| Metric | Source | Calculation |
|--------|--------|-----------|
| **Entry Count** | entries repository | `listByProject(projectId).length` |
| **Complete Entries** | entries repository | `listByProject().where(status == complete).length` |
| **Pending Photos** | photos repository | `listByProject().where(syncStatus == pending).length` |
| **Bid Items** | quantities repository | `listByProject().length` |
| **Quantities Tracked** | quantities repository | `listByProject().where(quantityCompleted != null).length` |
| **Active Contractors** | contractors repository | `listByProject().length` |
| **Budget Used** | quantities repository | Sum of (quantityCompleted × unitPrice) |
| **Budget Remaining** | quantities repository | Sum of (quantity - quantityCompleted) × unitPrice |

## Relationships

Dashboard is a **read-only aggregation**:

```
DashboardScreen
    ├─→ Reads: Project (current context)
    ├─→ Reads: DailyEntry[] (for entry count, status, recent activity)
    ├─→ Reads: Photo[] (for photo count, sync status)
    ├─→ Reads: BidItem[] & EntryQuantity[] (for budget, quantities)
    ├─→ Reads: Contractor[] (for contractor count, equipment list)
    └─→ Reads: Weather (placeholder; for location conditions)

Display Components:
    ├─→ StatCard (Entry count, photo count, etc.)
    ├─→ BudgetOverviewCard (Budget used/remaining, bar chart)
    ├─→ TrackedItemRow (Recent entries, photos, activities)
    └─→ AlertItemRow (Warnings, overdue items, pending sync)
```

## Repository Pattern

Dashboard does **not have a repository**. Instead, it depends on repositories from other features:

```dart
class ProjectDashboardScreen extends StatefulWidget {
  @override
  State<ProjectDashboardScreen> createState() => _ProjectDashboardScreenState();
}

class _ProjectDashboardScreenState extends State<ProjectDashboardScreen> {
  // Dependencies injected via context.read<>()
  late DailyEntryRepository _entryRepository;
  late PhotoRepository _photoRepository;
  late QuantityRepository _quantityRepository;
  late ContractorRepository _contractorRepository;

  @override
  void initState() {
    super.initState();
    _entryRepository = context.read<DailyEntryRepository>();
    _photoRepository = context.read<PhotoRepository>();
    _quantityRepository = context.read<QuantityRepository>();
    _contractorRepository = context.read<ContractorRepository>();
    _loadDashboardData();
  }

  Future<void> _loadDashboardData() async {
    // Load data from multiple repositories
    final entries = await _entryRepository.listByProject(projectId);
    final photos = await _photoRepository.listByProject(projectId);
    final quantities = await _quantityRepository.listByProject(projectId);
    final contractors = await _contractorRepository.listByProject(projectId);

    // Calculate aggregates
    final entryCount = entries.length;
    final completeCount = entries.where((e) => e.status == EntryStatus.complete).length;
    final budgetUsed = _calculateBudgetUsed(quantities);

    setState(() {
      // Update UI with aggregates
    });
  }
}
```

## State Management

Dashboard is **presentation-only** with minimal state:

```dart
class ProjectDashboardScreen extends StatefulWidget {
  final String projectId;

  const ProjectDashboardScreen({required this.projectId});

  @override
  State<ProjectDashboardScreen> createState() => _ProjectDashboardScreenState();
}

class _ProjectDashboardScreenState extends State<ProjectDashboardScreen> {
  // Local state only
  bool _isLoading = false;
  String? _error;

  // Aggregated metrics (calculated once on load)
  int _entryCount = 0;
  int _completeEntries = 0;
  int _pendingPhotos = 0;
  double _budgetUsed = 0;
  List<DailyEntry> _recentEntries = [];
  List<Photo> _recentPhotos = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadDashboardData();
    });
  }

  Future<void> _loadDashboardData() async {
    setState(() => _isLoading = true);

    try {
      final entries = await context.read<DailyEntryRepository>().listByProject(widget.projectId);
      final photos = await context.read<PhotoRepository>().listByProject(widget.projectId);
      final quantities = await context.read<QuantityRepository>().listByProject(widget.projectId);

      setState(() {
        _entryCount = entries.length;
        _completeEntries = entries.where((e) => e.status == EntryStatus.complete).length;
        _pendingPhotos = photos.where((p) => p.syncStatus == SyncStatus.pending).length;
        _budgetUsed = _calculateBudgetUsed(quantities);
        _recentEntries = entries.take(5).toList();
        _recentPhotos = photos.take(5).toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Failed to load dashboard: $e';
        _isLoading = false;
      });
    }
  }

  // Metric calculations
  double _calculateBudgetUsed(List<BidItem> quantities) {
    double total = 0;
    for (final item in quantities) {
      if (item.quantityCompleted != null) {
        total += (item.quantityCompleted! * item.unitPrice);
      }
    }
    return total;
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    return Column(
      children: [
        // Header with project name
        ProjectHeaderWidget(projectId: widget.projectId),

        // Stat cards
        Row(
          children: [
            DashboardStatCard(label: 'Entries', value: '$_entryCount'),
            DashboardStatCard(label: 'Complete', value: '$_completeEntries'),
            DashboardStatCard(label: 'Photos', value: '$_pendingPhotos pending'),
          ],
        ),

        // Budget overview
        BudgetOverviewCard(
          budgetUsed: _budgetUsed,
          budgetTotal: _calculateBudgetTotal(),
        ),

        // Recent activities
        TrackedItemsList(
          entries: _recentEntries,
          photos: _recentPhotos,
        ),
      ],
    );
  }
}
```

### No Reactive Updates

Dashboard **does not use Provider pattern** for state management. It is a simple StatefulWidget that loads data once on init. This keeps the dashboard decoupled from other features' provider trees.

If real-time updates are needed (feature added in future), consider:
- Using `Consumer<DailyEntryProvider>()` to listen for entry changes
- Using `Consumer<PhotoProvider>()` to listen for photo changes
- Rebuilding aggregates when dependencies notify

## Offline Behavior

**Fully offline**: All dashboard data read from local SQLite. No network calls required. Aggregation and calculations happen locally. Cloud sync status shown (e.g., "5 photos pending sync"), but actual sync performed separately.

### Read Path (Offline)
- Query each repository (entries, photos, quantities, contractors)
- Calculate aggregates locally
- Display results without network

## Testing Strategy

### Widget Tests (Dashboard-level)
- **Layout**: Verify stat cards, budget card, recent items displayed
- **Data aggregation**: Mock repositories, verify metrics calculated correctly
- **Error handling**: Verify error message shown on load failure
- **Navigation**: Tap stat cards → navigate to respective feature screens

Location: `test/features/dashboard/presentation/screens/project_dashboard_screen_test.dart`

### Integration Tests
- **Full flow**: Navigate to project → dashboard loads → verify metrics match data
- **Cross-feature sync**: Create entry in entries feature → return to dashboard → verify count updated
- **Budget calculation**: Create quantities → update completion → dashboard budget updates

Location: `test/features/dashboard/presentation/integration/`

### Test Coverage
- ≥ 80% for dashboard screen (integration testing focus)
- Metric calculation functions: 100% (pure functions)

## Performance Considerations

### Target Response Times
- Dashboard load: < 500 ms (multiple queries)
- Metric calculation: < 100 ms (local processing)
- Screen render: < 300 ms (all data in memory)

### Memory Constraints
- Dashboard metrics: ~1-2 KB (all scalar values)
- Recent items cache: ~50-100 KB (5 recent entries + 5 photos)

### Optimization Opportunities
- Cache aggregates for 1 minute (user likely not interacting with other features)
- Lazy-load recent items (load only when viewing section)
- Batch queries in single transaction (reduce database round-trips)
- Pull-to-refresh to reload when stale

## File Locations

```
lib/features/dashboard/
├── presentation/
│   ├── screens/
│   │   ├── screens.dart
│   │   └── project_dashboard_screen.dart
│   │
│   └── widgets/
│       ├── widgets.dart
│       ├── dashboard_stat_card.dart
│       ├── budget_overview_card.dart
│       ├── tracked_item_row.dart
│       └── alert_item_row.dart
│
└── dashboard.dart                    # Feature entry point

lib/core/router/
└── app_router.dart                   # Dashboard route as shell/home
```

### Import Pattern

```dart
// Dashboard only uses repositories from other features
import 'package:construction_inspector/features/entries/data/repositories/daily_entry_repository.dart';
import 'package:construction_inspector/features/photos/data/repositories/photo_repository.dart';
import 'package:construction_inspector/features/quantities/data/repositories/quantity_repository.dart';
import 'package:construction_inspector/features/contractors/data/repositories/contractor_repository.dart';
```

