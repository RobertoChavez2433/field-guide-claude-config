# Workflow Improvements Spec

**Date**: 2026-03-22
**Source**: Workflow insights report (`.claude/docs/workflow-insights-report.md`)
**Session**: S624

---

## Overview

### Purpose
Bundle all workflow insights findings into a single improvement effort: config remediation, process improvements, codebase fixes, automated enforcement, and skill updates.

### Scope
**Included:**
- Fix all stale config files (.gitignore, CLAUDE.md, agent configs, rule files)
- Reconcile 5 constraint violations (case-by-case)
- Fix 55 `catch (_)` and 8 unsafe `.firstWhere` (re-audit first)
- Move raw SQL out of `project_setup_screen.dart`
- Resolve 2 stale defects
- Create `/spike` skill for research/hypothesis work
- Add lightweight process path (XS+S bypass full pipeline)
- Tiered pre-commit hooks (hard block security, warn code quality)
- Update brainstorming skill (remove adversarial review)
- Update writing-plans skill (spec as source of truth, review role clarity)
- Populate 3 empty agent memories

**Excluded:**
- SQLite encryption (BLOCKER-28, separate spec)
- GitHub Actions CI (separate spec)
- Sync branch merge (operational, not a spec)
- Test infrastructure changes

### Success Criteria
- 0 stale config files (currently 19 stale/critical)
- 0 open constraint violations
- Pre-commit hooks catching security anti-patterns
- `/spike` skill operational
- Lightweight path documented and usable for XS+S changes
- Brainstorming and writing-plans skills updated per decisions above

---

## Decisions Made

### Constraint Violations (Case-by-Case)
| Violation | Decision | Rationale |
|-----------|----------|-----------|
| V1: Sync retry 3→5 | Verify code, update docs | Code is likely right, docs are stale. Must verify first. |
| V2: Toolbox persistence | Update docs | Toolbox evolved past original "ephemeral" constraint. 4 tables with CRUD+sync. |
| V3: SHA256→djb2 | Update docs | djb2 sufficient for change detection. HTTPS handles transport integrity. |
| V4: Entry state reversal | Update docs | `undoSubmission()` (SUBMITTED→DRAFT) is intentional. Inspectors need to fix accidental submissions. |
| V5: Raw SQL in presentation | Fix code | Move 6 `db.execute()`/`db.delete()` from `project_setup_screen.dart` into project repository. Architecturally sound — follows existing data flow pattern. |

### Process Decisions
- **Lightweight path**: XS (single-file mechanical) and S (up to 3 files, known pattern) bypass full pipeline
- **Pre-commit hooks**: Tiered — hard block security patterns, warn on code quality patterns
- **Anti-pattern list**: Must be re-audited against current codebase before enforcement. Old lists are stale.
- **Brainstorming skill**: Remove adversarial review entirely. Brainstorming captures intent only.
- **Writing-plans skill**: Spec is user's source of truth for intent/scope/vision. Reviews verify the plan against codebase, not the spec's goals. Adversarial reviewer finds holes in the plan. Security reviewer unchanged.

---

## Work Categories

### Category 1: Config Remediation (Mechanical)

| # | File(s) | Change | Priority |
|---|---------|--------|----------|
| 1 | `.gitignore` | Add `test_results/` (underscore) pattern | P0 |
| 2 | `.gitignore` | Add `autoload/_state.md`, `state/*.json` to stop commit noise | P0 |
| 3 | `implement-orchestrator.md:89` | `haiku` → `sonnet` | P0 |
| 4 | `CLAUDE.md` | "9 agents" → "10 agents" | P1 |
| 5 | 5 rule/config files | "13 features" → "17 features" | P1 |
| 6 | 2 config files | "9 agents" → "10 agents" | P1 |
| 7 | 11 instances across 5 rule files | `debugPrint` → `Logger.*()` in examples | P1 |
| 8 | `backend-supabase-agent.md` | 15 bare `supabase` → `npx supabase` | P1 |
| 9 | 6 instances in rules | bare `flutter`/`dart` → `pwsh -Command "..."` | P1 |
| 10 | `sync-patterns.md` | 7 `[BRANCH: feat/sync-engine-rewrite]` annotations — remove after merge | P2 |

### Category 2: Stale Defect Resolution

| # | Defect | Action |
|---|--------|--------|
| 1 | `secure_password_change = false` (auth) | Mark RESOLVED — verified `true` at `config.toml:207` |
| 2 | `PRAGMA foreign_keys never enabled` (projects/database) | Mark RESOLVED — verified at `database_service.dart:61,83`. Remove stale code comment at `project_local_datasource.dart:112` |

