# Claude Directory Audit & Update Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Fix every live-context file in `.claude/` so agents get accurate codebase context post-S678. ~80 files across 12 phases + verification.
**Spec:** `.claude/specs/2026-03-30-claude-directory-audit-update-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-30-claude-directory-audit-update/analysis.md`

**Architecture:** Documentation-only plan — no app code changes. All files in `.claude/`. Tier-based execution: foundation → rules → agents → docs → PRDs → constraints → state/defects → skills → guides.
**Tech Stack:** Markdown, JSON (state files). All agents are `general-purpose`.
**Blast Radius:** ~80 direct, 0 dependent, 0 tests, 1 cleanup (DELETE pagination guide)

**Reviews:**
- Code review: APPROVE (2 CRITICAL fixed — constraint paths corrected)
- Security review: APPROVE (1 HIGH fixed, 4 MEDIUM addressed inline)
- Completeness review: 80/82 COVERED, 2 PARTIAL fixed in concatenation

---

## Master Dispatch Groups

| Group | Phases | Parallelism | Notes |
|-------|--------|-------------|-------|
| **1** | Phase 1 | Sequential | Foundation — must complete before all others |
| **2** | Phases 2 + 3 | Parallel (2 + 5 sub-phases) | Rules — no interdependencies between sub-phases |
| **3** | Phase 4 | Parallel (12 sub-phases) | Agent defs + memory — depends on rules being done |
| **4** | Phases 5.1–5.6 | 6 parallel | Priority architecture doc rewrites |
| **5** | Phases 5.7–5.13 | 7 parallel | Remaining architecture doc rewrites |
| **6** | Phases 6.1–6.13 | Batch 3-4 at a time | Overview doc updates |
| **7** | Phases 7.1–7.4 | 4 parallel | New feature doc creation |
| **8** | Phases 8.1–8.8 | All parallel | PRD updates |
| **9** | Phases 9.1–9.10 | All parallel | Constraint updates |
| **10** | Phases 10–11 | All parallel | State/defects + skills |
| **11** | Phase 12 | All parallel | Guides/index |
| **Final** | Phase 13 | Sequential | Phantom reference verification |

---

<!-- ============================================================ -->
<!-- PART 1: FOUNDATION, RULES, AGENTS (Phases 1-4)               -->
<!-- ============================================================ -->

## Phase 1: CLAUDE.md + State Files

### Sub-phase 1.1: Update CLAUDE.md

**Files:**
- Modify: `.claude/CLAUDE.md`

**Agent**: general-purpose

#### Step 1.1.1: Fix skill count in Pointers table

Read `.claude/CLAUDE.md`. In the Pointers table, the row for Skills says "10 definitions" — update to 11 (actual count of skill directories). Verify agent count is still 10.

#### Step 1.1.2: Update Data Flow diagram

Replace:
```
Screen -> Provider -> Repository -> SQLite (local) -> Supabase (sync)
```
with:
```
Screen -> Provider -> UseCase -> Repository -> SQLite (local) -> Supabase (sync)
```

#### Step 1.1.3: Verify all pointer paths

For each path in the Pointers table, verify the file/directory exists. Fix any broken paths.

### Sub-phase 1.2: Rewrite FEATURE-MATRIX.json

**Files:**
- Modify: `.claude/state/FEATURE-MATRIX.json`

**Agent**: general-purpose

#### Step 1.2.1: Add missing feature entries

Add entries for calculator, forms, gallery, todos following existing schema. Set appropriate dependencies:
- calculator: depends_on toolbox, required_by []
- forms: depends_on entries/projects/pdf, required_by entries/toolbox
- gallery: depends_on photos, required_by toolbox
- todos: depends_on [], required_by toolbox

#### Step 1.2.2: Fix total_features and generated_at

Set `total_features: 17`, `generated_at: "2026-03-30"`.

### Sub-phase 1.3: Update PROJECT-STATE.json

**Files:**
- Modify: `.claude/state/PROJECT-STATE.json`

**Agent**: general-purpose

#### Step 1.3.1: Fix version and phase fields

Fix `app_version` to `"0.1.0"`. Update `next_release_target` to `"TBD"`. Update `current_phase` to reflect S676+S677 IMPLEMENTED. Update `session_notes` to reference S678.

