# Workflow & Documentation System Implementation Roadmap

**Goal**: Enable agent autonomy through comprehensive, lazy-loaded documentation + structured state tracking + quality gates.

**Success Metric**: Next phase runs with 0 sub-agent permission failures, zero 3-round fix cycles, and documented constraints available to all agents.

---

## Phase 0: Foundation (Today - 4 hours)

### Step 0.1: Create Directory Structure
```bash
mkdir -p .claude/docs
mkdir -p .claude/architecture-decisions
mkdir -p .claude/state
mkdir -p .claude/hooks
```

### Step 0.2: Create JSON State Files (Templates)

**File 1: `.claude/state/PROJECT-STATE.json`**
```json
{
  "metadata": {
    "app_name": "Construction Inspector App",
    "app_version": "1.2.3",
    "last_updated": "2026-02-13T00:00:00Z"
  },

  "current_status": {
    "phase": "Phase 7: PDF V2 Extraction Cleanup + Documentation System",
    "phase_status": "in_progress",
    "last_release": "2026-02-01",
    "next_release_target": "2026-02-28"
  },

  "active_blockers": [
    {
      "id": "BLOCK-001",
      "title": "Flutter OCR rendering in headless tests",
      "severity": "medium",
      "owner": "qa-testing-agent",
      "status": "investigating",
      "notes": "Platform binding timeouts in integration tests"
    }
  ],

  "next_three_priorities": [
    "Complete PDF V2 extraction cleanup (4 remaining tasks)",
    "Build documentation system (feature overviews + architectures)",
    "Implement sync conflict resolution for concurrent edits"
  ],

  "dependencies_at_risk": []
}
```

**File 2: `.claude/state/TASK-LIST.json`**
```json
{
  "current_phase": "Phase 7: PDF V2 Cleanup",
  "phase_completion": 0,

  "tasks": [
    {
      "id": "T7.1",
      "feature": "pdf",
      "title": "Document quality profiler",
      "status": "complete",
      "assigned_to": "backend-data-layer-agent",
      "test_contract": {
        "functional_tests": ["quality_profiler_test.dart"],
        "quality_metrics": ["coverage >= 85%", "analyzer_warnings: 0"]
      },
      "completion": {
        "tests_passing": 45,
        "tests_failing": 0,
        "coverage": 92,
        "completed_at": "2026-02-12T18:30:00Z"
      },
      "files_modified": [
        "lib/features/pdf/services/extraction/stages/document_quality_profiler.dart"
      ]
    },
    {
      "id": "T7.2",
      "feature": "pdf",
      "title": "Element validator",
      "status": "pending",
      "assigned_to": null,
      "test_contract": {
        "functional_tests": [
          "Valid element passes validation",
          "Invalid element rejected with reason",
          "Edge case: Empty element list handled",
          "Edge case: Malformed element structure"
        ],
        "quality_metrics": ["coverage >= 90%", "analyzer_warnings: 0"],
        "performance_benchmarks": ["validate_single_element: < 10ms"]
      },
      "completion": null
    }
  ],

  "summary": {
    "total_tasks": 2,
    "completed": 1,
    "in_progress": 0,
    "pending": 1,
    "completion_percentage": 50
  }
}
```

