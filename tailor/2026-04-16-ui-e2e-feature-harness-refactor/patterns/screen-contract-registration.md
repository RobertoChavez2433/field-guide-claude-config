# Pattern — Atomic Screen + Contract + Flow Registration

The three registries must stay aligned. Any feature spec that introduces or re-declares a screen touches all three in the same commit.

## Exemplars

- `lib/core/driver/screen_registry.dart:111-285` — 36 `ScreenRegistryEntry` constructions. Each entry carries an optional `seedArgs` list matching the constructor parameters.
- `lib/core/driver/screen_contract_registry.dart:40-212` — 16 `ScreenContract` entries. Each carries `id`, `rootKey`, `routes`, `seedArgs`, `actionKeys`, `stateKeys`.
- `lib/core/driver/flows/forms_flow_definitions.dart` / `navigation_flow_definitions.dart` / `verification_flow_definitions.dart` — per-concern `FlowDefinition` maps composed in `flow_registry.dart:6-10`.

## Signatures

```dart
class ScreenRegistryEntry {
  const ScreenRegistryEntry({ required this.builder, this.seedArgs = const <String>[] });
  final ScreenBuilder builder; // Widget Function(Map<String, dynamic> data)
  final List<String> seedArgs;
}

class ScreenContract {
  const ScreenContract({
    required this.id,
    required this.rootKey,
    required this.routes,
    this.seedArgs = const <String>[],
    this.actionKeys = const <String>[],
    this.stateKeys = const <String>[],
  });
}

class FlowDefinition {
  const FlowDefinition({
    required this.name,
    required this.routes,
    required this.defaultInitialLocation,
    required this.seedScreens,
  });
}
```

## Rules the writer should encode into the plan

1. **`screenContracts.rootKey` must be a typed `TestingKeys.*` sentinel.** String keys in `actionKeys`/`stateKeys` are allowed (and currently used for `<placeholder>` templates), but the screen's root key is typed.
2. **`screenRegistry.seedArgs` ⊆ `screenContracts.seedArgs` for screens that have both.** The writer should spec-check this in the plan for every migrated screen.
3. **Sub-flow YAML `requires:` must map to a precondition name handled by `HarnessSeedData.seedScreenData` or `seedBaseData`.** An unresolved name is a plan-stage failure, not a runtime failure — add a `tools/validate_feature_spec.py` step or a Dart unit test.
4. **`flowRegistry` additions go in the right per-concern file.** Forms flows → `forms_flow_definitions.dart`. Navigation/tab-switch/deep-link flows → `navigation_flow_definitions.dart`. Role/permission verification and form-completeness/export-verification → `verification_flow_definitions.dart`. Do not create a new flow-definitions file per feature — the concern axes already split cleanly.

## Applied to a feature migration

To migrate feature `X` with screens `[FooScreen, BarScreen]`:

1. Add a `FooScreen` + `BarScreen` entry to `screenRegistryEntries` (`screen_registry.dart`).
2. If sync-visible or referenced in a `deep_link_entry` sub-flow, add a matching `ScreenContract` in `screenContracts` (`screen_contract_registry.dart`).
3. If the feature introduces new flow definitions, add them to the matching `*_flow_definitions.dart` file and ensure they are picked up by `flowRegistry`.
4. Add/extend the sentinel key in the owning `lib/shared/testing_keys/<feature>_keys.dart` and re-export via `testing_keys.dart`.
5. Write `.claude/test-flows/features/<feature>.md` with the sub-flow YAML whose `requires:` match new/existing precondition names in `HarnessSeedData`.

Every step above lands in the same commit.
