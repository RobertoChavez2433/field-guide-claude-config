# Context & Vision: Documentation System + Agent Autonomy

**Last Updated**: 2026-02-13 | **Status**: Phase 0 Complete, Phase 1 Starting

---

## The Problem We Identified

### 1. Monolithic Codebase with Fragmented Context
- 13 independent features (auth, sync, entries, photos, contractors, dashboard, locations, projects, quantities, settings, toolbox, weather) all documented in scattered places
- Great PRD exists for PDF extraction pipeline, but ZERO documentation for other 12 features
- When agents work on sync, auth, or entries, they operate "blind" with minimal context
- Results in off-target implementations, repeated corrections, architectural violations

### 2. Sub-Agent Infrastructure Failures
- Sub-agents fail with `classifyHandoffIfNeeded` errors (appearing in ~8 sessions)
- Permission failures (write, test, web access) discovered AFTER agent spawning
- No pre-flight validation before Task dispatch
- Results in wasted spawns, rework, context bloat

### 3. Buggy Code Requiring 3+ Fix Cycles
- 30 instances of buggy generated code across 30 sessions
- Common patterns: over-broad regex, missing enum values, hardcoded strings, copy-paste V1 code
- Agents ship untested work → user discovers failures → 2-3 rounds of fixes
- No immediate post-work validation

### 4. Repeated Architectural Corrections
- Same decisions rejected 5+ times: "no hybrid OCR", "no V1 toggles", "no legacy imports"
- User explains constraints every session → agents don't retain context across sessions
- Architectural decisions scattered across 30+ sessions, not encoded anywhere persistent

### 5. Token Inefficiency
- Risk of creating massive CLAUDE.md that wastes tokens loading irrelevant context
- Agents need right information, not everything

---

## The Solution We Designed

### Core Strategy: Lazy-Load Documentation + Distributed Constraints

Instead of one massive CLAUDE.md, we created a **modular, feature-centric documentation system** where:
- Each agent auto-loads only its relevant rules, docs, and state files via **frontmatter**
- Features are independently documented (overview + architecture)
- Architectural constraints are feature-specific, not global
- State is tracked in JSON (machine-readable for agents + scripts)
- Quality gates are automated (pre-flight + post-work validation)

### Key Principles

