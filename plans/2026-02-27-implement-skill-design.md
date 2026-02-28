# /implement Skill — Field Guide App

**Date**: 2026-02-27
**Source**: Adapted from Hackers_Keyboard_Fork, Hiscores_Tracker, Tablite, Voice_Recorder_Notes_App
**Architecture**: Supervisor + Orchestrator (2-layer)

---

## Overview

A `/implement <plan-path>` skill that takes a plan file and autonomously executes it phase-by-phase using specialized agents, with quality gates, checkpoint recovery, and context handoff support.

### Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | 2-layer (Supervisor + Orchestrator) | Main context stays clean, crash recovery via checkpoint, can loop orchestrators indefinitely |
| Quality gates | 6 gates (Build, Analyze, P1 Fixes, Code Review, Completeness, Security) | Security gate replaces Performance gate from other projects — leverages new security-agent |
| Agent routing | Specialized agents by file path | Leverages existing 8 agents instead of generic general-purpose for everything |
| Build commands | `pwsh -Command "flutter ..."` | Git Bash silently fails on Flutter — must use pwsh wrapper per CLAUDE.md |

---

## Files to Create

| File | Purpose |
|------|---------|
| `.claude/skills/implement/SKILL.md` | Skill definition (supervisor prompt + embedded orchestrator prompt) |

### Files to Update

| File | Change |
|------|--------|
| `.claude/CLAUDE.md` | Add `implement` to Skills table |

---

## Phase 1: Supervisor Layer

The skill entry point. Runs in the main conversation window. Never touches source code.

### Frontmatter

```yaml
name: implement
description: "Spawn an orchestrator agent to implement a plan. Main window stays clean as a pure supervisor."
user-invocable: true
```

### Iron Law

```
NEVER use Edit or Write tools on source files. Only Read (plan/checkpoint), Task (spawn orchestrator), AskUserQuestion.
The ONLY file you may Write is `.claude/state/implement-checkpoint.json`.
```

### Supervisor Workflow

**Step 1: Accept the Plan**
1. User provides plan file path (or name — search `.claude/plans/` if needed)
2. Read the plan file to extract the phase list (names only)
3. Check for existing checkpoint at `.claude/state/implement-checkpoint.json`:
   - Same plan path → ask "Resume from checkpoint or start fresh?"
   - Different plan path → delete it, start fresh
   - Not exists → start fresh
4. Initialize checkpoint JSON if starting fresh
5. Present phase list to user, confirm before starting

**Step 2: Spawn Orchestrator**
- Single foreground Task: `subagent_type: general-purpose, model: opus`
- Pass: plan file path, checkpoint file path

**Step 3: Handle Orchestrator Result**

| Status | Action |
|--------|--------|
| DONE | Present final summary. Delete checkpoint file. |
| HANDOFF | Log handoff count. Spawn fresh orchestrator (Step 2 again). |
| BLOCKED | Present blocked issue(s). Ask user: fix manually, skip, or adjust plan. |

Loop: `while status != DONE: spawn orchestrator`

**Step 4: Final Summary**
```
## Implementation Complete

**Plan**: [plan filename]
**Orchestrator cycles**: N (M handoffs)

### Phases
1. [Phase] — DONE
...

### Files Modified
- [file list]

### Quality Gates
- Build: PASS
- Analyze: PASS
- P1 Fix Pass: PASS (N P1s fixed)
- Full Code Review: PASS (N cycles)
- Plan Completeness: PASS
- Security Review: PASS

### Per-Phase Reviews
1. [Phase] — PASS/FAIL (N P0, M P1, K P2)

### P2 Nitpicks (for awareness)
- [list]

### Decisions Made
- [list]

Ready to review and commit.
```

Supervisor does NOT commit or push.

---

## Phase 2: Orchestrator Layer

Spawned by the supervisor. Dispatches specialized agents, runs builds, enforces quality gates, manages checkpoint state. Never writes code itself.

### Tools Allowed

Read, Glob, Grep, Bash, Task, Write (ONLY for checkpoint file)

### Pre-Authorized Bash Commands

```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
pwsh -Command "flutter build apk --debug"
```

All Flutter commands MUST use `pwsh -Command "..."` wrapper (Git Bash silently fails).

