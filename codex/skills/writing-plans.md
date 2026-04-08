# Codex Skill: Writing Plans

## Trigger

- `/writing-plans <spec>`
- `writing plans <spec>`

## Goal

Turn an approved shared spec into a detailed implementation plan using the same
`.claude` planning directories Claude uses, but with Codex-tagged artifact
names.

## Hard Gate

Do not write plan steps until all of these are true:

1. The approved spec has been read from `.claude/specs/`.
2. Dependency analysis and blast radius work are complete.
3. Analysis artifacts have been saved to `.claude/dependency_graphs/`.

## Workflow

1. Read the approved spec from `.claude/specs/YYYY-MM-DD-<topic>-codex-spec.md`
   or the shared Claude-authored equivalent.
2. Read the matching adversarial review if one exists.
3. Build the dependency graph and blast radius:
   - prefer CodeMunch if available
   - otherwise use targeted repo search and code tracing
4. Save analysis to `.claude/dependency_graphs/YYYY-MM-DD-<topic>-codex/`.
5. Write the plan to `.claude/plans/YYYY-MM-DD-<topic>-codex-plan.md`.
6. Run one review round using `code-review-agent` and `security-agent`
   personas.
7. Address CRITICAL/HIGH findings in the plan.
8. Present the plan summary and wait for approval before implementation.

## Plan Requirements

- Organize as Phase > Sub-phase > Step.
- Assume the implementing agent starts with zero local context.
- Name exact files to create, modify, test, verify, or clean up.
- Include verification commands and expected outcomes.
- Include cleanup work explicitly.
- Prefer TDD and offline-first reasoning where relevant.

## Analysis Outputs

Save these when writing a new Codex-authored plan:

- `.claude/dependency_graphs/YYYY-MM-DD-<topic>-codex/dependency-graph.md`
- `.claude/dependency_graphs/YYYY-MM-DD-<topic>-codex/blast-radius.md`

## Shared-State Guarantee

This skill writes plans and dependency analysis into the same `.claude`
directories Claude uses, so either tool can continue the implementation flow.

## Upstream Reference

- `.claude/skills/writing-plans/SKILL.md`
