---
name: context-memory-optimization
description: Optimize session state and defects memory with 3-tier archiving system
status: COMPLETE
created: 2026-02-01
completed: 2026-02-01
priority: HIGH
---

# Context Memory Optimization Plan

## Problem Analysis

### Current Issues
1. **_state.md bloat**: 1126 lines, 49KB - read every `/resume-session`
   - Contains 50+ session summaries (sessions 193-242)
   - Each session: 20-50 lines of verbose detail
   - Files Modified lists often 10-20 files each
   - Completed plan tracking for plans finished months ago

2. **defects.md growing**: ~240 lines, will continue growing
   - No archiving mechanism
   - Old defects rarely referenced but always loaded
   - No date prefixes for age tracking

3. **No automatic archiving**: Both files accumulate forever

4. **Redundant storage**: Same info in _state.md AND session-log.md

### Context Cost Per Session
- _state.md: ~49KB read
- defects.md: ~12KB read
- Total: ~61KB minimum context before any work begins

## Solution: 3-Tier Memory System

### Tier 1: HOT Memory (Read Every Session)
| File | Max Size | Contents |
|------|----------|----------|
| `_state.md` | ~300 lines (~15KB) | Last 10 sessions, current phase, active plan |
| `defects.md` | ~200 lines (~8KB) | Last 15 defects, categories |

### Tier 2: COLD Memory (On-Demand Only)
| File | Contents |
|------|----------|
| `state-archive.md` | Sessions older than last 10 |
| `defects-archive.md` | Defects older than last 15 |

### Tier 3: Reference Files (Lazy Load via @reference)
| File | When to Load |
|------|--------------|
| `tech-stack.md` | Technical decisions needed |
| `standards.md` | Coding pattern questions |
| `session-log.md` | Historical investigation |

---

## Phase 1: Extract Learnings from Current State - COMPLETE

Before archiving, scan _state.md for:
- Patterns that should become defects
- Key architectural decisions worth preserving
- Completed plan summaries (compress to 1-liners)

**Output**: List of items to preserve before compression

### Phase 1 Results (Session 243)
**New Defects Added** (5 patterns extracted from session history):
1. Patrol CLI Version Mismatch (Session 236)
2. Deprecated Flutter APIs (Session 238)
3. Seed Version Not Incremented (Sessions 201, 205, 207)
4. flutter_secure_storage v10 Breaking Changes (Session 229)
5. Fixed broken @ reference and TestingKeys path in existing defects

**Key Architectural Decisions** (already documented):
- Feature-first organization with 13 features
- Provider + Repository pattern for state management
- Offline-first with SQLite local, Supabase sync
- Patrol for E2E testing with TestingKeys pattern

**Completed Plans** (already in _state.md):
- Analyzer Cleanup Plan v2 (Phases 1-11)
- Dependency Modernization Plan v2 (Stages 0-10)
- PDF Parsing Fixes v2 (Phases 0-4)
- Clumped Text PDF Parser (Phases 1-6)
- Form Completion Debug v3 (Phases 1-4)

---

## Phase 2: Create Archive Files - COMPLETE (via v2)

### 2.1 Create `state-archive.md`

**Location**: `.claude/memory/state-archive.md`

```markdown
---
name: state-archive
description: Historical session records (on-demand reference only)
lazy_load: true
---

# Session Archive

Historical session records. **Do not read during /resume-session.**
Only reference when investigating past work.

---

## February 2026

### Session 242 (2026-02-01)
Phases 8,10,11 complete. Scripts to scripts/, test_driver removed.
Commits: `1374d5e`, `92fb6c0`

---

## January 2026

### Session 241 (2026-01-31)
Phase 7: Patrol docs alignment
Commit: `6189ae8`

[... continues ...]
```

### 2.2 Create `defects-archive.md`

**Location**: `.claude/memory/defects-archive.md`

```markdown
---
name: defects-archive
description: Archived defect patterns (on-demand reference only)
lazy_load: true
---

# Defects Archive

Archived defect patterns. **Do not read during /resume-session.**
Only reference when investigating recurring issues.

---

## Archived 2026-02-01

### [ASYNC] 2025-12-15: Original Async Context Safety
**Pattern**: Using context after await without mounted check
**Prevention**: Always `if (!mounted) return;` before setState/context after await
**Archived**: No recurrence in 60 days

[... continues ...]
```

---

## Phase 3: Rewrite `_state.md` - COMPLETE

**Target**: ~300 lines maximum

### New Template

