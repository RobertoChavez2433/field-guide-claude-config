# Planning Pipeline Restructure — Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Replace the planning-agent + dispatching-parallel-agents with a streamlined Brainstorming → Writing-Plans → Implement skill pipeline, with adversarial reviews, CodeMunch integration, and new artifact directories.

**Spec:** Design approved via brainstorming session 2026-03-08 (this session).

**Architecture:** The planning-agent is eliminated. Brainstorming becomes a standalone user-invocable skill that produces specs (`.claude/specs/`). Writing-plans is a new skill that reads specs, indexes the codebase via CodeMunch MCP, builds dependency graphs (`.claude/dependency_graphs/`), and produces detailed Phase > Sub-phase > Step plans. Both skills include adversarial reviews. The implement skill already supports the Phase > Sub-phase > Step format and needs only minor updates.

**Tech Stack:** Markdown skill definitions, JSON state files, MCP CodeMunch integration.

**Blast Radius:** 11 files modified, 4 files deleted, 3 directories created = 18 discrete changes across Tier 1 + Tier 2 files.

**Note:** All changes are to `.claude/` configuration files, not Dart source code. Flutter analyze/test gates will pass trivially since no `lib/` code is touched.

---

## Phase 1: Infrastructure — Create Directories and Delete Obsolete Files

### Sub-phase 1.1: Create new artifact directories

**Files:**
- Create: `.claude/specs/.gitkeep`
- Create: `.claude/dependency_graphs/.gitkeep`
- Create: `.claude/adversarial_reviews/.gitkeep`

**Agent**: `general-purpose`

#### Step 1.1.1: Create specs directory

Create `.claude/specs/.gitkeep` (empty file). This directory stores brainstorming output — approved design specifications.

#### Step 1.1.2: Create dependency_graphs directory

Create `.claude/dependency_graphs/.gitkeep` (empty file). This directory stores CodeMunch analysis output — dependency graphs and blast radius documents, organized as `YYYY-MM-DD-<name>/` subdirectories.

#### Step 1.1.3: Create adversarial_reviews directory

Create `.claude/adversarial_reviews/.gitkeep` (empty file). This directory stores spec-level adversarial review reports, organized as `YYYY-MM-DD-<name>/review.md`.

### Sub-phase 1.2: Delete obsolete files

**Files:**
- Delete: `.claude/agents/planning-agent.md`
- Delete: `.claude/agent-memory/planning-agent/MEMORY.md` (and empty parent dir)
- Delete: `.claude/skills/dispatching-parallel-agents/SKILL.md` (and empty parent dir)

**Agent**: `general-purpose`

#### Step 1.2.1: Delete planning-agent

Delete `.claude/agents/planning-agent.md`. This agent is replaced by the brainstorming and writing-plans skills.

#### Step 1.2.2: Delete planning-agent memory

Delete `.claude/agent-memory/planning-agent/MEMORY.md` and remove the empty `planning-agent/` directory. This memory is orphaned since the agent no longer exists.

#### Step 1.2.3: Delete dispatching-parallel-agents skill

Delete `.claude/skills/dispatching-parallel-agents/SKILL.md` and remove the empty `dispatching-parallel-agents/` directory. This skill was never used.

---

## Phase 2: Core Skills — Rewrite Brainstorming and Create Writing-Plans

### Sub-phase 2.1: Rewrite brainstorming skill

**Files:**
- Rewrite: `.claude/skills/brainstorming/SKILL.md`

**Agent**: `general-purpose`

#### Step 2.1.1: Write new brainstorming SKILL.md

Replace the entire contents of `.claude/skills/brainstorming/SKILL.md` with the following:

