# Flutter Design Tokens

Mapping design system tokens to Flutter implementation.

## Color Tokens

### ThemeData ColorScheme

```dart
// Access via Theme.of(context).colorScheme
colorScheme.primary       // Primary brand color
colorScheme.onPrimary     // Text/icons on primary
colorScheme.secondary     // Secondary accent
colorScheme.onSecondary   // Text/icons on secondary
colorScheme.surface       // Card/sheet backgrounds
colorScheme.onSurface     // Text on surface
colorScheme.error         // Error states
colorScheme.onError       // Text on error
```

### AppTheme Custom Colors

Reference: `lib/core/theme/app_theme.dart`

```dart
// Project-specific colors
class AppTheme {
  // Primary palette
  static const primaryColor = Color(0xFF1976D2);
  static const primaryLight = Color(0xFF63A4FF);
  static const primaryDark = Color(0xFF004BA0);

  // Semantic colors
  static const successColor = Color(0xFF4CAF50);
  static const warningColor = Color(0xFFFFC107);
  static const errorColor = Color(0xFFF44336);

  // Construction domain
  static const safetyOrange = Color(0xFFFF6D00);
  static const concreteGray = Color(0xFF9E9E9E);
  static const blueprintBlue = Color(0xFF0D47A1);
}
```

### Usage Patterns

```dart
// GOOD: Use tokens
Container(
  color: Theme.of(context).colorScheme.surface,
  child: Text(
    'Title',
    style: TextStyle(color: Theme.of(context).colorScheme.onSurface),
  ),
)

// BAD: Hardcoded colors
Container(
  color: Colors.white,  // Won't adapt to dark mode
  child: Text(
    'Title',
    style: TextStyle(color: Colors.black),  // Won't adapt
  ),
)
```

## Typography Tokens

### Material 3 Text Theme

```dart
// Access via Theme.of(context).textTheme
textTheme.displayLarge   // 57sp - Hero text
textTheme.displayMedium  // 45sp
textTheme.displaySmall   // 36sp
textTheme.headlineLarge  // 32sp - Screen titles
textTheme.headlineMedium // 28sp
textTheme.headlineSmall  // 24sp
textTheme.titleLarge     // 22sp - Section headers
textTheme.titleMedium    // 16sp - Card titles
textTheme.titleSmall     // 14sp
textTheme.bodyLarge      // 16sp - Primary content
textTheme.bodyMedium     // 14sp - Secondary content
textTheme.bodySmall      // 12sp - Captions
textTheme.labelLarge     // 14sp - Buttons
textTheme.labelMedium    // 12sp - Labels
textTheme.labelSmall     // 11sp - Tags
```

### Usage Patterns

```dart
// GOOD: Use theme text styles
Text(
  'Screen Title',
  style: Theme.of(context).textTheme.headlineLarge,
)

// GOOD: Extend theme style
Text(
  'Bold Title',
  style: Theme.of(context).textTheme.titleLarge?.copyWith(
    fontWeight: FontWeight.bold,
  ),
)

// BAD: Inline text style
Text(
  'Screen Title',
  style: TextStyle(fontSize: 32, fontWeight: FontWeight.w400),
)
```

## Spacing Tokens

### Spacing Constants

```dart
// Define in lib/core/theme/spacing.dart
class Spacing {
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 16.0;
  static const double lg = 24.0;
  static const double xl = 32.0;
  static const double xxl = 48.0;
}
```

### Usage Patterns

```dart
// GOOD: Use spacing tokens
Padding(
  padding: EdgeInsets.all(Spacing.md),
  child: Column(
    children: [
      Text('Title'),
      SizedBox(height: Spacing.sm),
      Text('Subtitle'),
    ],
  ),
)

// BAD: Magic numbers
Padding(
  padding: EdgeInsets.all(16.0),  // What's 16? Why 16?
  child: Column(
    children: [
      Text('Title'),
      SizedBox(height: 8.0),  // Inconsistent spacing
      Text('Subtitle'),
    ],
  ),
)
```

## Component Tokens

### Buttons

```dart
// Primary button (filled)
ElevatedButton(
  style: ElevatedButton.styleFrom(
    backgroundColor: Theme.of(context).colorScheme.primary,
    foregroundColor: Theme.of(context).colorScheme.onPrimary,
    minimumSize: Size(88, 48),  // 48dp height for touch targets
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(8),
    ),
  ),
  onPressed: () {},
  child: Text('Primary Action'),
)

// Secondary button (outlined)
OutlinedButton(
  style: OutlinedButton.styleFrom(
    minimumSize: Size(88, 48),
    side: BorderSide(color: Theme.of(context).colorScheme.primary),
  ),
  onPressed: () {},
  child: Text('Secondary Action'),
)
```

### Cards

```dart
Card(
  elevation: 1,
  shape: RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(12),
  ),
  child: Padding(
    padding: EdgeInsets.all(Spacing.md),
    child: content,
  ),
)
```

### Input Fields

```dart
TextField(
  decoration: InputDecoration(
    labelText: 'Field Label',
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(8),
    ),
    contentPadding: EdgeInsets.symmetric(
      horizontal: Spacing.md,
      vertical: Spacing.md,
    ),
  ),
)
```

## Touch Target Standards

For field use with gloves:

```dart
// Minimum 48dp touch targets
const double kMinTouchTarget = 48.0;

// For primary actions, use larger
const double kLargeTouchTarget = 56.0;

// FAB size
const double kFabSize = 56.0;

// Example: Large button for field use
SizedBox(
  height: kLargeTouchTarget,
  width: double.infinity,
  child: ElevatedButton(
    onPressed: () {},
    child: Text('Save Entry'),
  ),
)
```

## Responsive Breakpoints

```dart
class Breakpoints {
  static const double mobile = 600;
  static const double tablet = 900;
  static const double desktop = 1200;
}

// Usage
Widget build(BuildContext context) {
  final width = MediaQuery.of(context).size.width;

  if (width < Breakpoints.mobile) {
    return MobileLayout();
  } else if (width < Breakpoints.tablet) {
    return TabletLayout();
  } else {
    return DesktopLayout();
  }
}
```
