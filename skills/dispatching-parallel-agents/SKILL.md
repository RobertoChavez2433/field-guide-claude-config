---
name: dispatching-parallel-agents
description: Coordinate multiple agents concurrently on independent problems to avoid sequential bottlenecks and prevent agents from reverting each other's changes
context: fork
agent: planning-agent
user-invocable: true
---

# Dispatching Parallel Agents

**Purpose**: Coordinate multiple agents working simultaneously on independent problems, avoiding sequential bottlenecks and preventing agents from reverting each other's changes.

## When to Use This Pattern

Deploy parallel agents when:
- You have 2+ **independent** tasks that can be worked on without shared state or sequential dependencies
- Multiple unrelated failures exist across different files or subsystems
- Independent problems require no shared context between agents
- Fixing one issue won't resolve (or conflict with) others

**Do NOT use parallel agents when**:
- Failures are related or one depends on the result of another
- Agents would need to edit the same files
- You don't yet understand the full system well enough to divide the work safely

## The Core Risk: Agents Reverting Each Other

When two agents write to overlapping files, the second agent's write wins — erasing the first agent's work. This is the most common parallel-agent failure mode.

**Prevention**:
1. Map every task to its file scope before dispatching
2. Ensure zero file overlap between agent assignments
3. After all agents complete, review all outputs before integrating
4. If overlap is unavoidable, run those tasks sequentially instead

## Implementation Steps

### Step 1: Identify Independent Domains

Group related failures or tasks into non-overlapping domains:
```
Domain A: lib/features/pdf/services/extraction/stages/  (PDF pipeline)
Domain B: test/features/pdf/extraction/stages/          (Stage tests)
Domain C: lib/features/pdf/services/extraction/models/  (Data models)
```

Each domain should be ownable by exactly one agent.

### Step 2: Write Focused Agent Prompts

Each agent prompt must be:
- **Narrowly focused** on one problem domain
- **Self-contained** with all necessary context (agents start fresh — no shared memory)
- **Explicit about deliverables** (what files to modify, what output to produce)
- **Scoped with file boundaries** (list exact files the agent may touch)

**Good prompt structure**:
```
Task: [Specific problem to solve]
Files in scope: [Exact list — agent must not touch files outside this list]
Context: [All relevant background — don't assume the agent knows anything]
Expected output: [Specific deliverable — test passes, file updated, etc.]
```

**Bad prompt (too broad)**:
```
"Fix all the failing tests"
```

**Good prompt (scoped)**:
```
"Fix the 3 failing tests in test/features/pdf/extraction/stages/row_classifier_v3_test.dart.
The failures are caused by [specific error message].
Files in scope: lib/features/pdf/services/extraction/stages/row_classifier_v3.dart,
test/features/pdf/extraction/stages/row_classifier_v3_test.dart.
Do not modify any other files."
```

### Step 3: Dispatch Concurrently

Send ALL independent agent Task calls in a single message — this is what makes them truly parallel:

```
[Single message with multiple Task tool calls]
- Task 1: Fix row classifier failures (scope: stages/row_classifier_v3.dart)
- Task 2: Fix cell extractor failures (scope: stages/cell_extractor_v2.dart)
- Task 3: Update fixture JSON files (scope: test/fixtures/*.json)
```

### Step 4: Review and Integrate

After all agents complete:
1. Read each agent's output summary
2. Check for any file conflicts (did two agents edit the same file?)
3. Verify fixes don't contradict each other
4. Run the full test suite once to confirm no regressions

## Agent Assignment by Domain (This Project)

| Domain | Agent | Primary Files |
|--------|-------|--------------|
| PDF pipeline stages | `pdf-agent` | `lib/features/pdf/services/extraction/stages/` |
| Flutter UI / widgets | `frontend-flutter-specialist-agent` | `lib/features/**/presentation/` |
| Data models / repositories | `backend-data-layer-agent` | `lib/features/**/data/` |
| Tests / debugging | `qa-testing-agent` | `test/` |
| Architecture / code quality | `code-review-agent` | Read-only review |
| Database / Supabase | `backend-supabase-agent` | Supabase files |

## Quick Checklist Before Dispatching

- [ ] Each task is independent (no sequential dependency)
- [ ] Zero file overlap between all agent scopes
- [ ] Each prompt is self-contained with full context
- [ ] Expected deliverables are explicit
- [ ] All Task calls will be sent in a single message

## After Parallel Runs: Verify File State

Agents can silently overwrite each other's work. After any parallel run:
```
git diff --stat   # See all modified files at a glance
```
If unexpected files appear modified, investigate before proceeding.
