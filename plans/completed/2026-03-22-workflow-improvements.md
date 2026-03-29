# Workflow Improvements Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Bundle all workflow insights findings into a single improvement effort covering config remediation, constraint reconciliation, code fixes, skill updates, automated enforcement, and agent memory population.
**Spec:** `.claude/specs/2026-03-22-workflow-improvements-spec.md`

**Architecture:** Mechanical config edits across `.claude/` files, followed by targeted Dart code fixes (raw SQL migration, anti-pattern remediation), skill file updates, pre-commit hook creation, and agent memory population. No new features — purely hygiene and process improvement.
**Tech Stack:** Dart/Flutter, PowerShell (hooks), Markdown (config/skills/docs)
**Blast Radius:** ~30 config files, 6 Dart source files (V5 fix), 8 PDF model files (firstWhere), ~25 Dart files (catch fixes), 3 skill files, 1 hook script, 3 agent memory files

---

## Phase 1: Config Remediation

### Sub-phase 1.0: .gitignore Fixes (P0)

**Files:**
- Modify: `.claude/.gitignore`

**Agent:** `general-purpose`

#### Step 1.0.1: Add test_results/ pattern
Add `test_results/` (with underscore) to `.claude/.gitignore`. The existing `test-results/` (with hyphen) does not match the actual directory name.
<!-- WHY: 17MB of binary test artifacts are not being ignored due to hyphen/underscore mismatch -->

#### Step 1.0.2: Add state file patterns
Add these patterns to `.claude/.gitignore` to stop commit noise (79% of .claude commits are state file updates):
```
autoload/_state.md
state/*.json
```

### Sub-phase 1.1: Feature/Agent Count Corrections

**Files:**
- Modify: `.claude/docs/INDEX.md:14,111`
- Modify: `.claude/docs/guides/README.md:49`
- Modify: `.claude/docs/features/README.md:3`
- Modify: `.claude/state/AGENT-FEATURE-MAPPING.json:234`
- Modify: `.claude/docs/directory-reference.md:9`
- Modify: `.claude/CLAUDE.md` (Pointers table)

**Agent:** `general-purpose`

#### Step 1.1.1: Update "13 features" to "17 features"
Find and replace "13 features" with "17 features" in:
- `.claude/docs/INDEX.md` at lines 14 and 111
- `.claude/docs/guides/README.md` at line 49
- `.claude/docs/features/README.md` at line 3
- `.claude/state/AGENT-FEATURE-MAPPING.json` at line 234

#### Step 1.1.2: Update "9 agents" to "10 agents"
Find and replace in:
- `.claude/docs/directory-reference.md` at line 9
- `.claude/CLAUDE.md` Pointers table: change `Agents (9 definitions)` to `Agents (10 definitions)`

### Sub-phase 1.2: debugPrint to Logger in Rules

**Files:**
- Modify: `.claude/rules/pdf/pdf-generation.md:180,201,206`
- Modify: `.claude/rules/database/schema-patterns.md:201,205,211`
- Modify: `.claude/rules/frontend/flutter-ui.md:107`
- Modify: `.claude/rules/auth/supabase-auth.md:152,159,161`
- Modify: `.claude/rules/backend/data-layer.md:250`

**Agent:** `general-purpose`

#### Step 1.2.1: Update pdf-generation.md
Replace all `debugPrint` references with `Logger.pdf()` at lines 180, 201, 206.

#### Step 1.2.2: Update schema-patterns.md
Replace all `debugPrint` references with `Logger.db()` at lines 201, 205, 211.

#### Step 1.2.3: Update flutter-ui.md
Replace `debugPrint` reference with `Logger.ui()` at line 107.

#### Step 1.2.4: Update supabase-auth.md
Replace all `debugPrint` references with `Logger.auth()` at lines 152, 159, 161.

#### Step 1.2.5: Update data-layer.md
Replace `debugPrint` reference with `Logger.db()` at line 250.

### Sub-phase 1.2b: Bare supabase to npx supabase in Agent

**Files:**
- Modify: `.claude/agents/backend-supabase-agent.md`

**Agent:** `general-purpose`

#### Step 1.2b.1: Update bare supabase commands
Find all bare `supabase` commands in `.claude/agents/backend-supabase-agent.md` and replace with `npx supabase`. Grep for `supabase` and verify each instance uses the `npx` prefix.

