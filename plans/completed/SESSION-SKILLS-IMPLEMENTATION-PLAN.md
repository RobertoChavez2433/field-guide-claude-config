# Session Skills Implementation Plan
**Status**: Ready to Execute
**Last Updated**: 2026-02-13
**Scope**: Design and implement `/resume-session` and `/end-session` skills
**Estimated Timeline**: 2 hours
**Context Required**: This document is self-contained; no need to re-read prior conversation

---

## Executive Summary

Implement two session management skills that integrate with Phase 1 documentation system:

1. **`/resume-session`** — Ask user intent, load only necessary context
2. **`/end-session`** — Update state files, mark completed plans, reorganize defects by feature

Key design principle: **User tells intent → I load selectively (not everything)**

---

## Phase 1 Context (Locked In)

- ✓ 26 feature docs created (13 overviews + 13 architectures)
- ✓ 13 constraint files created (all 13 features)
- ✓ FILING-SYSTEM.md updated with prds/ section
- ✓ FEATURE-MATRIX.json updated with all 13 features
- ✓ .claude/prds/ directory created + PDF PRD moved

Next phase: Phase 2 (agent frontmatter updates, lightweight PRDs)

---

## Skill 1: `/resume-session` (Ask-First Approach)

### Purpose
Load only the context needed for today's work. Prevent wasting tokens on irrelevant docs.

### Design Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User executes: /resume-session                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ ASK: "What are we working on today?"                        │
│                                                             │
│ Options:                                                    │
│  a) Implementation (pick feature)                           │
│  b) Planning (pick feature/topic)                           │
│  c) Review/debugging code                                   │
│  d) Just browsing / understanding                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
         ┌──────────────────┼──────────────────┐
         ↓                  ↓                  ↓                  ↓
    Implementation      Planning            Review           Browsing
         │                  │                  │                  │
         ├─→ "Which feature?"       │                  │
         │   (pdf/sync/auth/       ├─→ "Which feature?"   ├─→ Show status
         │    entries/photos/      │                  │    only
         │    contractors/...)"     ├─→ Ask for current   │
         │                         │    blocker context  │
         ├─→ "Which task?"         │                      │
         │   (offer from          ├─→ Don't load PRDs    │
         │    TASK-LIST.json)     │    (waste of tokens) │
         │                         │                      │
         └─→ LOAD CONTEXT:        └─→ LOAD CONTEXT:     └─→ LOAD CONTEXT:
             - Feature docs             - Constraint file    - PROJECT-STATE.json
             - Constraints              - Overview doc       - High-level summary
             - Rules (if exists)        - Architecture doc
             - Feature state            - Feature state
             - Shared rules             - Shared rules

             Show status before
             returning control
```

### What `/resume-session` Loads

**IMPLEMENTATION Path:**
```
Always load:
  ✓ rules/architecture.md (shared)
  ✓ architecture-decisions/data-validation-rules.md (shared)
  ✓ IMPLEMENTATION-PLAN-PHASE-1-FINAL.md (current phase plan)
  ✓ PROJECT-STATE.json (status/blockers)

