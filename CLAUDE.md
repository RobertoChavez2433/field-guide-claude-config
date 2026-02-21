# Construction Inspector App

Cross-platform mobile/desktop app for construction inspectors. Offline-first with cloud sync.

## Quick Reference
<!-- Defects: per-feature files in .claude/defects/_defects-{feature}.md -->

## Archives (On-Demand) DO NOT AUTO-LOAD THESE
- `.claude/logs/state-archive.md`
- `.claude/logs/defects-archive.md`

## Project Structure
```
lib/
├── core/        # Router, theme, config, database
├── shared/      # Base classes, utilities
├── features/    # 17 features: auth, calculator, contractors, dashboard, entries, forms,
│                # gallery, locations, pdf, photos, projects, quantities, settings, sync,
│                # todos, toolbox (hub for calculator/forms/gallery/todos), weather
└── services/    # Cross-cutting (photo, image, permission)
```

## Key Files
| File | Purpose |
|------|---------|
| `lib/main.dart` | Entry, providers |
| `lib/core/router/app_router.dart` | Routes |
| `lib/core/database/database_service.dart` | SQLite schema |
| `lib/features/sync/` | Sync orchestrator |

## Domain Rules (with paths: frontmatter)
| Rule | Loads When |
|------|------------|
| `rules/architecture.md` | Any lib/**/*.dart |
| `rules/platform-standards.md` | Android/iOS config files |
| `rules/frontend/flutter-ui.md` | lib/**/presentation/** |
| `rules/backend/data-layer.md` | lib/**/data/** |
| `rules/backend/supabase-sql.md` | Supabase work |
| `rules/auth/supabase-auth.md` | lib/features/auth/** |
| `rules/pdf/pdf-generation.md` | lib/features/pdf/** |
| `rules/sync/sync-patterns.md` | lib/features/sync/** |
| `rules/database/schema-patterns.md` | lib/core/database/** |
| `rules/testing/patrol-testing.md` | integration_test/**, test/** |

## Agents
| Agent | Use For | Phase |
|-------|---------|-------|
| `planning-agent` | Requirements, implementation plans | PLAN |
| `frontend-flutter-specialist-agent` | Screens, widgets, performance | IMPLEMENT |
| `backend-data-layer-agent` | Models, repositories, providers | IMPLEMENT |
| `backend-supabase-agent` | Sync, schema, RLS | IMPLEMENT |
| `auth-agent` | Auth flows | IMPLEMENT |
| `pdf-agent` | PDF generation | IMPLEMENT |
| `code-review-agent` | Architecture, code quality | REVIEW |
| `qa-testing-agent` | Testing, debugging | TEST/VERIFY |

**Note**: All agents must be at root `.claude/agents/` level (no subdirectories).

## Skills (Agent Enhancements)
| Skill | Purpose | Used By |
|-------|---------|---------|
| `brainstorming` | Collaborative design | planning-agent |
| `systematic-debugging` | Root cause analysis | qa-testing-agent |
| `interface-design` | Design system | frontend-flutter-specialist |
| `pdf-processing` | CLI PDF analysis/debugging | pdf-agent |
| `dispatching-parallel-agents` | Coordinate parallel agents, prevent revert conflicts | planning-agent |
| `resume-session` | Load HOT context on session start | User-invoked |
| `end-session` | Session handoff with auto-archiving | User-invoked |

Skills are loaded via `skills:` frontmatter in agent files. Claude auto-delegates to agents based on task description.

## Session
- `/resume-session` - Load HOT context only
- `/end-session` - Save state with auto-archiving
- State: `.claude/autoload/_state.md` (max 5 sessions)
- Defects: Per-feature files in `.claude/defects/` (max 5 per feature)
- Archives: `.claude/logs/state-archive.md`, `.claude/logs/defects-archive.md`

## Directory Reference
| Directory | Purpose |
|-----------|---------|
| plans/ | Implementation plans and design specs |
| prds/ | Product Requirements Documents |
| agent-memory/ | Agent-specific memory (auto-managed) |
| defects/ | Per-feature defect tracking files |
| logs/ | Archives (state, defects, archive-index) |
| code-reviews/ | Code review reports (auto-saved by code-review-agent) |
| hooks/ | Pre-flight and post-work validation scripts |
| test-results/ | UI test findings per journey run |

## Documentation System
`.claude/docs/` — Feature overviews + architecture docs (lazy-loaded by agents)
`.claude/architecture-decisions/` — Feature-specific constraints + shared rules
`.claude/state/` — JSON state files for project tracking
`.claude/hooks/` — Pre-flight + post-work validation scripts
Agents load feature docs on demand; see `state/feature-{name}.json` per feature.

## Quick Reference Commands

**CRITICAL**: Git Bash silently fails on Flutter. ALWAYS use pwsh wrapper.

### Build & Run
1. `pwsh -Command "flutter run -d windows"`                                    — Run on desktop
2. `pwsh -Command "flutter clean && flutter build apk --release"`              — Build APK
3. `pwsh -Command "flutter clean"`                                             — Clean build artifacts

### Testing
4. `pwsh -Command "flutter test"`                                              — All tests

### Process Management (SAFE — preserves MCP servers)
5. `pwsh -Command "Stop-Process -Name 'construction_inspector' -Force -ErrorAction SilentlyContinue"`  — Kill app ONLY

### Dependencies & Diagnostics
6. `pwsh -Command "flutter pub get"`       — Get dependencies
7. `pwsh -Command "flutter pub upgrade"`   — Upgrade dependencies
8. `pwsh -Command "flutter analyze"`       — Static analysis
9. `pwsh -Command "flutter doctor"`        — Environment diagnostics

### Git
10. `git log --oneline -10`                 — Recent commits
11. `git diff --stat`                       — Change summary

### Common Mistakes (from 577+ errors across 30+ sessions)
- NEVER run flutter/dart directly in Git Bash — ALWAYS use `pwsh -Command "..."`
- NEVER use wc, sed, awk, grep as Bash — use Read/Edit/Grep tools instead
- ALWAYS use `-ErrorAction SilentlyContinue` on Stop-Process
- ALWAYS set `timeout: 600000` on `flutter run` commands (default 120s is too short)
- ALWAYS quote paths with spaces: `"C:\Users\rseba\Projects\Field Guide App"`
- **NEVER run `Stop-Process -Name 'dart'`** — this kills MCP servers (dart-mcp), not just the app. Only kill `construction_inspector`.

## Development Tools
| Tool | Location | Purpose |
|------|----------|---------|
| run_and_tail_logs.ps1 | `tools/` | Run app with live log tailing |
| dump_inspect.py | `tools/` | Crash dump analysis |

## Data Flow
```
Screen -> Provider -> Repository -> SQLite (local) -> Supabase (sync)
```

## Platform Requirements
See `.claude/rules/platform-standards.md` for Android SDK (compileSdk 36/targetSdk 36/minSdk 24/Gradle 8.14/AGP 8.11.1), iOS 15.0+, and test config (Orchestrator 1.6.1 / JVM 12G / Patrol 4.1.0).

## Repositories
| Repo | URL |
|------|-----|
| App Code | https://github.com/RobertoChavez2433/construction-inspector-tracking-app |
| Claude Config | https://github.com/RobertoChavez2433/field-guide-claude-config |

`.claude/` is gitignored from app repo and tracked separately.

## Audit System & Lint Suggestions

**Backlogged plan**: `.claude/backlogged-plans/2026-02-15-audit-system-design.md`

### Git Workflow (Feature Branch + PR)
- Work on feature branches, never commit directly to main
- Use `gh pr create` to open PRs, `gh pr merge --squash` to merge
- Pre-commit hook at `tools/audit/pre-commit.sh` validates every commit (not yet implemented)
- CI (`quality-gate.yml`) must pass before merging to main

### Lint Rule Suggestions (Per-Session Check)
Each session, after completing implementation work, check:
1. Did we encounter a new anti-pattern or recurring issue during this session?
2. Could it be caught by a grep pattern or custom lint rule?
3. If yes, suggest it to the user: "I noticed [pattern]. Want to add this as a [grep check / custom lint rule]?"
4. Reference: 68 existing checks in the audit system plan

### Pre-Commit Hook
- Location: `tools/audit/pre-commit.sh` (symlinked from `.git/hooks/pre-commit`) **(not yet implemented)**
- Setup: Run `tools/audit/setup-hooks.sh` once after cloning **(not yet implemented)**
- Hook scripts do not yet exist on disk. Run `tools/audit/setup-hooks.sh` once they are created.
- Bypass (WIP only): `git commit --no-verify` (CI will still catch issues)

## UI Testing via dart-mcp (Standardized Procedure)

Uses dart-mcp MCP server + Flutter Driver extension for app interaction.

### Prerequisites (already set up)
- `flutter_driver` is a dev dependency in `pubspec.yaml`
- `lib/driver_main.dart` — entry point that calls `enableFlutterDriverExtension()` before `app.main()`
- Dialogs guarded with `const bool.fromEnvironment('FLUTTER_DRIVER')` to auto-skip (Driver can't interact with overlays)

### Launch Sequence (3 calls)
```
1. mcp__dart-mcp__launch_app(root: "C:\Users\rseba\Projects\Field Guide App", device: "windows", target: "lib/driver_main.dart")
   → Returns { dtdUri, pid }
2. mcp__dart-mcp__connect_dart_tooling_daemon(uri: <dtdUri>)
3. mcp__dart-mcp__get_widget_tree(summaryOnly: true) — verify app state
```

### Interacting with the App
- **Use `flutter_driver` commands**: `tap`, `enter_text`, `get_text`, `scroll`, `screenshot`, `waitFor`
- **Find widgets by**: `ByValueKey` (preferred), `ByText`, `ByType`, `BySemanticsLabel`
- **Screenshots**: `flutter_driver` `screenshot` command returns the image directly — use this, not VM service HTTP
- **Always `get_widget_tree` first** to discover keys/text before attempting taps

### Flutter Driver Limitations (CRITICAL — do NOT retry, work around)
| Limitation | Workaround |
|------------|------------|
| **Can't find widgets in dialog overlays** (AlertDialog, BottomSheet, showDialog) | Guard dialogs with `FLUTTER_DRIVER` env check to auto-skip in driver mode |
| **`timeout` int param causes type cast error** in dart-mcp | Don't pass `timeout` parameter to flutter_driver commands |
| **Nested finders (Descendant/Ancestor) fail** — JSON serialization bug in dart-mcp | Use `ByValueKey` or `ByText` instead. Add `ValueKey` to widgets if needed |
| **Widget tree can be 250K+ chars** — overflows tool output | Use `screenshot` for visual state. Parse tree with python/jq, don't read raw JSON |
| **`waitFor`/`tap` timeout = driver can't find widget** | Don't retry the same finder. Check if widget is in an overlay or use a different finder type |

### Widget Tree Parsing (when screenshot isn't enough)
When `get_widget_tree` output is saved to file, extract text/keys efficiently:
```python
# Extract labeled widgets from saved widget tree JSON
python -c "import sys,json; [extract logic]" < tree.txt
```
Or use `Grep` on the saved file for `textPreview` or `keyValueString`.

### Adding Testability to Widgets
When flutter_driver can't find a widget, add a `ValueKey` in source code and `hot_reload`:
```dart
TextButton(key: const ValueKey('my_button'), ...)
```
Keys MUST be added to widgets BEFORE they render — hot reload won't update already-built dialogs.

### If Build Fails (PDB lock / stale build / native_assets)
```
pwsh -Command "Stop-Process -Name 'construction_inspector' -Force -ErrorAction SilentlyContinue; Start-Sleep 2; Remove-Item -Recurse -Force 'C:\Users\rseba\Projects\Field Guide App\build' -ErrorAction SilentlyContinue"
mkdir -p "C:/Users/rseba/Projects/Field Guide App/build/native_assets/windows"
pwsh -Command "Set-Location 'C:\Users\rseba\Projects\Field Guide App'; flutter pub get; flutter build windows --debug"
```
**CRITICAL**: Always create `build/native_assets/windows` before building — cmake install fails without it.

### Rules
- **NEVER** `Stop-Process -Name 'dart'` — kills MCP servers
- **ONLY** `Stop-Process -Name 'construction_inspector'` to kill app
- After app crash: just call `launch_app` again — MCP servers survive
- Findings: `.claude/test-results/YYYY-MM-DD-ui-test-findings.md`
- **If a driver command times out, DON'T retry the same command** — diagnose why (overlay? missing key? wrong finder?)

## Widget Test Harness (Isolated Screen Testing)

Purpose: render one screen at a time with real providers backed by in-memory SQLite for faster, lower-load UI testing than full-app launch.

### Launch Sequence (harness config + entry point)
1. Write `harness_config.json` at project root with target screen + optional data.
2. `mcp__dart-mcp__launch_app(root: "C:\Users\rseba\Projects\Field Guide App", device: "windows", target: "lib/test_harness.dart")`
3. `mcp__dart-mcp__connect_dart_tooling_daemon(uri: <dtdUri>)`
4. Use `flutter_driver` commands (`screenshot`, `tap`, `enter_text`, `get_text`, `waitFor`) against the rendered screen.

### `harness_config.json` Format
```json
{
  "screen": "ProctorEntryScreen",
  "data": {
    "responseId": "test-response-001"
  }
}
```
- `screen`: registry key from harness screen registry.
- `data`: optional per-screen constructor/seed inputs.

### Available Screens
- Screens are defined in the harness registry file (single source of truth): `lib/test_harness/screen_registry.dart`.
- Current scope includes 0582B forms screens plus standalone app screens supported by the harness provider stack.

### Add a New Screen to Harness
1. Add a registry entry in `lib/test_harness/screen_registry.dart` (`'ScreenName': (data) => Screen(...)`).
2. Add `ValueKey` coverage for interactive elements in the screen widget.
3. Add/update keys in `lib/shared/testing_keys/testing_keys.dart`.
4. If the screen needs extra context, extend harness seeding (`harness_config.json` `data` + seed helper) before launch.

## Context Efficiency

Rules to minimize token waste across sessions:

### Subagent Usage
- **Prefer parallel Task calls** in a single message over `run_in_background`. Parallel calls already run concurrently without polling overhead.
- When `run_in_background` is necessary, read output **exactly once** using `block=true` to wait for completion. Never poll with timeout then re-read.
- **Never call TaskOutput more than once** for the same subagent.
- Cap **Explore agents at 3 per session**. Use Glob/Grep/Read directly for targeted file searches.
- Only spawn a subagent when the task genuinely requires 5+ tool calls. For simpler work, do it inline.

### Context Hygiene
- Don't echo back file contents already in context.
- When summarizing subagent results to the user, keep it to 3-5 bullets. Don't paste the full agent output.
- Prefer file:line references over pasting code blocks when discussing changes.