### Sub-phase 1.3: Bare Flutter to pwsh -Command in Rules

**Files:**
- Modify: `.claude/rules/frontend/flutter-ui.md:12-15`
- Modify: `.claude/rules/backend/data-layer.md:12-14`
- Modify: `.claude/rules/platform-standards.md:194,231,236`

**Agent:** `general-purpose`

#### Step 1.3.1: Update flutter-ui.md
Replace bare `flutter` commands at lines 12-15 with `pwsh -Command "flutter ..."` equivalents.

#### Step 1.3.2: Update data-layer.md
Replace bare `flutter` commands at lines 12-14 with `pwsh -Command "flutter ..."` equivalents.

#### Step 1.3.3: Update platform-standards.md
Replace bare `flutter` commands at lines 194, 231, 236 with `pwsh -Command "flutter ..."` equivalents.

### Sub-phase 1.3b: BRANCH Annotations in sync-patterns.md (P2 — Deferred)

**Files:**
- Modify: `.claude/rules/sync/sync-patterns.md:8,68,109,147,204`

**Agent:** `general-purpose`

#### Step 1.3b.1: Note BRANCH annotations for post-merge cleanup
The 5 `[BRANCH: feat/sync-engine-rewrite]` annotations in section headings should be stripped AFTER the branch merges to main. Since we are currently ON that branch, do NOT remove them yet.

**Action for now:** Add a comment at the top of the file:
```markdown
<!-- TODO: Remove [BRANCH: feat/sync-engine-rewrite] annotations from 5 section headings after branch merges to main -->
```

### Sub-phase 1.4: Haiku to Sonnet in Orchestrator

**Files:**
- Modify: `.claude/agents/implement-orchestrator.md:89`

**Agent:** `general-purpose`

#### Step 1.4.1: Update model reference
Change `haiku` to `sonnet` at line 89 of `.claude/agents/implement-orchestrator.md`.
<!-- WHY: User preference — all agent models should be sonnet minimum -->

### Sub-phase 1.5: Stale Defect Resolution

**Files:**
- Modify: `.claude/defects/_defects-auth.md:35-38`
- Modify: `.claude/defects/_defects-projects.md:49-53`
- Modify: `lib/features/projects/data/datasources/local/project_local_datasource.dart:112`
- Modify: `lib/features/projects/data/repositories/project_repository.dart:152`

**Agent:** `general-purpose`

#### Step 1.5.1: Mark secure_password_change defect as RESOLVED
In `.claude/defects/_defects-auth.md` at lines 35-38, mark the secure_password_change defect as `RESOLVED` with a note that it has been fixed.

#### Step 1.5.2: Mark PRAGMA foreign_keys defect as RESOLVED
In `.claude/defects/_defects-projects.md` at lines 49-53, mark the PRAGMA foreign_keys defect as `RESOLVED` with a note that it has been fixed.

#### Step 1.5.3: Update stale PRAGMA comments in Dart code
Update the stale comments to reflect that PRAGMA foreign_keys IS now enabled (at `database_service.dart:61,83`):

- `lib/features/projects/data/datasources/local/project_local_datasource.dart:112` — Change "PRAGMA foreign_keys is never enabled in this codebase, so CASCADE deletes will not fire" to "PRAGMA foreign_keys is enabled (database_service.dart:61), so CASCADE deletes will fire"
- `lib/features/projects/data/repositories/project_repository.dart:152` — Same update: change "Since PRAGMA foreign_keys is never enabled, CASCADE won't fire" to "Since PRAGMA foreign_keys is enabled (database_service.dart:61), CASCADE will fire for child records"

**NOTE:** These are sentences within larger doc comments. Update only the stale sentences, do NOT delete the entire doc block.

---

## Phase 2: Constraint Reconciliation

### Sub-phase 2.1: V1 — Sync Retry Count

**Files:**
- Modify: `.claude/architecture-decisions/sync-constraints.md:8`

**Agent:** `general-purpose`

#### Step 2.1.1: Verify actual retry count in code
Search for retry logic in `lib/features/sync/` to confirm whether the code uses 3 or 5 retries. Use Grep to find the constant.

