---
name: writing-plans
description: "Use when you have an approved spec for a multi-step task, before touching code. Indexes codebase, builds dependency graph, and creates detailed implementation plans."
user-invocable: true
---

# Writing Plans

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

## Overview

Write comprehensive implementation plans assuming the implementing agent has **zero context** for our codebase. Document everything they need to know: which files to touch, complete code with annotations explaining WHY, exact verification commands, and expected output. Give them the whole plan as bite-sized steps organized into Phases, Sub-phases, and Steps.

**Principles:** DRY. YAGNI. TDD. Offline-first.

<HARD-GATE>
Do NOT write any plan steps until you have:
1. Received and read the approved spec from `.claude/specs/`
2. Completed full codebase indexing with CodeMunch
3. Built the dependency graph and blast radius analysis
4. Saved the analysis to `.claude/dependency_graphs/`
</HARD-GATE>

## Checklist

Complete these items **in order**:

1. **Read the spec** — load the approved spec from `.claude/specs/`
2. **Index the codebase** — full CodeMunch index of the project
3. **Build dependency graph** — trace all symbols affected by the spec's changes
4. **Determine blast radius** — map every file, function, and method impacted
5. **Map cleanup needs** — identify dead code, unused imports, stale references
6. **Save analysis** — write to `.claude/dependency_graphs/YYYY-MM-DD-<name>/`
7. **Write the plan** — Phase > Sub-phase > Step with full code + annotations
8. **Run adversarial review** — light review (code-review + security, one round, parallel)
9. **Address findings** — fix any CRITICAL/HIGH issues in the plan
10. **Present to user** — show plan summary and await approval

## Process Flow

```
Read Spec from .claude/specs/
    ↓
Index Codebase (CodeMunch MCP: mcp__jcodemunch__index_folder)
    ↓
Build Dependency Graph + Blast Radius
    ↓
Save Analysis → .claude/dependency_graphs/YYYY-MM-DD-<name>/
    ↓
Write Plan (Phase > Sub-phase > Step)
    ↓
Adversarial Review (code-review-agent + security-agent, parallel, one round)
    ↓
Address CRITICAL/HIGH Findings
    ↓
Present to User → User Approves?
    ↓ yes                    ↓ no
Save to .claude/plans/     Revise plan
```

---

## Step 1: Read the Spec

Load the approved spec from `.claude/specs/YYYY-MM-DD-<name>-spec.md`.

Extract:
- Feature requirements and success criteria
- Data model changes
- User flow changes
- UI components needed
- Offline behavior requirements
- Testing strategy
- Security implications
- Migration/cleanup needs

Also read the adversarial review at `.claude/adversarial_reviews/YYYY-MM-DD-<name>/review.md` for any NICE-TO-HAVE items that should be incorporated into the plan.

---

## Step 2: Index the Codebase

Use the CodeMunch MCP to perform a **full index** of the project:

```
mcp__jcodemunch__index_folder(path: ".", use_ai_summaries: true)
```

This gives a complete symbol map of every function, class, method, and constant in the codebase.

Then get the repository outline:
```
mcp__jcodemunch__get_repo_outline(repo: "<indexed-repo-name>")
```

---

## Step 3: Build Dependency Graph

Using the CodeMunch index, trace the dependency chain for every change the spec requires:

1. **Identify entry points** — use `search_symbols` to find existing symbols that will be modified
2. **Trace callers** — use `get_symbol` with `context_lines` to see who calls these symbols
3. **Trace callees** — what do these symbols depend on?
4. **Map the graph** — document the full dependency chain (2+ levels deep)
5. **Identify cross-cutting concerns** — shared utilities, base classes, mixins

For each affected symbol, document:
- Symbol name and file path (with line number)
- What calls it (callers)
- What it calls (callees)
- Impact: MODIFY | VERIFY | TEST | CLEANUP

---

## Step 4: Determine Blast Radius

