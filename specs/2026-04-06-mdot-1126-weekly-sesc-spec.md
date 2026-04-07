# MDOT Form 1126 — Weekly SESC Report

**Spec date:** 2026-04-06
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
- Drawn-signature capture with audit trail (Tier 3 e-signature)
- Daily-entry attachment via existing document/export flow
- Weekly reminder (banner on daily entry + dashboard todo) when 7+ days since last 1126 and SESC measures exist

**Out:**
- Contractor rep signatures (inspector-only this iteration)
- Biometric re-auth gate / PKI signing
- Auto-pulling rainfall from the weather feature
- Cross-week corrective-action lifecycle (each form is self-contained)
- Form locking after signing
- Fixed-weekday auto-anchoring

### Success Criteria
- [ ] Inspector can fill 1126 from the forms hub the same way they fill 0582B
- [ ] Second-week fill auto-populates header, sequenced report number, rolling 7-day date range, and SESC measures table from the prior week's response
- [ ] Rainfall events captured as structured (date + inches) entries and written into the PDF rainfall fields
- [ ] Each carried measure shown as a tri-state checklist (still in place / needs action / removed); "needs action" reveals corrective-action fields inline
- [ ] Drawn signature embedded in flattened PDF; audit row written to `signature_audit_log` and synced
- [ ] Completed PDF lands in the chosen daily entry's export folder with naming consistent with other exported documents
- [ ] Banner + dashboard todo appears 7 days after last 1126 when project has SESC measures

---

## 2. Data Model

### Reuse (no new form tables)
- `inspector_form` — one new builtin row: `mdot_1126`, `is_builtin=1`, server-seeded
- `form_response` — one row per weekly fill, `form_type='mdot_1126'`, scoped by project
- `form_export` — bridge to attach the generated PDF to a daily entry

### New table: `signature_audit_log`
| Field | Type | Required | Notes |
|---|---|---|---|
| id | TEXT | Yes | UUID |
| form_response_id | TEXT | Yes | FK → form_response.id |
| user_id | TEXT | Yes | Authenticated inspector UUID |
| device_id | TEXT | Yes | Platform device identifier |
| platform | TEXT | Yes | `android` / `ios` / `windows` |
| app_version | TEXT | Yes | e.g., `0.1.2+3` |
| signed_at_utc | TEXT | Yes | ISO-8601 UTC |
| gps_lat | REAL | No | Captured if location permission granted |
| gps_lng | REAL | No | Same |
| document_hash_sha256 | TEXT | Yes | SHA-256 of pre-sign flattened PDF bytes |
| signature_png_hash_sha256 | TEXT | Yes | SHA-256 of captured PNG bytes |
| signature_png_path | TEXT | Yes | Local blob path (existing storage pattern) |
| created_at | TEXT | Yes | Standard timestamp |
| updated_at | TEXT | Yes | Standard timestamp |
| deleted_at | TEXT | No | Soft delete |

- Sync: standard SQLite trigger → `change_log`, gated by `sync_control.pulling='0'`
- RLS on Supabase: scope by `user_id`/`company_id` matching existing form_response policies
- Re-signing (form is always editable) writes a **new** row; the latest row by `signed_at_utc` is the active signature

### Form response payload (JSON inside `form_response.data`)
Top-level keys for the 1126-specific structured data:
```
{
  "header": { project_id, contractor, inspector, permit_number, location, ... },
  "report_number": "...",
  "inspection_date": "YYYY-MM-DD",
  "date_of_last_inspection": "YYYY-MM-DD",  // derived: inspection_date - 7
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
  "signature_audit_id": "..."
}
```

---

## 3. User Flow

### Entry points
1. Forms hub → "MDOT 1126" tile (same affordance as 0582B)
2. Daily entry banner: "Weekly SESC report due — last filled X days ago" → tap → starts new 1126
3. Dashboard todo card: "Weekly SESC report" → tap → starts new 1126

