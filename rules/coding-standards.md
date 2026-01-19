# Coding Standards

## Model Pattern

All data models follow this structure (see `lib/data/models/project.dart`):

```dart
class Example {
  final String id;
  final String name;
  final DateTime createdAt;
  final DateTime updatedAt;

  Example({
    String? id,
    required this.name,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) : id = id ?? const Uuid().v4(),
       createdAt = createdAt ?? DateTime.now(),
       updatedAt = updatedAt ?? DateTime.now();

  Example copyWith({String? name}) => Example(
    id: id,
    name: name ?? this.name,
    createdAt: createdAt,
    updatedAt: DateTime.now(),
  );

  Map<String, dynamic> toMap() => { /* fields */ };
  factory Example.fromMap(Map<String, dynamic> map) => Example(/* fields */);
}
```

## Provider Loading Pattern

Always use `addPostFrameCallback` to load data after widget builds:

```dart
@override
void initState() {
  super.initState();
  WidgetsBinding.instance.addPostFrameCallback((_) {
    _loadData();
  });
}
```

## Async Context Safety

Check `mounted` before using context after async operations:

```dart
Future<void> _doSomething() async {
  await someAsyncOperation();
  if (!mounted) return;
  context.read<Provider>().doThing();
}
```

## Enum Serialization

```dart
// Serialize
'type': type.name

// Deserialize
type: ContractorType.values.byName(map['type'] as String)
```

## Navigation

```dart
// Push with parameters
context.pushNamed('report', pathParameters: {'entryId': entry.id});

// Go (replace)
context.goNamed('dashboard');

// Query parameters
context.pushNamed('entry', queryParameters: {'section': 'weather'});
```

## Theme Colors

Use `AppTheme` constants, not hardcoded colors:
- `AppTheme.textPrimary` (not `Colors.black87`)
- `AppTheme.textSecondary` (not `Colors.grey.shade600`)
- `AppTheme.primaryBlue`, `AppTheme.success`, `AppTheme.warning`, `AppTheme.error`

## Anti-Patterns to Avoid

1. **Don't** call `setState()` in `dispose()` - causes widget errors
2. **Don't** use `Provider.of(context)` after async - check `mounted` first
3. **Don't** hardcode colors - use theme
4. **Don't** skip barrel exports - always update `models.dart`, `providers.dart`
5. **Don't** use `firstWhere` without `orElse` - can throw
6. **Don't** save in `dispose()` - use `WidgetsBindingObserver` lifecycle

## File Organization

```
lib/
├── core/              # Router, theme, config, database
├── shared/            # Base classes, common utilities
├── features/          # Feature-first modules
│   └── [feature]/
│       ├── data/
│       │   ├── models/       # Entity classes
│       │   ├── repositories/ # Business logic
│       │   └── datasources/  # CRUD (local/ and remote/)
│       └── presentation/
│           ├── providers/    # State management
│           ├── screens/      # Full pages
│           └── widgets/      # Reusable components
├── data/              # LEGACY: Backward-compatible barrel re-exports
├── presentation/      # LEGACY: Backward-compatible barrel re-exports
└── services/          # Cross-cutting services
```

## Barrel Exports

**Feature barrels** (preferred):
- `lib/features/[feature]/data/data.dart`
- `lib/features/[feature]/presentation/presentation.dart`

**Legacy barrels** (backward-compat):
- `lib/data/models/models.dart`
- `lib/presentation/providers/providers.dart`
