---
name: writing-plans
description: "Use when you have an approved spec for a multi-step task, before touching code. Main agent gathers context via CodeMunch + MCP tools, then hands off to a plan-writer agent, then dispatches parallel adversarial reviews."
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

**Reviews do NOT:**
- Override the spec's scope or goals
- Reject features the user explicitly approved in the spec
- Add requirements not in the spec

## Architecture

Subagents CANNOT use MCP tools or spawn sub-subagents. Therefore the main agent (you) drives the entire workflow, delegating only the plan-writing and adversarial reviews to subagents.

```
Main Agent (you)
  ├─ Phase 1: Read spec + Index codebase (CodeMunch MCP — only you have access)
  ├─ Phase 2: Build dependency graph + blast radius (CodeMunch MCP)
  ├─ Phase 3: Save dependency graph to disk
  ├─ Phase 4: Spawn plan-writer agent (Agent tool, model: opus)
  │     └─ Reads dependency graph + spec from disk, writes the plan
  ├─ Phase 5: Adversarial review (dispatch 2 agents in PARALLEL)
  │     ├─ code-review-agent (Agent tool)
  │     └─ security-agent (Agent tool)
  ├─ Phase 6: Address findings (edit plan inline or re-spawn plan-writer)
  └─ Phase 7: Present summary to user
```

## Your Workflow

### Phase 1: Read Spec + Index Codebase

Do these in PARALLEL (you have MCP access):

1. Read the spec file from `.claude/specs/`
2. Read the adversarial review if it exists (from `.claude/adversarial_reviews/`)
3. Run `mcp__jcodemunch__index_folder` on the project root with `incremental: true`, `use_ai_summaries: false`

Once indexing completes:
4. Run `mcp__jcodemunch__get_repo_outline`

### Phase 2: Build Dependency Graph + Blast Radius

Using CodeMunch (only you have MCP access):

1. `mcp__jcodemunch__get_file_outline` on every file listed in "Files to Modify" in the spec
2. `mcp__jcodemunch__search_symbols` for every key symbol mentioned in the spec
3. `mcp__jcodemunch__get_symbol` to read full source of each relevant symbol
4. For each symbol found, trace callers/callees 2+ levels deep using `search_symbols`
5. Categorize all affected symbols: DIRECT | DEPENDENT | TEST | CLEANUP

### Phase 3: Save Dependency Graph

Write the analysis to `.claude/dependency_graphs/YYYY-MM-DD-<name>/analysis.md` with:
- Direct changes (files, symbols, line ranges, change type)
- Dependent files (callers, consumers — 2+ levels)
- Test files that exercise affected code
- Dead code to clean up after rewrite
- Data flow diagram (ASCII)
- Blast radius summary counts

### Phase 4: Spawn Plan-Writer Agent

Spawn a single agent via Agent tool:
- `subagent_type: general-purpose`
- `model: opus`

