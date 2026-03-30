# Claude Directory Audit & Update — Part 1: Foundation, Rules, Agents

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix all Tier 1 (foundation) and Tier 2 (rules) files plus agent definitions to reflect accurate codebase state post-S678.
**Spec:** `.claude/specs/2026-03-30-claude-directory-audit-update-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-30-claude-directory-audit-update/analysis.md`

**Blast Radius:** ~35 direct files, 0 dependent, 0 tests, 0 cleanup

**Dispatch Groups:**
- **Group 1:** Phase 1 (must complete first — other phases reference CLAUDE.md conventions)
- **Group 2:** Phase 2 + Phase 3 (rules can be done in parallel)
- **Group 3:** Phase 4 (agents reference rules, so rules must be done first)
- **Verification:** grep check after all complete

---

## Phase 1: CLAUDE.md + State Files

### Sub-phase 1.1: Update CLAUDE.md

**Files:**
- Modify: `.claude/CLAUDE.md`

**Agent**: general-purpose

#### Step 1.1.1: Fix skill count in Pointers table

Read `.claude/CLAUDE.md`. In the Pointers table, the row for Agents says "10 definitions" — verify the actual count by listing `.claude/agents/*.md` (exclude memory files). If the count is different from 10, update it. Do the same for Skills by listing `.claude/skills/*.md` — the spec says it should be 11, not 10. Update the Skills row to reflect the actual count.

#### Step 1.1.2: Update Data Flow diagram

In the Data Flow section, replace:
```
Screen -> Provider -> Repository -> SQLite (local) -> Supabase (sync)
```
with:
```
Screen -> Provider -> UseCase -> Repository -> SQLite (local) -> Supabase (sync)
```
This reflects the clean architecture refactor (S676) which added domain/usecases layers.

#### Step 1.1.3: Verify all pointer paths

For each path listed in the Pointers table, verify the file/directory actually exists. If any path is broken, fix it. Key paths to check:
- `.claude/agents/`
- `.claude/skills/`
- `.claude/docs/directory-reference.md`
- `.claude/rules/platform-standards.md`
- `.claude/rules/frontend/ui-prototyping.md`
- `.claude/rules/testing/patrol-testing.md`
- `.claude/memory/MEMORY.md`
- `.claude/logs/state-archive.md`
- `.claude/logs/defects-archive.md`
- `.claude/backlogged-plans/2026-02-15-audit-system-design.md`

### Sub-phase 1.2: Rewrite FEATURE-MATRIX.json

**Files:**
- Modify: `.claude/state/FEATURE-MATRIX.json`

**Agent**: general-purpose

#### Step 1.2.1: Read current file and identify gaps

Read `.claude/state/FEATURE-MATRIX.json`. Identify which of the 17 features are present and which are missing. The full feature list is: auth, calculator, contractors, dashboard, entries, forms, gallery, locations, pdf, photos, projects, quantities, settings, sync, todos, toolbox, weather.

#### Step 1.2.2: Add missing feature entries

For each missing feature (expected: calculator, forms, gallery, todos), add an entry following the exact same JSON schema as existing entries. Each entry needs:
- `name`: short name (e.g., "calculator")
- `full_name`: display name (e.g., "Calculator")
- `status`: set to "implemented" if the feature directory exists in `lib/features/`
- `docs`: object with paths to any feature-specific docs
- `constraints`: path to feature-specific constraints if any
- `test_coverage`: set appropriately based on whether tests exist
- `required_by`: array of features that depend on this one
- `depends_on`: array of features this one depends on

Key dependency relationships:
- calculator, forms, gallery, todos all depend on toolbox (toolbox is the hub)
- forms depends on pdf (for export)
- gallery depends on photos

#### Step 1.2.3: Fix total_features count

Update `total_features` from 13 to 17.

#### Step 1.2.4: Update generated_at timestamp

Set `generated_at` to `"2026-03-30"`.

### Sub-phase 1.3: Update PROJECT-STATE.json

**Files:**
- Modify: `.claude/state/PROJECT-STATE.json`

**Agent**: general-purpose

