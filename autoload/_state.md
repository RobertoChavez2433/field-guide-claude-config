# Session State

**Last Updated**: 2026-03-03 | **Session**: 490

## Current Phase
- **Phase**: Testing System Overhaul — IMPLEMENTED
- **Status**: Brainstormed + implemented full ADB testing overhaul. 30 flows, 12 journeys, 4 tiers, flag-based CLI. Patrol deprecated. Phases 0-2 + 4 complete. Phases 3 + 5 deferred (require device). Dual code review passed.

## HOT CONTEXT - Resume Here

### What Was Done This Session (490)

1. **Brainstormed testing system overhaul** — 7-question design session via `/brainstorming` skill
   - Decided: Replace Patrol entirely, 4 tiers (Smoke/Feature/Journey/Full), flag style CLI, both feature + journey grouping
   - Designed: 30 flows (3 smoke + 18 feature + 9 journey-support), 12 journeys, per-run output directories
2. **Implemented via `/implement` skill** — Phases 0, 1, 2, 4 complete
   - Phase 0: Moved Patrol tests to `integration_test/_deprecated/patrol/`, commented out CI jobs
   - Phase 1: Created registry.md (30 flows + 12 journeys), output-format.md, .gitkeep
   - Phase 2: Rewrote SKILL.md (4-tier flags), updated test-wave-agent.md (haiku + output rules), deleted test-orchestrator-agent.md
   - Phase 4: Verified all flow step definitions against actual screen source code and TestingKeys
3. **Dual code review** — Both passed
   - Completeness review: PARTIAL (1 minor gap — ui-dumps/ missing from output-format.md, fixed)
   - File reference review: PASS (179 key-element references valid, 10 cross-file refs valid, all deps valid, no circular deps)
4. **Fixed ui-dumps gap** — Added ui-dumps/ directory and naming convention to output-format.md

### What Needs to Happen Next

1. **Dry run `/test --smoke`** — Connect device, validate 3 smoke flows work end-to-end (Phase 3)
2. **Journey validation** — Run `/test --full`, fix flow chaining issues (Phase 5)
3. **Fix sync defects** — entry_equipment/entry_quantities use `created_at` but tables only have `updated_at`
4. **Fix BLOCKER-24** — add UNIQUE index to SQLite projects table
5. **Fix BLOCKER-22** — location field stuck loading
6. **COMMIT + PUSH** all changes on `fix/sync-dns-resilience` branch

## Blockers

### BLOCKER-24: SQLite Missing UNIQUE Constraint on Project Number — Sync Race
**Status**: OPEN — HIGH PRIORITY
**Symptom**: User creates project, sees "already exists" on save, or project appears duplicated. Supabase has `UNIQUE(company_id, project_number)` but SQLite doesn't — duplicate inserts succeed locally then fail on sync.
**Root cause**: `ProjectRepository.create()` does soft check-then-insert (TOCTOU race). No DB-level constraint prevents duplicates.
**Fix**: Add `CREATE UNIQUE INDEX idx_project_number_company ON projects(company_id, project_number)` to SQLite. Bump DB version. Migration for existing installs.
**Files**: `lib/core/database/schema/core_tables.dart`, `lib/core/database/database_service.dart`

### BLOCKER-22: Location Field Stuck "Loading" on New Entry Screen
**Status**: OPEN — HIGH PRIORITY
**Symptom**: When creating a new entry, the location field shows perpetual "loading" spinner. No location was added during project creation (which is allowed — location is nullable now). The entry editor appears to be trying to auto-fetch weather/location data and getting stuck when no location exists.
**Root cause**: NOT YET INVESTIGATED.
**Files to investigate**: `lib/features/entries/presentation/screens/entry_editor_screen.dart`, weather service, location provider.

### BLOCKER-23: Flutter Keys Not Propagating to Android resource-id
**Status**: OPEN — MEDIUM PRIORITY (mitigated by content-desc/text fallback in redesigned test skill)
**Workaround**: Use `content-desc` (from Semantics labels) or `text` attributes for element finding. Baked into redesigned wave agent.

### BLOCKER-25: Nested Task Tool Calls Don't Work in Subagents
**Status**: OPEN — ARCHITECTURAL LIMITATION
**Workaround**: Main agent acts as thin orchestrator, dispatches wave agents directly. test-orchestrator-agent.md deleted — orchestration is top-level only.

### BLOCKER-11: dart-mcp Testing Strategy Is Wrong Tier
**Status**: SUPERSEDED by testing system overhaul (Session 490). Patrol replaced with ADB flows.

### BLOCKER-10: Fixture Generator Requires SPRINGFIELD_PDF Runtime Define
**Status**: OPEN (PDF scope only).

## Recent Sessions

### Session 490 (2026-03-03)
**Work**: Brainstormed + implemented testing system overhaul. 30 flows, 12 journeys, 4 tiers, flag-based CLI. Patrol deprecated to `_deprecated/`. Dual code review passed. 1 minor gap (ui-dumps/) fixed.
**Decisions**: Replace Patrol entirely. 4 tiers (Smoke/Feature/Journey/Full). Flag style CLI (`/test --entries --smoke`). Per-run output directories (`YYYY-MM-DD_HHmm_{descriptor}/`). Top-level orchestration (no orchestrator agent). Haiku for wave agents. Defects stay in existing `.claude/defects/` system.
**Next**: Dry run `/test --smoke` with device, fix sync defects, fix BLOCKER-24, commit+push.

