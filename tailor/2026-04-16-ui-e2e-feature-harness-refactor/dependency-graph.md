# Dependency Graph

## Driver Surface (HTTP layer)

```
DriverServer (lib/core/driver/driver_server.dart)
├── DriverDiagnosticsHandler       — design-system diagnostics
├── DriverDeletePropagationHandler — `/driver/delete-*`
├── DriverFileInjectionHandler     — `/driver/inject-file`
├── DriverDataSyncHandler          — uses DriverDataSyncRoutes (11 endpoints)
│   ├── part driver_data_sync_handler_maintenance_routes.dart
│   ├── part driver_data_sync_handler_mutation_routes.dart
│   └── part driver_data_sync_handler_query_routes.dart
├── DriverShellHandler             — uses DriverShellRoutes (ready/find/screenshot/tree/hot-restart)
└── DriverInteractionHandler       — uses DriverInteractionRoutes (12 endpoints)
    ├── part driver_interaction_handler_gesture_routes.dart
    ├── part driver_interaction_handler_navigation_routes.dart
    └── part driver_interaction_handler_system_routes.dart
```

Handlers are tried in strict order in `_handleRequest`. Any new `/driver/seed` endpoint must slot in ahead of the final `404` return — the existing convention is: every handler owns a `*Routes.matches(path)` shortcut and returns `false` when it does not own the path.

## Screen Contracts, Screen Builder, and Flow Registry

```
screenRegistry (screen_registry.dart)        — 36 entries, Widget builders for /driver/set-screen
screenContracts (screen_contract_registry.dart) — 16 entries with rootKey + routes + action/state keys
flowRegistry (flow_registry.dart)            — union of:
  ├── formsFlowDefinitions (flows/forms_flow_definitions.dart)
  ├── navigationFlowDefinitions (flows/navigation_flow_definitions.dart)
  └── verificationFlowDefinitions (flows/verification_flow_definitions.dart)
```

All three are independent maps keyed by screen id or flow name. The spec's "Registries kept in sync" rule means a feature spec migration must touch all three files in the same commit when introducing a new screen + sub-flow.

## Harness Seed

```
HarnessSeedData (harness_seed_data.dart)
├── HarnessSeedDefaults (harness_seed_defaults.dart)  — string IDs (defaultProjectId, …)
├── HarnessPayAppSeedData (harness_seed_pay_app_data.dart)
├── seedBaseData() — idempotent: _clearBaseSeedRows + re-insert projects/locations/contractors/…
└── seedScreenData(dbService, screen, data) — per-screen precondition seeding
    ├── _seedFormData  (MdotHubScreen/FormGalleryScreen/FormViewerScreen/QuickTestEntryScreen/ProctorEntryScreen/WeightsEntryScreen)
    └── seedPayAppData (PayApplicationDetailScreen/ContractorComparisonScreen)
```

Downstream importers of `HarnessSeedData` / defaults are:
- `screen_registry.dart` (default ids for builders)
- `driver_interaction_handler` (set-screen seeding path)
- form/pay-app seeding code paths

This is the existing shape that `/driver/seed` must lean on — do **not** create a parallel fixture loader.

## Router (go_router) Path Ownership

```
lib/core/router/app_router.dart  — composes route modules
├── authRoutes()       — /login, /register, /forgot-password, /verify-otp, /update-password, /update-required, /consent, /profile-setup, /company-setup, /pending-approval, /account-status
├── projectRoutes()    — /project/new, /project/:projectId/edit, /quantities, /quantity-calculator/:entryId
├── entryRoutes()      — /entry/:projectId/:date, /report/:entryId, /entries, /drafts/:projectId, /review, /review-summary, /personnel-types/:projectId
├── formRoutes()       — /import/preview/:projectId, /mp-import/preview/:projectId, /form/new/:formId, /form/:responseId
├── toolboxRoutes()    — /toolbox, /forms, /calculator, /gallery, /todos
├── settingsRoutes()   — /settings/trash, /settings/saved-exports, /edit-profile, /admin-dashboard, /help-support, /legal-document, /oss-licenses
├── payAppRoutes()     — /pay-app/:payAppId, /pay-app/:payAppId/compare, /analytics/:projectId
└── syncRoutes()       — /sync/dashboard, /sync/conflicts (kDebugMode only)
```

`deep_link_entry` sub-flow MUST drive `/driver/navigate` at a path that exists in the table above. `/sync/conflicts` is `kDebugMode`-only; matrix collapse rules must reflect that.

## Testing Keys Facade

```
testing_keys.dart (shared)
├── exports + delegates from 16 per-feature key files
├── TestingKeys facade class  — static accessors that forward to per-feature key classes
└── feature key files:
    auth_keys.dart, common_keys.dart, consent_keys.dart, contractors_keys.dart,
    documents_keys.dart, entries_keys.dart, locations_keys.dart, navigation_keys.dart,
    pay_app_keys.dart, photos_keys.dart, projects_keys.dart, quantities_keys.dart,
    settings_keys.dart, support_keys.dart, sync_keys.dart, toolbox_keys.dart
```

New sentinel keys MUST live in the owning per-feature file and be re-exported by `testing_keys.dart`. Blind additions directly to `TestingKeys` break the facade pattern.

## Test-Flow Docs

```
.claude/test-flows/
├── flow-dependencies.md          — REWRITE as feature taxonomy index
├── tiers/*.md (7 files)          — DELETE after per-feature cutover
├── features/*.md (NEW, 16 files) — per spec § Feature Taxonomy
└── sync/*.md (5 files)           — UNTOUCHED (S01-S21 + framework)
```

`.claude/skills/test/SKILL.md` lists `tiers/*` paths explicitly in the "Required References" block — the skill must be updated in the same PR to point at `features/*`.
