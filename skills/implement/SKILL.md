---
name: implement
description: "Execute implementation plans via headless Claude instances with real-time checkpoint visibility and batch-level quality gates."
user-invocable: true
---

# /implement Skill

Execute implementation plans using headless `claude --bare` instances with structured JSON output. The main conversation is a **thin orchestrator** — it dispatches agents, parses their structured output, updates the checkpoint, and reports progress. It never reads plan content or edits source files.

## Architecture

```
Main conversation (thin orchestrator)
  |
  +- Reads plan metadata ONLY (phase names, line ranges) — never reads plan content
  +- Initializes/resumes checkpoint (single file)
  |
  +- FOR EACH PHASE (sequential):
  |     +- Launches implementer (foreground, live visibility)
  |     |     Tools: Read, Edit, Write, Glob, Grep, Bash(pwsh*)
  |     |     Context: worker-rules.md + inline phase prompt
  |     |     Returns: structured JSON via --json-schema (stdout)
  |     |     Includes lint verification before completion
  |     |
  |     +- Orchestrator parses structured output, updates checkpoint
  |     |
  |     +- Launches 3 reviewers (parallel background)
  |     |     completeness: reviewer-rules.md + completeness-review-agent.md
  |     |     code review:  reviewer-rules.md + code-review-agent.md
  |     |     security:     reviewer-rules.md + security-agent.md
  |     |     Returns: structured findings JSON (stdout)
  |     |
  |     +- Orchestrator consolidates findings in context
  |     |     If zero critical+high+medium → PASS
  |     |     If findings increase vs prior round → ESCALATE to user
  |     |
  |     +- If findings: launches fixer (foreground, live visibility)
  |     |     Context: worker-rules.md + code-fixer-agent.md + inline findings
  |     |     Fixes CRITICAL + HIGH + MEDIUM only (skips LOW)
  |     |     Max 3 review/fix cycles
  |     |
  |     +- Low findings logged to checkpoint
  |     +- Updates checkpoint, reports phase complete
  |
  +- Final summary from checkpoint
```

## IRON LAW

The main conversation NEVER edits source files directly. It only writes:
- Checkpoint JSON (`.claude/state/implement-checkpoint.json`)

The orchestrator NEVER reads plan content into its context — agents read the plan themselves via line ranges passed in the inline prompt.

NO files in `.claude/outputs/` — everything flows through stdout via `--json-schema`.

Allowed tools: Read (checkpoint + plan metadata only), Write (checkpoint only), Bash (headless launches only).

NEVER run `flutter clean`. It is prohibited.

---

## Step 1: Accept & Parse Plan

1. User invokes `/implement <plan-path> [phase-numbers]`
2. If bare filename -> search `.claude/plans/` for the file
3. Read plan, extract **metadata only**: phase names and their line ranges (start/end line numbers)
4. Extract spec path from plan header (`**Spec:**` line)
5. Set checkpoint path: `.claude/state/implement-checkpoint.json`
6. Check for existing checkpoint:
   - File does not exist -> start fresh
   - File exists and `"plan"` matches -> ask: "Resume from checkpoint (phases done: X) or start fresh?"
   - File exists but different plan -> delete and start fresh
7. Present phases to user for confirmation:

```
Plan: [plan filename]
Spec: [spec filename]
Phases:
  Phase 1 (lines 10-85) — [name]
  Phase 2 (lines 86-140) — [name]
  ...

Start implementation? (yes / no / adjust)
```

Wait for user confirmation before proceeding.

---

## Step 2: Initialize Checkpoint

If starting fresh, write the checkpoint JSON to `.claude/state/implement-checkpoint.json` following the structure in `reference/checkpoint-template.json`.

Key fields:
- `plan`: absolute path to plan file
- `spec`: absolute path to spec file
- `phases`: object keyed by phase number with status, plan_lines, implementation details, review results, and `low_findings`
- `modified_files`: cumulative list across all phases
- `decisions`: cumulative decisions list
- `blocked`: array of blocked items

---

## Step 3: Phase Execution Loop

Process each phase sequentially. Each phase goes through: implement → review → fix (if needed).

### Step 3a: Launch Implementer (foreground)

Build the headless command per `reference/headless-commands.md` implementer pattern.

Construct the inline `-p` prompt with:
- Phase number
- Plan path + line range (e.g., "Read lines 10-85 of the plan")
- Spec path
- Brief phase name for orientation

**Do NOT read the plan content into the orchestrator's context.** The agent reads it directly.

Run in foreground with `tee` pipeline for live visibility:
```
... 2>&1 | tee >(python3 .claude/tools/stream-filter.py > /dev/tty) | python3 .claude/tools/extract-result.py
```

The `extract-result.py` script outputs ONLY the `structured_output` JSON, which the orchestrator captures and parses.

### Step 3b: Process Implementer Result

1. Parse the structured JSON from stdout (matches implementer schema in `reference/headless-commands.md`)
2. Validate: required fields present, status is `done`/`failed`/`blocked`
3. If `lint_clean` is false -> log warning but proceed to reviews
4. Update checkpoint:
   - Set phase implementation fields
   - Append `files_created` and `files_modified` to checkpoint's `modified_files` (dedup)
   - Record decisions
