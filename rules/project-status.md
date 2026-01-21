# Project Status

## Current State
- **Phase**: Feature-First Reorganization COMPLETE
- **Tests**: 363 passing
- **Analyzer**: 0 errors, 10 info warnings (expected deprecations)

## Capabilities
- 12 features: auth, projects, locations, contractors, quantities, entries, photos, pdf, sync, dashboard, settings, weather
- PDF export with template filling
- Supabase auth & offline-first sync
- 3 theme modes (Light/Dark/High Contrast)

## Active Work

See `.claude/plans/_state.md` for current session focus.

## Pending Tasks

### Code Quality
- Extract mega-screen dialogs (entry_wizard, report)
- DRY refactoring in data layer
- Migrate deprecated barrel imports

### Sync Service
- Run supabase_schema_v3.sql (personnel_types tables)
- Run supabase_schema_v4_rls.sql (RLS policies)

### Future Features
- AASHTOWare Integration (lib/features/aashtoware/)
- Separate Photos/Attachments in report screen

## Historical Data

Session log and phase history: `.claude/logs/session-log.md` (not agent-referenced)
