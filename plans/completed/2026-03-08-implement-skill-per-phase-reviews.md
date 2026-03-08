# Plan: Implement Skill — Per-Phase Reviews Rewrite

**Date**: 2026-03-08
**Target**: `.claude/skills/implement/SKILL.md`
**Scope**: Rewrite the implement skill to add per-phase completeness, code review, and security reviews with hard gating, plus simplify end-of-pipeline gates.

---

## Motivation

1. **Catch issues earlier** — Bugs found at end-of-pipeline are expensive; later phases build on flawed code.
2. **Reduce end-of-pipeline cost** — Reviewing ALL files at once is token-expensive and overwhelming.
3. **Prevent wiring gaps** — Historical defects show completeness issues (method defined but never called, adapter not registered) that slip through.
4. **Enforce testing per-phase** — Tests are being deferred despite plans calling for them. No more deferral.

---

## Design Decisions (from brainstorming)

| Decision | Choice |
|----------|--------|
| Per-phase security scope | Phase files + their dependencies/imports |
| Completeness depth | Full functional spot-check (checklist + tests + wiring + behavior) |
| End-of-pipeline gates | Keep as final integration pass (3 gates, down from 6) |
| Gating strictness | Hard gate — fix ALL findings (CRITICAL through LOW) before advancing |
| Per-phase review order | Completeness first → code + security in parallel → merge → fix |
| Max retries | 3 cycles per review stage |
| Severity standard | CRITICAL/HIGH/MEDIUM/LOW across all three reviewers |
| Plan fidelity | Plans done to a T. Nothing extra, nothing omitted. Verified functionally. |
| Testing | Mandatory per-phase (flutter test always runs, not "if tests exist") |

### Model Allocation

| Role | Agent Type | Model | Writes Code |
|------|-----------|-------|-------------|
| Implementer | Routed specialist | Sonnet | Yes |
| Per-phase Completeness | general-purpose | Sonnet | No |
| Per-phase Code Review | code-review-agent | Opus | No |
| Per-phase Security | security-agent | Opus | No |
| Fixer (all stages) | general-purpose | Sonnet | Yes |
| Integration Completeness | general-purpose | Opus | No |
| Integration Code Review | code-review-agent | Opus | No |
| Integration Security | security-agent | Opus | No |

---

## Phase 0: Update Checkpoint Schema

**File**: `.claude/skills/implement/SKILL.md` — Supervisor Step 1, item 5

Replace the checkpoint initialization JSON with:

```json
{
  "plan": "<plan file path>",
  "phases": [
    {
      "name": "Phase N title",
      "status": "pending",
      "reviews": {
        "completeness": {
          "status": "pending",
          "critical": 0, "high": 0, "medium": 0, "low": 0,
          "tests_verified": false,
          "fix_cycles": 0
        },
        "code_review": {
          "status": "pending",
          "critical": 0, "high": 0, "medium": 0, "low": 0,
          "fix_cycles": 0
        },
        "security": {
          "status": "pending",
          "critical": 0, "high": 0, "medium": 0, "low": 0,
          "fix_cycles": 0
        }
      }
    }
  ],
  "modified_files": [],
  "build": "pending",
  "analyze_and_test": "pending",
  "integration_reviews": {
    "completeness": {"status": "pending", "critical": 0, "high": 0, "medium": 0, "low": 0, "fix_cycles": 0},
    "code_review": {"status": "pending", "critical": 0, "high": 0, "medium": 0, "low": 0, "fix_cycles": 0},
    "security": {"status": "pending", "critical": 0, "high": 0, "medium": 0, "low": 0, "fix_cycles": 0}
  },
  "decisions": [],
  "fix_attempts": [],
  "blocked": []
}
```

**Removed fields**: `phase_reviews`, `review`, `lint`, `p1_fixes`, `completeness`, `security` (all replaced by the new structure).

---

## Phase 1: Update Supervisor Final Summary

**File**: `.claude/skills/implement/SKILL.md` — Supervisor Step 4

Replace the final summary template with:

```
## Implementation Complete

**Plan**: [plan filename]
**Orchestrator cycles**: N (M handoffs)

### Phases
1. [Phase name] — DONE
   - Completeness: PASS (C:0, H:0, M:0, L:0) | Tests verified
   - Code Review:  PASS (C:0, H:0, M:0, L:0)
   - Security:     PASS (C:0, H:0, M:0, L:0)
   - Fix cycles: N
2. [Phase name] — DONE
   ...

### Files Modified
- [file list from checkpoint]

### Integration Gates
- Build:              PASS
- Analyze + Test:     PASS
- Integration Reviews:
  - Completeness: PASS (C:0, H:0, M:0, L:0)
  - Code Review:  PASS (C:0, H:0, M:0, L:0)
  - Security:     PASS (C:0, H:0, M:0, L:0)

### Decisions Made
- [list]

Ready to review and commit.
```

---

## Phase 2: Update Orchestrator — Severity Standard

**File**: `.claude/skills/implement/SKILL.md` — Orchestrator prompt section

Add a new section after "Agent Routing Table" called "Severity Standard":

```
## Severity Standard

ALL reviewers (completeness, code review, security) report findings using this unified format:

  CRITICAL  — Blocks pipeline. Breaks functionality, security vulnerability,
              or plan requirement completely missing.
  HIGH      — Significant issue. Wrong behavior, missing tests, weak security,
              incomplete wiring.
  MEDIUM    — Quality issue. Suboptimal pattern, missing edge case handling,
              could be better.
  LOW       — Nitpick. Style, naming, minor improvement opportunity.

ALL severity levels get fixed. No deferrals. A phase cannot advance until all
findings from all three reviewers are resolved.

Finding format (returned by each reviewer):
  severity: CRITICAL|HIGH|MEDIUM|LOW
  category: completeness|code-quality|security
  file: <path>
  line: <number>
  finding: <description>
  fix_guidance: <how to fix>
```

Update the reviewer agent table to replace old P0/P1/P2 references:

```
| Role | subagent_type | model | Writes Code? |
|------|--------------|-------|-------------|
| Completeness Reviewer (per-phase) | `general-purpose` | sonnet | No |
| Code Reviewer (per-phase) | `code-review-agent` | claude-opus-4-6 | No |
| Security Reviewer (per-phase) | `security-agent` | claude-opus-4-6 | No |
| Completeness Reviewer (integration) | `general-purpose` | claude-opus-4-6 | No |
| Code Reviewer (integration) | `code-review-agent` | claude-opus-4-6 | No |
| Security Reviewer (integration) | `security-agent` | claude-opus-4-6 | No |
| Fixer | `general-purpose` | sonnet | Yes |
```

---

## Phase 3: Rewrite Implementation Loop (Steps 1a-1g)

**File**: `.claude/skills/implement/SKILL.md` — Orchestrator "Implementation Loop" section

Replace the entire "Implementation Loop" section with:

