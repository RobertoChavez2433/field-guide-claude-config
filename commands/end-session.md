---
name: end-session
description: End session workflow - save state, update notes, analyze code, commit changes
---

# End Session

Complete session with proper handoff.

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
```markdown
# Session State

**Last Updated**: [TODAY] | **Session**: [N+1]

## Current Phase
- **Phase**: [Current phase]
- **Status**: [Status]

## Last Session (Session N)
**Summary**: [Brief summary]
**Files Modified**:
- file.dart - change description

## Active Plan
**Status**: [READY | IN PROGRESS | COMPLETED]

**Completed**:
- [x] Task done

**Next Tasks**:
- [ ] Task to do

## Key Decisions
- [Decision made]

## Future Work
| Item | Status | Reference |
|------|--------|-----------|

## Open Questions
[Questions or "None"]
```

**Update `.claude/memory/defects.md`** (if mistakes were made):
```markdown
### Title
**Pattern**: What to avoid
**Prevention**: How to avoid
```

**Append to `.claude/logs/session-log.md`** (historical record):
```markdown
### YYYY-MM-DD (Session N)
- [Summary of main work]
- [Key files modified]
```

### 4. Commit Changes
```bash
git add -A
git commit -m "Session: [summary]"
```

**IMPORTANT**: Do NOT include "Co-Authored-By" in commit messages.

### 5. Optional Push
Ask user if they want to push to remote.

### 6. Complete
Present:
- Session summary
- Commit hash
- Next session: Run `/resume-session`
