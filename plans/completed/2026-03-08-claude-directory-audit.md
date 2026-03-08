# .claude/ Directory Baseline Audit & Cleanup — Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Bring every `.claude/` file path, class reference, and feature description into sync with the current codebase on `feat/sync-engine-rewrite`.
**Spec:** `.claude/specs/2026-03-08-claude-directory-audit-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-08-claude-directory-audit/`

**Architecture:** Scan-first pipeline — 1 Opus mapper scans the codebase and produces an audit report, user reviews it, then 10 Opus workers fix in parallel, followed by Agent #10 (CLAUDE.md owner) which runs after the others to collect their CLAUDE.md findings. Security invariants protect normative content from accidental modification.
**Tech Stack:** CodeMunch MCP for indexing, Glob/Grep/Read for reference validation, Edit for fixes.
**Blast Radius:** ~163 .claude/ files scanned, 0 app code changes, 1 new skill created.

---

## Phase 0: Rollback Safety

### Sub-phase 0.1: Commit and Tag Current State

**Agent**: `general-purpose` (Opus)

#### Step 0.1.1: Commit current .claude/ state

The `.claude/` directory is its own git repo (has `.claude/.git/`), tracked separately from the app repo. Commit and tag in the config repo:

```bash
cd C:/Users/rseba/Projects/Field_Guide_App/.claude
git add -A
git commit -m "chore: snapshot before baseline audit 2026-03-08"
git tag pre-audit-2026-03-08
```

**Verify**: `git log --oneline -1` shows the snapshot commit. `git tag` includes `pre-audit-2026-03-08`.
**Note**: The app repo is at `C:/Users/rseba/Projects/Field_Guide_App/` (separate `.git`). The config repo is at `C:/Users/rseba/Projects/Field_Guide_App/.claude/` (its own `.git`).

---

## Phase 1: Mapper Scan

### Sub-phase 1.1: Index Codebase and Produce Audit Report

**Agent**: `general-purpose` (Opus)
**Output**: `.claude/outputs/audit-report-2026-03-08.md`

#### Step 1.1.1: Index codebase with CodeMunch

```
mcp__jcodemunch__index_folder(path: "C:\\Users\\rseba\\Projects\\Field_Guide_App", use_ai_summaries: false, max_files: 2000)
```

If CodeMunch is unavailable, fallback to Glob + Grep + Read to build the file inventory manually.

#### Step 1.1.2: Record branch and commit

```bash
git branch --show-current   # Should be: feat/sync-engine-rewrite
git rev-parse HEAD           # Record full commit hash
```

#### Step 1.1.3: Build codebase snapshot

Using CodeMunch `get_file_tree` and `search_symbols`, document:
- All files under `lib/features/` (per-feature directory listing)
- All files under `lib/core/`, `lib/shared/`, `lib/services/`
- All class names (models, providers, repositories, datasources, screens, widgets)
- Database tables from `lib/core/database/schema/*.dart`
- Routes from `lib/core/router/app_router.dart`
- Provider registrations from `lib/main.dart`

#### Step 1.1.4: Scan all .claude/ files for references

For every `.claude/` file in scope (see blast-radius.md for full list):
1. Read the file
2. Extract all file path references (patterns: `lib/`, `.dart`, `lib/features/`, `lib/core/`)
3. Extract all class/model name references
4. Validate each reference against the codebase snapshot from Step 1.1.3
5. Record broken references per file

#### Step 1.1.5: Identify stale content

Flag any `.claude/` content that describes:
- `entry_personnel` system (removed in commit `8551571`)
- Old sync architecture (pre-rewrite — `sync_service.dart`, `sync_repository.dart` without the engine/ layer)
- Legacy PII migration code (removed in commit `3676de8`)
- Deprecated test files (removed in commit `1341d86`)
- Old provider names that were changed (commit `ad486c0`)

#### Step 1.1.6: Identify orphaned files and branch-only files

Check for orphans:
- `agent-memory/` directories with no matching `agents/*.md` file
- Agent files not listed in CLAUDE.md's agent table (`test-wave-agent`)
- Skills not listed in CLAUDE.md's skills table (`test`)
- Architecture-decision files for features that don't exist
- **Note**: `agent-memory/test-orchestrator-agent/` was confirmed absent during planning — verify this still holds

