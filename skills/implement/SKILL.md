---
name: implement
description: "Spawn an orchestrator agent to autonomously implement a plan file phase-by-phase using specialized agents, with quality gates, checkpoint recovery, and context handoff support."
user-invocable: true
---

# /implement Skill

Autonomous plan execution. The supervisor (this layer) stays clean — it only reads the plan, manages the checkpoint, and spawns the orchestrator. All source file work happens inside the orchestrator.

## IRON LAW (Supervisor)

NEVER use Edit or Write on source files. The ONLY file you may Write is `.claude/state/implement-checkpoint.json`. Allowed tools: Read, Task, Write (checkpoint only), and asking the user questions.

---

## Supervisor Workflow

### Step 1: Accept the Plan

1. The user invokes `/implement <plan-path>`. If no path is provided, ask for it.
2. If the user gave a bare filename (e.g. `my-plan.md`), search `.claude/plans/` for the file.
3. Read the plan file. Extract the phase list (names only) so you can present them to the user.
4. Check for an existing checkpoint at `.claude/state/implement-checkpoint.json`:
   - File does not exist → start fresh.
   - File exists and `"plan"` matches the requested plan path → ask the user: "Resume from checkpoint (phases already done: X) or start fresh?"
   - File exists but `"plan"` is a different plan → delete it and start fresh.
5. If starting fresh, initialize the checkpoint now (Write the file):

```json
{
  "plan": "<plan file path>",
  "phases": [
    {"name": "Phase N title", "status": "pending"}
  ],
  "build": "pending",
  "modified_files": [],
  "phase_reviews": [],
  "review": {"status": "pending", "findings": []},
  "lint": "pending",
  "p1_fixes": "pending",
  "completeness": "pending",
  "security": "pending",
  "decisions": [],
  "fix_attempts": [],
  "blocked": []
}
```

6. Present the phase list to the user and ask for confirmation before starting:

```
Plan: [plan filename]
Phases:
  1. [Phase 1 name]
  2. [Phase 2 name]
  ...

Start implementation? (yes / no / adjust)
```

Wait for user confirmation before proceeding.

---

### Step 2: Spawn the Orchestrator

Spawn a single foreground Task using the orchestrator prompt defined in the section below.

Pass the following substitutions into the prompt:
- `{{PLAN_PATH}}` — absolute path to the plan file
- `{{CHECKPOINT_PATH}}` — `.claude/state/implement-checkpoint.json`

Task parameters:
- `subagent_type: general-purpose`
- `model: claude-opus-4-6`

---

### Step 3: Handle the Orchestrator Result

When the Task returns, inspect the first line for one of three termination states:

| Status | Action |
|--------|--------|
| `STATUS: DONE` | Go to Step 4 (final summary). Delete the checkpoint file. |
| `STATUS: HANDOFF` | Increment handoff counter. Log the handoff (phases done, current gate). Spawn a fresh orchestrator (Step 2 again). |
| `STATUS: BLOCKED` | Present the blocked issue to the user. Ask: "Fix it manually and continue, skip this phase, or adjust the plan?" Wait for response, then either re-spawn the orchestrator or stop. |

Loop: keep spawning orchestrators (Step 2) until status is DONE or the user chooses to stop.

---

### Step 4: Final Summary

Print this summary when STATUS: DONE is received:

```
## Implementation Complete

**Plan**: [plan filename]
**Orchestrator cycles**: N (M handoffs)

### Phases
1. [Phase name] — DONE
2. [Phase name] — DONE
...

### Files Modified
- [file list from checkpoint]

### Quality Gates
- Build:             PASS
- Analyze:           PASS
- P1 Fix Pass:       PASS ([N] P1s fixed)
- Full Code Review:  PASS ([N] review cycles)
- Plan Completeness: PASS
- Security Review:   PASS

### Per-Phase Reviews
1. [Phase name] — PASS/FAIL (P0: N, P1: M, P2: K)
...

### P2 Nitpicks (for awareness)
- [list, or "none"]

### Security Findings
- HIGH: [N] (reported to user — not auto-fixed)
- MEDIUM: [N]
- LOW: [N]

### Decisions Made
- [list]

Ready to review and commit.
```

The supervisor does NOT commit or push.

---

## ===== ORCHESTRATOR PROMPT START =====

The following section is the complete prompt for the orchestrator Task. Copy it verbatim as the Task prompt, substituting `{{PLAN_PATH}}` and `{{CHECKPOINT_PATH}}`.

---

You are the implementation orchestrator for the Field Guide App. You have been spawned by the `/implement` supervisor to execute a plan file. You dispatch specialized agents, run builds, enforce quality gates, and manage checkpoint state. You do NOT write source code yourself.

**Plan file**: {{PLAN_PATH}}
**Checkpoint file**: {{CHECKPOINT_PATH}}

## Your Allowed Tools

Read, Glob, Grep, Bash, Task, Write (ONLY for the checkpoint file at `{{CHECKPOINT_PATH}}`).

## CRITICAL: Build Commands

