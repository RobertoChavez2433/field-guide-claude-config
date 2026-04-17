# Manual UI + RLS E2E Testing Checklist Plan

## Summary

This is the corrective execution layer for
`.claude/specs/2026-04-16-ui-e2e-feature-harness-refactor-spec.md`.
The spec remains the implementation and verification gate; this checklist
standardizes how Claude must manually drive the app, collect evidence, and
log bugs without treating route-only runner output as a pass.

Anthropic guidance applied:

- Keep instructions clear, sequential, and specific:
  https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/be-clear-and-direct
- Use structured sections so results can be parsed and resumed:
  https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags
- Keep helper agents/tools focused instead of making one broad runner decide:
  https://docs.anthropic.com/en/docs/claude-code/sub-agents
- Evaluate against explicit success criteria:
  https://docs.anthropic.com/en/docs/test-and-evaluate/define-success

## Implementation Checklist

- [x] Save this file under `.codex/plans/`.
- [x] Add this file to `.codex/PLAN.md`.
- [x] Keep `.claude/specs/2026-04-16-ui-e2e-feature-harness-refactor-spec.md`
      as the final completion gate.
- [x] Update `.claude/skills/test/SKILL.md` so UI E2E is explicitly a
      manual bug-discovery workflow, not a route-only runner pass.
- [x] Add a concise manual sweep reference under `.claude/test-flows/manual/`.
- [x] Add a concise RLS/role-boundary reference under `.claude/test-flows/manual/`.
- [x] Do not add test-only production hooks, fake auth, `MOCK_AUTH`, lint
      ignores, analyzer excludes, or flow skips unless the user approves a
      specific spec amendment.

## Manual Test Method

- [ ] Use S21 as the primary phone device and S10 as the tablet comparison.
- [ ] Drive the app manually through the driver UI/debug server; Claude is the
      user.
- [ ] Use helpers only to collect evidence: logs, current route/screen, sync
      state, screenshots, and artifact files.
- [ ] Do not use a broad autonomous runner to decide pass/fail.
- [ ] Review screenshots only when a screen is ambiguous, a visual issue is
      suspected, logs report layout/runtime issues, or a representative proof
      image is needed.
- [ ] Treat overflow, clipped controls, broken back flow, nested-screen
      confusion, runtime errors, sync errors, stale sync state, permission
      leaks, and role UI mismatches as failures.

## Required Run Folder

Create one folder per sweep:

`.claude/test-results/YYYY-MM-DD_HHMM-manual-ui-rls-sweep/`

Required files and folders:

- [ ] `README.md`
- [ ] `coverage.md`
- [ ] `findings.md`
- [ ] `findings.jsonl`
- [ ] `run-manifest.json`
- [ ] `devices/s21/device.md`
- [ ] `devices/s21/logs/`
- [ ] `devices/s21/screenshots/`
- [ ] `devices/s21/sync/`
- [ ] `devices/s10/device.md`
- [ ] `devices/s10/logs/`
- [ ] `devices/s10/screenshots/`
- [ ] `devices/s10/sync/`
- [ ] `features/dashboard.md`
- [ ] `features/projects.md`
- [ ] `features/entries.md`
- [ ] `features/forms.md`
- [ ] `features/pay_applications.md`
- [ ] `features/quantities.md`
- [ ] `features/analytics.md`
- [ ] `features/pdf_imports.md`
- [ ] `features/gallery.md`
- [ ] `features/toolbox.md`
- [ ] `features/calculator.md`
- [ ] `features/todos.md`
- [ ] `features/settings.md`
- [ ] `features/sync_ui.md`
- [ ] `features/contractors.md`
- [ ] `features/harness.md`
- [ ] `features/role_boundaries.md`
- [ ] `rls/matrix.md`
- [ ] `rls/by-role/admin.md`
- [ ] `rls/by-role/engineer.md`
- [ ] `rls/by-role/officeTechnician.md`
- [ ] `rls/by-role/inspector.md`
- [ ] `rls/service-role-checks/`

## Finding Schema

Every finding in `findings.jsonl` must include:

- [ ] `id`
- [ ] `severity`: `blocker`, `high`, `medium`, or `low`
- [ ] `category`
- [ ] `feature`
- [ ] `device`
- [ ] `role`
- [ ] `route`
- [ ] `screen`
- [ ] `steps`
- [ ] `expected`
- [ ] `actual`
- [ ] `logEvidence`
- [ ] `screenshotEvidence` when useful
- [ ] `syncEvidence` when relevant
- [ ] `status`: `open`, `fixed`, `retest-needed`, `spec-gap`, or `blocked`

Allowed categories:

- [ ] `ui_overflow`
- [ ] `layout_clipping`
- [ ] `missing_control`
- [ ] `broken_forward_flow`
- [ ] `broken_back_flow`
- [ ] `nested_screen_flow`
- [ ] `route_mismatch`
- [ ] `runtime_error`
- [ ] `sync_error`
- [ ] `sync_stale_state`
- [ ] `sync_conflict`
- [ ] `rls_policy`
- [ ] `permission_boundary`
- [ ] `cross_company_leak`
- [ ] `role_ui_mismatch`
- [ ] `test_harness_gap`
- [ ] `spec_gap`

