# Claude Filing System - Complete Visual Map

**Purpose**: One source of truth for where every file lives and how it's named across all 13 features.

---

## `.claude/` Directory Structure

```
.claude/
│
├── CLAUDE.md                                    ← Main reference (unchanged)
├── CONTEXT-VISION.md                           ← System vision (unchanged)
├── IMPLEMENTATION-ROADMAP.md                   ← Roadmap (unchanged)
├── FILING-SYSTEM.md                            ← THIS FILE (naming conventions)
│
├── agents/                                      ← Agent definitions
│   ├── pdf-agent.md
│   ├── backend-supabase-agent.md
│   ├── auth-agent.md
│   ├── frontend-flutter-specialist-agent.md
│   ├── backend-data-layer-agent.md
│   ├── code-review-agent.md
│   ├── qa-testing-agent.md
│   └── planning-agent.md
│
├── docs/                                        ← Feature documentation
│   └── features/                                ← Per-feature docs
│       ├── feature-pdf-overview.md
│       ├── feature-pdf-architecture.md
│       ├── feature-sync-overview.md
│       ├── feature-sync-architecture.md
│       ├── feature-auth-overview.md
│       ├── feature-auth-architecture.md
│       ├── feature-entries-overview.md
│       ├── feature-entries-architecture.md
│       ├── feature-photos-overview.md
│       ├── feature-photos-architecture.md
│       ├── feature-contractors-overview.md
│       ├── feature-contractors-architecture.md
│       ├── feature-dashboard-overview.md
│       ├── feature-dashboard-architecture.md
│       ├── feature-locations-overview.md
│       ├── feature-locations-architecture.md
│       ├── feature-projects-overview.md
│       ├── feature-projects-architecture.md
│       ├── feature-quantities-overview.md
│       ├── feature-quantities-architecture.md
│       ├── feature-settings-overview.md
│       ├── feature-settings-architecture.md
│       ├── feature-toolbox-overview.md
│       ├── feature-toolbox-architecture.md
│       ├── feature-weather-overview.md
│       └── feature-weather-architecture.md
│
├── architecture-decisions/                      ← Constraints & rules (feature-specific)
│   ├── data-validation-rules.md                 ← SHARED (applies to all features)
│   ├── pdf-v2-constraints.md
│   ├── sync-conflict-strategy.md
│   ├── auth-offline-behavior.md
│   ├── entries-constraints.md
│   ├── photos-constraints.md
│   ├── contractors-constraints.md
│   ├── dashboard-constraints.md
│   ├── locations-constraints.md
│   ├── projects-constraints.md
│   ├── quantities-constraints.md
│   ├── settings-constraints.md
│   ├── toolbox-constraints.md
│   └── weather-constraints.md
│
├── state/                                       ← JSON state files (machine-readable)
│   ├── PROJECT-STATE.json                       ← Overall health, blockers, priorities
│   ├── TASK-LIST.json                           ← Current phase tasks + contracts
│   ├── FEATURE-MATRIX.json                      ← All 13 features + status
│   ├── AGENT-CHECKLIST.json                     ← Pre-flight + post-work validation
│   ├── feature-pdf.json
│   ├── feature-sync.json
│   ├── feature-auth.json
│   ├── feature-entries.json
│   ├── feature-photos.json
│   ├── feature-contractors.json
│   ├── feature-dashboard.json
│   ├── feature-locations.json
│   ├── feature-projects.json
│   ├── feature-quantities.json
│   ├── feature-settings.json
│   ├── feature-toolbox.json
│   └── feature-weather.json
│
├── rules/                                       ← Expert guides (existing, unchanged)
│   ├── architecture.md
│   ├── platform-standards.md
│   ├── pdf/
│   │   └── pdf-generation.md
│   ├── sync/
│   │   └── sync-patterns.md
│   ├── database/
│   │   └── schema-patterns.md
│   ├── auth/
│   │   └── supabase-auth.md
│   ├── backend/
│   │   ├── data-layer.md
│   │   └── supabase-sql.md
│   ├── frontend/
│   │   └── flutter-ui.md
│   └── testing/
│       └── patrol-testing.md
│
├── prds/                                        ← PRD files for all 13 features
│   ├── pdf-extraction-v2-prd-2.0.md
│   └── [other PRDs by feature]
│
├── plans/                                       ← Implementation plans & detailed specs
│   ├── 2026-02-12-cmap-corruption-detection.md
│   ├── 2026-02-12-ocr-only-pipeline-design.md
│   └── [other detailed plans by date]
│
├── hooks/                                       ← Validation scripts
│   ├── pre-agent-dispatch.sh
│   └── post-agent-coding.sh
│
└── [other existing directories unchanged]
    ├── skills/
    ├── plugins/
    ├── autoload/
    ├── logs/
    └── ...
```

