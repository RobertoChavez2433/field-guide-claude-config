# Layered Issue Report — 2026-04-05 Sync Verification Run

## Purpose
This report consolidates every GitHub issue filed during the April 5, 2026 verification session and organizes them by the repo's layer model so the next implementation session can attack them in a disciplined order.

Where an issue already has an explicit `layer:*` label, that label is treated as canonical.
Where an older issue was filed without layer labels, this report assigns a **recommended primary layer** and optional **secondary layer** for planning.

## Layer Model Used
- `layer:app-wiring` — startup, routing, bootstrap, DI
- `layer:state` — providers, local state refresh, derived UI state
- `layer:presentation` — screens, flows, navigation, interaction UX
- `layer:services` — cross-cutting services, mapping, integration logic
- `layer:shared-ui` — reusable UI primitives, styling, contrast, shared patterns
- `layer:data` — repositories, datasources, models
- `layer:database` — SQLite schema, migrations, persistence structure
- `layer:sync` — sync engine, scope tracking, cursors, Supabase transport
- `layer:auth` — authentication, sessions, consent, rebind semantics
- `layer:tests-tooling` — drivers, test infra, automation keys

## Executive Summary
The issue set splits into three clear clusters:

1. **Sync/control-plane defects**
   These are the highest leverage problems because they create false stale state, broken auto-refresh, and unreliable verification outcomes.
   Core issues: `#204`, `#205`, `#212`, `#224`.

2. **State-refresh / session-consistency defects**
   These make the UI show old values even after successful actions.
   Core issues: `#198`, `#202`, `#225`.

3. **Presentation / UX defects**
   These are numerous and visible, but most are downstream of the first two clusters rather than root causes.

## Recommended Tackle Order
1. Fix `layer:sync` blockers.
2. Fix `layer:auth` and `layer:state` refresh bugs.
3. Re-run sync verification.
4. Then fix presentation and shared-UI issues with fresh confidence in the data flow.

## Issues By Layer

### `layer:sync`

#### `#204` OPEN
- Title: Inspector full sync fails integrity verification and clears cursors after a successful sync cycle
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/204
- Primary layer: `layer:sync`
- Secondary layer: `layer:data`
- Why this layer:
  The defect is in integrity checking, cursor reset behavior, and sync-cycle control flow.
- Evidence depth:
  Confirmed by logs repeatedly. We captured integrity drift lines across multiple tables followed by cursor clears.
- Impact:
  Broad. This can poison subsequent sync behavior and makes other failures harder to interpret.
- Recommended fix order:
  First.

#### `#205` OPEN
- Title: Realtime sync hint RPC registration fails because required Supabase functions are missing
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/205
- Primary layer: `layer:sync`
- Secondary layer: `layer:database`
- Why this layer:
  This is the private-channel / realtime registration path, but the immediate failure is backend schema-cache/RPC availability.
- Evidence depth:
  Confirmed by logs and backend checks.
  We saw `register_sync_hint_channel` failures (`PGRST202`) and `sync_hint_subscriptions` missing from schema cache (`PGRST205`).
- Impact:
  Critical to auto-catch-up, foreground hints, private-channel verification, and rebind behavior.
- Recommended fix order:
  First, with `#204`.

#### `#212` OPEN
- Title: Foreground inspector does not auto-catch-up after admin sync
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/212
- Primary layer: `layer:sync`
- Secondary layer: `layer:state`
- Why this layer:
  The inspector stayed stale until a manual sync was run; the backend row had already changed.
- Evidence depth:
  Confirmed by logs plus backend state plus screenshots.
- Impact:
  High user-facing sync failure. The core promise of foreground freshness is broken.
- Recommended fix order:
  Immediately after `#205`, or in the same fix set if both share root cause.

#### `#224` OPEN
- Title: Android resume quick sync does not catch up remote entry changes
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/224
- Primary layer: `layer:sync`
- Secondary layer: `layer:state`
- Why this layer:
  Resume quick sync did run, but it had no dirty scope and pulled nothing.
- Evidence depth:
  Confirmed by Android lifecycle control through `adb`, logs, backend state, and before/after screenshots.
- Impact:
  High. Resume freshness path is effectively broken even when lifecycle hooks fire.
- Recommended fix order:
  Same workstream as `#212`.

#### `#211` OPEN
- Title: Inspector does not show deletion notification banner after synced project removal
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/211
- Primary layer: `layer:presentation` (canonical label)
- Secondary layer: `layer:sync`
- Why this still matters to sync:
  The data removal succeeded; the missing banner is the user-facing sync acknowledgement failure.
