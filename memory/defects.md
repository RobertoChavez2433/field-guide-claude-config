# Defects Log

Critical patterns to avoid. Archive: `defects-archive.md`

## Format
```
### Title
**Pattern**: What to avoid
**Prevention**: How to avoid
```

---

## Active Patterns

### Async Context Safety
**Pattern**: Using context after await without mounted check
**Prevention**: Always `if (!mounted) return;` before setState/context after await
**Example**:
```dart
await someAsyncOp();
if (!mounted) return;  // REQUIRED
context.read<Provider>();
```

### Async in dispose()
**Pattern**: Calling async methods in dispose() - context already deactivated
**Prevention**: Use `WidgetsBindingObserver.didChangeAppLifecycleState` for lifecycle saves

### Unsafe Collection Access
**Pattern**: .first on empty list, firstWhere without orElse
**Prevention**: Use `.where().firstOrNull` pattern
```dart
// BAD: throws on empty
items.first
items.firstWhere((e) => e.id == id)

// GOOD: returns null safely
items.where((e) => e.id == id).firstOrNull
```

### Supabase Instance Access
**Pattern**: Accessing Supabase.instance without checking configuration
**Prevention**: Always check `SupabaseConfig.isConfigured` first
```dart
final user = SupabaseConfig.isConfigured
    ? Supabase.instance.client.auth.currentUser
    : null;
```

### Test Delays
**Pattern**: Using hardcoded Future.delayed() in tests
**Prevention**: Use condition-based waits
```dart
// BAD
await Future.delayed(Duration(seconds: 2));

// GOOD
await $.waitUntilVisible(finder);
```

### Rethrow in Callbacks
**Pattern**: Using `rethrow` in .catchError() or onError callbacks
**Prevention**: Use `throw error` in callbacks, `rethrow` only in catch blocks

---

<!-- Add new defects above this line -->