#### Step 2.1.2: Update constraint doc
In `.claude/architecture-decisions/sync-constraints.md` at line 8, change "max 3 attempts" to "max 5 attempts" (assuming code confirms 5).
<!-- WHY: Code is likely right, docs are stale. Verified in step 2.1.1. -->

### Sub-phase 2.2: V2 — Toolbox Persistence

**Files:**
- Modify: `.claude/architecture-decisions/toolbox-constraints.md:34-37`

**Agent:** `general-purpose`

#### Step 2.2.1: Rewrite persistence section
Rewrite the toolbox persistence section (lines 34-37) to reflect that the toolbox has evolved past the original "ephemeral" constraint. It now has 4 tables with CRUD and sync operations. Document the current reality:

```markdown
### Persistence
The toolbox features (calculator, forms, gallery, todos) use persistent SQLite storage
with full CRUD operations and cloud sync support. Each sub-feature has its own table(s)
managed through the standard repository/datasource pattern.
```
<!-- WHY: Toolbox evolved past original "ephemeral" constraint. 4 tables with CRUD+sync. -->

### Sub-phase 2.3: V3 — SHA256 to Hash-Based Detection

**Files:**
- Modify: `.claude/architecture-decisions/sync-constraints.md:6`

**Agent:** `general-purpose`

#### Step 2.3.1: Update hash algorithm reference
In `.claude/architecture-decisions/sync-constraints.md` at line 6, change "SHA256" to "hash-based change detection" (or similar neutral phrasing that covers djb2).
<!-- WHY: djb2 sufficient for change detection. HTTPS handles transport integrity. -->

### Sub-phase 2.4: V4 — Entry State Reversal

**Files:**
- Modify: `.claude/architecture-decisions/entries-constraints.md:20-21`

**Agent:** `general-purpose`

#### Step 2.4.1: Allow SUBMITTED to DRAFT transition
Update lines 20-21 to document that `undoSubmission()` (SUBMITTED -> DRAFT) is an intentional, allowed state transition.
<!-- WHY: undoSubmission() is intentional — allows correcting premature submissions. -->

---

## Phase 3: V5 Raw SQL Fix

### Sub-phase 3.1: Add saveDraftSuppressed() to ProjectRepository

**Files:**
- Modify: `lib/features/projects/data/repositories/project_repository.dart`
- Modify: `lib/main.dart` (constructor call site)
- Modify: `lib/core/driver/driver_server.dart` (constructor call site — main_driver equivalent)
- Modify: `lib/test_harness.dart` (constructor call site — harness_providers equivalent)

**Agent:** `backend-data-layer-agent`

#### Step 3.1.1: Add DatabaseService dependency
Add `DatabaseService` as a constructor parameter to `ProjectRepository`. Current constructor is `ProjectRepository(this._localDatasource)` at line 18.

New constructor: `ProjectRepository(this._localDatasource, this._databaseService)`

Add field: `final DatabaseService _databaseService;`

**IMPORTANT: Update ALL constructor call sites:**
- `lib/main.dart` — find `ProjectRepository(` and add the DatabaseService argument
- `lib/core/driver/driver_server.dart` — same
- `lib/test_harness.dart` — same (if it exists as a separate call site)

Use Grep to find all `ProjectRepository(` call sites and update every one. If the constructor change is missed at any site, `flutter analyze` will hard-fail.

#### Step 3.1.2: Add saveDraftSuppressed method
Add a method that wraps the save operation with sync_control suppression:

```dart
/// Saves a project draft while suppressing change_log triggers.
/// WHY: Draft saves should not trigger sync — the project isn't finalized yet.
/// FROM SPEC: V5 constraint violation fix — move raw SQL out of presentation layer.
// TODO: Extract sync_control suppression to a SyncControlService for reuse
// (same pattern exists in soft_delete_service.dart:346-411)
Future<void> saveDraftSuppressed(Project project) async {
  final db = await _databaseService.database;
  await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
  try {
    await save(project);
  } finally {
    await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
  }
}
```

### Sub-phase 3.2: Add discardDraft() to ProjectRepository

**Files:**
- Modify: `lib/features/projects/data/repositories/project_repository.dart`

**Agent:** `backend-data-layer-agent`

#### Step 3.2.1: Add discardDraft method
Add a method that deletes the draft project and all its related data while suppressing sync:

