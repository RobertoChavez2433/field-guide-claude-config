# Testing System Overhaul — Design Plan

**Date**: 2026-03-03 | **Status**: DESIGN COMPLETE — AWAITING APPROVAL
**Replaces**: Patrol E2E tests (moved to deprecated folder)

## Overview

### Purpose
Replace the broken/outdated Patrol E2E testing system with a fully automated ADB+Vision testing framework that covers the entire app. Tests run on a physical Android device via USB, using UIAutomator for element finding, ADB for interaction, and Claude vision for screenshot verification.

### Scope
- **In scope**: 30 feature flows, 12 journeys, 4 test tiers, flag-based CLI, structured output
- **Out of scope**: iOS testing, emulator support, CI/CD integration (future)

### Success Criteria
- [ ] Single `/test --smoke` runs 3 flows end-to-end without manual intervention
- [ ] `/test --full` exercises all 30 flows + 12 journeys
- [ ] Every run produces a self-contained results folder with screenshots, logs, flow reports
- [ ] Failed flows auto-file defects to `.claude/defects/_defects-{feature}.md`
- [ ] Old Patrol tests moved to `integration_test/_deprecated/`

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Patrol fate | Replace entirely | Old tests outdated/broken; single system to maintain |
| Flow grouping | Feature flags + journey flags | Targeted per-feature + cross-feature integration |
| Test tiers | 4: Smoke / Feature / Journey / Full | Most granular control |
| CLI syntax | Flag style (`/test --entries --smoke`) | Clean, extensible, familiar |
| Old tests | Move to deprecated folder | Don't delete, but stop maintaining |
| Orchestration | Top-level agent dispatches 1-flow wave agents | Avoids BLOCKER-25 (nested Task) and turn exhaustion |
| Output | Per-run directories with date_time_descriptor naming | Clean, self-contained, no junk accumulation |
| Defect filing | Existing `.claude/defects/` system | Consistent with project conventions |

---

## 1. CLI Interface

### Syntax
```
/test --<flag> [--<flag> ...]
```

### Tier Flags
| Flag | What runs | Est. time |
|------|-----------|-----------|
| `--smoke` | 3 smoke flows (login, navigate-tabs, create-entry-quick) | ~2-3 min |
| `--feature` | All 18 feature flows | ~20-30 min |
| `--journey` | All 12 journeys | ~40-60 min |
| `--full` | All flows + all journeys (deduped) | ~60-90 min |

### Feature Flags (run specific feature flows)
| Flag | Flows triggered |
|------|----------------|
| `--auth` | login, register, forgot-password |
| `--projects` | create-project, edit-project |
| `--entries` | create-entry, edit-entry, review-submit |
| `--contractors` | add-contractors |
| `--quantities` | add-quantities |
| `--pdf` | import-pdf |
| `--photos` | capture-photo |
| `--sync` | sync-check |
| `--settings` | settings-theme, edit-profile |
| `--toolbox` | calculator, forms-fill, gallery-browse, todos-crud |

### Journey Flags (run specific journeys)
| Flag | Journey |
|------|---------|
| `--onboarding` | register → profile-setup → company-setup |
| `--daily-work` | login → create-project → create-entry → add-quantities → review-submit → sync-check |
| `--project-setup` | login → create-project → edit-project → import-pdf → add-contractors |
| `--field-documentation` | login → create-entry → capture-photo → forms-fill → add-quantities |
| `--offline-sync` | login → create-entry (offline) → sync-check (reconnect) |
| `--admin-flow` | login (admin) → admin-dashboard → approve-member |
| `--budget-tracking` | login → create-project → import-pdf → add-quantities → quantities-check |
| `--entry-lifecycle` | login → create-entry → edit-entry → capture-photo → review-submit |
| `--multi-day` | login → create-entry (day 1) → create-entry (day 2) → review-submit (both) |
| `--contractor-mgmt` | login → create-project → add-contractors → create-entry → add-contractors (to entry) |
| `--settings-personalization` | login → settings-theme → edit-profile → todos-crud |
| `--data-recovery` | login → create-entry (offline) → sync-check → edit-entry → sync-check |