Identify branch-only files (exist on `feat/sync-engine-rewrite` but not on `main`):
```bash
git diff --name-only main...feat/sync-engine-rewrite -- lib/
```
Record these files — any `.claude/` references to them should be tagged `[BRANCH: feat/sync-engine-rewrite]`.

#### Step 1.1.7: Build cross-reference map

For each `.claude/` file, record which other `.claude/` files it references (e.g., a PRD referencing an architecture doc, an agent referencing a rule file).

#### Step 1.1.8: Write audit report

Save the complete audit report to `.claude/outputs/audit-report-2026-03-08.md` with sections:
1. **Codebase Snapshot** (branch, commit, file counts per feature)
2. **Broken References** (per-file, with line numbers)
3. **Stale Content** (descriptions of removed features/code)
4. **Orphaned Files** (config files with no codebase counterpart)
5. **Cross-Reference Map** (inter-file references)
6. **Branch-Only Files** (files that exist only on this branch, not main)

#### Step 1.1.9: Present report to user

Display a summary of findings:
- Total broken references found
- Top 10 most-affected files
- Orphaned items
- Stale content areas

**GATE**: Wait for user approval before proceeding to Phase 3.

---

## Phase 2: User Review

User reviews the audit report at `.claude/outputs/audit-report-2026-03-08.md` and approves or adjusts the fix scope. No agent work in this phase.

---

## Phase 3: Fix — Worker Agents (11 × Opus)

**Execution order**: Agents #1–#9 and #11 run in parallel (10 agents). Agent #10 (CLAUDE.md + Misc) runs AFTER the other 10 complete, so it can collect their CLAUDE.md issue reports.

Each agent receives the audit report path (`.claude/outputs/audit-report-2026-03-08.md`) as input context.

Agents that discover CLAUDE.md issues MUST write them to `.claude/outputs/agent-N-claude-md-issues.md` (e.g., `agent-6-claude-md-issues.md`). Agent #10 reads these files before updating CLAUDE.md.

**CRITICAL**: Every agent MUST read `.claude/specs/2026-03-08-claude-directory-audit-spec.md` section "Security Invariants" before making any changes.

**Note on `general-purpose` agent type**: This means a direct Opus-level Task call without loading a specific agent `.md` file. These agents have full Read/Edit/Write/Bash/Glob/Grep access.

### Sub-phase 3.1: Feature Docs A (Agent #1)

**Agent**: `general-purpose` (Opus)
**Files** (10):
- `docs/features/feature-auth-overview.md`
- `docs/features/feature-auth-architecture.md`
- `docs/features/feature-contractors-overview.md`
- `docs/features/feature-contractors-architecture.md`
- `docs/features/feature-dashboard-overview.md`
- `docs/features/feature-dashboard-architecture.md`
- `docs/features/feature-entries-overview.md`
- `docs/features/feature-entries-architecture.md`
- `docs/features/feature-locations-overview.md`
- `docs/features/feature-locations-architecture.md`

#### Step 3.1.1: Read audit report broken references for assigned files

Read `.claude/outputs/audit-report-2026-03-08.md` and extract all broken references for the 10 assigned files.

#### Step 3.1.2: For each feature (auth, contractors, dashboard, entries, locations)

For each of the 5 features:

1. **Read current code structure**: Use `mcp__jcodemunch__get_file_tree` for `lib/features/{name}/`
2. **Read existing overview doc**: Read the `-overview.md` file
3. **Read existing architecture doc**: Read the `-architecture.md` file
4. **Compare and fix**:
   - Fix all broken file paths from the audit report
   - Update class/model/provider names that were renamed
   - Update the "File Structure" or "Directory Structure" section to match current layout
   - Update the "Key Classes" or "Models" section with current class names
   - Update provider names and screen names if they changed
   - Remove references to deleted code (entry_personnel for entries/contractors)
   - Add references to new files/classes not mentioned
   - For sync-related references, tag changes with `[BRANCH: feat/sync-engine-rewrite]`
5. **Do NOT**: Rewrite prose, design rationale, or architecture philosophy

#### Step 3.1.3: Verify no broken references remain

After all fixes, grep each modified file for `lib/` paths and validate they exist on disk.

#### Step 3.1.4: Report CLAUDE.md issues

If any CLAUDE.md issues found (unlikely for this agent), write them to output for Agent #10.

---

### Sub-phase 3.2: Feature Docs B (Agent #2)

