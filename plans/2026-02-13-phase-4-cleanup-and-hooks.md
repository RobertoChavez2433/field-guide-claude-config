# Phase 4: Cleanup, Reference Fixes, and Native Hooks

**Created**: 2026-02-13
**Status**: APPROVED
**Goal**: Make `.claude/` directory impeccable — zero broken references, zero orphans, and 3 native Claude Code hooks enforcing quality automatically.

---

## Workstream 1: Fix Broken References (16 issues)

### 1A. Fix feature docs paths in state JSONs

All state JSON files reference `docs/feature-*` but actual path is `docs/features/feature-*`.

**Files to fix** (13 per-feature state JSONs + FEATURE-MATRIX.json):
| File | Change |
|------|--------|
| `state/FEATURE-MATRIX.json` | All 13 `"overview"` and `"architecture"` paths: `docs/feature-*` → `docs/features/feature-*` |
| `state/feature-pdf.json` | `overview` + `architecture` paths |
| `state/feature-sync.json` | `overview` + `architecture` paths |
| `state/feature-auth.json` | `overview` + `architecture` paths |
| `state/feature-entries.json` | `overview` + `architecture` paths |
| `state/feature-photos.json` | `overview` + `architecture` paths |
| `state/feature-contractors.json` | `overview` + `architecture` paths |
| `state/feature-dashboard.json` | `overview` + `architecture` paths |
| `state/feature-locations.json` | `overview` + `architecture` paths |
| `state/feature-projects.json` | `overview` + `architecture` paths |
| `state/feature-quantities.json` | `overview` + `architecture` paths |
| `state/feature-settings.json` | `overview` + `architecture` paths |
| `state/feature-toolbox.json` | `overview` + `architecture` paths |
| `state/feature-weather.json` | `overview` + `architecture` paths |

### 1B. Fix PRD path references

PRDs live in `prds/` not `plans/`. Fix all files referencing the old path.

**Files to fix**:
| File | Old Path | New Path |
|------|----------|----------|
| `state/feature-pdf.json` | `plans/2026-02-11-pdf-extraction-pipeline-v2-prd-2.0.md` | `prds/pdf-extraction-v2-prd-2.0.md` |
| `state/FEATURE-MATRIX.json` | `plans/2026-02-11-pdf-extraction-pipeline-v2-prd-2.0.md` | `prds/pdf-extraction-v2-prd-2.0.md` |
| `architecture-decisions/pdf-v2-constraints.md` | any `plans/` PRD references | `prds/` |
| `autoload/_state.md` | any `plans/` PRD references in Active Plans | `prds/` |

**Verify**: Check all state JSONs for `prd` fields — ensure they point to `prds/` directory.

### 1C. Fix auth constraint reference

| File | Old Reference | Correct Reference |
|------|---------------|-------------------|
| `state/feature-auth.json` | FIXED — renamed file to `auth-constraints.md` | `auth-constraints.md` |

### 1D. Fix frontend agent system.md reference

| File | Line | Fix |
|------|------|-----|
| `agents/frontend-flutter-specialist-agent.md` | ~202 | Remove or fix `system.md` reference |

**Action**: Read the agent file, find the reference, determine if it should be `design-system.md` or removed entirely.

---

## Workstream 2: Clean Up Orphaned Files (9 files)

### 2A. Archive completed planning docs to `plans/completed/`

These files served their purpose — they led to the current documentation system. Archive, don't delete.

| File | Reason |
|------|--------|
| `IMPLEMENTATION-ROADMAP.md` | Phases 0-3 complete, Phase 4 is this plan |
| `FILING-SYSTEM.md` | Design doc that produced current directory structure |
| `CONTEXT-VISION.md` | Vision doc that produced current system |
| `analysis-workflow-improvements.md` | Inspiration doc, recommendations implemented |
| `SESSION-SKILLS-IMPLEMENTATION-PLAN.md` | Skills system implemented |
| `PHASE-0-CHECKLIST.md` | Phase 0 completed |
| `SESSION-323-INCIDENT-REPORT.md` | Historical incident report |