### Combining Flags
```
/test --smoke --entries          # Smoke flows + entries feature flows
/test --daily-work --sync        # daily-work journey + sync feature flows
/test --auth --projects          # Auth + projects feature flows
```

### Special Flags
| Flag | Behavior |
|------|----------|
| `--all` | Alias for `--full` |
| `--list` | Print available flows/journeys, don't run |
| `--dry-run` | Parse flags, show what would run, don't execute |

---

## 2. Flow Registry

### Format
Each flow in `.claude/test-flows/registry.md`:

```markdown
### {flow-name}
- feature: {feature-name}
- tier: smoke | feature
- timeout: {seconds}
- deps: [{flow-names}]
- steps:
  1. {Action description} → {element to find} → {interaction}
  2. ...
- verify: {success criteria}
- key-elements: [{TestingKey names}]
```

Each journey:
```markdown
### {journey-name}
- tier: journey
- flows: [{ordered flow list}]
- description: {what this proves}
```

### Complete Flow Inventory (30 flows)

#### Smoke Tier (3 flows)

| # | Flow | Feature | Deps | Timeout | Description |
|---|------|---------|------|---------|-------------|
| 1 | `login` | auth | [] | 60s | Email/password login → verify dashboard |
| 2 | `navigate-tabs` | navigation | [login] | 60s | Tap all 4 bottom nav tabs, verify each loads |
| 3 | `create-entry-quick` | entries | [login] | 90s | Create minimal entry (date only), save as draft |

#### Feature Tier (18 flows)

| # | Flow | Feature | Deps | Timeout | Description |
|---|------|---------|------|---------|-------------|
| 4 | `register` | auth | [] | 120s | Create account → profile setup → company setup |
| 5 | `forgot-password` | auth | [] | 90s | Password reset via OTP |
| 6 | `create-project` | projects | [login] | 120s | Create project with name/number/client |
| 7 | `edit-project` | projects | [create-project] | 120s | Edit project, add locations |
| 8 | `create-entry` | entries | [create-project] | 180s | Full entry: location, contractors, quantities, notes |
| 9 | `edit-entry` | entries | [create-entry] | 120s | Reopen draft, modify fields, re-save |
| 10 | `review-submit` | entries | [create-entry] | 120s | Batch review → mark ready → submit |
| 11 | `add-contractors` | contractors | [create-project] | 120s | Add prime + sub contractors with equipment/personnel |
| 12 | `add-quantities` | quantities | [create-project] | 120s | Log quantities against bid items |
| 13 | `import-pdf` | pdf | [create-project] | 180s | Import bid items from PDF |
| 14 | `capture-photo` | photos | [create-entry] | 90s | Take photo, name it, attach to entry |
| 15 | `sync-check` | sync | [login] | 60s | Verify sync runs, check logcat for errors |
| 16 | `settings-theme` | settings | [login] | 60s | Toggle theme, verify change persists |
| 17 | `edit-profile` | settings | [login] | 60s | Edit inspector name/initials |
| 18 | `calculator` | toolbox | [login] | 60s | Open calculator, perform calculation |
| 19 | `forms-fill` | toolbox | [create-project] | 120s | Open form, fill fields, save |
| 20 | `gallery-browse` | toolbox | [login] | 60s | Open gallery, verify photos display |
| 21 | `todos-crud` | toolbox | [login] | 60s | Create, complete, delete a todo |

#### Additional Feature Flows (9 flows for journey support)

| # | Flow | Feature | Deps | Timeout | Description |
|---|------|---------|------|---------|-------------|
| 22 | `profile-setup` | auth | [register] | 90s | Complete profile setup (name, title) |
| 23 | `company-setup` | auth | [profile-setup] | 90s | Select/join company |
| 24 | `admin-dashboard` | settings | [login] | 60s | Open admin panel, view requests |
| 25 | `approve-member` | settings | [admin-dashboard] | 60s | Approve pending member request |
| 26 | `quantities-check` | quantities | [add-quantities] | 60s | Verify budget tracking shows correct totals |
| 27 | `create-entry-day2` | entries | [create-entry] | 120s | Create entry for a different date |
| 28 | `create-entry-offline` | entries | [login] | 120s | Create entry while device is offline |
| 29 | `add-contractors-entry` | contractors | [create-entry, add-contractors] | 90s | Add contractors to an existing entry |
| 30 | `sync-reconnect` | sync | [create-entry-offline] | 90s | Reconnect and verify offline entry syncs |