1. **Lazy-Loading**: Agent only reads what it needs (PDF agent doesn't load sync docs)
2. **Accessibility**: Docs in markdown (human-readable), state in JSON (machine-parseable)
3. **Autonomy**: Agents can validate their own work before handoff
4. **Continuity**: JSON state files enable session-to-session progress tracking
5. **Clarity**: Feature constraints prevent repeated corrections

---

## What We Built (Phase 0 - Complete)

### 1. Directory Structure (3 new directories)
```
.claude/
├── architecture-decisions/    (feature constraints + shared rules)
├── state/                      (JSON state tracking)
└── hooks/                      (pre/post-flight validation scripts)
```

### 2. Constraint System (14 files)
**Shared Rules** (`data-validation-rules.md`):
- User input validation, null safety, API boundaries
- Database patterns, testing requirements, code quality
- Async/concurrency patterns
- Applies to ALL features

**Feature-Specific Constraints** (13 files):
- `pdf-v2-constraints.md` — OCR-only routing, no V1 imports, no hybrid strategies
- `sync-conflict-strategy.md` — Last-write-wins only, bidirectional sync
- `auth-offline-behavior.md` — Cached tokens, session persistence
- 10 more stubs (to be filled in Phase 1)

### 3. State Files (17 JSON files)

**Core State (4 files)**:
- `PROJECT-STATE.json` — Overall health, blockers, priorities, risk dependencies
  - Current phase: OCR migration (45% complete)
  - Blocker: Flutter OCR platform binding timeout
  - Next 3 priorities: Complete OCR migration, build docs system, implement sync conflict resolution

- `TASK-LIST.json` — Current work with test contracts and benchmarks
  - 5 PDF migration tasks (Phase 1 complete, 2-5 pending)
  - Each task defines: test contract, quality metrics, performance benchmarks
  - Example: T2.1 blocked by platform binding timeout

- `FEATURE-MATRIX.json` — All 13 features + their metadata
  - Status: 12 stable, 1 in-progress (PDF)
  - Test coverage: 55-92%
  - Documentation status: 12 features need docs

- `AGENT-CHECKLIST.json` — Pre-flight + post-work validation templates
  - Pre-flight: write permissions, test runner, analyzer checks
  - Post-work: tests passing, analyzer clean, constraints met
  - Spawn limits: max 3 agents/wave, max 2 waves total

**Feature Metadata (13 files)**:
- `feature-[name].json` for each feature
- Stores: docs links, constraints file, integration points, test coverage
- Example: `feature-pdf.json` links to pdf-v2-constraints.md and PDF PRD

### 4. Hook Scripts (2 files)
- `pre-agent-dispatch.sh` — Run BEFORE spawning agents (validates environment)
- `post-agent-coding.sh` — Agents run after coding (validates tests, linting, constraints)

### 5. Agent Frontmatter Updates (8 agents)
All agents now include:
```yaml
frontmatter:
  rules: [list of applicable rule files]
  docs: [list of applicable doc files]
  state: [list of state files to read]
```

Examples:
- **pdf-agent**: loads pdf-generation rules, pdf-v2-constraints, feature-pdf docs
- **backend-supabase-agent**: loads supabase-sql rules, sync-conflict-strategy, sync docs
- **code-review-agent**: loads architecture rules, AGENT-CHECKLIST (for Wave 2 validation)

### 6. CLAUDE.md Update
Added "Documentation System (Phase 0 - Active)" section explaining:
- Lazy-loading strategy
- Agent context loading via frontmatter
- State files and their purposes
- Constraint files and their relationship to agents

---

## How The System Works

### Agent Workflow (Two-Wave Quality Gates)

```
WAVE 1: IMPLEMENTATION (Max 3 agents, parallel)
  ├─ Pre-flight validation
  │  ├─ Check write permissions (dart pub get test)
  │  ├─ Check test runner available
  │  └─ Check analyzer available
  │
  ├─ Load context from frontmatter
  │  ├─ Load rules (architecture.md, feature-specific rules, constraints)
  │  ├─ Load docs (feature overviews, architecture, PRDs)
  │  └─ Load state (task contract, metrics, project blockers)
  │
  ├─ Implement task
  │  └─ Code against test contract (not guesses)
  │
  └─ Post-work validation
     ├─ Run tests (must pass, agent iterates if failing)
     ├─ Run analyzer (must be clean)
     ├─ Verify constraints (feature-specific + shared)
     └─ Report: "Task complete + X tests passing + 0 warnings"

WAVE 2: INTEGRATION REVIEW (1 agent, sequential)
  └─ code-review-agent
     ├─ Read all Wave 1 outputs
     ├─ For each feature: load constraints, verify compliance
     ├─ Run full test suite (flutter test)
     ├─ Check benchmarks vs. targets
     ├─ Cross-cutting validation (enum consistency, hardcoded strings, V1 imports)
     └─ Report: "Ready to merge" or "Blockers: [list]"
```

### Key Properties

1. **Pre-flight safety**: No permission surprises
2. **Context clarity**: Agents know constraints before starting
3. **First-pass quality**: Tests + analyzer validated before handoff
4. **Cross-cutting validation**: Wave 2 catches seams (enum mismatches, etc.)
5. **Spawn limits**: Max 3 agents prevents context explosion

---

## Future Roadmap

### Phase 1: Feature Documentation (6-8 hours)

**What**: Draft overview + architecture docs for all 13 features

**Process**:
1. I draft `docs/feature-[name]-overview.md` (500 words)
   - Purpose, key responsibilities, data sources, integration points, offline behavior, edge cases
2. You review, give feedback
3. I draft `docs/feature-[name]-architecture.md` (800 words)
   - Data model, repository pattern, state management, offline behavior, testing strategy
4. You review, approve
5. Move to next feature

**Features in order**:
1. PDF (most complex, in-progress)
2. Sync (critical for offline-first)
3. Auth (foundational)
4. Entries (core feature)
5. Photos (integration with entries)
6. Then: contractors, dashboard, locations, projects, quantities, settings, toolbox, weather

**Output**: 26 new docs (2 per feature × 13)

### Phase 2: Brainstorming Skill Enhancement (3-4 hours)

**What**: Update brainstorming skill to be TDD-first

**New Phase 3**: Define Test Contract & Performance Benchmarks
- Before design, define what success looks like
- Functional tests (happy path, errors, edge cases)
- Performance benchmarks (load time, response latency, memory)
- Quality metrics (test coverage, analyzer warnings)
- Scalability assumptions (what if it grows?)
- Get user approval on test contract before proceeding to design

**Benefits**:
- Agents implement against tests, not guesses
- Scope bounded by tests (prevents feature creep)
- Benchmarks are performance targets, not afterthoughts

### Phase 3: Constraint Files Completion (2-3 hours)

**What**: Fill in the 12 constraint stub files

**Process**:
- For each feature, document:
  - Hard rules (violations = reject proposal)
  - Soft guidelines (violations = discuss)
  - Integration points with other features
  - Performance/quality targets

**Example** (already done for PDF):
```markdown
# PDF V2 Constraints

## Hard Rules
- ✗ No V1 imports
- ✗ OCR-only routing (no hybrid)
- ✗ No legacy compatibility flags
- ✗ Re-extraction loop must differentiate configs

## Soft Guidelines
- Performance target: < 15 sec/page
- Test coverage: >= 90%
```

### Phase 4: Workflow Integration & Testing (2-3 hours)

**What**: Run first real task through new system

**Steps**:
1. Use new brainstorming skill (TDD-first planning)
2. Create tasks in TASK-LIST.json with test contracts
3. Run pre-flight validation
4. Spawn max 3 agents with Wave 1 implementation
5. Agents run post-work validation automatically
6. code-review-agent does Wave 2 integration review
7. Measure: Did quality improve? Did spawn failures decrease?

**Success Metrics**:
- 0 sub-agent permission failures
- 0 3-round fix cycles (first-pass quality)
- Tests + linter passing before handoff
- Better agent context accuracy

---

## Key Design Decisions

### 1. Individual Feature Metadata Files (not monolithic)
**Decision**: Create `state/feature-[name].json` for each feature
**Why**:
- Agents can query feature-specific metadata efficiently
- Easier to update one feature without affecting others
- Follows lazy-load philosophy

### 2. JSON State Files (not markdown)
**Decision**: Track project state in JSON, not markdown
**Why**:
- Agents can parse programmatically
- Scripts can update state files reliably
- Schema validation possible
- Less ambiguous than markdown

### 3. Frontmatter for Context Loading
**Decision**: Each agent loads rules + docs via frontmatter, not auto-load everything
**Why**:
- Only relevant context per agent
- Token-efficient (don't load PDF docs to sync agent)
- Explicit and maintainable

### 4. Two-Wave Agent Execution
**Decision**: Wave 1 (parallel implementation) + Wave 2 (sequential review)
**Why**:
- Catches integration seams (enum mismatches, hardcoded strings)
- First-pass quality (tests pass before handoff)
- Prevents the 3-round fix cycle pattern

### 5. Pre-flight + Post-work Validation
**Decision**: Validate environment before spawning, validate code after implementation
**Why**:
- No permission surprises (pre-flight)
- No untested code shipped (post-work)
- Agents iterate autonomously (up to 5 attempts)

---

## Architectural Constraints

### Permanent Decisions (Non-Negotiable)

These constraints prevent the repeated corrections you've had to make:

**PDF Extraction (V2)**:
- ✗ No hybrid OCR strategies (binary native/OCR routing only)
- ✗ No V1 imports in V2 code
- ✗ No legacy compatibility flags or toggles
- ✗ No ToUnicode CMap repair attempts

**Sync Engine**:
- ✗ Last-write-wins conflict resolution only (no merge attempts)
- ✗ Bidirectional sync with checksum verification
- ✗ Offline-first write ordering

**Authentication**:
- ✗ Cached tokens for offline sessions only
- ✗ No live token refresh during offline operation
- ✗ Session persistence required

**All Features**:
- ✓ User input validated at form AND repository levels
- ✓ No nullable types for required business logic
- ✓ All API calls wrapped in try-catch
- ✓ Transactions for multi-step DB operations
- ✓ Test coverage >= 85%
- ✓ Analyzer must run clean

---

## How to Use This System

### Before Starting Work
1. Read `PROJECT-STATE.json` (understand current phase, blockers, priorities)
2. Read `TASK-LIST.json` (see pending tasks + test contracts)
3. Check `FEATURE-MATRIX.json` (see which features need docs/testing)

### When Brainstorming a Feature
1. Use `/brainstorming` skill (now TDD-first in Phase 1)
2. Define test contract + benchmarks (not just design)
3. Get user approval on tests before proceeding

### When Assigning Work to Agents
1. Run pre-flight validation: `bash .claude/hooks/pre-agent-dispatch.sh`
2. Spawn max 3 agents for Wave 1 (check AGENT-CHECKLIST.json for limits)
3. Each agent auto-loads context from frontmatter
4. Agents run post-work validation automatically
5. code-review-agent handles Wave 2 integration review
6. Update TASK-LIST.json when complete

### When Adding a New Feature
1. Create `docs/feature-[name]-overview.md` (overview)
2. Create `docs/feature-[name]-architecture.md` (architecture)
3. Create `state/feature-[name].json` (metadata)
4. Create `architecture-decisions/[name]-constraints.md` (constraints)
5. Link in `FEATURE-MATRIX.json`
6. Update agent frontmatter if it works on this feature

---

## Why This System Solves Your Problems

| Problem | Solution |
|---------|----------|
| **Monolith context**: 13 features with scattered docs | Feature-specific lazy-loaded docs + metadata files |
| **Agent blindness**: Agents lack context | Frontmatter auto-loads relevant rules + docs + state |
| **Sub-agent failures**: Permission errors, missing tools | Pre-flight validation catches issues before spawning |
| **Buggy code cycles**: No immediate validation | Post-work validation (tests, linter, constraints) before handoff |
| **Repeated corrections**: Architectural decisions scattered | Feature-specific constraint files prevent re-proposals |
| **Token waste**: Massive CLAUDE.md loads irrelevant info | Lazy-loading only relevant context per agent/task |

---

## Quick Start Next Session

### To Resume from Here:

1. **Read this file** (`CONTEXT-VISION.md`) for full context
2. **Read** `PROJECT-STATE.json` for current blockers + priorities
3. **Read** `TASK-LIST.json` for what's pending (OCR migration Phases 2-5)
4. **Next real work**: Start Phase 1 (feature documentation)
   - Draft `docs/feature-pdf-overview.md` + `docs/feature-pdf-architecture.md`
   - User reviews 1-by-1
   - Move through remaining 12 features

### Commit Strategy:

- **App repo**: User decides when to commit OCR migration changes + Phase 1 work
- **Claude config repo**: Commit after Phase 1 docs complete (whole system in sync)

---

## File Tree Reference

```
.claude/
├── CLAUDE.md (main reference, now with Documentation System section)
├── CONTEXT-VISION.md (THIS FILE - master vision)
├── IMPLEMENTATION-ROADMAP.md (4-phase roadmap, for reference)
├── PHASE-0-CHECKLIST.md (Phase 0 verification, archived)
├── analysis-workflow-improvements.md (friction analysis, archived)
│
├── agents/ (8 agents, now with frontmatter)
│   ├── pdf-agent.md (loads PDF-specific rules + docs)
│   ├── backend-supabase-agent.md (loads sync rules + docs)
│   ├── auth-agent.md (loads auth rules + docs)
│   └── ... (5 more)
│
├── architecture-decisions/ (constraints system)
│   ├── data-validation-rules.md (shared, applies to all)
│   ├── pdf-v2-constraints.md (PDF-specific, detailed)
│   ├── sync-conflict-strategy.md (stub)
│   ├── auth-offline-behavior.md (stub)
│   └── ... (10 more feature stubs)
│
├── state/ (JSON state files, machine-readable)
│   ├── PROJECT-STATE.json (app health, blockers, priorities)
│   ├── TASK-LIST.json (current work + test contracts)
│   ├── FEATURE-MATRIX.json (all 13 features + status)
│   ├── AGENT-CHECKLIST.json (validation templates)
│   └── feature-[name].json × 13 (feature metadata)
│
├── hooks/ (validation scripts)
│   ├── pre-agent-dispatch.sh (run before spawning agents)
│   └── post-agent-coding.sh (agents run after coding)
│
├── docs/ (feature documentation, to be created in Phase 1)
│   ├── feature-pdf-overview.md (NEXT)
│   ├── feature-pdf-architecture.md (NEXT)
│   └── ... (24 more docs for other 12 features)
│
├── rules/ (existing, unchanged)
├── skills/ (existing, will enhance brainstorming in Phase 2)
├── plans/ (existing PRDs + implementation plans)
└── ... (other existing directories)
```

---

## Summary

You identified a real problem: **monolithic codebase → fragmented context → poor agent autonomy → repeated work**.

We designed a solution: **modular documentation system + lazy-loading + JSON state + quality gates**.

We implemented Phase 0: **Directory structure, state files, constraint system, hook scripts, agent frontmatter updates**.

We're ready for Phase 1: **Write comprehensive feature docs (1 by 1 for your review)**.

The system is **modular, scalable, and solves the root cause** (not just symptoms).

---

**Next session**: `/resume-session` will load this file. Start with Phase 1 (PDF feature docs).