**File 3: `.claude/state/FEATURE-MATRIX.json`**
```json
{
  "features": [
    {
      "name": "pdf",
      "full_name": "PDF Extraction & Generation",
      "status": "in_progress",
      "docs": {
        "overview": "docs/feature-pdf-overview.md",
        "architecture": "docs/feature-pdf-architecture.md",
        "prd": "plans/2026-02-11-pdf-extraction-pipeline-v2-prd-2.0.md"
      },
      "constraints": "architecture-decisions/pdf-v2-constraints.md",
      "metrics": {
        "test_coverage": 87,
        "needs_documentation": false,
        "needs_refactoring": false
      }
    },
    {
      "name": "sync",
      "full_name": "Sync Engine",
      "status": "stable",
      "docs": {
        "overview": "docs/feature-sync-overview.md",
        "architecture": "docs/feature-sync-architecture.md",
        "prd": null
      },
      "constraints": "architecture-decisions/sync-conflict-strategy.md",
      "metrics": {
        "test_coverage": 92,
        "needs_documentation": true,
        "needs_refactoring": false
      }
    },
    {
      "name": "auth",
      "full_name": "Authentication",
      "status": "stable",
      "docs": {
        "overview": "docs/feature-auth-overview.md",
        "architecture": "docs/feature-auth-architecture.md",
        "prd": null
      },
      "constraints": "architecture-decisions/auth-offline-behavior.md",
      "metrics": {
        "test_coverage": 88,
        "needs_documentation": true,
        "needs_refactoring": false
      }
    },
    {
      "name": "entries",
      "full_name": "Entry Management",
      "status": "stable",
      "docs": {
        "overview": "docs/feature-entries-overview.md",
        "architecture": "docs/feature-entries-architecture.md",
        "prd": null
      },
      "constraints": "architecture-decisions/entries-constraints.md",
      "metrics": {
        "test_coverage": 78,
        "needs_documentation": true,
        "needs_refactoring": true
      }
    },
    {
      "name": "photos",
      "full_name": "Photo Management",
      "status": "stable",
      "docs": {
        "overview": "docs/feature-photos-overview.md",
        "architecture": "docs/feature-photos-architecture.md",
        "prd": null
      },
      "constraints": "architecture-decisions/photos-constraints.md",
      "metrics": {
        "test_coverage": 82,
        "needs_documentation": true,
        "needs_refactoring": false
      }
    }
  ]
}
```

**File 4: `.claude/state/AGENT-CHECKLIST.json`**
```json
{
  "pre_flight_validation": {
    "description": "Run before spawning agents. If any check fails, abort and fix.",
    "checks": [
      {
        "name": "write_permissions",
        "command": "pwsh -Command \"dart pub get\" 2>&1 | Select-String 'error' | Measure-Object | Select-Object -ExpandProperty Count",
        "expected": "0",
        "required": true
      },
      {
        "name": "test_runner",
        "command": "pwsh -Command \"flutter test --version\"",
        "expected": "Flutter",
        "required": true
      },
      {
        "name": "analyzer",
        "command": "dart analyze --version",
        "expected": "dart",
        "required": true
      }
    ]
  },

  "context_loading": {
    "description": "Each agent auto-loads from frontmatter + manual task context",
    "template": {
      "agent_rules_file": "agents/[AGENT_NAME].md",
      "feature_override_docs": "docs/feature-[FEATURE]-*.md",
      "feature_constraints": "architecture-decisions/[FEATURE]-*.md",
      "shared_constraints": "architecture-decisions/data-validation-rules.md"
    }
  },

  "spawn_limits": {
    "max_agents_per_wave": 3,
    "max_parallel_agents": 3,
    "max_waves_total": 2,
    "requires_user_approval_if_exceeds": true,
    "rationale": "Prevents context explosion and permission cascade failures"
  },

  "post_work_validation": {
    "agent_must_run": [
      {
        "check": "Unit tests for task",
        "command": "flutter test [task_test_file]",
        "acceptance": "100% tests passing"
      },
      {
        "check": "Linting & analyzer",
        "command": "dart analyze lib/features/[feature]/",
        "acceptance": "0 warnings, 0 errors"
      },
      {
        "check": "No hardcoded strings",
        "command": "grep -r '\\\"[A-Z].*\\\"' lib/features/[feature]/ --include='*.dart' | grep -v 'const\\|//\\|@'",
        "acceptance": "Only constants and comments"
      }
    ]
  },

  "wave_2_integration_review": {
    "agent": "code-review-agent",
    "responsibilities": [
      "Load architecture-decisions/[feature]-constraints.md for each modified feature",
      "Verify all feature-specific constraints are met",
      "Run full test suite",
      "Compare benchmark results to TASK-LIST.json targets",
      "Run dart analyze across all modified files",
      "Report: tests passing, benchmarks met, coverage, blockers"
    ]
  }
}
```

