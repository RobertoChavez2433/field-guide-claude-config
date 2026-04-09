# 2026-04-08 Sync Status + Merge Resolution Plan

## Corrected Product Direction

- Keep one existing route and screen: `/sync/dashboard`.
- Treat that screen as the user-facing `Sync Status` surface.
- Do not create a second production `Sync Status` screen.
- Gate raw diagnostics and repair tooling for internal/debug use only.
- Keep user-facing sync conflict handling lightweight:
  - banners
  - notices
  - honest status text
  - simple repair CTA when the device is blocked

## Audit Findings

- `ConflictResolver` is not missing.
  - It exists in `lib/features/sync/engine/conflict_resolver.dart`.
  - It is engine-only LWW winner selection plus `conflict_log` history.
  - It is not a true product merge workflow.
- `ConflictViewerScreen` is a debug/audit surface, not a production merge center.
  - It shows grouped conflict history.
  - It supports `dismiss` and `restore`.
  - It still exposes raw table/record data that should not be the normal user flow.
- The sync dashboard was already trying to serve two audiences at once.
  - users who only need to know whether sync is healthy
  - developers/operators who need fingerprints, bucket breakdowns, and raw conflict tooling
- The missing product seam was provider-owned sync attention state.
  - `SyncProvider` had pending state and generic notifications
  - it did not project blocked queue state or active grouped conflict attention for the shell/app bar/user surface

## Iteration 1 Landed

- `SyncProvider` now projects:
  - `blockedCount`
  - `activeConflictCount`
  - `hasBlockedAttention`
  - `hasConflictAttention`
  - deduped sync notices
- Initial and post-sync surface refresh now reloads:
  - pending buckets
  - grouped conflict count
  - blocked queue count
- New user-facing notices are emitted when:
  - grouped conflict attention increases
  - blocked queue attention increases
- The existing dashboard screen now presents itself as `Sync Status`.
- The existing screen stays one route, but only the user-safe layer is always shown.
- Debug-only on that same screen:
  - grouped/raw conflict log entrypoint
  - device fingerprint card
  - pending bucket breakdowns
  - blocked bucket breakdowns
  - rebuild-diagnostics action
  - stuck-records card
- The raw conflict viewer route `/sync/conflicts` is now debug-only.
- Settings now labels the entrypoint `Sync Status`.
- The sync status actions now include `Report Sync Issue`, which routes to the
  existing help/support flow instead of inventing a second reporting path.
- Shell banners and the sync status icon now reflect:
  - blocked queue attention
  - conflict attention
  - not just transport failure/pending upload state

## Merge Resolution System Design

### What It Is

- Automatic engine resolution remains LWW.
- Product-facing merge resolution becomes an attention/reporting layer on top:
  - the app tells the user when a newer version was kept automatically
  - the app tells the user when local sync is blocked on-device
  - the app routes the user to the single sync status screen

### What It Is Not

- No raw conflict-log editing for normal users.
- No second production screen.
- No field-by-field merge editor in this phase.

### Product Contract

- `Pending` means uploadable local work still queued.
- `Blocked` means local queue rows are stuck and need a repair path.
- `Conflicts` means grouped logical records where one side won automatically.
- Notices explain what happened in user-safe language without exposing table IDs.

## Lint-First Enforcement

### Landed

- `no_sync_conflict_navigation_outside_debug_owners`
  - raw conflict-log navigation now stays inside the approved debug-only owner

### Next Lint Opportunities

- `no_sync_debug_surface_outside_debug_gates`
  - target: sync fingerprint cards, bucket diagnostics, raw repair controls
- `no_sync_dashboard_debug_copy_in_user_surface`
  - target: terms like `conflict_log`, `change_log`, `integrity`, raw table names in user widgets
- `no_conflict_repository_usage_outside_debug_owners`
  - keep raw conflict history access out of product screens/providers

## TODO

### Immediate

- [x] Keep one sync route/screen and remove the split-screen direction from the plan
- [x] Gate conflict viewer route to debug only
- [x] Make the dashboard read as `Sync Status`
- [x] Move grouped conflict and blocked attention into `SyncProvider`
- [x] Add user-safe sync notices and shell/app-bar attention states
- [x] Add a lint boundary around raw conflict-log navigation
- [x] Reuse the existing help/support flow as the user-facing sync issue report path

### Next

- [ ] Define a small sync-issue taxonomy for support reports so user submissions are actionable
- [ ] Add explicit widget/contract tests for:
  - blocked banner visibility
  - conflict notice visibility
  - debug-only conflict action absence in production-gated widget logic
- [ ] Decide whether `Fix Sync Issues` should remain user-visible or become support-assisted only
- [ ] Add a second lint boundary for raw conflict repository access outside debug owners

### Later

- [ ] Add richer conflict reason projection so notices can distinguish:
  - remote newer
  - local newer but push skipped
  - stale-state repaired
- [ ] Consider a structured `SyncAttentionNotice` model instead of plain strings
- [ ] If support burden justifies it, add an operator-only grouped merge/replay tool without exposing raw conflict history to end users

## Honest Remaining Gaps

- This is still not a full merge editor.
- The engine still auto-resolves and logs history.
- The product improvement here is honesty and containment:
  - one user-facing status surface
  - debug tooling kept internal
  - provider-owned attention projection instead of silent drift
