# Part 4: Scaffolded Repository Method Wiring + Miscellaneous

> Phases 16-22 of the codebase cleanup. Wires data-layer methods through to providers/UI, plus miscellaneous fixes.

---

## Phase 16: Wire DailyEntry Methods to Provider/UI

### Sub-phase 16.1: Add Filtering Use Case

**Files:**
- Create: `lib/features/entries/domain/usecases/filter_entries_use_case.dart`
- Test: `test/features/entries/domain/usecases/filter_entries_use_case_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 16.1.1: Create FilterEntriesUseCase

Create `lib/features/entries/domain/usecases/filter_entries_use_case.dart`:

```dart
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
import 'package:construction_inspector/features/entries/domain/repositories/daily_entry_repository.dart';

/// WHY: Pass-through use case for entry filtering operations.
/// Keeps provider decoupled from repository interface details.
class FilterEntriesUseCase {
  final DailyEntryRepository _repository;

  FilterEntriesUseCase({required DailyEntryRepository repository})
      : _repository = repository;

  /// Filter entries by date range within a project.
  Future<List<DailyEntry>> byDateRange(
    String projectId,
    DateTime startDate,
    DateTime endDate,
  ) =>
      _repository.getByDateRange(projectId, startDate, endDate);

  /// Filter entries by location within a project.
  Future<List<DailyEntry>> byLocation(String locationId) =>
      _repository.getByLocationId(locationId);

  /// Filter entries by status within a project.
  Future<List<DailyEntry>> byStatus(String projectId, EntryStatus status) =>
      _repository.getByStatus(projectId, status);

  /// Update the status of a single entry.
  Future<void> updateStatus(String id, EntryStatus status) =>
      _repository.updateStatus(id, status);

  /// Get total entry count for a project.
  Future<int> countForProject(String projectId) =>
      _repository.getCountByProject(projectId);
}
```

#### Step 16.1.2: Write unit test

Create `test/features/entries/domain/usecases/filter_entries_use_case_test.dart` with mock repository tests verifying:
- `byDateRange` delegates to `repository.getByDateRange`
- `byLocation` delegates to `repository.getByLocationId`
- `byStatus` delegates to `repository.getByStatus`
- `updateStatus` delegates to `repository.updateStatus`
- `countForProject` delegates to `repository.getCountByProject`

#### Step 16.1.3: Verify

Run: `pwsh -Command "flutter test test/features/entries/domain/usecases/filter_entries_use_case_test.dart"`

### Sub-phase 16.2: Wire Filtering Methods to DailyEntryProvider

**Files:**
- Modify: `lib/features/entries/presentation/providers/daily_entry_provider.dart`
- Modify: `lib/main.dart` (add FilterEntriesUseCase to provider construction)
- Test: `test/features/entries/presentation/providers/daily_entry_provider_filter_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 16.2.1: Add FilterEntriesUseCase dependency to DailyEntryProvider

In `lib/features/entries/presentation/providers/daily_entry_provider.dart`:

1. Add import for `FilterEntriesUseCase`.
2. Add `final FilterEntriesUseCase _filterEntriesUseCase;` field.
3. Add to constructor: `required FilterEntriesUseCase filterEntriesUseCase,` and wire in initializer list.
4. Add filter state fields after line 57:

```dart
  // Filter state
  // WHY: Tracks active filter for the entry list view — enables UI to show
  // which filter is active and clear it.
  EntryFilterType? _activeFilter;
  List<DailyEntry> _filteredEntries = [];
  bool _filterLoading = false;

  EntryFilterType? get activeFilter => _activeFilter;
  List<DailyEntry> get filteredEntries => _filteredEntries;
  bool get filterLoading => _filterLoading;
```

5. Add filter enum above the class:

```dart
/// WHY: Typed filter categories for the entry list view.
enum EntryFilterType { dateRange, location, status }
```

6. Add methods after the `loadMoreEntries` method (after line 362):

```dart
  /// Filter entries by date range.
  /// WHY: Enables calendar range selection on HomeScreen.
  Future<void> filterByDateRange(
    String projectId,
    DateTime startDate,
    DateTime endDate,
  ) async {
    _filterLoading = true;
    _activeFilter = EntryFilterType.dateRange;
    notifyListeners();
    try {
      _filteredEntries = await _filterEntriesUseCase.byDateRange(
        projectId, startDate, endDate,
      );
    } catch (e) {
      Logger.ui('[DailyEntryProvider] filterByDateRange error: $e');
      _filteredEntries = [];
    } finally {
      _filterLoading = false;
      notifyListeners();
    }
  }

  /// Filter entries by location.
  /// WHY: Enables location-based filtering from the location picker.
  Future<void> filterByLocation(String locationId) async {
    _filterLoading = true;
    _activeFilter = EntryFilterType.location;
    notifyListeners();
    try {
      _filteredEntries = await _filterEntriesUseCase.byLocation(locationId);
    } catch (e) {
      Logger.ui('[DailyEntryProvider] filterByLocation error: $e');
      _filteredEntries = [];
    } finally {
      _filterLoading = false;
      notifyListeners();
    }
  }

  /// Filter entries by status.
  /// WHY: Enables draft/submitted toggle in the entry list.
  Future<void> filterByStatus(String projectId, EntryStatus status) async {
    _filterLoading = true;
    _activeFilter = EntryFilterType.status;
    notifyListeners();
    try {
      _filteredEntries = await _filterEntriesUseCase.byStatus(projectId, status);
    } catch (e) {
      Logger.ui('[DailyEntryProvider] filterByStatus error: $e');
      _filteredEntries = [];
    } finally {
      _filterLoading = false;
      notifyListeners();
    }
  }

  /// Clear any active filter, returning to the full entry list.
  void clearFilter() {
    _activeFilter = null;
    _filteredEntries = [];
    notifyListeners();
  }

  /// Get total entry count for a project (async from DB).
  /// WHY: Enables "X entries" display on project dashboard card.
  Future<int> getEntryCount(String projectId) async {
    try {
      return await _filterEntriesUseCase.countForProject(projectId);
    } catch (e) {
      Logger.ui('[DailyEntryProvider] getEntryCount error: $e');
      return 0;
    }
  }
```

