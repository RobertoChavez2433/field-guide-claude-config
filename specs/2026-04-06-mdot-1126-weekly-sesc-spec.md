# MDOT Form 1126 — Weekly SESC Report

**Spec date:** 2026-04-06
**Last clarified:** 2026-04-07
**Status:** Approved
**Source PDF:** `.claude/specs/assets/mdot-1126-weekly-sesc.pdf` (downloaded from https://mdotjboss.state.mi.us/webforms/GetDocument.htm?fileName=1126.pdf — copy into app assets during implementation)
**Sizing:** M (full pipeline — brainstorming → tailor → writing-plans → implement)

---

## 1. Overview

### Purpose
Add MDOT Form 1126 (Weekly Soil Erosion & Sedimentation Control Report) to the forms feature so inspectors can fulfill the weekly SESC monitoring requirement, attach the completed PDF to a daily entry, and have it export with that day's bundle.

### Scope
**In:**
- New builtin form `mdot_1126` registered through existing forms registries
- `Mdot1126PdfFiller` for the existing AcroForm template
- Carry-forward use case from prior week's response
- Structured "new week" prompt flow (rainfall, measure review, new measures, corrective actions)
- Drawn-signature capture with generic reusable audit/storage architecture (Tier 3 e-signature)
- Daily-entry attachment where `form_response.entry_id` is the authoritative link
- Attach-step default to the daily entry matching `inspection_date`, with inline create if that entry does not exist
- Weekly cadence reminders anchored to the first signed 1126 for the project
- Computed persistent reminders in two places once the first 1126 has been signed:
  - dashboard top card / banner-like reminder
  - toolbox TODO feature reminder
- Daily-entry reminder banner on today's entry only, when today's entry exists

**Out:**
- Contractor rep signatures (inspector-only this iteration)
- Biometric re-auth gate / PKI signing
- Auto-pulling rainfall from the weather feature
- Cross-week corrective-action lifecycle (each form is self-contained)
- Stored `todo_items` rows for the weekly reminder
- User-facing audit-log viewer

### Success Criteria
- [ ] Inspector can fill 1126 from the forms hub the same way they fill 0582B
- [ ] Second-week fill auto-populates header, sequenced report number, rolling 7-day date range, and SESC measures table from the prior week's response
- [ ] Rainfall events captured as structured (date + inches) entries and written into the PDF rainfall fields
- [ ] Each carried measure shown as a tri-state checklist (still in place / needs action / removed); "needs action" reveals corrective-action fields inline
- [ ] Drawn signature embedded in flattened PDF; generic signature audit/file rows are written and synced
- [ ] Completed form is attached to the chosen daily entry via `form_response.entry_id`
- [ ] Daily export writes the IDR, form PDFs, and photos for that entry into one folder on disk
- [ ] If a signed 1126 is edited, the active signature is immediately cleared and export is blocked until re-signed
- [ ] Weekly reminders stay anchored to the first signed 1126 schedule and are not reset by extra same-week inspections
- [ ] Weekly reminders continue until the project is archived, deleted, or inactive

---

## 2. Data Model

### Reuse (no new form tables)
- `inspector_form` — one new builtin row: `mdot_1126`, `is_builtin=1`, server-seeded
- `form_response` — one row per weekly fill, `form_type='mdot_1126'`, scoped by project
- `form_response.entry_id` — authoritative attachment link to the chosen daily entry; may start `NULL` while drafting from the forms hub/dashboard
- `form_export` — export metadata for generated PDFs; not the source of truth for attachment

### New table: `signature_audit_log`
| Field | Type | Required | Notes |
|---|---|---|---|
| id | TEXT | Yes | UUID |
| signed_record_type | TEXT | Yes | Generic sign target, `form_response` for 1126 this iteration |
| signed_record_id | TEXT | Yes | ID of the signed record |
| project_id | TEXT | Yes | Direct project scoping for local triggers and sync |
| company_id | TEXT | Yes | Direct company scoping for backend security |
| user_id | TEXT | Yes | Authenticated inspector UUID |
| device_id | TEXT | Yes | Platform device identifier |
| platform | TEXT | Yes | `android` / `ios` / `windows` |
| app_version | TEXT | Yes | e.g., `0.1.2+3` |
| signed_at_utc | TEXT | Yes | ISO-8601 UTC |
| gps_lat | REAL | No | Captured if location permission granted |
| gps_lng | REAL | No | Same |
| document_hash_sha256 | TEXT | Yes | SHA-256 of pre-sign flattened PDF bytes |
| signature_file_id | TEXT | Yes | FK → `signature_files.id` |
| created_at | TEXT | Yes | Standard timestamp |
| updated_at | TEXT | Yes | Standard timestamp |
| deleted_at | TEXT | No | Soft delete |

### New table: `signature_files`
Dedicated reusable file-backed table for captured signature PNGs. This is intentionally separate from `export_artifacts` because signatures are not export history.

| Field | Type | Required | Notes |
|---|---|---|---|
| id | TEXT | Yes | UUID |
| project_id | TEXT | Yes | Direct project scoping |
| company_id | TEXT | Yes | Direct company scoping |
| local_path | TEXT | Yes | App-documents path to the PNG |
| remote_path | TEXT | No | Supabase storage path after sync |
| mime_type | TEXT | Yes | `image/png` |
| file_size_bytes | INTEGER | Yes | PNG size |
| sha256 | TEXT | Yes | SHA-256 of captured PNG bytes |
| created_by_user_id | TEXT | Yes | Authenticated inspector UUID |
| created_at | TEXT | Yes | Standard timestamp |
| updated_at | TEXT | Yes | Standard timestamp |
| deleted_at | TEXT | No | Soft delete |

- Sync:
  - `signature_audit_log` uses standard SQLite trigger → `change_log`, gated by `sync_control.pulling='0'`
  - `signature_files` is a file-backed sync table with a dedicated storage bucket/path convention
- RLS on Supabase: company/project scoped, backend/system facing only, no user-facing audit-log screen in this iteration
- Re-signing writes a **new** audit row and a new signature file
- Editing a signed form immediately clears the current `signature_audit_id` from the response payload; the prior audit rows remain historical but no signature is considered active until re-sign

### Form response payload (JSON inside `form_response.response_data`)
Top-level keys for the 1126-specific structured data:
```
{
  "header": { project_id, contractor, inspector, permit_number, location, ... },
  "report_number": "...",
  "inspection_date": "YYYY-MM-DD",
  "date_of_last_inspection": "YYYY-MM-DD",  // actual previous signed 1126 inspection date
  "rainfall_events": [{ "date": "YYYY-MM-DD", "inches": 0.0 }],
  "measures": [
    {
      "id": "uuid",
      "description": "...",
      "location": "...",
      "status": "in_place" | "needs_action" | "removed",
      "corrective_action": "..."  // only when status == needs_action
    }
  ],
  "signature_audit_id": "...",   // null while unsigned or after post-sign edits
  "weekly_cycle_anchor_date": "YYYY-MM-DD"  // first signed 1126 inspection date for this project
}
```

---

## 3. User Flow

### Entry points
1. Forms hub → "MDOT 1126" tile (same affordance as 0582B)
2. Daily entry banner: "Weekly SESC report due — last filled X days ago" → tap → starts new 1126
3. Dashboard reminder card: "Weekly SESC report" → tap → starts new 1126

### First-week fill
```
Forms Hub → New MDOT 1126 → blank form
  → only profile/user autofill is prefilled (no prior-week carry-forward)
  → user fills header / inspection_date / rainfall / measures
  → draws signature
  → attach step defaults to daily entry matching inspection_date
      → if that entry does not exist, offer inline create for that date
      → user may override to any other daily entry
  → save
  → export-ready state persists locally even if export-to-disk has not happened yet
```

### Subsequent-week fill (carry-forward)
```
New MDOT 1126 → carry-forward use case loads prior response
  → header (A) + report_number+1 (B) + new date range (C) + measures table (D) prefilled
  → guided prompt steps:
      1. "Has there been any rainfall this week?"
         No  → rainfall_events = []
         Yes → structured entry sheet (date picker + inches per event, add multiple)
      2. Measures review checklist:
          For each carried row → tri-state (still in place / needs action / removed)
          "Needs action" reveals inline corrective-action text field (required)
      3. "Add new SESC measures?" → optional add-row section
  → signature
  → attach step defaults to daily entry matching inspection_date
      → if that entry does not exist, offer inline create for that date
      → user may override to any other daily entry
  → save
```

### Reminder behavior
- Weekly cycle anchor: the first signed 1126 for the project establishes the recurring 7-day schedule
- Due dates repeat every 7 days from that anchor date
- Additional same-week inspections (for example rainfall-triggered extra forms) do **not** shift the anchor
- Late fills are expected to be backdated to the intended scheduled inspection date so the cycle stays anchored
- Reminders start only after the project has at least one signed 1126
- Reminders stop when the project is archived, deleted, or inactive
- Dashboard reminder:
  - computed UI card, placed at the top of the project dashboard in a banner-like position
  - persistent until the current scheduled weekly inspection has been satisfied
- Toolbox reminder:
  - computed persistent recurring reminder in the toolbox TODO feature
  - not stored as a `todo_items` row
- Daily-entry banner:
  - shown only on today's daily entry
  - only when today's entry exists
  - dashboard reminder covers the "no entry yet for today" case

---

## 4. UI Components

### New widgets (under `lib/features/forms/presentation/`)
| Widget | Purpose |
|---|---|
| `Mdot1126FormScreen` | Top-level form screen, registered in `form_screen_registry` |
| `RainfallEventsEditor` | Add/remove rainfall events (date picker + inches) |
| `SescMeasuresChecklist` | Tri-state review of carried measures with inline corrective-action field |
| `SescMeasureAddSection` | Add-new-measure rows |
| `SignaturePadField` | Reusable wrapper around `signature` package canvas; emits PNG bytes |
| `WeeklySescReminderBanner` | Daily-entry banner widget |
| `WeeklySescReminderCard` | Dashboard top reminder card |

### Reuses
- `form_accordion`, `status_pill_bar`, `summary_tiles`
- Existing daily-entry export pipeline for folder export
- Existing daily-entry creation flow for inline create-on-attach

### TestingKeys
- `TestingKeys.mdot1126FormScreen`
- `TestingKeys.mdot1126RainfallAddButton`
- `TestingKeys.mdot1126MeasureRow`
- `TestingKeys.mdot1126SignaturePad`
- `TestingKeys.mdot1126AttachDailyEntryPicker`
- `TestingKeys.weeklySescReminderBanner`
- `TestingKeys.weeklySescReminderCard`
- `TestingKeys.weeklySescToolboxTodo`

---

## 5. State Management

Reuses existing `InspectorFormProvider`. New domain pieces:

- `LoadPrior1126UseCase` — fetches latest non-deleted `form_response` for `form_type='mdot_1126'` scoped to project
- `BuildCarryForward1126UseCase` — takes prior response + new inspection_date, returns prefilled payload (header, sequenced report number, actual prior inspection date, carried measures with status reset to `in_place` and `corrective_action` cleared)
- `SignFormResponseUseCase` — 1126-specific wrapper over generic signature capture/audit/file infrastructure; captures PNG, hashes pre-sign PDF + PNG, writes `signature_files` + `signature_audit_log`, returns audit id
- `InvalidateFormSignatureOnEditUseCase` — clears the active `signature_audit_id` whenever a signed 1126 is edited
- `Resolve1126AttachmentEntryUseCase` — chooses the default entry matching `inspection_date` and supports user override
- `CreateInspectionDateEntryUseCase` — inline create of the daily entry for `inspection_date` when no matching entry exists
- `ComputeWeeklySescReminderUseCase` — determines cycle anchor, current due window, and reminder visibility for dashboard / toolbox / today's entry banner

Registries to extend:
- `builtin_forms.dart` — register `mdot_1126`
- `form_screen_registry` → `Mdot1126FormScreen`
- `form_pdf_filler_registry` → `Mdot1126PdfFiller`
- `form_initial_data_factory` → first-week defaults + carry-forward path
- `form_validator_registry` → `Mdot1126Validator` (require inspection_date, signature, all measure rows resolved)
- `form_quick_action_registry` → "New 1126" hub action

---

## 6. Offline Behavior

- Fully offline (consistent with rest of forms feature)
- `form_response`, `signature_audit_log`, and `signature_files` write through existing local-first flow; `change_log` triggers handle sync
- PDF generation is local (Syncfusion or existing PDF service — implementation chooses based on what 0582B already uses)
- Reminder logic computes from local SQLite only — no network dependency
- Attach flow can create the inspection-date daily entry locally while offline
- Sync direction:
  - bidirectional via existing forms adapter for `form_response`
  - new standard adapter for `signature_audit_log`
  - new file-backed adapter for `signature_files`

---

## 7. Edge Cases

| Scenario | Handling |
|---|---|
| First-ever 1126 (no prior week) | Skip carry-forward, show blank form except for profile/user autofill |
| Prior week's measures table is empty | Skip review checklist step, go straight to "add measures" |
| User cancels mid-fill | Standard form draft behavior (existing pattern) |
| No daily entry exists for inspection_date | Attach step offers inline create for that exact date |
| Daily entry deleted after attachment | Existing soft-delete cascade applies to `form_response.entry_id` linkage |
| Re-signing (form edited after sign) | Edit immediately clears active signature; next signature writes a new audit row and new signature file; prior audit rows remain historical |
| GPS permission denied | Audit row stores NULL lat/lng; signature still valid |
| Extra rainfall-driven 1126 in the same scheduled week | Allowed, but does not reset the weekly cycle anchor or next due date |
| Inspector fills a missed week late | Expected behavior is to backdate the form to the intended scheduled inspection date so the cycle stays anchored |
| Two devices fill 1126 in the same scheduled week | Sync conflict resolved by existing conflict resolver; report_number collision possible — accept last-write-wins, surface in conflict viewer |
| Project has never had a signed 1126 | No reminder fires yet |
| No daily entry exists for today | No entry-screen banner; dashboard reminder still shows |
| Project is archived, deleted, or inactive | All recurring 1126 reminders stop |

---

## 8. Testing Strategy

### Unit
- `BuildCarryForward1126UseCase` — header/report#/date range/measures correctly prefilled; corrective_action and status reset
- `Mdot1126Validator` — rejects unresolved measure rows, missing signature, missing inspection_date
- `SignFormResponseUseCase` — hashes computed correctly, audit row + signature file inserted, sync triggers fire
- `InvalidateFormSignatureOnEditUseCase` — editing a signed form clears the active signature immediately
- `ComputeWeeklySescReminderUseCase` — anchor date stays fixed; extra same-week forms do not reset cadence; archived/deleted/inactive projects suppress reminders

### Widget
- `Mdot1126FormScreen` — guided prompt flow renders correctly for first-week vs carry-forward paths
- `SescMeasuresChecklist` — corrective-action field appears only on "needs action"
- Attach step — defaults to matching inspection-date entry and offers inline create when missing
- `WeeklySescReminderBanner` — appears only on today's entry when today's entry exists and the scheduled cycle is due
- `WeeklySescReminderCard` — appears at the top of the dashboard when the current cycle is due

### Integration / Driver
- End-to-end: fill first 1126 → create missing inspection-date entry inline → attach → export daily entry → IDR + 1126 + photos present in one folder
- Carry-forward: fill week 1 → advance clock 7 days → start week 2 → verify prefill → sign → attach
- Cadence: create extra same-week inspection → verify next due date did not shift
- Sync: sign on device A → pull on device B → audit row present, signature image retrievable from synced signature file
- Edit-after-sign: open signed 1126 → edit field → verify signature is cleared immediately and export is blocked until re-sign

---

## 9. Security Implications

- **Authentication:** Signing requires authenticated session (existing app gate)
- **Attribution:** `user_id` from session, plus device_id, GPS, and document hash provide E-SIGN/UETA-compliant audit trail
- **RLS:** signature storage is company/project scoped and backend/system facing; no user-facing audit-log reader in this iteration
- **Integrity:** SHA-256 hash of pre-sign PDF and signature PNG stored — any tamper detectable on replay
- **PII:** GPS coordinates are inspector-attributable; protected by company-scoped RLS
- **Reuse:** Generic signature tables are intentionally reusable for future signed forms so the security model is defined once

---

## 10. Migration / Cleanup

### Schema changes
- New table `signature_audit_log` (schema v53)
- New table `signature_files` (schema v53)
- New triggers for both tables
- New Supabase migration for both tables + RLS policies + Realtime publication + signature storage bucket/policies
- Bump schema version, update `schema_verifier`, update database test fixtures (per CLAUDE.md "schema changes touch 5 files" rule)

### New files (high level)
- `lib/features/forms/data/registries/mdot_1126_registrations.dart`
- `lib/features/forms/data/pdf/mdot_1126_pdf_filler.dart`
- `lib/features/forms/data/validators/mdot_1126_validator.dart`
- `lib/features/forms/domain/usecases/load_prior_1126_use_case.dart`
- `lib/features/forms/domain/usecases/build_carry_forward_1126_use_case.dart`
- `lib/features/forms/domain/usecases/sign_form_response_use_case.dart`
- `lib/features/forms/domain/usecases/invalidate_form_signature_on_edit_use_case.dart`
- `lib/features/forms/domain/usecases/resolve_1126_attachment_entry_use_case.dart`
- `lib/features/forms/domain/usecases/compute_weekly_sesc_reminder_use_case.dart`
- `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart`
- `lib/features/forms/presentation/widgets/rainfall_events_editor.dart`
- `lib/features/forms/presentation/widgets/sesc_measures_checklist.dart`
- `lib/features/forms/presentation/widgets/signature_pad_field.dart`
- `lib/features/forms/presentation/widgets/weekly_sesc_reminder_banner.dart`
- `lib/features/forms/presentation/widgets/weekly_sesc_reminder_card.dart`
- `lib/features/signatures/data/models/signature_audit_log.dart`
- `lib/features/signatures/data/models/signature_file.dart`
- `assets/templates/forms/mdot_1126.pdf` (copy from `.claude/specs/assets/mdot-1126-weekly-sesc.pdf`)

### Dependencies
- `signature` (canvas)
- `crypto` (SHA-256 — likely already present)
- PDF embedding via whichever library 0582B already uses; if AcroForm coverage is insufficient, add `syncfusion_flutter_pdf`

### Cleanup checklist
- [ ] Add `mdot_1126` to all four lint allowlists if any path-scoped rules apply
- [ ] Update `pubspec.yaml` assets section
- [ ] Update sync adapter config to register `signature_audit_log` and file-backed `signature_files`
- [ ] Stop using ad hoc `assets/forms/...` path assumptions for builtin 1126 export and preview flows; follow `assets/templates/forms/...`

---

## Decisions & Rationale

| Decision | Choice | Why |
|---|---|---|
| Attachment source of truth | `form_response.entry_id` | Scales cleanly across many future forms; export metadata stays separate from attachment state |
| Day attachment | Default to the entry matching `inspection_date`, with override and inline create | Keeps the common path fast while still supporting missed forms and extra same-week inspections |
| Reminder placement | Banner + dashboard todo | Maximize visibility; SESC monitoring is mandatory once measures exist |
| Carry forward | Header + report# + date range + measures table | Most stable week-to-week data; rainfall/corrective fields blanked because they vary |
| Weekly cycle anchor | First signed 1126 inspection date for the project | Keeps the recurring schedule stable; extra same-week inspections do not reset cadence |
| Week boundary | Actual prior signed 1126 inspection date + anchored 7-day cadence | Matches operational intent better than blindly using `inspection_date - 7` |
| Rainfall capture | Structured (date + inches per event) | Writable directly into PDF fields, no manual transcription |
| Measures editing | Tri-state review checklist + add section | Matches inspection workflow — measures are reviewed, not re-entered |
| Corrective action lifecycle | Self-contained per form | Simpler; if action needed, it's filled out same session |
| Signature | Drawn + generic reusable audit/file architecture (Tier 3) | Industry standard for field inspection apps; E-SIGN/UETA compliant; reusable across future forms; offline-capable |
| Signature scope | Inspector only | Contractor rep deferred to later iteration |
| Editing post-sign | Always editable; edit immediately clears active signature; re-sign creates new audit row | Avoids delete/recreate friction while keeping signature validity unambiguous |
| Storage pattern | Reuse `form_response` + registries | Same path as 0582B; no special-case tables |
| Reminder start condition | First signed 1126 for the project | More reliable than inferring "SESC exists" from free-text entry fields |
| Reminder persistence | Computed dashboard card + computed toolbox recurring reminder | Persistent requirement without creating user-editable todo records |
| Reminder stop condition | Project archived, deleted, or inactive | Matches "job closed" intent |
| Daily export | One folder containing IDR + attached form PDFs + photos | Matches field workflow for sharing/emailing/uploading the full daily package |
