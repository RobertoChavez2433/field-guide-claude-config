# Pattern — Adding a TestingKeys Sentinel

Testing keys are modular: one per-feature file exports a key class, `testing_keys.dart` imports each class and re-delegates static getters so `TestingKeys.*` remains the single call-site.

## Structure

```
lib/shared/testing_keys/
├── testing_keys.dart           — facade, exports + delegates per feature
├── auth_keys.dart              — AuthTestingKeys
├── common_keys.dart            — CommonTestingKeys
├── consent_keys.dart           — ConsentTestingKeys
├── contractors_keys.dart       — ContractorsTestingKeys
├── documents_keys.dart         — DocumentsTestingKeys
├── entries_keys.dart           — EntriesTestingKeys
├── locations_keys.dart         — LocationsTestingKeys
├── navigation_keys.dart        — NavigationTestingKeys
├── pay_app_keys.dart           — PayAppTestingKeys
├── photos_keys.dart            — PhotosTestingKeys
├── projects_keys.dart          — ProjectsTestingKeys
├── quantities_keys.dart        — QuantitiesTestingKeys
├── settings_keys.dart          — SettingsTestingKeys
├── support_keys.dart           — SupportTestingKeys
├── sync_keys.dart              — SyncTestingKeys
└── toolbox_keys.dart           — ToolboxTestingKeys
```

## Exemplar (sync_keys.dart:1-96)

```dart
class SyncTestingKeys {
  SyncTestingKeys._();
  static const syncDashboardScreen = Key('sync_dashboard_screen');
  static const conflictViewerScreen = Key('conflict_viewer_screen');
  static const syncNowTile = Key('sync_now_tile');
  // …
  static Key syncBucketTile(String name) => Key('sync_bucket_tile_$name');
}
```

Facade re-delegation (testing_keys.dart:74-98):

```dart
class TestingKeys {
  TestingKeys._();
  static const bottomNavigationBar = NavigationTestingKeys.bottomNavigationBar;
  static const confirmationDialog = CommonTestingKeys.confirmationDialog;
  // … per-feature delegations …
}
```

## Rules

1. **Add to the right per-feature file.** Sentinel keys for `ToolboxHomeScreen` go in `toolbox_keys.dart`, not `testing_keys.dart`.
2. **Key string literal = lowercase snake case.** Matches existing convention (`sync_dashboard_screen`, `conflict_viewer_screen`, `form_gallery_screen`).
3. **Factory keys for collection items.** Use `static Key fooCard(String id) => Key('foo_card_$id')`. Avoid dynamic lookup by index when an id exists (id-stable keys survive reorder).
4. **Re-export from facade.** Every new sentinel added to `<feature>_keys.dart` must have a matching `static const` or `static Key` delegation in `testing_keys.dart` so `TestingKeys.*` and per-feature class access stay interchangeable.
5. **No production code may import `Key('…')` literals.** Rubric item 2. Replace existing offenders (list in `blast-radius.md`).

## Screen-contract alignment

`screenContracts[id].rootKey` must equal the sentinel you just added. Example pattern for `ToolboxHomeScreen`:

```dart
// in toolbox_keys.dart
static const toolboxHomeScreen = Key('toolbox_home_screen');

// in testing_keys.dart
static const toolboxHomeScreen = ToolboxTestingKeys.toolboxHomeScreen;

// in screen_contract_registry.dart
'ToolboxHomeScreen': const ScreenContract(
  id: 'ToolboxHomeScreen',
  rootKey: TestingKeys.toolboxHomeScreen,
  routes: ['/toolbox'],
  actionKeys: [...],
  stateKeys: ['toolbox_home_screen'],
),
```

The `rootKey` `Key('toolbox_home_screen')` and the `stateKeys` string `'toolbox_home_screen'` are the same literal — they must match.
