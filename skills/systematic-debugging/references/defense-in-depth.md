# Defense in Depth

Four-layer validation strategy to catch bugs before they escape.

## The Four Layers

### Layer 1: Static Analysis

Catch bugs at compile time.

```bash
# Flutter/Dart analysis
flutter analyze

# Auto-fix what's possible
dart fix --apply
```

**What It Catches**:
- Type mismatches
- Null safety violations
- Unused variables/imports
- Deprecated API usage
- Missing await keywords

**Action**: Run before every commit. Zero tolerance for analysis errors.

### Layer 2: Unit Tests

Catch logic bugs in isolation.

```bash
# All unit tests
flutter test test/

# Specific test file
flutter test test/data/models/project_test.dart
```

**What It Catches**:
- Model serialization errors
- Repository logic bugs
- Business rule violations
- Edge case handling

**Coverage Targets**:
- Models: 100% serialization coverage
- Repositories: Core CRUD operations
- Services: Happy path + error cases

### Layer 3: Widget/Integration Tests

Catch UI and interaction bugs.

```bash
# Widget tests
flutter test test/presentation/

# Integration tests
flutter test integration_test/
```

**What It Catches**:
- Widget rendering issues
- State management bugs
- Navigation problems
- Form validation errors

**Key Patterns**:
- `pumpWidget` for widget tests
- `pumpAndSettle` for animations
- Mock dependencies for isolation

### Layer 4: E2E Tests (Patrol)

Catch real-world user flow bugs.

```bash
# All E2E tests
patrol test

# Specific flow
patrol test -t integration_test/patrol/e2e_tests/entry_flow_test.dart
```

**What It Catches**:
- System permission handling
- Deep link flows
- Cross-screen state
- Native feature integration

**Key Patterns**:
- Use TestingKeys, never hardcoded keys
- waitFor conditions, never hardcoded delays
- Atomic test scenarios

## Layer Priority During Debug

When debugging, check layers in order:

```
1. Does it pass static analysis?
   NO -> Fix analysis errors first

2. Do unit tests pass?
   NO -> Bug is in business logic

3. Do widget tests pass?
   NO -> Bug is in UI layer

4. Do E2E tests pass?
   NO -> Bug is in integration/real-world flow
```

## Defensive Coding Patterns

### Null Safety Defense

```dart
// Layer 1: Type system
final String? maybeNull = getData();

// Layer 2: Explicit check
if (maybeNull == null) {
  return defaultValue;
}

// Layer 3: Assert in debug
assert(maybeNull.isNotEmpty, 'Expected non-empty string');
```

### Async Safety Defense

```dart
// Layer 1: Proper return type
Future<void> loadData() async {
  // Layer 2: Error handling
  try {
    await _repository.fetch();

    // Layer 3: Mounted check
    if (!mounted) return;

    setState(() { /* ... */ });
  } catch (e) {
    // Layer 4: Graceful degradation
    _handleError(e);
  }
}
```

### State Mutation Defense

```dart
// Layer 1: Immutable models
@immutable
class Project {
  final String id;
  final String name;

  // Layer 2: Copy method
  Project copyWith({String? name}) => Project(
    id: id,
    name: name ?? this.name,
  );
}

// Layer 3: Provider notification
void updateProject(String name) {
  _project = _project.copyWith(name: name);
  notifyListeners(); // Never forget!
}
```

## Regression Prevention

After fixing any bug:

1. **Add test** that would have caught it
2. **Add to _defects.md** if it's a pattern
3. **Consider** if other code has same bug
4. **Run full suite** to catch regressions
