# Claude Directory Audit & Update — Part 3: PRDs, Constraints, Skills, Guides

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Update all PRDs, rewrite stale constraints, create missing constraints, fix state/defect files, update skills and guides.
**Spec:** `.claude/specs/2026-03-30-claude-directory-audit-update-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-30-claude-directory-audit-update/analysis.md`

**Blast Radius:** ~52 direct files, 0 dependent, 0 tests, 1 cleanup (DELETE pagination guide)

---

## Phase 8: PRDs

### Sub-phase 8.1: CREATE forms-prd.md

**Files:**
- Create: `.claude/prds/forms-prd.md`

**Agent**: general-purpose

#### Step 8.1.1: Create the forms PRD

Create `.claude/prds/forms-prd.md` documenting the Inspector Forms & MDOT Hub feature. Structure it to match existing PRD format. Include:

**Registry system:**
- FormScreenRegistry — maps form type to screen builder
- FormPdfFillerRegistry — maps form type to PDF filler
- FormCalculatorRegistry — maps form type to calculator
- FormValidatorRegistry — maps form type to validator
- FormQuickActionRegistry — maps form type to quick actions
- FormInitialDataFactory — creates initial data for new form responses

**Form lifecycle:** draft → submitted (immutable after submit)

**Models:**
- InspectorForm — immutable built-in form definition
- FormResponse — project-scoped, mutable until submitted
- FormExport — export data container
- AutoFillResult — result of auto-fill operation

**MDOT 0582B specifics:**
- Mdot0582bCalculator — IDR calculations
- Mdot0582bValidator — field validation rules
- Mdot0582bPdfFiller — PDF form filling

**Services:**
- AutoFillService — auto-populates fields from project data
- OnePointCalculator — single-point proctor calculation
- FormStateHasher — change detection via hashing
- FormPdfService — PDF export orchestration

**Use cases:**
- CalculateFormFieldUseCase, NormalizeProctorRowUseCase
- LoadFormResponsesUseCase, SaveFormResponseUseCase, SubmitFormResponseUseCase, DeleteFormResponseUseCase
- LoadFormsUseCase, ManageDocumentsUseCase, ExportFormUseCase

**Screens:**
- FormsListScreen — list of form responses for a project
- FormGalleryScreen — gallery of available form templates
- MdotHubScreen — MDOT-specific form hub
- FormViewerScreen — renders a specific form for editing

**DI:** forms_providers.dart, forms_init.dart

---

### Sub-phase 8.2: REWRITE sync-prd.md

**Files:**
- Modify: `.claude/prds/sync-prd.md`

**Agent**: general-purpose

#### Step 8.2.1: Replace entire sync architecture description

Read the current file, then rewrite it entirely. Replace all sync_queue / SyncAdapter / hash-based change detection content with the actual architecture:

**Core engine:**
- change_log trigger system — SQLite triggers on INSERT/UPDATE/DELETE write to change_log table
- ChangeTracker — reads from change_log to determine what needs syncing
- SyncEngine — orchestrates the sync process
- SyncOrchestrator — higher-level coordination (manual + push-triggered + lifecycle)
- SyncRegistry — ordered registration of all adapters
- SyncMutex — prevents concurrent sync runs

**Adapters:**
- TableAdapter base class — abstract adapter for each syncable table
- 20+ concrete adapters (one per syncable table), each handles push/pull for its table
- Per-adapter processing (NOT all-or-nothing)

**Post-sync integrity:**
- IntegrityChecker — verifies FK relationships after sync
- OrphanScanner — finds and handles orphaned records

**Push sync:**
- FcmHandler — receives FCM push notifications to trigger sync

**Lifecycle:**
- SyncLifecycleManager — integrates sync with app lifecycle (foreground/background)

**Screens:**
- SyncDashboardScreen — sync status, last sync time, manual trigger
- ConflictViewerScreen — view and resolve sync conflicts

**Provider:** SyncProvider

---

### Sub-phase 8.3: UPDATE settings-prd.md

**Files:**
- Modify: `.claude/prds/settings-prd.md`

**Agent**: general-purpose

#### Step 8.3.1: Add missing feature sections