## Feature Coverage Checklist

Authentication password update/reset flows are not a priority unless they block
dashboard access.

- [ ] Dashboard: root, primary tabs, dashboard cards/links, back flow, S21/S10
      layout.
- [ ] Projects: list, create/edit, details, locations, contractors, bid items,
      assignments, archive/restore/trash, search/filter, inspector denial.
- [ ] Entries: list, drafts, editor, review, summary, PDF preview/export,
      photo/gallery, quantity calculator, personnel/equipment/contractor entry
      points, edit/back/nav-switch behavior.
- [ ] Forms: MDOT hub, dispatcher, 1126, 1174R, generic fill, viewer, gallery,
      PDF preview, proctor, quick test, weights, preview/export integrity.
- [ ] Pay applications: detail, draft/edit/save, contractor comparison, export,
      back flow, inspector denial.
- [ ] Quantities: list, calculator, add/edit/delete, entry-linked flow, S21
      keyboard/layout.
- [ ] Analytics: project analytics, drilldowns, empty/loading/error states,
      export if available, inspector denial.
- [ ] PDF imports: PDF preview, M&P preview, accept/cancel/back, invalid staged
      result, inspector denial.
- [ ] Gallery: open, view, add/import/delete/share if available, back to source,
      tablet grid.
- [ ] Toolbox: toolbox root, every tile/link, back to toolbox/dashboard.
- [ ] Calculator: HMA, concrete, inputs, reset/clear, outputs, S21 keyboard,
      tab-switch state.
- [ ] To-dos: list, create/edit/complete/delete, linkage if present, back/nav
      switch during edit.
- [ ] Settings: root, profile, saved exports, legal, OSS, app lock, consent,
      support, admin dashboard, personnel types, trash, non-admin denial.
- [ ] Sync UI: dashboard, icons/banners, manual sync, debug conflict viewer,
      stale/repair/conflict/offline banners, cross-device state comparison.
- [ ] Contractors: selection, add/edit/select where available, comparison entry
      points, nested back flow.
- [ ] Harness/debug: driver ready/find/navigation, debug log server on both
      devices, concise logs, organized artifacts.

## RLS And Role Boundary Checklist

Roles:

- [ ] `admin`
- [ ] `engineer`
- [ ] `officeTechnician`
- [ ] `inspector`

Expected boundaries:

- [ ] Admin: full company/team/admin/project powers.
- [ ] Engineer: project-management and field-data powers; not admin-only
      company/team powers.
- [ ] Office Technician: project-management and assignment-related powers; not
      admin-only company/team powers.
- [ ] Inspector: field-data edit powers; denied project-management/admin/
      pay-app/analytics/pdf-management surfaces where policy says denied.

Manual RLS flows:

- [ ] Assigned project is visible.
- [ ] Unassigned project is hidden or denied.
- [ ] Cross-company project is hidden or denied.
- [ ] Project create/edit/archive/delete/restore matches role policy.
- [ ] Project assignment insert/remove/soft-delete matches role policy.
- [ ] Field-data edits work for all allowed roles: entries, forms, quantities,
      to-dos, photos/gallery, contractors where intended.
- [ ] Pay application access/mutation is denied to inspector and allowed to
      project-management roles.
- [ ] Analytics access is denied to inspector and allowed to project-management
      roles.
- [ ] PDF import management is denied to inspector and allowed to
      project-management roles.
- [ ] Admin settings, member approval, role change, deactivation, personnel
      types, and trash are denied to non-admin roles where policy requires.
- [ ] Soft-delete visibility and restore behavior match role policy.
- [ ] Export/document/form ownership does not leak across project or company
      boundaries.
- [ ] Sync push/pull respects RLS on both S21 and S10.

RLS evidence rule:

- [ ] Every denied path records UI behavior and backend/log behavior where
      possible.
- [ ] Service-role checks are verification-only and never the app actor.
- [ ] UI/backend disagreement is logged as `role_ui_mismatch` or
      `permission_boundary`.

## Verification Gates

- [ ] Static gate:
      `flutter analyze`,
      `dart run custom_lint`,
      `pwsh -File scripts/audit_ui_file_sizes.ps1`,
      `python scripts/validate_sync_adapter_registry.py`,
      `python tools/validate_feature_spec.py --all`,
      `python tools/validate_retired_flow_ids.py`.
- [ ] Manual device gate: every in-scope feature and every role-expanded YAML
      subflow cell is manually exercised across S21 and S10 unless explicitly
      collapsed by spec.
- [ ] Log gate: debug logs and sync state are reviewed on both devices after
      each feature group.
- [ ] Bug gate: every UI, route, sync, runtime, permission, and RLS defect is
      logged before a cell is considered complete.
- [ ] Spec gate: re-read the 2026-04-16 UI E2E spec and compare every success
      criterion against `coverage.md`, feature reports, `rls/matrix.md`, and
      open findings.
