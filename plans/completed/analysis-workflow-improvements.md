# Workflow Improvements Analysis
Based on Insights Report + Project Setup Review

## Current State

**Strengths:**
- Well-documented CLAUDE.md with clear agent/skill separation
- Comprehensive defects log capturing patterns to avoid
- Settings with broad permissions for power users
- 6 specialized agents + 6 skills covering the full dev lifecycle
- Session management (resume/end-session skills)

**Gaps:**
- No hooks directory (settings.local.json only)
- No automated validation after agent-generated code
- No per-session checkpoint tracking
- Architectural decisions scattered (repeated corrections across 30 sessions)

---

## Friction Analysis: Insights Report → Root Causes

### Category 1: Sub-Agent Infrastructure Failures (21% of sessions)

**Symptom**: "classifyHandoffIfNeeded is not defined" errors in ~8 sessions

**Root Cause**:
- Sub-agents hit turn limits → framework error → context bloat
- Permission issues (write, web access) discovered AFTER agent spawning
- No pre-flight validation before Task dispatch

**Current Band-Aid**: You re-run tasks manually or in follow-up sessions

---

### Category 2: Buggy Generated Code (30 instances across sessions)

**Common Patterns**:
1. **Over-broad regex** — Currency pattern matches more than intended
2. **Missing enum values** — V1 enums not updated when adding V2 variants
3. **Hardcoded strings** — Constants updated in one file but not secondary references
4. **Bad mocks** — Fixture format mismatches (pipeline output vs. curated format)
5. **Copy-paste V1** — Agents reuse legacy V1 code in V2 tasks (you caught this!)

**Current Band-Aid**: 3-round fix cycles during implementation

**Prevention Opportunity**: Test immediately after each edit, catch issues before they cascade

---

### Category 3: Wrong Approaches (21 instances)

**Repeated corrections you made**:
- Hybrid OCR strategies (rejected 5+ times) → Binary routing only
- V1/V2 settings toggles (rejected) → No legacy compatibility flags
- ToUnicode repair ideas (rejected) → Native/OCR routing only
- V1 imports in V2 code (rejected) → Zero legacy imports

**Current Band-Aid**: You re-explain decision every session

**Prevention Opportunity**: Encode architectural decisions in CLAUDE.md constraints section

---

### Category 4: Planning Sessions Without Execution (5 sessions)

**Pattern**: Plan created, scope clarified, but no implementation starts

**Root Cause**:
- Context consumed by exploration + planning
- Agent dispatch deferred to next session
- Golden fixture regeneration never executed (lingered at discussion stage)

**Prevention**: Front-load decisions, compress planning phase, add checkpoint protocol

---

## Proposed Hook Strategy

Hooks run **locally** (post-edit, pre-commit) to catch issues before they spread.

### Hook 1: Post-Edit Code Validation

**Trigger**: After any `.dart` file in `lib/features/pdf/` is edited

**Runs**:
```bash
dart analyze --no-fatal-infos lib/features/pdf/ 2>&1 | head -30
```

**Prevents**:
- Syntax errors (immediate feedback)
- Missing imports
- Type mismatches (hardcoded strings, enum mismatches)

**Why**: Agents frequently forget to update secondary references when changing enums/constants. Early detection stops cascading failures.

---

### Hook 2: Fixture Format Validator

**Trigger**: After `test/features/pdf/extraction/fixtures/` JSON files are modified

**Runs**:
```bash
# Validate fixture schema matches expected format
python3 .claude/scripts/validate_fixture_format.py test/features/pdf/extraction/fixtures/
```

**Prevents**:
- Pipeline output overwriting curated fixtures (session 321 issue)
- Format mismatches between golden and integration tests
- Silent fixture corruption

**Why**: Golden fixture regeneration repeatedly created mismatches. Schema validation prevents silent data loss.

---

### Hook 3: V1 Legacy Code Guard

**Trigger**: Any edit to `lib/features/pdf/services/extraction/`

**Runs**:
```bash
# Detect V1 imports in V2 code
grep -r "import.*deprecated" lib/features/pdf/services/extraction/ --include="*.dart" || echo "✓ No legacy imports"
grep -r "from_v1\|v1_compat\|LegacyStage" lib/features/pdf/services/extraction/ --include="*.dart" || echo "✓ No V1 compat patterns"
```