#### Journey Tier (12 journeys)

| # | Journey | Flows | Description |
|---|---------|-------|-------------|
| J1 | `onboarding` | register → profile-setup → company-setup | New user signup to dashboard |
| J2 | `daily-work` | login → create-project → create-entry → add-quantities → review-submit → sync-check | Full inspector daily workflow |
| J3 | `project-setup` | login → create-project → edit-project → import-pdf → add-contractors | Complete project configuration |
| J4 | `field-documentation` | login → create-entry → capture-photo → forms-fill → add-quantities | Entry with all attachments |
| J5 | `offline-sync` | login → create-entry-offline → sync-reconnect | Offline-first verification |
| J6 | `admin-flow` | login → admin-dashboard → approve-member | Admin member management |
| J7 | `budget-tracking` | login → create-project → import-pdf → add-quantities → quantities-check | Budget tracking end-to-end |
| J8 | `entry-lifecycle` | login → create-entry → edit-entry → capture-photo → review-submit | Single entry: draft → submitted |
| J9 | `multi-day` | login → create-entry → create-entry-day2 → review-submit | Batch work across days |
| J10 | `contractor-mgmt` | login → create-project → add-contractors → create-entry → add-contractors-entry | Contractor setup + entry use |
| J11 | `settings-personalization` | login → settings-theme → edit-profile → todos-crud | Inspector customization |
| J12 | `data-recovery` | login → create-entry-offline → sync-reconnect → edit-entry → sync-check | Offline → sync → edit → sync |

---

## 3. Output Structure

### Directory Layout
```
.claude/test-results/
├── YYYY-MM-DD_HHmm_{descriptor}/     # Per-run directory
│   ├── run-summary.md                 # Overall results table
│   ├── screenshots/                   # All screenshots
│   │   └── {flow}-{step:02d}-{desc}.png
│   ├── ui-dumps/                      # UIAutomator XML snapshots
│   │   └── {flow}-{step:02d}.xml
│   ├── logs/                          # Logcat captures
│   │   ├── {flow}-logcat.log          # Per-flow logcat
│   │   └── full-session.log           # Complete session logcat
│   └── flows/                         # Per-flow detailed reports
│       └── {flow}.md                  # Step-by-step with screenshot refs
```

### Descriptor Naming
| Invocation | Descriptor |
|------------|-----------|
| `/test --smoke` | `_smoke` |
| `/test --entries --sync` | `_entries-sync` |
| `/test --daily-work` | `_daily-work` |
| `/test --full` | `_full` |
| `/test --entries --daily-work` | `_entries_daily-work` |

### Run Summary Format (`run-summary.md`)
```markdown
# Test Run: 2026-03-03_1933_smoke

**Date**: 2026-03-03 19:33
**Branch**: fix/sync-dns-resilience
**Device**: SM-G996U (Android 15)
**Tier**: smoke
**Duration**: 3m 42s

## Results

| # | Flow | Status | Duration | Defects | Notes |
|---|------|--------|----------|---------|-------|
| 1 | login | PASS | 45s | 0 | — |
| 2 | navigate-tabs | PASS | 62s | 0 | — |
| 3 | create-entry-quick | FAIL | 115s | 1 | Location field stuck loading |

## Summary
- **Total**: 3 | **Pass**: 2 | **Fail**: 1 | **Skip**: 0
- **Defects filed**: 1 → .claude/defects/_defects-entries.md
- **Screenshots**: 12 → screenshots/
- **Logs**: 3 → logs/
```

