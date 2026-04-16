# Tailor Manifest — UI E2E Feature Harness Refactor

**Spec:** `.claude/specs/2026-04-16-ui-e2e-feature-harness-refactor-spec.md`
**Date:** 2026-04-16
**Branch:** `gocr-integration`

## What Was Analyzed

- Approved spec (intent, scope, audit deliverables, open questions).
- Driver surface: `lib/core/driver/*` (31 files) — HTTP routes, handlers, registries, harness seed.
- Test harness: `.claude/test-flows/**` (tier docs + sync docs + flow-dependencies index), `.claude/skills/test/SKILL.md`.
- Testing keys: `lib/shared/testing_keys/*.dart` (17 files) via modular per-feature facade.
- Presentation surface: 57 `_screen.dart` files under `lib/features/**/presentation/screens/`.
- Router: `lib/core/router/routes/*.dart` (8 route modules) to verify route literals.
- Role gating: `lib/features/auth/data/models/user_role.dart`.
- PDF AcroForm path: existing `syncfusion_flutter_pdf` usage in `lib/features/forms/data/services/form_pdf_field_writer.dart` and `test/features/forms/services/form_pdf_field_writer_test.dart`.
- File-size audit: `scripts/audit_ui_file_sizes.ps1` (300-line ceiling) — currently 45 violations.

## What Was Produced

- `manifest.md` — this file.
- `dependency-graph.md` — driver/registry/harness/router import chains and downstream reach.
- `ground-truth.md` — verified literals and flagged gaps the writer must reconcile.
- `blast-radius.md` — affected files, symbols, registry atomicity, and cleanup targets.
- `patterns/driver-endpoint.md` — how to add a new `/driver/*` route in line with `DriverDataSyncRoutes` / `DriverShellRoutes`.
- `patterns/screen-contract-registration.md` — atomic registration in `screenRegistry` + `screenContracts` + feature spec.
- `patterns/feature-spec-markdown.md` — prose + fenced YAML authored per feature, with sub-flow catalog.
- `patterns/testing-keys-module.md` — how a new `TestingKeys` sentinel key is added in the right per-feature file.
- `patterns/harness-seed-extension.md` — adding precondition seeding via `HarnessSeedData` / `/driver/seed`.
- `patterns/pdf-acroform-helper.md` — syncfusion-based AcroForm read helper (existing seams confirmed).
- `patterns/presentation-decomposition.md` — 300-line ceiling compliance through existing mixin/helpers/actions split.
- `source-excerpts/by-file.md` — key excerpts grouped by file for implementation reference.
- `source-excerpts/by-concern.md` — excerpts grouped by concern (routes, contracts, seed, keys, rubric anchors).

## Research Agents Used

None. CodeMunch outline + `Read`/`Grep`/`Glob` covered the surface. One CodeMunch call returned truncated JSON; findings were recovered via targeted `Read` on the same files.

## Budget / Freshness

- CodeMunch repo index: `local/Field_Guide_App-37debbe5` (indexed 2026-04-15).
- Branch tip: `53707175` (Android Firebase CI checklist).
- No secrets were read or emitted in this tailor run.
