# Construction Inspector App

Cross-platform mobile/desktop app for construction inspectors. Offline-first with cloud sync.

## Quick Reference
@.claude/autoload/_tech-stack.md
@.claude/autoload/_defects.md
@.claude/rules/architecture.md

## Archives (On-Demand) DO NOT AUTO-LOAD THESE
- `.claude/logs/state-archive.md`
- `.claude/logs/defects-archive.md`

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
| `flutter-specialist-agent` | Screens, widgets, performance | IMPLEMENT |
| `data-layer-agent` | Models, repositories, providers | IMPLEMENT |
| `supabase-agent` | Sync, schema, RLS | IMPLEMENT |
| `auth-agent` | Auth flows | IMPLEMENT |
| `pdf-agent` | PDF generation | IMPLEMENT |
| `code-review-agent` | Architecture, code quality | REVIEW |
| `qa-testing-agent` | Testing, debugging | TEST/VERIFY |

## Skills (Agent Enhancements)
| Skill | Purpose | Used By |
|-------|---------|---------|
| `brainstorming` | Collaborative design | planning-agent |
| `systematic-debugging` | Root cause analysis | qa-testing-agent |
| `test-driven-development` | Red-Green-Refactor | All IMPLEMENT + qa-testing |
| `verification-before-completion` | Evidence gate | qa-testing, code-review |
| `interface-design` | Design system | flutter-specialist |

Skills are embedded in agent behavior via `@` references - no slash commands needed.

## Session
- `/resume-session` - Load HOT context only
- `/end-session` - Save state with auto-archiving
- State: `.claude/autoload/_state.md` (max 10 sessions)
- Defects: `.claude/autoload/_defects.md` (max 15 defects)
- Archives: `.claude/logs/state-archive.md`, `.claude/logs/defects-archive.md`

## Git Rules
- **NEVER** include "Co-Authored-By" in commits
- User is sole author

## Build Commands
**CRITICAL**: Git Bash silently fails on Flutter. Always use:
```bash
pwsh -Command "flutter clean && flutter build apk --release"
```

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
| Gradle | 8.13 | Latest stable |
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

### Key Config Files
- `android/app/build.gradle.kts` - SDK versions, test options
- `android/gradle.properties` - JVM heap, Gradle settings
- `ios/Runner.xcodeproj/project.pbxproj` - iOS deployment target

## Repositories
| Repo | URL |
|------|-----|
| App Code | https://github.com/RobertoChavez2433/construction-inspector-tracking-app |
| Claude Config | https://github.com/RobertoChavez2433/field-guide-claude-config |

`.claude/` is gitignored from app repo and tracked separately.