#### Step 1.3.1: Read and fix version fields

Read `.claude/state/PROJECT-STATE.json`. Fix `app_version` to match `last_release_version` which should be `"0.1.0"`.

#### Step 1.3.2: Fix next_release_target

The `next_release_target` has a past date of `"2026-03-10"`. Update it to a reasonable future date or set it to `"TBD"` if no specific target is set.

#### Step 1.3.3: Update current_phase and session_notes

Update `current_phase` to reflect that S676 (Clean Architecture Refactor) and S677 (Pre-Release Hardening) are IMPLEMENTED. Update `session_notes` to reference S678 (Claude Directory Audit).

### Sub-phase 1.4: Update AGENT-FEATURE-MAPPING.json

**Files:**
- Modify: `.claude/state/AGENT-FEATURE-MAPPING.json`

**Agent**: general-purpose

#### Step 1.4.1: Add missing features to features array

Read `.claude/state/AGENT-FEATURE-MAPPING.json`. Add entries for the 4 missing features (calculator, forms, gallery, todos) to the `features` array, following the exact same schema as existing entries. For each:
- `calculator`: primary_agent = "general-purpose", supporting_agents = ["frontend-flutter-specialist"]
- `forms`: primary_agent = "general-purpose", data_agent = "backend-data-layer", supporting_agents = ["frontend-flutter-specialist", "pdf"]
- `gallery`: primary_agent = "frontend-flutter-specialist", supporting_agents = ["general-purpose"]
- `todos`: primary_agent = "general-purpose", supporting_agents = ["frontend-flutter-specialist"]

#### Step 1.4.2: Update agent arrays to include new features

For each agent that is listed as primary or supporting for the new features, update that agent's `primary_features` and `supporting_features` arrays to include the new feature names.

### Sub-phase 1.5: Update AGENT-CHECKLIST.json

**Files:**
- Modify: `.claude/state/AGENT-CHECKLIST.json`

**Agent**: general-purpose

#### Step 1.5.1: Read and update if stale

Read `.claude/state/AGENT-CHECKLIST.json`. Check if any entries reference outdated information (wrong file paths, removed tools, stale counts). Update any stale entries to match current state.

### Sub-phase 1.6: Update directory-reference.md

**Files:**
- Modify: `.claude/docs/directory-reference.md`

**Agent**: general-purpose

#### Step 1.6.1: Add missing .claude/ subdirectories

Read `.claude/docs/directory-reference.md`. Add entries for any missing `.claude/` subdirectories. Verify these exist and add if missing from the doc:
- `context-bundles/`
- `spikes/`
- `projects/`
- `settings.local.json`

#### Step 1.6.2: Clarify toolbox sub-features as full features

If the document describes calculator, forms, gallery, or todos as mere "sub-features of toolbox," update the descriptions to clarify they are full features with their own `lib/features/` directories, data layers, and presentation layers. Toolbox is a hub that routes to them, but each is a standalone feature.

---

## Phase 2: Architecture + Data Layer Rules

### Sub-phase 2.1: Rewrite architecture.md

**Files:**
- Modify: `.claude/rules/architecture.md`

**Agent**: general-purpose

#### Step 2.1.1: Read current file

Read `.claude/rules/architecture.md` in full.

#### Step 2.1.2: Update clean architecture scope

Replace any language that says clean architecture is "only used by sync" or limited to specific features. The correct state is: clean architecture is now the norm across nearly ALL features after the S676 refactor.

#### Step 2.1.3: Document standard feature structure

Ensure the standard feature structure template includes all four layers:
- `data/` — contains `datasources/local/`, `datasources/remote/`, `models/`, `repositories/`
- `domain/` — contains `repositories/` (interfaces), `usecases/`
- `presentation/` — contains `providers/`, `screens/`, `widgets/`, `controllers/`
- `di/` — contains feature-specific provider definitions

#### Step 2.1.4: Remove phantom syncStatus field reference

Search the file for any reference to a `syncStatus` field on DailyEntry or any model. Remove it. The correct sync mechanism is: SQLite triggers auto-populate the `change_log` table on INSERT/UPDATE/DELETE. There is no per-model sync status field.