### Sub-phase 1.4: Update AGENT-FEATURE-MAPPING.json

**Files:**
- Modify: `.claude/state/AGENT-FEATURE-MAPPING.json`

**Agent**: general-purpose

#### Step 1.4.1: Add 4 missing features and update agent arrays

Add calculator, forms, gallery, todos to features array with appropriate agent assignments. Update agent primary_features/supporting_features arrays to include new features.

### Sub-phase 1.5: Update AGENT-CHECKLIST.json

**Files:**
- Modify: `.claude/state/AGENT-CHECKLIST.json`

**Agent**: general-purpose

#### Step 1.5.1: Read and update if stale

Check for outdated information. Update any stale entries.

### Sub-phase 1.6: Update directory-reference.md

**Files:**
- Modify: `.claude/docs/directory-reference.md`

**Agent**: general-purpose

#### Step 1.6.1: Add missing subdirectories and clarify sub-features

Add context-bundles/, spikes/, projects/, settings.local.json. Clarify calculator/forms/gallery/todos are full features, not just "sub-features of toolbox."

---

## Phase 2: Architecture + Data Layer Rules

### Sub-phase 2.1: Rewrite architecture.md

**Files:**
- Modify: `.claude/rules/architecture.md`

**Agent**: general-purpose

#### Step 2.1.1: Rewrite for clean architecture norm

Read file. Replace "only sync uses clean architecture" with: clean architecture is now the norm. Standard feature structure: `data/`, `domain/`, `presentation/`, `di/`. Remove phantom `syncStatus` field. Replace all `AppTheme.*` with `FieldGuideColors.of(context).*`. Fix stale line numbers (database_service is 1900+ lines at v46). Update feature count to 17. Update anti-pattern table.

### Sub-phase 2.2: Rewrite data-layer.md

**Files:**
- Modify: `.claude/rules/backend/data-layer.md`

**Agent**: general-purpose

#### Step 2.2.1: Rewrite for current state

Read file. Fix DB version to 46. List all schema files from `lib/core/database/schema/` (verify by glob). Fix feature count to 17. Remove phantom seed_data_service.dart/seed_data_loader.dart. Add domain/di layers to feature template. Remove SyncStatus enum. Document shared base classes at correct paths.

---

## Phase 3: Feature-Specific Rules

### Sub-phase 3.1: Rewrite sync-patterns.md

**Files:**
- Modify: `.claude/rules/sync/sync-patterns.md`

**Agent**: general-purpose

#### Step 3.1.1: Full rewrite

Replace phantom SyncAdapter/SupabaseSyncAdapter with TableAdapter + 20+ concrete adapters. Replace sync_queue with change_log trigger system. Document engine (SyncEngine, ChangeTracker, ConflictResolver, IntegrityChecker, SyncMutex, SyncRegistry, OrphanScanner, StorageCleanup, ScopeType), application layer (SyncOrchestrator, SyncLifecycleManager, BackgroundSyncHandler, FcmHandler), config (SyncConfig), domain (SyncTypes), DI (sync_providers.dart). Fix screens: SyncDashboardScreen + ConflictViewerScreen (NOT project_selection_screen). Fix widgets: SyncStatusIcon + DeletionNotificationBanner (NOT sync_status_banner).

### Sub-phase 3.2: Update supabase-auth.md

**Files:**
- Modify: `.claude/rules/auth/supabase-auth.md`

**Agent**: general-purpose

#### Step 3.2.1: Fix syntax and add flows

Fix Riverpod ref.read() → Provider context.read(). Add consent gate, multi-tenant company flow, OTP verification. Verify deep link scheme is `com.fieldguideapp.inspector`. Document all 10 auth screens.

### Sub-phase 3.3: Update flutter-ui.md

**Files:**
- Modify: `.claude/rules/frontend/flutter-ui.md`

**Agent**: general-purpose

#### Step 3.3.1: Fix deprecated constants and stale references

Replace ALL AppTheme.* with FieldGuideColors.of(context).* / Theme.of(context).colorScheme.*. Remove Stepper claim on EntryEditorScreen. Remove _buildStatCard. Fix line references by reading actual files.

### Sub-phase 3.4: Update schema-patterns.md