**Prevents**:
- Copy-paste V1 code (you caught this in phases 4A/4B)
- Unintended legacy dependencies
- Architectural violations

**Why**: Agents frequently reuse V1 code when they should write V2. Guard catches it immediately.

---

### Hook 4: Test Suite Post-Edit

**Trigger**: After any `lib/features/pdf/` file is edited

**Runs**:
```bash
# Run tests only for changed feature, fail fast
pwsh -Command "flutter test test/features/pdf/ --reporter=compact 2>&1 | tail -20"
```

**Prevents**:
- Buggy code shipping from editing session
- Fixture mismatches propagating
- "3-round fix cycle" pattern

**Why**: Your sessions show agents generate code, you discover failures during review, 2-3 fix rounds follow. Test immediately = first-pass quality.

---

### Hook 5: Checkpoint Pre-Commit

**Trigger**: Before any git commit

**Runs**:
```bash
# Verify IMPLEMENTATION-STATE.json exists and is valid
python3 -m json.tool .claude/IMPLEMENTATION-STATE.json > /dev/null && echo "✓ Checkpoint valid" || echo "✗ Invalid checkpoint state"
```

**Prevents**:
- Session resumption without proper state tracking
- Lost progress when context limits hit
- Duplicate work across sessions

**Why**: Your insights mention context limits forcing early session ends. Checkpoint protocol requires validation on every commit.

---

### Hook 6: Architectural Constraints Guard

**Trigger**: Any edit to `lib/features/pdf/services/extraction/`

**Runs**:
```bash
# Prevent proposed patterns you've rejected
grep -i "hybrid.*ocr\|settings.*toggle.*v1\|legacy.*compat" lib/features/pdf/services/extraction/ --include="*.dart" && \
  echo "⚠ WARNING: Rejected architectural pattern detected" && exit 1 || \
  echo "✓ No architectural violations"
```

**Prevents**:
- Repeated proposals for hybrid OCR (rejected 5+ times)
- V1/V2 toggle settings
- ToUnicode repair strategies

**Why**: You've had to reject these approaches multiple times. Automatic detection prevents re-proposals.

---

## Workflow Change Recommendations

### 1. Add Architectural Decisions Section to CLAUDE.md

**Current**: Scattered across 30 sessions

**Proposed**:

```markdown
## Architectural Constraints (PDF Extraction V2)

**HARD RULES** (violations = reject proposal):
- ✗ No hybrid OCR strategies — use binary native/OCR routing ONLY
- ✗ No V1/V2 settings toggles — no legacy compatibility flags
- ✗ No ToUnicode repair attempts — use routing instead
- ✗ No V1 imports in V2 code — zero legacy dependencies
- ✗ No copy-paste V1 implementations — all V2 code must be novel

**SOFT GUIDELINES** (violations = discuss first):
- Prefer native text extraction, fall back to OCR only when needed
- Test fixture formats before regenerating golden outputs
- Update all enum values and constant references together

**Why These Exist**: [Link to decision history or PRD rationale]
```

**Impact**: Every new session (including sub-agents) inherits these constraints automatically. No repeated corrections.

---

### 2. Create IMPLEMENTATION-STATE.json Template

**Purpose**: Session-to-session resumption without re-discovery

**Structure**:
```json
{
  "plan_file": "plans/2026-02-12-v2-pipeline-cleanup.md",
  "phases": [
    {
      "id": "P7",
      "status": "in_progress",
      "tasks": [
        {
          "id": "T7.1",
          "status": "complete",
          "description": "Document quality profiler",
          "files_modified": ["lib/features/pdf/services/extraction/stages/document_quality_profiler.dart"],
          "tests_passing": 45,
          "tests_failing": 0
        }
      ]
    }
  ],
  "last_test_run": {
    "total": 730,
    "passing": 730,
    "failing": 0,
    "timestamp": "2026-02-13T10:30:00Z"
  },
  "next_action": "Implement T7.2 (element validator) — fix row classification edge cases",
  "blockers": [],
  "notes": "Springfield fixture regeneration complete. All golden tests passing."
}
```

