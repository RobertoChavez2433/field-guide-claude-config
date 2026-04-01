---
name: writing-plans
description: "Reads tailor output and writes implementation plans. Main agent writes directly for small/medium plans, splits across plan-writer subagents for large ones. Then runs 3-sweep adversarial reviews with fix loops."
user-invocable: true
---

# Writing Plans

**Announce at start:** "I'm using the writing-plans skill to create an implementation plan."

## Spec as Source of Truth

The spec represents the user's approved intent, scope, and vision. It is the product of collaborative brainstorming and captures decisions the user has explicitly made.

**Reviews verify the plan, not the spec.** Adversarial reviewers should:
- Challenge whether the plan correctly implements the spec's intent
- Find gaps, holes, or better implementation approaches in the plan
- Verify file paths, symbols, and dependencies against actual codebase
- Security reviewer: find security flaws in the planned implementation
- Completeness reviewer: ensure every spec requirement is captured

**Reviews do NOT:**
- Override the spec's scope or goals
- Reject features the user explicitly approved in the spec
- Add requirements not in the spec

## Architecture

```
Main Agent
  ├─ Phase 1: Accept — read spec, find matching tailor output
  ├─ Phase 2: Load tailor output into context
  ├─ Phase 3: Determine writer strategy (direct vs. subagents)
  ├─ Phase 4: Write the plan (main agent or Agent tool subagents)
  ├─ Phase 5: Review loop (3 parallel reviewers, plan-fixer, max 3 cycles)
  └─ Phase 6: Present summary
```

**Prerequisite:** The `/tailor` skill must have been run on the spec first. This skill does NOT do CodeMunch research — it consumes tailor output.

---

## Your Workflow

### Phase 1: Accept

1. User invokes `/writing-plans <spec-path>` (or prompted for path if not provided)
2. Read the spec from `.claude/specs/`
3. Search for matching tailor output in `.claude/tailor/` by date prefix + spec slug
   - Derive spec-slug from filename (e.g., `2026-03-31-quality-gates` from `2026-03-31-quality-gates-spec.md`)
   - Look for `.claude/tailor/YYYY-MM-DD-<spec-slug>/manifest.md`
4. **Hard gate**: If no tailor output found → "No tailor output found. Run `/tailor <spec-path>` first." STOP.
5. Read `manifest.md` to verify tailor output matches the spec path

### Phase 2: Load Tailor Output

Read all tailor directory files in order:

1. `manifest.md` — index, spec reference, summary stats
2. `ground-truth.md` — verified literals table
3. `dependency-graph.md` — what depends on what
4. `blast-radius.md` — what breaks if we change X
5. `patterns/*.md` — all pattern files (architectural patterns + reusable methods)
6. `source-excerpts/by-concern.md` — source organized by spec concern
7. `source-excerpts/by-file.md` — source organized by file path

This replaces the old CodeMunch research + analysis report + context bundle phases entirely. The tailor output IS the context.

### Phase 3: Determine Writer Strategy

Estimate plan size from spec scope + tailor analysis:

- **Under ~2000 lines** → main agent writes the plan directly
- **Over ~2000 lines** → split across plan-writer-agent subagents via Agent tool

For multi-writer splits:
1. Identify natural split points from the dependency graph — phase boundaries where no cross-phase file dependencies exist
2. Assign phase ranges to each writer
3. **Parallel** by default (each writer gets independent phases)
4. **Sequential** only when the dependency graph shows phases that MUST be written in order
5. Writer fragments go to `.claude/plans/parts/`

### Phase 4: Write the Plan

#### Direct (main agent writes)

Write the plan to `.claude/plans/YYYY-MM-DD-<name>.md` following the Plan Format Reference below. Use real code, real paths, real imports from the tailor map throughout. The tailor output gives you everything — patterns show "how we do it", methods give copy-paste-ready signatures, ground truth verifies every literal.

