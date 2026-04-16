# Pattern — Feature Spec Markdown (prose + fenced YAML)

The spec (§ Per-Feature `.md` Template) defines the skeleton. This pattern nails down how it must render so the runner can parse it deterministically.

## Skeleton (from spec, verbatim)

```markdown
# Feature: <name>

## Purpose
<one paragraph>

## Screens
- <screen_name>: <file path>
- ...

## Preconditions catalog
<each named precondition used by sub-flows below>

## Sub-flows

```yaml
- name: forward_happy
  requires: [project_draft, location_a]
  appliesTo:
    roles: [admin, inspector]
    devices: [s21, s10]
  steps:
    - tap: <TestingKey>
    - text: { key: <TestingKey>, value: "..." }
    - wait: <TestingKey>
  assertions:
    - find: <sentinel_key>
    - currentRoute: <expected path>
```

## Retired flow IDs
<list of T##, P##, M## IDs this feature replaces>
```

## Reusable conventions

### Step verbs (must match existing `/driver/*` endpoints from `DriverInteractionRoutes`)

| YAML verb | Driver endpoint | Payload |
|---|---|---|
| `tap` | `POST /driver/tap` | `{"key": "<testing_key_string>"}` |
| `tap_text` | `POST /driver/tap-text` | `{"text": "…"}` |
| `text` | `POST /driver/text` | `{"key": "…", "value": "…"}` |
| `wait` | `GET /driver/wait?key=…` | URL param |
| `scroll` | `POST /driver/scroll` | `{"direction": "down"/"up"/…}` |
| `scroll_to_key` | `POST /driver/scroll-to-key` | `{"key": "…"}` |
| `drag` | `POST /driver/drag` | `{"from": {…}, "to": {…}}` |
| `back` | `POST /driver/back` | — |
| `navigate` | `POST /driver/navigate` | `{"path": "/<route>"}` |
| `dismiss_keyboard` | `POST /driver/dismiss-keyboard` | — |
| `dismiss_overlays` | `POST /driver/dismiss-overlays` | — |

### Assertion verbs

| YAML verb | Driver endpoint | Meaning |
|---|---|---|
| `find` | `GET /driver/find?key=…` | `exists === true`, `enabled/visible` optional |
| `current_route` | `GET /driver/current-route` | string equality on `route` |
| `pdf_fields_populated` | (new helper — see `patterns/pdf-acroform-helper.md`) | every expected AcroForm field has a non-empty value |
| `pdf_is_acroform` | (same helper) | form dictionary + non-zero field count |

### YAML keys

- `name` — kebab or snake case, must match the `Sub-flow Catalog` names: `forward_happy`, `backward_traversal`, `nav_bar_switch_mid_flow`, `back_at_root`, `deep_link_entry`, `tab_switch_mid_edit`, `orientation_change`, `form_completeness`, `export_verification`, `role_restriction`. Omit sub-flows that do not apply; missing means N/A, not failure (spec § Sub-flow Catalog).
- `requires` — precondition names from the feature's `Preconditions catalog` section. Validator matches against `HarnessSeedData.seedScreenData` switch + feature-owned seeders.
- `appliesTo.roles` — subset of `[admin, engineer, officeTechnician, inspector]`. MUST align with `lib/features/auth/data/models/user_role.dart` flags (role gating column in spec § Feature Taxonomy).
- `appliesTo.devices` — subset of `[s21, s10]`.
- `steps` — ordered list; YAML sequence items.
- `assertions` — ordered list; last step failure aborts the sub-flow.

### `TestingKey` references in YAML

Write the sentinel string exactly as produced at runtime (`'sync_dashboard_screen'` — not `TestingKeys.syncDashboardScreen`). Keys with an id parameter (e.g. `locationDeleteButton(id)`) use a placeholder syntax: `'location_delete_button_<locationId>'`, matching how `screenContracts` already renders placeholders (`driver_data_sync_routes.dart` has no such templates, but `screenContracts.actionKeys` does — see `screen_contract_registry.dart:45-51`).

## Retired flow IDs block

Spec § Old-Tier → New-Feature Mapping gives the starting assignment. Each feature `.md` must list the old IDs it absorbs verbatim from that table. This block exists so `.claude/test-flows/tiers/*.md` deletion is safe — every old ID has a new home.