**Agent**: `general-purpose` (Opus)
**Files** (10):
- `docs/features/feature-pdf-overview.md`
- `docs/features/feature-pdf-architecture.md`
- `docs/features/feature-photos-overview.md`
- `docs/features/feature-photos-architecture.md`
- `docs/features/feature-projects-overview.md`
- `docs/features/feature-projects-architecture.md`
- `docs/features/feature-quantities-overview.md`
- `docs/features/feature-quantities-architecture.md`
- `docs/features/feature-settings-overview.md`
- `docs/features/feature-settings-architecture.md`

#### Steps: Same as Sub-phase 3.1 (Steps 3.1.1–3.1.4) but for features: pdf, photos, projects, quantities, settings.

**Special attention**: PDF feature has extensive `services/extraction/` pipeline — verify architecture doc lists current stages, models, and pipeline structure.

---

### Sub-phase 3.3: Feature Docs C (Agent #3)

**Agent**: `general-purpose` (Opus)
**Files** (7):
- `docs/features/feature-sync-overview.md`
- `docs/features/feature-sync-architecture.md`
- `docs/features/feature-toolbox-overview.md`
- `docs/features/feature-toolbox-architecture.md`
- `docs/features/feature-weather-overview.md`
- `docs/features/feature-weather-architecture.md`
- `docs/features/README.md`

#### Steps: Same as Sub-phase 3.1 (Steps 3.1.1–3.1.4) but for features: sync, toolbox, weather.

**Special attention — Sync**: This feature was completely rewritten. The architecture doc likely describes the OLD sync architecture. Update to reflect:
- New directory structure: `adapters/`, `application/`, `config/`, `domain/`, `engine/`
- Key new classes: `SyncEngine`, `SyncOrchestrator`, `TableAdapter` (base class with 17 concrete adapters), `ChangeTracker`, `ConflictResolver`, `IntegrityChecker`, `SyncRegistry`, `SyncMutex`
- New application layer: `BackgroundSyncHandler`, `FcmHandler`, `SyncLifecycleManager`
- New presentation: `SyncProvider`, `SyncDashboardScreen`, `ConflictViewerScreen`, `ProjectSelectionScreen`
- Tag ALL sync changes with `[BRANCH: feat/sync-engine-rewrite]`

**README.md**: Update the feature doc index to match current file list and count (~39 total docs, not 30).

---

### Sub-phase 3.4: PRDs (Agent #4)

**Agent**: `general-purpose` (Opus)
**Files** (14): All files in `prds/`

#### Step 3.4.1: Read audit report for PRD broken references

#### Step 3.4.2: For each PRD

1. Read the PRD file
2. Read the corresponding feature code via CodeMunch
3. Fix broken file paths
4. Update class/model names
5. For each feature section (requirements, data model, etc.):
   - If the requirement was implemented as described → leave as-is
   - If the requirement was implemented differently → update to reflect actual implementation, note `[IMPLEMENTED: differently than spec]`
   - If the requirement was descoped → note `[DESCOPED]`
   - If new functionality was added beyond the PRD → note `[ADDED: not in original spec]`
6. Do NOT rewrite the PRD's purpose, vision, or rationale sections

#### Step 3.4.3: Handle special PRDs

- `pdf-extraction-v2-prd-2.0.md` — Large file (55KB). Focus on file path fixes and status annotations only.
- `2026-02-21-project-based-architecture-prd.md` — Large file (38KB). Focus on file path fixes and implementation status only.

---

### Sub-phase 3.5: Architecture Decisions (Agent #5)

**Agent**: `general-purpose` (Opus)
**Files** (15): All files in `architecture-decisions/`

#### Step 3.5.1: Read audit report for constraint file broken references

#### Step 3.5.2: For each constraint file

1. Read the constraint file
2. **SECURITY INVARIANT**: Do NOT modify any line containing `MUST` or `MUST NOT` hard rules. Only fix file path references and class names in the "References" or "Files" sections.
3. Fix broken file paths to point to current locations
4. Update class/model names that were renamed
5. Remove references to deleted code files (not the rules about them)

---

### Sub-phase 3.6: Agents + Memories (Agent #6)

**Agent**: `general-purpose` (Opus)
**Files** (18): 9 agent files + 8 memory dirs (9 MEMORY.md files + 1 extra: pdf-agent/stage-4c-implementation.md)