```markdown
---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation."
user-invocable: true
---

# Brainstorming Ideas Into Specs

## Overview

Help turn ideas into fully formed design specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design in validated sections and get user approval. After approval, run an adversarial review, address findings, and hand off to the writing-plans skill.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity.
</HARD-GATE>

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short (a few sentences for truly simple projects), but you MUST present it and get approval.

## Checklist

You MUST complete these items in order:

1. **Explore project context** — check files, docs, recent commits, defects
2. **Ask clarifying questions** — one at a time, understand purpose/constraints/success criteria
3. **Propose 2-3 approaches** — with trade-offs and your recommendation
4. **Present spec sections** — scaled to complexity, get user approval after each section
5. **Write spec document** — save to `.claude/specs/YYYY-MM-DD-<topic>-spec.md`
6. **Run adversarial review** — orchestrate multi-agent deep review of the spec
7. **Address findings** — fix MUST-FIX items, update spec
8. **Present to user** — show review results + updated spec for final approval
9. **Hand off to writing-plans** — offer to invoke writing-plans skill with spec path

## Process Flow

```
Explore project context
    ↓
Ask clarifying questions (one at a time)
    ↓
Propose 2-3 approaches with trade-offs
    ↓
Present spec in sections → User approves each?
    ↓ yes                          ↓ no
Write spec to .claude/specs/     Revise section
    ↓
Adversarial Review (orchestrator dispatches agents)
    ↓
Address MUST-FIX findings, update spec
    ↓
Present review + updated spec to user → Approved?
    ↓ yes                                 ↓ no
Offer to invoke writing-plans          Revise further
```

**The terminal state is offering to invoke writing-plans.** Do NOT invoke any other implementation skill.

---

## Iron Law

> **ONE QUESTION AT A TIME. PREFER MULTIPLE CHOICE.**

Never overwhelm with a list of questions. Each message should advance understanding by exactly one step.

## Core Principles

1. **Ask, don't assume** — Gather requirements before proposing solutions
2. **Multiple choice > open-ended** — Reduces cognitive load, surfaces options the user might not have considered
3. **Incremental validation** — Break designs into digestible sections
4. **YAGNI ruthlessly** — Remove unnecessary features during design. Don't design for hypothetical requirements.
5. **Document decisions** — Export to `.claude/specs/` for handoff to writing-plans
6. **Scale to complexity** — Small features get lean specs. Not all sections are required.

---

## The Process

### Phase 1: Understanding

**Goal**: Understand what the user actually wants before proposing anything.

1. Read existing code/documentation relevant to the feature
2. Check `.claude/defects/_defects-{feature}.md` for related past issues
3. Check `.claude/prds/` for any existing PRD on this feature
4. Ask 3-5 clarifying questions, ONE AT A TIME
5. Use multiple choice when possible (see reference: question-patterns.md)

**Question Types**:
- Scope: "Which of these should be included?"
- Priority: "What's most important to get right first?"
- Constraints: "Are there any hard requirements?"
- Context: "What problem is this solving?"

### Phase 2: Exploring

**Goal**: Present approaches with trade-offs for informed decision-making.

1. Present 2-3 distinct approaches with trade-offs
2. Lead with your recommended option and explain why
3. For each approach, explain:
   - How it works
   - Pros and cons
   - When it's the right choice
4. Ask: "Which direction resonates?"
5. Explore the chosen direction deeper

**Approach Template**:
```markdown
## Option A: [Name] (Recommended)
**How it works**: [1-2 sentences]
**Pros**: [Bullet list]
**Cons**: [Bullet list]
**Best when**: [Condition]
```

### Phase 3: Presenting

**Goal**: Break the design into validated sections, scaled to complexity.

1. Present spec in sections (see reference: design-sections.md)
2. Scale each section to its complexity: a few sentences if straightforward, up to 200-300 words if nuanced
3. After each section, ask for validation
4. Only proceed when user confirms understanding
5. Iterate if needed before finalizing

**Spec Sections** (include all that are relevant — small features may skip some):
1. Overview (what and why, success criteria)
2. Data Model (entities, relationships, sync)
3. User Flow (screens, navigation, entry points)
4. UI Components (widgets, layout, reusable patterns)
5. State Management (provider/repository design)
6. Offline Behavior (sync, conflict resolution, queue)
7. Edge Cases (error states, boundaries, permissions)
8. Testing Strategy (what to test, coverage expectations)
9. Performance Considerations (bottlenecks, optimization)
10. Security Implications (auth, data exposure, RLS)
11. Migration/Cleanup (dead code removal, schema changes)

---

## Output

When the spec is complete and user has approved all sections:

1. **Export to file**: `.claude/specs/YYYY-MM-DD-<topic>-spec.md`
2. **Include**:
   - All validated sections
   - Decisions made with rationale
   - Approach selected and why alternatives were rejected
   - Success criteria (measurable)

---

## Adversarial Review

After the spec is saved, run an adversarial review. This is the most important review in the pipeline because it validates the core ideas before any plan or code is written.

### Review Orchestration

Dispatch agents to perform a thorough adversarial review:

**Code Review Agent** (`code-review-agent`, model: claude-opus-4-6):
- Completeness: Does the spec cover all requirements? Missing edge cases?
- Architecture: Does this integrate well with existing patterns? Are there simpler approaches?
- Devil's advocate: What if this step fails? What about race conditions? What about offline mode? What about large datasets?
- Technical debt: Will this introduce debt? Over-engineering?

**Security Agent** (`security-agent`, model: claude-opus-4-6):
- Security implications: Auth gaps? Data exposure? RLS policy needs?
- Threat modeling: What could go wrong from a security perspective?
- OWASP compliance: Any mobile top 10 concerns?

Both agents also:
- Research the codebase for pattern compliance
- Suggest alternative approaches that achieve the same or better results
- Challenge every assumption creatively

### Review Output

Save to `.claude/adversarial_reviews/YYYY-MM-DD-<topic>/review.md`:

```markdown
# Adversarial Review: [Topic]

