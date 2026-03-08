# Test Skill Design

**Date**: 2026-03-03
**Status**: Approved
**Origin**: Brainstorming session (Session 486)

## Overview

A `/test` skill that builds the app, installs it on a USB-connected Android device, and runs user flows via ADB. Uses UIAutomator for precise interaction and Claude's vision for visual verification. An orchestrator agent coordinates wave-based execution, dispatching one task agent per dependency wave to keep context windows manageable.

### Scope

**Included**: Build + install, flow registry with dependency chains, ADB interaction (UIAutomator + screencap), log collection, defect auto-filing, markdown report generation.

**Excluded**: iOS testing, emulator management, Patrol/Flutter Driver integration, multi-device parallel testing.

### Success Criteria

- Single `/test` invocation builds, installs, and exercises flows without manual intervention
- Each wave agent gets a fresh context (only its wave's screenshots + XML dumps)
- Orchestrator stays thin — only sees wave summaries, not raw screenshots
- Failures auto-file to `.claude/defects/_defects-{feature}.md`
- Full report with screenshots saved to `.claude/test-results/`

## Agent Hierarchy

```
User invokes /test
  └─ Orchestrator (Sonnet)
       ├─ Inline: build APK, install, launch
       ├─ Dispatch: WaveAgent-1 (Sonnet) → [login]
       ├─ Dispatch: WaveAgent-2 (Sonnet) → [create-project, sync-check]
       ├─ Dispatch: WaveAgent-3 (Sonnet) → [create-entry]
       └─ Dispatch: WaveAgent-4 (Sonnet) → [submit-entry]
```

## Flow Registry

### Format

Single file at `.claude/test-flows/registry.md`. Each flow is an H2 section:

```markdown
## login
- **feature**: auth
- **deps**: []
- **precondition**: App is on login screen
- **steps**:
  1. Enter email in login field
  2. Enter password
  3. Tap "Sign In" button
  4. Wait for dashboard to load
- **verify**: Dashboard screen visible with project list or empty state
- **key-elements**: [emailField, passwordField, signInButton]
```

### Fields

| Field | Purpose |
|-------|---------|
| `feature` | Maps to defect file (`_defects-{feature}.md`) |
| `deps` | Dependency chain — orchestrator computes waves from this |
| `key-elements` | `TestingKeys` resource-ids the agent looks for in UIAutomator XML |
| `steps` | Human-readable intent — agent interprets into ADB commands |
| `verify` | What agent checks via screenshot + vision after completing steps |
| `precondition` | Expected app state before flow begins |

### Wave Computation

Orchestrator builds waves from deps using topological sort:

```
Wave 0: [login]                        (no deps)
Wave 1: [create-project, sync-check]   (dep: login)
Wave 2: [create-entry]                 (dep: create-project)
Wave 3: [submit-entry]                 (dep: create-entry)
```

### Git Diff Auto-Selection

When user runs `/test` with no args:

1. Read `git diff main...HEAD --name-only`
2. Map changed file paths to features (`lib/features/entries/*` → `entries`)
3. Select all flows matching those features
4. Add transitive dependencies (if `create-entry` selected, `login` and `create-project` are pulled in)

## Agent Interaction Model

### Wave Agent Lifecycle

Each wave agent receives from the orchestrator:

- Flows to execute (from registry)
- App package name + main activity
- Known TestingKeys for those flows
- Previous wave results (pass/fail per flow, any state notes)
- Instructions: interaction method, screenshot dir, output format

### ADB Interaction Loop

Each flow within a wave follows this cycle:

```
┌─────────────────────────────────┐
│  1. uiautomator dump            │
│     → parse XML, find elements  │
│       by resource-id / text     │
├─────────────────────────────────┤
│  2. adb shell input tap X Y     │
│     (center of element bounds)  │
├─────────────────────────────────┤
│  3. sleep 1-2s (animation wait) │
├─────────────────────────────────┤
│  4. screencap → pull PNG        │
│     → Claude vision reads image │
│     → "What do I see? Expected?"│
├─────────────────────────────────┤
│  5. Decision:                   │
│     ✓ Expected → next step      │
│     ✗ Unexpected → log failure  │
│     ? Unclear → retry once      │
└─────────────────────────────────┘
```

### Element Finding Strategy

Priority order:

1. **resource-id** — Most reliable. Maps to `TestingKeys`. Agent searches XML for `resource-id="com.package:id/keyName"`
2. **text content** — Fallback. Search by `text="Sign In"` or `content-desc="Sign In"`
3. **Vision-guided coordinates** — Last resort. Screenshot → ask Claude "where is the button?" → estimate tap point

### Log Collection

At the end of each flow (pass or fail):

```
adb logcat -d -t "60" *:W    → recent warnings/errors
adb logcat -d -s flutter      → Flutter-specific logs
```

### Wave Agent Return Format

```markdown
## Wave 2 Results

### create-project: PASS (8s)
- Screenshots: [create-project-1.png, create-project-2.png]
- Notes: Project "Test Project" created successfully. Appeared in list.
- Logs: clean

### sync-check: FAIL (15s)
- Screenshots: [sync-check-1.png, sync-check-fail.png]
- Failure: Sync indicator shows error icon after 10s wait
- Logs: "SocketException: Failed host lookup" at 14:32:05
- Suggested defect: sync feature, connectivity handling
```

### Failure Handling

| Scenario | Behavior |
|----------|----------|
| Flow fails | Mark FAIL, capture screenshot + logs, continue to next flow in wave |
| Flow fails + has dependents | Orchestrator marks dependent flows as SKIP in subsequent waves |
| App crashes | Agent detects via `adb shell pidof`, attempts relaunch, marks flow FAIL if unrecoverable |
| Element not found | Retry UIAutomator dump once after 3s wait. If still missing, try vision fallback. Then FAIL. |
| Agent itself errors | Orchestrator catches, marks entire wave as ERROR, continues remaining waves |

## Output & Reporting

### Report File

Saved to `.claude/test-results/YYYY-MM-DD-HHmm-run.md`:

```markdown
# Test Run 2026-03-03 14:30

**Branch**: fix/sync-dns-resilience
**Trigger**: /test (auto-selected from git diff)
**Flows selected**: login, create-project, create-entry, submit-entry, sync-check
**Device**: Pixel 7a (adb devices)

## Summary: 3/5 PASS | 1 FAIL | 1 SKIP

| Flow | Status | Duration | Wave |
|------|--------|----------|------|
| login | PASS | 12s | 0 |
| create-project | PASS | 8s | 1 |
| sync-check | PASS | 15s | 1 |
| create-entry | FAIL | 25s | 2 |
| submit-entry | SKIP | — | 3 |

## Failures

### create-entry (Wave 2)
**Symptom**: Location field shows perpetual loading spinner.
**Screenshot**: screenshots/create-entry-fail.png
**Logs**: ...
**Suggested root cause**: ...

## Screenshots
- screenshots/login-1.png
- screenshots/create-entry-fail.png
- ...
```

### Defect Auto-Filing

When a flow fails, the orchestrator appends to `.claude/defects/_defects-{feature}.md`:

```markdown
### DEFECT: create-entry flow failure (2026-03-03 auto-test)
**Status**: OPEN
**Source**: Automated test run
**Symptom**: Location field stuck loading, save button disabled
**Logs**: LocationProvider._fetchLocation called with null location_id
**Screenshot**: .claude/test-results/2026-03-03-1430-run/screenshots/create-entry-fail.png
**Related**: BLOCKER-22
```

Orchestrator checks for existing open defects with matching symptoms before filing to avoid duplicates.

### Chat Summary

```
Test Run: 3/5 PASS | 1 FAIL | 1 SKIP

❌ create-entry: Location field stuck loading (→ _defects-entries.md)
⏭️ submit-entry: skipped (depends on create-entry)

Report: .claude/test-results/2026-03-03-1430-run.md
Screenshots: .claude/test-results/2026-03-03-1430-run/screenshots/
Defects filed: 1 new (entries)
```

### Retention

Only the 5 most recent run directories are kept. Orchestrator deletes older ones at the start of each run.

### Directory Structure

```
.claude/test-results/
├── 2026-03-03-1430-run.md
├── 2026-03-03-1430-run/
│   └── screenshots/
│       ├── login-1.png
│       └── ...
└── (older runs)
```

## File Layout

```
.claude/
├── skills/
│   └── test/
│       ├── test.md                    # Skill entry point
│       └── references/
│           ├── adb-commands.md        # ADB command reference for agents
│           └── uiautomator-parsing.md # XML parsing + element finding
├── agents/
│   ├── test-orchestrator-agent.md     # Orchestrator agent definition
│   └── test-wave-agent.md            # Wave task agent definition
└── test-flows/
    └── registry.md                    # Flow registry
```

## Orchestrator Responsibilities

```
test-orchestrator-agent (Sonnet):
1. Read .claude/test-flows/registry.md
2. If "auto": git diff → feature mapping → flow selection + deps
3. Compute waves via topological sort on deps
4. Verify ADB device connected (adb devices)
5. Build APK inline (pwsh build.ps1 -Platform android)
6. Install + launch app (adb install, adb shell am start)
7. For each wave:
   a. Dispatch test-wave-agent with:
      - Flows for this wave
      - Previous wave results
      - App package/activity info
      - Screenshot output dir
   b. Collect results
   c. If flow FAIL → mark dependents SKIP in future waves
8. Write report to .claude/test-results/
9. File defects for failures
10. Print chat summary
11. Clean up old test runs (keep 5)
```

## Wave Agent Responsibilities

```
test-wave-agent (Sonnet):
1. For each flow in wave (sequential):
   a. Read flow steps + key-elements + verify criteria
   b. For each step:
      - uiautomator dump → parse XML → find element
      - tap/input via ADB
      - wait → screencap → vision verify
   c. After all steps: verify criteria via screenshot
   d. Collect logcat output
   e. Mark PASS/FAIL with observations
2. Pull all screenshots to local dir
3. Return structured results to orchestrator
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Interaction | Hybrid (UIAutomator + Vision) | Precise taps + visual understanding |
| Flow source | Registry + git diff + user override | Automation with control |
| Build step | Orchestrator inline | Simple, no wasted agent |
| Execution | Dependency waves | Logical ordering, fresh context per wave |
| Agent model | Sonnet | Vision capable, cost-efficient |
| Output | Report file + chat summary + defect filing | Persistent + immediate + actionable |
| Orchestrator sees | Wave summaries only | Context stays thin |

## Implementation Phases

### Phase 0: Foundation (registry + reference docs)

- Create `.claude/test-flows/registry.md` with 5 starter flows (login, create-project, create-entry, submit-entry, sync-check)
- Create `references/adb-commands.md` — ADB command patterns for tap, input, screencap, uiautomator, logcat, app launch/kill
- Create `references/uiautomator-parsing.md` — XML structure, element finding by resource-id/text, bounds parsing to coordinates

### Phase 1: Agents (orchestrator + wave agent definitions)

- Create `test-orchestrator-agent.md` — full prompt with wave computation, build steps, dispatch loop, report generation, defect filing
- Create `test-wave-agent.md` — full prompt with ADB interaction loop, UIAutomator parsing, vision verification, failure handling
- Create `skills/test/test.md` — skill entry point

### Phase 2: Integration (git diff mapping + TestingKeys audit)

- Add feature-to-path mapping in orchestrator (or as a reference file)
- Audit existing `TestingKeys` in `lib/shared/testing_keys/` — ensure key flows have resource-ids on critical elements
- Add missing keys if needed for the 5 starter flows

### Phase 3: Dry Run & Iterate

- Run `/test login` end-to-end on connected device
- Fix agent prompts based on actual ADB output, XML format, screenshot quality
- Expand to full `/test` (all flows) once login works reliably