- Evidence depth:
  Confirmed visually after successful delete-cascade verification.
- Impact:
  Medium. Loss of feedback rather than loss of data.
- Recommended fix order:
  After the core sync/control-plane fixes.

### `layer:auth`

#### `#198` CLOSED
- Title: ToS consent is requested again after signing back in
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/198
- Primary layer: `layer:auth`
- Secondary layer: `layer:state`
- Why this layer:
  This is session/consent persistence, not a visual styling defect.
- Evidence depth:
  Originally filed from direct behavior during sign-out/sign-in flow.
- Impact:
  Medium-high trust issue. Re-consent on same account feels like data loss or broken account state.
- Current note:
  Closed upstream, but kept here for historical completeness because it was filed during this run.

### `layer:state`

#### `#202` OPEN
- Title: Quantity picker search text is not cleared after selecting a quantity
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/202
- Primary layer: `layer:state`
- Secondary layer: `layer:presentation`
- Why this layer:
  The stale search value is likely a controller/reset-state bug.
- Evidence depth:
  Visual reproduction.
- Impact:
  Medium. Repeated friction in a common flow.

#### `#225` OPEN
- Title: Settings trash count stays stale after deleting trash and syncing
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/225
- Primary layer: `layer:state`
- Secondary layer: `layer:presentation`
- Why this layer:
  The visible symptom is stale derived state after a successful destructive workflow and sync.
- Evidence depth:
  Visual reproduction from the Settings screenshot.
- Impact:
  Medium. Makes the app look untrustworthy even if the underlying delete succeeded.
- Follow-up verification still needed:
  Confirm whether the source count is stale in provider state or whether the backend/local trash rows truly remain nonzero.

#### `#206` OPEN
- Title: Inspector report can get stuck on Loading after sync and throws a Null-to-String cast error
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/206
- Primary layer: `layer:state`
- Secondary layer: `layer:services`
- Why this layer:
  The visible crash is on the report route after sync, likely due to invalid post-sync view-model/state hydration.
- Evidence depth:
  Confirmed by logs and UI behavior.
- Impact:
  High. This blocks report usage after sync.

### `layer:services`

#### `#210` OPEN
- Title: Entry PDF preview shows mismapped values and fields in the wrong positions
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/210
- Primary layer: `layer:services` (canonical label)
- Secondary layer: `layer:presentation`
- Why this layer:
  This is PDF mapping/filling logic, not primarily screen chrome.
- Evidence depth:
  Confirmed by screenshot plus PDF log lines showing wrong values mapped into fields.
- Impact:
  High. Exported/reporting output is incorrect.

### `layer:presentation`

#### `#199` OPEN
- Title: Review Drafts screen has no way to delete a draft
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/199
- Primary layer: `layer:presentation`
- Secondary layer: `layer:state`
- Why this layer:
  Missing action/affordance on the screen.
- Evidence depth:
  Visual reproduction.
- Impact:
  Medium.

#### `#200` OPEN
- Title: Dashboard Review Drafts action should use the same tile-card style as Start/Continue Entry
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/200
- Primary layer: `layer:presentation`
- Secondary layer: `layer:shared-ui`
- Why this layer:
  This is layout consistency and affordance parity.
- Evidence depth:
  Visual review.
- Impact:
  Low-medium.

#### `#201` OPEN
- Title: Android soft keyboard frequently stays open and blocks action buttons
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/201
- Primary layer: `layer:presentation`
- Secondary layer: `layer:shared-ui`
- Why this layer:
  The failure is in interaction behavior and screen/input handling.
- Evidence depth:
  Reproduced repeatedly during testing.
- Impact:
  High annoyance; can block task completion.

#### `#203` OPEN
- Title: Quantities + button should open the quantity list directly
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/203
- Primary layer: `layer:presentation`
- Secondary layer: `layer:state`
- Why this layer:
  Expected interaction/entry flow mismatch.
- Evidence depth:
  Visual/behavioral.
- Impact:
  Medium.

#### `#209` OPEN
- Title: Forms list shows internal identifier/status instead of friendly form name
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/209
- Primary layer: `layer:presentation` (canonical label)
- Secondary layer: `layer:state`
- Why this layer:
  The UI is surfacing internal identifiers instead of user-facing names.
- Evidence depth:
  Visual reproduction with screenshot.