#### Step 2.1.5: Replace AppTheme color references

Replace ALL `AppTheme.*` color references with the correct patterns. Read `lib/core/theme/field_guide_colors.dart` to verify exact property names. Expected mappings:
- `AppTheme.primaryBlue` → `Theme.of(context).colorScheme.primary`
- `AppTheme.success` / `AppTheme.statusSuccess` → `FieldGuideColors.of(context).statusSuccess`
- `AppTheme.warning` / `AppTheme.statusWarning` → `FieldGuideColors.of(context).statusWarning`
- `AppTheme.error` / `AppTheme.statusError` → `Theme.of(context).colorScheme.error` (NO FieldGuideColors equivalent)
- `AppTheme.textPrimary` → `Theme.of(context).colorScheme.onSurface`
- `AppTheme.textSecondary` → `Theme.of(context).colorScheme.onSurfaceVariant`
**IMPORTANT**: Verify exact property names by reading field_guide_colors.dart — do NOT assume names from this plan.

#### Step 2.1.6: Fix stale line number references

Fix any line number references to `database_service.dart` — the file is now 1900+ lines at schema version 46, not 180 lines. Fix any stale `home_screen.dart` line references by reading the actual file to get current line numbers. Remove specific line numbers if they will go stale quickly; prefer method/class name references instead.

#### Step 2.1.7: Update feature count

Ensure the file references 17 features total (not 13 or any other number).

#### Step 2.1.8: Update anti-pattern table

Review the anti-pattern table. Specifically: if any row recommends `AppTheme.*` as the FIX for hardcoded colors, update it to recommend `Theme.of(context).colorScheme.*` and `FieldGuideColors.of(context).*` instead — AppTheme constants are now deprecated. Also add `AppTheme.*` usage as an anti-pattern if not already listed.

### Sub-phase 2.2: Rewrite data-layer.md

**Files:**
- Modify: `.claude/rules/backend/data-layer.md`

**Agent**: general-purpose

#### Step 2.2.1: Read current file

Read `.claude/rules/backend/data-layer.md` in full.

#### Step 2.2.2: Fix DB version

Update all references to the database version. The current version is 46, not 20 or any other number.

#### Step 2.2.3: Update schema organization

Replace the schema file list with the correct 14 files (verify by listing `lib/core/database/schema/`):
- core_tables, entry_tables, contractor_tables, personnel_tables, quantity_tables, photo_tables, toolbox_tables, extraction_tables, sync_tables, sync_engine_tables, form_export_tables, entry_export_tables, document_tables, consent_tables, support_tables

Note: the exact count may differ — list `lib/core/database/schema/` to get the ground truth list.

#### Step 2.2.4: Update feature count to 17

Replace any feature count that says fewer than 17. Add calculator, forms, gallery, todos if they are missing from any feature list.

#### Step 2.2.5: Remove phantom seed files

Remove ALL references to `seed_data_service.dart` and `seed_data_loader.dart`. These files DO NOT EXIST in the codebase. Search the entire file for these strings and remove every mention.

#### Step 2.2.6: Update feature structure template

Ensure the feature structure template shows all four layers: `data/`, `domain/`, `presentation/`, `di/`. This matches the post-S676 clean architecture standard.

#### Step 2.2.7: Remove SyncStatus enum reference

Remove any reference to a `SyncStatus` enum. This does not exist. Sync uses `change_log` triggers, not per-model status enums.

#### Step 2.2.8: Document shared base classes

Ensure these shared base classes are correctly documented with their actual paths:
- `BaseRepository` and `ProjectScopedRepository` — located in `lib/shared/repositories/`
- `BaseLocalDatasource`, `GenericLocalDatasource`, `ProjectScopedDatasource` — located in `lib/shared/datasources/`

---

## Phase 3: Feature-Specific Rules

### Sub-phase 3.1: Rewrite sync-patterns.md

**Files:**
- Modify: `.claude/rules/sync/sync-patterns.md`

**Agent**: general-purpose

#### Step 3.1.1: Read current file

