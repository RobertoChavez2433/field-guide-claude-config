# Pay Application Implementation And Sync Verification Plan

Date: 2026-04-06
Author: Codex
Source of truth: `.claude/specs/2026-04-05-pay-application-spec.md`

## Purpose

Implement the approved Pay Application feature exactly as captured in the
spec. This plan replaces the prior drifted content in this file and treats the
spec as authoritative if any plan detail disagrees.

## Locked Scope

### In Scope

1. Unified export-history architecture via parent `export_artifacts`
2. Pay Application `.xlsx` export with saved pay-app detail records
3. Exported Forms history integration for saved pay apps
4. Contractor pay-app comparison and standalone discrepancy PDF export
5. Project analytics updates, including `change since last pay app`
6. Sync registration and verification for saved exported artifacts
7. Test-flow and verification-doc updates required by the new feature

### Out Of Scope

- Change orders / contract modification workflows
- Retainage calculations
- Stored materials tracking
- AASHTOWare API integration
- In-app editing of saved exported pay applications
- Automatic write-back from contractor comparison into tracked data
- Multi-project aggregation

## Product Rules That Must Not Drift

- Pay apps persist only on export.
- Saved pay apps are read-only snapshots in-app.
- Exact same `project + period_start + period_end` is the pay-app identity.
- Re-export of the exact same range prompts for replacement.
- Replacement reuses the prior pay-app number unless the user overrides it.
- Overlapping non-identical pay-app ranges are blocked.
- Pay-app numbers are chronological, unique per project, and auto-assigned with
  user override.
- Saved pay-app status is `exported` for v1.
- Exported Forms history is a filtered exported-artifact browser, separate from
  editable saved form responses.
- Contractor comparison starts from a saved pay-app detail screen.
- Contractor comparison does not write back to project data in v1.
- Contractor comparison produces a standalone PDF discrepancy report only.
- Imported contractor files are ephemeral and are not retained.
- AppTerminology must be respected throughout copy and UI labels.

## Delivery Tracks

### 1. Export Artifact Foundation

Deliver the shared export-history layer first so pay apps and future exports
share one architecture.

Work:
- Add `export_artifacts` schema, model, repository, provider, adapter config,
  and change-log triggers
- Add `pay_applications` schema, model, repository, provider, adapter config,
  and change-log triggers
- Bump the local schema version and verifier coverage for the new tables
- Register `export_artifacts` before `pay_applications` in sync
- Route pay-app files through the parent artifact row and existing file-sync
  pipeline
- Support soft delete fields and FK indexes on both tables
- Enforce unique `project_id + period_start + period_end`
- Enforce unique pay-app number per project

Acceptance:
- Saved pay apps can sync as exported artifacts without inventing a separate
  history mechanism
- Delete propagation removes the child row, parent row, local file, and remote
  file

### 2. Pay Application Export Workflow

Implement the export flow as a form-like export, not a live editable form.

Work:
- Add pay-app feature module and routes
- Add date-range selection dialog with exact-range and overlap validation
- Add pay-app number review dialog with auto-assigned default and uniqueness
  validation
- Resolve previous pay app for chaining totals
- Build G703-style `.xlsx` export from tracked quantities and bid items
- Persist `ExportArtifact` + `PayApplication` only after export succeeds
- Prompt before replacing an exact-range saved pay app
- Preserve pay-app number on replacement unless the user overrides it
- Reuse the shared save/share dialog pattern, with no preview path for Excel

Acceptance:
- Export flow blocks overlapping non-identical ranges
- Export flow allows exact-range replacement only after explicit confirmation
- Saved pay app opens from history with summary/details metadata and actions

### 3. Exported Forms History Integration

Reframe Forms history around exported artifacts, not around saved editable form
responses.

Work:
- Build or extend exported-artifact history list filtered by artifact type
- Surface pay apps in the same exported history surface as IDR exports, form
  PDFs, and photo exports
- Keep editable saved form responses in their existing separate surface
- Add saved pay-app detail screen with:
  - pay-app number
  - project
  - date range
  - status `exported`
  - totals snapshot
  - exported timestamp
  - actions: share/export, compare contractor pay app, delete

Acceptance:
- Saved pay apps appear in exported Forms history
- Tapping a saved pay app opens a detail view, not direct action-only behavior
- Exported history remains separate from editable saved form responses

### 4. Contractor Comparison

Implement contractor reconciliation as a saved-pay-app subflow, with no data
write-back in v1.

Work:
- Launch comparison from saved pay-app detail view
- Support import from `.xlsx`, `.csv`, and best-effort `.pdf`
- Match by item number first, then description fallback
- Provide manual cleanup/remap/add/remove before comparison
- Compare contractor cumulative totals and period totals against app totals
- Add optional daily discrepancy section only when contractor data contains
  daily detail