### Flow Report Format (`flows/{flow}.md`)
```markdown
# Flow: create-entry

**Status**: PASS | **Duration**: 138s | **Steps**: 8/8

## Steps

### Step 1: Navigate to Calendar tab
- **Action**: Tap bottom nav "Calendar" button
- **Element**: content-desc="Calendar" in BottomNavigationBar
- **Screenshot**: ../screenshots/create-entry-01-calendar.png
- **Logcat**: Clean (0 warnings)

### Step 2: Select today's date
- **Action**: Tap date cell for 2026-03-03
- **Element**: text="3" in TableCalendar
- **Screenshot**: ../screenshots/create-entry-02-date-selected.png
- **Logcat**: 1 warning (non-critical: "No weather data cached")

## Verification
- ✅ Entry visible in calendar
- ✅ Draft status badge shown
- ✅ No errors in logcat
```

### Retention Policy
- **Keep last 5 runs** — orchestrator deletes oldest on pre-flight
- **Screenshots are gitignored** — .claude/test-results/ is in .gitignore
- `run-summary.md` is human-readable for quick review

---

## 4. Agent Architecture

### Orchestration Flow
```
User: /test --entries --smoke
         │
         ▼
┌─────────────────────────┐
│ TOP-LEVEL AGENT (Main)  │  ← Reads SKILL.md, parses flags
│                         │  ← Resolves flags → flow list (deduped)
│ 1. Pre-flight           │  ← ADB check, APK build/install, create run dir
│ 2. Wave computation     │  ← Topological sort by deps → wave groups
│ 3. Wave dispatch loop   │  ← For each wave: dispatch wave agent(s)
│ 4. Summary              │  ← Write run-summary.md, report to user
└────────┬────────────────┘
         │  Task(subagent_type="test-wave-agent")
         │  1 flow per agent dispatch
         │
    ┌────┴─────┬──────────┐
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│ Wave   │ │ Wave   │ │ Wave   │
│ Agent  │ │ Agent  │ │ Agent  │
│ (flow) │ │ (flow) │ │ (flow) │
└────────┘ └────────┘ └────────┘
    │          │          │
    ▼          ▼          ▼
  Writes:    Writes:    Writes:
  flows/     flows/     flows/
  screenshots/ screenshots/ screenshots/
  logs/      logs/      logs/
```

### Top-Level Agent Responsibilities
1. **Parse flags** → resolve to concrete flow list
2. **Pre-flight**: `adb devices`, check device, build APK if >1h old, install, launch app
3. **Create run directory**: `.claude/test-results/YYYY-MM-DD_HHmm_{descriptor}/` with subdirs
4. **Compute waves**: Topological sort on deps. Flows in same wave have no mutual deps.
5. **Dispatch wave agents**: `Task(subagent_type="test-wave-agent")` with prompt containing:
   - Flow definition (steps, key-elements, verify)
   - Run directory paths (screenshots, logs, flows)
   - Device info (serial, package name)
   - Previous wave results (so agent knows app state)
6. **Check wave results**: Read `flows/{flow}.md` after agent returns
7. **Handle failures**: If flow FAIL → mark dependent flows as SKIP
8. **Write run-summary.md**: Compile all flow results into summary table
9. **Cleanup**: Delete oldest run if >5 exist
10. **Report to user**: 1-line per failure, total pass/fail/skip, path to run dir

### Wave Agent Responsibilities
1. **Phase A (Pre-Check)**: Verify app running (`pidof`), clear logcat
2. **Phase B (Execute Steps)**: For each step:
   - UIAutomator dump → parse XML → find element (content-desc > text > vision)
   - ADB tap/input
   - Wait 1-2s for settle
   - Check logcat (MANDATORY after every interaction)
   - Screenshot → save to `screenshots/{flow}-{step:02d}-{desc}.png`
   - Verify expected state
3. **Phase C (Final Verification)**: Final screenshot, verify success criteria
4. **Phase D (Write Report)**: Write `flows/{flow}.md` with step-by-step results
5. **Phase E (Defects)**: If FAIL, file to `.claude/defects/_defects-{feature}.md`

### Model Selection
| Agent | Model | Rationale |
|-------|-------|-----------|
| Top-level orchestrator | Opus (inherited) | Needs to parse complex flag logic |
| Wave agents | Haiku | Fast, cheap, sufficient for ADB commands + vision |

---

## 5. File Changes