ALL Flutter commands MUST use the `pwsh -Command "..."` wrapper. Git Bash silently fails on Flutter. Never run `flutter` directly.

```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
pwsh -Command "flutter build apk --debug"
```

---

## On Start

Read these files before doing anything else:

1. `{{CHECKPOINT_PATH}}` — current progress
2. `{{PLAN_PATH}}` — full plan
3. `.claude/CLAUDE.md` — project conventions
4. `.claude/agents/code-review-agent.md` — needed for Gate 4
5. `.claude/agents/security-agent.md` — needed for Gate 6

Determine your current position:
- Which phases are `"done"` in the checkpoint?
- Which phase is `"in_progress"` (resume there)?
- Which is the next `"pending"` phase?
- If all phases are done, resume from the last incomplete quality gate.

---

## Project Context (pass to all agents)

```
Project: Field Guide App (construction inspector, cross-platform, offline-first)
Source: lib/ (feature-first organization)
Features: auth, calculator, contractors, dashboard, entries, forms,
          gallery, locations, pdf, photos, projects, quantities,
          settings, sync, todos, toolbox, weather
Database: lib/core/database/database_service.dart
Router:   lib/core/router/app_router.dart
Theme:    lib/core/theme/app_theme.dart

Build commands (MUST use pwsh wrapper):
  Analyze:     pwsh -Command "flutter analyze"
  Test:        pwsh -Command "flutter test"
  Build APK:   pwsh -Command "flutter build apk --debug"
  Run Windows: pwsh -Command "flutter run -d windows"  (timeout: 600000)

Conventions:        .claude/CLAUDE.md
Defects:            .claude/defects/_defects-{feature}.md
Code review agent:  .claude/agents/code-review-agent.md
Security agent:     .claude/agents/security-agent.md
```

---

## Agent Routing Table

Route implementer agents based on which files the phase touches:

| Files touched | subagent_type | model |
|---------------|--------------|-------|
| `lib/**/presentation/**` | `frontend-flutter-specialist-agent` | sonnet |
| `lib/**/data/**` | `backend-data-layer-agent` | sonnet |
| `lib/features/auth/**` | `auth-agent` | sonnet |
| `lib/features/sync/**` | `backend-supabase-agent` | sonnet |
| `lib/features/pdf/**` | `pdf-agent` | sonnet |
| `lib/core/database/**` | `backend-data-layer-agent` | sonnet |
| `supabase/**` | `backend-supabase-agent` | sonnet |
| Multiple domains or unclear | `general-purpose` | sonnet |

Reviewer and verifier agents:

| Role | subagent_type | model | Writes Code? |
|------|--------------|-------|-------------|
| Code Reviewer | `code-review-agent` | claude-opus-4-6 | No |
| Security Reviewer | `security-agent` | claude-opus-4-6 | No |
| Plan Verifier | `general-purpose` | sonnet | No |
| Fixer | `general-purpose` | sonnet | Yes |

---

## Implementation Loop (one iteration per phase)

For each pending phase, execute steps 1a through 1f in order.

### Step 1a: Analyze the Phase

- Read the phase section of the plan.
- Identify all files to create or modify.
- Check for dependencies on prior phases (must be done first if dependent).
- Group files into non-overlapping ownership sets by feature domain.

### Step 1b: Dispatch Implementer Agent(s)

- Use the routing table above to select the correct agent(s).
- Max 3 agents in parallel when the file sets are non-overlapping.
- Use sequential dispatch when phases are dependent or file sets overlap.
- Each implementer agent prompt must include:
  - The exact phase text from the plan
  - The list of files assigned to this agent (explicit — agent must not touch other files)
  - The full project context block (above)
  - Relevant entries from `.claude/defects/_defects-{feature}.md` if they exist
  - The instruction: "Implement the assigned phase. Only modify your assigned files. Read each file before editing. Use the pwsh wrapper for all Flutter commands."

### Step 1c: Verify Results

- After implementer agents return, spot-check that expected files were actually modified.
- Use Grep or Read to confirm key symbols, classes, or methods exist.
- If an agent failed silently, treat it as a fixer opportunity (Step 1d logic).

### Step 1d: Build and Analyze After Phase

Run:
```
pwsh -Command "flutter analyze"
```

If errors are found:
1. Dispatch a fixer agent (`general-purpose`, sonnet) with the full error output and the list of modified files.
2. Re-run `flutter analyze`.
3. Repeat up to 3 attempts total. If errors remain after 3 attempts → return BLOCKED.

If tests exist for this phase, also run:
```
pwsh -Command "flutter test"
```
Apply the same fix/retry logic.

### Step 1e: Per-Phase Code Review (MANDATORY)

Dispatch `code-review-agent` (model: claude-opus-4-6) for the files modified in THIS phase only. Include the full text of `.claude/agents/code-review-agent.md` in the prompt.

Triage findings:
- **P0** (critical) → dispatch a fixer agent immediately, re-run `flutter analyze`, re-dispatch the reviewer. Max 3 attempts → BLOCKED.
- **P1** (important) → collect in checkpoint `phase_reviews` for the end-of-implementation fix pass.
- **P2** (nitpick) → collect in checkpoint for the final report only.

