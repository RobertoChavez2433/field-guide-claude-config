# Claude Directory Audit & Update — Dependency Analysis

**Date**: 2026-03-30
**Type**: Documentation-only (no app code changes)
**Spec**: `.claude/specs/2026-03-30-claude-directory-audit-update-spec.md`

## Blast Radius

| Category | Count |
|----------|-------|
| Direct changes | ~80 `.claude/` files |
| Dependent files | 0 (no app code depends on `.claude/`) |
| Test files | 0 (no tests for documentation) |
| Cleanup (DELETE) | 1 file (pagination-widgets-guide.md) |

## Tier Dependencies (Execution Order)

```
Tier 1: CLAUDE.md, state files (Phases 1)
  ↓ (rules reference CLAUDE.md conventions)
Tier 2: Rules files (Phases 2-3)
  ↓ (agents load rules via frontmatter)
Tier 3: Agents, feature docs, PRDs, constraints, defects (Phases 4-10)
  ↓ (skills reference agents and docs)
Tier 4: Skills, guides, test flows, index (Phases 11-12)
```

## Cross-Reference Map

### Files that reference other `.claude/` files:
- `CLAUDE.md` → rules/*, docs/*, memory/*, logs/*, backlogged-plans/*
- `docs/INDEX.md` → docs/features/*, docs/guides/*
- `docs/directory-reference.md` → all `.claude/` subdirectories
- All constraint files → corresponding feature-*-overview.md and feature-*-architecture.md
- All agent definitions → rules files (via frontmatter), feature docs, constraint files
- `FEATURE-MATRIX.json` → docs/features/*, architecture-decisions/*
- `AGENT-FEATURE-MAPPING.json` → agents/*, rules/*
- All feature-*.json → docs/features/*, architecture-decisions/*, prds/*

### Files that reference `lib/` paths (must be verified against codebase mapper):
- All 26 feature docs (overview + architecture)
- All 14 PRDs
- All 14 constraint files
- All 11 rules files
- All 10 agent definitions
- All agent-memory files
- All defect files
- Test flow docs

## Ground Truth: Codebase Mapper Summary

### 17 Features (lib/features/)

| Feature | Files | Layers | DI File | Key Classes |
|---------|-------|--------|---------|-------------|
| auth | 48 | data/domain/presentation/services/di | auth_providers.dart | AuthService, AuthProvider, AppConfigProvider, 7 use cases, 10 screens |
| calculator | 13 | data/domain/presentation/di | calculator_providers.dart | CalculatorService, CalculatorProvider, CalculationHistory |
| contractors | 36 | data/domain/presentation/di | contractors_providers.dart | ContractorProvider, EquipmentProvider, PersonnelTypeProvider, 3 repo interfaces |
| dashboard | 10 | presentation/domain(barrel) | none | ProjectDashboardScreen, 4 widgets |
| entries | 85 | data/domain/presentation/di | entries_providers.dart | DailyEntryProvider, EntryExportProvider, 7 use cases, 6 screens, report_widgets/ |
| forms | 72 | data/domain/presentation/di | forms_providers.dart + forms_init.dart | 6 registries, 9 use cases, InspectorFormProvider, FormExportProvider, 4 screens |
| gallery | 5 | presentation/domain(barrel)/di | gallery_providers.dart | GalleryProvider, GalleryScreen |
| locations | 18 | data/domain/presentation/di | locations_providers.dart | LocationProvider, LocationRepository interface+impl |
| pdf | 100+ | services/data/presentation/domain(barrel)/di | pdf_providers.dart | 20+ extraction stages, PdfService, ExtractionPipeline |
| photos | 22 | data/domain/presentation/di | photos_providers.dart | PhotoProvider, PhotoRepository interface+impl |
| projects | 56 | data/domain/presentation/di | projects_providers.dart | ProjectProvider, 4 use cases, ProjectAssignmentProvider, ProjectSyncHealthProvider |
| quantities | 34 | data/domain/presentation/utils/di | quantities_providers.dart | BidItemProvider, EntryQuantityProvider, BudgetSanityChecker |
| settings | 38 | data/domain/presentation/di | settings_providers.dart + consent_support_factory.dart | ThemeProvider, AdminProvider, ConsentProvider, SupportProvider, 9 screens |
| sync | 52 | adapters/engine/application/config/domain/data/presentation/di | sync_providers.dart | SyncEngine, SyncOrchestrator, 20+ TableAdapters, SyncProvider |
| todos | 12 | data/domain/presentation/di | todos_providers.dart | TodoProvider, TodoItemRepository interface+impl |
| toolbox | 3 | presentation/domain(barrel) | none | ToolboxHomeScreen (hub) |
| weather | 6 | services/domain/di | weather_providers.dart | WeatherService, WeatherServiceInterface |

### lib/core/ Key Classes
- DatabaseService (version 46, 1900+ lines)
- AppRouter (go_router, auth guard, consent gate)
- AppInitializer, AppDependencies, buildAppProviders()
- Logger (file + HTTP transports, PII scrubbing)
- FieldGuideColors (ThemeExtension), DesignConstants
- 18 design system components (AppScaffold, AppDialog, etc.)
- 14 schema files in database/schema/

### lib/shared/ Key Classes
- BaseLocalDatasource, GenericLocalDatasource, ProjectScopedDatasource, BaseRemoteDatasource
- BaseRepository, BaseListProvider, PagedListProvider
- 16 testing key files
- Utilities: naturalSort, validators, date_utils, snackbar_helper, etc.

### lib/services/ (6 cross-cutting services)
- PhotoService, ImageService, PermissionService, DocumentService, SoftDeleteService, StartupCleanupService

### Supabase
- 38+ migrations, 1 edge function (daily-sync-push), 1 email template

### Test
- 312 test files across test/features/, test/core/, test/data/, test/golden/, test/helpers/

## File Format Templates

### feature-*-overview.md format:
```
---
feature: {name}
type: overview
scope: {description}
updated: YYYY-MM-DD
---
# {Feature} Feature Overview
## Purpose
## Key Responsibilities
## Key Files (table)
## Data Sources
## Integration Points
```

### feature-*-architecture.md format:
```
---
feature: {name}
type: architecture
scope: {description}
updated: YYYY-MM-DD
---
# {Feature} Feature Architecture
## Data Model (entities table)
## Relationships (ASCII diagram)
## File Locations (tree)
## State Management (provider description)
## Repository Pattern (interface + impl)
```

### *-constraints.md format:
```
# {Feature} Constraints
## Hard Rules (✗ MUST / MUST NOT)
## Soft Guidelines (⚠ recommendations)
## Integration Points
## Performance Targets
## Testing Requirements
## References
```

### feature-*.json format:
```json
{
  "id": "{name}",
  "name": "{Full Name}",
  "status": "stable|in_progress|planned",
  "current_phase": "{description}",
  "description": "{one line}",
  "docs": { "overview": "...", "architecture": "...", "prd": "..." },
  "constraints_file": "...",
  "constraints_summary": ["..."],
  "integration": { "depends_on": [], "required_by": [] },
  "metrics": { "test_coverage_percentage": N, "last_updated": "..." }
}
```

### FEATURE-MATRIX.json entry format:
```json
{
  "name": "{name}",
  "full_name": "{Full Name}",
  "status": "stable|in_progress|planned",
  "docs": { "overview": "...", "architecture": "...", "prd": "..." },
  "constraints": "...",
  "test_coverage": "N%",
  "required_by": [],
  "depends_on": []
}
```
