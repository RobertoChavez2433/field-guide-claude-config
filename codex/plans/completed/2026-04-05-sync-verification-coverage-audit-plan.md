# Sync Verification Coverage Audit

Date: 2026-04-05
Author: Codex

## Goal

Determine whether the current sync verification suite actually covers the live
sync system end to end, identify missing tables or weak flows, and recommend a
verification shape that keeps real UI driving as the primary signal.

## Current Verdict

Driving the app is still the right primary approach.

Reason:
- it validates real navigation, keys, buttons, state wiring, and visible user
  outcomes
- it catches defects that pure API or DB verification misses
- it exercises the actual sync triggers users rely on

But the current suite is not yet complete enough to claim full data coverage.
It is best described as:
- strong on core project and entry sync journeys
- weak on some file-backed and user-scoped sync tables
- under-instrumented on local persistence verification

## Sync Registry Baseline

The live sync registry currently registers 22 adapters in
`lib/features/sync/engine/sync_registry.dart`:

1. `projects`
2. `project_assignments`
3. `locations`
4. `contractors`
5. `equipment`
6. `bid_items`
7. `personnel_types`
8. `daily_entries`
9. `photos`
10. `entry_equipment`
11. `entry_quantities`
12. `entry_contractors`
13. `entry_personnel_counts`
14. `inspector_forms`
15. `form_responses`
16. `form_exports`
17. `entry_exports`
18. `documents`
19. `todo_items`
20. `calculation_history`
21. `support_tickets`
22. `user_consent_records`

## Coverage Assessment

### Strong Coverage

These have real user-meaningful create/sync/pull/delete coverage today:

- `projects`
- `project_assignments`
- `locations`
- `contractors`
- `equipment`
- `bid_items`
- `personnel_types`
- `daily_entries`
- `entry_equipment`
- `entry_quantities`
- `entry_contractors`
- `entry_personnel_counts`
- `todo_items`
- `calculation_history`

Why this is strong:
- the flows are UI-driven
- they round-trip through Settings sync
- they are checked in Supabase
- they are checked again on the second device

### Weak Or Partial Coverage

- `photos`
  - Covered as a sync table, but creation uses `inject-photo-direct` in
    `.claude/test-flows/sync/flows-S01-S03.md` instead of the real camera or
    gallery button path.
  - This verifies sync transport, but not the full attachment UX pipeline.

- `documents`
  - Covered in S11, but creation uses `inject-document-direct` in
    `.claude/test-flows/sync/flows-S11-S19.md`.
  - This verifies sync and storage, but not the real document picker flow.

- `inspector_forms`
  - S04 covers forms, but the steps are still high-level and the verification
    explicitly calls out `form_responses`, not a strong `inspector_forms`
    assertion.
  - Coverage exists in spirit, but it is not yet crisp enough to trust as a
    regression guard.

- `form_responses`
  - Covered, but only through one form family and one fairly loose flow.
  - Good starter coverage, not exhaustive.

- `form_exports`
  - Mentioned in delete-cascade checks and storage references, but not verified
    as a first-class sync round-trip: create in UI, push to Supabase, pull to
    another device, and verify local visibility.

- `entry_exports`
  - Same gap as `form_exports`.
  - Export generation is exercised, but sync lifecycle coverage is incomplete.

- S07 "Update All"
  - Good intent, but currently only spot-checks a subset of the tables after
    mutation.
  - It is not yet a true per-table round-trip update verification.

### Missing Coverage

- `support_tickets`
  - Registered sync adapter exists, but there is no S-flow covering support
    ticket create/push/pull/status-update behavior.

- `user_consent_records`
  - Registered sync adapter exists, but there is no S-flow covering consent
    record insert-only push semantics.

## Non-Table Coverage Gaps

### Local Persistence Is Under-Verified

The current framework intentionally favors visual verification and bans
`/driver/local-record`.

That keeps the suite user-realistic, but it leaves an important blind spot:
- a record can look correct in the UI while local SQLite or `change_log` state
  is wrong
- stale queued rows can keep sync "working visually" while the device is
  actually unhealthy
- this exact class of contamination already happened during this verification
  pass

Conclusion:
- UI-only receive verification is not enough for a bulletproof sync system
- it should remain primary, but not exclusive

### File/OS Boundary Flows Need Better Test Shape

Camera, gallery, and native file pickers are hard to automate reliably.
The current suite compensates by injecting files directly.