```
## Implementation Loop (one iteration per phase)

For each pending phase, execute steps 1a through 1g in order.

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
  - The instruction: "Implement the assigned phase exactly as written. Do not add anything
    beyond what the plan specifies. Do not omit anything the plan requires. Only modify your
    assigned files. Read each file before editing. Use the pwsh wrapper for all Flutter commands.
    If the plan specifies tests for this phase, you MUST write them — do not defer testing."

### Step 1c: Verify Results

- After implementer agents return, spot-check that expected files were actually modified.
- Use Grep or Read to confirm key symbols, classes, or methods exist.
- If an agent failed silently, treat it as a fixer opportunity (Step 1d logic).

### Step 1d: Build + Analyze + Test (MANDATORY)

Run both commands in sequence:
```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
```

Both are MANDATORY — never skip `flutter test`. If errors are found in either:
1. Dispatch a fixer agent (`general-purpose`, sonnet) with the full error output and the list of modified files.
2. Re-run both commands.
3. Repeat up to 3 attempts total. If errors remain after 3 attempts → return BLOCKED.

### Step 1e: Per-Phase Completeness Review (MANDATORY)

Dispatch a completeness reviewer (`general-purpose`, sonnet) with:
- The exact phase text from the plan (every requirement)
- The list of files modified in this phase
- The full project context block

The completeness reviewer must verify ALL of the following:
1. **Plan checklist**: Every requirement in the phase text is DONE or MISSING. Nothing extra was added beyond what the plan specifies.
2. **Test verification**: If the plan specifies tests for this phase, confirm they were actually written and are meaningful (not stubs or empty tests). If the plan does not mention tests, flag this as a finding — every phase should have tests.
3. **Wiring check**: New code is actually connected to the app (registered in providers, added to routes, called from the right entry points). A method that exists but is never called is MISSING.
4. **Functional spot-check**: Read the actual implementation and verify it does what the plan describes. Do not just match names — verify behavior.

Report findings using the severity standard (CRITICAL/HIGH/MEDIUM/LOW).

If ANY findings exist:
1. Dispatch a fixer agent (`general-purpose`, sonnet) with ALL findings and fix guidance.
2. Re-dispatch the completeness reviewer.
3. Repeat up to 3 attempts total. If findings remain after 3 attempts → return BLOCKED.

### Step 1f: Per-Phase Code Review + Security Review (MANDATORY)

After completeness passes, dispatch BOTH reviewers in parallel:

**Code Review**: Dispatch `code-review-agent` (model: claude-opus-4-6) for the files modified in this phase. Include the full text of `.claude/agents/code-review-agent.md` in the prompt. Instruct it to report findings using the severity standard (CRITICAL/HIGH/MEDIUM/LOW).

**Security Review**: Dispatch `security-agent` (model: claude-opus-4-6) for the files modified in this phase PLUS their direct imports/dependencies. Include the full text of `.claude/agents/security-agent.md` in the prompt. Instruct it to report findings using the severity standard (CRITICAL/HIGH/MEDIUM/LOW).

Merge findings from both reviewers into a single list.

If ANY findings exist:
1. Dispatch a fixer agent (`general-purpose`, sonnet) with ALL merged findings and fix guidance.
2. Re-run `flutter analyze` and `flutter test` after fixes.
3. Re-dispatch BOTH reviewers.
4. Repeat up to 3 attempts total. If findings remain after 3 attempts → return BLOCKED.

### Step 1g: Update Checkpoint (MANDATORY after every phase)

1. Read the current checkpoint from disk.
2. Set the phase status to `"done"`.
3. Populate the phase's `reviews` object with results from all three reviewers:
   ```json
   {
     "completeness": {"status": "pass", "critical": 0, "high": 0, "medium": 0, "low": 0, "tests_verified": true, "fix_cycles": 1},
     "code_review": {"status": "pass", "critical": 0, "high": 0, "medium": 0, "low": 0, "fix_cycles": 0},
     "security": {"status": "pass", "critical": 0, "high": 0, "medium": 0, "low": 0, "fix_cycles": 0}
   }
   ```
4. Append modified files to `modified_files` (no duplicates).
5. Append any decisions made to `decisions`.
6. Write the updated checkpoint to disk.
7. Print: `Checkpoint updated: phase [N] marked done, [X] files added. Reviews: completeness=PASS, code=PASS, security=PASS.`
```

---

## Phase 4: Rewrite Quality Gate Loop

**File**: `.claude/skills/implement/SKILL.md` — Orchestrator "Quality Gate Loop" section

Replace the entire "Quality Gate Loop" section with:

```
## Quality Gate Loop (after all phases are done)

Run all 3 gates in order. Each gate must pass before the next begins. Update the checkpoint after every gate.

### Gate 1: Build

```
pwsh -Command "flutter build apk --debug"
```

- Fail → dispatch fixer (`general-purpose`, sonnet) with full build output → rebuild. Max 3 attempts → BLOCKED.
- Pass → checkpoint: `"build": "pass"`

### Gate 2: Analyze + Test

```
pwsh -Command "flutter analyze"
pwsh -Command "flutter test"
```

Run the full test suite against all changes. Both must pass.

- Errors → dispatch fixer → re-run both. Max 3 attempts → BLOCKED.
- Pass → checkpoint: `"analyze_and_test": "pass"`

### Gate 3: Integration Reviews

This is the final safety net. All three reviewers run at Opus on the FULL changeset, looking for cross-phase issues that per-phase reviews cannot catch.

**Order**: Completeness first → Code Review + Security Review in parallel.

**Integration Completeness** (model: claude-opus-4-6):
Dispatch a completeness reviewer (`general-purpose`, claude-opus-4-6) with:
- The FULL plan text (all phases)
- ALL files in `modified_files`
- Instruction: "Verify the entire plan was implemented to the letter. Nothing extra was added. Nothing was omitted. All tests are present and meaningful. All new code is wired into the app. Verify behavior, not just names."

If findings exist → dispatch fixer → re-verify. Max 3 attempts → BLOCKED.
Pass → checkpoint: `integration_reviews.completeness.status = "pass"`

**Integration Code Review** (model: claude-opus-4-6):
Dispatch `code-review-agent` for ALL files in `modified_files`. Focus on cross-phase concerns:
- DRY/KISS violations across phases (repeated logic, duplicated patterns)
- Architectural consistency (do phases work together coherently?)
- Integration patterns (data flow between components from different phases)

**Integration Security Review** (model: claude-opus-4-6):
Dispatch `security-agent` for ALL files in `modified_files` plus their dependencies. Focus on:
- Cross-phase auth/data flow (does Phase 3's endpoint respect Phase 1's auth?)
- Full OWASP scorecard
- Cumulative attack surface

Run code review and security review in parallel. Merge findings.

If ANY findings exist:
1. Dispatch fixer (`general-purpose`, sonnet) with ALL findings.
2. Re-run `flutter analyze` and `flutter test`.
3. Re-dispatch both reviewers.
4. Max 3 attempts → BLOCKED.

Pass → checkpoint: `integration_reviews.code_review.status = "pass"`, `integration_reviews.security.status = "pass"`
```