**Spec**: `.claude/specs/YYYY-MM-DD-<topic>-spec.md`
**Date**: YYYY-MM-DD
**Reviewers**: code-review-agent, security-agent

## Holes Found
[Issues where the spec is incomplete or inconsistent]

## Alternative Approaches
[Better ways to achieve the same result, with reasoning]

## Codebase Pattern Compliance
[Where the spec follows or deviates from existing patterns]

## Security Implications
[Auth, data exposure, RLS, OWASP concerns]

## Recommendations

### MUST-FIX (spec is broken without this)
- [Item with rationale and suggested resolution]

### SHOULD-CONSIDER (better approach exists)
- [Item with rationale and alternative]

### NICE-TO-HAVE (optimization opportunity)
- [Item with rationale]
```

### Handling Findings

1. Address all **MUST-FIX** items — update the spec
2. Present **SHOULD-CONSIDER** items to the user for decision
3. Note **NICE-TO-HAVE** items in the spec for the writing-plans skill
4. Update the spec file with all changes
5. Present the review summary + updated spec to the user

---

## Handoff to Writing-Plans

After the user approves the reviewed spec:

**"Spec complete and reviewed. Saved to `.claude/specs/YYYY-MM-DD-<topic>-spec.md`.**
**Adversarial review saved to `.claude/adversarial_reviews/YYYY-MM-DD-<topic>/review.md`.**

**Ready to create the implementation plan? I'll invoke the writing-plans skill to:**
1. Index the codebase with CodeMunch
2. Build the dependency graph and blast radius
3. Write a detailed Phase > Sub-phase > Step plan

**Proceed with writing-plans?"**

Wait for user confirmation before invoking.

---

## Reference Documents

@.claude/skills/brainstorming/references/question-patterns.md
@.claude/skills/brainstorming/references/design-sections.md

## Flutter/Construction Adaptations

When designing for this app, always consider:

- **Offline-first**: How does this work without network?
- **Field conditions**: Gloved hands, bright sunlight, rushed users
- **GPS tagging**: Does this feature need location data?
- **PDF generation**: Will this data appear in reports?
- **Sync conflicts**: What if same record edited on two devices?

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Do This Instead |
|--------------|----------------|-----------------|
| Question dump | Overwhelms user | One question per message |
| Open-ended only | Harder to answer | Provide multiple choice options |
| Assume requirements | Builds wrong thing | Ask first, build second |
| Monolithic design | Hard to validate | Break into sections, validate each |
| Skip to solution | Misses context | Understand before exploring |
| "Too simple" skip | Unexamined assumptions | Every project gets a spec |
| Skip adversarial review | Misses holes in spec | Always run review after spec |
```

