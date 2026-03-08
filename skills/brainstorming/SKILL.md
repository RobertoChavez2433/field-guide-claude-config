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