```dart
/// Discards a draft project and all associated data, suppressing change_log triggers.
/// WHY: Discarding a draft should not sync deletions — the data was never finalized.
/// FROM SPEC: V5 constraint violation fix — move raw SQL out of presentation layer.
Future<void> discardDraft(String projectId) async {
  final db = await _databaseService.database;
  await db.execute("UPDATE sync_control SET value = '1' WHERE key = 'pulling'");
  try {
    for (final table in ['bid_items', 'contractors', 'locations', 'personnel_types']) {
      await db.delete(table, where: 'project_id = ?', whereArgs: [projectId]);
    }
    await db.delete('projects', where: 'id = ?', whereArgs: [projectId]);
    await db.delete('change_log',
        where: "table_name = 'projects' AND record_id = ?",
        whereArgs: [projectId]);
  } finally {
    await db.execute("UPDATE sync_control SET value = '0' WHERE key = 'pulling'");
  }
}
```

### Sub-phase 3.3: Refactor project_setup_screen.dart

**Files:**
- Modify: `lib/features/projects/presentation/screens/project_setup_screen.dart:118-127,355-378`

**Agent:** `frontend-flutter-specialist-agent`

#### Step 3.3.1: Refactor _initEagerDraft()
Replace lines 118-127. The screen already accesses the repository via `projectProvider.repository` (see existing line 124: `projectProvider.repository.save(project)`). Call the new method directly:

```dart
// FROM SPEC: V5 fix — raw SQL moved to repository layer
// NOTE: Screen already uses projectProvider.repository.save() — no proxy needed (KISS)
await projectProvider.repository.saveDraftSuppressed(project);
```

Remove the `final db = await context.read<DatabaseService>().database;` line and all raw SQL.

#### Step 3.3.2: Refactor _discardDraft()
Replace lines 355-378 with:

```dart
// FROM SPEC: V5 fix — raw SQL moved to repository layer
await projectProvider.repository.discardDraft(_projectId!);
```

Remove the `final db = await context.read<DatabaseService>().database;` line and all raw SQL.

### Sub-phase 3.4: Verification

**Agent:** `general-purpose`

#### Step 3.4.1: Run flutter analyze
```
pwsh -Command "flutter analyze"
```
Verify no analysis errors in the modified files (project_setup_screen.dart, project_repository.dart, main.dart, etc).

---

## Phase 4: Anti-Pattern Fixes

### Sub-phase 4.1: Fix 8 Unsafe .firstWhere in PDF Extraction Models

**Files:**
- Modify: `lib/features/pdf/services/extraction/models/classified_rows.dart:71,148,314`
- Modify: `lib/features/pdf/services/extraction/models/document_checksum.dart:165`
- Modify: `lib/features/pdf/services/extraction/models/ocr_element.dart:74`
- Modify: `lib/features/pdf/services/extraction/models/processed_items.dart:78`
- Modify: `lib/features/pdf/services/extraction/models/quality_report.dart:103,110`

**Agent:** `pdf-agent`

#### Step 4.1.1: Fix classified_rows.dart (3 instances)
Replace each `.firstWhere((e) => e.name == map['key'])` with the safe pattern:

```dart
// BEFORE:
type: RowType.values.firstWhere((e) => e.name == map['type'])

// AFTER:
// NOTE: Safe enum deserialization — defaults to fallback if map value is unrecognized
type: RowType.values.where((e) => e.name == map['type']).firstOrNull ?? RowType.data,
```

Apply at lines 71, 148, and 314. Use the appropriate enum type and default value for each instance.

#### Step 4.1.2: Fix document_checksum.dart (1 instance)
Apply the same safe pattern at line 165.

#### Step 4.1.3: Fix ocr_element.dart (1 instance)
Apply the same safe pattern at line 74.

#### Step 4.1.4: Fix processed_items.dart (1 instance)
Apply the same safe pattern at line 78.

#### Step 4.1.5: Fix quality_report.dart (2 instances)
Apply the same safe pattern at lines 103 and 110.

### Sub-phase 4.1b: Re-Audit catch(_) Instances Before Fixing

**Files:** Read-only audit across `lib/`

**Agent:** `general-purpose`

#### Step 4.1b.1: Audit current catch(_) and catch(e)-silent instances
**FROM SPEC: "Both counts need re-verification against current code before fixing."**

