# Test Output Format Reference

Documentation format templates for test wave agents and the top-level orchestrator. All test runs produce a self-contained results directory with screenshots, logs, flow reports, and a summary.

## Directory Layout

```
.claude/test-results/
  YYYY-MM-DD_HHmm_{descriptor}/     # Per-run directory
    run-summary.md                   # Overall results table
    screenshots/                     # All screenshots
      {flow}-{step:02d}-{desc}.png   # Step screenshots
      {flow}-final.png               # Final verification screenshot
    ui-dumps/                        # UIAutomator XML snapshots
      {flow}-{step:02d}.xml          # Per-step XML hierarchy dump
    logs/                            # Logcat captures
      {flow}-logcat.log              # Per-flow logcat (warnings + flutter)
      full-session.log               # Complete session logcat
    flows/                           # Per-flow detailed reports
      {flow}.md                      # Step-by-step with screenshot refs
```

## Descriptor Naming Convention

The descriptor suffix is derived from the test invocation flags:

| Invocation | Descriptor |
|------------|-----------|
| `/test --smoke` | `_smoke` |
| `/test --entries --sync` | `_entries-sync` |
| `/test --daily-work` | `_daily-work` |
| `/test --full` | `_full` |
| `/test --entries --daily-work` | `_entries_daily-work` |
| `/test login` | `_login` |
| `/test create-entry submit-entry` | `_create-entry_submit-entry` |
| `/test` (auto-select) | `_auto` |

Rules:
- Feature flags are joined with `-` (e.g., `entries-sync`)
- Journey flags keep their hyphenated name (e.g., `daily-work`)
- Mixed feature + journey flags use `_` as separator (e.g., `entries_daily-work`)
- Named flows use `_` as separator (e.g., `create-entry_submit-entry`)
- Auto-select uses `_auto`

## Run Summary Format (`run-summary.md`)

```markdown
# Test Run: YYYY-MM-DD_HHmm_{descriptor}

**Date**: YYYY-MM-DD HH:mm
**Branch**: {git branch name}
**Device**: {model} (Android {version})
**Tier**: {smoke | feature | journey | full | custom}
**Invocation**: /test {flags}
**Duration**: {total time}

## Results

| # | Flow | Status | Duration | Defects | Notes |
|---|------|--------|----------|---------|-------|
| 1 | login | PASS | 45s | 0 | -- |
| 2 | navigate-tabs | PASS | 62s | 0 | -- |
| 3 | create-entry-quick | FAIL | 115s | 1 | Location field stuck loading |

## Summary
- **Total**: {N} | **Pass**: {P} | **Fail**: {F} | **Skip**: {S}
- **Defects filed**: {count} -> GitHub Issues
- **Screenshots**: {count} -> screenshots/
- **Logs**: {count} -> logs/

## Defects Filed

| # | Flow | Feature | Defect ID | Description |
|---|------|---------|-----------|-------------|
| 1 | create-entry-quick | entries | [TEST] 2026-03-03 | Location field stuck loading |

## Wave Execution

| Wave | Flows | Status | Duration |
|------|-------|--------|----------|
| 0 | login | 1/1 PASS | 45s |
| 1 | navigate-tabs, create-entry-quick | 1/2 PASS | 177s |
```

## Flow Report Format (`flows/{flow}.md`)

Each flow gets a detailed step-by-step report. Wave agents write these during execution.

```markdown
# Flow: {flow-name}

**Status**: PASS | FAIL | SKIP
**Duration**: {seconds}s
**Steps**: {completed}/{total}
**Feature**: {feature-name}
**Wave**: {wave-number}

## Steps

### Step 1: {step description}
- **Action**: {what was done}
- **Element**: {content-desc or text used to find element}
- **Result**: SUCCESS | FAIL | SKIP
- **Screenshot**: ../screenshots/{flow}-01-{desc}.png
- **Logcat**: Clean (0 warnings) | {N} warnings (non-critical) | ERROR: {error text}

### Step 2: {step description}
- **Action**: {what was done}
- **Element**: {content-desc or text used to find element}
- **Result**: SUCCESS
- **Screenshot**: ../screenshots/{flow}-02-{desc}.png
- **Logcat**: Clean

## Verification
- [PASS] {verification criterion 1}
- [PASS] {verification criterion 2}
- [FAIL] {verification criterion 3} -- {what went wrong}

## Logcat Summary
- **Total warnings**: {count}
- **Flutter errors**: {count}
- **Network errors**: {count}
- **Critical**: {any critical log lines, or "None"}

## Notes
{Any observations, timing issues, workarounds applied, or context for future runs}
```

