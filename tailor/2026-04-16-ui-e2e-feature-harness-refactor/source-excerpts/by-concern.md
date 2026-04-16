# Source Excerpts — By Concern

---

## Concern: sub-flow verb ↔ driver endpoint mapping

- `/driver/tap` (`driver_interaction_routes.dart:4`) — `tap: <testingKey>`
- `/driver/tap-text` (`driver_interaction_routes.dart:5`) — `tap_text: <literal>`
- `/driver/text` (`driver_interaction_routes.dart:7`) — `text: {key, value}`
- `/driver/wait` (`driver_interaction_routes.dart:11`) — `wait: <testingKey>`
- `/driver/navigate` (`driver_interaction_routes.dart:12`) — `navigate: <path>` (deep-link sub-flow)
- `/driver/back` (`driver_interaction_routes.dart:10`) — `back` (back_at_root, backward_traversal sub-flows)
- `/driver/current-route` (`driver_interaction_routes.dart:15`) — `current_route: <path>` assertion
- `/driver/find` (`driver_shell_handler.dart:19`) — `find: <sentinelKey>` assertion
- `/driver/scroll` + `/driver/scroll-to-key` (`driver_interaction_routes.dart:8-9`) — optional sub-flow steps
- `/driver/dismiss-keyboard` (`driver_interaction_routes.dart:13`) — every text-entry step on Android per `.claude/skills/test/SKILL.md` Sync Hard Rule 3 (still applies in UX context after soft keyboard shows)

Every step verb in the feature-spec YAML must map to one of these endpoints.

---

## Concern: precondition seeding path

The seed endpoint path (new) sits atop:

- `seedBaseData(dbService)` (`harness_seed_data.dart:40-154`) — baseline project/user/locations/contractor/personnel/bid-item/entry.
- `seedScreenData(dbService, screen, data)` (`harness_seed_data.dart:213-234`) — per-screen dispatch switch.
- `seedPayAppData(dbService, data)` (`harness_seed_pay_app_data.dart`) — pay-app detail + comparison seeding.
- `_seedFormData(dbService, data)` (`harness_seed_data.dart:236-…`) — form-response + inspector-form rows.

Feature-spec `requires: [baseline]` → `seedBaseData`. `requires: [pay_app_draft]` → `seedPayAppData` or a new per-feature seeder matching the pattern.

---

## Concern: role collapse rules

From `lib/features/auth/data/models/user_role.dart`:

```dart
enum UserRole { admin, engineer, officeTechnician, inspector }
bool get canManageProjects => this == admin || this == engineer || this == officeTechnician;
bool get canEditFieldData => true;
bool get isAdmin => this == admin;
```

Spec matrix collapse rules resolved:

| Spec rule | YAML `roles` |
|---|---|
| Admin-only surfaces (admin-dashboard, personnel-types, trash) | `[admin]` |
| Project-management surfaces (pay_apps, analytics, pdf import, project-setup mutations) | `[admin, engineer, officeTechnician]` |
| Field-data features (forward_happy) | `[admin, engineer, officeTechnician]` + companion `role_restriction` sub-flow with `[inspector]` |
| Read-only everywhere else | `[admin, engineer, officeTechnician, inspector]` |

---

## Concern: sentinel key conventions (from existing per-feature key files)

- File suffix: `<feature>_keys.dart`
- Class suffix: `<Feature>TestingKeys`
- Sentinel literal: lowercase snake-case of screen name + `_screen` — e.g. `sync_dashboard_screen`, `conflict_viewer_screen`, `form_gallery_screen`, `project_list_screen`, `entries_list_screen`.
- Factory keys: `Key('<kind>_<subject>_$id')`, e.g. `Key('conflict_card_$conflictId')`, `Key('project_card_$projectId')`.
- Facade delegation: `static const fooSentinel = FeatureTestingKeys.fooSentinel;` in `testing_keys.dart`.

---

## Concern: route literals needed by `deep_link_entry`