Feature-specific (based on user's feature choice):
  ✓ docs/feature-{name}-overview.md
  ✓ docs/feature-{name}-architecture.md
  ✓ architecture-decisions/{name}-constraints.md
  ✓ state/feature-{name}.json
  ✓ rules/{domain}/{name}.md (if exists)

Conditional (based on task):
  - prds/{name}-prd-*.md (only if requires_deep_spec: true in task)
  - docs/feature-{other}-* (only if integration_with set)
  - state/PROJECT-STATE.json (already loaded)

DO NOT load:
  ✗ Other features' docs
  ✗ FEATURE-MATRIX.json (agent doesn't need it)
  ✗ All state files at once
```

**PLANNING Path:**
```
Always load:
  ✓ rules/architecture.md (shared)
  ✓ CONTEXT-VISION.md (to understand why features exist)
  ✓ PROJECT-STATE.json (to understand phase/blockers)

Feature-specific (based on user's feature choice):
  ✓ docs/feature-{name}-overview.md
  ✓ docs/feature-{name}-architecture.md
  ✓ architecture-decisions/{name}-constraints.md

DO NOT load:
  ✗ implementation PRDs (waste for planning)
  ✗ implementation plans (not relevant yet)
  ✗ test-related files
```

**REVIEW/DEBUG Path:**
```
Always load:
  ✓ rules/architecture.md
  ✓ architecture-decisions/data-validation-rules.md
  ✓ PROJECT-STATE.json

Ask: "Which feature is having issues?"
  → Load that feature's full context (docs + constraints + state)
  → Load related feature docs if needed (integration points)
```

**BROWSING Path:**
```
Load only:
  ✓ PROJECT-STATE.json summary
  ✓ FEATURE-MATRIX.json (to see all features)

Show:
  - Current phase (Phase 1 complete, Phase 2 next)
  - Active blockers
  - Next 3 priorities
  - List of all 13 features + status
```

### Status Display (Shown Before Returning)

```
════════════════════════════════════════════════════════════
                  SESSION STATUS
════════════════════════════════════════════════════════════

📊 CURRENT PHASE: Phase 1 Complete, Phase 2 Next
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Phase 1: Feature documentation system (39 files created)
  - 26 feature docs (overview + architecture for all 13)
  - 13 constraint files (all features documented)
  - FILING-SYSTEM.md updated with prds/ + lazy-loading rules
  - FEATURE-MATRIX.json updated (all 13 features linked)

⧗ Phase 2 (NEXT): Agent frontmatter updates
  - Update 8 agent files with feature-specific context
  - Create 12 lightweight PRDs (200-400 words each)
  - Lock in lazy-loading compliance

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 ACTIVE BLOCKERS (from PROJECT-STATE.json)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCK-001: OCR rendering timeout (Flutter platform binding)
  - Impact: PDF extraction tests fail intermittently
  - Status: In investigation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 NEXT 3 PRIORITIES (from PROJECT-STATE.json)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Complete Phase 1 documentation (DONE)
2. Phase 2: Agent frontmatter updates
3. Phase 2: Create lightweight PRDs for stable features

════════════════════════════════════════════════════════════
```

---

## Skill 2: `/end-session` (Automatic State Management)

### Purpose
Automatically capture work completed, update state files, and reorganize defects. Zero user input.

### Design Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User executes: /end-session                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ ANALYZE CONTEXT (automatic)                                │
├─────────────────────────────────────────────────────────────┤
│ • Read git diff → identify changed features & files        │
│ • Load current state files                                 │
│ • Check TASK-LIST.json for current task                   │
│ • Determine what work was done                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ UPDATE STATE FILES (all automatically)                      │
├─────────────────────────────────────────────────────────────┤
│ 1. PROJECT-STATE.json                                      │
│    - Mark completed tasks                                  │
│    - Shift priorities                                      │
│    - Add session_notes entry with timestamp                │
│                                                             │
│ 2. TASK-LIST.json                                          │
│    - Mark current task "completed"                         │
│    - Move to next task (status: "pending")                 │
│                                                             │
│ 3. feature-{name}.json (for each touched feature)          │
│    - Update last_updated timestamp                         │
│    - Update metrics if docs/tests done                     │
│    - Mark affected docs/constraints as modified            │
│                                                             │
│ 4. Reorganize defects                                      │
│    - Archive resolved defects (if any)                     │
│    - Keep only active ones per feature                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ DISPLAY SESSION SUMMARY                                     │
├─────────────────────────────────────────────────────────────┤
│ ✓ Marked complete:                                          │
│   - [Task from TASK-LIST.json]                            │
│ ✓ Updated features: [feature list from git diff]           │
│ ✓ State files saved                                        │
│ ✓ Defects reorganized                                      │
│                                                             │
│ Next task: [Next pending task from TASK-LIST.json]         │
└─────────────────────────────────────────────────────────────┘
```

**Design Principle**: Git operations handled by separate `/commit` skill. End-session focuses purely on state management.

### Files Updated by `/end-session`

1. **PROJECT-STATE.json**
   ```json
   {
     "current_phase": "Phase 2",
     "phase_progress": "15%",
     "active_blockers": [...],
     "next_priorities": [...],
     "session_notes": [
       {
         "timestamp": "2026-02-13T14:30:00Z",
         "task_completed": "T1.1: Create feature docs + constraints",
         "features_touched": ["pdf", "sync", "auth"],
         "files_modified": 39
       }
     ]
   }
   ```

2. **TASK-LIST.json**
   ```json
   {
     "current_phase_tasks": [
       {
         "id": "T1.1",
         "title": "Create feature docs + constraints",
         "status": "completed",
         "completed_date": "2026-02-13"
       },
       {
         "id": "T2.1",
         "title": "Update agent frontmatter",
         "status": "pending",
         "created_date": "2026-02-13"
       }
     ]
   }
   ```

3. **feature-{name}.json** (auto-updated for touched features)
   ```json
   {
     "name": "pdf",
     "last_updated": "2026-02-13T14:30:00Z",
     "docs": {
       "overview": { "status": "completed" },
       "architecture": { "status": "completed" }
     }
   }
   ```

4. **Defects Reorganized** (auto-archived if resolved)
   ```
   .claude/autoload/
   ├── _defects-pdf.md (active defects only)
   ├── _defects-sync.md
   ├── _defects-auth.md
   └── ... (one per feature, max 5 each)

   .claude/logs/
   ├── _defects-pdf-archive.md (resolved)
   └── ... (feature archives)
   ```

---

## Implementation Steps

### Step 1: Create `/resume-session` Skill
**Location**: `.claude/skills/resume-session/`
**Files**:
- `resume-session.md` (main skill definition)
- `references/status-template.md` (status display format)

**Checklist**:
- [ ] Ask user for intent (implementation/planning/review/browsing)
- [ ] Based on intent, ask for feature (if applicable)
- [ ] Load IMPLEMENTATION-PLAN-PHASE-1-FINAL.md (current phase)
- [ ] Load PROJECT-STATE.json (status)
- [ ] Load feature-specific docs (based on choice)
- [ ] Display status before returning
- [ ] Don't load PRDs for planning (waste of tokens)

**Effort**: ~1 hour

---

### Step 2: Create `/end-session` Skill
**Location**: `.claude/skills/end-session/`
**Files**:
- `end-session.md` (main skill definition)

**Checklist**:
- [ ] Analyze git diff to find changed files/features
- [ ] Load current state files (PROJECT-STATE.json, TASK-LIST.json)
- [ ] Auto-detect current task from TASK-LIST.json
- [ ] Update PROJECT-STATE.json (session_notes + priorities)
- [ ] Update TASK-LIST.json (mark task complete, move to next)
- [ ] Update feature-{name}.json (timestamps for touched features)
- [ ] Archive resolved defects, keep active ones only
- [ ] Display summary (what was updated)

**Effort**: ~1 hour

---

## Files to Create

| Path | Purpose | Type |
|------|---------|------|
| `.claude/skills/resume-session/resume-session.md` | Main skill | Skill definition |
| `.claude/skills/resume-session/references/status-template.md` | Status display format | Reference |
| `.claude/skills/end-session/end-session.md` | Main skill | Skill definition |
| `.claude/skills/end-session/references/state-update-template.md` | State file update format | Reference |
| `.claude/autoload/_defects-pdf.md` | PDF defects | State file |
| `.claude/autoload/_defects-sync.md` | Sync defects | State file |
| `.claude/autoload/_defects-auth.md` | Auth defects | State file |
| ... (10 more for remaining features) | ... | ... |

**Total**: 16 new files + reorganization of existing defects

---

## Success Criteria

When complete, you should have:

- ✓ `/resume-session` skill that asks user intent, loads only necessary context
- ✓ `/end-session` skill that automatically updates all state files with zero user input
- ✓ Git operations moved to dedicated `/commit` skill (planned separately)
- ✓ PROJECT-STATE.json tracks session_notes with completed tasks
- ✓ TASK-LIST.json auto-marks completed tasks and advances to next
- ✓ feature-{name}.json files auto-updated with timestamps
- ✓ Defects auto-archived when resolved
- ✓ Ready for Phase 2 (agent frontmatter updates)

---

## Decision Log (Locked In)

✓ `/resume-session` asks user intent first (don't assume context)
✓ `/end-session` updates state files (not create new plan files)
✓ Defects organized by feature (less clutter, more relevance)
✓ Don't load PRDs for planning (token waste)
✓ Don't save token metrics in session summary (too speculative)
✓ Completed plans tracked in PROJECT-STATE.json["completed_plans"]

---

## When Resuming This Work

1. **Read this file** (you're reading it now)
2. **Current task**: Implement `/resume-session` skill
3. **Reference files**:
   - IMPLEMENTATION-PLAN-PHASE-1-FINAL.md (completed work)
   - PROJECT-STATE.json (current state)
   - CLAUDE.md lines 72-77 (session skills context)
4. **No need to re-read**: The 20+ messages above — it's all captured here

---

## Implementation Status

### ✅ Complete

- [x] Updated plan with zero-questioning `/end-session` flow
- [x] Created `.claude/skills/resume-session/resume-session.md` (full specification)
- [x] Created `.claude/skills/end-session/end-session.md` (full specification)

### Remaining

The skill definitions above are complete and ready for use. They document:

1. **`/resume-session`**: Ask user intent → load selective context → show status
2. **`/end-session`**: Auto-detect work from git → update state files → show summary

To make these fully functional, the system will:
- Call `/resume-session` → user answers intent question → context loads
- Call `/end-session` → runs automatic state updates → displays summary

**Next**: These skills are ready to test. Git handling (`/commit` skill) planned separately per user request.