### First-week fill
```
Forms Hub → New MDOT 1126 → blank form
  → user fills header / inspection_date / rainfall / measures
  → draws signature
  → picks daily entry to attach to
  → save → PDF generated → attached to daily entry's export folder
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
  → pick daily entry to attach to
  → save → PDF → daily entry export folder
```

### Reminder behavior
- Trigger: `now - last_1126.signed_at >= 7 days` AND project has any SESC measures recorded
- Banner on daily entry screen (dismissible per session, returns next day)
- Dashboard todo card (persistent until a new 1126 is signed)

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

### Reuses
- `form_accordion`, `status_pill_bar`, `summary_tiles`
- Existing daily-entry export pipeline (`form_export`, `manage_documents_use_case`)
- Existing dashboard todo card pattern

### TestingKeys
- `TestingKeys.mdot1126FormScreen`
- `TestingKeys.mdot1126RainfallAddButton`
- `TestingKeys.mdot1126MeasureRow`
- `TestingKeys.mdot1126SignaturePad`
- `TestingKeys.mdot1126AttachDailyEntryPicker`
- `TestingKeys.weeklySescReminderBanner`

---

## 5. State Management

Reuses existing `InspectorFormProvider`. New domain pieces:

- `LoadPrior1126UseCase` — fetches latest non-deleted `form_response` for `form_type='mdot_1126'` scoped to project
- `BuildCarryForward1126UseCase` — takes prior response + new inspection_date, returns prefilled payload (header, sequenced report number, rolling date range, measures with status reset to `in_place` and `corrective_action` cleared)
- `SignFormResponseUseCase` — captures PNG, hashes pre-sign PDF + PNG, writes `signature_audit_log` row, returns audit id
- `AttachFormResponseToDailyEntryUseCase` — wraps existing `manage_documents_use_case` flow

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
- `form_response` and `signature_audit_log` write through existing local-first flow; `change_log` triggers handle sync
- PDF generation is local (Syncfusion or existing PDF service — implementation chooses based on what 0582B already uses)
- Reminder logic computes from local SQLite only — no network dependency
- Sync direction: bidirectional via existing forms adapter; signature audit log gets a new adapter row in sync configuration

---

## 7. Edge Cases

| Scenario | Handling |
|---|---|
| First-ever 1126 (no prior week) | Skip carry-forward, show blank form |
| Prior week's measures table is empty | Skip review checklist step, go straight to "add measures" |
| User cancels mid-fill | Standard form draft behavior (existing pattern) |
| Daily entry deleted after attachment | Existing soft-delete cascade applies |
| Re-signing (form edited after sign) | New audit row, prior audit row preserved |
| GPS permission denied | Audit row stores NULL lat/lng; signature still valid |
| Two devices fill 1126 same week | Sync conflict resolved by existing conflict resolver; report_number collision possible — accept last-write-wins, surface in conflict viewer |
| Project has no SESC measures yet | No reminder fires |

---

## 8. Testing Strategy

### Unit
- `BuildCarryForward1126UseCase` — header/report#/date range/measures correctly prefilled; corrective_action and status reset
- `Mdot1126Validator` — rejects unresolved measure rows, missing signature, missing inspection_date
- `SignFormResponseUseCase` — hashes computed correctly, audit row inserted, sync trigger fires

### Widget
- `Mdot1126FormScreen` — guided prompt flow renders correctly for first-week vs carry-forward paths
- `SescMeasuresChecklist` — corrective-action field appears only on "needs action"
- `WeeklySescReminderBanner` — appears at 7d threshold, hides when SESC measures absent

### Integration / Driver
- End-to-end: fill first 1126 → attach → export daily entry → PDF present in export folder
- Carry-forward: fill week 1 → advance clock 7 days → start week 2 → verify prefill → sign → attach
- Sync: sign on device A → pull on device B → audit row present, signature image retrievable