---

## Naming Conventions (CRITICAL)

### 1. Feature Documentation (`docs/`)

**PATTERN**: `feature-{feature-name}-{doc-type}.md`

**Examples**:
- `docs/features/feature-pdf-overview.md` — 300-400 words, business context + integration
- `docs/features/feature-pdf-architecture.md` — 800 words, data model + state management
- `docs/features/feature-sync-overview.md`
- `docs/features/feature-sync-architecture.md`
- `docs/features/feature-auth-overview.md`
- `docs/features/feature-auth-architecture.md`

**Rules**:
- ✓ ALL LOWERCASE (consistent glob patterns)
- ✓ Hyphens, not underscores
- ✓ Feature name matches `.claude/state/feature-{name}.json`
- ✓ Feature name matches `lib/features/{name}/` directory in code

**Naming for all 13 features**:
```
pdf, sync, auth, entries, photos, contractors,
dashboard, locations, projects, quantities, settings, toolbox, weather
```

---

### 2. Constraints Files (`architecture-decisions/`)

**PATTERN**: `{feature-name}-constraints.md` OR `{feature-name}-{aspect}.md`

**Examples**:
- `data-validation-rules.md` — SHARED (applies to all)
- `pdf-v2-constraints.md` — All V2 pipeline rules
- `sync-conflict-strategy.md` — Sync-specific constraints
- `auth-offline-behavior.md` — Auth-specific constraints
- `entries-constraints.md` — Entries-specific constraints

**Rules**:
- ✓ ALL LOWERCASE
- ✓ Match feature name in `feature-{name}-*.md` docs
- ✓ ONE constraint file per feature (or split if massive, but keep consistent)
- ✓ Shared rules in `data-validation-rules.md` (loaded by all agents)

---

### 3. State Files (`state/`)

**CORE STATE FILES** (4 files, loaded by all agents):
```
PROJECT-STATE.json          ← Overall app health, blockers, next 3 priorities
TASK-LIST.json              ← Current phase tasks + test contracts + metrics
FEATURE-MATRIX.json         ← All 13 features + status + integration
AGENT-CHECKLIST.json        ← Pre-flight + post-work validation templates
```

**FEATURE STATE FILES** (13 files, 1 per feature):

**PATTERN**: `feature-{feature-name}.json`

**Examples**:
- `feature-pdf.json`
- `feature-sync.json`
- `feature-auth.json`
- ... (repeat for all 13)

**Each contains**:
```json
{
  "feature_name": "pdf",
  "full_name": "PDF Extraction & Generation",
  "status": "in_progress",
  "owner_agent": "pdf-agent",
  "docs": {
    "overview": "docs/features/feature-pdf-overview.md",
    "architecture": "docs/features/feature-pdf-architecture.md",
    "prd": "prds/pdf-extraction-v2-prd-2.0.md"
  },
  "constraints": "architecture-decisions/pdf-v2-constraints.md",
  "integration_points": {
    "depends_on": ["photos", "sync"],
    "required_by": ["entries", "reports"]
  },
  "metrics": {
    "test_coverage": 87,
    "needs_documentation": false,
    "needs_refactoring": false
  },
  "last_updated": "2026-02-12T18:00:00Z"
}
```