#### Step 3.6.1: Read audit report for agent file broken references

#### Step 3.6.2: For each agent file

1. Read the agent `.md` file
2. **SECURITY INVARIANT**: Do NOT modify `tools`, `disallowedTools`, `model`, `permissionMode` YAML frontmatter fields. These define agent capabilities.
3. Fix file path references in the agent's context/prompt sections
4. Update class names and feature descriptions
5. Update any `@` file references that point to moved/renamed files
6. If the agent references feature docs, rules, or architecture-decisions that were renamed, update the references

#### Step 3.6.3: For each agent memory file

1. Read the memory `MEMORY.md` file
2. **SECURITY INVARIANT (security-agent only)**: Do NOT delete any findings. Only update file paths within findings.
3. Fix broken file path references
4. Update class/model names
5. Remove references to code that no longer exists (except security findings)

#### Step 3.6.4: Handle orphans and report CLAUDE.md issues

- Check if `agent-memory/test-orchestrator-agent/` exists on disk (confirmed absent during planning — verify). If found, check for security findings before deleting.
- Verify `test-wave-agent` has correct references.
- **Write CLAUDE.md issues** to `.claude/outputs/agent-6-claude-md-issues.md`:
  - `test-wave-agent` missing from CLAUDE.md agent table
  - Any other CLAUDE.md discrepancies found

---

### Sub-phase 3.7: Rules (Agent #7)

**Agent**: `general-purpose` (Opus)
**Files** (11): All files in `rules/` and subdirectories (2 root files + 9 in subdirs)

#### Step 3.7.1: Read audit report for rule file broken references

#### Step 3.7.2: For each rule file

1. Read the rule file
2. **SECURITY INVARIANT**: Do NOT modify lines containing security directives (token storage, logging prohibitions, RLS patterns, PKCE requirements). Only fix file paths and class names.
3. Fix broken file path references and code examples
4. Update class/model names that were renamed
5. Verify code snippet examples still reflect actual patterns (if a code example references a class that was renamed, update the class name in the example)

**Special attention — `rules/sync/sync-patterns.md`**: This likely describes the OLD sync architecture. Update file paths and class names to reflect the new engine/ architecture. Tag with `[BRANCH: feat/sync-engine-rewrite]`.

**Special attention — `rules/architecture.md`**: Update feature count to "13 features (plus 4 toolbox sub-features)" if it currently says something different.

---

### Sub-phase 3.8: State JSONs (Agent #8)

**Agent**: `general-purpose` (Opus)
**Files** (17): All files in `state/`

#### Step 3.8.1: Read audit report for state JSON broken references

#### Step 3.8.2: For each feature state JSON

1. Read the JSON file
2. **SECURITY INVARIANT**: Do NOT modify `constraints_summary` arrays. Do NOT move `active_blockers` to resolved.
3. Update `files` or `file_inventory` arrays to match current feature directory contents
4. Update `status` field only if clearly wrong (e.g., feature marked "not started" but has full implementation)
5. Update `key_classes` or `models` arrays with current class names
6. Update `providers`, `screens`, `repositories` arrays if they exist and are outdated
7. Fix any file paths in other fields

#### Step 3.8.3: For special state files

- `FEATURE-MATRIX.json` — Update the matrix to reflect current feature status and file counts
- `AGENT-FEATURE-MAPPING.json` — Update agent-to-feature mappings
- `AGENT-CHECKLIST.json` — Update checklist items
- `PROJECT-STATE.json` — Update `current_branch`, `last_commit` fields. Do NOT modify `active_blockers`.

---

### Sub-phase 3.9: Skills + Audit Skill (Agent #9)

**Agent**: `general-purpose` (Opus)
**Files** (~25 existing + 1 new): 9 `SKILL.md` files + ~15 reference files across `references/` subdirectories + new `skills/audit-config/SKILL.md`

Reference files by skill:
- `brainstorming/references/` — 2 files (design-sections.md, question-patterns.md)
- `interface-design/references/` — 2 files (construction-domain.md, flutter-tokens.md)
- `pdf-processing/references/` — 4 files + `scripts/` directory
- `systematic-debugging/references/` — 4 files
- `test/references/` — 3 files (adb-commands.md, output-format.md, uiautomator-parsing.md)

#### Step 3.9.1: Verify existing skill references