```markdown
---
name: session-state
description: Current working context (hot memory)
max_sessions: 10
---

# Session State

**Last Updated**: YYYY-MM-DD | **Session**: N

## Current Phase
- **Phase**: [Name]
- **Status**: [Status]

## Active Plan
- **File**: @.claude/plans/[name].md
- **Progress**: X/Y tasks

## Recent Sessions

### Session N (YYYY-MM-DD)
**Work**: Brief 1-line summary
**Commits**: `abc1234`

### Session N-1 (YYYY-MM-DD)
**Work**: Brief 1-line summary
**Commits**: `def5678`

[Max 10 sessions - oldest auto-rotates to @.claude/memory/state-archive.md]

## Deferred Plans
- OCR Fallback: @.claude/plans/ocr-fallback.md

## Open Questions
None

## Reference
- Archive: @.claude/memory/state-archive.md
- Defects: @.claude/memory/defects.md
```

### Session Format (max 5 lines each)

```markdown
### Session 242 (2026-02-01)
**Work**: Phases 8, 10, 11 - removed test_driver/, moved scripts to scripts/
**Commits**: `1374d5e`, `92fb6c0`
```

---

## Phase 4: Rewrite `defects.md` - COMPLETE

**Target**: ~200 lines maximum (15 active defects)

### New Template

```markdown
---
name: defects
description: Active anti-patterns to avoid (hot memory)
max_defects: 15
archive: .claude/memory/defects-archive.md
---

# Defects Log

Active patterns to avoid. Oldest auto-archives after 15 entries.

## Categories
- **[ASYNC]** - Context safety, dispose issues
- **[E2E]** - Patrol testing patterns
- **[FLUTTER]** - Widget, Provider patterns
- **[DATA]** - Repository, collection access
- **[CONFIG]** - Supabase, credentials, environment

---

## Active Patterns

### [ASYNC] 2026-01-21: Async Context Safety
**Pattern**: Using context after await without mounted check
**Prevention**: Always `if (!mounted) return;` before setState/context after await
**Ref**: @lib/features/entries/presentation/screens/entry_wizard_screen.dart

### [E2E] 2026-01-18: Test Helper Missing scrollTo()
**Pattern**: Calling `$(finder).tap()` on widgets below the fold
**Prevention**: Always `$(finder).scrollTo()` before `$(finder).tap()`

[... max 15 defects ...]

---

<!-- ROTATION: When adding defect 16+, move oldest to @.claude/memory/defects-archive.md -->
```

### Defect Format (max 5 lines each)

```markdown
### [CATEGORY] YYYY-MM-DD: Brief Title
**Pattern**: What to avoid (1 line)
**Prevention**: How to avoid (1-2 lines)
**Ref**: @path/to/file.dart (optional)
```

---

## Phase 5: Update Commands - COMPLETE

### 5.1 Update `end-session.md`

```markdown
---
name: end-session
description: End session with auto-archiving
---

# End Session

## Actions

### 1. Gather Summary
[existing content]

### 2. Run Quality Checks
[existing content]

### 3. Update State Files

**Update `.claude/plans/_state.md`:**
- Write compressed session summary (max 5 lines)
- If >10 sessions exist:
  1. Move oldest session to `.claude/memory/state-archive.md`
  2. Prepend to appropriate month section
  3. Remove from _state.md

**Update `.claude/memory/defects.md`** (if mistakes were made):
- Add new defect with date prefix and category
- If >15 defects exist:
  1. Move oldest defect to `.claude/memory/defects-archive.md`
  2. Prepend to "Archived YYYY-MM-DD" section
  3. Remove from defects.md

### 4. Session Rotation Logic

```
IF session_count > 10:
  oldest = sessions[-1]
  APPEND oldest to state-archive.md under month header
  REMOVE oldest from _state.md

IF defect_count > 15:
  oldest = defects[-1]
  APPEND oldest to defects-archive.md with archive date
  REMOVE oldest from defects.md
```

### 5. Commit Changes
[existing content]
```

### 5.2 Update `resume-session.md`

```markdown
---
name: resume-session
description: Resume session with minimal context load
---

# Resume Session

## Actions

### 1. Read HOT Memory Only
1. `.claude/plans/_state.md` - Current state (max 10 sessions)
2. `.claude/memory/defects.md` - Active patterns (max 15 defects)

**DO NOT READ** (lazy load only when needed):
- `.claude/memory/state-archive.md`
- `.claude/memory/defects-archive.md`
- `.claude/memory/tech-stack.md`
- `.claude/logs/session-log.md`

### 2. Check Git
[existing content]

### 3. Present Context
[existing content]

## On-Demand References
Read these only when relevant to the task:
- Tech details: @.claude/memory/tech-stack.md
- Session history: @.claude/memory/state-archive.md
- Defect history: @.claude/memory/defects-archive.md
- Architecture: @.claude/docs/architectural_patterns.md
```