Read `.claude/rules/sync/sync-patterns.md` in full.

#### Step 3.1.2: Replace phantom SyncAdapter with TableAdapter

Remove all references to `SyncAdapter` (as a standalone interface) and `SupabaseSyncAdapter`. Replace with the actual architecture:
- `TableAdapter` — abstract class in `lib/features/sync/adapters/table_adapter.dart`
- This is the base class for all concrete adapters

#### Step 3.1.3: Document concrete adapters

List the 20+ concrete adapters. Verify the actual list by reading `lib/features/sync/adapters/` directory, but expected adapters include:
- ProjectAdapter, LocationAdapter, ContractorAdapter, EquipmentAdapter
- PersonnelTypeAdapter, BidItemAdapter, DailyEntryAdapter
- EntryContractorsAdapter, EntryEquipmentAdapter, EntryPersonnelCountsAdapter, EntryQuantitiesAdapter
- PhotoAdapter, InspectorFormAdapter, FormResponseAdapter, FormExportAdapter
- EntryExportAdapter, DocumentAdapter, TodoItemAdapter
- ProjectAssignmentAdapter, CalculationHistoryAdapter, TypeConverters

#### Step 3.1.4: Replace sync_queue with change_log system

Search for and remove any references to `sync_queue` (if present — may not be in this file). Replace with the correct mechanism:
- SQLite triggers auto-populate the `change_log` table on INSERT/UPDATE/DELETE
- The `ChangeTracker` class reads from `change_log` to determine what needs syncing

#### Step 3.1.5: Document engine components

Ensure these engine components are documented:
- `SyncEngine` — core sync execution
- `ChangeTracker` — reads change_log
- `ConflictResolver` — handles conflicts
- `IntegrityChecker` — validates data integrity
- `SyncMutex` — prevents concurrent syncs
- `SyncRegistry` — registers adapters
- `OrphanScanner` — finds orphaned records
- `StorageCleanup` — cleans up old data
- `ScopeType` — enum for sync scope

#### Step 3.1.6: Document application layer

Document the application-layer orchestration:
- `SyncOrchestrator` — coordinates sync operations
- `SyncLifecycleManager` — manages sync lifecycle
- `BackgroundSyncHandler` — handles background sync
- `FcmHandler` — handles Firebase Cloud Messaging for push-triggered syncs

#### Step 3.1.7: Document config, domain, and DI

- Config: `SyncConfig`
- Domain: `SyncTypes` (in `sync_types.dart`)
- DI: `sync_providers.dart`

#### Step 3.1.8: Fix screen references