### Sub-phase 2.2: Create writing-plans skill

**Files:**
- Create: `.claude/skills/writing-plans/SKILL.md`

**Agent**: `general-purpose`

#### Step 2.2.1: Write writing-plans SKILL.md

Create `.claude/skills/writing-plans/SKILL.md` with the following content:

```markdown
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
```

### Sub-phase 2.3: Update design-sections reference doc

**Files:**
- Modify: `.claude/skills/brainstorming/references/design-sections.md`

**Agent**: `general-purpose`

#### Step 2.3.1: Add 4 new sections to design-sections.md

Read the current file at `.claude/skills/brainstorming/references/design-sections.md`. It has 7 sections. Add 4 new sections (8-11) after the existing Edge Cases section (section 7) but before the "Validation Prompt" section at the end.

**Update the Section Order list** at the top of the file to include:
```
8. **Testing Strategy** - What and how to test
9. **Performance Considerations** - Bottlenecks and optimization
10. **Security Implications** - Auth, data exposure, RLS
11. **Migration/Cleanup** - Schema changes, dead code removal
```

**Add these 4 new section templates** after the Edge Cases section (after the `---` following section 7) and before the `## Validation Prompt` section:

```markdown
---

## 8. Testing Strategy Section

```markdown
## Testing Strategy

### Unit Tests
| Component | Test Focus | Priority |
|-----------|-----------|----------|
| [Model/Repository] | [What to test] | HIGH/MED/LOW |

### Widget Tests
| Screen/Widget | Test Focus | Priority |
|--------------|-----------|----------|
| [ScreenName] | [Key interactions] | HIGH/MED/LOW |

### Integration Tests
- [ ] [End-to-end flow to verify]
- [ ] [Critical path to test]

### Coverage Expectations
- [Which areas need thorough coverage vs. smoke tests]
```

---

## 9. Performance Considerations Section

```markdown
## Performance Considerations

### Potential Bottlenecks
| Area | Concern | Mitigation |
|------|---------|------------|
| [Database] | [Large query] | [Indexing, pagination] |
| [UI] | [Heavy rebuild] | [const widgets, selective rebuild] |

### Optimization Targets
- [Lazy loading strategy]
- [Caching approach]
- [Image/file size management]

### Benchmarks
- [Acceptable load time for this feature]
- [Max acceptable memory usage]
```

---

## 10. Security Implications Section

```markdown
## Security Implications

### Authentication & Authorization
- [Which operations require auth?]
- [Role-based access needed?]

### Data Exposure
| Data | Sensitivity | Protection |
|------|------------|------------|
| [Field] | PII/Internal/Public | [RLS/Encryption/Masking] |

### RLS Policies
- [New policies needed for Supabase tables]
- [Existing policies to verify]

### Input Validation
- [Untrusted input boundaries]
- [Sanitization requirements]
```

---

## 11. Migration/Cleanup Section

```markdown
## Migration/Cleanup

### Schema Changes
| Table | Change | Migration Strategy |
|-------|--------|-------------------|
| [table_name] | [ADD/MODIFY/DROP column] | [Strategy] |

### Dead Code Removal
- [Files/methods that become unused]
- [Imports to clean up]

### Backward Compatibility
- [Data migration needed?]
- [Feature flags for gradual rollout?]

### Cleanup Checklist
- [ ] [Remove deprecated code]
- [ ] [Update imports]
- [ ] [Clean up test fixtures]
```
```

Also update the note after the section order list to say:
> **Note:** Not all sections are required for every feature. Scale to complexity — small features may only need Overview, Data Model, and User Flow.

---

## Phase 3: Update Implement Skill

### Sub-phase 3.1: Update implement skill for new pipeline

**Files:**
- Modify: `.claude/skills/implement/SKILL.md`

**Agent**: `general-purpose`

