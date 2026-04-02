# Construction Inspector App

Cross-platform mobile/desktop app for construction inspectors. Offline-first with cloud sync.

**HARD CONSTRAINT: Security is non-negotiable. No shortcuts that bypass approval flows, weaken RLS, or create privilege escalation paths.**

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

## Data Flow
```
Screen -> Provider -> UseCase -> Repository -> SQLite (local) -> Supabase (sync)
```

## Domain Rules (lazy-loaded via paths: frontmatter)
| Rule | Loads When |
|------|------------|
| `rules/architecture.md` | Any lib/**/*.dart |
| `rules/platform-standards.md` | Android/iOS config files |
| `rules/frontend/flutter-ui.md` | lib/**/presentation/** |
| `rules/frontend/ui-prototyping.md` | mockups/** |
| `rules/backend/data-layer.md` | lib/**/data/** |
| `rules/backend/supabase-sql.md` | Supabase work |
| `rules/auth/supabase-auth.md` | lib/features/auth/** |
| `rules/pdf/pdf-generation.md` | lib/features/pdf/** |
| `rules/sync/sync-patterns.md` | lib/features/sync/** |
| `rules/database/schema-patterns.md` | lib/core/database/** |
| `rules/testing/patrol-testing.md` | test/**, integration_test/**, lib/test_harness/** |

## Quick Reference Commands

**CRITICAL**: Git Bash silently fails on Flutter. ALWAYS use pwsh wrapper.

### Build & Run
1. `pwsh -File tools/build.ps1 -Platform android` — Release APK
2. `pwsh -File tools/build.ps1 -Platform windows` — Windows build
3. `pwsh -File tools/build.ps1 -Platform android -BuildType debug` — Debug APK
4. `pwsh -Command "flutter run -d windows"` — Desktop dev

### Testing & Diagnostics
5. `pwsh -Command "flutter test"` — All tests
6. `pwsh -Command "flutter pub get"` — Get dependencies
7. `pwsh -Command "flutter analyze"` — Static analysis

### Supabase CLI
8. `npx supabase db push` — Push pending migrations to remote
9. `npx supabase db pull` — Pull remote schema changes
10. `npx supabase db diff` — Diff local vs remote schema

### Process Management
11. `pwsh -Command "Stop-Process -Name 'construction_inspector' -Force -ErrorAction SilentlyContinue"` — Kill app ONLY

### Common Mistakes
- NEVER run flutter/dart directly in Git Bash — ALWAYS use `pwsh -Command "..."`
- NEVER use wc, sed, awk, grep as Bash — use Read/Edit/Grep tools instead
- ALWAYS use `-ErrorAction SilentlyContinue` on Stop-Process
- ALWAYS set `timeout: 600000` on `flutter run` commands (default 120s too short)
- ALWAYS quote paths with spaces
- **NEVER run `Stop-Process -Name 'dart'`** — kills MCP servers. Only kill `construction_inspector`.

## Session & Workflow
- `/resume-session` — Load HOT context | `/end-session` — Save state with auto-archiving
- State: `.claude/autoload/_state.md` | Defects: GitHub Issues (labeled by feature/type/priority/layer)
- Git: Feature branches only, never commit to main. `gh pr create` / `gh pr merge --squash`
- Planning pipeline: `brainstorming` (spec) → `tailor` (research) → `writing-plans` (plan) → `implement` (execute)
- **Sizing guide:** XS (single-file mechanical) = no skill needed | S (up to 3 files, known pattern) = skip brainstorming + tailor + writing-plans | M+ = full pipeline. Security-sensitive changes (auth, RLS, sync, data exposure) always require full pipeline regardless of size.

## Pointers (on-demand, NOT auto-loaded)
| What | Where |
|------|-------|
| Agents (10 definitions) | `.claude/agents/` — loaded via skills: frontmatter |
| Skills (11 definitions) | `.claude/skills/` — loaded on-demand by agents or user |
| Directory structure | `.claude/docs/directory-reference.md` |
| Platform requirements | `.claude/rules/platform-standards.md` |
| UI prototyping workflow | `.claude/rules/frontend/ui-prototyping.md` |
| Testing setup & harnesses | `.claude/rules/testing/patrol-testing.md` |
| Detailed project knowledge | `.claude/memory/MEMORY.md` |
| Archives | `.claude/logs/state-archive.md` |
| Audit system (backlogged) | `.claude/backlogged-plans/2026-02-15-audit-system-design.md` |

## Repositories
| Repo | URL |
|------|-----|
| App Code | https://github.com/RobertoChavez2433/construction-inspector-tracking-app |
| Claude Config | https://github.com/RobertoChavez2433/field-guide-claude-config |
| CodeMunch Fork | https://github.com/RobertoChavez2433/dart_tree_sitter_fork |

`.claude/` is gitignored from app repo and tracked separately.

## Context Efficiency
- **Prefer parallel Agent calls** over `run_in_background`.
- Cap **Explore agents at 3 per session**. Only spawn subagents for 5+ tool-call tasks.
- Don't echo back file contents already in context. Prefer file:line references over code blocks.
- Summarize subagent results in 3-5 bullets, not full output.
