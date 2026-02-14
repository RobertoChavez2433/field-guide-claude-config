# Implementation Plan: Documentation System + Feature Docs Phase 1

**Status**: Ready to Execute
**Last Updated**: 2026-02-13
**Scope**: Complete foundation for agent autonomy via lazy-loaded docs + constraints
**Estimated Timeline**: 13-15 hours of work
**Context Required**: Minimal (all decisions locked in)

---

## Executive Summary

You will execute a 4-phase rollout to transform the codebase from fragmented documentation to a unified, lazy-loaded system that enables agent autonomy:

| Phase | Deliverable | Files | Hours | Status |
|-------|---|---|---|---|
| **0** | ✓ Directory structure, state files, constraints skeleton, FILING-SYSTEM.md | 15 | 4 | **COMPLETE** |
| **1** | Feature documentation (overview + architecture for all 13) + PRD directory | 39 | 8-10 | **NEXT** |
| **2** | Agent frontmatter updates + PRD template creation | 8 agents + 12 PRDs | 3-4 | After Phase 1 |
| **3** | Workflow integration + validation | Scripts, CLAUDE.md update | 2 | After Phase 2 |
| **4** | Test with real agent task (Wave 1 + Wave 2) | Actual work | 3 | After Phase 3 |

**Total Scope**: **52 files created/modified, 52 hours estimated for complete system** (you've done 4, have 48 remaining)

---

## Phase 1: Feature Documentation (YOUR IMMEDIATE NEXT WORK)

### 1.1: Create PRD Directory + Move PDF PRD

**Step 1**: Create directory
```bash
mkdir -p .claude/prds
```

**Step 2**: Move existing PDF PRD
```bash
# Physically move file to new location
mv .claude/plans/2026-02-11-pdf-extraction-pipeline-v2-prd-2.0.md \
   .claude/prds/pdf-extraction-v2-prd-2.0.md

# Update any references in state files
# (Will be done in Step 1.3)
```

**Files involved**: 1 (move, not new)

---

### 1.2: Create 13 Feature Overview Docs + 13 Feature Architecture Docs

**Location**: `.claude/docs/`

**Files to create** (26 total):

#### Group A: Critical Path (Highest Priority)
1. ✓ `feature-pdf-overview.md` (300-400 words)
2. ✓ `feature-pdf-architecture.md` (800 words)
3. ✓ `feature-sync-overview.md` (300-400 words)
4. ✓ `feature-sync-architecture.md` (800 words)
5. ✓ `feature-auth-overview.md` (300-400 words)
6. ✓ `feature-auth-architecture.md` (800 words)

#### Group B: Core Features (Secondary Priority)
7. ✓ `feature-entries-overview.md`
8. ✓ `feature-entries-architecture.md`
9. ✓ `feature-photos-overview.md`
10. ✓ `feature-photos-architecture.md`

#### Group C: Remaining 8 Features (Tertiary Priority)
11-26. `feature-{name}-overview.md` + `architecture.md` for:
- contractors, dashboard, locations, projects, quantities, settings, toolbox, weather

**Writing guidelines per file**:

**Overview.md (300-400 words each)**:
- Purpose (1-2 sentences: why feature exists)
- Key responsibilities (3-5 bullet points: what it does)
- Key files (table: file → purpose)
- Data sources (SQLite, Supabase, cache)
- Integration points (depends on, required by)
- Offline behavior (if applicable)
- Edge cases & limitations
- Pointer to detailed specs ("See {rules-file} for template mapping details")

**Architecture.md (800 words each)**:
- Data model (entity table with fields)
- Relationships (1-N, 1-1, etc.)
- Repository pattern (key classes + methods)
- State management (Provider, ChangeNotifier, key state)
- Offline behavior (read/write queuing, conflict resolution)
- Testing strategy (unit/widget/integration tiers)
- Performance considerations
- File locations (`lib/features/{name}/...`)

**Effort**: ~30 minutes per feature × 13 = 6.5 hours
**Output**: 26 files, ~15,000-20,000 words total

---

### 1.3: Create 13 Constraint Files

**Location**: `.claude/architecture-decisions/`

**Files to create** (13 total, one per feature):

1. ✓ `pdf-v2-constraints.md` (EXISTS - keep as-is)
2. `sync-conflict-strategy.md` (NEW)
3. `auth-offline-behavior.md` (NEW)
4. `entries-constraints.md` (NEW)
5. `photos-constraints.md` (NEW)
6. `contractors-constraints.md` (NEW)
7. `dashboard-constraints.md` (NEW)
8. `locations-constraints.md` (NEW)
9. `projects-constraints.md` (NEW)
10. `quantities-constraints.md` (NEW)
11. `settings-constraints.md` (NEW)
12. `toolbox-constraints.md` (NEW)
13. `weather-constraints.md` (NEW)

**Template per file (300-500 words)**:

```markdown
# {Feature} Constraints

## Hard Rules (Violations = Reject Proposal)
- ✗ Rule 1 (non-negotiable)
- ✗ Rule 2
- ✗ Rule 3

## Soft Guidelines (Violations = Discuss)
- ⚠ Guideline 1
- ⚠ Guideline 2

## Integration Points
- **Depends on**: [Feature 1], [Feature 2]
- **Required by**: [Feature 1], [Feature 2]

## Performance Targets
- Target 1: < X ms
- Target 2: >= Y% coverage

## Testing Requirements
- >= 85% test coverage
- All public methods tested (happy + error paths)
- Integration tests for sync/offline scenarios (if applicable)
```

**Effort**: ~20 minutes per feature × 12 = 4 hours (PDF constraint already exists)
**Output**: 13 files, ~4,000-5,000 words total

---

### 1.4: Update FILING-SYSTEM.md

**Changes**:

A. **Add PRD Directory Section** (after "Directory Structure"):
```markdown
### prds/
PRD files for all 13 features. One PRD per feature (may have versions).

PATTERN: {feature}-{type}-prd-{version}.md

EXAMPLES:
- pdf-extraction-v2-prd-2.0.md (complex feature, detailed)
- sync-prd-1.0.md (simpler feature, lightweight)
```

B. **Update Lazy-Loading Rules** - Change references from `plans/PRD` to `prds/{name}-prd-*.md`:
- Line 523: `- plans/2026-02-11-pdf-extraction-pipeline-v2-prd-2.0.md` → `- prds/pdf-extraction-v2-prd-2.0.md`
- Line 671: Same change

C. **Update Enforcement Rule** - Line 744: `- plans/PRD` → `- prds/{name}-prd-*.md`

D. **Add new section**: "PRD Guidelines"
```markdown
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
```

**Effort**: ~30 minutes
**Output**: Updated FILING-SYSTEM.md with 3 new sections

---

### 1.5: Update State Files (if not already done in Phase 0)

**Files to update**:

A. **state/FEATURE-MATRIX.json** - Ensure all 13 features have entries:
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
        "prd": "prds/pdf-extraction-v2-prd-2.0.md"
      },
      "constraints": "architecture-decisions/pdf-v2-constraints.md",
      ...
    },
    { "name": "sync", ... },
    { "name": "auth", ... },
    ... (12 more)
  ]
}
```

B. **state/feature-{name}.json** (13 files) - Ensure all created in Phase 0:
- Each should reference corresponding docs, constraints, PRD (if exists)

**Effort**: ~30 minutes (mostly copy-paste with name substitution)
**Output**: Updated JSON files with all 13 features properly linked

---

## Phase 1 Summary: Deliverables

| Category | Files | Words | Hours |
|----------|-------|-------|-------|
| **Move PDF PRD** | 1 | - | 0.25 |
| **Feature overviews** | 13 | 4,500-5,200 | 3.5 |
| **Feature architectures** | 13 | 10,400-13,000 | 6.5 |
| **Constraint files** | 12 | 3,600-6,000 | 3 |
| **Update FILING-SYSTEM.md** | 1 | +800 | 0.5 |
| **Update state files** | 14 | - | 0.5 |
| **SUBTOTAL** | **54 files** | **~24,000 words** | **~14.25 hours** |

---

## Execution Strategy for Phase 1

### Option 1: One-Feature-at-a-Time (Recommended)
1. Draft `feature-pdf-overview.md` + `architecture.md` + `pdf-v2-constraints.md`
2. **You review** (check for clarity, redundancy, completeness)
3. Approve or request revisions
4. Move to Sync
5. Repeat for all 13
6. **Timeline**: 14 hours spread over 2-3 sessions

### Option 2: Batch by Priority (Faster)
1. Draft Group A (PDF, Sync, Auth) completely
2. You review all 3
3. Draft Group B (Entries, Photos)
4. You review
5. Draft Group C (remaining 8)
6. You review
7. **Timeline**: 14 hours compressed into 1-2 sessions

**Recommendation**: **Option 1** (one at a time) keeps quality high and feedback cycles tight.

---

## Critical Enforcement Rules (Lock These In)

### Rule 1: No Content Duplication
- Feature overview ≠ constraint file ≠ architecture doc ≠ rules guide ≠ PRD
- Each file has ONE purpose
- If you're tempted to repeat content, link to source instead ("See pdf-generation.md for template mapping details")

### Rule 2: Lazy-Loading Strict Compliance
- Agents load: overview + architecture + constraints for THEIR feature only
- Agents DON'T load: other features' docs, full FEATURE-MATRIX.json, all state files
- Conditional: PRD, integration docs, PROJECT-STATE.json (check task indicator)

### Rule 3: File Naming Consistency
- All 13 features use same naming pattern
- Feature name matches: lib/features/{name}/, docs/{name}-*, constraints/{name}-*, state/feature-{name}.json
- If feature name is multi-word, use hyphen (not underscore, not camelCase)

### Rule 4: Constraint Files Are Mandatory
- Every feature must have a constraints file
- Even if it's "standard constraints + 2-3 custom rules"
- This prevents architectural drift

---

## Files Summary (What Exists vs. What's Created)

### Pre-Phase-0 (Before System Design)
- ✓ rules/ (10 files)
- ✓ plans/ (4 files - PDF only)
- ✓ docs/ (5 files - guidelines, not feature docs)
- ✓ state/ (foundation with 4 core JSON files)

### Phase 0 Delivered (Already Done)
- ✓ FILING-SYSTEM.md
- ✓ CONTEXT-VISION.md
- ✓ IMPLEMENTATION-ROADMAP.md
- ✓ architecture-decisions/data-validation-rules.md
- ✓ architecture-decisions/pdf-v2-constraints.md
- ✓ state/PROJECT-STATE.json
- ✓ state/TASK-LIST.json
- ✓ state/FEATURE-MATRIX.json (template)
- ✓ state/AGENT-CHECKLIST.json
- ✓ state/feature-pdf.json (template)
- ✓ agent frontmatter examples

### Phase 1 To Create (YOUR WORK)
- **NEW**: prds/ directory (0 → 13 PRDs eventually, start with 1 moved from plans/)
- **NEW**: 26 feature docs (overview + architecture for all 13)
- **NEW**: 12 constraint files (sync, auth, entries, photos, contractors, dashboard, locations, projects, quantities, settings, toolbox, weather)
- **UPDATE**: FILING-SYSTEM.md (add PRD section, update lazy-loading examples)
- **UPDATE**: state files (ensure all 13 features linked correctly)

**Total Phase 1 Files Created**: 39 new + 1 directory
**Total Docs Written**: ~24,000 words

---

## After Phase 1: What's Next (Reference Only)

### Phase 2: Agent Frontmatter Updates
- Update 8 agent files with frontmatter pointing to feature docs + constraints
- Create PRD template for lightweight features (sync, auth, entries, photos)
- Create 12 simple PRD files (200-400 words each) for stable features

### Phase 3: Workflow Integration
- Update CLAUDE.md with "Documentation System" section
- Create optional pre-flight validation script
- Create session kickoff checklist

### Phase 4: Test with Real Work
- Pick one real task (e.g., "Fix bug in entries feature")
- Run through new system: brainstorm → agent dispatch → post-work validation
- Measure: Did agent have right context? Did quality improve?

---

## Resuming This Work

When you come back to continue:

1. **Read this file** (you're reading it now)
2. **Current task**: Draft Phase 1 files (start with pdf-overview.md)
3. **Reference files**: FILING-SYSTEM.md, CONTEXT-VISION.md, pdf-v2-constraints.md (already exists, use as template)
4. **No need to re-read**: The 20+ messages above — it's all captured here

---

## Quick Command Reference

```bash
# Create prds directory
mkdir -p .claude/prds