**Rules**:
- ✓ Feature name matches `feature-{name}-overview.md`
- ✓ Feature name matches `lib/features/{name}/` in code
- ✓ Feature name matches agent name (if dedicated agent exists)

---

### 4. Agent Files (`agents/`)

**PATTERN**: `{feature-name}-agent.md` OR `{domain}-agent.md`

**Examples**:
```
pdf-agent.md                          ← Works on lib/features/pdf/
backend-supabase-agent.md             ← Works on sync + backend
auth-agent.md                         ← Works on lib/features/auth/
frontend-flutter-specialist-agent.md  ← Works on UI across all features
code-review-agent.md                  ← Meta: reviews all code
qa-testing-agent.md                   ← Meta: tests all features
planning-agent.md                     ← Meta: planning only
```

**Each agent file includes frontmatter**:
```yaml
---
name: pdf-agent
frontmatter:
  rules:
    - rules/architecture.md              (shared)
    - rules/pdf/pdf-generation.md        (feature-specific)
    - architecture-decisions/data-validation-rules.md   (shared)
    - architecture-decisions/pdf-v2-constraints.md      (feature-specific)
  docs:
    - docs/features/feature-pdf-overview.md       (feature-specific)
    - docs/features/feature-pdf-architecture.md   (feature-specific)
    - prds/pdf-extraction-v2-prd-2.0.md (PRD)
  state:
    - state/PROJECT-STATE.json           (current blockers/priorities)
    - state/TASK-LIST.json               (current phase + test contracts)
    - state/feature-pdf.json             (feature metadata)
---
```

**Rules**:
- ✓ Feature-specific agents: `{feature-name}-agent.md`
- ✓ Meta agents: `{domain}-agent.md`
- ✓ Frontmatter lists ONLY files needed for that agent (lazy-load)
- ✓ All agents load: `rules/architecture.md` + `architecture-decisions/data-validation-rules.md`

---

### 5. PRD Files (`prds/`)

**PATTERN**: `{feature}-{type}-prd-{version}.md`

**EXAMPLES**:
- `pdf-extraction-v2-prd-2.0.md` (complex feature, detailed, 1000+ lines)
- `sync-prd-1.0.md` (simpler feature, lightweight 200-400 words)

---

### 6. Rules Files (`rules/`)