### Inputs

- Plan file: `{{PLAN_PATH}}`
- Checkpoint file: `{{CHECKPOINT_PATH}}` (`.claude/state/implement-checkpoint.json`)
- Conventions: `.claude/CLAUDE.md`
- Active defects: `.claude/defects/_defects-*.md`
- Code review agent: `.claude/agents/code-review-agent.md`
- Security agent: `.claude/agents/security-agent.md`

### On Start

1. Read checkpoint file
2. Read plan file
3. Read `.claude/CLAUDE.md`
4. Read `.claude/agents/code-review-agent.md` and `.claude/agents/security-agent.md`
5. Determine current position (which phases done, which is next)
6. If resuming mid-review-cycle, pick up from last gate state

### Implementation Loop (for each phase)

**Step 1a: Analyze the Phase**
- Identify files to modify and dependencies on prior phases
- Group files into non-overlapping ownership sets by feature domain

**Step 1b: Dispatch Implementer Agent(s)**

Route to specialized agents based on file paths:

| Phase touches... | Dispatch to | subagent_type |
|-----------------|-------------|---------------|
| `lib/**/presentation/**` | frontend-flutter-specialist-agent | frontend-flutter-specialist-agent |
| `lib/**/data/**` | backend-data-layer-agent | backend-data-layer-agent |
| `lib/features/auth/**` | auth-agent | auth-agent |
| `lib/features/sync/**` | backend-supabase-agent | backend-supabase-agent |
| `lib/features/pdf/**` | pdf-agent | pdf-agent |
| `lib/core/database/**` | backend-data-layer-agent | backend-data-layer-agent |
| `supabase/**` | backend-supabase-agent | backend-supabase-agent |
| Multiple domains / unclear | general-purpose (sonnet) | general-purpose |

All implementer agents use model: sonnet.

Rules:
- Max 3 parallel agents for independent file sets
- Sequential for dependent phases
- Each agent receives: phase plan text, assigned files, `.claude/CLAUDE.md` conventions, relevant defect file entries
- Instruction: "Implement the assigned phase. Only modify your assigned files. Read each file before editing."

**Step 1c: Verify Results**
- After agents return, spot-check that expected files were modified (Grep/Read)

**Step 1d: Build & Analyze**
- Run: `pwsh -Command "flutter analyze"`
- If errors: dispatch fixer agent (Sonnet) with error output, max 3 attempts → BLOCKED
- Run: `pwsh -Command "flutter test"` (if tests exist for the phase)
- Same fix/retry logic

**Step 1e: Per-Phase Code Review (MANDATORY)**
- Dispatch code-review-agent (Opus) for files modified in THIS phase only
- Include full text of `.claude/agents/code-review-agent.md` in prompt
- P0 found → dispatch fixer, re-analyze, re-review (max 3 attempts → BLOCKED)
- P1 found → collect for end-of-implementation fix pass
- P2 → collect for final report

**Step 1f: Update Checkpoint (MANDATORY)**
- Read current checkpoint from disk
- Update phase status to "done"
- Append modified files (no duplicates)
- Append phase review result
- Record decisions
- Write updated checkpoint to disk
- Confirm: "Checkpoint updated: phase [N] marked done, [X] files added"

### Quality Gate Loop (after all phases done)

Run 6 gates in order. Each must pass before the next. Update checkpoint after each.

**Gate 1: Build**
- `pwsh -Command "flutter build apk --debug"`
- Fail → fixer → rebuild, max 3 attempts
- Checkpoint: `"build": "pass"`

**Gate 2: Analyze**
- `pwsh -Command "flutter analyze"`
- Errors → fixer → re-analyze, max 3 attempts
- Checkpoint: `"lint": "pass"`

**Gate 3: P1 Fix Pass**
- Collect ALL P1 findings from per-phase reviews
- Group by feature ownership
- Dispatch fixer(s) → re-analyze, max 3 attempts per P1
- Checkpoint: `"p1_fixes": "pass"`

**Gate 4: Full Code Review**
- Dispatch code-review-agent (Opus) for ALL modified files
- P0/P1 → fixer → re-analyze → re-review
- Loop until `QUALITY GATE: PASS`
- Checkpoint: `"review": {"status": "pass", "findings": [...]}`