### Step 0.3: Create Shared Constraint File

**File: `.claude/architecture-decisions/data-validation-rules.md`**
```markdown
# Shared Data Validation Rules

Applied to ALL features. Feature-specific constraints are in `[feature]-constraints.md`.

## Mandatory Rules

### User Input Validation
- [ ] All user input (text, numbers, dates) validated before use
- [ ] Validation happens at form level AND repository level
- [ ] Error messages are user-friendly and actionable

### Null Safety
- [ ] No nullable types used for business logic data
- [ ] Late initialization only where unavoidable (e.g., async setup)
- [ ] All `?` types documented with rationale

### API Boundaries
- [ ] All external API calls wrapped in try-catch
- [ ] Network errors reported to UI as SnackBar or ErrorWidget
- [ ] Timeouts enforced (default: 30 seconds)

### Database Access
- [ ] No raw SQL in Dart code (use repository pattern)
- [ ] Transactions used for multi-step operations
- [ ] Cascade deletes documented and tested

### Testing Requirements
- [ ] All public methods have unit tests
- [ ] Happy path + error cases tested
- [ ] Coverage >= 85% for feature

### Code Quality
- [ ] Analyzer runs clean (dart analyze)
- [ ] No hardcoded strings (use constants)
- [ ] All enums updated together (no partial updates)

## Why These Exist

These rules prevent:
- User data corruption (validation)
- Null pointer crashes (null safety)
- Silent network failures (API error handling)
- Data inconsistency (transactions)
- Brittle tests (comprehensive coverage)
- Maintenance burden (code quality)
```

---

## Phase 1: Documentation (Next 6-8 hours)

Create feature overview + architecture docs for each feature. Use this template for consistency.

### Overview Template (500 words)
```markdown
# Feature: [FEATURE_NAME]

## Purpose
[1-2 sentences: Why does this feature exist? What problem does it solve?]

## Key Responsibilities
- [Responsibility 1]
- [Responsibility 2]
- [Responsibility 3]

## Key Files
| File | Purpose |
|------|---------|
| `lib/features/[feature]/data/...` | [Purpose] |
| `lib/features/[feature]/domain/...` | [Purpose] |
| `lib/features/[feature]/presentation/...` | [Purpose] |

## Data Sources
- **Local**: SQLite table `[table_name]` in `lib/core/database/...`
- **Remote**: Supabase table `[table_name]` with RLS policies
- **Cache**: [In-memory Provider / SharedPreferences / etc.]

## Integration Points
- **Requires**: [Feature 1], [Feature 2]
- **Required By**: [Feature 1], [Feature 2]

## Offline Behavior
[How this feature works offline, sync strategy, conflict resolution]

## Edge Cases & Limitations
[Known limitations, edge cases, workarounds]
```

### Architecture Template (800 words)
```markdown
# Feature: [FEATURE_NAME] - Architecture

## Data Model

### Primary Entity: [EntityName]
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | String | Yes | UUID |
| [field] | [Type] | [Yes/No] | [Description] |

### Relationships
- [Entity] → [Entity]: [description]
- [Entity] ← [Entity]: [description]

## Repository Pattern

### [FeatureName]Repository
**Responsibilities**:
- CRUD operations for [Entity]
- Sync coordination with [SyncFeature]
- Conflict resolution per [Architecture Decision]

**Key Methods**:
```dart
Future<List<Entity>> getAll();
Future<Entity?> getById(String id);
Future<void> create(Entity entity);
Future<void> update(Entity entity);
Future<void> delete(String id);
```

## State Management

### [FeatureName]Provider (ChangeNotifier)
**State**:
- `entities`: List<Entity>
- `isLoading`: bool
- `error`: String?

**Key Methods**:
- `loadAll()`: Fetch from local DB, refresh from cloud
- `create(Entity)`: Save locally, queue for sync
- `update(Entity)`: Save locally, queue for sync

## Offline Behavior
- **Write Operations**: Saved to local DB, queued in `sync_queue` table
- **Read Operations**: From local DB (eventually consistent)
- **Sync**: [Strategy - immediate/background/manual]
- **Conflict Resolution**: [Strategy per architecture-decisions/[feature]-conflict.md]

## Testing Strategy
- **Unit Tests**: Repository methods with mocked DB
- **Widget Tests**: UI forms and validation
- **Integration Tests**: E2E flow with real DB

## Performance Considerations
[Memory usage, query efficiency, sync performance, etc.]
```

