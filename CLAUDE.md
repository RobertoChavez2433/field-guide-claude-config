# Construction Inspector App

Cross-platform mobile/desktop app for construction inspectors. Offline-first with cloud sync.

## Quick Reference
@.claude/memory/tech-stack.md
@.claude/memory/standards.md
@.claude/memory/defects.md

## Archives (On-Demand)
@.claude/memory/state-archive.md
@.claude/memory/defects-archive.md

## Project Structure
```
lib/
├── core/        # Router, theme, config, database
├── shared/      # Base classes, utilities
├── features/    # 13 features: auth, contractors, dashboard, entries, locations,
│                # pdf, photos, projects, quantities, settings, sync, toolbox, weather
├── data/        # LEGACY: empty directories
├── presentation/# LEGACY: empty directories
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
- `/resume-session` - Load HOT context only (~25KB)
- `/end-session` - Save state with auto-archiving
- State: `.claude/plans/_state.md` (max 10 sessions)
- Defects: `.claude/memory/defects.md` (max 15 defects)
- Archives: `.claude/memory/state-archive.md`, `.claude/memory/defects-archive.md`
- Plan: `.claude/implementation/implementation_plan.md`

## Git Rules
- **NEVER** include "Co-Authored-By" in commits
- User is sole author

## Build Commands
**CRITICAL**: Git Bash silently fails on Flutter. Always use `pwsh -Command "flutter clean && flutter build apk --release"`

## Data Flow
```
Screen -> Provider -> Repository -> SQLite (local) -> Supabase (sync)
```

## Platform Requirements (2026 Standards)

### Android
| Component | Version | Notes |
|-----------|---------|-------|
| compileSdk | 36 | Android 16 - Latest stable |
| targetSdk | 36 | Required for Play Store |
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
| Test Orchestrator | 1.6.1 | Proper test isolation |
| JVM Heap (Tests) | 12G | Prevents OOM in long test runs |
| Max Tests Per Batch | 5 | Memory resets between batches |
| Patrol | 4.1.0 | Native automation |

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