For each of the 9 existing skills:
1. Read the `SKILL.md` file
2. Check all file path references (`@` references, file paths in instructions)
3. Fix any broken references
4. Read each file in the `references/` subdirectory (if it exists) and fix broken paths
5. **Write CLAUDE.md issues** to `.claude/outputs/agent-9-claude-md-issues.md`:
   - `test` skill missing from CLAUDE.md skills table
   - `audit-config` skill needs to be added to CLAUDE.md skills table

#### Step 3.9.2: Build new `/audit-config` skill

Create `.claude/skills/audit-config/SKILL.md` with this content:

```markdown
---
description: "Audit the .claude/ directory against the current codebase. Validates file paths, class references, and security invariants."
---

# Audit Config

## Overview

One-command health check of the `.claude/` configuration directory against the current codebase. Finds broken file paths, stale class references, orphaned config files, and missing coverage.

## Checklist

1. Index codebase with CodeMunch (or use existing recent index)
2. Scan all `.claude/` files for file path references
3. Validate each reference against disk
4. Check class/model names against codebase definitions
5. Verify security invariants
6. Produce structured report
7. Present findings to user with recommended fixes

## Process

### Step 1: Index Codebase

```
mcp__jcodemunch__index_folder(path: ".", use_ai_summaries: false, max_files: 2000)
```

Fallback: Use Glob + Grep + Read if CodeMunch unavailable.

### Step 2: Scan References

For each `.claude/` file in scope:
- `docs/features/` (26 files + README)
- `prds/` (14 files)
- `agents/` (9 files)
- `agent-memory/` (10 files across 8 dirs)
- `architecture-decisions/` (15 files)
- `rules/` (9-11 files)
- `state/` (17 files)
- `skills/` (9+ SKILL.md files)
- `CLAUDE.md`
- `docs/` root and guides (~12 files)
- `hooks/` (2 files)
- `autoload/_state.md`
- `memory/MEMORY.md`
- `defects/` (~15 files)

Extract file path patterns: `lib/`, `.dart`, `lib/features/`, `lib/core/`
Extract class name patterns: PascalCase words that look like Dart classes

### Step 3: Validate

For each reference:
- File paths: Check if file exists on disk using Glob
- Class names: Check if class exists in CodeMunch index using search_symbols

### Step 4: Security Invariant Check

Verify:
- [ ] All agent files have expected `tools`/`disallowedTools` fields
- [ ] security-agent has `disallowedTools: Write, Edit, Bash`
- [ ] security-agent body contains Iron Law ("NEVER MODIFY CODE. REPORT ONLY.")
- [ ] Constraint files contain `MUST`/`MUST NOT` rules (count ≥ expected)
- [ ] CLAUDE.md contains string "Security is non-negotiable" (grep, not line number)
- [ ] Rule files contain security directive sentinel strings (token storage, RLS patterns)
- [ ] `active_blockers` in PROJECT-STATE.json count is consistent

### Step 5: Report

Save to `.claude/outputs/audit-report-YYYY-MM-DD.md`:

```markdown
# .claude/ Audit Report — YYYY-MM-DD

**Branch**: [current branch]
**Commit**: [commit hash]
**Scanned**: [N] .claude/ files against [N] codebase files

## Summary
- Broken paths: [N]
- Stale references: [N]
- Orphaned config files: [N]
- Missing coverage: [N]
- Security invariants: [PASS/FAIL]

## Broken Paths
[Per-file list with line numbers]