**EXISTING STRUCTURE** (don't change):
```
rules/
├── architecture.md              (all agents load)
├── platform-standards.md
├── pdf/
│   └── pdf-generation.md        (pdf-agent loads)
├── sync/
│   └── sync-patterns.md         (sync agents load)
├── database/
│   └── schema-patterns.md
├── auth/
│   └── supabase-auth.md         (auth-agent loads)
├── backend/
│   ├── data-layer.md            (data-layer agents load)
│   └── supabase-sql.md          (supabase-agent loads)
├── frontend/
│   └── flutter-ui.md            (frontend agents load)
└── testing/
    └── patrol-testing.md        (qa-testing-agent loads)
```

**Naming rule**: Each domain (pdf, sync, auth, etc.) may have its own `rules/{domain}/` subdirectory.

---

## Complete File Mapping Example: PDF Feature

Here's how **all the pieces fit together** for ONE feature (PDF):

```
AGENT LAYER
───────────
agents/pdf-agent.md
  └─ frontmatter loads:
     ├─ rules/architecture.md (shared)
     ├─ rules/pdf/pdf-generation.md (feature-specific)
     ├─ architecture-decisions/data-validation-rules.md (shared)
     ├─ architecture-decisions/pdf-v2-constraints.md (feature-specific)
     ├─ docs/features/feature-pdf-overview.md (NEW - Phase 1)
     ├─ docs/features/feature-pdf-architecture.md (NEW - Phase 1)
     ├─ prds/pdf-extraction-v2-prd-2.0.md (existing)
     └─ state/feature-pdf.json (meta)

DOCUMENTATION LAYER
───────────────────
docs/features/feature-pdf-overview.md       (NEW - Phase 1, 300-400 words)
docs/features/feature-pdf-architecture.md   (NEW - Phase 1, 800 words)
prds/pdf-extraction-v2-prd-2.0.md (existing, 1,112 lines)
rules/pdf/pdf-generation.md        (existing, expert guide)

CONSTRAINTS LAYER
─────────────────
architecture-decisions/data-validation-rules.md (shared)
architecture-decisions/pdf-v2-constraints.md    (feature-specific)

STATE LAYER
───────────
state/PROJECT-STATE.json    (overall health, blockers, priorities)
state/TASK-LIST.json        (current phase + test contracts)
state/FEATURE-MATRIX.json   (all 13 features)
state/feature-pdf.json      (feature metadata)

CODE LAYER
──────────
lib/features/pdf/           (actual implementation)
test/features/pdf/          (tests)
integration_test/           (integration tests)
```

---

## How Agents Use This Map

### Agent Initialization (Pre-Flight)
1. Agent reads `.claude/FILING-SYSTEM.md` (this file)
2. Looks up feature in agent frontmatter
3. Loads all files listed in frontmatter (rules, docs, state)
4. Loads `architecture-decisions/data-validation-rules.md` (ALWAYS)
5. Loads current task from `state/TASK-LIST.json`

### Agent Decision-Making
When agent needs to know something:
- **"What can I build?"** → Read `docs/features/feature-{name}-overview.md` + `feature-{name}.json`
- **"What constraints apply?"** → Read `architecture-decisions/{name}-constraints.md`
- **"What files should I touch?"** → Read `state/feature-{name}.json` (integration points)
- **"What's the current blockers?"** → Read `state/PROJECT-STATE.json`
- **"What are my test contracts?"** → Read `state/TASK-LIST.json`
- **"What's the detailed spec?"** → Read PRD in `plans/`

### Agent Post-Work
1. Agent verifies constraints from `architecture-decisions/{name}-constraints.md`
2. Agent checks test contracts from `state/TASK-LIST.json`
3. Agent runs post-work validation
4. Agent updates `state/feature-{name}.json` (if status changed)
5. Agent reports completion

---

## Consistency Checks (For QA)

Run these queries to verify the system is consistent:

### Check 1: Feature names consistent across layers
```bash
# All these should list the same 13 features:
ls .claude/docs/features/feature-*-overview.md | sed 's/.*feature-//;s/-overview.*//'
ls .claude/state/feature-*.json | sed 's/.*feature-//;s/.json//'
ls .claude/architecture-decisions/*-constraints.md | sed 's/-constraints.*//' (minus data-validation-rules)
ls lib/features/
```

### Check 2: Feature state file matches FEATURE-MATRIX
```bash
# For each feature in state/feature-*.json, should have entry in FEATURE-MATRIX.json with same name
jq '.features[].name' state/FEATURE-MATRIX.json
ls state/feature-*.json | sed 's/.*feature-//;s/.json//'
```

### Check 3: Agent frontmatter files exist
```bash
# For each file listed in agent frontmatter, file should exist
# (Use manual inspection of agent files)
```

---

## When Adding the 13th Feature (Example: Weather)

1. **Create documentation**:
   ```
   .claude/docs/features/feature-weather-overview.md
   .claude/docs/features/feature-weather-architecture.md
   ```

2. **Create constraints**:
   ```
   .claude/architecture-decisions/weather-constraints.md
   ```

3. **Create state**:
   ```
   .claude/state/feature-weather.json
   ```

4. **Update FEATURE-MATRIX.json**:
   - Add entry with name: `weather`

5. **Create/update agent**:
   - If new agent: `agents/weather-agent.md` with frontmatter pointing to weather docs/constraints
   - If existing agent handles it: Update agent's frontmatter to include weather docs

6. **Verify consistency**:
   - Run checks above

---

## Summary Table

| Layer | Naming Pattern | Count | Shared? | Purpose |
|-------|---|---|---|---|
| Agents | `{name}-agent.md` | 8 | N/A | Agent definitions with frontmatter |
| Feature Docs | `feature-{name}-overview.md` + `architecture.md` | 26 (2×13) | No | Overview + architecture per feature |
| Constraints | `data-validation-rules.md` + `{name}-constraints.md` | 14 (1 shared + 13) | 1 shared | Hard/soft rules |
| Feature State | `feature-{name}.json` | 13 | No | Per-feature metadata |
| Core State | `PROJECT-STATE.json`, `TASK-LIST.json`, etc. | 4 | Yes | Shared across all agents |
| Rules | `{domain}/{name}.md` | Varies | No | Expert guides (existing) |
| Plans | `YYYY-MM-DD-{topic}-prd-*.md` | Varies | No | PRDs (existing) |

---

## Key Principles

1. ✓ **Consistency**: Same naming pattern across all 13 features
2. ✓ **Predictability**: If you know feature name, you can find all related files
3. ✓ **No Redundancy**: Each file has ONE purpose, not duplicated elsewhere
4. ✓ **Agent-Friendly**: Agents can follow the map to find what they need
5. ✓ **Strict Lazy-Loading**: Agents load ONLY what they need for THIS task (not everything "just in case")
6. ✓ **Scalable**: Adding feature #14 follows same pattern as #1-13

---

## PRD Guidelines (When to Create One)

### Create PRD When:
- Feature is undergoing major redesign (like PDF V2)
- Feature is new and complex (new behavior, integrations)
- Feature will take 3+ phases to complete

### Don't Create PRD When:
- Feature is stable (test coverage > 80%, no changes planned)
- Feature is simple (single screen, straightforward logic)
- Constraint file + architecture doc are sufficient

### PRD Template:

**For Complex Features** (like PDF):
- 1,000+ lines
- Detailed stage-by-stage spec
- Performance benchmarks
- Test contracts

**For Simple Features** (like sync, auth):
- 200-400 words
- Purpose, scope, core requirements
- Key entities, success criteria
- Pointers to detailed docs

---

## Lazy-Loading Rules (CRITICAL - Enforce Strictly)

### ✓ ALWAYS Load (No Exceptions)

These files are **universal** and apply to every agent, every task:

```yaml
shared_rules:
  - rules/architecture.md              # Foundational patterns (all agents)
  - architecture-decisions/data-validation-rules.md  # Mandatory safety rules (all agents)
```

**Why**: These establish baseline constraints that prevent repeated mistakes.

---

### ✓ FEATURE-SPECIFIC Load (When Working on Feature X)

When an agent works on feature `{name}`, it loads:

```yaml
feature_rules:
  - rules/{domain}/{name}.md           # Expert guide for this feature
  - architecture-decisions/{name}-constraints.md  # Hard/soft rules for this feature

feature_docs:
  - docs/features/feature-{name}-overview.md    # Business purpose + integration points
  - docs/features/feature-{name}-architecture.md # Data model + state management

feature_state:
  - state/feature-{name}.json          # Feature metadata + integration points
```

**Cost per feature**: ~4,000 tokens (lightweight)

**Why**: Agent needs to understand its specific domain but not others.

---

### ✗ NEVER Load (Except Explicit Request)

These files are **context bloat** and should NOT be in frontmatter:

```yaml
# DON'T load:
- docs/features/feature-{OTHER_FEATURE}-*.md    # Other features' docs (unless integrating)
- state/FEATURE-MATRIX.json            # Full feature list (agent doesn't need it)
- Any other agent's rules              # Different domains have different rules
- All PRDs at once                      # Load only when working on that phase
- All state files at once               # Load only current task state
```

**Why**: Wastes tokens and creates context confusion (agent doesn't know which rules apply to their work).

---

### ? CONDITIONAL Load (Check Task Indicator)

These files load **only if the current task requires them**. The task indicator is in `state/TASK-LIST.json`:

#### When to Load: `prds/[PRD]`

**Task indicator**: `"requires_deep_spec": true`

```yaml
optional_deep_spec:
  - prds/pdf-extraction-v2-prd-2.0.md
```

**When**: Task involves understanding full 7-stage pipeline spec, confidence models, or performance benchmarks

**Cost**: +3,800 tokens (load only when needed)

**Example tasks**:
- "Rewrite golden test with 3-layer framework" (needs full spec)
- "Build parameterized benchmark suite" (needs perf targets from PRD)
- "Implement re-extraction loop" (needs decision points from PRD)

**Counter-example** (don't load PRD):
- "Fix broken test for Stage 4" (constraints file is enough)
- "Update fixture file" (overview + architecture sufficient)

---

#### When to Load: Integration with Another Feature

**Task indicator**: `"integration_with": ["feature-name"]`

```yaml
optional_integration_docs:
  - docs/features/feature-sync-overview.md      # If integrating with sync
  - docs/features/feature-auth-architecture.md  # If integrating with auth
```

**When**: Task involves wiring two features together

**Cost**: +1,500-2,000 tokens per integrated feature (load only when needed)

**Example tasks**:
- "Wire PDF extraction into entries feature" (load entries-overview.md)
- "Add sync queue for PDF changes" (load sync-overview.md + sync-architecture.md)
- "Validate auth before PDF processing" (load auth-overview.md)

---

#### When to Load: Cross-Feature Blockers

**Task indicator**: `"requires_blocker_context": true`

```yaml
optional_project_state:
  - state/PROJECT-STATE.json           # Check active blockers
```

**When**: Task depends on resolving a blocker, or you need to understand risk dependencies

**Cost**: ~280 tokens

**Example tasks**:
- "Unblock OCR rendering timeout" (need BLOCK-001 context)
- "Implement sync conflict resolution" (might depend on other feature blockers)

---

### Current Task Context (NOT in Frontmatter)

**TASK DETAILS should come in the task prompt, not frontmatter:**

Instead of loading entire `TASK-LIST.json`, the parent prompt includes:
```json
{
  "task_id": "T2.1",
  "feature": "pdf",
  "title": "Regenerate OCR golden fixtures",
  "test_contract": [...],
  "requires_deep_spec": true,
  "integration_with": [],
  "requires_blocker_context": false
}
```

**Agent uses this to know**:
- ✓ Which feature to work on
- ✓ What test success looks like
- ✓ Whether to load deep spec (PRD)
- ✓ Which other features to integrate with

---

## Agent Frontmatter Template (Lazy-Loading Compliant)

```yaml
---
name: {agent-name}
frontmatter:

  # SHARED (always loaded)
  shared_rules:
    - rules/architecture.md
    - architecture-decisions/data-validation-rules.md

  # FEATURE-SPECIFIC (loaded when working on this feature)
  feature_rules:
    - rules/{domain}/{name}.md
    - architecture-decisions/{name}-constraints.md

  feature_docs:
    - docs/features/feature-{name}-overview.md
    - docs/features/feature-{name}-architecture.md

  feature_state:
    - state/feature-{name}.json

  # CONDITIONAL (loaded only if task indicator set)
  # Task prompt will indicate if these are needed via:
  #   - requires_deep_spec: true → load PRD
  #   - integration_with: [feature] → load that feature's overview/architecture
  #   - requires_blocker_context: true → load PROJECT-STATE.json
  optional:
    # Don't include these here; agent checks task prompt and requests if needed
    # Example: "Task requires deep spec, loading PRD..."
---
```

---

## Examples: What Different Tasks Load

### Task Type A: Simple Feature Enhancement (Low Context)

```
Task: "Fix broken test for Stage 4 quality validation"

Frontmatter loads:
  - rules/architecture.md
  - architecture-decisions/data-validation-rules.md
  - rules/pdf/pdf-generation.md
  - architecture-decisions/pdf-v2-constraints.md
  - docs/features/feature-pdf-overview.md
  - docs/features/feature-pdf-architecture.md
  - state/feature-pdf.json

Token cost: ~4,500 tokens ✓
Task prompt includes: test_contract + which test file to fix
```

### Task Type B: Deep Implementation (Medium Context)

```
Task: "Rewrite golden test with 3-layer framework"
      (requires_deep_spec: true)

Frontmatter loads:
  + SAME AS ABOVE (~4,500 tokens)
  + prds/pdf-extraction-v2-prd-2.0.md  (+3,800 tokens)

Token cost: ~8,300 tokens ✓
Task prompt includes: test_contract + benchmark targets from PRD
```

### Task Type C: Integration Work (Medium-High Context)

```
Task: "Wire PDF extraction into entries feature"
      (integration_with: ["entries"])

Frontmatter loads:
  PDF context:
    - rules/architecture.md
    - architecture-decisions/data-validation-rules.md
    - rules/pdf/pdf-generation.md
    - architecture-decisions/pdf-v2-constraints.md
    - docs/features/feature-pdf-overview.md
    - docs/features/feature-pdf-architecture.md
    - state/feature-pdf.json

  Entries context:
    - docs/features/feature-entries-overview.md
    - docs/features/feature-entries-architecture.md
    - state/feature-entries.json
    - architecture-decisions/entries-constraints.md

Token cost: ~8,000 tokens ✓
Task prompt includes: which APIs to expose + which entry screens to integrate with
```

### Task Type D: Blocker Resolution (Medium Context)

```
Task: "Investigate and fix OCR rendering timeout"
      (requires_blocker_context: true)

Frontmatter loads:
  + PDF context (as above) (~4,500 tokens)
  + state/PROJECT-STATE.json  (+280 tokens)

Token cost: ~4,780 tokens ✓
Task prompt includes: BLOCK-001 details + investigation notes
```

---

## Lazy-Loading Enforcement Checklist

**Before frontmatter is finalized, agent verifies:**

- [ ] Shared rules loaded? (rules/architecture.md + data-validation-rules.md)
- [ ] Feature-specific rules loaded? (rules/{domain}/{name}.md + constraints)
- [ ] Feature docs loaded? (overview + architecture)
- [ ] Feature state loaded? (feature-{name}.json)
- [ ] Other feature docs excluded? (unless integration_with indicates otherwise)
- [ ] PRD excluded? (unless requires_deep_spec: true in task)
- [ ] PROJECT-STATE excluded? (unless requires_blocker_context: true in task)
- [ ] FEATURE-MATRIX excluded? (never needed)
- [ ] Unrelated rules excluded? (only load your domain's rules)

**Token cost estimate**: Should be 4,000-8,000 tokens max (before task work)

---

## Enforcement Rule for Phase 1 Documentation

When writing `feature-{name}-overview.md` and `feature-{name}-architecture.md`, each doc:

**MUST NOT duplicate content from**:
- `rules/{domain}/{name}.md` (expert guide)
- `architecture-decisions/{name}-constraints.md` (hard/soft rules)
- `plans/PRD` (detailed spec)

**SHOULD include**:
- Purpose + why this feature exists
- Integration points (depends_on, required_by)
- Key responsibilities (what this feature does)
- Pointers to detailed specs (e.g., "See pdf-generation.md for template mapping details")
- File locations (which lib/features/{name}/ paths agents will work on)
- Testing patterns (if not covered in rules)

**Result**: Docs are 300-800 words, lightweight, and don't repeat existing context.
