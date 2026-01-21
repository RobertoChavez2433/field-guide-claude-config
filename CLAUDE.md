# Construction Inspector App

Cross-platform mobile/desktop app for construction inspectors. Offline-first with cloud sync.

## Quick Reference
@.claude/memory/tech-stack.md
@.claude/memory/standards.md
@.claude/memory/defects.md

## Project Structure
```
lib/
├── core/        # Router, theme, config, database
├── shared/      # Base classes, utilities
├── features/    # 12 features: auth, contractors, dashboard, entries, locations,
│                # pdf, photos, projects, quantities, settings, sync, weather
├── data/        # LEGACY: barrel re-exports
├── presentation/# LEGACY: barrel re-exports
└── services/    # Cross-cutting (photo, image, permission)
```

## Key Files
| File | Purpose |
|------|---------|
| `lib/main.dart` | Entry, providers |
| `lib/core/router/app_router.dart` | Routes |
| `lib/core/database/database_service.dart` | SQLite schema |
| `lib/features/sync/` | Sync orchestrator |

## Domain Guidelines
@.claude/rules/frontend/ (UI patterns)
@.claude/rules/backend/ (Data layer)
@.claude/rules/auth/ (Authentication)

## Agents
| Agent | Use For |
|-------|---------|
| `flutter-specialist-agent` | Screens, widgets, performance |
| `data-layer-agent` | Models, repositories, providers |
| `supabase-agent` | Sync, schema, RLS |
| `auth-agent` | Auth flows |
| `qa-testing-agent` | Testing, debugging |
| `code-review-agent` | Architecture, code quality |
| `pdf-agent` | PDF generation |
| `planning-agent` | Requirements, implementation plans |

## Session
- `/resume-session` - Load context
- `/end-session` - Save state
- State: `.claude/plans/_state.md`
- Plan: `.claude/implementation/implementation_plan.md`

## Git Rules
- **NEVER** include "Co-Authored-By" in commits
- User is sole author

## Data Flow
```
Screen -> Provider -> Repository -> SQLite (local) -> Supabase (sync)
```

## Repositories
| Repo | URL |
|------|-----|
| App Code | https://github.com/RobertoChavez2433/construction-inspector-tracking-app |
| Claude Config | https://github.com/RobertoChavez2433/field-guide-claude-config |

`.claude/` is gitignored from app repo and tracked separately.
