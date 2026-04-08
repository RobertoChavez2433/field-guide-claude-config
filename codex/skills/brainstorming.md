# Codex Skill: Brainstorming

## Trigger

- `/brainstorming`
- `brainstorming`
- `brainstorm <topic>`

## Goal

Turn an idea into an approved spec before any implementation work starts.
Mirror Claude's brainstorming workflow closely enough that either tool can pick
up the same design conversation without a process shift.

## Hard Gate

- Do not write code, scaffold files, invoke implementation workflows, or make
  behavior changes until the user has approved the design.
- Treat "small" requests the same way. Scale the spec down, but do not skip it.

## Core Rules

- Ask one question at a time.
- Prefer multiple choice or tightly bounded options when practical.
- Keep the user in the loop after every major decision, not just at the end.
- If Codex's structured question tool is unavailable, ask concise plain-text
  questions instead of skipping the questioning phase.
- Load only the narrowest relevant `.claude/` context instead of broad browsing.

## Workflow Checklist

1. Explore current project context:
   - relevant code paths
   - feature state, relevant GitHub issue context, constraints, and active plans
   - current session handoff only if it matters to the topic
2. Ask 3-5 clarifying questions one at a time:
   - scope
   - priority
   - constraints
   - success criteria
3. Present 2-3 approaches with tradeoffs and a recommendation.
4. Present the spec in validated sections, stopping after each section for user
   confirmation.
5. Save the approved spec to
   `.claude/specs/YYYY-MM-DD-<topic>-codex-spec.md`.
6. Run adversarial review:
   - prefer the same code-review/security review pattern Claude uses
   - if agent dispatch is unavailable, perform the same review manually and
     capture holes, alternatives, pattern compliance, and security risks
7. Address MUST-FIX findings and surface SHOULD-CONSIDER items to the user.
8. Present the reviewed spec and offer handoff to implementation planning:
   - prefer `.claude/plans/YYYY-MM-DD-<topic>-codex-plan.md` for Codex-authored plans
   - reference existing `.claude/plans/*.md` files instead of duplicating them

## Context Loading Pattern

1. Start with the smallest topic-specific context set:
   - `.claude/state/feature-<name>.json`
   - `.claude/architecture-decisions/<name>-constraints.md`
   - matching feature docs only if needed
   - GitHub issue context only if it materially affects the design
2. Load PRDs or active plans only when they materially affect the design.
3. If the topic is cross-cutting, load only the relevant shared rules subset.
4. Avoid historical noise unless the design depends on old rationale.

## Spec Sections

Use only the sections the topic needs. For small changes, a short overview/data
model/user-flow spec may be enough.

1. Overview
2. Data Model
3. User Flow
4. UI Components
5. State Management
6. Offline Behavior
7. Edge Cases
8. Testing Strategy
9. Performance Considerations
10. Security Implications
11. Migration/Cleanup

Detailed templates live in:

- `.codex/skills/references/brainstorming-design-sections.md`

## Questioning Aids

Prefer multiple choice prompts when possible. Reuse the question patterns in:

- `.codex/skills/references/brainstorming-question-patterns.md`

## Output Convention

- Summarize the chosen direction.
- State tradeoffs and rejected alternatives.
- Record measurable success criteria.
- Save the spec to `.claude/specs/YYYY-MM-DD-<topic>-codex-spec.md`.
- Save the review to
  `.claude/adversarial_reviews/YYYY-MM-DD-<topic>-codex/review.md`.
- End by offering plan creation, not implementation.

## Project Adaptations

When the topic touches app behavior, always pressure-test for:

- offline-first use
- field conditions such as glare, gloves, and rushed data entry
- sync conflicts and queue behavior
- PDF/reporting implications
- auth, data exposure, and tenant boundaries

## Shared-Pattern Guarantee

This wrapper is the Codex-facing equivalent of
`.claude/skills/brainstorming/SKILL.md`. It preserves the same hard gate,
questioning style, spec-first flow, review step, and handoff pattern.

## Upstream Reference

- `.claude/skills/brainstorming/SKILL.md`
- `.claude/skills/brainstorming/references/question-patterns.md`
- `.claude/skills/brainstorming/references/design-sections.md`