5. Report to user:
   ```
   Phase N implementation complete.
     Status: done
     Files: 4 created, 2 modified
     Lint: clean
   ```
6. If status is `failed` or `blocked` -> ask user: retry / skip / stop

### Step 3c: Launch Reviewers (parallel background)

Launch 3 reviewer commands per `reference/headless-commands.md` reviewer pattern, all with `run_in_background: true`:

1. **Completeness reviewer** — `reviewer-rules.md` + `completeness-review-agent.md`
2. **Code reviewer** — `reviewer-rules.md` + `code-review-agent.md`
3. **Security reviewer** — `reviewer-rules.md` + `security-agent.md`

Each reviewer's `-p` prompt includes:
- Phase number
- Plan path + line range
- Spec path
- File list from implementer's output (`files_created` + `files_modified`)
- Review type identification

Reviewers use `--output-format json` (not stream-json) since they run in background.

Wait for all 3 to complete. Parse `structured_output` from each result using `jq '.structured_output'` or equivalent.

### Step 3d: Consolidate Findings & Gate

1. Parse all 3 findings JSONs (matches findings schema in `reference/findings-schema.json`)
2. Count blocking findings: critical + high + medium across all reviewers
3. Separate low findings for logging
4. **Approval gate**: If zero blocking findings across all 3 reviewers → PASS
5. **Monotonicity check**: If this is cycle 2+ and blocking findings >= previous cycle's count → ESCALATE
   - Print findings to user, ask: continue / stop / manual fix
6. **Hard cap**: Max 3 review/fix cycles → BLOCKED if still failing
7. Log all LOW findings to checkpoint's `low_findings` array (never fixed, never block)

### Step 3e: Launch Fixer (if needed, foreground)

If blocking findings exist:
1. Consolidate all CRITICAL + HIGH + MEDIUM findings from all 3 reviewers into a single JSON list
2. Build fixer command per `reference/headless-commands.md` fixer pattern
3. Pass consolidated findings as inline JSON in the `-p` prompt
4. Run foreground with `tee` pipeline for live visibility
5. Parse structured fixer output
6. Return to Step 3c (re-review full phase scope, not just fix diff)

### Step 3f: Update Checkpoint

1. Mark phase status as `"done"` (or `"blocked"` if hit cap)
2. Record per-phase review results (finding counts per reviewer, fix cycles)
3. Store low findings in `low_findings` array
4. Write updated checkpoint to disk
5. Report phase complete to user:

```
Phase N complete.
  Completeness: PASS | Code Review: PASS | Security: PASS
  Fix cycles: 1
  Low findings logged: 3
  Files: [list]

Proceeding to Phase N+1...
```

---

## Step 4: Final Summary

After ALL phases complete, print:

```
## Implementation Complete

**Plan**: [plan filename]
**Phases**: N

### Phases
Phase 1 — DONE
  Completeness: PASS | Code Review: PASS | Security: PASS | Fix cycles: N
  Files: [list]
Phase 2 — DONE
  ...

### Files Modified
[deduped list from checkpoint]

### Decisions Made
[from checkpoint]

### Low Findings (logged, not fixed)
[count] across all phases

Ready to review and commit.
```

Read the final checkpoint to populate this summary. The main conversation does NOT commit or push.

---

## Step 5: Error Handling

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Implementer crash | No structured output or malformed JSON | Mark phase failed, ask user |
| Implementer timeout | Bash tool timeout | Use `--max-turns 80` as guardrail |
| Review fix loops | 3 cycles without clean reviews | BLOCKED, show remaining findings to user |
| Findings increase | Monotonicity check fails (cycle N >= cycle N-1) | ESCALATE to user immediately |
| Reviewer crash | No structured output or malformed JSON | Re-run that reviewer only |
| Fixer crash | No structured output or malformed JSON | Re-run fixer with same findings |

---

## Step 6: Troubleshooting

- **`unset CLAUDECODE` not working**: Use `CLAUDECODE= claude --bare ...` instead
- **Empty output from pipeline**: Check that `extract-result.py` received the `result` event
- **Permission denied**: Verify `--permission-mode acceptEdits` + `--allowedTools` covers needed tools
- **Rate limits**: Headless retries automatically. If persistent, wait between phases.
- **Structured output missing**: Agent may have hit max-turns before producing output. Check stream for truncation.
- **`tee` redirection not working**: Ensure using bash (not cmd/powershell) for the pipeline

---

## Reference Files

| File | Purpose |
|------|---------|
| `reference/worker-rules.md` | Static rules for implementers + fixers (appended via --append-system-prompt-file) |
| `reference/reviewer-rules.md` | Static rules for all 3 reviewer types (appended via --append-system-prompt-file) |
| `reference/headless-commands.md` | Exact CLI command patterns with --bare, --json-schema |
| `reference/checkpoint-template.json` | Checkpoint structure (single source of truth) |
| `reference/findings-schema.json` | JSON schema for --json-schema validation (all reviewer types) |
| `reference/severity-standard.md` | Severity definitions and verdict rules |
