---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation."
user-invocable: true
---

# Brainstorming Ideas Into Specs

## Overview

Help turn ideas into fully formed design specs through natural collaborative dialogue.

Start by understanding the current project context, then ask questions one at a time to refine the idea. Once you understand what you're building, present the design in validated sections and get user approval. After approval, write the spec and offer to hand off to the writing-plans skill.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity. Exception: XS/S-sized tasks per CLAUDE.md sizing guide may skip brainstorming when the user confirms scope inline.
</HARD-GATE>

## Anti-Pattern: "This Is Too Simple To Need A Design"

Every project goes through this process. A todo list, a single-function utility, a config change — all of them. "Simple" projects are where unexamined assumptions cause the most wasted work. The design can be short (a few sentences for truly simple projects), but you MUST present it and get approval.

## Checklist

You MUST complete these items in order:

1. **Explore project context** — check files, docs, recent commits, GitHub Issues
2. **Ask clarifying questions** — one at a time, understand purpose/constraints/success criteria
3. **Propose 2-3 approaches** — with trade-offs and your recommendation
4. **Present spec sections** — scaled to complexity, get user approval after each section
5. **Write spec document** — save to `.claude/specs/YYYY-MM-DD-<topic>-spec.md`
6. **Hand off to writing-plans** — offer to invoke writing-plans skill with spec path

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
Offer to invoke writing-plans
```

**The terminal state is offering to invoke writing-plans.** See HARD-GATE above — no implementation actions until design is approved.

---

## Iron Law

> **ONE QUESTION AT A TIME. PREFER MULTIPLE CHOICE.**

Never overwhelm with a list of questions. Each message should advance understanding by exactly one step.

## Core Principles

1. **Ask, don't assume** — Gather requirements before proposing solutions
2. **Zero ambiguity gate** — Keep asking questions until there is zero ambiguity in the user's intent, scope, and vision. The entire point of brainstorming is to capture the user's vision. Do not advance to Phase 2 until you can restate the user's intent, scope, and vision back to them and they confirm it is exactly right.
3. **Multiple choice > open-ended** — Reduces cognitive load, surfaces options the user might not have considered
4. **Incremental validation** — Break designs into digestible sections
5. **YAGNI ruthlessly** — Remove unnecessary features during design. Don't design for hypothetical requirements.
6. **Document decisions** — Export to `.claude/specs/` for handoff to writing-plans
7. **Scale to complexity** — Small features get lean specs. Not all sections are required.

---

## The Process

### Phase 1: Understanding

**Goal**: Understand what the user actually wants before proposing anything.

1. Read existing code/documentation relevant to the feature
2. Check `gh issue list --label "{feature}" --state open` for related past issues
3. Check `.claude/prds/` for any existing PRD on this feature
4. Ask clarifying questions ONE AT A TIME until there is zero ambiguity about:
   - **Intent**: What problem are we solving? What does success look like?
   - **Scope**: What's in vs. out? What are the boundaries?
   - **Vision**: How should it feel to use? What's the user's mental model?
5. Use multiple choice when possible (see reference: question-patterns.md)
6. **Ambiguity check**: When you believe you understand, restate the user's intent, scope, and vision in your own words and ask: "Is this exactly right, or did I miss something?" Do NOT proceed until they confirm.

**Question Types**:
- Scope: "Which of these should be included?"
- Priority: "What's most important to get right first?"
- Constraints: "Are there any hard requirements?"
- Context: "What problem is this solving?"
- Intent: "What does success look like when this is done?"
- Vision: "How do you picture this working from the user's perspective?"

### Gate: Intent Confirmed

Before entering Phase 2, you MUST:
1. Summarize the user's intent, scope, and vision in 3-5 bullet points
2. Ask: "Is this exactly right, or did I miss something?"
3. If the user corrects anything, ask follow-up questions on the correction until clear
4. Only proceed to Phase 2 when the user explicitly confirms

This is not optional. The spec captures the user's vision — if you misunderstand the vision, the spec is wrong, the plan is wrong, and the implementation is wrong. Get it right here.

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

## Terminal State

After the spec is written and user has approved all sections:

**"Spec complete. Saved to `.claude/specs/YYYY-MM-DD-<topic>-spec.md`.**

**Ready to map the codebase? I'll invoke the tailor skill to:**
1. Index the codebase with CodeMunch
2. Discover architectural patterns and reusable methods
3. Verify ground truth against the codebase

**After tailoring, run `/writing-plans` to create the implementation plan.**

**Proceed with `/tailor`?"**

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
| "Too simple" skip | Unexamined assumptions | Every project gets a spec (XS/S tasks may skip when user confirms scope inline per CLAUDE.md sizing guide; security-sensitive changes always use full pipeline) |
| Rush to approaches | Proposing solutions before fully understanding vision | Stay in Phase 1 until zero ambiguity confirmed by user |