**Files:**
- Modify: `.claude/rules/database/schema-patterns.md`

**Agent**: general-purpose

#### Step 3.4.1: Fix version and remove phantoms

Fix version to 46. Remove seed file references. Update migration example.

### Sub-phase 3.5: Update pdf-generation.md

**Files:**
- Modify: `.claude/rules/pdf/pdf-generation.md`

**Agent**: general-purpose

#### Step 3.5.1: Fix paths and class names

Fix data/services/ → services/. Fix OcrConfigV2 → TesseractConfigV2. Add MpExtractionService. Remove PdfImportProgressManager.

---

## Phase 4: Agent Definitions + Memory

### Sub-phase 4.1–4.10: Fix all 10 agent definitions

**Agent**: general-purpose

Key fixes per agent (read each file, apply changes):
- **implement-orchestrator.md**: /tmp/ → .claude/outputs/
- **debug-research-agent.md**: Remove mcp__jcodemunch__* from frontmatter
- **auth-agent.md**: Add 7 missing screens, add di/auth_providers.dart
- **backend-data-layer-agent.md**: Remove seed phantoms, fix sync_queue→change_log, update DI location, add schema tables
- **backend-supabase-agent.md**: Remove supabase_schema_v4_rls.sql, update table list 13→20+, fix entry_personnel→entry_personnel_counts
- **code-review-agent.md**: Fix "only sync uses clean architecture" → most features do
- **frontend-flutter-specialist-agent.md**: Verify widget catalog
- **pdf-agent.md**: Remove structure_preserver.dart, fix [PDF]→Logger.pdf()
- **qa-testing-agent.md**: Fix keys count 13→16, add consent_keys/documents_keys/support_keys
- **security-agent.md**: Fix sync_queue→change_log, fix pdf_data_builder glob, update RLS table list to include all syncable tables

### Sub-phase 4.11: Fix agent .memory.md files

Fix backend-data-layer-agent.memory.md (DB version, remove seeds). Check other .memory.md files.

### Sub-phase 4.12: Fix agent-memory MEMORY.md files

Fix code-review-agent (main.dart line count, remove row_classifier_v2), pdf-agent (remove 6 phantoms), security-agent (mark 3 resolved). **Also read and verify the remaining 5 agent-memory MEMORY.md files** (auth-agent, backend-data-layer-agent, backend-supabase-agent, frontend-flutter-specialist-agent, qa-testing-agent) — apply surgical fixes for any phantom references found.

---

<!-- ============================================================ -->
<!-- PART 2: FEATURE DOCUMENTATION (Phases 5-7)                    -->
<!-- ============================================================ -->

## Phase 5: Feature Architecture Docs — REWRITE (13 existing)

REWRITE all 13 architecture docs with ground truth. Each must include: accurate layer structure (data/domain/presentation/di), key class names, DI wiring, patterns, relationships. Frontmatter updated: 2026-03-30.

### Sub-phases 5.1–5.13

One sub-phase per feature: auth, settings, projects, entries, sync, toolbox, contractors, dashboard, locations, pdf, photos, quantities, weather.

Each step: Read current file + scan lib/features/{name}/ for ground truth → rewrite with accurate content.

See Part 2 plan file (`.claude/plans/2026-03-30-claude-directory-audit-update-part2-feature-docs.md`) for detailed per-feature instructions with full class lists.

---

## Phase 6: Feature Overview Docs — UPDATE (13 existing)

UPDATE all 13 overview docs. Fix Key Files tables, purpose/scope, screen lists, provider lists, relationships. Frontmatter updated: 2026-03-30.

### Sub-phases 6.1–6.13

One sub-phase per feature. See Part 2 plan file for detailed per-feature instructions.

---

## Phase 7: Feature Docs — CREATE (4 missing features)

CREATE 8 new files: forms, calculator, gallery, todos (overview + architecture each).

### Sub-phases 7.1–7.4

One sub-phase per feature. See Part 2 plan file for detailed content specifications per feature.

---

<!-- ============================================================ -->
<!-- PART 3: PRDs, CONSTRAINTS, SKILLS, GUIDES (Phases 8-12)       -->
<!-- ============================================================ -->

## Phase 8: PRDs

### Sub-phases 8.1–8.8

