---
paths:
  - "lib/features/**/presentation/**/*.dart"
  - "lib/core/theme/**/*.dart"
  - "lib/core/router/**/*.dart"
---

# Frontend Guidelines

## Common Commands
```bash
flutter run -d windows          # Run on Windows
flutter run                     # Run on connected device
flutter analyze                 # Check for issues
flutter test                    # Test all
```

## Code Style

### Screen Structure
```dart
class MyScreen extends StatefulWidget {
  @override
  State<MyScreen> createState() => _MyScreenState();
}

class _MyScreenState extends State<MyScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadData());
  }

  @override
  void dispose() {
    // Cleanup subscriptions, controllers
    super.dispose();
  }
}
```

### Theme Colors
Use `AppTheme` constants:
- `AppTheme.primaryBlue` - Primary brand
- `AppTheme.success/warning/error` - Semantic
- `AppTheme.textPrimary/Secondary` - Text
- NEVER hardcode Colors.* values

### Navigation
```dart
context.pushNamed('route', pathParameters: {'id': id});
context.goNamed('route');  // Replace
context.pop();             // Back
```

## State Management

### Provider Pattern
```dart
// Read once (actions)
context.read<MyProvider>().doAction();

// Watch for rebuilds
Consumer<MyProvider>(
  builder: (context, provider, child) => Widget(),
);
```

### Async Safety
```dart
await asyncOperation();
if (!mounted) return;  // ALWAYS check
context.read<Provider>().update();
```

## UI Guidelines

### Responsive Breakpoints
- Mobile: < 600px
- Tablet: 600-1200px
- Desktop: > 1200px

### Card-Based Lists
- Leading icon/avatar
- Title and subtitle
- Trailing action/status

### Forms
- Use Stepper for multi-step
- Validate before advancing
- Show loading during submit

## Error Handling
```dart
try {
  await operation();
} catch (e) {
  if (!mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Error: $e')),
  );
}
```

## Logging
```dart
debugPrint('INFO: $message');  // Development only
```

## Pull Request Template
```markdown
## UI Changes
- [ ] Screens affected:
- [ ] Theme colors used (no hardcoding)
- [ ] Responsive tested (mobile/tablet/desktop)
- [ ] Dark mode verified

## Testing
- [ ] Widget tests added
- [ ] Manual testing on target device
```

## Detailed UI Patterns

### Split View / Master-Detail Pattern

Used in Calendar screen for entry list + report preview:

```
┌─────────────────────────────────────────────────┐
│ [Calendar Header + Month View]                  │
├─────────────────────────────────────────────────┤
│ Entry List (180px)  │  Report Preview (flex)    │
│ ┌────────────────┐  │ ┌───────────────────────┐ │
│ │ ▶ Location A   │  │ │ Weather: Sunny        │ │
│ │   Draft        │  │ │ Activities: ...       │ │
│ │                │  │ │ Safety: ...           │ │
│ │   Location B   │  │ │ [Edit] buttons        │ │
│ │   Complete     │  │ │                       │ │
│ └────────────────┘  │ └───────────────────────┘ │
└─────────────────────────────────────────────────┘
```

Implementation pattern (Reference: `lib/features/entries/presentation/screens/home_screen.dart:395-410`):
- Track `_selectedEntryId` state for highlighting
- Left panel: Fixed-width `SizedBox` with `ListView.builder`
- Right panel: `Expanded` widget with scrollable content
- Selection state updates preview via `setState()`
- Edit buttons pass section identifier as query parameter

Reference: `lib/features/entries/presentation/screens/home_screen.dart:326-760`

### Form Organization (Detailed)

Multi-step forms use Flutter's `Stepper` widget with:
- Step validation before advancing
- Custom controls builder for navigation buttons
- Form state preserved across steps

Reference: `lib/features/entries/presentation/screens/entry_wizard_screen.dart:80-95`

### Theming Pattern

Centralized theme with brand colors. Reference: `lib/core/theme/app_theme.dart:1-95`

#### Color Naming

- Primary brand colors: `primaryBlue`, `secondaryBlue`
- Semantic colors: `success`, `warning`, `error`
- Domain-specific: `sunny`, `rainy`, `overcast` (weather tags)

#### Theme Usage

Access via `Theme.of(context)` or direct `AppTheme.primaryBlue` for custom widgets.

### Clickable Stat Cards Pattern

Dashboard stat cards use `InkWell` wrapper with `onTap` parameter:

```dart
Widget _buildStatCard(String label, String value, IconData icon, Color color, {VoidCallback? onTap}) {
  return Card(
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: // ... content
    ),
  );
}
```

Reference: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart:265-295`
