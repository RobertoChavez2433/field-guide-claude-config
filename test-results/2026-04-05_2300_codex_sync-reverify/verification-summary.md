# Sync Re-Verification Summary — 2026-04-05

## Verdict

- `#204` status: **verified fixed**
- `#205` status: **verified fixed for registration + teardown semantics**
- `#224` status: **verified fixed at sync/pull layer**
- `#212` status: **still open**

Because `#212` is still open, the sync system is **not** yet bulletproof enough to clear the full sync issue set.

## Evidence

### `#204` Integrity / cursor poisoning

- Inspector full sync logs no longer clear pull cursors after tolerated drift.
- Evidence from debug logs:
  - `INTEGRITY TOLERATED: ... Not resetting cursor.`
  - `Integrity check incomplete or failed; preserving previous last_integrity_check timestamp`
- No new evidence of destructive cursor resets was observed during the rerun window.

### `#205` Private-channel registration / teardown

- Live registration works after the channel generator fix:
  - active rows existed for both devices with distinct opaque `sync_hint:` channel names
  - app logs showed successful subscriptions for both devices
- Rebind teardown initially exposed a client ordering bug:
  - sign-out attempted `deactivate_sync_hint_channel` after auth loss
  - log: `permission denied for function deactivate_sync_hint_channel`
- Client fix applied:
  - sign-out now deactivates the channel before `auth.signOut()`
  - handler dispose skips deactivate RPC when auth is already gone
- Re-verified live after rebuild:
  - before sign-out row: `318ca0b4-d8dc-4cb1-a38c-620ac869d7f9`
  - after sign-out same row revoked at `2026-04-06 00:18:19.783757+00`
  - after sign-in new active row: `0a732b9a-a8ce-4913-ac22-1ddcce548ede`
  - only one active row remained for device `8361b13c-5f53-4cef-8fc4-211edcb21b49`
  - no `deactivate RPC failed` log on rerun

### `#224` Resume quick sync catch-up

- Clean Android rerun:
  - before screenshot: `s12-clean-before-background-rt9.png`
  - server mutation: `RT9 clean resume marker`
  - logs:
    - `App resumed, triggering quick sync`
    - `Quick sync fallback: running scoped incremental pull (no_dirty_scopes)`
    - `quick pull complete: 1 pulled, 0 errors`
- Local device record after resume updated to `RT9 clean resume marker`.
- UI on the already-open report route remained stale until one route refresh.
- After navigating away and back, screenshot `s12-clean-after-navback-rt9.png` showed the updated marker.

### `#212` Foreground auto catch-up

- Still not good enough.
- Foreground server mutation on the shared report entry:
  - inspector remained stale after the wait window: `s13-insp-after-wait-rt5.png`
  - after one route navigation away/back, UI refreshed: `s13-insp-after-navback-rt5.png`
- Post-rebind foreground mutation also remained stale:
  - before: `s19-rerun-before-rt8-report.png`
  - after wait: `s19-rerun-after-wait-rt8.png`
  - after navback: `s19-rerun-after-navback-rt8.png` still stale on `RT7`
- Rebind logs showed channel replacement working, but no automatic post-mutation quick pull was captured after the `RT8` update.

## Conclusion

- The sync control plane is materially improved:
  - private registration works
  - sign-out/sign-in channel replacement now works
  - resume quick sync no longer no-ops when dirty scopes are empty
  - integrity drift no longer poisons later sync cycles
- The remaining blocker is foreground freshness on already-open report UI, especially after rebind.
- Do **not** close the sync issue set yet.