Use Grep to find ALL `catch (_)` and `catch (e)` instances in `lib/`. For each `catch (e)` block, check if `e` is actually used in the body (passed to Logger, rethrown, or otherwise referenced).

Categorize each instance as:
- **KEEP**: Intentional suppression (logger internals, test driver, ProcessInfo.currentRss, table-may-not-exist guards, sync_mutex lock detection)
- **FIX**: Add `Logger.<category>()` call (auth, entries, sync screens, photo/image, settings/theme)
- **REVIEW**: JSON decode fallbacks in forms models — decide per-instance

Output the categorized list as a comment block in the plan checkpoint or as inline notes for sub-phases 4.2-4.7. This step MUST complete before any fixes begin.

### Sub-phase 4.2: Fix catch(_) in Auth Providers

**Files:**
- Modify: `lib/features/auth/presentation/providers/auth_provider.dart` and related auth files
- **Exact scope determined by Step 4.1b.1 audit**

**Agent:** `general-purpose`

#### Step 4.2.1: Add Logger.auth() to catch blocks
For each `catch (_)` or `catch (e)` block that silently swallows errors, add `Logger.auth()` logging:

```dart
// BEFORE:
} catch (e) {
  _error = 'Something failed';
}

// AFTER:
} catch (e) {
  Logger.auth('Auth operation failed: $e');
  _error = 'Something failed';
}
```

Ensure `Logger` import is present: `import 'package:construction_inspector/core/logging/logger.dart';`

### Sub-phase 4.3: Fix catch(_) in Entry Providers

**Files:**
- Modify: `lib/features/entries/presentation/providers/` (~3 instances)

**Agent:** `general-purpose`

#### Step 4.3.1: Add Logger.ui() or Logger.db() to catch blocks
Same pattern as 4.2.1 but use appropriate Logger category based on context (`.ui()` for presentation logic, `.db()` for data operations).

### Sub-phase 4.4: Fix catch(_) in Sync Screens

**Files:**
- Modify: `lib/features/sync/presentation/` (~3 instances)

**Agent:** `general-purpose`

#### Step 4.4.1: Add Logger.sync() to catch blocks
Same pattern using `Logger.sync()`.

### Sub-phase 4.5: Fix catch(_) in Photo/Image Services

**Files:**
- Modify: `lib/features/photos/data/datasources/` and `lib/services/` (~5 instances)

**Agent:** `general-purpose`

#### Step 4.5.1: Add Logger.photo() to catch blocks
Same pattern using `Logger.photo()`.

### Sub-phase 4.6: Fix catch(_) in Settings/Theme Providers

**Files:**
- Modify: `lib/features/settings/presentation/providers/` (~4 instances)

**Agent:** `general-purpose`

#### Step 4.6.1: Add Logger.ui() to catch blocks
Same pattern using `Logger.ui()`.

### Sub-phase 4.7: Review JSON Decode Catch Blocks in Forms Models

**Files:**
- Review: `lib/features/forms/data/models/` (~10 instances)

**Agent:** `general-purpose`

#### Step 4.7.1: Audit forms model catch blocks
Read each catch block in forms models. These may be intentional schema migration guards where bad/old data should silently fall back to defaults. For each:
- If intentional: add a `// NOTE: Intentional — schema migration fallback` comment
- If not intentional: add appropriate `Logger.db()` call

### Sub-phase 4.8: Update Anti-Pattern Table in architecture.md

**Files:**
- Modify: `.claude/rules/architecture.md:121-131`

**Agent:** `general-purpose`

#### Step 4.8.1: Add 4 new anti-pattern entries
Add these rows to the anti-pattern table after line 131:

| Anti-Pattern | Why It's Bad | Fix |
|---|---|---|
| `catch (_)` without logging | Silently swallows errors, makes debugging impossible | Add `Logger.<category>()` call |
| `debugPrint` in production code | Not captured by logging system, no filtering/routing | Use `Logger.<category>()` |
| Raw SQL in presentation layer | Violates separation of concerns, untestable | Move to repository/datasource layer |
| `db.delete()` without soft-delete check | Bypasses trash/recovery system | Use `SoftDeleteService` or repository delete |

---

## Phase 5: Skill Updates

