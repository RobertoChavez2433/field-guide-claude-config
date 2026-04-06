# Pattern: Provider (State Management)

## How We Do It
Providers extend `ChangeNotifier` (optionally with `SafeAction` mixin). They hold private state fields with public getters, use `notifyListeners()` after mutations, and expose async action methods. For project-scoped list management, extend `BaseListProvider<T, R>`. For custom providers, extend `ChangeNotifier with SafeAction` directly. Providers live in `lib/features/<feature>/presentation/providers/`.

## Exemplars

### EntryQuantityProvider (`lib/features/quantities/presentation/providers/entry_quantity_provider.dart`)
Custom ChangeNotifier with SafeAction — not using BaseListProvider because quantities are entry-scoped, not project-scoped.

```dart
class EntryQuantityProvider extends ChangeNotifier with SafeAction {
  final EntryQuantityRepository _repository;
  EntryQuantityProvider(this._repository);

  // SafeAction accessors
  @override bool get safeActionIsLoading => _isLoading;
  @override set safeActionIsLoading(bool value) => _isLoading = value;
  @override String? get safeActionError => _error;
  @override set safeActionError(String? value) => _error = value;
  @override String get safeActionLogTag => 'EntryQuantityProvider';

  // State
  List<EntryQuantity> _quantities = [];
  bool _isLoading = false;
  String? _error;

  // Actions
  Future<void> loadQuantitiesForEntry(String entryId) async {
    await runSafeAction('load quantities', () async {
      _quantities = await _repository.getByEntryId(entryId);
    }, buildErrorMessage: (_) => 'Failed to load quantities.');
  }
}
```

### EntryExportProvider (`lib/features/entries/presentation/providers/entry_export_provider.dart`)
Simple ChangeNotifier without SafeAction — manual try/catch pattern.

```dart
class EntryExportProvider extends ChangeNotifier {
  final ExportEntryUseCase _exportEntryUseCase;
  bool _isExporting = false;
  String? _errorMessage;
  List<EntryExport> _exportHistory = [];
  bool _isLoadingHistory = false;

  Future<List<String>> exportAllFormsForEntry(String entryId, {String? currentUserId}) async {
    _isExporting = true; _errorMessage = null; notifyListeners();
    try {
      final paths = await _exportEntryUseCase.call(entryId, currentUserId: currentUserId);
      return paths;
    } on Exception catch (e) {
      _errorMessage = 'Export failed.';
      return [];
    } finally {
      _isExporting = false; notifyListeners();
    }
  }
}
```

## Reusable Methods (from SafeAction mixin)

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `runSafeAction` | `safe_action_mixin.dart` | `Future<bool> runSafeAction(String name, Future<void> Function() action, {String Function(Object)? buildErrorMessage})` | Wraps async ops with loading/error/notify |

## Reusable Methods (from BaseListProvider)

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `loadItems` | `base_list_provider.dart:100` | `Future<void> loadItems(String projectId)` | Load all items for project |
| `createItem` | `base_list_provider.dart:112` | `Future<bool> createItem(T item)` | Create with auto-notify |
| `updateItem` | `base_list_provider.dart:128` | `Future<bool> updateItem(T item)` | Update with auto-notify |
| `deleteItem` | `base_list_provider.dart:147` | `Future<bool> deleteItem(String id)` | Delete with auto-notify |
| `checkWritePermission` | `base_list_provider.dart:193` | `bool checkWritePermission(String action)` | Guard writes behind canEditFieldData |

## Imports
```dart
import 'package:flutter/foundation.dart'; // ChangeNotifier
import 'package:construction_inspector/shared/providers/safe_action_mixin.dart';
import 'package:construction_inspector/core/logging/logger.dart';
```