**Action**: Move all 7 files to `plans/completed/` (directory already exists).

### 2C. Delete artifacts

| File | Reason |
|------|--------|
| `architecture-decisions${feature}-constraints.md` | Template artifact with literal `${feature}` in filename. Contains duplicate weather constraints. |

**Action**: Verify it's truly a duplicate of `weather-constraints.md`, then delete.

### 2D. Evaluate settings.local.json

| File | Action |
|------|--------|
| `settings.local.json` | Read contents. If empty or contains only defaults, delete. If it has local hook config or permissions, keep. |

### 2E. Remove legacy defects redirect

| File | Action |
|------|--------|
| `autoload/_defects.md` | Delete — per-feature defect files in `defects/` are the canonical source now. Verify no agent files still have `@.claude/autoload/_defects.md` references first. If they do, remove those references. |

---

## Workstream 3: Wire Native Claude Code Hooks (3 hooks)

### 3A. Create/update `.claude/settings.json`

Read existing `settings.json` first — merge hooks config into it, don't overwrite existing settings.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post-edit-validate.sh",
            "timeout": 120,
            "statusMessage": "Running dart analyzer..."
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check-doc-staleness.sh",
            "timeout": 10,
            "statusMessage": "Checking doc freshness..."
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-agent-dispatch.sh",
            "timeout": 120,
            "statusMessage": "Pre-flight agent validation..."
          }
        ]
      }
    ]
  }
}
```

### 3B. Write Hook 1: Post-Edit Analyzer

**File**: `.claude/hooks/post-edit-validate.sh`

**Behavior**:
1. Read JSON event from stdin (contains `tool_input.file_path`)
2. Extract file path from the event
3. Early-exit (exit 0) if file is not `.dart`
4. Run `pwsh -Command "dart analyze {FILE_PATH} --no-fatal-infos"`
5. Parse output for errors (not warnings/info)
6. If errors found: output JSON `{"systemMessage": "Analyzer errors in {FILE}: {ERROR_DETAILS}. Fix before continuing."}` and exit 0
7. If clean: silent exit 0

**Edge cases**:
- File might be in a package subdirectory — use full absolute path
- Analyzer might fail if pubspec is broken — catch and report
- Only report errors, not warnings or info (--no-fatal-infos flag)

### 3C. Write Hook 2: Doc Staleness Check

**File**: `.claude/hooks/check-doc-staleness.sh`

**Behavior**:
1. Read JSON event from stdin (contains `transcript_path`)
2. Read transcript JSONL file
3. Find all Write/Edit tool uses where `file_path` matches `lib/features/*/`
4. Extract unique feature names from paths (e.g., `lib/features/pdf/...` → `pdf`)
5. Find all Write/Edit tool uses where `file_path` matches `docs/features/feature-*`
6. Extract feature names from doc paths
7. Compute `modified_features - documented_features` = stale features
8. If stale features exist: output JSON `{"systemMessage": "Code modified for feature(s) [{FEATURES}] but docs were not updated. Consider updating: docs/features/feature-{FEATURE}-overview.md"}`
9. If no stale features: silent exit 0

**Edge cases**:
- Transcript might be large — only scan for Write/Edit entries, skip reads
- Feature name extraction must handle nested paths: `lib/features/pdf/services/extraction/...` → `pdf`
- Skip if no `.dart` files were edited (e.g., only JSON/MD changes)

### 3D. Update Hook 3: Sub-Agent Pre-Flight

**File**: `.claude/hooks/pre-agent-dispatch.sh` (already exists — rewrite for native hook format)

**Behavior**:
1. Read JSON event from stdin (contains agent type info)
2. **Dependency check**: Run `pwsh -Command "dart pub get --dry-run 2>&1"`
   - If errors → exit 2 with stderr: "Dependencies not resolved. Run 'flutter pub get' first."
3. **Analyzer baseline**: Run `pwsh -Command "dart analyze lib/ --no-fatal-infos 2>&1"`
   - Count error lines (not warnings)
   - If errors > 0 → exit 2 with stderr: "Codebase has {N} analyzer errors. Fix before spawning agents."
4. **Pass**: exit 0

**Note**: Removed spawn-limit check from earlier design — Claude Code doesn't expose active agent count to hooks. The spawn limit (max 3) is documented in AGENT-CHECKLIST.json and agent instructions instead.

### 3E. Make all hook scripts executable

```bash
chmod +x .claude/hooks/post-edit-validate.sh
chmod +x .claude/hooks/check-doc-staleness.sh
chmod +x .claude/hooks/pre-agent-dispatch.sh
```

### 3F. Delete old unused hook

**File**: `.claude/hooks/post-agent-coding.sh`

This was the manual post-work script. Its functionality is now covered by:
- Hook 1 (analyzer runs automatically after every edit)
- Agent instructions (agents verify constraints from their frontmatter)

**Action**: Delete after confirming Hook 1 is working.

---

## Workstream 4: Update State Files and CLAUDE.md

### 4A. Update `autoload/_state.md`

- Remove references to "4-path resume-session" in session 332 notes
- Update Active Plans to reference this plan instead of IMPLEMENTATION-ROADMAP.md
- Clean up any `plans/` PRD path references

### 4B. Update CLAUDE.md

Add hooks section to the Documentation System area:

```markdown
### Hooks (Native Claude Code)
| Hook | Event | Purpose |
|------|-------|---------|
| `post-edit-validate.sh` | PostToolUse (Write/Edit) | Runs dart analyze on .dart files, reports errors |
| `check-doc-staleness.sh` | Stop | Warns if feature code changed but docs weren't updated |
| `pre-agent-dispatch.sh` | SubagentStart | Validates dependencies and analyzer before spawning agents |

Configured in `.claude/settings.json`. Hooks run automatically — no manual invocation needed.
```

### 4C. Update IMPLEMENTATION-ROADMAP.md (before archiving)

Mark Phase 4 as COMPLETE with summary of what was done, then archive per Workstream 2A.

---

## Execution Order

```
Step 1: Workstream 1 — Fix all broken references (14 files)
        Can be parallelized: agents fix state JSONs + agent files simultaneously

Step 2: Workstream 2 — Clean up orphans (move/delete 9 files)
        Sequential: verify before deleting

Step 3: Workstream 3 — Write and wire hooks (3 scripts + settings.json)
        Sequential: write scripts → configure settings → test

Step 4: Workstream 4 — Update state files and CLAUDE.md
        Sequential: depends on Workstreams 1-3 being complete

Step 5: Verification
        - Run: pwsh -Command "dart analyze lib/"  (baseline clean)
        - Test Hook 1: Edit a .dart file, verify analyzer runs automatically
        - Test Hook 2: Edit lib/features/pdf/ code, verify doc staleness reminder
        - Test Hook 3: Spawn a sub-agent, verify pre-flight runs
        - Grep for any remaining broken paths in .claude/ directory
```

---

## Agent Assignments

| Workstream | Agent | Rationale |
|------------|-------|-----------|
| 1 (References) | Direct edits (no agent needed) | Simple find-and-replace across JSON files |
| 2 (Cleanup) | Direct file moves (no agent needed) | Archive moves, delete artifacts |
| 3 (Hooks) | Direct implementation | Shell scripts, settings.json config |
| 4 (State updates) | Direct edits | CLAUDE.md and _state.md updates |

No sub-agents needed — this is all configuration work, not feature implementation.

---

## Success Criteria

| Metric | How to verify |
|--------|---------------|
| Zero broken references | Grep `.claude/` for all file paths, verify each exists |
| Zero orphaned files | No loose .md files at `.claude/` root (except CLAUDE.md) |
| Hook 1 fires on .dart edits | Edit a .dart file → see "Running dart analyzer..." status |
| Hook 2 fires on Stop | Edit lib/features/pdf/ code → see doc staleness reminder |
| Hook 3 fires on agent spawn | Spawn a Task agent → see "Pre-flight agent validation..." status |
| Docs path consistency | All state JSONs use `docs/features/feature-*` pattern |
| PRD path consistency | All references use `prds/` not `plans/` |
