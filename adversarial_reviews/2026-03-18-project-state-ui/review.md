# Adversarial Review: Project State UI & Assignments

**Spec**: `.claude/specs/2026-03-18-project-state-ui-spec.md`
**Date**: 2026-03-18
**Reviewers**: code-review-agent, security-agent

## MUST-FIX (6 items — all addressed in spec update)

### MF-1: Add `ENABLE ROW LEVEL SECURITY` to migration
Without it, all RLS policies are advisory-only. Cross-company data fully exposed.
**Resolution**: Added to migration DDL.

### MF-2: Enforce `assigned_by = auth.uid()` server-side
Client can spoof `assigned_by` to attribute assignments to other admins.
**Resolution**: Added `enforce_created_by()` trigger + INSERT policy check.

### MF-3: Cross-company assignee injection
INSERT policy doesn't verify `user_id` belongs to same company.
**Resolution**: Added `user_id IN (SELECT id FROM user_profiles WHERE company_id = get_my_company_id() AND status = 'approved')` to INSERT WITH CHECK.

### MF-4: "Unassigned" badge has no data source
Assignment deletion removes the row. No tombstone for badge to read.
**Resolution**: Added `unassigned_at TEXT` column to `synced_projects`. Assignment adapter writes this on detected deletion.

### MF-5: Auto-enrollment injection point unspecified
Spec said "on pull" without saying where in the engine.
**Resolution**: Specified as post-pull callback: `adapter.onPullComplete(pulledRows, currentUserId)` called by engine after each table's pull.

### MF-6: Document data access model for self-enrollment
Self-enrollment lets any inspector pull any company project data.
**Resolution**: Documented: assignments are organizational, not access-control. RLS scopes by company_id. Self-enrollment is allowed but assignment status is visible on cards.

## SHOULD-CONSIDER (8 items — decisions made)

### SC-7: Assignment pull scope
**Decision**: Scoped SELECT RLS — inspectors see only their own assignments, admins/engineers see all. One adapter, server handles scoping.

### SC-8: Missing triggers
**Decision**: Add both `enforce_insert_updated_at` and `update_updated_at_column` triggers for consistency.

### SC-9: SyncProvider notification mechanism
**Decision**: Pending notifications queue (`List<String> pendingNotifications`). UI checks after sync, shows snackbars, provider clears them.

### SC-10: Magic string filter
**Decision**: Use proper Dart enum `CompanyFilter { all, onDevice, notDownloaded }`.

### SC-11: Stale role retry loop
**Decision**: Skip — user says this will never happen in practice. Existing RLS denial logging is sufficient.

### SC-12: Draft-project assignment orphan
**Decision**: Hold assignments in-memory until wizard save. Same pattern as locations/contractors. No orphan risk.

### SC-13: Archived tab access model
**Decision**: Respect assignments. Only assigned members can download archived projects. Unassigned members see metadata only.

### SC-14: Legacy screen deletion
**Decision**: Delete + full GoRouter route audit. Remove all navigation paths.

## NICE-TO-HAVE (4 items — all included)

### NH-15: Drop redundant `created_at` — keep `assigned_at` only
### NH-16: Add `company_id` column for integrity RPC support
### NH-17: Single-pass computation of all 3 tab lists
### NH-18: Audit log entries (`RAISE LOG`) for assignment INSERT/DELETE