That is acceptable as a fallback, but it is weaker than ideal because it skips:
- the "Add Photo" button path
- the source picker dialog path
- the "Attach Document" button path
- the provider/controller logic immediately around those user actions

## Recommended Verification Model

Do not replace UI-driven sync verification.

Instead, make it a layered proof for every important flow:

1. UI mutation proof
   - create or edit through the real app screens
   - this remains the source of truth for user realism

2. Cloud proof
   - verify exact rows and storage objects in Supabase

3. Local persistence proof
   - verify exact SQLite rows on both devices by ID
   - verify `change_log` drains or contains only expected items

4. UI receive proof
   - verify the receiving device shows the synced result in the app

5. Log proof
   - verify the sync cycle does not silently finish with errors, stuck retries,
     or unexpected FK skips

That gives you:
- real user flow coverage
- actual transport verification
- local storage correctness
- deterministic failure localization

## Concrete Flow Additions

### Add New First-Class Flows

1. Support Ticket Sync
   - UI: create support ticket from Help/Support screen
   - Cloud: verify `support_tickets` row in Supabase
   - Local: verify row exists locally and sync queue clears
   - Optional admin-side mutation: change status remotely and verify pull back

2. Consent Audit Sync
   - UI: trigger consent accept or revoke path
   - Cloud: verify `user_consent_records` inserts
   - Local: verify insert-only local rows and queue drain
   - Assert no updates or deletes are attempted

3. Entry Export Sync
   - UI: export entry PDF from report/editor path
   - Cloud: verify `entry_exports` row and storage object
   - Local: verify pulled row on second device
   - UI: verify export/document surface shows it if intended

4. Form Export Sync
   - UI: export form PDF from form screen
   - Cloud: verify `form_exports` row and storage object
   - Local: verify pull to second device

### Strengthen Existing Flows

1. Photos
   - keep direct injection as a fallback
   - preferred path: tap real Add Photo UI, then use a deterministic test hook
     only at the OS boundary

2. Documents
   - keep direct injection as a fallback
   - preferred path: tap real Attach Document UI, then return a controlled test
     file from the picker boundary

3. Forms
   - make S04 concrete and assert both `inspector_forms` and
     `form_responses`

4. Update All
   - turn S07 into a real coverage table with explicit per-entity assertions,
     not spot-checks only

## Better Way To Verify While Preserving Real User Flows

Best next-step design:

- keep UI-driven actions for create/edit/delete
- add diagnostics after the action instead of replacing the action

For media/doc flows specifically:
- use UI-first, controlled-boundary testing
- tap the real app buttons
- let the driver return a deterministic gallery/document selection result
- do not bypass the app by inserting the final database row unless the OS
  boundary is completely untestable

That preserves:
- button coverage
- provider/controller coverage
- dialog and state-flow coverage

Without adding:
- flaky camera automation
- flaky system picker automation

## Structural Improvements Needed

1. Generate a sync coverage manifest from `SyncRegistry`
   - source of truth should be the live registry, not hand-maintained docs
   - every adapter should map to at least one verification flow

2. Add per-flow postcondition templates
   - expected local rows
   - expected Supabase rows
   - expected storage objects
   - expected empty or non-empty change log
   - expected sync log markers

3. Tighten cleanup and isolation
   - every run should track exact created IDs
   - teardown should clear remote and local artifacts for those exact IDs
   - old non-`VRF-` historical E2E artifacts should be cleaned once so they stop
     polluting later reruns

4. Fix stale documentation
   - `.codex/skills/test.md` still references removed
     `.claude/test-flows/registry.md` and
     `.claude/test-flows/sync-verification-guide.md`
   - current source of truth is the split `test-flows/sync/` layout

## Recommended Next Execution Order

1. Add a coverage manifest generated from `SyncRegistry`.
2. Add two missing flows:
   - support ticket sync
   - consent audit sync
3. Strengthen export coverage:
   - entry export
   - form export
4. Replace photo/document direct injection as the primary path with UI-first,
   controlled-boundary flows.
5. Add local SQLite and `change_log` assertions to every sync flow.

## Bottom Line

Your instinct is correct: driving the app should stay at the center of sync
verification.

The improvement is not "replace UI with direct DB checks."

The improvement is:
- UI to perform the real user action
- then verify the exact same data at the local DB, sync queue, Supabase row,
  storage object, and receiving UI

That is the shortest path from "online and functioning" to "bulletproof."