**Usage**:
1. Create at start of phase
2. Update after every task completion
3. Save in git (committed with each task)
4. Next session reads → resumes immediately

**Impact**: Context freed from "where were we?" discovery. More time implementing.

---

### 3. Pre-Flight Agent Dispatch Checklist

**Current**: Spawn 5-8 agents, some fail with permission errors

**Proposed**: Before any Task tool call:

```markdown
## Agent Dispatch Validation

1. **Permissions**:
   - [ ] Test sub-agent can write files (run `flutter pub get`)
   - [ ] Test sub-agent can run tests (run `flutter test --version`)
   - [ ] Test sub-agent can access web if needed (WebFetch test)

2. **Constraints**:
   - [ ] Each agent receives HARD RULES from CLAUDE.md
   - [ ] Each agent knows: no V1 imports, no hybrid OCR, no legacy compat
   - [ ] Each agent given expected fixture format (JSON schema link)

3. **Task Decomposition**:
   - [ ] Max 3-4 agents per wave (context-per-agent)
   - [ ] Sequential waves: implementation → integration → testing
   - [ ] Each agent has clear definition of done (tests passing)

4. **Abort Criteria**:
   - [ ] If agent hits "classifyHandoffIfNeeded" error → escalate to sequential execution
   - [ ] If agent permission denied → fix environment before retry
   - [ ] If tests failing → agent iterates (not shipped)
```

**Impact**: Fewer failed agent spawns. Faster execution. Clear handoffs between waves.

---

### 4. Post-Agent Code Review Audit

**Current**: Agents ship work, you discover 3-round fixes needed

**Proposed**: Before accepting agent output:

```markdown
## Post-Agent Acceptance Criteria

- [ ] **No V1 copy-paste**: Search for hardcoded class names from V1 stages
- [ ] **Constant references updated everywhere**: Grep old constant names in repo
- [ ] **Enum values complete**: All V1 values migrated OR documented rationale for removal
- [ ] **Fixture formats verified**: Compare output JSON schema vs. curated fixtures
- [ ] **Tests passing**: Full test suite green (not just unit tests)
- [ ] **No hardcoded strings**: Check for literal values that should be parameters
- [ ] **Analyzer clean**: `dart analyze` passes with no warnings
```

**Impact**: First-pass code quality. Fewer fix rounds. Agents iterate autonomously until criteria met.

---

## Implementation Roadmap

| Step | Effort | Impact | Timeline |
|------|--------|--------|----------|
| 1. Add hooks directory + 6 hook scripts | 2h | Catches 30% of bugs early | Today |
| 2. Add Architectural Constraints to CLAUDE.md | 1h | Prevents repeated corrections | Today |
| 3. Create IMPLEMENTATION-STATE.json template | 1h | Enables session resumption | Today |
| 4. Document pre-flight & post-agent checklists | 1h | Reduces agent failures | Today |
| 5. Test hooks on real work (next phase) | 2h | Validate effectiveness | Next phase |

---

## Expected Impact

### Before (Current Pattern)
- 30 buggy code instances per 30 sessions
- 3-round fix cycles per feature
- Sub-agent failures in 8 sessions
- Architectural decisions repeated 5+ times
- 54% fully-achieved sessions

### After (With Hooks + Workflow)
- Bugs caught in minutes (post-edit hooks)
- First-pass code quality (test immediately)
- Agent permissions validated pre-dispatch
- Architectural constraints inherited (one-time write to CLAUDE.md)
- Expected: 65-75% fully-achieved sessions

---

## Questions for User

1. **Hooks Framework**: Claude Code doesn't have a built-in "hooks" system yet. Should we:
   - Use `.claude/scripts/` directory with bash/python that you run manually before commits?
   - Create a custom "pre-work" skill that runs these validations?
   - Set up a git pre-commit hook that runs automatically?

2. **Checkpoint Aggressiveness**: How often should the state file be updated?
   - Every task completion (most accurate)?
   - Every 4 hours (session-checkpoint style)?
   - Manual on demand?

3. **Priority**: Which issue hurts most?
   - Sub-agent failures (infrastructure)
   - Buggy code requiring fix cycles (quality)
   - Repeated architectural corrections (efficiency)
   - Planning without execution (throughput)
