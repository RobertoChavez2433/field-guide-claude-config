# Manual UI Sweep

Use this overlay when the goal is bug discovery across the dashboard surfaces.
Claude manually drives the app through the driver UI/debug server. Helpers may
collect evidence, but they do not decide pass/fail.

## Run Folder

Write one run under:

`.claude/test-results/YYYY-MM-DD_HHMM-manual-ui-rls-sweep/`

Required top-level files:

- `README.md`
- `coverage.md`
- `findings.md`
- `findings.jsonl`
- `run-manifest.json`

Required folders:

- `devices/s21/{logs,screenshots,sync}/`
- `devices/s10/{logs,screenshots,sync}/`
- `features/`
- `rls/by-role/`
- `rls/service-role-checks/`

## Per-Screen Checks

For every screen visited:

- no overflow, clipping, hidden controls, or off-screen primary actions
- forward path works
- back path is intuitive and does not create nested/dead-end screens
- nav switching preserves state or shows the expected discard prompt
- current route/sentinel matches the visible screen
- debug logs show no new runtime/layout/sync errors
- sync banners/status match the actual device state
- role-gated controls match the active role

## Feature Order

1. dashboard
2. projects
3. entries
4. forms
5. pay_applications
6. quantities
7. analytics
8. pdf_imports
9. gallery
10. toolbox
11. calculator
12. todos
13. settings
14. sync_ui
15. contractors
16. harness/debug surfaces
17. role_boundaries

## Screenshot Rule

Capture screenshots at checkpoints, but only review them when:

- the screen is visually ambiguous
- logs report layout/runtime issues
- a control appears missing or clipped
- back/forward flow lands unexpectedly
- sync or permission behavior needs visual proof
- a representative final proof image is useful

## Findings

Every defect goes into both `findings.md` and `findings.jsonl`. A cell cannot
pass when screenshots, logs, sync state, or visible UI behavior show a defect.