Read the current file. First, correct the existing "Primary storage: SharedPreferences (no SQLite table)" claim — settings now uses SQLite tables (user_consent_records, support_tickets) and the user_profiles table for profile data. SharedPreferences is only for device-local app settings (theme, gauge number). Then add sections for:
- **Consent:** ConsentScreen, ConsentRecord model, ConsentProvider, ConsentRepository
- **Help/Support:** HelpSupportScreen, SupportTicket model, SupportProvider, SupportRepository
- **Legal:** LegalDocumentScreen
- **OSS:** OssLicensesScreen
- **Admin:** AdminDashboardScreen, AdminProvider, AdminRepository
- **Trash:** TrashScreen, TrashRepository
- **Edit Profile:** EditProfileScreen
- **Storage note:** user_profiles table + UserProfile model for profile data, NOT SharedPreferences

---

### Sub-phase 8.4: UPDATE auth-prd.md

**Files:**
- Modify: `.claude/prds/auth-prd.md`

**Agent**: general-purpose

#### Step 8.4.1: Fix post-auth navigation

Change any reference to post-auth going to "project selection" — it goes to `/` (root, handled by router redirect).

#### Step 8.4.2: Remove MOCK_AUTH reference

Remove any mention of MOCK_AUTH if present — this is not how the app works.

#### Step 8.4.3: Add missing auth components

Add:
- Local SQLite tables: user_profiles, companies
- OTP flow (Supabase OTP verification)
- Inactivity timeout
- Consent gate (router checks ConsentProvider before allowing access)
- Multi-tenant company flow (CompanySetupScreen, PendingApprovalScreen, admin approval)
- Note: Auth has 10 screens now

---

### Sub-phase 8.5: UPDATE entries-prd.md

**Files:**
- Modify: `.claude/prds/entries-prd.md`

**Agent**: general-purpose

#### Step 8.5.1: Fix status lifecycle

Change any 3-state lifecycle (draft/submitted/complete) to 2-state: **draft** and **submitted** only. Remove any mention of COMPLETE status.

#### Step 8.5.2: Fix weather field

Change weather field type from string to `WeatherCondition?` enum.

#### Step 8.5.3: Add missing fields

Add `createdByUserId` and `updatedByUserId` fields to the entry model description.

#### Step 8.5.4: Fix editor description

Entry editor is a **single-screen with collapsible cards**, NOT a multi-step wizard.

---

### Sub-phase 8.6: UPDATE projects-prd.md

**Files:**
- Modify: `.claude/prds/projects-prd.md`

**Agent**: general-purpose

#### Step 8.6.1: Add AssignmentsStep to wizard

Note that the project setup wizard includes an AssignmentsStep.

#### Step 8.6.2: Add multi-tenant fields

Add `company_id`, `created_by_user_id`, `is_active` to the project model.

#### Step 8.6.3: Fix MDOT mode description

MDOT mode is a placeholder — no AASHTOWare adapter exists.

---

### Sub-phase 8.7: UPDATE photos-prd.md

**Files:**
- Modify: `.claude/prds/photos-prd.md`

**Agent**: general-purpose

#### Step 8.7.1: Fix photo_detail_dialog path

Change any path reference to photo_detail_dialog to: `lib/features/entries/presentation/widgets/photo_detail_dialog.dart`

#### Step 8.7.2: Add soft-delete columns

Add `deleted_at` and `deleted_by` to the photo model fields.

#### Step 8.7.3: Note file_path nullable

`file_path` is nullable (photo may exist remotely but not yet downloaded locally).

---

### Sub-phase 8.8: UPDATE remaining PRDs (batch)

**Files:**
- Modify: `.claude/prds/dashboard-prd.md`
- Modify: `.claude/prds/contractors-prd.md`
- Modify: `.claude/prds/quantities-prd.md`
- Modify: `.claude/prds/weather-prd.md`
- Modify: `.claude/prds/toolbox-prd.md`
- Modify: `.claude/prds/pdf-extraction-v2-prd-2.0.md`
- Modify: `.claude/prds/2026-02-21-project-based-architecture-prd.md`

**Agent**: general-purpose

#### Step 8.8.1: dashboard-prd.md

Fix navigation description: dashboard is nested in project flow via `/project/:id`, NOT bottom nav tabs.