- Impact:
  Medium.

### `layer:shared-ui`

#### `#207` OPEN
- Title: Dashboard empty-state View Projects button has poor text contrast
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/207
- Primary layer: `layer:shared-ui`
- Secondary layer: `layer:presentation`
- Why this layer:
  Contrast/accessibility issue in a reusable style pattern.
- Evidence depth:
  Visual reproduction from screenshot.
- Impact:
  Medium accessibility problem.

#### `#208` OPEN
- Title: Dashboard project header blue gradient feels visually out of place
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/208
- Primary layer: `layer:shared-ui`
- Secondary layer: `layer:presentation`
- Why this layer:
  This is a visual-system/theme direction issue.
- Evidence depth:
  Visual review.
- Impact:
  Low-medium.

## Closed / Non-Actionable Filing

#### `#213` CLOSED
- Title: App-bar sync icon runs full sync immediately instead of opening Sync Dashboard
- URL: https://github.com/Field-Guide/construction-inspector-tracking-app/issues/213
- Outcome:
  Closed after product clarification. The sync icon is intentionally a global full-sync affordance.
- Why keep it here:
  Prevents re-filing the same non-bug in the next session.

## Cross-Cutting Observations

### 1. Sync defects are creating secondary UI symptoms
Several UI complaints may be downstream of broken freshness paths:
- stale report content
- stale counts
- missing acknowledgement banners
- misleading “synced” feeling when data did not refresh

### 2. The highest-risk cluster is not visual
The biggest technical risk is the combination of:
- broken realtime/private-channel registration (`#205`)
- integrity/cursor instability (`#204`)
- no foreground auto-catch-up (`#212`)
- no reliable resume catch-up (`#224`)

Until those are corrected, every user-visible sync surface is suspect.

### 3. Some older issues still need canonical labels
The earlier filed issues (`#198`-`#208`, `#212`, `#224`, `#225`) do not all carry the newer structured `defect` / priority / `layer:*` labels.
Before implementation starts, it would be worth normalizing labels so GitHub matches this report.

## Suggested Next Session Plan

### Phase 1: Sync Root Causes
- `#205`
- `#204`
- `#212`
- `#224`

### Phase 2: Post-Sync / State Correctness
- `#206`
- `#225`
- `#211`
- `#202`

### Phase 3: PDF Correctness
- `#210`

### Phase 4: UI / UX Cleanup
- `#199`
- `#200`
- `#201`
- `#203`
- `#207`
- `#208`
- `#209`

## Issue Inventory
| Issue | State | Primary Layer | Secondary Layer | Short Name |
|------|-------|---------------|-----------------|------------|
| #198 | CLOSED | `layer:auth` | `layer:state` | ToS re-consent on sign-in |
| #199 | OPEN | `layer:presentation` | `layer:state` | No delete action in Review Drafts |
| #200 | OPEN | `layer:presentation` | `layer:shared-ui` | Review Drafts dashboard card mismatch |
| #201 | OPEN | `layer:presentation` | `layer:shared-ui` | Stuck Android keyboard |
| #202 | OPEN | `layer:state` | `layer:presentation` | Quantity search text not clearing |
| #203 | OPEN | `layer:presentation` | `layer:state` | `+` button opens wrong quantity flow |
| #204 | OPEN | `layer:sync` | `layer:data` | Integrity failures + cursor clears |
| #205 | OPEN | `layer:sync` | `layer:database` | Missing realtime/private-channel RPC path |
| #206 | OPEN | `layer:state` | `layer:services` | Report loading null-cast after sync |
| #207 | OPEN | `layer:shared-ui` | `layer:presentation` | Poor empty-state button contrast |
| #208 | OPEN | `layer:shared-ui` | `layer:presentation` | Unpleasant dashboard header gradient |
| #209 | OPEN | `layer:presentation` | `layer:state` | Forms screen shows internal names |
| #210 | OPEN | `layer:services` | `layer:presentation` | PDF field/value mis-mapping |
| #211 | OPEN | `layer:presentation` | `layer:sync` | Missing deletion notification banner |
| #212 | OPEN | `layer:sync` | `layer:state` | No foreground auto-catch-up |
| #213 | CLOSED | n/a | n/a | Closed by product clarification |
| #224 | OPEN | `layer:sync` | `layer:state` | Resume quick sync misses remote changes |
| #225 | OPEN | `layer:state` | `layer:presentation` | Trash count remains stale |