#### Multi-Writer (Agent tool subagents)

Dispatch plan-writer-agent subagents via Agent tool (`subagent_type: plan-writer-agent`, model: opus). Each receives in its prompt:
- `TAILOR_DIR` — absolute path to tailor output directory
- `OUTPUT_PATH` — path to write fragment (under `.claude/plans/parts/<plan-name>-writer-N.md`)
- `PHASE_ASSIGNMENT` — which phases to write
- Plan format template (inline in prompt — paste from Plan Format Reference below)
- Agent routing table (inline in prompt — paste from Agent Routing Table below)

For parallel multi-writer: dispatch ALL writers in a SINGLE message (multiple Agent tool calls).
For sequential multi-writer: dispatch one at a time, wait for completion before next.

After all writers complete:
1. Read all fragments from `.claude/plans/parts/`
2. Concatenate in phase order
3. Add the plan header (from the format template)
4. Structural check:
   - Verify phase numbering is sequential with no gaps
   - Verify no duplicate file paths across phases without reason
   - Verify all phases have agent assignments
   - Fix any merge artifacts (duplicate headers, broken numbering)
5. Write the final plan to `.claude/plans/YYYY-MM-DD-<name>.md`

### Phase 5: Review Loop

Create the review directory: `.claude/plans/review_sweeps/<plan-name>-<date>/`

Dispatch ALL 3 review agents in a SINGLE message via Agent tool:

1. **Code Review** (`subagent_type: code-review-agent`, model: opus):
   - Read the plan at `.claude/plans/YYYY-MM-DD-<name>.md`
   - Read the spec at `.claude/specs/YYYY-MM-DD-<name>-spec.md`
   - Code quality, DRY/KISS, correctness
   - **Ground truth verification**: cross-reference ALL string literals and identifiers in plan code blocks against the actual codebase (routes, keys, columns, method signatures, enum values, file paths)
   - Return APPROVE or REJECT with findings

2. **Security Review** (`subagent_type: security-agent`, model: opus):
   - Read the plan at `.claude/plans/YYYY-MM-DD-<name>.md`
   - Security vulnerabilities, auth gaps, RLS implications, data exposure
   - Return APPROVE or REJECT with findings

3. **Completeness Review** (`subagent_type: completeness-review-agent`, model: opus):
   - Read the plan at `.claude/plans/YYYY-MM-DD-<name>.md`
   - Read the spec at `.claude/specs/YYYY-MM-DD-<name>-spec.md`
   - Read the tailor ground truth at `.claude/tailor/YYYY-MM-DD-<spec-slug>/ground-truth.md`
   - Does the plan fully capture every spec requirement?
   - Flags drift, gaps, lazy shortcuts, missing requirements
   - The spec is sacred — deviations are always findings
   - Return APPROVE or REJECT with findings

Save reports to the review directory with cycle suffix from the start:
- `code-review-cycle-1.md` (subsequent cycles: `code-review-cycle-2.md`, etc.)
- `security-review-cycle-1.md`
- `completeness-review-cycle-1.md`

#### Fix Findings

If ANY reviewer returned findings:

1. Consolidate ALL findings from all 3 reviewers into one list
2. Dispatch `plan-fixer-agent` via Agent tool:
   - `subagent_type: plan-fixer-agent`
   - Provide: plan path, consolidated findings, spec path
   - The fixer addresses ALL findings unless they stray from spec intent
   - Surgical edits only — never rewrites the plan

#### Review/Fix Loop

After the fixer completes:

1. Re-run ALL 3 review sweeps — full re-review, not just the reviews that had findings
2. If findings remain → dispatch fixer again
3. **Max 3 cycles.** If still failing after 3 rounds, escalate to user with:
   - Remaining findings
   - Fix attempts made
   - Recommendation for how to proceed

Save each cycle's reports with the cycle suffix (e.g., `code-review-cycle-2.md`).

### Phase 6: Present Summary

