# Codex Skill: Systematic Debugging

## Trigger

- `/systematic-debugging`
- `systematic debugging`
- `systematic debug <issue>`

## Goal

Debug with the same root-cause-first discipline Claude uses, as an interactive
workflow in the main conversation.

## Hard Rules

- No fixes before root-cause investigation.
- Stay interactive and visible; show findings after each phase.
- Do not write code without explicit user approval.
- Do not skip from investigation to implementation.
- Use parallel research only for read-only exploration when needed.

## Required Context First

Before debugging a feature, load:

1. the smallest relevant feature state and constraints files
2. any relevant GitHub issue context or issue IDs already referenced in the conversation/state
3. only the code paths directly involved in the failure

Load broader docs or test guidance only when the investigation requires them.

## Three-Phase Framework

### Phase 1: Root Cause Investigation

- read the exact error and reproduction steps
- isolate the failure
- instrument boundaries in multi-layer flows
- trace the data path upstream
- identify when it last worked and what changed

After Phase 1, present findings and confirm the investigation direction.

### Phase 2: Pattern Analysis

- find a similar working path
- compare differences
- inspect timing and async behavior
- validate assumptions about the data and environment

### Phase 3: Hypothesis And Root Cause Report

- form one hypothesis at a time
- support it with evidence
- identify the most upstream origin of the failure
- describe the proposed fix approach without implementing it
- list the files likely to change
- state risk

Then stop and let the user decide whether to implement, investigate further, or
defer.

## Stop Conditions

Stop and reassess if:

- 3 hypotheses fail
- the issue expands to 5+ files without a clear root cause
- the proposed "fix" only suppresses symptoms
- you cannot explain why the bug exists yet

## Reference Files

- `.claude/skills/systematic-debugging/references/root-cause-tracing.md`
- `.claude/skills/systematic-debugging/references/defense-in-depth.md`
- `.claude/skills/systematic-debugging/references/condition-based-waiting.md`

## Shared-Pattern Guarantee

This wrapper follows the same root-cause discipline and issue-driven debugging as
`.claude/skills/systematic-debugging/SKILL.md`, so both tools use the same
debugging standards.

## Upstream Reference

- `.claude/skills/systematic-debugging/SKILL.md`