#### Step 8.8.2: contractors-prd.md

Fix sync description: change_log triggers, NOT sync_queue.

#### Step 8.8.3: quantities-prd.md

Add note about open defects: search doesn't filter properly, numeric sort uses string comparison.

#### Step 8.8.4: weather-prd.md

Fix field name: `WeatherCondition?` enum, not string 'condition'. Column name is `weather` not `weather_condition`.

#### Step 8.8.5: toolbox-prd.md

Fix file counts: gallery has di/domain/presentation directories, todos has full data/domain/di/presentation structure.

#### Step 8.8.6: pdf-extraction-v2-prd-2.0.md

Remove `[NOT IMPLEMENTED]` TODO for confidence_calibrator. Note that pdfrx migration is completed.

#### Step 8.8.7: 2026-02-21-project-based-architecture-prd.md

Fix stale sync references: `sync_queue` → `change_log`, `SupabaseSyncAdapter` → `TableAdapter`. Fix schema version reference: was 23→24, now 46.

---

## Phase 9: Architecture Decisions / Constraints

### Sub-phase 9.1: REWRITE sync-constraints.md

**Files:**
- Modify: `.claude/architecture-decisions/sync-constraints.md`

**Agent**: general-purpose

#### Step 9.1.1: Replace entire file

Read the current file, then rewrite it entirely. Replace:
- Hash-based change detection → trigger-based change_log
- All-or-nothing sync → per-adapter processing
- SyncAdapter → TableAdapter base class
- Add: SyncEngine, SyncRegistry, SyncMutex, IntegrityChecker, OrphanScanner, FcmHandler
- 20+ adapters process independently
- Document the change_log schema (table_name, record_id, operation, timestamp)
- Document adapter ordering (parents before children)
- **SECURITY HARD RULE (from review):** MUST NOT trust client-provided company_id in sync payloads — server RLS validates company_id from JWT app_metadata

---

### Sub-phase 9.2: REWRITE settings-constraints.md

**Files:**
- Modify: `.claude/architecture-decisions/settings-constraints.md`

**Agent**: general-purpose

#### Step 9.2.1: Replace entire file

Read the current file, then rewrite. Expand from "theme/language/notifications" to full scope:
- Consent: ConsentScreen, ConsentRecord, ConsentProvider, ConsentRepository
- Support: HelpSupportScreen, SupportTicket, SupportProvider, SupportRepository. Note LogUploadRemoteDatasource sends data remotely.
- Admin: AdminDashboardScreen, AdminProvider, AdminRepository
- Trash: TrashScreen, TrashRepository
- Legal: LegalDocumentScreen
- OSS: OssLicensesScreen
- Edit Profile: EditProfileScreen

---

### Sub-phase 9.3: REWRITE toolbox-constraints.md

**Files:**
- Modify: `.claude/architecture-decisions/toolbox-constraints.md`

**Agent**: general-purpose

#### Step 9.3.1: Replace entire file

Read the current file, then rewrite. Replace:
- JSON-schema builder → registry-based model
- Remove toolbox_autofill table reference
- Hub + feature routing: ToolboxHomeScreen → calculator/forms/gallery/todos as independent features
- Add FormScreenRegistry, FormPdfFillerRegistry, FormCalculatorRegistry, FormValidatorRegistry patterns
- Each sub-feature (calculator, forms, gallery, todos) is its own feature directory under lib/features/

---

### Sub-phase 9.4: UPDATE entries-constraints.md

**Files:**
- Modify: `.claude/architecture-decisions/entries-constraints.md`

**Agent**: general-purpose

#### Step 9.4.1: Fix status states

Change 3-state to 2-state: draft/submitted only. Remove COMPLETE. Remove `completed_at` field.

#### Step 9.4.2: Fix location relationship

`locationId` is a direct FK, NOT a junction table.

#### Step 9.4.3: Remove syncStatus field

Remove any `syncStatus` field reference — sync is handled via change_log, not per-record status.

#### Step 9.4.4: Add entry capabilities

Add entry export and form attachment capabilities.

---

### Sub-phase 9.5: UPDATE contractors-constraints.md

**Files:**
- Modify: `.claude/architecture-decisions/contractors-constraints.md`