Show the user:
- Plan file path
- Phase count, sub-phase count, step count
- Files affected (direct, dependent, tests, cleanup)
- Agents involved
- Review verdicts (per cycle if multiple)
- Fix cycles completed
- Any unresolved findings (should be zero if passed)

---

## Plan Format Reference

The plan writer (whether you or a subagent) must follow these standards.

### Plan Document Header

Every plan MUST start with this header:

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** [One sentence]
**Spec:** `.claude/specs/YYYY-MM-DD-<name>-spec.md`
**Tailor:** `.claude/tailor/YYYY-MM-DD-<spec-slug>/`

**Architecture:** [2-3 sentences]
**Tech Stack:** [Key technologies]
**Blast Radius:** [N direct, N dependent, N tests, N cleanup]

---
```

### Plan Hierarchy

**Phase** = Major milestone (e.g., "Data Layer", "UI Components", "Integration")
**Sub-phase** = Coherent unit of work within a phase (e.g., "Entry Model", "Repository")
**Step** = Single atomic action (2-5 minutes)

### Step Granularity

Each step is ONE action:
- "Write the failing test for X" — step
- "Run test to verify it fails" — step
- "Implement the minimal code" — step
- "Run test to verify it passes" — step

### Task Structure Template

````markdown
## Phase N: [Milestone Name]

### Sub-phase N.M: [Component Name]

**Files:**
- Create: `exact/path/to/file.dart`
- Modify: `exact/path/to/existing.dart:123-145`
- Test: `test/exact/path/to/test.dart`

**Agent**: [agent-name from routing table]

#### Step N.M.1: Write failing test for [specific behavior]

```dart
// WHY: This test verifies [specific behavior] because [reason]
void main() {
  test('should [expected behavior]', () {
    final sut = ClassName();
    final result = sut.methodName(input);
    expect(result, expectedValue);
  });
}
```

#### Step N.M.2: Verify test fails

Run: `pwsh -Command "flutter test test/exact/path/test.dart"`
Expected: FAIL with "[specific error message]"

#### Step N.M.3: Implement minimal code

```dart
// WHY: [Business reason]
// NOTE: Matches pattern in [reference file]
ReturnType methodName(ParamType param) {
  return computedValue;
}
```

#### Step N.M.4: Verify test passes

Run: `pwsh -Command "flutter test test/exact/path/test.dart"`
Expected: PASS
````

### Agent Routing Table

| File Pattern | Agent |
|-------------|-------|
| `lib/**/presentation/**` | `frontend-flutter-specialist-agent` |
| `lib/**/data/**` | `backend-data-layer-agent` |
| `lib/core/database/**` | `backend-data-layer-agent` |
| `lib/features/auth/**` | `auth-agent` |
| `lib/features/pdf/**` | `pdf-agent` |
| `lib/features/sync/**` | `backend-supabase-agent` |
| `supabase/**` | `backend-supabase-agent` |
| `test/**`, `integration_test/**` | `qa-testing-agent` |
| Multiple domains or `.claude/` config | `general-purpose` |

> `general-purpose` is the built-in Agent tool subagent type, not a `.claude/agents/` file.

### Test Run Rules

**CRITICAL: Plans must NEVER include `flutter test` (full suite) inside sub-phases.** The full test suite runs once per phase at the orchestrator level — not per sub-phase. Including full-suite runs in sub-phase steps causes the implementer to run the entire test suite dozens of times, wasting 10+ minutes per run.

| Allowed in sub-phase steps | NOT allowed in sub-phase steps |
|---------------------------|-------------------------------|
| `flutter test test/specific/file_test.dart` (targeted) | `flutter test` (full suite) |
| `flutter analyze` (fast, seconds) | `flutter test --coverage` |

The last step of the **final sub-phase in each phase** may include `flutter analyze` as a verification gate. The orchestrator handles `flutter test` after each phase completes.

### Phase Ordering Rules

1. **Data layer first** — Models, repositories, datasources before UI
2. **Dependencies before dependents** — If Phase 2 uses Phase 1 output, Phase 1 first
3. **Tests alongside implementation** — Every sub-phase includes targeted test steps (specific test files only)
4. **Cleanup last** — Dead code removal in final phase
5. **Integration phase** — Wire everything together after all features

---

## Code Annotation Standards

Every code block in the plan MUST include annotations where logic isn't self-evident:

```dart
// WHY: [Business reason for this code]
// NOTE: [Pattern choice, references existing convention]
// IMPORTANT: [Non-obvious behavior or gotchas]
// FROM SPEC: [References specific spec requirement]
```

---

## Ground Truth Verification

Ground truth was verified during `/tailor` and is available at `.claude/tailor/*/ground-truth.md`. The code-review-agent double-checks during Phase 5 review sweeps.

**Every string literal in plan code must match the verified ground truth.** Plans that use assumed names instead of real ones will fail at runtime.

| Category | Source of Truth |
|----------|----------------|
| Route paths | `lib/core/router/app_router.dart` |
| Widget keys | `lib/shared/testing_keys/*.dart` |
| DB column names | `lib/core/database/database_service.dart` |
| DB table names | `lib/core/database/database_service.dart` |
| Model field names | `lib/features/**/data/models/*.dart` |
| Provider/service APIs | Actual class method signatures |
| RPC function names | `supabase/migrations/*.sql` |
| Enum values | Model files where enums are defined |
| File paths in code | Glob to confirm existence |

---

## Hard Gate

<HARD-GATE>
Do NOT write the plan (Phase 4) until:
1. Tailor output has been found and loaded (Phases 1-2)
2. Writer strategy has been determined (Phase 3)

Do NOT dispatch reviewers (Phase 5) until the plan file exists at `.claude/plans/`.
</HARD-GATE>

---

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Do This Instead |
|--------------|----------------|-----------------|
| Writing plans without tailor output | Missing codebase context → bad plans | Run `/tailor` first |
| Using headless `claude --agent` for writers | Dead pattern — permission bug | Use Agent tool subagents |
| Dispatching subagents for small plans | Unnecessary overhead, loses context | Main agent writes plans under ~2000 lines directly |
| Vague steps ("add validation") | Implementing agent has to think | Complete code with annotations |
| Missing file paths | Agent guesses wrong | Exact `path/to/file.dart:line` |
| Skipping tests | Breaks TDD cycle | Every sub-phase has test steps |
| Assumed names in plan code | Runtime failures every time | Cross-reference against tailor ground-truth.md |
| Sequential adversarial review | Wastes time | Always dispatch all 3 in parallel |
| Partial re-review after fixes | Misses regressions | Always run ALL 3 sweeps each cycle |
| Telling subagent writers to "read files" | They can read but lack full context | Give them the tailor directory path |
| `flutter test` (full suite) in sub-phase steps | Runs 3600+ tests per sub-phase, 10+ min each | Use targeted `flutter test test/specific_test.dart` only; orchestrator runs full suite per phase |

---

## Remember

- **Tailor output is the prerequisite** — if it doesn't exist, stop and tell user to run `/tailor`
- **Main agent writes small/medium plans directly** — subagents only for 2000+ line plans
- **No headless `claude --agent` in the planning pipeline** — all writers use Agent tool
- **Ground truth verified in tailor, double-checked in code-review sweep**
- **3 full sweeps every cycle** — never partial re-review after fixes
- **Spec is sacred** — completeness reviewer guards user intent; reviews verify the plan, not the spec

## Save Location

Plans: `.claude/plans/YYYY-MM-DD-<feature-name>.md`
Writer fragments: `.claude/plans/parts/<plan-name>-writer-N.md`
Review sweeps: `.claude/plans/review_sweeps/<plan-name>-<date>/`