Replace any reference to `project_selection_screen.dart` (doesn't exist in sync context) with the correct screens:
- `SyncDashboardScreen`
- `ConflictViewerScreen`

Replace any reference to `sync_status_banner` widget (doesn't exist) with the correct widgets:
- `SyncStatusIcon`
- `DeletionNotificationBanner`

### Sub-phase 3.2: Update supabase-auth.md

**Files:**
- Modify: `.claude/rules/auth/supabase-auth.md`

**Agent**: general-purpose

#### Step 3.2.1: Read current file

Read `.claude/rules/auth/supabase-auth.md` in full.

#### Step 3.2.2: Fix Riverpod syntax to Provider syntax

Search for any `ref.read()` or `ref.watch()` Riverpod-style syntax. Replace with `context.read()` / `context.watch()` Provider-style syntax. The app uses the `provider` package, NOT Riverpod.

#### Step 3.2.3: Add consent gate documentation

Add documentation about the consent gate in the router: `AppRouter` checks `ConsentProvider` to determine if the user has accepted terms before allowing access to the main app.

#### Step 3.2.4: Add multi-tenant company flow

Document the multi-tenant company flow screens:
- `CompanySetupScreen` — company registration
- `PendingApprovalScreen` — waiting for admin approval
- Admin approval flow

#### Step 3.2.5: Add OTP verification flow

Document the OTP verification flow using `OtpVerificationScreen`.

#### Step 3.2.6: Verify deep link scheme

Ensure the documented deep link scheme is `com.fieldguideapp.inspector`.

#### Step 3.2.7: Update auth screen list

Ensure the complete list of 10 auth screens is documented:
1. LoginScreen
2. RegisterScreen
3. ForgotPasswordScreen
4. OtpVerificationScreen
5. UpdatePasswordScreen
6. ProfileSetupScreen
7. CompanySetupScreen
8. PendingApprovalScreen
9. AccountStatusScreen
10. UpdateRequiredScreen

### Sub-phase 3.3: Update flutter-ui.md

**Files:**
- Modify: `.claude/rules/frontend/flutter-ui.md`

**Agent**: general-purpose

#### Step 3.3.1: Read current file

Read `.claude/rules/frontend/flutter-ui.md` in full.

#### Step 3.3.2: Replace deprecated AppTheme constants

Replace ALL deprecated `AppTheme.*` constants. Read `lib/core/theme/field_guide_colors.dart` to verify exact property names. Expected mappings (same as Step 2.1.5):
- `AppTheme.primaryBlue` → `Theme.of(context).colorScheme.primary`
- `AppTheme.success`/`statusSuccess` → `FieldGuideColors.of(context).statusSuccess`
- `AppTheme.warning`/`statusWarning` → `FieldGuideColors.of(context).statusWarning`
- `AppTheme.error`/`statusError` → `Theme.of(context).colorScheme.error` (NO FieldGuideColors equivalent)
- `AppTheme.textPrimary` → `Theme.of(context).colorScheme.onSurface`
- `AppTheme.textSecondary` → `Theme.of(context).colorScheme.onSurfaceVariant`
**IMPORTANT**: Verify exact property names by reading field_guide_colors.dart.

#### Step 3.3.3: Fix stale widget references

Remove or correct these stale references:
- EntryEditorScreen does NOT use a `Stepper` widget — remove any claim it does
- `_buildStatCard` method does NOT exist on the dashboard — remove references
- `DashboardStatCard` widget is located at `lib/features/dashboard/presentation/widgets/dashboard_stat_card.dart`

#### Step 3.3.4: Update home_screen.dart line references

Read `lib/features/entries/presentation/screens/home_screen.dart` to get current line numbers. Update any stale line references in the rule file to match the current code. Prefer method/class name references over line numbers where possible.

### Sub-phase 3.4: Update schema-patterns.md

**Files:**
- Modify: `.claude/rules/database/schema-patterns.md`

**Agent**: general-purpose

#### Step 3.4.1: Read current file

Read `.claude/rules/database/schema-patterns.md` in full.

#### Step 3.4.2: Fix version references

Update all database version references to 46 (current version).

#### Step 3.4.3: Remove phantom seed file references

Remove ALL references to `seed_data_service.dart` and `seed_data_loader.dart`. These files do not exist.

#### Step 3.4.4: Update migration example

If the file contains a migration example, verify it reflects the current `openDatabase` pattern by reading `lib/core/database/database_service.dart` (first ~100 lines for the open pattern). Update the example if stale.

### Sub-phase 3.5: Update pdf-generation.md

**Files:**
- Modify: `.claude/rules/pdf/pdf-generation.md`

**Agent**: general-purpose

#### Step 3.5.1: Read current file

Read `.claude/rules/pdf/pdf-generation.md` in full.

#### Step 3.5.2: Fix service directory path

Replace any reference to `data/services/` with the correct path: `lib/features/pdf/services/`. Verify by listing the actual directory.

#### Step 3.5.3: Fix OcrConfigV2 reference

Replace `OcrConfigV2` with `TesseractConfigV2`. The actual file is at `lib/features/pdf/ocr/tesseract_config_v2.dart` (verify by glob).

#### Step 3.5.4: Add MpExtractionService reference

Add a reference to `MpExtractionService` if not already present. Verify the actual file path by searching for it in `lib/features/pdf/`.

#### Step 3.5.5: Remove PdfImportProgressManager reference

Remove any reference to `PdfImportProgressManager`. This class does not exist.

---

## Phase 4: Agent Definitions + Memory

### Sub-phase 4.1: Fix implement-orchestrator.md

**Files:**
- Modify: `.claude/agents/implement-orchestrator.md`

**Agent**: general-purpose

#### Step 4.1.1: Check for /tmp/ path and fix if present

Read `.claude/agents/implement-orchestrator.md`. Search for any `/tmp/` path references. If found, replace with `.claude/outputs/` or another Windows-safe path. Note: the `/tmp/` path may be in the implement SKILL file (`.claude/skills/implement/skill.md`) rather than the agent definition — that's covered in Phase 11.1.

### Sub-phase 4.2: Fix debug-research-agent.md

**Files:**
- Modify: `.claude/agents/debug-research-agent.md`

**Agent**: general-purpose

#### Step 4.2.1: Remove MCP tool references from frontmatter

Read `.claude/agents/debug-research-agent.md`. Remove any `mcp__jcodemunch__*` tools from the frontmatter `allowed_tools` or similar sections. Subagents cannot use MCP tools — these would cause runtime errors.

### Sub-phase 4.3: Fix auth-agent.md

**Files:**
- Modify: `.claude/agents/auth-agent.md`

**Agent**: general-purpose

#### Step 4.3.1: Add missing auth screens

Read `.claude/agents/auth-agent.md`. Ensure all 10 auth screens are listed in the agent's knowledge base or file references:
- OtpVerificationScreen
- UpdatePasswordScreen
- ProfileSetupScreen
- CompanySetupScreen
- PendingApprovalScreen
- AccountStatusScreen
- UpdateRequiredScreen
(LoginScreen, RegisterScreen, ForgotPasswordScreen should already be present)

#### Step 4.3.2: Add auth DI reference

Add `di/auth_providers.dart` to the agent's file references if not already present.

### Sub-phase 4.4: Fix backend-data-layer-agent.md

**Files:**
- Modify: `.claude/agents/backend-data-layer-agent.md`

**Agent**: general-purpose

#### Step 4.4.1: Remove phantom seed file references

Remove all references to `seed_data_service.dart` and `seed_data_loader.dart`.

#### Step 4.4.2: Fix sync_queue to change_log

Replace all `sync_queue` references with `change_log`.

#### Step 4.4.3: Update DI location note

If the file says DI is in `main.dart`, update to say DI is now in feature-specific `di/` directories (e.g., `lib/features/entries/di/entries_providers.dart`).

#### Step 4.4.4: Add missing schema tables

Update any schema table list to include the full set. List `lib/core/database/schema/` to get the ground truth.

### Sub-phase 4.5: Fix backend-supabase-agent.md

**Files:**
- Modify: `.claude/agents/backend-supabase-agent.md`

**Agent**: general-purpose

#### Step 4.5.1: Remove phantom RLS SQL reference

Remove any reference to `supabase_schema_v4_rls.sql`. This file does not exist.

#### Step 4.5.2: Update schema table list

Update the schema table list count from 13 to 20+ tables. Reference the actual Supabase migration files in `supabase/migrations/` for the ground truth list.

#### Step 4.5.3: Fix entry_personnel reference

Replace `entry_personnel` with `entry_personnel_counts` wherever it appears as a table name reference.

### Sub-phase 4.6: Fix code-review-agent.md

**Files:**
- Modify: `.claude/agents/code-review-agent.md`

**Agent**: general-purpose

#### Step 4.6.1: Update clean architecture statement

Replace any statement like "only sync uses clean architecture" with the correct statement: "most features now use clean architecture with domain/usecases and di/ layers" (post-S676).

### Sub-phase 4.7: Fix frontend-flutter-specialist-agent.md

**Files:**
- Modify: `.claude/agents/frontend-flutter-specialist-agent.md`

**Agent**: general-purpose

#### Step 4.7.1: Verify widget catalog

Read the file. Verify that the widget catalog references are accurate against the actual `lib/` structure. Update any stale widget references.

### Sub-phase 4.8: Fix pdf-agent.md

**Files:**
- Modify: `.claude/agents/pdf-agent.md`

**Agent**: general-purpose

#### Step 4.8.1: Remove phantom structure_preserver.dart reference

Remove any reference to `structure_preserver.dart`. This file does not exist.

#### Step 4.8.2: Fix logging references

Replace any `[PDF]` debug print logging references with `Logger.pdf()` — the new logging system from S582.

### Sub-phase 4.9: Fix qa-testing-agent.md

**Files:**
- Modify: `.claude/agents/qa-testing-agent.md`

**Agent**: general-purpose

#### Step 4.9.1: Update testing keys count

Update the testing keys count from 13 to 16 (or whatever the actual count is). Verify by listing `lib/**/testing_keys*.dart` or similar pattern.

#### Step 4.9.2: Add missing testing key files

Add references to these testing key files if not already present:
- `consent_keys.dart`
- `documents_keys.dart`
- `support_keys.dart`

### Sub-phase 4.10: Fix security-agent.md

**Files:**
- Modify: `.claude/agents/security-agent.md`

**Agent**: general-purpose

#### Step 4.10.1: Fix sync_queue to change_log

Replace all `sync_queue` references with `change_log`.

#### Step 4.10.2: Fix pdf_data_builder.dart glob path

Replace any glob pattern reference to `pdf_data_builder.dart` with the exact path: `lib/features/entries/presentation/controllers/pdf_data_builder.dart`.

### Sub-phase 4.11: Fix agent memory files

**Files:**
- Modify: `.claude/agents/backend-data-layer-agent.memory.md`
- Modify: Other agent memory files as needed (read first to check)

**Agent**: general-purpose

#### Step 4.11.1: Fix backend-data-layer-agent.memory.md

Read `.claude/agents/backend-data-layer-agent.memory.md`. Fix:
- DB version references (should be 46)
- Remove phantom `seed_data_service.dart` and `seed_data_loader.dart` references

#### Step 4.11.2: Check other agent memory files

Read any other `*.memory.md` files in `.claude/agents/`. Apply surgical fixes for any stale references found.

### Sub-phase 4.12: Fix agent-memory MEMORY.md files

**Files:**
- Modify: `.claude/agent-memory/code-review-agent/MEMORY.md`
- Modify: `.claude/agent-memory/pdf-agent/MEMORY.md`
- Modify: `.claude/agent-memory/security-agent/MEMORY.md`

**Agent**: general-purpose

#### Step 4.12.1: Fix code-review-agent memory

Read `.claude/agent-memory/code-review-agent/MEMORY.md`. Fix:
- `main.dart` line count reference (should match actual)
- Remove phantom `row_classifier_v2.dart` reference

#### Step 4.12.2: Fix pdf-agent memory

Read `.claude/agent-memory/pdf-agent/MEMORY.md`. Remove these 6 phantom references:
- `structure_preserver.dart`
- `deprecated/` directory
- 4 test files that don't exist (read the file to identify the specific phantom test file paths)

#### Step 4.12.3: Fix security-agent memory

Read `.claude/agent-memory/security-agent/MEMORY.md`. Mark these 3 resolved findings as RESOLVED:
- `flutter_secure_storage` is now used (implemented in S677)
- `PRAGMA foreign_keys` is now enabled
- Stale line number references (these are no longer relevant post-refactor)

---

## Verification Step

After all phases complete, run grep checks across `.claude/` for these phantom references that should no longer appear in active (non-archived) files:

1. `seed_data_service` — should be gone from rules, agents, memory
2. `seed_data_loader` — should be gone from rules, agents, memory
3. `sync_queue` — should be gone from rules and agents (may remain in historical/archived files)
4. `SyncAdapter` — as standalone reference, not as part of "TableAdapter" (should be gone from rules/agents)
5. `SupabaseSyncAdapter` — should be completely gone
6. `AppTheme.primaryBlue` — should be gone from rules
7. `project_selection_screen.dart` — should be gone from sync-related files
8. `sync_status_banner` — should be completely gone
9. `PdfImportProgressManager` — should be completely gone

**Exclusions:** archived files in `.claude/logs/`, `.claude/specs/archived/`, and git history are expected to contain stale references and should NOT be modified.

If any phantom references are found in active files, fix them before marking the plan complete.
