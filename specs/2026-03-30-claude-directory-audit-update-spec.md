# Claude Directory Audit & Update Spec

**Date**: 2026-03-30
**Session**: 679
**Size**: L+ (80 files, 12 phases, documentation only)
**Status**: APPROVED

---

## Overview

### Purpose
Fix every live-context file in `.claude/` so agents spawned in future sessions get accurate codebase context post-S678. Currently ~80 files contain phantom architectures, deprecated API recommendations, wrong file paths, missing features, and structurally wrong descriptions.

### Success Criteria
- Every file path referenced in a live `.claude/` file resolves to an actual file in the codebase
- Every class name, provider name, and screen name referenced matches reality
- All 17 features are represented in FEATURE-MATRIX, state files, and documentation
- Rules describe patterns the code actually follows (clean architecture with `domain/`+`di/`, `FieldGuideColors` not deprecated `AppTheme.*`, `change_log` not `sync_queue`, `TableAdapter` not `SyncAdapter`)
- Zero "phantom" references (classes, files, or patterns that don't exist)

### Ground Truth Source
The opus codebase mapper output (agent `adb522feb54a93b88`, S679) serves as the authoritative reference for all updates. Every rewrite/update must be verified against it, not assumed.

### Approach Selected
**Tier-based (top-down)** — fix foundation files first (CLAUDE.md, state, rules), then agent context (docs, PRDs, constraints), then skills/guides. Each tier builds on already-fixed tiers above it.

### Alternatives Rejected
- **By feature (horizontal slices)** — too much file-hopping per phase, agents touching constraints + PRDs + docs + rules in one pass
- **By action type (rewrite/update/create)** — no logical grouping, hard to verify consistency across related files

---

## Scope

### Included (Live Context — Tiers 1-4)
- **Tier 1**: CLAUDE.md, MEMORY.md, _state.md, FEATURE-MATRIX.json, PROJECT-STATE.json, AGENT-FEATURE-MAPPING.json
- **Tier 2**: All 11 rules files
- **Tier 3**: 10 agent definitions, 3 agent memory files, 8 agent-memory directories, 26 feature docs (13 existing + 4 new pairs), 14 PRDs (13 existing + 1 new), 16 constraint files (14 existing + 2 new), 17 state files (13 existing + 4 new), 16 defect files
- **Tier 4**: 11 skill definitions + references, 6 guide docs, 2 test flow docs, INDEX.md, directory-reference.md

### Excluded
- Historical/archival files: completed plans, old code reviews, adversarial reviews, debug sessions, archived specs, dependency graphs
- App code (`lib/`, `test/`, `tools/`, `supabase/`) — no code changes
- `.claude/.git/` internals

### Depth
**Structural (Option B)** — feature docs include layer structure, key classes (repositories, providers, screens, use cases), DI wiring, and architectural patterns. Not exhaustive file lists of every widget and utility.

### PRD Scope
- **CREATE**: forms PRD only (complex registry system warrants full requirements doc)
- **REWRITE**: sync PRD (phantom architecture)
- **UPDATE**: settings PRD + remaining 11 PRDs (surgical fixes)
- **SKIP**: calculator, gallery, todos PRDs (simple features, overview + architecture docs suffice)

---

## Constraints & Ground Rules

1. **Every file path written must be verified against the codebase mapper output** — no assumed paths. This is the #1 cause of stale docs.
2. **Structural depth** — feature docs include layer structure, key classes, DI wiring, patterns. Not every widget or utility file.
3. **No app code changes** — this plan touches only `.claude/` files. If an audit finding reveals an actual code bug, log it to the appropriate defect file, don't fix it.
4. **Preserve existing format conventions** — each doc type has an established format. Match the existing format, just with correct content.
5. **Pagination widgets guide** — DELETE rather than rewrite. The widgets were never implemented.
6. **Defect file hygiene** — only mark defects RESOLVED if the audit confirmed the fix exists in code. Don't speculatively resolve.
7. **State files for new features** — follow the exact JSON schema used by the existing 13 `feature-*.json` files.

---

## Phase Structure

### Phase Group 1: Foundation (Tier 1)

#### Phase 1: CLAUDE.md + State Files
**Action**: UPDATE + REWRITE
**Files** (6):
- `CLAUDE.md` — fix skill count (10→11), verify all pointer paths, update Data Flow to show domain/use-case layer
- `state/FEATURE-MATRIX.json` — REWRITE: add forms, calculator, gallery, todos. Fix total_features 13→17. Update generated_at.
- `state/PROJECT-STATE.json` — fix app_version, release target, current_phase (S677 implemented), session_notes
- `state/AGENT-FEATURE-MAPPING.json` — add 4 missing features to routing
- `state/AGENT-CHECKLIST.json` — update if stale
- `docs/directory-reference.md` — add missing subdirectories (context-bundles, spikes, projects, settings.local.json)

---

### Phase Group 2: Rules (Tier 2)

#### Phase 2: Architecture + Data Layer Rules
**Action**: REWRITE
**Files** (2):
- `rules/architecture.md` — clean architecture is now the norm (not "only sync"). Add `domain/` and `di/` layers to standard feature structure. Fix `syncStatus` phantom field. Fix theme references to `FieldGuideColors`. Fix stale DB line references. Fix stale line number references throughout.
- `rules/backend/data-layer.md` — DB version 46 not 20. Add 7 missing schema files (extraction_tables, form_export_tables, entry_export_tables, document_tables, sync_engine_tables, support_tables, consent_tables). Fix feature list to 17. Remove phantom `seed_data_service.dart`/`seed_data_loader.dart`. Add `domain/` + `di/` layers to feature structure template.

#### Phase 3: Feature-Specific Rules
**Action**: REWRITE (sync) + UPDATE (rest)
**Files** (5):
- `rules/sync/sync-patterns.md` — REWRITE: replace phantom `SyncAdapter`/`SupabaseSyncAdapter` with actual `TableAdapter` + 20+ concrete adapters. Replace `sync_queue` with `change_log` trigger system. Fix file organization diagram. Add `SyncEngine`, `SyncRegistry`, `SyncMutex`, `IntegrityChecker`, `OrphanScanner`, `FcmHandler`, `SyncLifecycleManager`. Remove nonexistent screens (`project_selection_screen`) and widgets (`sync_status_banner`). Update adapter count to 20+.
- `rules/auth/supabase-auth.md` — UPDATE: fix Riverpod `ref.read` syntax → Provider `context.read`. Add consent gate routing. Add multi-tenant company flow. Add OTP verification flow. Verify deep link scheme (`com.fieldguideapp.inspector`).
- `rules/frontend/flutter-ui.md` — UPDATE: replace all deprecated `AppTheme.*` constants with `FieldGuideColors.of(context).*` and `Theme.of(context).colorScheme.*`. Fix all stale line number references (Stepper reference, `_buildStatCard`, home_screen ranges).
- `rules/database/schema-patterns.md` — UPDATE: fix version references. Remove phantom seed files. Update migration example to reflect current patterns.
- `rules/pdf/pdf-generation.md` — UPDATE: fix `data/services/` → `services/`. Fix `OcrConfigV2` → `TesseractConfigV2`. Add `MpExtractionService` reference. Remove `PdfImportProgressManager` reference.

---

### Phase Group 3: Agent Context (Tier 3)

#### Phase 4: Agent Definitions + Memory
**Action**: UPDATE
**Files** (~21):
- 10 agent definition files — key fixes:
  - `implement-orchestrator.md` + `skills/implement/skill.md`: `/tmp/` → Windows-safe temp path
  - `debug-research-agent.md`: remove MCP tools from frontmatter (subagents can't use MCP)
  - `auth-agent.md`: add 7 missing screens to screen list, add `di/auth_providers.dart`
  - `backend-data-layer-agent.md`: remove phantom `seed_data_service.dart`/`seed_data_loader.dart`, fix `sync_queue` → `change_log`, update DI location, add missing schema tables
  - `backend-supabase-agent.md`: remove phantom `supabase_schema_v4_rls.sql`, update schema table list (13→20+), fix `entry_personnel` → `entry_personnel_counts`
  - `code-review-agent.md`: fix "only sync uses clean architecture" → most features do
  - `frontend-flutter-specialist-agent.md`: verify widget catalog paths
  - `pdf-agent.md`: remove phantom `structure_preserver.dart`, fix logging `[PDF]` → `Logger.pdf()`
  - `qa-testing-agent.md`: fix testing keys count (13→16), add `consent_keys`, `documents_keys`, `support_keys`
  - `security-agent.md`: fix `sync_queue` → `change_log`, fix `pdf_data_builder.dart` glob path
- 3 agent `.memory.md` files:
  - `backend-data-layer-agent.memory.md`: fix DB version, remove phantom seed files
  - Others: surgical fixes per audit
- 8 `agent-memory/*/MEMORY.md` files:
  - `code-review-agent`: fix main.dart line count, remove phantom `row_classifier_v2.dart`
  - `pdf-agent`: remove 6 phantom file references (structure_preserver, deprecated dir, 4 test files)
  - `security-agent`: mark 3 resolved findings (flutter_secure_storage, PRAGMA, line numbers)

#### Phase 5: Feature Architecture Docs — REWRITE (13 existing)
**Action**: REWRITE
**Files** (13):
All `docs/features/feature-*-architecture.md` for: auth, contractors, dashboard, entries, locations, pdf, photos, projects, quantities, settings, sync, toolbox, weather.

Each rewritten doc must include:
- Accurate layer structure showing `data/` (datasources/local, datasources/remote, models, repositories), `domain/` (repositories interfaces, usecases), `presentation/` (providers, screens, widgets, controllers), `di/`
- Key class names verified against codebase mapper
- DI wiring (what's in the `di/*_providers.dart` file)
- Architectural patterns specific to that feature
- Relationships to other features
- NO exhaustive file list — structural depth only

Priority rewrites (most structurally wrong):
- auth (company/team system completely missing)
- settings (consent/support/admin/trash completely missing)
- projects (assignments/sync-health/import completely missing)
- entries (7 use cases, export/document subsystems missing)
- sync (phantom architecture)
- toolbox (all provider paths wrong, forms registry missing)

#### Phase 6: Feature Overview Docs — UPDATE (13 existing)
**Action**: UPDATE
**Files** (13):
All `docs/features/feature-*-overview.md` for the same 13 features.

Each updated doc must fix:
- Key Files table: correct paths, add missing files, remove nonexistent files
- Purpose/scope description (especially settings — now owns consent/legal/support/admin)
- Screen list (auth has 10 screens, not 3)
- Provider list
- Feature relationships

#### Phase 7: Feature Docs — CREATE (4 missing features)
**Action**: CREATE
**Files** (8):
- `docs/features/feature-forms-overview.md` + `feature-forms-architecture.md`
- `docs/features/feature-calculator-overview.md` + `feature-calculator-architecture.md`
- `docs/features/feature-gallery-overview.md` + `feature-gallery-architecture.md`
- `docs/features/feature-todos-overview.md` + `feature-todos-architecture.md`

Content source: codebase mapper output for each feature (forms: 72 files, calculator: 13, gallery: 5, todos: 12).

#### Phase 8: PRDs
**Action**: CREATE (1) + REWRITE (1) + UPDATE (12)
**Files** (14):
- CREATE `prds/forms-prd.md` — registry system (FormScreenRegistry, FormPdfFillerRegistry, FormCalculatorRegistry, FormValidatorRegistry, FormQuickActionRegistry, FormInitialDataFactory), form lifecycle (draft/submitted), InspectorForm + FormResponse + FormExport models, MDOT 0582B specifics (calculator, validator, PDF filler), auto-fill service, form state hashing
- REWRITE `prds/sync-prd.md` — replace entire `sync_queue`/`SyncAdapter` description with `change_log`/`TableAdapter` engine, 20+ adapters, SyncEngine + SyncOrchestrator, trigger-based change tracking
- UPDATE `prds/settings-prd.md` — add consent (ConsentScreen, ConsentRecord, ConsentProvider), help/support (HelpSupportScreen, SupportTicket, SupportProvider), legal (LegalDocumentScreen), OSS (OssLicensesScreen), admin (AdminDashboardScreen, AdminProvider), trash (TrashScreen, TrashRepository), edit profile. Update storage from SharedPreferences to UserProfile model.
- UPDATE `prds/auth-prd.md` — fix post-auth navigation, remove MOCK_AUTH, add local SQLite tables (user_profiles, companies), add extended auth flows (OTP, inactivity, consent gate)
- UPDATE `prds/entries-prd.md` — fix status lifecycle (2-state not 3), fix weather field type, add multi-tenant fields
- UPDATE `prds/projects-prd.md` — add assignments step, add multi-tenant fields, clarify MDOT mode is placeholder
- UPDATE `prds/photos-prd.md` — fix photo_detail_dialog path (moved to entries), add soft-delete columns, file_path nullable
- UPDATE `prds/dashboard-prd.md` — fix navigation structure (not bottom nav)
- UPDATE `prds/contractors-prd.md` — fix sync description to change_log
- UPDATE `prds/quantities-prd.md` — note open defects (search, sort)
- UPDATE `prds/weather-prd.md` — fix field name (WeatherCondition enum not string)
- UPDATE `prds/toolbox-prd.md` — fix file counts for gallery/todos
- UPDATE `prds/pdf-extraction-v2-prd-2.0.md` — remove [NOT IMPLEMENTED] TODO for confidence_calibrator, note pdfrx migration done
- `prds/2026-02-21-project-based-architecture-prd.md` — UPDATE stale sync/schema references (historical but cross-referenced)

#### Phase 9: Architecture Decisions / Constraints
**Action**: REWRITE (3) + UPDATE (11) + CREATE (2)
**Files** (16):
- REWRITE `sync-constraints.md` — replace hash-based with trigger-based change_log, replace all-or-nothing with per-adapter processing, replace SyncAdapter with TableAdapter, add SyncEngine/SyncRegistry/SyncMutex/IntegrityChecker/OrphanScanner/FCM
- REWRITE `settings-constraints.md` — expand scope from "theme/language/notifications" to consent/support/admin/trash/legal/OSS. Add ConsentProvider, SupportProvider, AdminProvider. Note remote datasource (log_upload).
- REWRITE `toolbox-constraints.md` — replace JSON-schema builder pattern with registry-based model. Remove `toolbox_autofill` table reference. Update to hub + feature routing model. Add MDOT Hub, form registries.
- UPDATE `entries-constraints.md` — fix 3-state → 2-state (draft/submitted). Remove COMPLETE references. Fix `completed_at` → doesn't exist. Fix locationId (direct FK not junction table). Remove `syncStatus` field reference. Add entry export and forms attachment.
- UPDATE `contractors-constraints.md` — fix model fields (remove role/email/company, add type/contactName/createdByUserId). Fix `entry_contractors` junction description. Add soft-delete integration.
- UPDATE `locations-constraints.md` — fix junction table → direct FK. Fix COMPLETE → SUBMITTED.
- UPDATE `photos-constraints.md` — fix field names (filePath not local_path, remotePath not supabase_url). Remove per-record sync_status. Add actual fields (projectId, filename, caption, locationId, latitude, longitude, capturedAt).
- UPDATE `projects-constraints.md` — fix lifecycle states (ProjectMode is localAgency/mdot, not PLANNING/ACTIVE/COMPLETE/ARCHIVED). Add multi-tenant company scope.
- UPDATE `quantities-constraints.md` — fix "no direct sync" claim (bid_item_adapter and entry_quantities_adapter exist).
- UPDATE `weather-constraints.md` — weather is NOT a placeholder. WeatherService calls Open-Meteo API. Fix condition enum values. Note auto-fetch in EntryEditorScreen.
- UPDATE `pdf-v2-constraints.md` — remove deprecated/ folder reference (already cleaned up).
- UPDATE `dashboard-constraints.md` — fix `_buildStatCard` reference (method doesn't exist).
- UPDATE `auth-constraints.md` — add consent gate, multi-tenant company flow, admin approval.
- UPDATE `data-validation-rules.md` — minor, add catch-without-logging note.
- CREATE `forms-constraints.md` — registry patterns (how to register a new form: screen, PDF filler, calculator, validator, quick actions), form lifecycle (draft→submitted), InspectorForm immutability, FormResponse project-scoped, form export contracts, auto-fill service contract
- CREATE `consent-telemetry-constraints.md` — Sentry crash reporting (consent-gated via SentryConsent), Aptabase analytics (consent-gated via Analytics class), consent flow gate in router, ConsentRecord model, data collection rules, opt-in/opt-out behavior, PII scrubbing in Logger

#### Phase 10: State + Defect Files
**Action**: CREATE (4) + UPDATE (~6)
**Files** (~10):
- CREATE `state/feature-forms.json`
- CREATE `state/feature-calculator.json`
- CREATE `state/feature-gallery.json`
- CREATE `state/feature-todos.json`
- UPDATE `defects/_defects-photos.md` — fix photo_detail_dialog path (now in entries/widgets), fix driver_server path (now lib/core/driver/)
- UPDATE `defects/_defects-database.md` — mark BackgroundSyncHandler.close() defect RESOLVED (close() call removed)
- UPDATE `defects/_defects-forms.md` — mark BUG-S04 RESOLVED (seedBuiltinForms now called via AppInitializer from both entrypoints)
- UPDATE `defects/_defects-sync-verification.md` — mark BUG-SV-6 RESOLVED (same fix as BUG-S04)
- UPDATE `defects/_defects-settings.md` — move BUG-S09-1 to RESOLVED (already marked "Fixed in S667" but still in Active)
- UPDATE `defects/_defects-toolbox.md` — resolve or redirect `form_fill_screen.dart [FILE REMOVED]` defects

---

### Phase Group 4: Skills & Guides (Tier 4)

#### Phase 11: Skills
**Action**: UPDATE + CREATE
**Files** (~5):
- UPDATE `skills/implement/skill.md` — fix `/tmp/` path → Windows-safe temp path (e.g., `$env:TEMP` or `.claude/outputs/`)
- UPDATE `skills/audit-config/SKILL.md` — fix agent count "9 files" → 13 files (10 defs + 3 memory)
- UPDATE `skills/test/SKILL.md` — fix testing keys count (13→16), add consent_keys, documents_keys, support_keys
- CREATE `skills/interface-design/references/design-system.md` — document FieldGuideColors ThemeExtension, DesignConstants, AppScaffold, design system component catalog from `lib/core/design_system/`
- UPDATE `skills/systematic-debugging/references/codebase-tracing-paths.md` — verify paths still valid

#### Phase 12: Guides + Test Flows + Index
**Action**: DELETE (1) + UPDATE (6) + CREATE (0)
**Files** (7):
- DELETE `docs/guides/implementation/pagination-widgets-guide.md` — references widgets that were never implemented
- UPDATE `docs/guides/testing/e2e-test-setup.md` — fix package name `com.example.construction_inspector` → `com.fvconstruction.construction_inspector` throughout (or actual package name if different)
- UPDATE `docs/guides/testing/manual-testing-checklist.md` — add test suites for forms, calculator, gallery, todos, consent/legal. Fix feature count 12→17.
- UPDATE `docs/INDEX.md` — fix "all 17 features" claim (now accurate with 4 new docs). Add 4 undocumented root docs. Add ui-prototyping-workflow.md reference. Fix file statistics.
- UPDATE `test-flows/registry.md` — fix wiring gap notes, verify screen references
- UPDATE `test-flows/sync-verification-guide.md` — fix driver path reference
- UPDATE `docs/guides/README.md` — fix "12 features" → 17

---

## Risk & Verification

### Risks

| Risk | Mitigation |
|------|-----------|
| Agent rewrites a doc with assumed class names | Plan mandates codebase mapper output as single source of truth. Review agents verify paths post-write. |
| 80 files is a lot of context for implementing agents | Batch by phase group. Each group's files are thematically related. |
| Forms PRD accuracy | Codebase mapper captured full registry system, use cases, screen structure. PRD describes what exists. |
| Docs drift stale after next implementation | Out of scope. Future `/audit-config` runs should catch drift. |

### Verification Strategy

After each phase group completes:
1. **Spot-check 3 random files** per phase for path accuracy against actual `lib/` structure
2. **Grep `.claude/` for known phantom references** that should be eliminated:
   - `SyncAdapter` (not as part of `TableAdapter`)
   - `SupabaseSyncAdapter`
   - `sync_queue`
   - `AppTheme.primaryBlue`
   - `seed_data_service`
   - `seed_data_loader`
   - `PdfImportProgressManager`
   - `PdfImportProgressDialog`
   - `form_fill_screen`
   - `project_selection_screen.dart` (sync feature)
   - `sync_status_banner`
   - `photo_service_impl`
3. **Verify FEATURE-MATRIX.json** lists exactly 17 features after Phase 1

---

## Audit Agent Outputs (Reference)

The following agent outputs contain the detailed findings this spec is based on:

| Agent | Type | ID | Focus |
|-------|------|----|-------|
| CLAUDE.md + state | sonnet | a06089b06f74b9d1d | FEATURE-MATRIX, PROJECT-STATE, CLAUDE.md, INDEX.md |
| Agents + skills | sonnet | af85722fa031b867f | 38 findings across 10 agents + 11 skills |
| Feature docs + guides | sonnet | a849b694cbec692ac | All 26 feature docs + 6 guides |
| Architecture + rules | sonnet | a3bc48871c0422e85 | 14 constraint files + 11 rule files |
| PRDs + defects | sonnet | a947547a1a7c3a176 | 14 PRDs + 16 defect files + test flows |
| Codebase mapper | opus | adb522feb54a93b88 | Ground truth: every feature, class, provider, screen |
| Deep content auditor | opus | afaa17d61e15b6700 | Cross-referenced every doc against source code |
| Gap analyst | opus | a6f7496b791f9b598 | 11 HIGH + 14 MEDIUM + 10 LOW priority gaps |