The plan-writer has NO MCP access, so pass ALL context it needs in the prompt:
- Full spec content (paste it — the agent can't read MCP-indexed data)
- Full adversarial review content
- Full dependency graph analysis content
- Key source excerpts it needs (symbol sources from Phase 2)
- The plan format template (see below)
- The agent routing table
- Save location: `.claude/plans/YYYY-MM-DD-<name>.md`

The plan-writer's ONLY job is to write the plan file using Write tool. It does NOT need to explore the codebase — you already did that.

### Phase 5: Adversarial Review (dispatch 2 agents in PARALLEL)

After the plan-writer returns, spawn BOTH review agents in a SINGLE message:

1. **code-review-agent** (subagent_type: code-review-agent):
   - Read the plan at `.claude/plans/YYYY-MM-DD-<name>.md`
   - Read the spec at `.claude/specs/YYYY-MM-DD-<name>-spec.md`
   - Does the plan cover EVERY spec requirement?
   - Are file paths correct? DRY/YAGNI? Test quality?
   - What's missing? What if a step fails?
   - Return APPROVE or REJECT with specific findings.

2. **security-agent** (subagent_type: security-agent):
   - Read the plan at `.claude/plans/YYYY-MM-DD-<name>.md`
   - Security vulnerabilities? Auth gaps? RLS implications? Data exposure?
   - Return APPROVE or REJECT with findings.

### Phase 6: Address Findings

- CRITICAL/HIGH: Fix in the plan (edit inline or re-spawn plan-writer)
- MEDIUM/LOW: Note in plan, address during implementation
- Save review reports to `.claude/code-reviews/YYYY-MM-DD-<name>-plan-review.md`

### Phase 7: Present Summary

Show the user:
- Plan file path
- Phase count, sub-phase count, step count
- Files affected (direct, dependent, tests, cleanup)
- Agents involved
- Review verdicts
- Any unresolved MEDIUM/LOW findings

## Plan Format Reference

The orchestrator must follow these standards when writing the plan.

### Plan Document Header

Every plan MUST start with this header:

```markdown
# [Feature Name] Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** [One sentence]
**Spec:** `.claude/specs/YYYY-MM-DD-<name>-spec.md`
**Analysis:** `.claude/dependency_graphs/YYYY-MM-DD-<name>/`

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

### Phase Ordering Rules

1. **Data layer first** — Models, repositories, datasources before UI
2. **Dependencies before dependents** — If Phase 2 uses Phase 1 output, Phase 1 first
3. **Tests alongside implementation** — Every sub-phase includes test steps
4. **Cleanup last** — Dead code removal in final phase
5. **Integration phase** — Wire everything together after all features

---

## Hard Gate (Pre-Flight Check)

<HARD-GATE>
Do NOT spawn the plan-writer agent (Phase 4) until YOU have:
1. Read the approved spec from `.claude/specs/`
2. Completed full codebase indexing with CodeMunch (`index_folder` + `get_repo_outline`)
3. Traced all affected symbols via CodeMunch (`get_file_outline`, `search_symbols`, `get_symbol`)
4. Built and saved the dependency graph to `.claude/dependency_graphs/`
</HARD-GATE>

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

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Do This Instead |
|--------------|----------------|-----------------|
| Delegating CodeMunch to subagent | Subagents have NO MCP access | Main agent runs all CodeMunch calls |
| Expecting subagent to spawn agents | Subagents can't use Agent tool | Main agent dispatches all subagents |
| Vague steps ("add validation") | Agent has to think | Complete code with annotations |
| Missing file paths | Agent guesses wrong | Exact `path/to/file.dart:line` |
| Skipping tests | Breaks TDD cycle | Every sub-phase has test steps |
| Giant phases | Hard to track | Break into 2-5 min steps |
| No blast radius analysis | Misses side effects | Always run CodeMunch first |
| No agent assignments | Wrong agent gets work | Route by file pattern |
| No cleanup phase | Leaves dead code | Always include cleanup |
| Sequential adversarial review | Wastes time | Always dispatch both in parallel |
| Telling plan-writer to "read files" | It can Read but lacks MCP context | Paste all needed source in prompt |

---

## Remember

- **You drive the workflow** — main agent does CodeMunch, dependency graph, and agent dispatch
- **Plan-writer gets ALL context in its prompt** — paste spec, review, dependency graph, key source excerpts
- **Exact file paths** — always, including line numbers for modifications
- **Complete code** — never "add validation here", always the actual code
- **Annotations** — explain WHY, not just WHAT
- **Verification commands** — `pwsh -Command "flutter test ..."` with expected output
- **Zero-context assumption** — implementing agent knows NOTHING about our codebase
- **DRY, YAGNI, TDD** — every step, every phase
- **No commits in plan** — implement first, commit after verification
- **CodeMunch first** — always index before planning
- **Parallel adversarial review** — code-review + security agents dispatched simultaneously

## Save Location

Plans are saved to: `.claude/plans/YYYY-MM-DD-<feature-name>.md`