**Gate 5: Plan Completeness**
- Dispatch verifier (Sonnet) with plan + all modified files
- Task A: Checklist verification (DONE/MISSING for each requirement)
- Task B: Build verification
- Task C: Functional spot-check (code actually implements behavior, not just matching names)
- Gaps → fixer → re-verify, max 3 attempts
- Checkpoint: `"completeness": "pass"`

**Gate 6: Security Review**
- Dispatch security-agent (Opus) for ALL modified files
- Include full text of `.claude/agents/security-agent.md` in prompt
- Scope review to files in `modified_files` list (not full codebase scan)
- CRITICAL findings → dispatch fixer → re-analyze → re-review
- HIGH findings → collect, report to user, do not auto-fix (user decides)
- MEDIUM/LOW → collect for final report
- Checkpoint: `"security": "pass"`

### Context Management

At ~80% context utilization:
1. Write final checkpoint state to disk
2. Return HANDOFF to supervisor

### Termination

**DONE** (all gates passed):
```
STATUS: DONE
PHASES: [count] completed
FILES: [list]
PHASE_REVIEWS: [phase]: PASS/FAIL (P0:N, P1:M, P2:K) for each
GATES: Build=PASS, Analyze=PASS, P1Fixes=PASS, Review=PASS, Completeness=PASS, Security=PASS
REVIEW_CYCLES: [count]
SECURITY_FINDINGS: [HIGH: N, MEDIUM: M, LOW: K]
P2_NITPICKS: [list or "none"]
DECISIONS: [list]
```

**HANDOFF** (context limit):
```
STATUS: HANDOFF
REASON: Context at ~80%. Checkpoint written.
PHASES_DONE: [count]/[total]
CURRENT_GATE: [which gate or "implementation"]
```

**BLOCKED** (max fix attempts exceeded):
```
STATUS: BLOCKED
ISSUE: [description]
FILE: [file:line]
ATTEMPTS: [count]/3
LAST_ERROR: [error text]
```

---

## Phase 3: Checkpoint Schema

```json
{
  "plan": "<plan file path>",
  "phases": [
    {"name": "Phase 1 title", "status": "done|in_progress|pending|blocked"},
    {"name": "Phase 2 title", "status": "pending"}
  ],
  "build": "pending|pass|fail",
  "modified_files": ["lib/features/auth/...", "lib/core/..."],
  "phase_reviews": [
    {"phase": 1, "status": "pass", "p0": 0, "p1": 1, "p2": 3}
  ],
  "review": {"status": "pending|pass|fail", "findings": []},
  "lint": "pending|pass|fail",
  "p1_fixes": "pending|pass|fail",
  "completeness": "pending|pass|fail",
  "security": "pending|pass|fail",
  "decisions": ["Used X pattern because Y"],
  "fix_attempts": [{"gate": "build", "phase": 1, "attempts": 2}],
  "blocked": []
}
```

---

## Phase 4: Agent Reference Table

| Role | subagent_type | model | Writes Code? |
|------|--------------|-------|-------------|
| Implementer (UI) | frontend-flutter-specialist-agent | sonnet | Yes |
| Implementer (data) | backend-data-layer-agent | sonnet | Yes |
| Implementer (auth) | auth-agent | sonnet | Yes |
| Implementer (sync/supabase) | backend-supabase-agent | sonnet | Yes |
| Implementer (PDF) | pdf-agent | sonnet | Yes |
| Implementer (cross-cutting) | general-purpose | sonnet | Yes |
| Code Reviewer | code-review-agent | opus | No |
| Security Reviewer | security-agent | opus | No |
| Plan Verifier | general-purpose | sonnet | No |
| Fixer | general-purpose | sonnet | Yes |

---

## Phase 5: Project Context (provided to all agents)

