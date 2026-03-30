---
name: implement
description: "Spawn an orchestrator agent to autonomously implement a plan file phase-by-phase using specialized agents, with quality gates, checkpoint recovery, and context handoff support."
user-invocable: true
---

# /implement Skill

Autonomous plan execution via `claude --agent implement-orchestrator`. The supervisor (this conversation) controls the **phase loop** — launching one orchestrator per phase (or phase group), verifying checkpoint progress between launches.

## Architecture

```
This conversation (supervisor)
  │
  ├─ Reads plan, builds phase dispatch list
  ├─ Initializes checkpoint JSON
  ├─ FOR EACH dispatch group:
  │     ├─ Launches: claude --agent implement-orchestrator --print (via Bash)
  │     │     └─ Orchestrator does: implement → build → reviews → fix → checkpoint
  │     ├─ Reads checkpoint to verify phase(s) marked done + reviews passed
  │     ├─ Reports progress to user
  │     └─ Handles: DONE → next group, HANDOFF → re-launch same group, BLOCKED → user prompt
  └─ Final summary when all groups complete
```

The orchestrator runs as a **separate main-thread CLI process** (not a subagent). This gives it:
- Agent tool access (can dispatch implementers, reviewers, fixers)
- Its own context window (doesn't consume ours)
- Behavioral self-restriction from its system prompt (won't use Edit/Write/Bash directly)
- `permissionMode: bypassPermissions` (no interactive prompts)

---

## IRON LAW (Supervisor)

NEVER use Edit or Write on source files. The ONLY file you may Write is `.claude/state/implement-checkpoint.json`. Allowed tools: Read, Write (checkpoint only), Bash (orchestrator launch only), and asking the user questions.

NEVER run `flutter clean`. It is prohibited.

---

## Supervisor Workflow

### Step 1: Accept the Plan

1. The user invokes `/implement <plan-path>`. If no path is provided, ask for it.
2. If the user gave a bare filename (e.g. `my-plan.md`), search `.claude/plans/` for the file.
3. Read the plan file. Extract the phase list (names only) so you can present them to the user.
4. **Build dispatch groups**: By default, each phase is its own dispatch group. However, lightweight phases (verification-only, run-a-command phases) can be grouped together. Present the grouping to the user for approval.
5. Check for an existing checkpoint at `.claude/state/implement-checkpoint.json`:
   - File does not exist → start fresh.
   - File exists and `"plan"` matches the requested plan path → ask the user: "Resume from checkpoint (phases already done: X) or start fresh?"
   - File exists but `"plan"` is a different plan → delete it and start fresh.
6. If starting fresh, initialize the checkpoint now (Write the file):

```json
{
  "plan": "<plan file path>",
  "dispatch_groups": [
    {"phases": [1], "status": "pending", "test_gate": "pending"},
    {"phases": [2], "status": "pending", "test_gate": "pending"},
    {"phases": [3, 4, 5, 6], "status": "pending", "test_gate": "pending"}
  ],
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

7. Present the plan with dispatch groups and ask for confirmation:

```
Plan: [plan filename]
Dispatch Groups:
  Group 1: Phase 1 — [Phase 1 name]
  Group 2: Phase 2 — [Phase 2 name]
  Group 3: Phases 3-6 — [Phase 3 name], [Phase 4 name], ...

Start implementation? (yes / no / adjust)
```

Wait for user confirmation before proceeding.

---

### Step 2: Phase Loop (Supervisor-Controlled)

The supervisor iterates over dispatch groups sequentially. For each group:

#### 2a: Launch the Orchestrator

Build the phase-specific prompt. The key difference from the old approach: the orchestrator is told to execute **ONLY the specified phases**, then return.

```bash
unset CLAUDECODE && claude --agent implement-orchestrator --print --output-format text "Execute ONLY the specified phases of the implementation plan, then return.

PLAN_PATH: <absolute path to plan file>
CHECKPOINT_PATH: <absolute path to checkpoint JSON>
PHASES_TO_EXECUTE: <comma-separated phase numbers, e.g. '1' or '3,4,5,6'>

Read the plan and checkpoint. Implement ONLY the listed phases following your Implementation Loop. For each phase: dispatch implementer, run build, run reviews, fix issues, update checkpoint. Do NOT proceed to phases not in PHASES_TO_EXECUTE. When all listed phases are done, return STATUS: DONE. If context runs low, return STATUS: HANDOFF with current progress." 2>&1 | tee .claude/outputs/implement-orchestrator-output.txt
```

**Launch parameters:**
- `unset CLAUDECODE` — bypasses nested-session protection
- `--print` — non-interactive headless mode
- `--output-format text` — plain text output (parseable)
- `| tee .claude/outputs/implement-orchestrator-output.txt` — capture output to file AND display
- `run_in_background: true` — always run as background task (no timeout limit)

After launching, tell the user:
```
Group N launched (Phases X-Y). Running in background.
```

#### 2b: Wait for Completion

Wait for the background task to complete. Once done, read the output file.

#### 2c: Verify Checkpoint

After the orchestrator returns, **always read the checkpoint file** to verify:
- Each phase in the group has `"status": "done"`
- All review statuses show `"pass"` (or have findings addressed)
- `modified_files` has been updated

This is the **trust-but-verify** step that prevents fabricated stats.

#### 2c-test: End-of-Group Test Gate

After checkpoint verification passes, run the full test suite ONCE for the group:

1. Launch a qa-testing-agent via:
   ```bash
   unset CLAUDECODE && claude --agent qa-testing-agent --print --output-format text "Run the full Flutter test suite. Command: pwsh -Command \"flutter test\". Return the full output. NEVER run flutter clean."
   ```
   with `run_in_background: true`
2. If all tests pass → update checkpoint: set `dispatch_groups[N].test_gate = "pass"` → proceed to 2d
3. If tests fail → launch a general-purpose fixer agent with:
   - The test failure output
   - The list of ALL files modified in this group (from `checkpoint.modified_files`)
   - "Fix the failing tests. Run `pwsh -Command 'flutter analyze'` after fixing to verify no regressions. NEVER run flutter clean."
4. Re-run tests. Max 3 cycles.
5. If still failing after 3 cycles → present to user as BLOCKED with test output

Skip the test gate if no files were modified in this group (checkpoint.modified_files unchanged from before the group started).

#### 2d: Handle Result

| Status | Action |
|--------|--------|
| `STATUS: DONE` + checkpoint verified | Report to user, advance to next dispatch group. |
| `STATUS: DONE` but checkpoint NOT updated | The orchestrator lied. Report to user, ask how to proceed. |
| `STATUS: HANDOFF` | Re-launch the same group (orchestrator will resume from checkpoint). |
| `STATUS: BLOCKED` | Present the blocked issue to the user. Ask: "Fix it manually and continue, skip this phase, or adjust the plan?" |

**Handoff loop**: keep re-launching the same group until it completes or the user stops.

#### 2e: Report Progress

After each group completes, report to the user:

```
Group N complete (Phases X-Y).
  Phase X: DONE — Reviews: completeness=PASS, code=PASS, security=PASS
  Phase Y: DONE — Reviews: completeness=PASS, code=PASS, security=PASS
  Test gate: PASS
  Files modified: [list]

Proceeding to Group N+1...
```

---

### Step 3: Final Summary

After ALL dispatch groups complete, print this summary:

```
## Implementation Complete

**Plan**: [plan filename]
**Orchestrator launches**: N (M handoffs)
**Total test runs**: N (1 per group + retries)

### Phases
1. [Phase name] — DONE
   - Completeness: PASS (C:0, H:0, M:0, L:0) | Tests verified
   - Code Review:  PASS (C:0, H:0, M:0, L:0)
   - Security:     PASS (C:0, H:0, M:0, L:0)
   - Fix cycles: N
2. [Phase name] — DONE
   ...

### Groups
- Group 1 (Phases X): Test gate PASS
- Group 2 (Phases X-Y): Test gate PASS (1 retry)
- ...

### Files Modified
- [file list from checkpoint]

### Decisions Made
- [list]

Ready to review and commit.
```

Read the final checkpoint to populate this summary. The supervisor does NOT commit or push.

---

## Troubleshooting

### Orchestrator runs phases outside its assigned group
The orchestrator's prompt says "ONLY the listed phases." If it ignores this, strengthen the instruction in the prompt or add a checkpoint verification that rejects work on unassigned phases.

### Orchestrator uses Edit/Write directly instead of dispatching
The orchestrator's system prompt behaviorally restricts it to Read/Glob/Grep/Agent. If it violates this, the agent file at `.claude/agents/implement-orchestrator.md` needs prompt strengthening.

### Orchestrator can't find agents
Custom agents must exist in `.claude/agents/`. Verify the files exist with Glob.

### Output file empty
Check that `unset CLAUDECODE` is included in the Bash command. Without it, the nested session check blocks the launch.

### Checkpoint not updated (fabrication detection)
If the orchestrator returns DONE but checkpoint phases are still "pending", the orchestrator skipped checkpoint writes. Report this to the user immediately. Do NOT proceed to the next group.

### Timeout
A single phase can take 30-60 minutes (implement + build + reviews + fix cycles). **Always use `run_in_background: true`** for the Bash call — background tasks have no timeout. Each dispatch group gets its own launch, so context exhaustion within a single group is rare.
