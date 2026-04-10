---
name: systematic-debugging
description: "Interactive root-cause-first debugging for issues that need evidence, instrumentation, and a clear stop-before-fixing gate."
user-invocable: true
disable-model-invocation: true
---

# Systematic Debugging

Debug with the user, not around the user. This skill is for evidence-driven
root cause analysis, especially when async behavior, sync state, driver flows,
or instrumentation matter.

## Iron Law

No fixes before root cause.

## Interaction Rules

- Stay interactive and visible.
- Present findings after each major phase.
- Do not write code without explicit user approval.
- Do not jump from investigation to implementation.
- Use background research only for read-only exploration.

## Mode Choice

Ask once at the start:

```text
Quick mode or Deep mode?
```

- `Quick`: direct investigation with targeted reads and logs
- `Deep`: adds a read-only `debug-research-agent` in parallel

## Reference Loading

Load only the references needed for the current issue:

- `references/log-investigation-and-instrumentation.md`
- `references/codebase-tracing-paths.md`
- `references/driver-integration.md`
- `references/debug-session-management.md`
- `references/defects-integration.md`

Do not front-load every reference file.

## Workflow

### 1. Triage

- confirm the bug statement and repro steps
- check whether this looks like a known issue pattern
- identify the smallest likely code path
- decide whether logs, driver automation, or manual repro are needed

Then present the triage summary before moving on.

### 2. Coverage And Instrumentation

- inspect existing logs on the suspected path
- identify blind spots
- add temporary hypothesis markers only where evidence is missing
- add permanent logging only when a real long-term coverage gap exists

Never log secrets, tokens, or raw credentials.

### 3. Reproduce

- prefer the driver path when it gives clearer evidence
- fall back to manual reproduction when driver setup is not worth the cost
- capture only the evidence needed to isolate the failure point

If using the driver, follow `references/driver-integration.md`.

### 4. Evidence Analysis

- compare expected vs actual log progression
- identify the first missing, wrong, or failing boundary
- compare against a similar working path when useful
- read background research findings only if they sharpen the diagnosis

### 5. Root Cause Report

Present:

- bug summary
- key evidence
- most upstream root cause
- proposed fix approach
- likely files to change
- risk level

Then stop and wait for the user to choose:

- `approved`
- `investigate more`
- `wrong direction`
- `defer`

## If The User Approves A Fix

After approval:

1. implement the approved fix
2. rerun the repro path
3. compare before vs after evidence
4. remove all temporary hypothesis markers
5. keep only logging that fills a real permanent gap
6. write a short scrubbed session note in `.claude/debug-sessions/`

## Cleanup Hard Gate

Before ending the session:

1. remove every temporary `Logger.hypothesis(...)` marker
2. verify none remain
3. stop any driver session you started unless the user wants it left up
4. avoid leaving stray debug-only scaffolding in production code

## Stop Conditions

Stop and reassess if:

- 3 hypotheses fail
- the issue expands beyond 5 files without a clear upstream cause
- the proposed fix only suppresses symptoms
- you still cannot explain why the bug exists

## Output Shape

Keep status updates short. Root-cause reports should be structured, but not
longer than needed to justify the next decision.