```
Source: lib/ (feature-first organization)
Features: auth, calculator, contractors, dashboard, entries, forms,
          gallery, locations, pdf, photos, projects, quantities,
          settings, sync, todos, toolbox, weather
Database: lib/core/database/database_service.dart
Router: lib/core/router/app_router.dart
Theme: lib/core/theme/app_theme.dart

Build commands (MUST use pwsh wrapper):
- Analyze: pwsh -Command "flutter analyze"
- Test: pwsh -Command "flutter test"
- Build APK: pwsh -Command "flutter build apk --debug"
- Run Windows: pwsh -Command "flutter run -d windows" (timeout: 600000)

Conventions: .claude/CLAUDE.md
Defects: .claude/defects/_defects-{feature}.md
Code review agent: .claude/agents/code-review-agent.md
Security agent: .claude/agents/security-agent.md
```

---

## Verification Criteria

- [ ] `/implement <plan-path>` invokes the supervisor
- [ ] Supervisor reads plan, presents phases, asks for confirmation
- [ ] Checkpoint file created at `.claude/state/implement-checkpoint.json`
- [ ] Orchestrator dispatches specialized agents based on file routing table
- [ ] All 6 quality gates execute in order
- [ ] Security gate uses security-agent with modified files scope
- [ ] Checkpoint updated after every phase and every gate
- [ ] HANDOFF works: fresh orchestrator resumes from checkpoint
- [ ] BLOCKED works: supervisor presents issue, asks user for resolution
- [ ] Final summary includes all gate results and file list
- [ ] Supervisor never commits or pushes

---

## Phase 6: Agent System Cleanup

Fixes identified from reviewing all 9 agents, 7 skills, and .claude directory structure.

### 6a. auth-agent.md — Stale Deep Link Scheme

The auth-agent references the **old** package name `com.fvconstruction.construction_inspector` in 3 places (lines 66, 77, 89). The app was renamed to `com.fieldguideapp.inspector`.

**Fix**:
- Line 66: `com.fvconstruction.construction_inspector://login-callback` → `com.fieldguideapp.inspector://login-callback`
- Line 77: `android:scheme="com.fvconstruction.construction_inspector"` → `android:scheme="com.fieldguideapp.inspector"`
- Line 89: `<string>com.fvconstruction.construction_inspector</string>` → `<string>com.fieldguideapp.inspector</string>`
- Line 96 (Supabase Dashboard redirect URL): same fix

### 6b. qa-testing-agent.md — Raw Flutter Commands

Lines 90-111 show raw `flutter analyze`, `flutter test`, `flutter build` commands without the `pwsh -Command` wrapper. Per CLAUDE.md, Git Bash silently fails on Flutter.