### Action Items for Phase 1

**Create these files:**
1. `docs/feature-pdf-overview.md` (update/refine existing knowledge)
2. `docs/feature-pdf-architecture.md` (new)
3. `docs/feature-sync-overview.md` (new)
4. `docs/feature-sync-architecture.md` (new)
5. `docs/feature-auth-overview.md` (new)
6. `docs/feature-auth-architecture.md` (new)
7. `docs/feature-entries-overview.md` (new)
8. `docs/feature-entries-architecture.md` (new)
9. `docs/feature-photos-overview.md` (new)
10. `docs/feature-photos-architecture.md` (new)

**Create constraint files:**
1. `architecture-decisions/pdf-v2-constraints.md`
2. `architecture-decisions/sync-conflict-strategy.md`
3. `architecture-decisions/auth-offline-behavior.md`
4. `architecture-decisions/entries-constraints.md`
5. `architecture-decisions/photos-constraints.md`

---

## Phase 2: Agent Enhancement (3-4 hours)

### Step 2.1: Add Frontmatter to Agent Definitions

Update each agent file (e.g., `agents/pdf-agent.md`) with:

```yaml
---
name: pdf-agent
frontmatter:
  rules:
    - rules/pdf/pdf-generation.md
    - architecture-decisions/pdf-v2-constraints.md
    - architecture-decisions/data-validation-rules.md
  docs:
    - docs/feature-pdf-overview.md
    - docs/feature-pdf-architecture.md
    - plans/2026-02-11-pdf-extraction-pipeline-v2-prd-2.0.md
  state:
    - state/FEATURE-MATRIX.json (read only, for context)
    - state/TASK-LIST.json (read only, for current task understanding)
---
```

**For each agent, specify its relevant feature docs** (don't load everything, lazy-load only what's needed).

### Step 2.2: Enhance Brainstorming Skill with TDD-First Planning

Update `.claude/skills/brainstorming/SKILL.md` to add **Phase 3: Define Test Contract & Performance Benchmarks** (as previously outlined).

### Step 2.3: Create Pre-Flight Validation Hook

**File: `.claude/hooks/pre-agent-dispatch.sh`**
```bash
#!/bin/bash
# Pre-flight checks before spawning agents

set -e

echo "🔍 Pre-flight validation..."

# Check 1: Write permissions
echo "  Checking write permissions..."
pwsh -Command "dart pub get" > /dev/null 2>&1 || { echo "  ✗ Write permissions failed"; exit 1; }
echo "  ✓ Write permissions OK"

# Check 2: Test runner
echo "  Checking test runner..."
pwsh -Command "flutter test --version" > /dev/null 2>&1 || { echo "  ✗ Test runner not available"; exit 1; }
echo "  ✓ Test runner OK"

# Check 3: Analyzer
echo "  Checking analyzer..."
dart analyze --version > /dev/null 2>&1 || { echo "  ✗ Analyzer not available"; exit 1; }
echo "  ✓ Analyzer OK"

echo "✅ All pre-flight checks passed. Safe to spawn agents."
```

### Step 2.4: Create Post-Work Validation Hook