- 8.1: CREATE forms-prd.md (registry system, lifecycle, models, MDOT specifics)
- 8.2: REWRITE sync-prd.md (change_log/TableAdapter engine)
- 8.3: UPDATE settings-prd.md (consent/support/legal/OSS/admin/trash)
- 8.4: UPDATE auth-prd.md (navigation, SQLite tables, OTP, consent gate)
- 8.5: UPDATE entries-prd.md (2-state, weather enum, multi-tenant)
- 8.6: UPDATE projects-prd.md (assignments, multi-tenant, MDOT placeholder)
- 8.7: UPDATE photos-prd.md (path fix, soft-delete, nullable)
- 8.8: UPDATE remaining 7 PRDs (batch)

See Part 3 plan file for detailed per-PRD instructions.

---

## Phase 9: Architecture Decisions / Constraints

### Sub-phases 9.1–9.10

All constraint files use path `.claude/architecture-decisions/`.

- 9.1: REWRITE sync-constraints (trigger-based, per-adapter, + company_id security rule)
- 9.2: REWRITE settings-constraints (full scope)
- 9.3: REWRITE toolbox-constraints (registry model)
- 9.4: UPDATE entries-constraints (2-state, FK, syncStatus, exports)
- 9.5: UPDATE contractors-constraints (model fields, soft-delete)
- 9.6: UPDATE locations/photos/projects constraints (batch)
- 9.7: UPDATE quantities/weather/pdf/dashboard constraints (batch)
- 9.8: UPDATE auth-constraints (consent gate, multi-tenant + security rules) + data-validation-rules
- 9.9: CREATE forms-constraints
- 9.10: CREATE consent-telemetry-constraints (+ PII scrubbing, breadcrumbs, log upload, integrity, retention)

See Part 3 plan file for detailed per-constraint instructions.

---

## Phase 10: State + Defect Files

### Sub-phase 10.1: CREATE 4 feature state files
feature-forms.json, feature-calculator.json, feature-gallery.json, feature-todos.json

### Sub-phase 10.2: UPDATE 6 defect files
Fix stale paths (photos, toolbox), mark resolved defects (database, forms BUG-S04, sync-verification BUG-SV-6, settings BUG-S09-1).

---

## Phase 11: Skills

### Sub-phases 11.1–11.5
- 11.1: Fix implement skill /tmp/ path
- 11.2: Fix audit-config agent count
- 11.3: Fix test skill keys count
- 11.4: CREATE design-system.md reference
- 11.5: Verify codebase-tracing-paths

---

## Phase 12: Guides + Test Flows + Index

### Sub-phases 12.1–12.5
- 12.1: DELETE pagination-widgets-guide.md
- 12.2: Fix e2e-test-setup package name
- 12.3: Add 5 test suites to manual-testing-checklist
- 12.4: Update INDEX.md
- 12.5: Fix test-flows + guides README

---

## Phase 13: Final Verification

### Sub-phase 13.1: Phantom Reference Grep

Grep `.claude/` (excluding .git/, plans/completed/, specs/archived/, code-reviews/, adversarial_reviews/, debug-sessions/, logs/) for:

1. `SyncAdapter` (standalone)
2. `SupabaseSyncAdapter`
3. `sync_queue`
4. `AppTheme.primaryBlue` (and .success, .warning, .error, .textPrimary, .textSecondary)
5. `seed_data_service`
6. `seed_data_loader`
7. `PdfImportProgressManager`
8. `PdfImportProgressDialog`
9. `form_fill_screen`
10. `project_selection_screen.dart` (sync context)
11. `sync_status_banner`
12. `photo_service_impl`
13. `_buildStatCard`

Fix any remaining hits inline.

---

## Detail Plan Files

For step-by-step instructions with full class lists and ground truth data per feature:
- **Part 1** (Phases 1-4): `.claude/plans/2026-03-30-claude-directory-audit-update-part1-foundation-rules-agents.md`
- **Part 2** (Phases 5-7): `.claude/plans/2026-03-30-claude-directory-audit-update-part2-feature-docs.md`
- **Part 3** (Phases 8-12): `.claude/plans/2026-03-30-claude-directory-audit-update-part3-prds-constraints-skills.md`