**Fix**: Wrap all Flutter commands in `pwsh -Command "..."`:
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
pwsh -Command "flutter test --coverage"
pwsh -Command "flutter test test/path/file.dart"
pwsh -Command "flutter test test/golden/"
pwsh -Command "flutter build windows --release"
pwsh -Command "flutter build apk --release"
```

Also patrol commands should use pwsh.

### 6c. backend-supabase-agent.md — Missing pwsh Wrapper

Lines 88-123 and 163-171 show raw `supabase` and `flutter` CLI commands without pwsh wrappers.

**Fix**: Wrap all commands in `pwsh -Command "..."`.

### 6d. pdf-agent.md — Raw Flutter Commands

Lines 171-179 show raw `flutter run`, `flutter analyze` without pwsh wrapper.

**Fix**: Wrap in `pwsh -Command "..."`.

### 6e. frontend-flutter-specialist-agent.md — Feature Count Mismatch

Line 110 says "13 feature modules" but CLAUDE.md lists 17 features (auth, calculator, contractors, dashboard, entries, forms, gallery, locations, pdf, photos, projects, quantities, settings, sync, todos, toolbox, weather).

**Fix**: Update to "17 feature modules" and list all of them.

### 6f. backend-data-layer-agent.md — "planned" Supabase Sync

Line 62 says "planned Supabase cloud sync" but sync is already implemented and functional.

**Fix**: Change "planned Supabase cloud sync" → "Supabase cloud sync".

### 6g. CLAUDE.md Skills Table — Missing New Entries

The skills table (lines 61-70) needs to include the new `implement` skill.

**Fix**: Add row: `| implement | Autonomous plan execution with quality gates | User-invoked |`

### 6h. planning-agent.md — Missing dispatching-parallel-agents Skill Load

The `skills:` frontmatter lists both `brainstorming` and `dispatching-parallel-agents`, but the "MANDATORY: Load Skills First" section (line 38-42) only mentions reading `brainstorming/SKILL.md`. It does not instruct the agent to also read `dispatching-parallel-agents/SKILL.md`.

**Fix**: Add second skill to the mandatory load section:
```
1. `.claude/skills/brainstorming/SKILL.md` - Collaborative design methodology
2. `.claude/skills/dispatching-parallel-agents/SKILL.md` - Parallel agent coordination
```

### 6i. code-review-agent.md — Raw Verification Commands

Lines 182-183 reference raw `flutter analyze` and `flutter test` without pwsh wrappers.

**Fix**: Wrap in `pwsh -Command "..."`.

### 6j. security-agent.md — Verification Section

The newly created security-agent has no Verification section (unlike code-review-agent which has one). It should not run commands (read-only), but should note that implementation agents handle remediation.

**Fix**: Add a brief verification note stating fixes are delegated via defect files, not performed by this agent.

---

## Phase 7: .claude Directory Cleanup

### 7a. Verify State Files Referenced by Agents Exist

Multiple agents reference these state files in frontmatter:
- `PROJECT-STATE.json`
- `FEATURE-MATRIX.json` (planning-agent only)
- `AGENT-CHECKLIST.json` (planning-agent, code-review-agent, qa-testing-agent)

**Action**: Verify these exist in `.claude/state/`. If missing, create minimal templates so agents don't fail on first read.

### 7b. Agent Memory Files — Consistency Check

Current agent-memory directories:
- `code-review-agent/MEMORY.md`
- `qa-testing-agent/MEMORY.md`
- `pdf-agent/MEMORY.md` + `stage-4c-implementation.md`
- `frontend-flutter-specialist-agent/MEMORY.md`
- `security-agent/MEMORY.md` (just created)

**Missing** agent-memory for:
- `auth-agent`
- `backend-data-layer-agent`
- `backend-supabase-agent`
- `planning-agent`

**Action**: Create empty MEMORY.md stubs for agents that don't have them yet, so the memory system is consistent. Use standard section headers:
```markdown
# {Agent Name} Memory

## Patterns Discovered

## Gotchas & Quirks

## Architectural Decisions