#### Step 3.1.1: Update plan search path in implement skill

Read `.claude/skills/implement/SKILL.md`. On line 22, the current text is:

```
2. If the user gave a bare filename (e.g. `my-plan.md`), search `.claude/plans/` for the file.
```

This is still correct — plans are still saved to `.claude/plans/`. No change needed here.

#### Step 3.1.2: Add spec and analysis references to orchestrator context

In the implement skill's orchestrator prompt section (around line 202-224, the "Project Context" block), add two new lines after the existing context:

After the line `Conventions:        .claude/CLAUDE.md`, add:
```
Specs:              .claude/specs/
Dependency graphs:  .claude/dependency_graphs/
```

#### Step 3.1.3: Update orchestrator On Start section

In the orchestrator prompt's "On Start" section (around line 182-198), after the existing files to read, add:

```
6. If the plan header references a spec file (`.claude/specs/...`), read it for additional context.
7. If the plan header references an analysis directory (`.claude/dependency_graphs/...`), read the `blast-radius.md` file for impact awareness.
```

---

## Phase 4: Documentation and State Cleanup

### Sub-phase 4.1: Update CLAUDE.md

**Files:**
- Modify: `.claude/CLAUDE.md`

**Agent**: `general-purpose`

#### Step 4.1.1: Remove planning-agent from Agents table

In `.claude/CLAUDE.md`, find the Agents table (around line 49-59). Remove the entire row:
```
| `planning-agent` | Requirements, implementation plans | PLAN |
```

#### Step 4.1.2: Update Skills table

In the Skills table (around line 63-74):

1. Change the brainstorming row from:
```
| `brainstorming` | Collaborative design | planning-agent |
```
to:
```
| `brainstorming` | Collaborative spec design with adversarial review | User-invoked |
```

2. Remove the dispatching-parallel-agents row:
```
| `dispatching-parallel-agents` | Coordinate parallel agents, prevent revert conflicts | planning-agent |
```

3. Add a new row for writing-plans (after the brainstorming row):
```
| `writing-plans` | CodeMunch-powered implementation plans with dependency analysis | User-invoked |
```

#### Step 4.1.3: Update Skills description paragraph

The paragraph after the Skills table (around line 75) currently says:
```
Skills are loaded via `skills:` frontmatter in agent files. Claude auto-delegates to agents based on task description.
```

Update it to:
```
Skills are loaded via `skills:` frontmatter in agent files or invoked directly by the user. The planning pipeline flows: brainstorming (spec) → writing-plans (plan) → implement (execute).
```

#### Step 4.1.4: Add new directories to Directory Reference

In the Directory Reference table (around line 84-94), add three new rows:
```
| specs/ | Design specifications from brainstorming |
| dependency_graphs/ | CodeMunch codebase analysis per plan |
| adversarial_reviews/ | Spec-level adversarial review reports |
```

#### Step 4.1.5: Update Documentation System paragraph

In the Documentation System section (around line 96-103), add after the existing entries:
```
`.claude/specs/` — Design specifications produced by brainstorming skill
`.claude/dependency_graphs/` — CodeMunch analysis (dependency graphs + blast radius)
`.claude/adversarial_reviews/` — Spec-level adversarial review reports
```

### Sub-phase 4.2: Update docs files

**Files:**
- Modify: `.claude/docs/INDEX.md`
- Modify: `.claude/docs/features/README.md`
- Modify: `.claude/docs/guides/README.md`
- Modify: `.claude/docs/guides/testing/e2e-test-setup.md`

**Agent**: `general-purpose`

#### Step 4.2.1: Update docs/INDEX.md

Read `.claude/docs/INDEX.md`. Make these 3 changes:

1. **Line 18**: Change `**Agents that load feature docs**: planning-agent, code-review-agent, qa-testing-agent (cross-cutting)` to `**Agents that load feature docs**: code-review-agent, qa-testing-agent (cross-cutting)`

2. **Line 34**: Change `Used by: **qa-testing-agent**, **planning-agent**` to `Used by: **qa-testing-agent**`

