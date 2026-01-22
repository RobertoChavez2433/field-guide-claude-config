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

## Platform Requirements (2026 Standards)

### Android
| Component | Version | Notes |
|-----------|---------|-------|
| compileSdk | 35 | Android 15 - Latest stable |
| targetSdk | 35 | Required for Play Store |
| minSdk | 24 | Android 7.0 - Drops devices older than 7 years |
| Gradle | 8.14 | Latest stable |
| Kotlin | 2.2.20 | Latest stable |
| Java | 17 | LTS version |

### iOS
| Component | Version | Notes |
|-----------|---------|-------|
| Minimum iOS | 15.0 | Drops iOS 13/14 for better performance |
| Xcode | 15.0+ | Required for iOS 15+ support |

### Test Configuration
| Setting | Value | Purpose |
|---------|-------|---------|
| Test Orchestrator | 1.5.2 | Proper test isolation |
| JVM Heap (Tests) | 12G | Prevents OOM in long test runs |
| Max Tests Per Batch | 5 | Memory resets between batches |
| Patrol | 3.20.0 | Native automation |

### Key Files
- `android/app/build.gradle.kts` - SDK versions, test options
- `android/gradle.properties` - JVM heap, Gradle settings
- `ios/Runner.xcodeproj/project.pbxproj` - iOS deployment target
- `.claude/docs/2026-platform-standards-update.md` - Full documentation

## Repositories
| Repo | URL |
|------|-----|
| App Code | https://github.com/RobertoChavez2433/construction-inspector-tracking-app |
| Claude Config | https://github.com/RobertoChavez2433/field-guide-claude-config |

`.claude/` is gitignored from app repo and tracked separately.