## Frequently Referenced Files
```

---

## Phase 8: Broken References & Documentation Cleanup

### 8a. `shared_rules` Path Ambiguity in ALL Agents

Every agent's `shared_rules` frontmatter lists `architecture.md`, but **no file exists at** `architecture-decisions/architecture.md`. The actual file is at `.claude/rules/architecture.md`.

The `shared_rules` field mixes two namespaces:
- **`architecture-decisions/` namespace** (constraint files that DO exist): `auth-constraints.md`, `data-validation-rules.md`, `sync-constraints.md`, etc.
- **`rules/` namespace** (technical rules that DON'T exist in `architecture-decisions/`): `architecture.md`, `database/schema-patterns.md`, `testing/patrol-testing.md`, `backend/supabase-sql.md`, `sync/sync-patterns.md`, `auth/supabase-auth.md`, `pdf/pdf-generation.md`

**Affected agents** (all 9): Every agent lists `architecture.md` in `shared_rules`.

Additionally these agents reference `rules/` paths in `shared_rules`:
- `backend-data-layer-agent`: `database/schema-patterns.md`
- `qa-testing-agent`: `testing/patrol-testing.md`
- `backend-supabase-agent`: `backend/supabase-sql.md`, `sync/sync-patterns.md`
- `auth-agent`: `auth/supabase-auth.md`
- `pdf-agent`: `pdf/pdf-generation.md`

**Decision needed**: The `shared_rules` field is agent frontmatter that instructs agents to read files. Since agents already have `@` inline references to the `rules/` files (which auto-load), the `shared_rules` entries for rules/ files are either:
1. **Redundant** (already covered by `@` references in the agent body) — remove them from `shared_rules`
2. **Intended to be different files** — create matching constraint files in `architecture-decisions/`

**Recommended fix**: Option 1 — remove `rules/` paths from `shared_rules` (they're already `@`-referenced inline). Keep only `architecture-decisions/` constraint files in `shared_rules`. This makes the naming unambiguous.

### 8b. CLAUDE.md Directory Reference — Missing/Empty Directories

The CLAUDE.md Directory Reference table lists:
- `prds/` — exists, has 14 PRDs
- `hooks/` — exists, has 2 shell scripts
- `test-results/` — exists, has test report files
- `code-reviews/` — exists (will receive security audit reports)

All referenced directories exist. No broken references found here.

### 8c. CLAUDE.md — Stale Backlogged Plans Reference

Line referencing audit system: `.claude/backlogged-plans/2026-02-15-audit-system-design.md` — the file exists. No fix needed.

### 8d. Feature Documentation — Missing Feature Docs

`context_loading` in agents tells them to read `docs/features/feature-{name}-overview.md`. These exist for all 14 features checked. However, features added since the docs were created may be missing:
- `calculator`, `forms`, `gallery`, `todos` — these are sub-features of `toolbox`. They don't have their own state/feature-{name}.json or overview docs.

**Fix**: Either create stub feature docs for `calculator`, `forms`, `gallery`, `todos`, or document in CLAUDE.md that these are sub-features covered by `feature-toolbox-overview.md`.

### 8e. Supabase Schema Reference — v3 vs v4 Ambiguity

`backend-supabase-agent.md` line 149 references `supabase/supabase_schema_v3.sql` as "Current Supabase schema", but there is also `supabase/supabase_schema_v4_rls.sql`. Plus there are migrations in `supabase/migrations/`.

**Fix**: Update the "Files to Reference" table to list:
- `supabase/migrations/` — Migration files (source of truth for production schema)
- `supabase/supabase_schema_v4_rls.sql` — RLS policies (NOTE: contains temporary permissive `anon` policies)
- Remove or mark v3 as "legacy/archived"

### 8f. Missing Feature State Files

Agents reference `state/feature-{name}.json` but only 14 feature JSON files exist:
`auth, contractors, dashboard, entries, locations, pdf, photos, projects, quantities, settings, sync, toolbox, weather`

**Missing**: `calculator`, `forms`, `gallery`, `todos` (sub-features of toolbox)

**Fix**: Same as 8d — either create stubs or document these are covered by `feature-toolbox.json`.

---

## Summary of All Changes

| Phase | Scope | Files |
|-------|-------|-------|
| **1-5** | /implement skill | `.claude/skills/implement/SKILL.md` (new) |
| **6a** | auth-agent stale deep link scheme | `.claude/agents/auth-agent.md` |
| **6b** | qa-testing-agent pwsh wrappers | `.claude/agents/qa-testing-agent.md` |
| **6c** | supabase-agent pwsh wrappers | `.claude/agents/backend-supabase-agent.md` |
| **6d** | pdf-agent pwsh wrappers | `.claude/agents/pdf-agent.md` |
| **6e** | frontend-agent feature count (13→17) | `.claude/agents/frontend-flutter-specialist-agent.md` |
| **6f** | data-layer-agent "planned" → "active" sync | `.claude/agents/backend-data-layer-agent.md` |
| **6g** | CLAUDE.md skills table: add `implement` | `.claude/CLAUDE.md` |
| **6h** | planning-agent missing skill load instruction | `.claude/agents/planning-agent.md` |
| **6i** | code-review-agent pwsh wrappers | `.claude/agents/code-review-agent.md` |
| **6j** | security-agent add verification note | `.claude/agents/security-agent.md` |
| **7a** | State file stubs (verify existence) | `.claude/state/*.json` |
| **7b** | Agent memory stubs (4 missing agents) | `.claude/agent-memory/*/MEMORY.md` |
| **8a** | Fix shared_rules path ambiguity (ALL agents) | All 9 agent `.md` files |
| **8b-8c** | CLAUDE.md directory/backlog refs | Verified OK — no changes |
| **8d** | Toolbox sub-feature doc coverage | `.claude/docs/features/` or `.claude/CLAUDE.md` |
| **8e** | Supabase schema version refs | `.claude/agents/backend-supabase-agent.md` |
| **8f** | Missing sub-feature state files | `.claude/state/` or `.claude/CLAUDE.md` |