### Session 489 (2026-03-03)
**Work**: Validated test orchestration delegation. Confirmed BLOCKER-25 (nested Task calls fail — subagents can't dispatch subagents). Top-level orchestration works: 3/4 PASS, 1 FAIL, 3 defects filed. Attempted headless mode (`claude -p`) as workaround — blocked by nesting protection. Planned next-session testing overhaul: replace Patrol with ADB flows, 3 tiers, helper scripts, haiku agents.
**Decisions**: Top-level orchestration only. 1 flow per agent. Haiku for wave agents. Next session: full testing system audit + brainstorm.
**Next**: Testing system overhaul brainstorm, fix sync defects, fix BLOCKER-24, commit+push.

### Session 488 (2026-03-03)
**Work**: Full `/test --all` run (3/5 PASS, 1 FAIL). Identified 4 structural test skill problems. Redesigned orchestrator (added Task tool + 80% handoff), wave agent (added Write/Edit + mandatory logcat + mandatory disk writes), ADB refs (Android 15 workarounds at top). Discovered BLOCKER-24 (SQLite missing UNIQUE on project_number).
**Decisions**: Orchestrator gets Task tool (not eliminated). Wave agents get Write/Edit + must check logcat after every interaction. 80% context handoff via disk file. content-desc primary element strategy (not resource-id).
**Next**: CLI restart, retry `/test --all`, fix BLOCKER-24, fix BLOCKER-22, commit+push.

### Session 487 (2026-03-03)
**Work**: First `/test` skill dry run on Samsung SM-G996U. Built+installed debug APK. Found 5 issues (Android 15 screencap, Git Bash paths, missing resource-ids, subagent perms, agent loading). Fixed `Bash(*)` permissions.
**Decisions**: `Bash(*)` wildcard over specific patterns. CLI restart needed for agent loading. `exec-out` pipe for Android 15 screenshots.
**Next**: Restart CLI, retry `/test --all`, fix Key→resource-id propagation, update ADB references.

### Session 486 (2026-03-03)
**Work**: Brainstormed + implemented `/test` skill (ADB-based on-device testing). 5-question design session, then `/implement` for Phases 0-2. 6 new config files, 2 Dart files modified. All quality gates passed. Phase 3 (dry run) deferred.
**Decisions**: Hybrid UIAutomator+Vision. Wave-based dispatch. SKILL.md convention. Wave agent read-only (Bash+Read). Feature-path map in registry.
**Next**: Fix BLOCKER-22, commit+push, dry run `/test login` with device.

## Active Plans

### Testing System Overhaul — IMPLEMENTED (Session 490)
- **Design**: `.claude/plans/2026-03-03-testing-system-overhaul.md`
- **Status**: Phases 0-2 + 4 implemented. Phases 3 + 5 deferred (require device). Dual review passed.
- **Files**: `.claude/test-flows/registry.md`, `.claude/skills/test/SKILL.md`, `.claude/agents/test-wave-agent.md`, `.claude/skills/test/references/output-format.md`, `.claude/skills/test/references/adb-commands.md`

### Review & Submit Flow + Auth — IMPLEMENTED (Session 484)
- **Plan**: `.claude/plans/2026-03-03-review-submit-flow-and-auth.md` (Rev 2, adversarial-reviewed)
- **Status**: All 5 phases implemented + reviewed + fixed. Awaiting commit+push+deploy.
- **Reviews**: `.claude/code-reviews/2026-03-03-review-submit-auth-review.md`, `.claude/code-reviews/2026-03-03-security-audit.md`

### Extraction Regression + Sync Fix — IMPLEMENTED (Session 481)
- **Plan**: `.claude/plans/2026-03-02-extraction-and-sync-fix.md`
- **Status**: All 4 phases implemented, all 6 quality gates passed. Supabase migration deployed (Session 482). Awaiting commit+push.

### Project-Based Multi-Tenant Architecture — DEPLOYED (Session 453)
- **PRD**: `.claude/prds/2026-02-21-project-based-architecture-prd.md`
- **Implementation plan**: `.claude/plans/2026-02-22-project-based-architecture-plan.md`

## Reference
- **Improvements**: `.claude/improvements.md`
- **Testing Overhaul Plan**: `.claude/plans/2026-03-03-testing-system-overhaul.md`
- **Multi-Tenant Plan**: `.claude/plans/2026-02-22-project-based-architecture-plan.md`
- **Multi-Tenant PRD**: `.claude/prds/2026-02-21-project-based-architecture-prd.md`
- **Archive**: `.claude/logs/state-archive.md`
- **Defects**: `.claude/defects/_defects-database.md`, `.claude/defects/_defects-toolbox.md`, `.claude/defects/_defects-pdf.md`, `.claude/defects/_defects-sync.md`, `.claude/defects/_defects-forms.md`, `.claude/defects/_defects-auth.md`, `.claude/defects/_defects-projects.md`, `.claude/defects/_defects-entries.md`