### Sub-phase 5.1: Update Brainstorming Skill

**Files:**
- Modify: `.claude/skills/brainstorming/skill.md`

**Agent:** `general-purpose`

#### Step 5.1.1: Remove adversarial review section
Remove lines 157-270 (entire Adversarial Review section and Handoff section).

#### Step 5.1.2: Update checklist
Remove steps 6-8 from the checklist (lines 25-35) — these are the adversarial review steps.

#### Step 5.1.3: Update process flow diagram
Remove review steps from the process flow diagram (lines 39-57).

#### Step 5.1.4: Clean up anti-patterns table
Remove the "Skip adversarial review" row from the anti-patterns table.

#### Step 5.1.5: Add terminal state
Add a new terminal state: after spec is written, offer to proceed to writing-plans skill.
<!-- FROM SPEC: Brainstorming captures intent only. No adversarial review. -->

### Sub-phase 5.2: Update Writing-Plans Skill

**Files:**
- Modify: `.claude/skills/writing-plans/skill.md`

**Agent:** `general-purpose`

#### Step 5.2.1: Add Spec as Source of Truth section
Insert after line 9 (before the Architecture section):

```markdown
## Spec as Source of Truth

The spec represents the user's approved intent, scope, and vision. It is the product of collaborative brainstorming and captures decisions the user has explicitly made.

**Reviews verify the plan, not the spec.** Adversarial reviewers should:
- Challenge whether the plan correctly implements the spec's intent
- Find gaps, holes, or better implementation approaches in the plan
- Verify file paths, symbols, and dependencies against actual codebase
- Security reviewer: find security flaws in the planned implementation

**Reviews do NOT:**
- Override the spec's scope or goals
- Reject features the user explicitly approved in the spec
- Add requirements not in the spec
```

### Sub-phase 5.3: Create /spike Skill

**Files:**
- Create: `.claude/skills/spike/skill.md`

**Agent:** `general-purpose`

#### Step 5.3.1: Create spike skill file
Create `.claude/skills/spike/skill.md` with the following content:

```markdown
---
name: spike
description: Time-boxed research and hypothesis testing. No code ships.
skills: frontmatter
---

# /spike — Research & Hypothesis Testing

## Purpose
Investigate a hypothesis or question through targeted codebase exploration, external research, and prototyping. Produces a findings document — never production code.

## Input
- A hypothesis, question, or area of uncertainty
- Optional: time constraint (default: 1-2 sessions max)

## Process

1. **Frame the hypothesis** — What are we trying to learn? What would confirm/deny it?
2. **Research** — Explore codebase, read docs, check dependencies, prototype if needed
3. **Document findings** — Write to `.claude/spikes/YYYY-MM-DD-<topic>.md`
4. **Recommend next step:**
   - **Proceed** — Findings support the hypothesis. Recommend writing a spec.
   - **Park** — Inconclusive. Document what's known, what's missing.
   - **Kill** — Hypothesis disproven or not viable. Document why.

## Output Format

```markdown
# Spike: [Topic]