From the dependency graph, map the full blast radius:

| Category | Description | Action |
|----------|-------------|--------|
| **Direct** | Files explicitly changed by the spec | Modify in plan |
| **Dependent** | Files that import/use changed symbols | Verify compatibility |
| **Test** | Tests for any Direct or Dependent file | Update or create |
| **Cleanup** | Dead code, unused imports after changes | Remove in cleanup phase |

---

## Step 5: Save Analysis

Save to `.claude/dependency_graphs/YYYY-MM-DD-<name>/`:

**`dependency-graph.md`** — Full symbol dependency map:
```markdown
## Symbol: ClassName.methodName
- **File**: `lib/features/X/data/repository.dart:45`
- **Callers**: [list with file:line]
- **Callees**: [list with file:line]
- **Impact**: MODIFY | VERIFY | TEST | CLEANUP
```

**`blast-radius.md`** — Summary of all affected files:
```markdown
## Blast Radius Summary

**Direct Changes**: N files
**Dependent Files**: N files
**Tests Needed**: N files
**Cleanup Items**: N items

### Direct Changes
| File | Changes | Risk |
|------|---------|------|

### Dependent Files
| File | Dependency | Action Needed |
|------|------------|---------------|

### Tests Needed
| File | Status | Action |
|------|--------|--------|

### Cleanup
| File | Item | Action |
|------|------|--------|
```

---

## Step 6: Write the Plan

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

## Step 7: Adversarial Review (Light)

After the plan is written, run a **light adversarial review**. This is lighter than the spec review because the spec has already been validated.

**One round, two agents in parallel:**

**Code Review Agent** (`code-review-agent`, model: claude-opus-4-6):
- Does the plan cover EVERY requirement from the spec?
- Are file paths correct and consistent?
- Does the plan follow DRY/YAGNI?
- Are test cases meaningful?
- Devil's advocate: What if a step fails? What's missing?

**Security Agent** (`security-agent`, model: claude-opus-4-6):
- Do any steps introduce security vulnerabilities?
- Auth/authorization gaps?
- RLS policy implications?
- Data exposure risks?

### Handling Findings
- **CRITICAL/HIGH** — Address before presenting to user
- **MEDIUM/LOW** — Note in plan, address during implementation

---

## Step 8: Present to User

**"Plan complete and saved to `.claude/plans/YYYY-MM-DD-<name>.md`.**

**Summary:**
- **Phases**: [N phases, N sub-phases, N total steps]
- **Files affected**: [N direct, N dependent, N tests, N cleanup]
- **Agents involved**: [list]

**Analysis**: `.claude/dependency_graphs/YYYY-MM-DD-<name>/`

**Ready to implement? Use `/implement .claude/plans/YYYY-MM-DD-<name>.md`**"

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
| Vague steps ("add validation") | Agent has to think | Complete code with annotations |
| Missing file paths | Agent guesses wrong | Exact `path/to/file.dart:line` |
| Skipping tests | Breaks TDD cycle | Every sub-phase has test steps |
| Giant phases | Hard to track | Break into 2-5 min steps |
| No blast radius analysis | Misses side effects | Always run CodeMunch first |
| No agent assignments | Wrong agent gets work | Route by file pattern |
| No cleanup phase | Leaves dead code | Always include cleanup |

---

## Remember

- **Exact file paths** — always, including line numbers for modifications
- **Complete code** — never "add validation here", always the actual code
- **Annotations** — explain WHY, not just WHAT
- **Verification commands** — `pwsh -Command "flutter test ..."` with expected output
- **Zero-context assumption** — implementing agent knows NOTHING about our codebase
- **DRY, YAGNI, TDD** — every step, every phase
- **No commits in plan** — implement first, commit after verification
- **CodeMunch first** — always index before planning

## Save Location

Plans are saved to: `.claude/plans/YYYY-MM-DD-<feature-name>.md`