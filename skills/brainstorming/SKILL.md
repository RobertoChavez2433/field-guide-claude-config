---
name: brainstorming
description: Collaborative design through structured questioning
agent: planning-agent
user-invocable: true
---

# Brainstorming Skill

**Purpose**: Collaborative design through structured questioning and incremental validation.

## Iron Law

> **ONE QUESTION AT A TIME. PREFER MULTIPLE CHOICE.**

Never overwhelm with a list of questions. Each message should advance understanding by exactly one step.

## Core Principles

1. **Ask, don't assume** - Gather requirements before proposing solutions
2. **Multiple choice > open-ended** - Reduces cognitive load, surfaces options
3. **Incremental validation** - Break designs into digestible sections
4. **Document decisions** - Export to `.claude/plans/` for handoff

## Three Phases

### Phase 1: Understanding

**Goal**: Understand what the user actually wants before proposing anything.

1. Read existing code/documentation relevant to the feature
2. Check `.claude/autoload/_defects.md` for related past issues
3. Ask 3-5 clarifying questions, ONE AT A TIME
4. Use multiple choice when possible

**Question Types**:
- Scope: "Which of these should be included?"
- Priority: "What's most important to get right first?"
- Constraints: "Are there any hard requirements?"
- Context: "What problem is this solving?"

### Phase 2: Exploring

**Goal**: Present approaches with trade-offs for informed decision-making.

1. Present 2-3 distinct approaches
2. For each approach, explain:
   - How it works
   - Pros and cons
   - When it's the right choice
3. Ask: "Which direction resonates?"
4. Explore the chosen direction deeper

**Approach Template**:
```markdown
## Option A: [Name]
**How it works**: [1-2 sentences]
**Pros**: [Bullet list]
**Cons**: [Bullet list]
**Best when**: [Condition]
```

### Phase 3: Presenting

**Goal**: Break the design into validated sections.

1. Present design in 200-300 word sections
2. After each section, ask for validation
3. Only proceed when user confirms understanding
4. Iterate if needed before finalizing

**Section Sequence**:
1. Overview (what we're building)
2. Data model (entities, relationships)
3. UI flow (screens, navigation)
4. Edge cases (offline, errors)
5. Implementation phases (PR-sized chunks)

## Output

When design is complete:

1. **Export to file**: `.claude/plans/YYYY-MM-DD-<topic>-design.md`
2. **Include**:
   - Decisions made with rationale
   - Implementation phases
   - Agent assignments per phase
   - Verification criteria

## Reference Documents

@.claude/skills/brainstorming/references/question-patterns.md
@.claude/skills/brainstorming/references/design-sections.md

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Do This Instead |
|--------------|----------------|-----------------|
| Question dump | Overwhelms user | One question per message |
| Open-ended only | Harder to answer | Provide multiple choice options |
| Assume requirements | Builds wrong thing | Ask first, build second |
| Monolithic design | Hard to validate | Break into 200-300 word sections |
| Skip to solution | Misses context | Understand before exploring |

## Flutter/Construction Adaptations

When designing for this app, always consider:

- **Offline-first**: How does this work without network?
- **Field conditions**: Gloved hands, bright sunlight, rushed users
- **GPS tagging**: Does this feature need location data?
- **PDF generation**: Will this data appear in reports?
- **Sync conflicts**: What if same record edited on two devices?