# Move PDF PRD
mv .claude/plans/2026-02-11-pdf-extraction-pipeline-v2-prd-2.0.md \
   .claude/prds/pdf-extraction-v2-prd-2.0.md

# View feature template (reference)
cat .claude/architecture-decisions/pdf-v2-constraints.md

# List what's been created
ls -la .claude/docs/feature-*
ls -la .claude/architecture-decisions/*-constraints.md
ls -la .claude/prds/
```

---

## Success Criteria for Phase 1

When complete, you should have:

- ✓ 13 overview docs (300-400 words each)
- ✓ 13 architecture docs (800 words each)
- ✓ 13 constraint files (300-500 words each)
- ✓ FILING-SYSTEM.md updated with PRD section + examples
- ✓ All state files updated to reference new docs
- ✓ Zero content duplication (docs don't repeat rules/constraints/PRD)
- ✓ All 13 feature names consistent across all files
- ✓ Ready for Phase 2 (agent frontmatter updates)

---

## Token Usage Notes

- **This file**: ~3,000 tokens (reference only)
- **Phase 1 work**: ~24,000 tokens (spread across 39 files)
- **Parent conversation** (what you just read): ~65,000 tokens (captured here, can be archived)
- **When resuming**: Read this file (~3,000 tokens) instead of full conversation (~65,000 tokens)

**Net savings on resume**: ~62,000 tokens per session

---

## Decision Log (Locked In)

✓ Use strict lazy-loading (don't load everything, load only per task)
✓ Create PRD directory separate from plans/
✓ Create constraint files for all 13 features (even stable ones)
✓ Feature overview ≠ architecture doc (different purposes)
✓ Use one-at-a-time review (PDF → Sync → Auth → rest)
✓ No content duplication across docs/constraints/rules/PRD
✓ All features follow same naming pattern

---

**You're ready to start. Next session: Draft feature-pdf-overview.md**