**Date:** YYYY-MM-DD
**Hypothesis:** [What we're investigating]
**Verdict:** Proceed | Park | Kill

## Findings
[Key discoveries, with evidence]

## Recommendation
[Next steps based on verdict]
```

## Rules
- **No production code ships from a spike.** Prototypes stay in scratch files or get deleted.
- **Time-boxed.** If you haven't found an answer in 2 sessions, write up what you know and Park it.
- **Be honest about uncertainty.** "I don't know" is a valid finding.

## Anti-Patterns
| Anti-Pattern | Why |
|---|---|
| Shipping spike code to production | Spikes are exploratory — not tested, not reviewed |
| Endless research without documenting | Time-box and write up findings |
| Skipping the recommendation | The whole point is to decide: proceed, park, or kill |
```

#### Step 5.3.2: Create spikes directory
Ensure `.claude/spikes/` directory exists (create with a `.gitkeep` if needed).

### Sub-phase 5.4: Document Lightweight Process Path

**Files:**
- Modify: `.claude/CLAUDE.md`

**Agent:** `general-purpose`

#### Step 5.4.1: Add lightweight path to Session & Workflow section
In the Session & Workflow section of `.claude/CLAUDE.md`, add after the existing pipeline line:

```markdown
- **Sizing guide:** XS (single-file mechanical) = no skill needed | S (up to 3 files, known pattern) = skip brainstorming + writing-plans | M+ = full pipeline
```

---

## Phase 6: Automated Enforcement

### Sub-phase 6.1: Create Pre-Commit Hook

**Files:**
- Create: `.claude/hooks/pre-commit.ps1`

**Agent:** `general-purpose`

#### Step 6.1.1: Create pre-commit.ps1
Create `.claude/hooks/pre-commit.ps1` with tiered pattern matching:

```powershell
# Pre-commit hook — tiered enforcement
# Hard block: security anti-patterns (exit 1)
# Warn only: code quality patterns (exit 0 with warning)

param()

# NOTE: @() ensures proper array parsing on Windows (line-ending issues without it)
$stagedFiles = @(git diff --cached --name-only --diff-filter=ACM)

$hardBlockPatterns = @(
    @{
        Pattern = 'db\.execute|db\.rawQuery|db\.rawUpdate|db\.rawDelete|db\.rawInsert'
        PathFilter = 'presentation/'
        Message = 'BLOCKED: Raw SQL found in presentation layer. Move to repository/datasource.'
    },
    @{
        Pattern = '\.env$'
        PathFilter = ''
        Message = 'BLOCKED: .env file staged for commit. Remove from staging.'
    }
)

$warnPatterns = @(
    @{
        Pattern = 'catch\s*\(_\)'
        PathFilter = 'lib/'
        Message = 'WARNING: catch (_) without logging detected. Consider adding Logger call.'
    },
    @{
        Pattern = '\.firstWhere\('
        PathFilter = 'lib/'
        Message = 'WARNING: .firstWhere() without orElse detected. Consider using .firstOrNull.'
    },
    @{
        Pattern = 'debugPrint'
        PathFilter = 'lib/'
        Message = 'WARNING: debugPrint found. Use Logger.<category>() instead.'
    }
)

$blocked = $false
$warned = $false

foreach ($file in $stagedFiles) {
    if (-not (Test-Path $file)) { continue }

    # Check .env files (filename-based check)
    if ($file -match '\.env$') {
        Write-Host "BLOCKED: .env file staged for commit: $file" -ForegroundColor Red
        $blocked = $true
        continue
    }

    # Only check Dart files for code patterns
    if ($file -notmatch '\.dart$') { continue }

    $content = Get-Content $file -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }

    foreach ($pattern in $hardBlockPatterns) {
        if ($pattern.PathFilter -and $file -notmatch $pattern.PathFilter) { continue }
        if ($pattern.Pattern -match '\.env') { continue } # handled above
        if ($content -match $pattern.Pattern) {
            Write-Host "$($pattern.Message) [$file]" -ForegroundColor Red
            $blocked = $true
        }
    }

    foreach ($pattern in $warnPatterns) {
        if ($pattern.PathFilter -and $file -notmatch $pattern.PathFilter) { continue }
        if ($content -match $pattern.Pattern) {
            Write-Host "$($pattern.Message) [$file]" -ForegroundColor Yellow
            $warned = $true
        }
    }
}

if ($blocked) {
    Write-Host "`nCommit blocked. Fix the issues above and try again." -ForegroundColor Red
    exit 1
}

if ($warned) {
    Write-Host "`nWarnings found but commit allowed. Consider fixing the issues above." -ForegroundColor Yellow
}

