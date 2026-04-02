# Pattern: Dashboard Widget

## How We Do It
Dashboard widgets live in `lib/features/dashboard/presentation/widgets/` and are exported via `widgets.dart` barrel. Each is a `StatelessWidget` that accepts data props and renders a themed card. Currently all use raw `Container` + `BoxDecoration` + `Text` with manual `TextStyle`. The migration target is `AppGlassCard` + `AppText.*` + `AppProgressBar`.

## Exemplars

### DashboardStatCard (lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart:6)
Animated stat card with `TweenAnimationBuilder` for scale/opacity entrance. Currently uses:
- Raw `Container` with gradient `BoxDecoration`
- `Text` with `tt.titleLarge!.copyWith(color: color, letterSpacing: -0.5)`
- `Text` with `tt.labelSmall!.copyWith(color: cs.onSurfaceVariant, letterSpacing: 0.3)`

Migration target:
- Replace `Container(decoration: ...)` with `AppGlassCard(child: ..., accentColor: color)`
- Replace `Text(value, style: tt.titleLarge!.copyWith(...))` with `AppText.titleLarge(value, color: color)`
- Replace `Text(label, style: tt.labelSmall!.copyWith(...))` with `AppText.labelSmall(label, color: cs.onSurfaceVariant)`
- Keep `TweenAnimationBuilder` wrapper as-is (animation is separate from card styling)

### TrackedItemRow (lib/features/dashboard/presentation/widgets/tracked_item_row.dart:8)
Shows bid item with usage percentage badge, progress bar, and quantity text. Currently uses:
- Raw `Container` with gradient `BoxDecoration`
- Raw `LinearProgressIndicator` (8px height)
- `Text` with manual `.copyWith` for 4 different text elements

Migration target:
- Replace outer `Container` with `AppGlassCard`
- Replace `LinearProgressIndicator` with `AppProgressBar(value: percentage)`
- Replace `Text` elements with `AppText.*` factories

### AlertItemRow (lib/features/dashboard/presentation/widgets/alert_item_row.dart:7)
Warning/error row for items approaching/exceeding budget. Currently:
- Raw `Container` with conditional color background
- No progress bar (should have one per spec)
- `Text` with manual `.copyWith`

Migration target:
- Replace `Container` with `AppGlassCard(accentColor: isOver90 ? cs.error : fg.statusWarning)`
- Add `AppProgressBar(value: percentage)`
- Replace `Text` with `AppText.*`

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `DashboardStatCard` constructor | `dashboard_stat_card.dart:13` | `const DashboardStatCard({label, value, icon, color, onTap?})` | Quick stats display |
| `BudgetOverviewCard` constructor | `budget_overview_card.dart:13` | `const BudgetOverviewCard({totalBudget, totalUsed, isLoading?})` | Budget summary card |
| `TrackedItemRow` constructor | `tracked_item_row.dart:13` | `const TrackedItemRow({item, usedQuantity, onTap?})` | Tracked bid item display |
| `AlertItemRow` constructor | `alert_item_row.dart:11` | `const AlertItemRow({item, percentage})` | Budget alert display |

## Imports
```dart
import 'package:construction_inspector/features/dashboard/presentation/widgets/widgets.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
```
