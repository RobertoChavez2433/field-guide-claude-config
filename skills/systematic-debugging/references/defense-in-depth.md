# Defense in Depth

Five-layer validation strategy to catch bugs before they escape.

## The Five Layers

### Layer 1: Static Analysis

Catch bugs at compile time.

```bash
# Flutter/Dart analysis
pwsh -Command "flutter analyze"

# Auto-fix what's possible
pwsh -Command "dart fix --apply"
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
pwsh -Command "flutter test test/"
```

**What It Catches**:
- Model serialization errors
- Repository CRUD logic bugs
- Business rule violations
- Sync adapter mapping errors (16 adapters in `test/features/sync/adapters/`)
- Engine component errors (change_tracker, conflict_resolver, integrity_checker, sync_mutex)
- Schema/migration correctness (`test/features/sync/schema/`)
- Trigger behavior (`test/features/sync/triggers/`)

**Coverage Targets**:
- Models: 100% serialization coverage
- Adapters: 100% mapping coverage
- Engine components: Happy path + error paths

### Layer 3: Widget Tests

Catch UI and state management bugs.

```bash
# Widget tests
pwsh -Command "flutter test test/features/"
```

**What It Catches**:
- Provider state management bugs
- Screen rendering issues
- Form validation errors
- Navigation problems

**Key Patterns**:
- `pumpWidget` for widget tests
- `pumpAndSettle` for animations
- Mock dependencies for isolation (MockDatabase, mock repositories from `test/helpers/`)

### Layer 4: ADB-Based E2E Tests

Catch real-world user flow bugs.

- `/test` skill with flow registry
- UIAutomator element finding + Claude vision verification
- Logcat monitoring after every interaction
- Real device, real permissions, real network

**Key Patterns**:
- Use TestingKeys (per-feature key classes), never hardcoded strings
- Poll for conditions via ADB, never hardcoded delays
- Atomic test scenarios

### Layer 5: Sync/Data Integrity

Catch sync engine and data layer bugs.

- `PRAGMA foreign_key_check` -- FK integrity
- `change_log` inspection -- trigger coverage
- `change_log` status -- pending operations
- IntegrityChecker -- orphan detection, constraint validation
- SchemaVerifier -- migration correctness
- Adapter integration tests (`test/features/sync/engine/adapter_integration_test.dart`)

## Layer Priority During Debug

When debugging, check layers in order:

```
1. Does it pass static analysis?
   NO -> Fix analysis errors first

2. Do unit/adapter tests pass?
   NO -> Bug is in business logic or sync mapping

3. Do widget tests pass?
   NO -> Bug is in UI/state layer

4. Do E2E flows pass on device?
   NO -> Bug is in integration/real-world flow

5. Does data integrity hold after sync?
   NO -> Bug is in sync engine, triggers, or schema
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

### Sync Safety Defense

```dart
// Layer 1: Adapter validates before push
Map<String, dynamic> toSupabaseMap(Map<String, dynamic> row) {
  assert(row['id'] != null, 'Cannot sync row without id');
  return {...row}..remove('change_log_id');
}

// Layer 2: Engine checks FK order
// SyncRegistry enforces push order: projects -> locations -> daily_entries -> ...

// Layer 3: IntegrityChecker post-sync
await integrityChecker.checkOrphans(db);
```

## Regression Prevention

After fixing any bug:

1. **Add test** that would have caught it
2. **Add to _defects.md** if it's a pattern
3. **Consider** if other code has same bug
4. **Run full suite** to catch regressions