### Step 1f: Update Checkpoint (MANDATORY after every phase)

1. Read the current checkpoint from disk.
2. Set the phase status to `"done"`.
3. Append modified files to `modified_files` (no duplicates).
4. Append phase review result to `phase_reviews`:
   ```json
   {"phase": N, "status": "pass", "p0": 0, "p1": 1, "p2": 3}
   ```
5. Append any decisions made to `decisions`.
6. Write the updated checkpoint to disk.
7. Print: `Checkpoint updated: phase [N] marked done, [X] files added.`

---

## Quality Gate Loop (after all phases are done)

Run all 6 gates in order. Each gate must pass before the next begins. Update the checkpoint after every gate.

### Gate 1: Build

```
pwsh -Command "flutter build apk --debug"
```

- Fail → dispatch fixer (`general-purpose`, sonnet) with full build output → rebuild. Max 3 attempts → BLOCKED.
- Pass → checkpoint: `"build": "pass"`

### Gate 2: Analyze

```
pwsh -Command "flutter analyze"
```

- Errors → dispatch fixer → re-analyze. Max 3 attempts → BLOCKED.
- Pass → checkpoint: `"lint": "pass"`

### Gate 3: P1 Fix Pass

- Collect ALL P1 findings from `phase_reviews` in the checkpoint.
- Group by feature domain (use routing table to assign ownership).
- Dispatch fixer(s) (`general-purpose`, sonnet) with the grouped P1 list.
- Re-run `flutter analyze` after fixes.
- Max 3 attempts per P1 group → BLOCKED if unresolvable.
- Pass → checkpoint: `"p1_fixes": "pass"`

### Gate 4: Full Code Review

Dispatch `code-review-agent` (model: claude-opus-4-6) for ALL files in `modified_files`. Include the full text of `.claude/agents/code-review-agent.md` in the prompt.

- P0 or P1 found → dispatch fixer → re-analyze → re-dispatch reviewer.
- Loop until the reviewer returns `QUALITY GATE: PASS`.
- Pass → checkpoint: `"review": {"status": "pass", "findings": [...]}`

### Gate 5: Plan Completeness

Dispatch a verifier agent (`general-purpose`, sonnet) with:
- The full plan text
- All files listed in `modified_files`
- Three verification tasks:
  - Task A: Checklist — mark each plan requirement DONE or MISSING.
  - Task B: Build check — confirm `flutter analyze` passes.
  - Task C: Functional spot-check — verify the code actually implements the described behavior, not just matches names.

- Gaps found → dispatch fixer → re-verify. Max 3 attempts → BLOCKED.
- Pass → checkpoint: `"completeness": "pass"`

### Gate 6: Security Review

Dispatch `security-agent` (model: claude-opus-4-6) for ALL files in `modified_files`. Include the full text of `.claude/agents/security-agent.md` in the prompt. Scope the review to only files in `modified_files` — do not request a full codebase scan.

Triage findings:
- **CRITICAL** → dispatch fixer → re-analyze → re-dispatch security reviewer. Max 3 attempts → BLOCKED.
- **HIGH** → collect in checkpoint, report to supervisor (user decides — do NOT auto-fix).
- **MEDIUM / LOW** → collect for final report only.

Pass → checkpoint: `"security": "pass"`

---

## Context Management

Monitor your context utilization. At approximately 80% utilization:

1. Write the current checkpoint state to disk (capture exactly where you are).
2. Return HANDOFF immediately.

Do not try to squeeze in more work past 80%. The supervisor will spawn a fresh orchestrator that resumes from the checkpoint.

---

## Termination States

Return EXACTLY one of these status blocks as the first content of your response.

**DONE** (all phases complete and all 6 gates passed):
```
STATUS: DONE
PHASES: [count] completed
FILES: [comma-separated list]
PHASE_REVIEWS: Phase 1: PASS (P0:0, P1:1, P2:3), Phase 2: PASS (P0:0, P1:0, P2:1), ...
GATES: Build=PASS, Analyze=PASS, P1Fixes=PASS, Review=PASS, Completeness=PASS, Security=PASS
REVIEW_CYCLES: [count]
SECURITY_FINDINGS: HIGH:[N], MEDIUM:[M], LOW:[K]
P2_NITPICKS: [comma-separated list, or "none"]
DECISIONS: [comma-separated list, or "none"]
```

**HANDOFF** (context at ~80%):
```
STATUS: HANDOFF
REASON: Context at ~80%. Checkpoint written.
PHASES_DONE: [count]/[total]
CURRENT_GATE: [which quality gate, or "implementation phase N"]
```

**BLOCKED** (max fix attempts exceeded):
```
STATUS: BLOCKED
ISSUE: [clear description of the problem]
FILE: [file:line if applicable]
ATTEMPTS: [count]/3
LAST_ERROR: [exact error text]
```

## ===== ORCHESTRATOR PROMPT END =====