### Files to Create
| File | Purpose |
|------|---------|
| `.claude/test-flows/registry.md` | Complete flow + journey registry (overwrite existing) |
| `.claude/skills/test/SKILL.md` | Updated skill definition with new flags + tiers |
| `.claude/agents/test-wave-agent.md` | Updated wave agent with output structure rules |
| `.claude/skills/test/references/output-format.md` | Documentation format templates for agents |

### Files to Modify
| File | Change |
|------|--------|
| `.claude/agents/test-orchestrator-agent.md` | Remove — orchestration is top-level now |
| `.gitignore` | Ensure `.claude/test-results/` screenshots are ignored |

### Files to Move
| From | To |
|------|-----|
| `integration_test/patrol/` | `integration_test/_deprecated/patrol/` |
| `integration_test/generate_golden_fixtures_test.dart` | Keep (PDF, not E2E) |
| `integration_test/generate_mp_fixtures_test.dart` | Keep (PDF, not E2E) |
| `integration_test/mp_extraction_integration_test.dart` | Keep (PDF, not E2E) |
| `integration_test/printing_diagnostic_test.dart` | Keep (diagnostic) |
| `integration_test/rendering_diagnostic_test.dart` | Keep (diagnostic) |

---

## 6. Implementation Phases

### Phase 0: Deprecate Old Tests
- Move `integration_test/patrol/` to `integration_test/_deprecated/patrol/`
- Keep non-Patrol integration tests (PDF, diagnostics)
- Update `.github/workflows/` to stop running Patrol tests (comment out e2e jobs)
- **Agent**: Bash (simple file moves + CI edits)

### Phase 1: Registry + Output Format
- Write complete `registry.md` with all 30 flows + 12 journeys
- Write `output-format.md` reference document
- Create `.claude/test-results/.gitkeep`
- **Agent**: `backend-data-layer-agent` (structured data definition)

### Phase 2: Skill + Agent Updates
- Rewrite `SKILL.md` with new flag syntax, tier system, flow resolution logic
- Update `test-wave-agent.md` with output structure rules, naming conventions
- Remove `test-orchestrator-agent.md` (top-level orchestration instead)
- **Agent**: `planning-agent` (config/documentation)

### Phase 3: Dry Run — Smoke Tier
- Run `/test --smoke` (3 flows: login, navigate-tabs, create-entry-quick)
- Verify output structure is correct
- Fix any issues with agent prompts or ADB commands
- **Agent**: Manual (user-driven test run)

### Phase 4: Feature Flows Build-Out
- Flesh out all 18 feature flow step definitions
- Ensure key-elements map to actual TestingKeys
- Run `/test --entries` as validation
- **Agent**: `qa-testing-agent`

### Phase 5: Journey Validation
- Run each journey, verify flow chaining works
- Fix dependency issues
- Run `/test --full` end-to-end
- **Agent**: Manual (user-driven)

---

## 7. Edge Cases

### Error Handling
| Scenario | Behavior |
|----------|----------|
| Device disconnected mid-run | FAIL current flow, SKIP remaining, write partial results |
| App crash during flow | Detect via `pidof`, attempt relaunch, FAIL if unrecoverable |
| Flow timeout exceeded | FAIL flow, capture screenshot + logcat, continue next flow |
| Element not found | Wait 3s, re-dump, retry; scroll + vision fallback; FAIL after 2 retries |
| APK build fails | Abort entire run, report build error |
| No device connected | Abort pre-flight, report "no device" |

### Boundaries
- **Max flows per run**: No limit (but --full may take 60-90 min)
- **Max screenshots per flow**: 20 (1 per step + verification)
- **Logcat buffer**: Last 60 warnings per flow
- **Run retention**: 5 most recent runs kept

### Device Workarounds (Android 15 / Samsung SM-G996U)
- Screenshot: `adb exec-out screencap -p > local.png` (not `/sdcard/`)
- Path mangling: `MSYS_NO_PATHCONV=1` prefix on all `/sdcard/` paths
- No resource-id: Use `content-desc` (Semantics) > `text` > vision fallback
- No KEYCODE_ENTER: Tap buttons directly instead
