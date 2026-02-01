---
name: end-session
description: End session with auto-archiving
---

# End Session

Complete session with proper handoff and auto-archiving.

## Actions

### 1. Gather Summary
Ask user for:
- Main focus of session
- Completed tasks
- Decisions made
- Next priorities
- Mistakes made (for defects log)

### 2. Run Quality Checks
```bash
flutter analyze lib/ --no-fatal-infos
git status
git diff --stat
```

### 3. Update State Files

**Update `.claude/plans/_state.md`:**
- Write compressed session summary (max 5 lines):
```markdown
### Session N (YYYY-MM-DD)
**Work**: Brief 1-line summary
**Commits**: `abc1234`
```
- If >10 sessions exist, run rotation (see below)

**Update `.claude/memory/defects.md`** (if mistakes were made):
- Add new defect with category and date:
```markdown
### [CATEGORY] YYYY-MM-DD: Title
**Pattern**: What to avoid
**Prevention**: How to avoid
```
- If >15 defects exist, run rotation (see below)

### 4. Session Rotation Logic

**When _state.md has >10 sessions:**
1. Take oldest session
2. Append to `.claude/memory/state-archive.md` under appropriate month header
3. Remove from _state.md

**When defects.md has >15 defects:**
1. Take oldest defect (from bottom of Active Patterns)
2. Append to `.claude/memory/defects-archive.md` with archive date
3. Remove from defects.md

### 5. Append to Session Log
Append brief entry to `.claude/logs/session-log.md`:
```markdown
### YYYY-MM-DD (Session N)
- [Summary of main work]
```

### 6. Commit Changes
```bash
git add -A
git commit -m "Session: [summary]"
```

**IMPORTANT**: Do NOT include "Co-Authored-By" in commit messages.

### 7. Complete
Present:
- Session summary
- Commit hash
- Next session: Run `/resume-session`