### Category 3: Constraint Reconciliation

| Violation | Action | Details |
|-----------|--------|---------|
| V1: Sync retry 3→5 | Verify code, update docs | Confirm 5 is intentional, document orchestrator vs engine difference |
| V2: Toolbox persistence | Update docs | Remove "no persistence" / "ephemeral" language, document the 4 tables |
| V3: SHA256→djb2 | Update docs | Change to "hash-based change detection", remove SHA256 requirement |
| V4: Entry state reversal | Update docs | Allow SUBMITTED→DRAFT, document `undoSubmission()` as intentional |
| V5: Raw SQL in presentation | Fix code | Move 6 `db.execute()`/`db.delete()` from `project_setup_screen.dart` into project repository |

### Category 4: Codebase Anti-Pattern Fixes

| Pattern | Current Count | Action |
|---------|--------------|--------|
| `catch (_)` silent swallowing | 55 across 28 files | Re-audit current state, then fix: add `Logger.error()` or rethrow as appropriate per-case |
| `.firstWhere` without safety | 8 instances | Replace with `.firstOrNull` + null check |

**Note:** Both counts need re-verification against current code before fixing.

### Category 5: Skill Updates

**Brainstorming skill:**
- Remove adversarial review section entirely
- Remove review orchestration, handling findings, and review output sections
- Terminal state: spec written → offer to invoke writing-plans
- Simplify checklist to: explore → ask → propose approaches → present sections → write spec → hand off

**Writing-plans skill:**
- Add explicit language: "The spec is the user's source of truth for intent, scope, and vision. Reviews do not override the spec's goals."
- Review waves verify the **plan** against the codebase, not the spec's intent
- Adversarial reviewer role: find holes/gaps in the plan, suggest better implementation approaches
- Security reviewer role: unchanged

**New `/spike` skill:**
- Input: hypothesis or question
- Output: findings document at `.claude/spikes/YYYY-MM-DD-<topic>.md`
- Time-boxed: 1-2 sessions
- No code ships — research only, throwaway prototypes fine
- Terminal state: recommend spec (proceed), park (needs more info), or kill (not viable)

### Category 6: Lightweight Process Path

| Size | Criteria | Process |
|------|----------|---------|
| **XS** | Single-file, mechanical | No skill invocation. Just do it. |
| **S** | Up to 3 files, well-understood pattern | Skip brainstorming and writing-plans. Implement directly. |
| **M+** | 4+ files or novel architecture | Full pipeline: brainstorming → writing-plans → implement |

Examples:
- XS: fix a typo, update a config value, rename a variable
- S: add a TestingKey, fix a `catch (_)`, update a stale rule, add Logger to a file
- M: new feature, architectural change, multi-file refactor

Document in CLAUDE.md under Session & Workflow section.

### Category 7: Pre-Commit Hooks (Tiered)

**Hard block (security/critical):**
- Raw SQL in `presentation/` directories
- `.env` or credential files being committed
- Other security patterns TBD during implementation

**Warn only (code quality):**
- `catch (_)` without logging
- `.firstWhere` without `orElse`
- `debugPrint` in lib/ code
- Other patterns TBD after re-auditing current anti-pattern list

**Implementation:** PowerShell-based for Windows compatibility. Grep-based pattern matching.

**Note:** Anti-pattern list must be re-derived from current codebase, not carried forward from stale docs.

### Category 8: Empty Agent Memory Population

| Agent | Current State | Action |
|-------|--------------|--------|
| `backend-supabase-agent` | 134 bytes (empty) | Populate with Supabase patterns, RLS conventions, migration workflow |
| `auth-agent` | 134 bytes (empty) | Populate with auth flow patterns, session management, deep linking |
| `backend-data-layer-agent` | 148 bytes (empty) | Populate with repository patterns, datasource conventions, schema knowledge |

Population method: agent reads codebase during implementation, writes findings to its own memory file.

---

## Rejected Alternatives

From the workflow insights report, these were evaluated and excluded:

| Item | Reason for Exclusion |
|------|---------------------|
| `flutter-cmd.sh` wrapper | Root cause is agent non-compliance, not missing wrapper |
| Dart custom lint rules | Anti-patterns are in agent prompts, not analyzable by Dart linter |
| Persistent test driver | Saves minutes not hours — app needs rebuild after code changes |
| SQLite encryption | Separate spec needed (significant effort, not drop-in) |
| GitHub Actions CI | Separate spec needed |

---

*Spec approved 2026-03-22, Session S624*
