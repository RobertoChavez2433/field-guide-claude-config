---
paths:
  - "lib/presentation/**/*.dart"
  - "lib/core/theme/**/*.dart"
  - "lib/core/router/**/*.dart"
---

# Frontend Guidelines

## Common Commands
```bash
flutter run -d windows          # Run on Windows
flutter run                     # Run on connected device
flutter analyze                 # Check for issues
flutter test test/presentation/ # Test UI
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
