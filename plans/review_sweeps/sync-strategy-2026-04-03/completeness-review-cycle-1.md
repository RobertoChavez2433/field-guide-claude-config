# Completeness Review — Cycle 1

**Verdict**: REJECT

**Spec:** `.claude/specs/2026-04-03-sync-strategy-codex-spec.md`
**Reviewed:** `.claude/plans/2026-04-03-sync-strategy.md` (3867 lines, 8 phases)
**Tailor:** `.claude/tailor/2026-04-03-sync-strategy-codex/` (12 files)

---

## Spec Coverage Matrix

| Spec Section | Plan Phase/Step | Status |
|---|---|---|
| R1: Three sync modes | Phase 1.1.1 (SyncMode enum) | COVERED |
| R2: Quick sync behavior | Phase 3.1.4 (SyncMode.quick case) | COVERED |
| R3: Full sync behavior | Phase 3.1.4 (SyncMode.full case) | COVERED |
| R4: Maintenance sync (integrity+orphan+company pulls+last_synced_at) | Phase 3.1.4 (SyncMode.maintenance case), Phase 4.1.6 | PARTIAL — see G1 |
| R5: Manual sync in main app chrome | Phase 7.1 (scaffold_with_nav_bar.dart) | COVERED |
| R6: Change log remains push source of truth | No changes to ChangeTracker | COVERED |
| R7: Hint-driven remote freshness | Phase 2 (DirtyScopeTracker), Phase 6 (FCM+Realtime) | PARTIAL — see G2 |
| R8: Full sync is fallback, not default | Phase 5.1 (lifecycle quick), Phase 5.3 (background maintenance) | COVERED |
| R9: Supabase Realtime hint payloads | Phase 6.2 (RealtimeHintHandler), Phase 6.4 (SQL migration) | COVERED |
| R10: FCM hint payloads, quick sync not full | Phase 6.1 (FcmHandler rewrite) | PARTIAL — see G2 |
| R11: Both Supabase Realtime + FCM needed | Phase 6.1 (FCM) + Phase 6.2 (Realtime) | COVERED |
| R12: Startup one-shot quick sync | Phase 5.2 (SyncInitializer startup) | COVERED |
| R13: Foreground hint -> mark dirty -> quick sync | Phase 6.2 (RealtimeHintHandler._handleHint) | COVERED |
| R14: Background FCM -> wake -> quick targeted sync later | Phase 6.1.4 (fcmBackgroundMessageHandler) | PARTIAL — see P1 |
| R15: User taps sync -> Full sync | Phase 7.2 (SyncDashboardScreen FilledButton) | COVERED |
| R16: Dirty-scope-aware system | Phase 2 (DirtyScopeTracker), Phase 1.1.2 (DirtyScope) | COVERED |
| R17: Project+table granularity preferred | Phase 2.1.1 (isDirty checks) | COVERED |
| R18: Non-goals preserved | No changes to triggers or adapter architecture | COVERED |
| R19: App open feels fresh | Phase 5.1.5 (resume quick sync) + Phase 5.2 (startup quick) | COVERED |
| R20: User can force full sync | Phase 7.1 + Phase 7.2 | COVERED |
| R21: Foreground changes reacted to quickly | Phase 6.2 (Realtime handler) | COVERED |
| R22: Background changes wake device | Phase 6.1 (FCM handler) | PARTIAL — see P1 |
| R23: Multi-project no broad sweep on open | Phase 5.1.5 + Phase 2 (dirty scope filtering) | COVERED |
| R24: No real-time collab semantics | Plan does not add collab features | COVERED |

---

## Critical Gaps

**G1: Maintenance sync omits company member pulls and last_synced_at update**
- Spec says (Core Decisions 1, Maintenance sync): "deferred or background work, integrity checks, orphan cleanup, **company member pulls**, **last_synced_at update**"
- Plan: The `SyncMode.maintenance` case inside `SyncEngine.pushAndPull()` (plan line 978-1027) does integrity + orphan + prune + dirty scope prune only. It explicitly says "No push, no pull. This is for background periodic maintenance." (line 982). Company member pulls and last_synced_at updates are gated to `mode == SyncMode.full` only (plan line 1812).
- Additionally, the plan's comment at line 2300 says "Push is still included so pending changes don't accumulate" but the actual maintenance mode implementation does NOT include push. This is an internal contradiction.
- Impact: Background sync (4-hour periodic) currently does full push+pull. After this plan, it will do ONLY integrity+orphan — no push, no pull, no company member sync. This means: (1) local pending changes can accumulate for hours without pushing, (2) company member list is never refreshed unless user manually triggers full sync, (3) last_synced_at is never updated during maintenance.
- Fix: Either (a) add company member pulls and last_synced_at update to the maintenance case in `syncLocalAgencyProjects`, or (b) make background sync use a dedicated mode that includes push + maintenance tasks, or (c) split the spec's maintenance sync definition to match the plan's intent and document the deviation explicitly.

