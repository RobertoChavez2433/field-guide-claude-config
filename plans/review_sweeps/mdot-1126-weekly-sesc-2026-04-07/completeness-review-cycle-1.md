# Completeness Review — Cycle 1

> **STATUS:** Addressed in fixer cycle 1. C1-C3, H1-H9, M1-M6, L1-L3 all
> applied. See fixer summary at the bottom of the plan file.



**Plan**: `.claude/plans/2026-04-06-mdot-1126-weekly-sesc.md`
**Reviewer**: completeness-review-agent (opus)
**Date**: 2026-04-07

## VERDICT: REJECT

54 requirements total — 29 MET, 16 PARTIALLY MET, 9 NOT MET.

## CRITICAL

### C1 — Signature PNG never embedded into flattened PDF
- Spec Success Criterion R5 mandates embedding. Plan's `fillMdot1126PdfFields` only returns text field map. `SignFormResponseUseCase` writes audit/file but never stamps the PNG onto the PDF.
- **Fix:** Add `embedSignatureInPdf` step inside `SignFormResponseUseCase` (or extend the PDF filler contract), calling `FormPdfService` to stamp the PNG onto the pre-sign PDF before hashing. The export PDF must contain the embedded image.

### C2 — Carry-forward orchestration never wired
- `LoadPrior1126UseCase` and `BuildCarryForward1126UseCase` are defined but never invoked. `FormInitialDataFactory.register` returns a static map. No path shows: "new 1126 tap → LoadPrior → BuildCarryForward → seed form_response payload."
- **Fix:** Either replace `FormInitialDataFactory` registration with a project-aware async builder, OR add a custom create path in `InspectorFormProvider`/provider-response-actions for 1126 that branches on prior existence. Add an explicit sub-phase showing the orchestration.

### C3 — `weekly_cycle_anchor_date` never persisted
- Spec §2 payload requires this field. Carry-forward copies it from prior (which is always null because it's never stored on first sign). `ComputeWeeklySescReminderUseCase` derives anchor at read time from earliest signed response — fragile.
- **Fix:** In `SignFormResponseUseCase`, after writing audit row, patch payload with `weekly_cycle_anchor_date = inspection_date` IF project has no prior signed 1126.

## HIGH

### H1 — First-week initial data payload missing keys
- Spec §2 payload keys not registered: `header`, `report_number`, `inspection_date`, `date_of_last_inspection`, `weekly_cycle_anchor_date`.
- **Fix:** Expand `FormInitialDataFactory` callback with all keys. Default `inspection_date = today`, `report_number = '1'`, `weekly_cycle_anchor_date = null`.

### H2 — "Rolling 7-day date range" unmapped
- Spec R2 mentions it; plan has no date_range_start/end fields or PDF mapping.
- **Fix:** Either add range fields to payload + PDF filler, OR document that `inspection_date` + `date_of_last_inspection` = the range, and confirm via PDF field dump in Phase 6.2.1.

### H3 — Reminders not reactive
- Dashboard/banner/toolbox use `FutureBuilder` directly. No refresh on sign or on `form_response` changes. Rebuilds every frame.
- **Fix:** Introduce `SescReminderProvider` (ChangeNotifier) that listens to `InspectorFormProvider` changes and exposes the computed snapshot. Widgets consume via `Consumer`.

### H4 — Signature invalidation not universal
- Hook in one provider extension only; all other write paths bypass it.
- **Fix:** Move into `FormResponseRepositoryImpl.update()` OR SQLite `AFTER UPDATE` trigger gated on `form_type='mdot_1126' AND OLD.response_data != NEW.response_data`.

### H5 — No auth assertion in `SignFormResponseUseCase`
- (Also SEC-1126-05.)

### H6 — `inspector_form` server seed missing
- Spec §2 says "server-seeded." Plan has no migration inserting the builtin `mdot_1126` row with `is_builtin=1`.
- **Fix:** Add `INSERT INTO public.inspector_form (id, name, ..., is_builtin) VALUES ('mdot_1126', 'MDOT 1126 Weekly SESC', ..., true) ON CONFLICT DO NOTHING;` to the signature migration or a companion migration.

### H7 — Edge case: prior measures empty → skip review step (R-EC2)
- Wizard step enum is linear. Nothing handles `measures.isEmpty → jump to addMeasures`.
- **Fix:** Add conditional skip in step router.

### H8 — Edge case: late fill backdating (R-EC9)
- No inspection-date picker affordance; no default-to-scheduled-date behavior.
- **Fix:** Add date picker field in wizard that defaults to next scheduled due date from `ComputeWeeklySescReminderUseCase` and allows backdating. Add integration test.

### H9 — `ExportBlockedException` undefined
- (Also code review.)

## MEDIUM

### M1 — Two-device conflict (R-EC10) not tested
- No test for report_number collision. No verification of `ConflictResolver` coverage for new tables.
- **Fix:** Add integration test to matrix.

### M2 — Spec §10 cleanup: `assets/forms/...` migration
- Not addressed.
- **Fix:** Add cleanup sub-phase grepping `assets/forms/` in `lib/` and migrating matches to `assets/templates/forms/`.

### M3 — Attach-step override list + widget test
- Spec §3 requires override to "any other daily entry." Plan has no candidate-list API or picker widget test.
- **Fix:** Add `listCandidates(projectId)` to `Resolve1126AttachmentEntryUseCase`. Create attach-step widget + widget test.

### M4 — Toolbox TODO extraction + widget test
- Phase 9.3 is inline `FutureBuilder` — no dedicated widget, no test.
- **Fix:** Extract `WeeklySescToolboxTodo` widget alongside banner/card. Add widget test.

### M5 — File sync round-trip verification
- No verification that `FileSyncHandler` pulls PNGs on device B and populates `local_path`.
- **Fix:** Verify in `mdot_1126_sync_test.dart`.

### M6 — `form_response.entry_id` soft-delete cascade verification
- Spec §7 row 5 says "existing cascade applies." Plan does not verify.
- **Fix:** Add a verification step or test.

## LOW

### L1 — Platform CHECK constraint drift
- Plan allows `macos/linux`; spec only lists `android/ios/windows`.
- **Fix:** Tighten CHECK to spec values OR document expansion.

### L2 — Ground-truth flags 5/6/7 deferred
- Design-system names, WizardActivityTracker API, DailyEntry constructor — plan only adds "NOTE: verify" comments. These affect compilation.
- **Fix:** Resolve in-plan before implementer runs. (Code review finds them as CRITICAL.)

### L3 — Asset copy is imperative, not reproducible
- PowerShell copy command won't re-run on fresh clones.
- **Fix:** Instruction to commit `assets/templates/forms/mdot_1126_form.pdf` to git.