**File: `.claude/hooks/post-agent-coding.sh`**
```bash
#!/bin/bash
# Post-work validation after agent coding

set -e

FEATURE=$1
TEST_PATH=$2

echo "🔍 Post-work validation for $FEATURE..."

# Run tests
echo "  Running tests..."
pwsh -Command "flutter test $TEST_PATH" > /dev/null 2>&1 || { echo "  ✗ Tests failed"; exit 1; }
echo "  ✓ Tests passing"

# Run analyzer
echo "  Running analyzer..."
dart analyze lib/features/$FEATURE/ > /dev/null 2>&1 || { echo "  ✗ Analyzer warnings found"; exit 1; }
echo "  ✓ Analyzer clean"

echo "✅ Post-work validation passed."
```

---

## Phase 3: Workflow Integration (2 hours)

### Step 3.1: Update CLAUDE.md with Structure Overview

Add to CLAUDE.md:

```markdown
## Documentation System (Active)

### Structure
- `docs/` — Feature overviews + architecture (lazy-loaded by agents)
- `architecture-decisions/` — Feature-specific constraints
- `state/` — JSON state files (PROJECT, TASK, FEATURE-MATRIX, AGENT-CHECKLIST)

### Agent Context Loading
Each agent loads via frontmatter in its definition file:
```yaml
frontmatter:
  rules: [list of rule files to load]
  docs: [list of doc files to load]
```

### State Files
- **PROJECT-STATE.json**: Overall app health, blockers, priorities
- **TASK-LIST.json**: Current work, test contracts, benchmarks
- **FEATURE-MATRIX.json**: All features + their doc status
- **AGENT-CHECKLIST.json**: Pre-flight + post-work validation templates

### Workflow
1. Brainstorm with TDD-first planning (Phase 3 defines test contracts)
2. Create tasks in TASK-LIST.json with test contract
3. Pre-flight validation runs automatically before agent spawn
4. Agents implement against test contract
5. Post-work validation ensures quality gates
6. Wave 2 integration review catches seams + updates state files
7. Commit with summary
```

### Step 3.2: Create Session Kickoff Template

**File: `.claude/skills/session-kickoff/SKILL.md`** (new skill)

```markdown
# Session Kickoff Skill

Runs at start of focused work session.

## Steps

1. Read PROJECT-STATE.json
   - Report current phase, blockers, next priorities

2. Read TASK-LIST.json
   - Show pending tasks for this phase
   - Show in-progress tasks awaiting agent completion

3. Run pre-flight validation
   - Check write permissions, test runner, analyzer

4. Ask user
   - "Which task should we work on next?"
   - "Any blockers to clear first?"

5. Prepare agent dispatch
   - Load task's test contract
   - Load feature's constraints + docs
   - Confirm spawn limits (max 3 agents per wave)
   - Ask user approval before spawning
```

---

## Phase 4: Test & Iterate (Next Real Task)

When you start the next real phase/task:

1. Use `/session-kickoff` skill
2. Run next task through **TDD brainstorming** (define tests + benchmarks first)
3. Dispatch agents with **pre-flight validation**
4. Agents implement against **test contract**
5. Post-work validation + **Wave 2 integration review**
6. Update state files + commit

**Measure**:
- Did sub-agents spawn without permission failures?
- Did code pass validation on first try (no 3-round cycles)?
- Did agents know right context (no off-target implementations)?

---

## Success Criteria

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Sub-agent permission failures | ~8 per 30 sessions | 0 | Phase 0 + 1 |
| Code requiring 3+ fix cycles | 30 instances | < 5 | Phase 1 + 2 |
| Agent context accuracy | ~70% | 90%+ | Phase 1 + 2 |
| Documentation coverage | 20% of features | 100% | Phase 1 |
| Spawn limit violations | Frequent | 0 | Phase 0 |

---

## Questions Before We Start

1. **Documentation Writing**: Should I draft all 10 feature docs, or do you want to review after I draft 2-3 templates?

2. **Frontmatter Format**: I showed YAML frontmatter — does Claude Code support this, or should we use JSON frontmatter?

3. **Priority**: Shall we tackle Phase 0 + Phase 1 documentation first (foundation), or jump straight to an agent enhancement test?