Each feature's `deep_link_entry` sub-flow MUST reference an existing `go_router` path. The route table in `dependency-graph.md` is exhaustive. Path parameters resolve via `state.pathParameters`:

- `/entry/:projectId/:date` requires both params.
- `/form/:responseId` requires the response id.
- `/pay-app/:payAppId` requires the pay app id.
- `/pay-app/:payAppId/compare` requires pay app id.
- `/analytics/:projectId` requires project id.
- `/import/preview/:projectId` and `/mp-import/preview/:projectId` require `state.extra` of specific types (`BidItemJobResult`/`PdfImportResult` vs `MpJobResult`/`MpExtractionResult`) — a `navigate` step alone cannot reach these without the extra, so either extend seed to set `state.extra` through a route-extra registry, or route these sub-flows through a seed step that populates an "imported" record and deep-links to the **non-preview** consumer screen.

Flag: `/review` and `/review-summary` use `state.extra` and redirect to `/` when null. `deep_link_entry` is not meaningful for these screens — treat them as `forward_happy`-only per spec § Sub-flow Catalog collapse rule.

Flag: `/sync/conflicts` is only registered in `kDebugMode` (see `lib/core/router/routes/sync_routes.dart:15-19`). Release builds cannot reach it.

---

## Concern: rubric item enforcement anchors

| Rubric | Anchor |
|---|---|
| 1. Design tokens | `rules/frontend/flutter-ui.md` + `FieldGuideColors.of(context)` / `Theme.of(context).colorScheme.*`. |
| 2. Testing keys | `rules/testing/testing.md` ("Use `TestingKeys`, not hardcoded `Key('…')` values"). |
| 3. Sentinel key per screen | `screen_contract_registry.dart::ScreenContract.rootKey` field. |
| 4. File size 300 | `scripts/audit_ui_file_sizes.ps1`. |
| 5. Decomposition | Existing `_mixin.dart` / `_helpers.dart` / `_actions.dart` split. |
| 6. Wiring integrity | `di/*screen_providers.dart` + architecture rule "Build dependencies through the typed DI containers". |
| 7. `go_router` compliance | `lib/core/router/routes/*.dart`; no raw `Navigator.push` in `lib/features/**/presentation/`. |
| 8. Back behavior | `router.canPop` in `driver_interaction_handler_navigation_routes.dart:90`; feature spec `back_at_root` assertion. |
| 9. Responsive | Existing breakpoints + LayoutBuilder uses in features; device matrix S21 (360dp) / S10 (~800dp). |
| 10. Mounted guard | `rules/frontend/flutter-ui.md` ("Check `mounted` after async gaps"). |
| 11. Driver contract | `screenRegistry` + `screenContracts` + `flowRegistry` three-way membership. |

---

## Concern: existing flow ID coverage to retire

Old 121-flow map is authoritative in `.claude/test-flows/flow-dependencies.md`. Every retired ID must appear in some feature `.md`'s `Retired flow IDs` block. Spec § Old-Tier → New-Feature Mapping pre-assigns:

| IDs | New file | Notes |
|---|---|---|
| T01-T04 | `auth.md` | |
| T05-T14 | `projects.md` | T14 = search |
| T15-T30 | `entries.md` | tiers 2 + 3 |
| T31-T34 | `todos.md` | |
| T35-T37, T43, T74 | `forms.md` | |
| T38-T39 | `calculator.md` | |
| T40 | `gallery.md` | |
| T41-T42 | owning feature's `export_verification` | |
| T44-T52 | `settings.md` | |
| T53-T58 | `settings.md` (admin) + `projects.md` (archive) | |
| T59-T67 | per feature | |
| T68-T77 | per feature | |
| T85-T91 | `role_restriction` sub-flows | |
| T92-T96 | `nav_bar_switch_mid_flow` / `deep_link_entry` | |
| P01-P05 | `pay_applications.md` | |
| P06 | sync harness | out of scope |
| M01-M13 | UX-relevant absorbed per feature; sync-only untouched | spec flagged gap #7 |
| S01-S21 | sync harness | out of scope |