## Stale References
[Class/model names that don't exist]

## Orphaned Config
[.claude/ files with no matching codebase feature]

## Missing Coverage
[Codebase features/files with no .claude/ docs]

## Security Invariants
[Pass/fail for each check]
```

### Step 6: Present to User

Display summary and ask if user wants to:
- A) Fix automatically (invoke brainstorming for significant changes)
- B) Fix manually
- C) Defer to next session

## Scope Exclusions

These directories are NOT scanned:
- `logs/` (historical archives)
- `adversarial_reviews/` (historical reviews)
- `code-reviews/` (historical reviews)
- `test-results/` (historical test data)
- `backlogged-plans/` (future-looking)
- `plans/sections/` (in-progress plan work)

## Security Invariants (Immutable)

This skill NEVER modifies files. It is read-only and report-only.
```

---

### Sub-phase 3.10: CLAUDE.md + Misc Config (Agent #10)

**Agent**: `general-purpose` (Opus)
**Files** (~17): CLAUDE.md (single owner) + docs root + guides + hooks + autoload + memory

**IMPORTANT**: This agent runs AFTER Agents #1-#9 and #11 complete (not in parallel).

#### Step 3.10.1: Collect CLAUDE.md issues from other agents

Read issue files written by other agents:
- `.claude/outputs/agent-6-claude-md-issues.md` (from Agents+Memories agent)
- `.claude/outputs/agent-9-claude-md-issues.md` (from Skills agent)
- Any other `agent-*-claude-md-issues.md` files in `.claude/outputs/`

Expected issues:
- Agent #6: `test-wave-agent` missing from agent table
- Agent #9: `test` skill missing from skills table, `audit-config` needs adding
- Possibly others discovered during the audit

#### Step 3.10.2: Update CLAUDE.md

1. **SECURITY INVARIANT**: Line 5 ("Security is non-negotiable...") is IMMUTABLE.
2. Add `test-wave-agent` to the Agents table (or remove if determined obsolete during Phase 1)
3. Add `test` skill to the Skills table
4. Add `audit-config` skill to the Skills table (new skill from Agent #9)
5. Fix any broken file paths in Quick Reference Commands, Key Files, etc.
6. Update feature count references to use "13 features (plus 4 toolbox sub-features)" consistently
7. Update any other stale references identified in the audit report

#### Step 3.10.3: Update docs/INDEX.md

Update file counts to match actual (currently claims 30, actual ~39). Add new files to the index.

#### Step 3.10.4: Update docs/ root files

For each of the 5 docs root files (ui-audit, ui-dependency-map, ui-refactor, etc.):
1. Read the file
2. Fix broken file paths and class names
3. These are recent (March 6) so likely mostly accurate

#### Step 3.10.5: Update docs/guides/

For each guide file:
1. Fix broken file paths and class names
2. **Special attention**: `chunked-sync-usage.md` likely references old sync classes — update to new engine architecture, tag with `[BRANCH: feat/sync-engine-rewrite]`
3. Update `README.md` to list all current guides

#### Step 3.10.6: Update hooks/

For each hook file:
1. Fix broken file paths and flutter commands
2. Ensure paths use correct format

#### Step 3.10.7: Update autoload/_state.md

Fix any broken plan paths, defect paths, or blocker references.

#### Step 3.10.8: Update memory/MEMORY.md

Fix broken file paths and outdated references. This is the project-level orchestrator memory.

---

### Sub-phase 3.11: Defects (Agent #11)

**Agent**: `general-purpose` (Opus)
**Files** (~15): All files in `defects/`

#### Step 3.11.1: Read audit report for defect file broken references

#### Step 3.11.2: For each defect file

1. Read the defect file
2. **SECURITY INVARIANT**: Finding descriptions, severity, status, and root cause analysis are IMMUTABLE. Only file path and line number references may be updated.
3. For each finding that references a file path:
   - Check if the file still exists at that path
   - If moved: update the path to the new location
   - If deleted: note `[FILE REMOVED]` next to the path but do NOT delete the finding
4. For line number references (`file.dart:45`):
   - If the file exists, try to locate the referenced code at or near the line number
   - If the line number is clearly wrong (code is now at a different line), update it
   - If uncertain, leave as-is (line numbers are fragile)

---

## Phase 4: Verification

### Sub-phase 4.1: Re-run Audit Scan

**Agent**: `general-purpose` (Opus)

#### Step 4.1.1: Re-index codebase

```
mcp__jcodemunch__index_folder(path: ".", use_ai_summaries: false, incremental: true)
```

#### Step 4.1.2: Re-scan all modified files

Run the same reference validation from Phase 1 Step 1.1.4 against all files that were modified in Phase 3. Count remaining broken references.

**Expected**: Zero broken file paths.

### Sub-phase 4.2: Security Invariant Check

**Agent**: `security-agent` (Opus)

#### Step 4.2.0: Get list of modified files

Generate manifest of all files changed since the pre-audit tag:
```bash
cd C:/Users/rseba/Projects/Field_Guide_App/.claude
git diff --name-only pre-audit-2026-03-08..HEAD
```

#### Step 4.2.1: Diff all modified .claude/ files

For each file in the manifest, check the diff and confirm:
- [ ] No `tools`/`disallowedTools`/`permissionMode` fields changed in agent files
- [ ] Security-agent Iron Law prose section ("NEVER MODIFY CODE. REPORT ONLY.") present in `agents/security-agent.md` body
- [ ] No `MUST`/`MUST NOT` hard rules removed from constraint files
- [ ] CLAUDE.md contains the string "Security is non-negotiable" (use grep, NOT line number — line may shift if content added above it)
- [ ] Rule file security directives preserved: grep for sentinel strings ("Never log tokens", "flutter_secure_storage", "auth.uid()", "Do not add custom deep link") and confirm count matches pre-audit
- [ ] `active_blockers` in PROJECT-STATE.json not incorrectly resolved
- [ ] Security-agent MEMORY.md findings preserved (finding count unchanged)
- [ ] Defect file findings unchanged (only paths updated)
- [ ] `constraints_summary` arrays in state JSONs unchanged

#### Step 4.2.2: Report security invariant status

If any invariant was violated, flag the specific file and change for rollback. Provide the exact diff lines showing the violation.

### Sub-phase 4.3: Present Results

#### Step 4.3.1: Generate change summary

List all files modified, grouped by agent, with a count of fixes applied per file.

#### Step 4.3.2: Present to user

Show:
- Total files modified
- Total broken references fixed
- Remaining issues (if any)
- Security invariant status (all PASS or specific FAILs)
- Orphaned items removed
- New skill created

#### Step 4.3.3: Commit changes

If user approves, commit each agent's changes as a separate commit:

```bash
cd .claude
git add docs/features/feature-auth-* docs/features/feature-contractors-* docs/features/feature-dashboard-* docs/features/feature-entries-* docs/features/feature-locations-*
git commit -m "audit: Agent #1 — Feature Docs A (auth, contractors, dashboard, entries, locations)"

# Repeat for each agent's files...
```

---

## Security Invariants Reference

Copy of the immutable content list from the spec. Every agent MUST read this before making changes.

| Agent | Protected Content | Rule |
|-------|-------------------|------|
| #5 (Arch-Decisions) | Lines with `MUST`/`MUST NOT` | Do NOT modify hard rules |
| #6 (Agents) | `tools`, `disallowedTools`, `model`, `permissionMode` frontmatter | Do NOT modify capability fields |
| #6 (Memories) | Security-agent findings | Update paths only, NEVER delete findings |
| #7 (Rules) | Security directives (token storage, RLS, PKCE) | Do NOT modify normative security lines |
| #8 (State) | `constraints_summary` arrays | Do NOT modify — these are normative |
| #8 (State) | `active_blockers` in PROJECT-STATE | Do NOT move to resolved without code proof |
| #10 (CLAUDE.md) | Line 5: "Security is non-negotiable..." | IMMUTABLE |
| #11 (Defects) | Finding descriptions, severity, status | Update paths only, NEVER modify findings |

---

## Agent Routing Summary

| Phase | Sub-phase | Agent Type | Model | Files | Parallel? |
|-------|-----------|------------|-------|-------|-----------|
| 0 | Rollback | general-purpose | Opus | git ops | Sequential |
| 1 | Mapper | general-purpose | Opus | scan all | Sequential |
| 3.1 | Feature Docs A | general-purpose | Opus | 10 | Parallel |
| 3.2 | Feature Docs B | general-purpose | Opus | 10 | Parallel |
| 3.3 | Feature Docs C | general-purpose | Opus | 7 | Parallel |
| 3.4 | PRDs | general-purpose | Opus | 14 | Parallel |
| 3.5 | Arch-Decisions | general-purpose | Opus | 15 | Parallel |
| 3.6 | Agents+Memories | general-purpose | Opus | 18 | Parallel |
| 3.7 | Rules | general-purpose | Opus | 11 | Parallel |
| 3.8 | State JSONs | general-purpose | Opus | 17 | Parallel |
| 3.9 | Skills+Audit | general-purpose | Opus | ~25+new | Parallel |
| 3.11 | Defects | general-purpose | Opus | ~15 | Parallel |
| 3.10 | CLAUDE.md+Misc | general-purpose | Opus | ~17 | **After #1-#9,#11** |
| 4.1 | Re-scan | general-purpose | Opus | scan modified | Sequential |
| 4.2 | Security Check | security-agent | Opus | diff check | Sequential |
| 4.3 | Present Results | general-purpose | Opus | summary | Sequential |