---

## Phase 5: Update Termination States

**File**: `.claude/skills/implement/SKILL.md` — Orchestrator "Termination States" section

Replace DONE status block with:

```
STATUS: DONE
PHASES: [count] completed
FILES: [comma-separated list]
PER_PHASE_REVIEWS:
  Phase 1: completeness=PASS(C:0,H:0,M:0,L:0) code=PASS(C:0,H:0,M:0,L:0) security=PASS(C:0,H:0,M:0,L:0) fix_cycles:N
  Phase 2: ...
GATES: Build=PASS, AnalyzeTest=PASS, IntegrationCompleteness=PASS, IntegrationCode=PASS, IntegrationSecurity=PASS
TOTAL_FIX_CYCLES: [count]
DECISIONS: [comma-separated list, or "none"]
```

Replace HANDOFF status block with:

```
STATUS: HANDOFF
REASON: Context at ~80%. Checkpoint written.
PHASES_DONE: [count]/[total]
CURRENT_POSITION: [which step/gate, e.g., "Phase 3 Step 1f (code+security review)" or "Gate 3 (integration reviews)"]
```

BLOCKED status block remains unchanged.

---

## Phase 6: Update On Start Section

**File**: `.claude/skills/implement/SKILL.md` — Orchestrator "On Start" section

Update the file list to read:

```
1. `{{CHECKPOINT_PATH}}` — current progress
2. `{{PLAN_PATH}}` — full plan
3. `.claude/CLAUDE.md` — project conventions
4. `.claude/agents/code-review-agent.md` — needed for per-phase and integration code review
5. `.claude/agents/security-agent.md` — needed for per-phase and integration security review
```

Update position determination to account for the new per-phase review steps:

```
Determine your current position:
- Which phases are `"done"` in the checkpoint? (all three reviews must be "pass")
- Which phase is `"in_progress"` (resume there)?
  - Check which review step the phase is on: did completeness pass? did code+security pass?
  - Resume from the first incomplete review step.
- Which is the next `"pending"` phase?
- If all phases are done, resume from the last incomplete integration gate.
```

---

## Verification Criteria

After all phases are implemented, the updated SKILL.md must satisfy:

1. Checkpoint schema has per-phase `reviews` object with all three reviewer types
2. `flutter test` is mandatory in Step 1d (not conditional)
3. Step 1e is completeness review (Sonnet) with plan checklist + tests + wiring + functional spot-check
4. Step 1f is code review (Opus) + security review (Opus) in parallel
5. All findings at all severity levels are fixed before advancing (no deferrals)
6. End-of-pipeline has 3 gates (Build, Analyze+Test, Integration Reviews)
7. Old Gate 3 (P1 Fix Pass) is removed
8. Integration reviews use Opus for all three reviewers
9. Integration reviews follow completeness-first → code+security parallel order
10. Severity standard (CRITICAL/HIGH/MEDIUM/LOW) is documented in the orchestrator prompt
11. Termination states reflect the new review structure
12. Final summary template shows per-phase review breakdown
13. No references to P0/P1/P2 remain anywhere in the file
14. No references to old `phase_reviews`, `lint`, `p1_fixes`, `review`, `completeness`, `security` top-level checkpoint fields