---

## Phase 6: Update Rule Files - COMPLETE

### 6.1 Update `defect-logging.md`

```markdown
---
name: defect-logging
description: Instructions for logging defects with auto-archiving
---

# Defect Logging Instructions

## When to Log
[existing content]

## Defect Format (Required)
```markdown
### [CATEGORY] YYYY-MM-DD: Brief Title
**Pattern**: What to avoid (1 line)
**Prevention**: How to avoid (1-2 lines)
**Ref**: @path/to/file.dart (optional)
```

## Categories (Required)
| Category | Use For |
|----------|---------|
| [ASYNC] | Context safety, dispose, mounted checks |
| [E2E] | Patrol testing patterns |
| [FLUTTER] | Widget, Provider, state patterns |
| [DATA] | Repository, collection, model patterns |
| [CONFIG] | Supabase, credentials, environment |

## Auto-Archive Rules
- Maximum 15 active defects in `defects.md`
- Defect 16+ triggers rotation of oldest to `defects-archive.md`
- Use `/end-session` to handle rotation automatically

## How to Log
1. Add new defects **at the top** of Active Patterns section
2. Include date prefix: `### [CAT] 2026-02-01: Title`
3. If >15 defects, move oldest to archive before adding new
```

---

## Phase 7: Update Reference Files - COMPLETE

### 7.1 Update `.claude/CLAUDE.md`

Add to Quick Reference:
```markdown
## Quick Reference
@.claude/memory/tech-stack.md
@.claude/memory/standards.md
@.claude/memory/defects.md

## Archives (On-Demand)
@.claude/memory/state-archive.md
@.claude/memory/defects-archive.md
```

Update Session section:
```markdown
## Session
- `/resume-session` - Load HOT context only (~25KB)
- `/end-session` - Save state with auto-archiving
- State: @.claude/plans/_state.md (max 10 sessions)
- Defects: @.claude/memory/defects.md (max 15 defects)
- Archives: @.claude/memory/state-archive.md, @.claude/memory/defects-archive.md
```

### 7.2 Update Agent Files

Add to agent files that may need historical context:

**`.claude/agents/code-review-agent.md`**:
```markdown
## Historical Reference
- Past sessions: @.claude/memory/state-archive.md
- Past defects: @.claude/memory/defects-archive.md
```

**`.claude/agents/planning-agent.md`**:
```markdown
## Historical Reference
- Past implementations: @.claude/memory/state-archive.md
```

**`.claude/agents/qa-testing-agent.md`**:
```markdown
## Historical Reference
- Past test issues: @.claude/memory/defects-archive.md
```

---

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `.claude/plans/_state.md` | REWRITE | Compress to ~300 lines, 10 sessions max |
| `.claude/memory/defects.md` | REWRITE | Add categories, dates, 15 max |
| `.claude/memory/state-archive.md` | CREATE | Historical sessions |
| `.claude/memory/defects-archive.md` | CREATE | Historical defects |
| `.claude/commands/end-session.md` | UPDATE | Add rotation logic |
| `.claude/commands/resume-session.md` | UPDATE | Clarify hot/cold memory |
| `.claude/rules/defect-logging.md` | UPDATE | Categories, format, archive rules |
| `.claude/CLAUDE.md` | UPDATE | Add archive references |
| `.claude/agents/code-review-agent.md` | UPDATE | Add archive reference |
| `.claude/agents/planning-agent.md` | UPDATE | Add archive reference |
| `.claude/agents/qa-testing-agent.md` | UPDATE | Add archive reference |

---

## Verification Checklist

After implementation:
- [ ] `/resume-session` loads <25KB context
- [ ] `_state.md` has max 10 sessions (~300 lines)
- [ ] `defects.md` has max 15 defects (~200 lines)
- [ ] All historical data preserved in archives
- [ ] All defects have [CATEGORY] and date prefix
- [ ] YAML frontmatter valid on all modified files
- [ ] @references used for lazy loading
- [ ] Rotation logic documented in `/end-session`

---

## Implementation Order

1. Phase 1: Extract learnings (review current state)
2. Phase 2: Create archive files (state-archive.md, defects-archive.md)
3. Phase 3: Rewrite _state.md (compress, move old sessions)
4. Phase 4: Rewrite defects.md (add categories, dates, move old defects)
5. Phase 5: Update commands (end-session, resume-session)
6. Phase 6: Update defect-logging.md
7. Phase 7: Update CLAUDE.md and agent files
8. Verification: Test /resume-session context size