7. Update `clear()` (line 502-513) to also reset filter state:

```dart
    _activeFilter = null;
    _filteredEntries = [];
    _filterLoading = false;
```

#### Step 16.2.2: Wire FilterEntriesUseCase in main.dart

In `lib/main.dart`, find where `DailyEntryProvider` is constructed and add `FilterEntriesUseCase` to the dependency injection. The use case takes `DailyEntryRepository` as its only dependency.

#### Step 16.2.3: Write provider tests

Test in `test/features/entries/presentation/providers/daily_entry_provider_filter_test.dart`:
- `filterByDateRange` sets `activeFilter`, populates `filteredEntries`, resets `filterLoading`
- `filterByLocation` sets `activeFilter` to `location`
- `filterByStatus` sets `activeFilter` to `status`
- `clearFilter` resets all filter state
- `getEntryCount` returns count from use case
- Error handling: each filter method catches exceptions, logs, returns empty list

#### Step 16.2.4: Verify

Run: `pwsh -Command "flutter test test/features/entries/presentation/providers/"`

---

## Phase 17: Wire Todo Methods to Provider/UI

### Sub-phase 17.1: Add Filter and Query Methods to TodoProvider

**Files:**
- Modify: `lib/features/todos/presentation/providers/todo_provider.dart`
- Test: `test/features/todos/presentation/providers/todo_provider_filter_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 17.1.1: Add repository-backed query methods

In `lib/features/todos/presentation/providers/todo_provider.dart`, add the following methods after `deleteCompleted()` (after line 204):

```dart
  /// Load todos linked to a specific daily entry.
  /// WHY: Entry editor shows related todos in a "Linked Todos" section.
  Future<List<TodoItem>> getByEntryId(String entryId) async {
    try {
      return await _repository.getByEntryId(entryId);
    } catch (e) {
      Logger.ui('[TodoProvider] getByEntryId error: $e');
      return [];
    }
  }

  /// Load todos filtered by priority.
  /// WHY: Priority filter chip on TodosScreen.
  Future<void> loadByPriority(TodoPriority priority) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _todos = await _repository.getByPriority(priority, projectId: _currentProjectId);
    } catch (e) {
      _error = 'Failed to filter by priority: $e';
      Logger.ui('[TodoProvider] loadByPriority error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Load only overdue todos.
  /// WHY: "Overdue" filter chip on TodosScreen.
  Future<void> loadOverdue() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _todos = await _repository.getOverdue(projectId: _currentProjectId);
    } catch (e) {
      _error = 'Failed to load overdue todos: $e';
      Logger.ui('[TodoProvider] loadOverdue error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Load todos due today.
  /// WHY: "Due Today" filter chip on TodosScreen.
  Future<void> loadDueToday() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _todos = await _repository.getDueToday(projectId: _currentProjectId);
    } catch (e) {
      _error = 'Failed to load due today todos: $e';
      Logger.ui('[TodoProvider] loadDueToday error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Get incomplete count from the database.
  /// WHY: Badge count on the Toolbox hub card — shows actionable items.
  Future<int> getIncompleteCount({String? projectId}) async {
    try {
      return await _repository.getIncompleteCount(projectId: projectId ?? _currentProjectId);
    } catch (e) {
      Logger.ui('[TodoProvider] getIncompleteCount error: $e');
      return 0;
    }
  }

  /// Delete all todos for a project.
  /// WHY: Cleanup when a project is removed from device.
  Future<bool> deleteByProject(String projectId) async {
    if (!canWrite()) {
      Logger.ui('[TodoProvider] deleteByProject blocked: canWrite returned false');
      return false;
    }
    try {
      await _repository.deleteByProjectId(projectId);
      if (_currentProjectId == projectId) {
        _todos = [];
        notifyListeners();
      }
      return true;
    } catch (e) {
      _error = 'Failed to delete project todos: $e';
      Logger.ui('[TodoProvider] deleteByProject error: $e');
      notifyListeners();
      return false;
    }
  }
```

#### Step 17.1.2: Write tests

Create `test/features/todos/presentation/providers/todo_provider_filter_test.dart`:
- `getByEntryId` returns list from repository
- `loadByPriority` replaces `_todos` with filtered results
- `loadOverdue` replaces `_todos` with overdue items
- `loadDueToday` replaces `_todos` with due-today items
- `getIncompleteCount` returns int from repository
- `deleteByProject` clears local state when current project matches
- Error handling for each method

#### Step 17.1.3: Verify

Run: `pwsh -Command "flutter test test/features/todos/presentation/providers/"`

### Sub-phase 17.2: Wire Filter Chips to TodosScreen

**Files:**
- Modify: `lib/features/todos/presentation/screens/todos_screen.dart`
- Test: `test/features/todos/presentation/screens/todos_screen_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 17.2.1: Add filter chip bar

In `lib/features/todos/presentation/screens/todos_screen.dart`, add a horizontal row of `FilterChip` widgets above the todo list:

- "All" chip: calls `provider.loadTodos(projectId: projectId)` (existing)
- "Overdue" chip: calls `provider.loadOverdue()`
- "Due Today" chip: calls `provider.loadDueToday()`
- "High Priority" chip: calls `provider.loadByPriority(TodoPriority.high)`

Track the selected chip in local state (`_selectedFilter`). Each chip tap sets the filter and reloads.

#### Step 17.2.2: Write widget test

Test that each filter chip is present and tapping triggers the appropriate provider method (use mock provider).

#### Step 17.2.3: Verify

Run: `pwsh -Command "flutter test test/features/todos/presentation/screens/todos_screen_test.dart"`

---

## Phase 18: Wire Document Methods to Provider/UI

### Sub-phase 18.1: Add Project-Level Document Loading to DocumentProvider

**Files:**
- Modify: `lib/features/forms/presentation/providers/document_provider.dart`
- Modify: `lib/features/forms/domain/usecases/manage_documents_use_case.dart`
- Test: `test/features/forms/presentation/providers/document_provider_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 18.1.1: Add getByProjectId pass-through to ManageDocumentsUseCase

In `lib/features/forms/domain/usecases/manage_documents_use_case.dart`, add:

```dart
  /// Get all documents for a project (all entries).
  /// WHY: Project-level document view shows all attached files.
  Future<List<Document>> getProjectDocuments(String projectId) =>
      _documentRepository.getByProjectId(projectId);
```

This requires the use case to hold a reference to `DocumentRepository`. Verify it already does; if not, add it as a constructor parameter.

#### Step 18.1.2: Add project document loading to DocumentProvider

In `lib/features/forms/presentation/providers/document_provider.dart`, add state and method after the `_entryDocuments` field (after line 15):

```dart
  List<Document> _projectDocuments = [];
  List<Document> get projectDocuments => _projectDocuments;
  bool _isLoadingProjectDocuments = false;
  bool get isLoadingProjectDocuments => _isLoadingProjectDocuments;
```

Update the `isLoading` getter (line 26) to include the new flag:

```dart
  bool get isLoading => _isLoadingDocuments || _isLoadingEntryDocuments || _isLoadingProjectDocuments;
```

Add method after `loadEntryDocuments` (after line 69):

```dart
  /// Load all documents for a project across all entries.
  /// WHY: Enables project-level document view showing all attached files.
  Future<void> loadProjectDocuments(String projectId) async {
    _isLoadingProjectDocuments = true;
    notifyListeners();
    try {
      _projectDocuments = await _useCase.getProjectDocuments(projectId);
    } catch (e) {
      _error = 'Failed to load project documents: $e';
    } finally {
      _isLoadingProjectDocuments = false;
      notifyListeners();
    }
  }
```

#### Step 18.1.3: Write tests

Create `test/features/forms/presentation/providers/document_provider_test.dart`:
- `loadProjectDocuments` sets loading state, populates `projectDocuments`, resets loading
- Error case: sets `_error`, resets loading

#### Step 18.1.4: Verify

Run: `pwsh -Command "flutter test test/features/forms/presentation/providers/document_provider_test.dart"`

---

## Phase 19: Wire Export Methods to Provider/UI

### Sub-phase 19.1: Add Export History to EntryExportProvider

**Files:**
- Modify: `lib/features/entries/presentation/providers/entry_export_provider.dart`
- Modify: `lib/features/entries/domain/usecases/export_entry_use_case.dart`
- Test: `test/features/entries/presentation/providers/entry_export_provider_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 19.1.1: Add repository query methods to ExportEntryUseCase

In `lib/features/entries/domain/usecases/export_entry_use_case.dart`, add methods that delegate to `EntryExportRepository`:

```dart
  /// Get all exports for a project.
  /// WHY: "Previous Exports" section in project detail screen.
  Future<List<EntryExport>> getByProjectId(String projectId) =>
      _entryExportRepository.getByProjectId(projectId);

  /// Get exports for a specific entry.
  /// WHY: "Previous Exports" section in entry detail screen.
  Future<List<EntryExport>> getByEntryId(String entryId) =>
      _entryExportRepository.getByEntryId(entryId);
```

This requires `ExportEntryUseCase` to hold a reference to `EntryExportRepository`. Verify it already does; if not, add it.

#### Step 19.1.2: Add export history state to EntryExportProvider

In `lib/features/entries/presentation/providers/entry_export_provider.dart`, add after the `_errorMessage` field (line 19):

```dart
  List<EntryExport> _exportHistory = [];
  List<EntryExport> get exportHistory => _exportHistory;
  bool _isLoadingHistory = false;
  bool get isLoadingHistory => _isLoadingHistory;
```

Add methods after `exportAllFormsForEntry` (after line 51):

```dart
  /// Load export history for a project.
  /// WHY: Enables "Previous Exports" section showing all past PDF exports.
  Future<void> loadExportHistory(String projectId) async {
    _isLoadingHistory = true;
    notifyListeners();
    try {
      _exportHistory = await _exportEntryUseCase.getByProjectId(projectId);
    } catch (e) {
      Logger.error('[EntryExportProvider] loadExportHistory error', error: e);
      _exportHistory = [];
    } finally {
      _isLoadingHistory = false;
      notifyListeners();
    }
  }

  /// Load export history for a specific entry.
  /// WHY: Entry detail screen shows past exports for that entry.
  Future<void> loadEntryExportHistory(String entryId) async {
    _isLoadingHistory = true;
    notifyListeners();
    try {
      _exportHistory = await _exportEntryUseCase.getByEntryId(entryId);
    } catch (e) {
      Logger.error('[EntryExportProvider] loadEntryExportHistory error', error: e);
      _exportHistory = [];
    } finally {
      _isLoadingHistory = false;
      notifyListeners();
    }
  }
```

Add necessary import for `EntryExport` model.

#### Step 19.1.3: Verify

Run: `pwsh -Command "flutter test test/features/entries/presentation/providers/"`

### Sub-phase 19.2: Add Export History to FormExportProvider

**Files:**
- Modify: `lib/features/forms/presentation/providers/form_export_provider.dart`
- Modify: `lib/features/forms/domain/usecases/export_form_use_case.dart`
- Test: `test/features/forms/presentation/providers/form_export_provider_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 19.2.1: Add repository query methods to ExportFormUseCase

In `lib/features/forms/domain/usecases/export_form_use_case.dart`, add:

```dart
  /// Get all form exports for a project.
  Future<List<FormExport>> getByProjectId(String projectId) =>
      _formExportRepository.getByProjectId(projectId);

  /// Get form exports for a specific entry.
  Future<List<FormExport>> getByEntryId(String entryId) =>
      _formExportRepository.getByEntryId(entryId);

  /// Get exports for a specific form response.
  Future<List<FormExport>> getByFormResponseId(String responseId) =>
      _formExportRepository.getByFormResponseId(responseId);
```

Verify `ExportFormUseCase` holds `FormExportRepository`; add if missing.

#### Step 19.2.2: Add export history state to FormExportProvider

In `lib/features/forms/presentation/providers/form_export_provider.dart`, add after `_errorMessage` (line 14):

```dart
  List<FormExport> _exportHistory = [];
  List<FormExport> get exportHistory => _exportHistory;
  bool _isLoadingHistory = false;
  bool get isLoadingHistory => _isLoadingHistory;
```

Add methods after `exportFormToPdf` (after line 43):

```dart
  /// Load export history for a project.
  /// WHY: Shows all past form exports across the project.
  Future<void> loadProjectExportHistory(String projectId) async {
    _isLoadingHistory = true;
    notifyListeners();
    try {
      _exportHistory = await _exportFormUseCase.getByProjectId(projectId);
    } catch (e) {
      Logger.error('[FormExportProvider] loadProjectExportHistory error', error: e);
      _exportHistory = [];
    } finally {
      _isLoadingHistory = false;
      notifyListeners();
    }
  }

  /// Load export history for a specific form response.
  /// WHY: Form detail screen shows "Previous Exports" for that response.
  Future<void> loadResponseExportHistory(String responseId) async {
    _isLoadingHistory = true;
    notifyListeners();
    try {
      _exportHistory = await _exportFormUseCase.getByFormResponseId(responseId);
    } catch (e) {
      Logger.error('[FormExportProvider] loadResponseExportHistory error', error: e);
      _exportHistory = [];
    } finally {
      _isLoadingHistory = false;
      notifyListeners();
    }
  }
```

Add necessary import for `FormExport` model.

#### Step 19.2.3: Verify

Run: `pwsh -Command "flutter test test/features/forms/presentation/providers/"`

---

## Phase 20: Wire Photo Utility Methods

### Sub-phase 20.1: Add Photo Count Methods to PhotoProvider

**Files:**
- Modify: `lib/features/photos/presentation/providers/photo_provider.dart`
- Test: `test/features/photos/presentation/providers/photo_provider_count_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 20.1.1: Add count and bulk-delete methods

In `lib/features/photos/presentation/providers/photo_provider.dart`, add after `getPhotoById` (after line 139):

```dart
  /// Get photo count for an entry (async DB query).
  /// WHY: Enables photo count badges on entry list items without loading full photo objects.
  Future<int> getPhotoCountForEntry(String entryId) async {
    final result = await _repository.getPhotoCountForEntry(entryId);
    if (result.isSuccess) {
      return result.data ?? 0;
    }
    Logger.photo('[PhotoProvider] getPhotoCountForEntry error: ${result.error}');
    return 0;
  }

  /// Get photo count for a project (async DB query).
  /// WHY: Enables project dashboard stats showing total photos.
  Future<int> getPhotoCountForProject(String projectId) async {
    final result = await _repository.getPhotoCountForProject(projectId);
    if (result.isSuccess) {
      return result.data ?? 0;
    }
    Logger.photo('[PhotoProvider] getPhotoCountForProject error: ${result.error}');
    return 0;
  }

  /// Delete all photos for an entry.
  /// WHY: Cascade cleanup when an entry is deleted.
  Future<bool> deletePhotosForEntry(String entryId) async {
    if (!canWrite()) {
      Logger.photo('[PhotoProvider] deletePhotosForEntry blocked: canWrite returned false');
      return false;
    }
    final result = await _repository.deletePhotosForEntry(entryId);
    if (result.isSuccess) {
      _photos.removeWhere((p) => p.entryId == entryId);
      notifyListeners();
      return true;
    }
    _error = result.error;
    Logger.photo('[PhotoProvider] deletePhotosForEntry error: ${result.error}');
    notifyListeners();
    return false;
  }
```

#### Step 20.1.2: Write tests

Create `test/features/photos/presentation/providers/photo_provider_count_test.dart`:
- `getPhotoCountForEntry` returns count on success, 0 on error
- `getPhotoCountForProject` returns count on success, 0 on error
- `deletePhotosForEntry` removes matching photos from local state
- `deletePhotosForEntry` blocked when `canWrite` returns false

#### Step 20.1.3: Verify

Run: `pwsh -Command "flutter test test/features/photos/presentation/providers/"`

---

## Phase 21: Wire EntryQuantity Utility Methods

### Sub-phase 21.1: Add Bid Item Query and Bulk Delete to EntryQuantityProvider

**Files:**
- Modify: `lib/features/quantities/presentation/providers/entry_quantity_provider.dart`
- Test: `test/features/quantities/presentation/providers/entry_quantity_provider_extra_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 21.1.1: Add methods

In `lib/features/quantities/presentation/providers/entry_quantity_provider.dart`, add after `getQuantitiesForBidItem` (after line 289):

```dart
  /// Load all quantities across all entries for a specific bid item.
  /// WHY: Enables bid item detail view showing every entry that reported
  /// quantities against this item, with running total.
  Future<List<EntryQuantity>> getQuantitiesForBidItemFromDb(String bidItemId) async {
    try {
      return await _repository.getByBidItemId(bidItemId);
    } catch (e) {
      Logger.db('[EntryQuantityProvider] getQuantitiesForBidItemFromDb error: $e');
      return [];
    }
  }

  /// Delete all quantities for a specific entry.
  /// WHY: Cascade cleanup when an entry is deleted.
  Future<bool> deleteQuantitiesForEntry(String entryId) async {
    try {
      await _repository.deleteByEntryId(entryId);
      if (_currentEntryId == entryId) {
        _quantities = [];
        notifyListeners();
      }
      return true;
    } catch (e) {
      Logger.db('[EntryQuantityProvider] deleteQuantitiesForEntry error: $e');
      _error = 'Failed to delete quantities: $e';
      notifyListeners();
      return false;
    }
  }

  /// Delete all quantities for a specific bid item.
  /// WHY: Cascade cleanup when a bid item is removed from a project.
  Future<bool> deleteQuantitiesForBidItem(String bidItemId) async {
    try {
      await _repository.deleteByBidItemId(bidItemId);
      _quantities.removeWhere((q) => q.bidItemId == bidItemId);
      _usedByBidItem.remove(bidItemId);
      notifyListeners();
      return true;
    } catch (e) {
      Logger.db('[EntryQuantityProvider] deleteQuantitiesForBidItem error: $e');
      _error = 'Failed to delete bid item quantities: $e';
      notifyListeners();
      return false;
    }
  }

  /// Get count of quantities for an entry (async DB query).
  /// WHY: Enables showing quantity count badges on entry list items.
  Future<int> getCountForEntry(String entryId) async {
    try {
      return await _repository.getCountByEntry(entryId);
    } catch (e) {
      Logger.db('[EntryQuantityProvider] getCountForEntry error: $e');
      return 0;
    }
  }
```

#### Step 21.1.2: Write tests

Create `test/features/quantities/presentation/providers/entry_quantity_provider_extra_test.dart`:
- `getQuantitiesForBidItemFromDb` returns list from repository
- `deleteQuantitiesForEntry` clears local state when current entry matches
- `deleteQuantitiesForBidItem` removes from local list and `_usedByBidItem` map
- `getCountForEntry` returns count, 0 on error

#### Step 21.1.3: Verify

Run: `pwsh -Command "flutter test test/features/quantities/presentation/providers/"`

---

## Phase 22: Miscellaneous Remaining Items

### Sub-phase 22.1: Fix Driver isSyncing Hardcoded False (L1)

**Files:**
- Modify: `lib/features/sync/application/sync_orchestrator.dart`
- Modify: `lib/core/driver/driver_server.dart`
- Test: `test/core/driver/driver_server_sync_status_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 22.1.1: Add isSyncing getter to SyncOrchestrator

In `lib/features/sync/application/sync_orchestrator.dart`, add a public getter:

```dart
  /// WHY: Exposes live syncing state to the driver endpoint.
  /// The driver's /sync-status response was hardcoded false.
  bool _isSyncing = false;
  bool get isSyncing => _isSyncing;
```

Then wrap the existing sync execution logic to set `_isSyncing = true` before the sync starts and `_isSyncing = false` in a `finally` block when it completes. Find the main sync method (likely `syncLocalAgencyProjects` or `syncAll`) and add the flag management.

#### Step 22.1.2: Wire to driver response

In `lib/core/driver/driver_server.dart` at line 1250-1252, replace:

```dart
        // TODO: Expose isSyncing getter on SyncOrchestrator for accurate status
        'isSyncing': false,
```

with:

```dart
        // WHY: Live syncing state from SyncOrchestrator (was hardcoded false).
        'isSyncing': syncOrchestrator?.isSyncing ?? false,
```

This requires the driver server to have a reference to `SyncOrchestrator`. Verify it does (check the class fields for `syncOrchestrator`); if not, add `SyncOrchestrator? syncOrchestrator;` as a settable field.

#### Step 22.1.3: Write test

Test that `/driver/sync-status` returns `isSyncing: true` when orchestrator is syncing, `false` when idle.

#### Step 22.1.4: Verify

Run: `pwsh -Command "flutter test test/core/driver/"`

### Sub-phase 22.2: Add Foreground Fraction Alert (L2)

**Files:**
- Modify: `lib/features/pdf/services/extraction/stages/grid_line_remover.dart`
- Test: `test/features/pdf/services/extraction/stages/grid_line_remover_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 22.2.1: Add logger warning

In `lib/features/pdf/services/extraction/stages/grid_line_remover.dart` at line 494, replace:

```dart
    // TODO: Alert if foregroundFraction < 0.01 or > 0.90 (threshold mismatch indicator)
    final foregroundPixels = cv.countNonZero(binary);
    final foregroundFraction = foregroundPixels / (rows * cols);
```

with:

```dart
    // WHY: Extreme foreground fractions indicate threshold mismatch —
    // too low = nearly all background (blank page?), too high = everything is foreground.
    final foregroundPixels = cv.countNonZero(binary);
    final foregroundFraction = foregroundPixels / (rows * cols);
    if (foregroundFraction < 0.01 || foregroundFraction > 0.90) {
      Logger.ocr('WARNING: foregroundFraction=$foregroundFraction '
          '(pixels=$foregroundPixels, total=${rows * cols}). '
          'Possible threshold mismatch — check image quality.');
    }
```

Ensure `Logger` is imported at the top of the file.

#### Step 22.2.2: Write test

Add test case to existing grid_line_remover tests (or create new test file) that verifies the warning is logged when foreground fraction is below 0.01 or above 0.90. Use a mock Logger or verify Logger output.

#### Step 22.2.3: Verify

Run: `pwsh -Command "flutter test test/features/pdf/services/extraction/stages/"`

### Sub-phase 22.3: Fix Sentry setExtra Deprecated (L4)

**Files:**
- Modify: `lib/core/logging/logger.dart`
- Test: `test/core/logging/logger_test.dart`

**Agent**: `general-purpose`

#### Step 22.3.1: Replace deprecated setExtra with setContexts

In `lib/core/logging/logger.dart` at line 248-250, replace:

```dart
          if (scrubbedStack != null) {
            scope.setExtra('stack_trace', scrubbedStack);
          }
```

with:

```dart
          if (scrubbedStack != null) {
            // WHY: setExtra is deprecated in Sentry SDK.
            // Use setContexts to attach stack trace as structured context.
            scope.setContexts('stack_trace', {'value': scrubbedStack});
          }
```

#### Step 22.3.2: Verify

Run: `pwsh -Command "flutter test test/core/logging/"`

### Sub-phase 22.4: Implement Form Sub-Screen Stubs (L6)

**Files:**
- Modify: `lib/features/forms/presentation/screens/mdot_hub_screen.dart`
- Test: `test/features/forms/presentation/screens/form_sub_screens_test.dart`

**Agent**: `frontend-flutter-specialist-agent`

#### Step 22.4.1: Implement FormFillScreen

Replace the stub at lines 1071-1078 with a proper screen that:
1. Reads the `FormResponse` via `InspectorFormProvider.loadResponseById(responseId)`
2. Displays the full form with all sections (header + proctor + test) in a read/edit view
3. This is effectively the same as `MdotHubScreen` but with all sections expanded

Since `FormFillScreen` currently just delegates to `MdotHubScreen`, and the hub screen IS the form fill experience, this stub is actually correct behavior. Add a `// WHY:` comment explaining the delegation:

```dart
class FormFillScreen extends StatelessWidget {
  final String responseId;

  const FormFillScreen({super.key, required this.responseId});

  @override
  // WHY: FormFillScreen is the full-form entry point. The MdotHubScreen
  // already implements the complete fill experience (header + proctor + test
  // sections). This delegation is intentional, not a stub.
  Widget build(BuildContext context) => MdotHubScreen(responseId: responseId);
}
```

#### Step 22.4.2: Implement QuickTestEntryScreen

Replace the stub at lines 1080-1087. This screen should open the `MdotHubScreen` but auto-expand to the test section (section index 2):

```dart
class QuickTestEntryScreen extends StatelessWidget {
  final String responseId;

  const QuickTestEntryScreen({super.key, required this.responseId});

  @override
  // WHY: Quick Test Entry jumps directly to the test section.
  // Pass initialSection to MdotHubScreen to auto-expand section 2.
  Widget build(BuildContext context) => MdotHubScreen(
    responseId: responseId,
    initialSection: 2,
  );
}
```

This requires adding an `initialSection` parameter to `MdotHubScreen`:

In the `MdotHubScreen` widget (line 21-28), add:

```dart
  final int? initialSection;

  const MdotHubScreen({super.key, required this.responseId, this.initialSection});
```

In `_MdotHubScreenState._hydrate` (line 246), update the default expanded logic:

```dart
    _expanded = widget.initialSection ??
        (!_headerConfirmed ? 0 : (proctors.isEmpty ? 1 : 2));
```

#### Step 22.4.3: Implement ProctorEntryScreen

Replace the stub at lines 1089-1096. Opens hub at proctor section (index 1):

```dart
class ProctorEntryScreen extends StatelessWidget {
  final String responseId;

  const ProctorEntryScreen({super.key, required this.responseId});

  @override
  // WHY: Proctor Entry jumps directly to the proctor section.
  Widget build(BuildContext context) => MdotHubScreen(
    responseId: responseId,
    initialSection: 1,
  );
}
```

#### Step 22.4.4: Implement WeightsEntryScreen

Replace the stub at lines 1098-1105. Opens hub at proctor section (index 1) since weights are part of the proctor workflow:

```dart
class WeightsEntryScreen extends StatelessWidget {
  final String responseId;

  const WeightsEntryScreen({super.key, required this.responseId});

  @override
  // WHY: Weights entry is part of the proctor workflow (section 1).
  // The weight readings input is inside HubProctorContent.
  Widget build(BuildContext context) => MdotHubScreen(
    responseId: responseId,
    initialSection: 1,
  );
}
```

#### Step 22.4.5: Write tests

Create `test/features/forms/presentation/screens/form_sub_screens_test.dart`:
- `FormFillScreen` renders `MdotHubScreen` with no `initialSection`
- `QuickTestEntryScreen` renders `MdotHubScreen` with `initialSection: 2`
- `ProctorEntryScreen` renders `MdotHubScreen` with `initialSection: 1`
- `WeightsEntryScreen` renders `MdotHubScreen` with `initialSection: 1`

#### Step 22.4.6: Verify

Run: `pwsh -Command "flutter test test/features/forms/presentation/screens/"`

### Sub-phase 22.5: FCM Foreground Messages Trigger Sync (L8)

**Files:**
- Modify: `lib/features/sync/application/fcm_handler.dart`
- Test: `test/features/sync/application/fcm_handler_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 22.5.1: Add SyncOrchestrator dependency to FcmHandler

In `lib/features/sync/application/fcm_handler.dart`, modify the class:

1. Add import for `SyncOrchestrator`:

```dart
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';
```

2. Add field and constructor parameter:

```dart
class FcmHandler {
  final AuthService? _authService;
  final SyncOrchestrator? _syncOrchestrator;
  bool _isInitialized = false;

  FcmHandler({AuthService? authService, SyncOrchestrator? syncOrchestrator})
      : _authService = authService,
        _syncOrchestrator = syncOrchestrator;
```

3. Replace the foreground handler (lines 72-77):

```dart
      // Handle foreground messages
      FirebaseMessaging.onMessage.listen((message) {
        Logger.sync('FCM foreground message messageId=${message.messageId}');
        final messageType = message.data['type'];
        if (messageType == 'daily_sync') {
          // WHY: Foreground sync trigger — was previously logged and ignored.
          // Trigger an actual sync so the user sees fresh data immediately.
          Logger.sync('FCM daily sync trigger (foreground) — triggering sync');
          _syncOrchestrator?.syncLocalAgencyProjects();
        }
      });
```

#### Step 22.5.2: Update FcmHandler construction site

Find where `FcmHandler` is constructed (likely in `lib/main.dart` or a service locator) and pass `SyncOrchestrator` to it.

#### Step 22.5.3: Write test

Create `test/features/sync/application/fcm_handler_test.dart`:
- Verify that when a foreground message with `type: 'daily_sync'` arrives, `syncOrchestrator.syncLocalAgencyProjects()` is called
- Verify non-daily_sync messages do not trigger sync

#### Step 22.5.4: Verify

Run: `pwsh -Command "flutter test test/features/sync/application/"`

### Sub-phase 22.6: Surface Circuit Breaker Trips to UI (M4)

**Files:**
- Modify: `lib/features/sync/engine/sync_engine.dart`
- Modify: `lib/features/sync/application/sync_orchestrator.dart`
- Modify: `lib/features/sync/presentation/providers/sync_provider.dart`
- Modify: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`
- Test: `test/features/sync/engine/sync_engine_circuit_breaker_test.dart`

**Agent**: `backend-supabase-agent`

#### Step 22.6.1: Add callback to SyncEngine

In `lib/features/sync/engine/sync_engine.dart`, add a callback field:

```dart
  /// WHY: Callback invoked when the circuit breaker trips for a record.
  /// Enables SyncOrchestrator to propagate trip events to the UI layer.
  void Function(String tableName, String recordId, int conflictCount)?
      onCircuitBreakerTrip;
```

At line 1650-1652, where the circuit breaker logs, invoke the callback:

```dart
              // WHY: Surface circuit breaker trips to UI via callback chain.
              Logger.sync('CIRCUIT BREAKER: Skipping re-push for ${adapter.tableName}/$recordId '
                  '(conflict count: $conflictCount). Record stuck — check conflict viewer.');
              onCircuitBreakerTrip?.call(adapter.tableName, recordId, conflictCount);
```

#### Step 22.6.2: Propagate through SyncOrchestrator

In `lib/features/sync/application/sync_orchestrator.dart`, add:

```dart
  /// WHY: Callback chain — SyncEngine → SyncOrchestrator → SyncProvider.
  void Function(String tableName, String recordId, int conflictCount)?
      onCircuitBreakerTrip;
```

Where the `SyncEngine` is created/configured, wire the callback:

```dart
  engine.onCircuitBreakerTrip = (tableName, recordId, count) {
    onCircuitBreakerTrip?.call(tableName, recordId, count);
  };
```

#### Step 22.6.3: Surface in SyncProvider

In `lib/features/sync/presentation/providers/sync_provider.dart`, add state:

```dart
  /// Records that are stuck in the circuit breaker (table/recordId pairs).
  final List<({String tableName, String recordId, int conflictCount})>
      _circuitBreakerTrips = [];

  List<({String tableName, String recordId, int conflictCount})>
      get circuitBreakerTrips => List.unmodifiable(_circuitBreakerTrips);
```

Wire the orchestrator callback in the constructor or init:

```dart
    _syncOrchestrator.onCircuitBreakerTrip = (tableName, recordId, count) {
      _circuitBreakerTrips.add((
        tableName: tableName,
        recordId: recordId,
        conflictCount: count,
      ));
      notifyListeners();
    };
```

Add a method to clear trips:

```dart
  /// Clear circuit breaker trip records after user acknowledges.
  void clearCircuitBreakerTrips() {
    _circuitBreakerTrips.clear();
    notifyListeners();
  }
```

#### Step 22.6.4: Display in SyncDashboard

In `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`, add a section that displays circuit breaker trips when `syncProvider.circuitBreakerTrips.isNotEmpty`:

- Show a warning card with amber background
- List each tripped record: `"[Table] Record stuck (X conflicts)"`
- Add a "Dismiss" button that calls `syncProvider.clearCircuitBreakerTrips()`

#### Step 22.6.5: Write test

Create `test/features/sync/engine/sync_engine_circuit_breaker_test.dart`:
- Verify callback is invoked when conflict count exceeds threshold
- Verify SyncProvider accumulates trip records
- Verify `clearCircuitBreakerTrips` resets list

#### Step 22.6.6: Verify

Run: `pwsh -Command "flutter test test/features/sync/"`

### Sub-phase 22.7: Extract ExtractionMetrics Datasource (M9)

**Files:**
- Create: `lib/features/pdf/data/datasources/local/extraction_metrics_local_datasource.dart`
- Modify: `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart`
- Test: `test/features/pdf/data/datasources/local/extraction_metrics_local_datasource_test.dart`

**Agent**: `backend-data-layer-agent`

#### Step 22.7.1: Create the datasource

Create `lib/features/pdf/data/datasources/local/extraction_metrics_local_datasource.dart`:

Read the full `ExtractionMetrics` class at `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart` to understand all raw SQL operations. Extract them into the datasource:

```dart
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

/// WHY: Moves raw SQL out of ExtractionMetrics service class into a proper
/// datasource following Clean Architecture layering. The service class should
/// call datasource methods, not execute SQL directly.
class ExtractionMetricsLocalDatasource {
  final Database _db;

  ExtractionMetricsLocalDatasource(this._db);

  /// Insert a top-level extraction metrics row.
  Future<void> insertExtractionMetric(Map<String, dynamic> values) async {
    await _db.insert('extraction_metrics', values);
  }

  /// Insert a stage metrics row.
  Future<void> insertStageMetric(Map<String, dynamic> values) async {
    await _db.insert('stage_metrics', values);
  }

  /// Query extraction metrics by extraction ID.
  Future<Map<String, dynamic>?> getByExtractionId(String extractionId) async {
    final results = await _db.query(
      'extraction_metrics',
      where: 'id = ?',
      whereArgs: [extractionId],
    );
    return results.isNotEmpty ? results.first : null;
  }

  /// Query stage metrics for an extraction run.
  Future<List<Map<String, dynamic>>> getStagesForExtraction(String extractionId) async {
    return await _db.query(
      'stage_metrics',
      where: 'extraction_id = ?',
      whereArgs: [extractionId],
    );
  }
}
```

#### Step 22.7.2: Refactor ExtractionMetrics to use datasource

In `lib/features/pdf/services/extraction/pipeline/extraction_metrics.dart`:

1. Change constructor to accept `ExtractionMetricsLocalDatasource` instead of `Database`:

```dart
class ExtractionMetrics {
  final ExtractionMetricsLocalDatasource _datasource;

  ExtractionMetrics(this._datasource);
```

2. Replace all `_db.insert(...)` calls with `_datasource.insertExtractionMetric(...)` and `_datasource.insertStageMetric(...)`.

3. Update all construction sites of `ExtractionMetrics` to pass the datasource instead of the raw `Database`. Search for `ExtractionMetrics(` to find them.

#### Step 22.7.3: Write tests

Create `test/features/pdf/data/datasources/local/extraction_metrics_local_datasource_test.dart`:
- `insertExtractionMetric` inserts a row into `extraction_metrics`
- `insertStageMetric` inserts a row into `stage_metrics`
- `getByExtractionId` returns row or null
- `getStagesForExtraction` returns list of stage rows

Use an in-memory SQLite database for testing.

#### Step 22.7.4: Verify

Run: `pwsh -Command "flutter test test/features/pdf/"`

---

## Dispatch Groups

### Group A (Phases 16-17): Entry and Todo Provider Wiring
- Phase 16: Wire DailyEntry filtering/count methods
- Phase 17: Wire Todo filter/query methods + TodosScreen filter chips
- **Agent**: `frontend-flutter-specialist-agent` (primary), `backend-data-layer-agent` (use case)

### Group B (Phases 18-19): Document and Export Provider Wiring
- Phase 18: Wire Document project-level loading
- Phase 19: Wire EntryExport and FormExport history
- **Agent**: `frontend-flutter-specialist-agent`

### Group C (Phases 20-21): Photo and Quantity Provider Wiring
- Phase 20: Wire Photo count/bulk-delete methods
- Phase 21: Wire EntryQuantity bid-item query/bulk-delete methods
- **Agent**: `frontend-flutter-specialist-agent`

### Group D (Phase 22.1-22.3): Miscellaneous Backend Fixes
- Sub-phase 22.1: Driver isSyncing fix
- Sub-phase 22.2: Foreground fraction alert
- Sub-phase 22.3: Sentry setExtra deprecated
- **Agent**: `general-purpose`

### Group E (Phase 22.4): Form Sub-Screen Implementation
- Sub-phase 22.4: Implement 4 form sub-screen stubs
- **Agent**: `frontend-flutter-specialist-agent`

### Group F (Phase 22.5-22.7): Sync and Extraction Fixes
- Sub-phase 22.5: FCM foreground sync trigger
- Sub-phase 22.6: Circuit breaker UI surfacing
- Sub-phase 22.7: ExtractionMetrics datasource extraction
- **Agent**: `backend-supabase-agent` (22.5-22.6), `backend-data-layer-agent` (22.7)

### Dependencies
- Groups A-F are independent and can run in parallel
- Within Phase 16: Sub-phase 16.1 (use case) must complete before 16.2 (provider)
- Within Phase 19: Sub-phases 19.1 and 19.2 are independent
- Within Phase 22: All sub-phases are independent

### Verification (after all groups)

Run: `pwsh -Command "flutter test"`
Run: `pwsh -Command "flutter analyze"`