## Screenshot Naming Convention

Format: `{flow}-{step:02d}-{short-description}.png`

Examples:
- `login-01-email-entered.png`
- `login-02-password-entered.png`
- `login-03-sign-in-tapped.png`
- `login-04-dashboard-loaded.png`
- `login-final.png`
- `create-entry-01-calendar.png`
- `create-entry-02-date-selected.png`
- `create-entry-03-location-picked.png`
- `create-entry-final.png`

Rules:
- Step numbers are zero-padded to 2 digits (01, 02, ... 99)
- Short description is lowercase, hyphen-separated, max 30 chars
- Final verification screenshot uses `-final.png` suffix
- Pre-flow state screenshots use `-00-initial.png`

## Logcat File Naming Convention

Format: `{flow}-logcat.log`

Examples:
- `login-logcat.log`
- `create-entry-logcat.log`
- `sync-check-logcat.log`
- `full-session.log` (complete session, captured at end of run)

Content format for per-flow logcat:
```
=== Logcat for flow: {flow-name} ===
=== Captured: YYYY-MM-DD HH:mm:ss ===
=== Filter: *:W (warnings and above) ===

{raw logcat output}

=== Flutter-specific logs ===
{filtered flutter tag output}
```

## UI Dump Naming Convention

Format: `{flow}-{step:02d}.xml`

Examples:
- `login-01.xml`
- `login-02.xml`
- `create-entry-03.xml`
- `sync-check-01.xml`

Rules:
- Step numbers match the corresponding screenshot step numbers
- Contains the raw UIAutomator XML hierarchy dump (`uiautomator dump` output)
- Used for debugging element-finding failures — inspect to see what content-desc/text attributes were available
- Not every step requires a dump — only save when element finding is needed or on failure

## Defect Filing Format

When a flow fails, the wave agent files a defect via GitHub Issues:

```bash
pwsh -File tools/create-defect-issue.ps1 `
    -Title "[TEST] {YYYY-MM-DD}: {flow-name} flow failure (auto-test)" `
    -Feature "{feature}" `
    -Type "defect" `
    -Priority "high" `
    -Layer @("{assessed layer}") `
    -Body "<body below>" `
    -Ref ".claude/test-results/{run-dir}/screenshots/{flow}-{step}-{desc}.png"
```

Body format: The existing markdown template block that follows this line in the source file (Status, Source, Symptom, Step, Logcat, Screenshot, Suggested cause) MUST be preserved as-is. That template becomes the `-Body` parameter value for the script call above.

## Retention Policy

- **Keep last 5 runs** -- the orchestrator deletes the oldest run directory when a 6th run starts
- **Screenshots are gitignored** -- `.claude/test-results/` content is not committed
- **run-summary.md is human-readable** -- designed for quick scanning in any text editor
- **Flow reports reference screenshots with relative paths** -- `../screenshots/` prefix

## Chat Summary Format

After a test run completes, the orchestrator reports to the user in this format:

```
Test Run: X/Y PASS | Z FAIL | W SKIP ({duration})

Failures:
  - [{feature}] {flow-name}: {one-line failure description}
  - [{feature}] {flow-name}: {one-line failure description}

Skipped (upstream dependency failed):
  - {flow-name} (depends on {failed-flow})

Report: .claude/test-results/{run-dir}/run-summary.md
Screenshots: .claude/test-results/{run-dir}/screenshots/ ({count} files)
Defects filed: N new GitHub Issues ({feature1}, {feature2})
```