**Agent**: general-purpose

#### Step 9.5.1: Fix model fields

Actual fields: `id`, `projectId`, `name`, `type`, `contactName`, `phone`, `createdAt`, `updatedAt`, `createdByUserId`. Remove any reference to `role`, `email`, `company` — these don't exist.

#### Step 9.5.2: Add soft-delete integration

Note soft-delete support: deleted_at/deleted_by columns exist in the DB schema but are NOT exposed in the Contractor Dart model class. Soft-delete is handled at the datasource/query layer (WHERE deleted_at IS NULL filtering). The model itself does not expose these fields.

---

### Sub-phase 9.6: UPDATE remaining constraints (batch 1)

**Files:**
- Modify: `.claude/architecture-decisions/locations-constraints.md`
- Modify: `.claude/architecture-decisions/photos-constraints.md`
- Modify: `.claude/architecture-decisions/projects-constraints.md`

**Agent**: general-purpose

#### Step 9.6.1: locations-constraints.md

Fix junction table → direct FK (DailyEntry has `locationId`). Fix COMPLETE → SUBMITTED.

#### Step 9.6.2: photos-constraints.md

Fix field names: `filePath` not `local_path`, `remotePath` not `supabase_url`. Remove per-record `sync_status`. Add actual fields: `projectId`, `filename`, `caption`, `locationId`, `latitude`, `longitude`, `capturedAt`.

#### Step 9.6.3: projects-constraints.md

ProjectMode enum is `localAgency`/`mdot` (NOT lifecycle states PLANNING/ACTIVE/COMPLETE/ARCHIVED). Add multi-tenant company scope: `company_id`, `created_by_user_id`.

---

### Sub-phase 9.7: UPDATE remaining constraints (batch 2)

**Files:**
- Modify: `.claude/architecture-decisions/quantities-constraints.md`
- Modify: `.claude/architecture-decisions/weather-constraints.md`
- Modify: `.claude/architecture-decisions/pdf-v2-constraints.md`
- Modify: `.claude/architecture-decisions/dashboard-constraints.md`

**Agent**: general-purpose

#### Step 9.7.1: quantities-constraints.md

Fix "no direct sync" — `bid_item_adapter` and `entry_quantities_adapter` exist and sync directly.

#### Step 9.7.2: weather-constraints.md

Weather is NOT a placeholder. WeatherService calls Open-Meteo API (`https://api.open-meteo.com/v1/forecast`). WeatherCondition enum: sunny, cloudy, overcast, rainy, snow, windy. Auto-fetch in EntryEditorScreen (`_isFetchingWeather` flag).

#### Step 9.7.3: pdf-v2-constraints.md

Remove `deprecated/` folder reference — folder doesn't exist.

#### Step 9.7.4: dashboard-constraints.md