---

## 9. Security Implications

- **Authentication:** Signing requires authenticated session (existing app gate)
- **Attribution:** `user_id` from session, plus device_id, GPS, and document hash provide E-SIGN/UETA-compliant audit trail
- **RLS:** `signature_audit_log` policies mirror `form_response` (company/project scoped); inspectors only read their own audit rows
- **Integrity:** SHA-256 hash of pre-sign PDF and signature PNG stored — any tamper detectable on replay
- **PII:** GPS coordinates are inspector-attributable; protected by company-scoped RLS
- **No new attack surface** beyond what forms feature already exposes

---

## 10. Migration / Cleanup

### Schema changes
- New table `signature_audit_log` (schema v51)
- New trigger `signature_audit_log_change_log_trg`
- New Supabase migration for the table + RLS policies + Realtime publication
- Bump schema version, update `schema_verifier`, update database test fixtures (per CLAUDE.md "schema changes touch 5 files" rule)

### New files (high level)
- `lib/features/forms/data/registries/mdot_1126_registrations.dart`
- `lib/features/forms/data/pdf/mdot_1126_pdf_filler.dart`
- `lib/features/forms/data/validators/mdot_1126_validator.dart`
- `lib/features/forms/domain/usecases/load_prior_1126_use_case.dart`
- `lib/features/forms/domain/usecases/build_carry_forward_1126_use_case.dart`
- `lib/features/forms/domain/usecases/sign_form_response_use_case.dart`
- `lib/features/forms/presentation/screens/mdot_1126_form_screen.dart`
- `lib/features/forms/presentation/widgets/rainfall_events_editor.dart`
- `lib/features/forms/presentation/widgets/sesc_measures_checklist.dart`
- `lib/features/forms/presentation/widgets/signature_pad_field.dart`
- `lib/features/forms/presentation/widgets/weekly_sesc_reminder_banner.dart`
- `assets/forms/mdot_1126.pdf` (copy from `.claude/specs/assets/mdot-1126-weekly-sesc.pdf`)

### Dependencies
- `signature` (canvas)
- `crypto` (SHA-256 — likely already present)
- PDF embedding via whichever library 0582B already uses; if AcroForm coverage is insufficient, add `syncfusion_flutter_pdf`

### Cleanup checklist
- [ ] Add `mdot_1126` to all four lint allowlists if any path-scoped rules apply
- [ ] Update `pubspec.yaml` assets section
- [ ] Update sync adapter config to register `signature_audit_log`

---

## Decisions & Rationale

| Decision | Choice | Why |
|---|---|---|
| Day attachment | User picks the day every time | Inspectors don't follow a fixed weekday; weekly reminder enforces cadence |
| Reminder placement | Banner + dashboard todo | Maximize visibility; SESC monitoring is mandatory once measures exist |
| Carry forward | Header + report# + date range + measures table | Most stable week-to-week data; rainfall/corrective fields blanked because they vary |
| Week boundary | Rolling 7d from inspection date | Matches the form's "date of last inspection" semantics |
| Rainfall capture | Structured (date + inches per event) | Writable directly into PDF fields, no manual transcription |
| Measures editing | Tri-state review checklist + add section | Matches inspection workflow — measures are reviewed, not re-entered |
| Corrective action lifecycle | Self-contained per form | Simpler; if action needed, it's filled out same session |
| Signature | Drawn + audit trail (Tier 3) | Industry standard for field inspection apps; E-SIGN/UETA compliant; offline-capable |
| Signature scope | Inspector only | Contractor rep deferred to later iteration |
| Editing post-sign | Always editable, re-sign creates new audit row | Avoids "delete and recreate" friction; audit chain preserved |
| Storage pattern | Reuse `form_response` + registries | Same path as 0582B; no special-case tables |
| Daily entry attachment | Existing document attachment flow | Reuses export pipeline; PDF lands in correct folder automatically |