- Export a standalone PDF discrepancy report
- Prompt if the user runs a new comparison while an in-session comparison
  result already exists
- Do not retain imported contractor files
- Keep comparison state ephemeral unless the user exports the discrepancy PDF

Acceptance:
- Comparison never mutates tracked quantities, entries, or bid items
- Totals-only contractor inputs still produce a useful discrepancy report
- PDF extraction failure can fall back into manual cleanup when possible

### 5. Analytics Enhancement

Implement pay-app-aware analytics without reintroducing removed change-order
concepts.

Work:
- Add `ProjectAnalyticsScreen`
- Add dashboard entry as the 4th quick card
- Add secondary analytics entry point from Pay Items
- Compute and display `change since last pay app`
- Support date filtering, progress by item, top recent activity, and pay-app
  comparison chart data

Acceptance:
- Analytics excludes change-order math entirely
- Analytics still shows `change since last pay app`

### 6. Sync And Offline Verification

The feature is local-first, but saved artifacts must sync cleanly once online.

Work:
- Verify local-first behavior for export, replace, delete, compare, discrepancy
  PDF export, and analytics
- Add sync verification coverage for `export_artifacts`
- Add sync verification coverage for `pay_applications`
- Verify parent-before-child pull ordering and delete propagation
- Verify file-sync behavior for pay-app `.xlsx` and discrepancy PDFs
- Verify imported contractor artifacts do not persist or sync

Acceptance:
- Offline export and delete work locally first
- Later sync reconciles metadata and file state without orphan rows/files
- Comparison-only inputs never create synced durable records

### 7. Testing System Updates

The spec explicitly requires updates to the maintained test system, not just
new local tests.

Work:
- Add/update unit tests for repository, provider, exporter, comparison, and
  analytics logic
- Add/update widget tests for pay-app dialogs, pay-app detail screen, exported
  history filtering, comparison cleanup flow, and analytics screen
- Add/update integration coverage for export, replace, overlap blocking, number
  override, delete propagation, contractor imports, and analytics
- Update:
  - `.codex/skills/test.md`
  - `.claude/skills/test/SKILL.md`
  - `.claude/test-flows/flow-dependencies.md`
  - `.claude/test-flows/tiers/toolbox-and-pdf.md`
- Add or update pay-app/export tier docs and sync/export verification docs
- Add the required `TestingKeys` for pay-app export, replace, detail,
  comparison, and analytics surfaces

Acceptance:
- The documented test-flow system knows how to verify pay-app export,
  replacement, overlap blocking, delete propagation, history visibility, and
  contractor comparison PDF export

### 8. Cross-Cutting Constraints

These are not optional polish items. They are part of the approved feature
contract.

Work:
- Keep pay-app `.xlsx` files and discrepancy PDFs in app-sandboxed,
  company-scoped storage paths
- Apply project/company-scoped access rules to `export_artifacts` and
  `pay_applications`
- Gate export, delete, contractor import, and discrepancy PDF export behind the
  existing `canEditFieldData` permission model
- Keep analytics and saved pay-app viewing read-only
- Preserve backward compatibility for prior export types in exported history

Acceptance:
- New artifact records respect existing auth and project/company scoping rules
- Existing exported artifact types continue to render in history after the new
  parent model is introduced

## Suggested Implementation Order

1. Export artifact foundation
2. Pay-application data/repository/provider layer
3. Pay-app export generator and replacement rules
4. Exported Forms history integration and pay-app detail screen
5. Contractor comparison flow and discrepancy PDF export
6. Analytics screen and navigation entry points
7. Sync verification and file/delete propagation checks
8. Cross-cutting auth/storage/backward-compatibility checks
9. Test-flow documentation updates and final verification pass

## Files And Systems Expected To Change

- `lib/core/database/database_service.dart`
- `lib/core/database/schema/`
- `lib/core/database/schema_verifier.dart`
- `test/core/database/schema_verifier_test.dart`
- `test/core/database/database_service_test.dart`
- export orchestrator / export history layers
- sync registry / adapter configs / file-sync integration
- Forms exported-history UI
- pay-app feature module
- analytics feature module
- contractor comparison flow
- maintained test skill + test-flow docs
- auth / storage / RLS policy touchpoints for new artifact tables

## Definition Of Done

- The code matches the approved pay-app spec with no change-order behavior left
  in scope.
- Saved pay apps are modeled as exported artifacts plus pay-app detail records.
- Export, replace, overlap blocking, delete propagation, and contractor
  comparison behavior all match the product rules above.
- Exported Forms history shows pay apps alongside the other exported artifact
  types without mixing them into editable saved form responses.
- Sync coverage exists for new durable records and file propagation.
- Auth, storage-scope, and backward-compatibility requirements from the spec
  are preserved.
- The maintained test-flow documentation is updated alongside code changes.
- If implementation details conflict with the spec, the spec wins and the plan
  must be revised before coding continues.