exit 0
```

### Sub-phase 6.2: Wire Hook into Git Config

**Files:**
- Create: `.githooks/pre-commit` (shell wrapper that calls the PowerShell script)

**Agent:** `general-purpose`

#### Step 6.2.1: Create shell wrapper
Create `.githooks/pre-commit`:

```bash
#!/bin/sh
# Pre-commit hook wrapper — calls PowerShell script for Windows compatibility
pwsh -ExecutionPolicy Bypass -File ".claude/hooks/pre-commit.ps1"
exit $?
```

#### Step 6.2.2: Configure git to use hooks directory
```bash
git config core.hooksPath .githooks
```

#### Step 6.2.3: Make hook executable
```bash
chmod +x .githooks/pre-commit
```

### Sub-phase 6.3: Test Hook

**Agent:** `general-purpose`

#### Step 6.3.1: Test hook against known violations
Create a temporary test file with known violations and verify the hook catches them:
```bash
pwsh -ExecutionPolicy Bypass -File ".claude/hooks/pre-commit.ps1"
```
Verify output shows appropriate blocks/warnings.

---

## Phase 7: Agent Memory Population

**SECURITY NOTE:** Do NOT include actual credential values, `.env` variable names, Supabase project URLs, or API keys in memory files. Document patterns and conventions only.

### Sub-phase 7.1: Populate Backend-Supabase Agent Memory

**Files:**
- Modify: `.claude/agents/backend-supabase-agent.memory.md`

**Agent:** `general-purpose`

#### Step 7.1.1: Research and populate memory
Read the following to extract patterns, then write a comprehensive memory file:
- `lib/features/sync/` — sync patterns, retry logic, conflict resolution
- `supabase/` — migration files, RLS policies
- `.claude/rules/backend/supabase-sql.md` — existing rules
- `.claude/rules/sync/sync-patterns.md` — sync patterns

Key areas to document:
- Supabase CLI usage (`npx supabase` commands)
- RLS policy patterns
- Migration workflow (push/pull/diff)
- Sync engine architecture
- Common gotchas

### Sub-phase 7.2: Populate Auth Agent Memory

**Files:**
- Modify: `.claude/agents/auth-agent.memory.md`

**Agent:** `general-purpose`

#### Step 7.2.1: Research and populate memory
Read the following to extract patterns:
- `lib/features/auth/` — auth flow, providers, services
- `.claude/rules/auth/supabase-auth.md` — auth rules

Key areas to document:
- Auth flow (sign-in, sign-up, sign-out, password reset)
- Session management
- `secure_password_change=true` setting
- OTP-based password reset flow
- Cache reset on sign-out
- Common gotchas

### Sub-phase 7.3: Populate Backend-Data-Layer Agent Memory

**Files:**
- Modify: `.claude/agents/backend-data-layer-agent.memory.md`

**Agent:** `general-purpose`

#### Step 7.3.1: Research and populate memory
Read the following to extract patterns:
- `lib/shared/data/` — base repository, base datasource
- `lib/features/*/data/` — concrete implementations
- `.claude/rules/backend/data-layer.md` — data layer rules
- `.claude/rules/database/schema-patterns.md` — schema patterns

Key areas to document:
- Repository pattern (`BaseRepository` and concrete repos)
- Datasource pattern (local + remote)
- Soft-delete service integration
- Change log / sync control patterns
- Database migration workflow
- Common gotchas

---

## Phase 8: Verification

### Sub-phase 8.1: Verify Config Files

**Agent:** `general-purpose`

#### Step 8.1.1: Verify 0 stale config files
Search all modified config files for stale references:
- Grep for "13 features" (should be 0 matches)
- Grep for "9 agents" (should be 0 matches in docs/CLAUDE.md)
- Grep for "debugPrint" in `.claude/rules/` (should be 0 matches)
- Grep for bare `flutter test`/`flutter build` in `.claude/rules/` (should be 0 matches)
- Grep for "haiku" in `.claude/agents/` (should be 0 matches)

### Sub-phase 8.2: Verify Constraint Violations

**Agent:** `general-purpose`

#### Step 8.2.1: Verify all 5 violations resolved
- V1: Check sync-constraints.md says "5 attempts"
- V2: Check toolbox-constraints.md reflects persistent storage
- V3: Check sync-constraints.md says "hash-based" not "SHA256"
- V4: Check entries-constraints.md allows SUBMITTED->DRAFT
- V5: Check project_setup_screen.dart has no raw SQL

### Sub-phase 8.3: Verify Pre-Commit Hooks

**Agent:** `general-purpose`

#### Step 8.3.1: Verify hook is configured
```bash
git config core.hooksPath
```
Should output `.githooks`.

### Sub-phase 8.4: Run Flutter Analyze

**Agent:** `general-purpose`

#### Step 8.4.1: Run full flutter analyze
```
pwsh -Command "flutter analyze"
```
<!-- NOTE: flutter analyze does not accept path arguments — it analyzes the entire project -->
Verify 0 analysis errors. Focus review on modified files in `lib/features/projects/` and `lib/features/pdf/services/extraction/models/`.