**G2: FCM edge function not updated to send hint payloads**
- Spec says (Remote Invalidation, Background Path): "send a small invalidation payload" and the hint payload shape includes "company_id, project_id, table_name, changed_at, optional scope_type"
- Tailor explicitly identified: "`supabase/functions/daily-sync-push/index.ts` handles the FCM push from server. This needs to be extended to send hint payloads." (fcm-handler-pattern.md line 79)
- Plan: The plan creates a Supabase SQL migration for Realtime broadcast triggers (Phase 6.4) but NEVER modifies the FCM edge function (`supabase/functions/daily-sync-push/index.ts`). Without updating this server-side function, FCM messages will continue to arrive with `type: daily_sync` and no hint fields.
- Impact: The FCM hint parsing code in the plan (Phase 6.1.3) will always fall through to the backward-compat path (no project_id/table_name in payload), meaning FCM can never deliver targeted invalidation hints. The entire "Background / Closed-App Path" from the spec is non-functional.
- Fix: Add a phase (or sub-phase under Phase 6) that modifies `supabase/functions/daily-sync-push/index.ts` to:
  1. Accept hint parameters (project_id, table_name, changed_at)
  2. Send `type: sync_hint` instead of (or in addition to) `type: daily_sync`
  3. Include the hint payload fields in the FCM data message

---

## Partial Coverage

**P1: Background FCM handler cannot mark dirty scopes**
- Spec says (Target Behavior - Background): "server emits FCM data message -> app wakes / schedules work -> quick targeted sync runs later"
- Plan: The `fcmBackgroundMessageHandler` rewrite (plan line 2519-2543) correctly identifies that it runs in a separate isolate with no access to the in-memory `DirtyScopeTracker`. The plan comments "Cannot mark dirty scopes here" and relies on the next foreground resume to trigger a quick sync. However, the quick sync on resume will have NO dirty scopes (tracker is in-memory, app was closed), so it will be push-only with no targeted pull.
- Impact: After a background FCM hint arrives and the app resumes, the quick sync will push local changes but pull nothing (no dirty scopes). The user must manually trigger a full sync to see the remote changes hinted by FCM. This partially defeats the purpose of background FCM hints.
- Fix: Consider persisting dirty scopes to SQLite (a single table with projectId, tableName, markedAt) so they survive app restarts. Or, on startup after FCM background wakeup, upgrade the startup sync from quick to full. Or, document this as an accepted limitation with the spec author.

**P2: Plan has inconsistent SyncMode import paths — references nonexistent file `sync_mode.dart`**
- Plan Phase 1.1.1 defines `SyncMode` in `lib/features/sync/domain/sync_types.dart`
- Multiple later phases (4.1.1, 5.1.2, 5.3.1, 6.1.2, 6.2.2, and test files) import from `lib/features/sync/engine/sync_mode.dart` — a file that is NEVER created in the plan
- Impact: If the implementing agent follows the import paths literally, all these files will fail compilation
- Fix: Replace all instances with the correct path: `sync_types.dart`

**P3: Contradictory SyncInitializer return type between Phase 6.3 and Phase 8.1.4**
- Phase 6.3 (Sub-phase 6.3.2, plan line 2840-2856) changes `SyncInitializer.create` return type to include `RealtimeHintHandler? realtimeHintHandler` and updates all destructuring call sites
- Phase 8.1.4 (plan line 3685-3699) says "No change to return type — DirtyScopeTracker is fully wired internally"
- These two phases contradict each other regarding the SyncInitializer return type.
- Fix: Decide on ONE approach. Either (a) Phase 6.3 adds RealtimeHintHandler to the return type, or (b) RealtimeHintHandler is wired internally and the return type stays unchanged. Remove the contradicting phase.

**P4: Duplicate/overlapping work between Phase 3 and Phase 4**
- Phase 3 (Sub-phases 3.2-3.5) modifies SyncEngineFactory, SyncOrchestrator, and SyncOrchestratorBuilder to wire DirtyScopeTracker and SyncMode
- Phase 4 (Sub-phases 4.1-4.2) modifies the SAME files with SAME changes
- Impact: The implementing agent will attempt the same modifications twice, causing conflicts on the second application
- Fix: Consolidate Phases 3 and 4 into a single phase, or clearly mark Phase 4's sub-phases as "verification only" if Phase 3 already made the changes

---

## Over-Engineering

**O1: Supabase broadcast trigger uses information_schema introspection**
- The SQL migration (Phase 6.4) uses `information_schema.columns` lookups to dynamically determine whether a table has `company_id` or `project_id` columns. This runs on EVERY insert/update/delete across 6 high-volume tables.
- The spec does not require dynamic schema introspection. A simpler approach would use separate trigger functions per table type.

**O2: Detailed SyncDashboard FilledButton UI with snackbar feedback**
- The spec says "user taps top-bar sync action -> app runs Full sync"
- The plan adds a prominent FilledButton.icon with progress spinner, snackbar success/error messages, and a testing key (Phase 7.2). Minor — acceptable gold-plating.

---

## Summary

- **Requirements:** 24 total, 17 met, 4 partially met, 2 not met (G1, G2), 1 covered by non-goal
- **Critical Gaps:** 2 (maintenance sync missing company member pulls/push; FCM edge function never updated)
- **Partial Coverage:** 4 (background FCM dirty scope persistence; import path errors; contradictory SyncInitializer return type; duplicate phases)
- **Over-Engineering:** 2 (dynamic schema introspection in SQL trigger; detailed UI polish beyond spec scope)
