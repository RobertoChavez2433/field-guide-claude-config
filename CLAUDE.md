# Construction Inspector App

Cross-platform mobile/desktop app for construction inspectors. Offline-first with cloud sync.

## Quick Reference
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

Skills are loaded via `skills:` frontmatter in agent files. Claude auto-delegates to agents based on task description.

## Hookify (Behavioral Guards)
Hookify is a **plugin** (not a skill) that enforces project rules via pattern matching. Rules are defined in `.claude/hookify.*.local.md` files. See `.claude/plugins/hookify/` for the plugin and `writing-rules` skill.

## Session
- `/resume-session` - Load HOT context only
- `/end-session` - Save state with auto-archiving
- State: `.claude/autoload/_state.md` (max 5 sessions)
- Defects: `.claude/autoload/_defects.md` (max 7 defects)
- Archives: `.claude/logs/state-archive.md`, `.claude/logs/defects-archive.md`

## Quick Reference Commands

**CRITICAL**: Git Bash silently fails on Flutter. ALWAYS use pwsh wrapper.

### Build & Run
1. `pwsh -Command "flutter run -d windows"`                                    — Run on desktop
2. `pwsh -Command "flutter clean && flutter build apk --release"`              — Build APK
3. `pwsh -Command "flutter clean"`                                             — Clean build artifacts

### Testing
4. `pwsh -Command "flutter test"`                                              — All tests
5. `pwsh -Command "flutter test test/features/pdf/table_extraction/"`          — PDF extraction tests
6. `pwsh -Command "flutter test test/features/pdf/services/ocr/"`              — OCR tests
7. `pwsh -Command "flutter test <path/to/specific_test.dart>"`                 — Single test file
8. `pwsh -Command "flutter test --dart-define=PDF_PARSER_DIAGNOSTICS=true"`    — Tests with diagnostics

### Process Management
9. `pwsh -Command "Stop-Process -Name 'construction_inspector' -Force -ErrorAction SilentlyContinue; Stop-Process -Name 'dart' -Force -ErrorAction SilentlyContinue"`

### Dependencies & Diagnostics
10. `pwsh -Command "flutter pub get"`       — Get dependencies
11. `pwsh -Command "flutter pub upgrade"`   — Upgrade dependencies
12. `pwsh -Command "flutter analyze"`       — Static analysis
13. `pwsh -Command "flutter doctor"`        — Environment diagnostics

### Git
14. `git log --oneline -10`                 — Recent commits
15. `git diff --stat`                       — Change summary

### Common Mistakes (from 577+ errors across 30+ sessions)
- NEVER run flutter/dart directly in Git Bash — ALWAYS use `pwsh -Command "..."`
- NEVER use wc, sed, awk, grep as Bash — use Read/Edit/Grep tools instead
- ALWAYS use `-ErrorAction SilentlyContinue` on Stop-Process
- ALWAYS set `timeout: 600000` on `flutter run` commands (default 120s is too short)
- ALWAYS quote paths with spaces: `"C:\Users\rseba\Projects\Field Guide App"`

## Key Packages
| Package | Purpose |
|---------|---------|
| provider | State management |
| go_router | Navigation |
| supabase_flutter | Backend/Auth |
| sqflite | Local storage |
| syncfusion_flutter_pdf | PDF generation |
| pdfx | PDF rendering to images |
| printing | PDF preview/rasterization |
| flusseract | Tesseract OCR (`packages/flusseract/`) |
| syncfusion_flutter_pdfviewer | PDF viewing/rendering |
| image | Image preprocessing |
| xml | HOCR parsing |

## Development Tools
| Tool | Location | Purpose |
|------|----------|---------|
| run_and_tail_logs.ps1 | `tools/` | Run app with live log tailing |
| dump_inspect.py | `tools/` | Crash dump analysis |

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