3. **Line 77**: Remove the entire row `| **planning-agent** | All feature docs (cross-cutting) |`

#### Step 4.2.2: Update docs/features/README.md

Read `.claude/docs/features/README.md`. On line 44, remove the entire line:
```
- **planning-agent** → All feature docs (cross-cutting)
```

#### Step 4.2.3: Update docs/guides/README.md

Read `.claude/docs/guides/README.md`. On line 12, change from:
```
| [E2E Test Setup](testing/e2e-test-setup.md) | Patrol E2E test environment configuration and troubleshooting | qa-testing-agent, planning-agent |
```
to:
```
| [E2E Test Setup](testing/e2e-test-setup.md) | Patrol E2E test environment configuration and troubleshooting | qa-testing-agent |
```

#### Step 4.2.4: Update docs/guides/testing/e2e-test-setup.md

Read `.claude/docs/guides/testing/e2e-test-setup.md`. On line 3, change from:
```
> **Used By**: [qa-testing-agent](../../../agents/qa-testing-agent.md) and [planning-agent](../../../agents/planning-agent.md) for test environment configuration and CI/CD integration
```
to:
```
> **Used By**: [qa-testing-agent](../../../agents/qa-testing-agent.md) for test environment configuration and CI/CD integration
```

### Sub-phase 4.3: Update AGENT-FEATURE-MAPPING.json

**Files:**
- Modify: `.claude/state/AGENT-FEATURE-MAPPING.json`

**Agent**: `general-purpose`

#### Step 4.3.1: Remove planning-agent from agents array

Read `.claude/state/AGENT-FEATURE-MAPPING.json`. Remove the entire planning-agent object from the `agents` array (lines 7-19, starting with `{` and ending with `}`). This includes the `"name": "planning-agent"` entry with its `description`, `file`, `phase`, `model`, `owns_paths`, `skills`, and `notes` fields.

#### Step 4.3.2: Update routing_rules description

Find the `routing_rules` section. On line 217, update the description from:
```
"description": "File-path-based routing for agent handoff, as defined in planning-agent.md"
```
to:
```
"description": "File-path-based routing for agent handoff, as defined in CLAUDE.md and the implement skill"
```

#### Step 4.3.3: Remove planning-agent from cross_cutting_agents

Find the `cross_cutting_agents` array (around lines 234-237). Remove the planning-agent entry:
```json
{
  "name": "planning-agent",
  "reason": "Cross-cutting: loads all feature docs, assigns phases to domain agents"
}
```

#### Step 4.3.4: Update overlap findings

Find the `overlap_findings` array entry (around line 260) that mentions `planning-agent`. Remove or rewrite any finding that references the planning-agent handoff table, since it no longer exists. The routing is now defined in the implement skill and writing-plans skill.

---

## Verification

After all phases are complete:

1. **Check no broken references**: Search all `.claude/` files for `planning-agent` — should only appear in historical/archival files (logs, completed plans, prds), never in active configuration files.

2. **Check skill registration**: Verify `.claude/CLAUDE.md` Skills table includes `brainstorming` (User-invoked) and `writing-plans` (User-invoked), and does NOT include `dispatching-parallel-agents`.

3. **Check directory existence**: Verify `.claude/specs/`, `.claude/dependency_graphs/`, `.claude/adversarial_reviews/` all exist.

4. **Check deleted files**: Verify `.claude/agents/planning-agent.md`, `.claude/skills/dispatching-parallel-agents/`, and `.claude/agent-memory/planning-agent/` no longer exist.

5. **Check new skills**: Verify `.claude/skills/brainstorming/SKILL.md` and `.claude/skills/writing-plans/SKILL.md` both exist and have correct `user-invocable: true` frontmatter.

6. **Pipeline flow test**: Confirm the new pipeline is coherent:
   - Brainstorming outputs to `.claude/specs/`
   - Writing-plans reads from `.claude/specs/`, writes analysis to `.claude/dependency_graphs/`, writes plan to `.claude/plans/`
   - Implement reads from `.claude/plans/`