Remove `_buildStatCard` reference (method doesn't exist). Dashboard uses `DashboardStatCard` widget.

---

### Sub-phase 9.8: UPDATE auth-constraints + data-validation-rules

**Files:**
- Modify: `.claude/architecture-decisions/auth-constraints.md`
- Modify: `.claude/architecture-decisions/data-validation-rules.md`

**Agent**: general-purpose

#### Step 9.8.1: auth-constraints.md

Add:
- Consent gate: router checks ConsentProvider
- Multi-tenant company flow: CompanySetupScreen, PendingApprovalScreen, admin approval
- Company switching: SwitchCompanyUseCase
- **SECURITY HARD RULES (from review):**
  - company_id MUST come from JWT app_metadata, NEVER from client payload
  - Admin approval status MUST be validated server-side via RLS/functions, not just client-side provider state
  - Company switching MUST trigger session refresh to update JWT claims

#### Step 9.8.2: data-validation-rules.md

Add catch-without-logging anti-pattern note: catch blocks must always log the error, never silently swallow exceptions.

---

### Sub-phase 9.9: CREATE forms-constraints.md

**Files:**
- Create: `.claude/architecture-decisions/forms-constraints.md`

**Agent**: general-purpose

#### Step 9.9.1: Create the file

Create `.claude/architecture-decisions/forms-constraints.md` documenting:
- **Registry patterns:** How to register a new form — implement screen → register in FormScreenRegistry, implement PDF filler → register in FormPdfFillerRegistry, implement calculator → register in FormCalculatorRegistry, implement validator → register in FormValidatorRegistry
- **Form lifecycle:** draft → submitted (immutable after submit)
- **InspectorForm** is immutable (built-in definition, seeded at app init)
- **FormResponse** is project-scoped and mutable until submitted
- **Form export contracts** — how form data is exported to PDF
- **Auto-fill service contract** — how AutoFillService populates fields from project data
- **Key constraint:** Forms are NOT user-defined schemas. They are developer-defined via registries.

---

### Sub-phase 9.10: CREATE consent-telemetry-constraints.md

**Files:**
- Create: `.claude/architecture-decisions/consent-telemetry-constraints.md`

**Agent**: general-purpose

#### Step 9.10.1: Create the file

Create `.claude/architecture-decisions/consent-telemetry-constraints.md` documenting:
- **Sentry crash reporting:** Consent-gated via SentryConsent class in `lib/core/config/sentry_consent.dart`. No crash reports sent without active consent.
- **Aptabase analytics:** Consent-gated via Analytics class in `lib/core/analytics/analytics.dart`. No analytics events sent without active consent.
- **Consent flow gate:** AppRouter checks ConsentProvider. New users must complete consent before accessing any app screen.
- **ConsentRecord model:** Stores consent version, timestamp, and user choice.
- **Data collection rules:** Must have active consent before sending ANY telemetry. Opt-in by default (no data sent until explicit consent).
- **Opt-out behavior:** Disabling consent immediately stops all telemetry. Existing data retention follows privacy policy.
- **PII scrubbing:** Logger strips PII in release builds (configured in Logger class).
- **Sentry breadcrumb scrubbing:** Breadcrumbs may contain PII even when crash reports are consent-gated — apply same scrubbing.
- **Log upload PII filtering:** LogUploadRemoteDatasource must apply PII filtering before sending support logs.
- **Consent record integrity:** ConsentRecord should be validated server-side (not just trusted from client).
- **Data retention:** Reference the privacy policy for specific retention periods.

---

## Phase 10: State + Defect Files

### Sub-phase 10.1: CREATE feature state files

**Files:**
- Create: `.claude/state/feature-forms.json`
- Create: `.claude/state/feature-calculator.json`
- Create: `.claude/state/feature-gallery.json`
- Create: `.claude/state/feature-todos.json`

**Agent**: general-purpose

#### Step 10.1.1: Read an existing state file for schema

Read any existing `.claude/state/feature-*.json` file to match the exact schema.

#### Step 10.1.2: Create feature-forms.json

Create with:
- id: "forms"
- name: "Inspector Forms & MDOT Hub"
- status: "stable"
- description: "Registry-based form system supporting built-in inspector forms with PDF export, auto-fill, and MDOT 0582B calculations"
- docs paths: prds/forms-prd.md, forms-constraints.md
- constraints_file: "forms-constraints.md"
- constraints_summary: "Registry-based form architecture. Forms are developer-defined, not user-defined. Lifecycle: draft → submitted (immutable)."
- integration: depends_on: ["entries", "projects"], required_by: ["entries"]

#### Step 10.1.3: Create feature-calculator.json

Create with:
- id: "calculator"
- name: "Construction Calculator"
- status: "stable"
- description: "Standalone construction calculator for field calculations"

#### Step 10.1.4: Create feature-gallery.json

Create with:
- id: "gallery"
- name: "Photo Gallery"
- status: "stable"
- description: "Photo gallery browsing and management within toolbox"

#### Step 10.1.5: Create feature-todos.json

Create with:
- id: "todos"
- name: "Task Management"
- status: "stable"
- description: "Task/todo management for project-scoped work items"

---

### Sub-phase 10.2: UPDATE defect files

**Files:**
- Modify: `.claude/defects/_defects-photos.md`
- Modify: `.claude/defects/_defects-database.md`
- Modify: `.claude/defects/_defects-forms.md`
- Modify: `.claude/defects/_defects-sync-verification.md`
- Modify: `.claude/defects/_defects-settings.md`
- Modify: `.claude/defects/_defects-toolbox.md`

**Agent**: general-purpose

#### Step 10.2.1: _defects-photos.md

Fix `photo_detail_dialog.dart` path → `lib/features/entries/presentation/widgets/photo_detail_dialog.dart`. Fix `driver_server.dart` path → `lib/core/driver/driver_server.dart`.

#### Step 10.2.2: _defects-database.md

Mark `BackgroundSyncHandler.close()` defect as RESOLVED — the close() call no longer exists in the code.

#### Step 10.2.3: _defects-forms.md

Mark BUG-S04 as RESOLVED — `seedBuiltinForms` is now called via `AppInitializer.initialize()` from both `main.dart` and `main_driver.dart`.

#### Step 10.2.4: _defects-sync-verification.md

Mark BUG-SV-6 as RESOLVED — same fix as BUG-S04 (seedBuiltinForms via AppInitializer).

#### Step 10.2.5: _defects-settings.md

Move BUG-S09-1 to RESOLVED section. The text already says "Fixed in S667" but it remains in the Active section.

#### Step 10.2.6: _defects-toolbox.md

Resolve or redirect `form_fill_screen.dart [FILE REMOVED]` defects. form_fill_screen was replaced by FormViewerScreen at `lib/features/forms/presentation/screens/form_viewer_screen.dart`. Update defect entries to reference the new file path and mark the file-removed aspect as resolved.

---

## Phase 11: Skills

### Sub-phase 11.1: UPDATE implement skill

**Files:**
- Modify: `.claude/skills/implement/skill.md`

**Agent**: general-purpose

#### Step 11.1.1: Fix output path

Replace `/tmp/implement-orchestrator-output.txt` with `.claude/outputs/implement-orchestrator-output.txt` (Windows-safe path).

---

### Sub-phase 11.2: UPDATE audit-config skill

**Files:**
- Modify: `.claude/skills/audit-config/SKILL.md`

**Agent**: general-purpose

#### Step 11.2.1: Fix agent count

Change "9 files" to "13 files (10 definitions + 3 memory files)" or whatever the actual count is after reading the file.

---

### Sub-phase 11.3: UPDATE test skill

**Files:**
- Modify: `.claude/skills/test/SKILL.md`

**Agent**: general-purpose

#### Step 11.3.1: Fix testing keys count

Update testing keys count: 15 feature-specific key files + 1 barrel export (testing_keys.dart) = 16 total files in lib/shared/testing_keys/. Add the three new keys files to any enumerated list: `consent_keys.dart`, `documents_keys.dart`, `support_keys.dart`.

---

### Sub-phase 11.4: CREATE design-system reference

**Files:**
- Create: `.claude/skills/interface-design/references/design-system.md`

**Agent**: general-purpose

#### Step 11.4.1: Create design system reference

Document:
- **FieldGuideColors** ThemeExtension at `lib/core/theme/field_guide_colors.dart`
- **DesignConstants** at `lib/core/theme/design_constants.dart`
- **Design system components** from `lib/core/design_system/` (list all ~18+ components):
  AppScaffold, AppDialog, AppBottomSheet, AppBottomBar, AppTextField, AppText, AppIcon, AppToggle, AppGlassCard, AppCounterField, AppErrorState, AppInfoBanner, AppDragHandle, AppBudgetWarningChip, AppChip, AppListTile, AppEmptyState, AppLoadingState, AppMiniSpinner, AppPhotoGrid, AppProgressBar, AppSectionCard, AppSectionHeader, AppStickyHeader

For each component, note its file path and one-line purpose.

---

### Sub-phase 11.5: UPDATE codebase-tracing-paths

**Files:**
- Modify: `.claude/skills/systematic-debugging/references/codebase-tracing-paths.md`

**Agent**: general-purpose

#### Step 11.5.1: Verify and fix paths

Read the file. For each path referenced, verify it still exists in the codebase. Fix any stale paths to their current locations.

---

## Phase 12: Guides + Test Flows + Index

### Sub-phase 12.1: DELETE pagination-widgets-guide.md

**Files:**
- Delete: `.claude/docs/guides/implementation/pagination-widgets-guide.md`

**Agent**: general-purpose

#### Step 12.1.1: Delete the file

Delete `.claude/docs/guides/implementation/pagination-widgets-guide.md`. This file references PaginatedListView, PaginationBar, PaginationDots, PageNumberSelector widgets that were NEVER IMPLEMENTED.

---

### Sub-phase 12.2: UPDATE e2e-test-setup.md

**Files:**
- Modify: `.claude/docs/guides/testing/e2e-test-setup.md`

**Agent**: general-purpose

#### Step 12.2.1: Fix package name

Replace all occurrences of `com.example.construction_inspector` with `com.fvconstruction.construction_inspector` throughout the file. Fix iOS bundle ID similarly.

---

### Sub-phase 12.3: UPDATE manual-testing-checklist.md

**Files:**
- Modify: `.claude/docs/guides/testing/manual-testing-checklist.md`

**Agent**: general-purpose

#### Step 12.3.1: Add missing test suites

Add test suites for: forms, calculator, gallery, todos, consent/legal.

#### Step 12.3.2: Fix feature count

Change "12 features across 12 test suites" to "17 features across 17 test suites."

---

### Sub-phase 12.4: UPDATE INDEX.md

**Files:**
- Modify: `.claude/docs/INDEX.md`

**Agent**: general-purpose

#### Step 12.4.1: Fix feature doc count

Update count now that 4 new feature doc pairs exist (forms, calculator, gallery, todos).

#### Step 12.4.2: Add undocumented root docs

Add references to: `2026-03-28-ui-refactor-audit.md`, `ios-build-guide.md`, `pdf-pipeline-performance-audit.md`, `workflow-insights-report.md`.

#### Step 12.4.3: Add ui-prototyping-workflow.md reference

Add reference to `ui-prototyping-workflow.md`.

#### Step 12.4.4: Fix file statistics

Update any file/directory count statistics to match current reality.

---

### Sub-phase 12.5: UPDATE test-flows and guides README

**Files:**
- Modify: `.claude/test-flows/registry.md`
- Modify: `.claude/test-flows/sync-verification-guide.md`
- Modify: `.claude/docs/guides/README.md`

**Agent**: general-purpose

#### Step 12.5.1: test-flows/registry.md

Read and verify all screen references still point to valid files. Fix any wiring gap notes that are no longer accurate.

#### Step 12.5.2: test-flows/sync-verification-guide.md

Fix driver path from `lib/test_harness/driver_server.dart` to `lib/core/driver/driver_server.dart`.

#### Step 12.5.3: docs/guides/README.md

Fix "12 features" to "17 features."

---

## Final Verification

### Sub-phase 13.1: Phantom Reference Grep

**Agent**: general-purpose

#### Step 13.1.1: Grep for phantom references

After all phases complete, grep the entire `.claude/` directory (excluding `.git/`, `plans/completed/`, `specs/archived/`, `code-reviews/`, `adversarial_reviews/`, `debug-sessions/`, `logs/`) for the following phantom references. Any remaining hits are bugs to fix:

1. `SyncAdapter` (standalone, not as part of TableAdapter)
2. `SupabaseSyncAdapter`
3. `sync_queue`
4. `AppTheme.primaryBlue` (and `.success`, `.warning`, `.error`, `.textPrimary`, `.textSecondary`)
5. `seed_data_service`
6. `seed_data_loader`
7. `PdfImportProgressManager`
8. `PdfImportProgressDialog`
9. `form_fill_screen`
10. `project_selection_screen.dart` (in sync context)
11. `sync_status_banner`
12. `photo_service_impl`
13. `_buildStatCard`

For each hit, fix inline by replacing with the correct current reference.

---

## Dispatch Groups

| Group | Phases | Parallelism | Notes |
|-------|--------|-------------|-------|
| 1 | 8.1–8.8 | All sub-phases run in parallel | PRD updates — no interdependencies |
| 2 | 9.1–9.10 | All sub-phases run in parallel | Constraint updates — no interdependencies |
| 3 | 10.1–10.2 + 11.1–11.5 | All sub-phases run in parallel | State/defects + skills — independent |
| 4 | 12.1–12.5 | All sub-phases run in parallel | Guides/index — independent |
| Final | 13.1 | Sequential after group 4 | Phantom reference cleanup |
