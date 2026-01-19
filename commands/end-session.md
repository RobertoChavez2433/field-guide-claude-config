---
name: end-session
description: End session workflow - save state, update notes, analyze code, commit changes
---

# End Session Command

Complete the current Claude Code session with proper handoff.

## Automatic Actions

### 1. Read Session Context
- `.claude/plans/_state.md` - Update session state
- `.claude/docs/current-plan.md` - Update plan status
- `.claude/docs/latest-session.md` - Update session notes
- `.claude/memory/defects.md` - Update defects

### 2. Gather Session Summary
Ask user for:
- Main focus of session
- Completed tasks
- Blockers/issues
- Decisions made
- Next priorities
- Analyze mistakes made

### 3. Run Quality Checks
```bash
flutter analyze lib/ --no-fatal-infos
git status
git diff --stat
```

### 4. Update State Files

**Update `.claude/plans/_state.md`:**
```markdown
# Session State
## Current Phase
**Phase**: [Current phase]
**Subphase**: [Current subphase]
**Last Updated**: [TODAY]

## Last Session Work
- [Summary of work done]

## Decisions Made
- [Key decisions]

## Open Questions
- [Unresolved items]
```

**Update `.claude/docs/latest-session.md`:**
```markdown
# Last Session: [DATE]

## Summary
[Session summary]

## Completed
- [Tasks completed]

## Files Modified
| File | Change |
|------|--------|
| path | description |

## Plan Status
- Status: [READY | IN PROGRESS | COMPLETED]
- Completed: [phases/tasks done]
- Remaining: [phases/tasks left]

## Next Priorities
1. [Priority 1]
2. [Priority 2]

## Decisions
- [Decision]: [Reasoning]

## Blockers
- [Any blockers or "None"]
```

**Update `.claude/memory/defects.md`** (if mistakes were made):
```markdown
### YYYY-MM-DD: [Brief Title]
**Issue**: [What went wrong]
**Root Cause**: [Why it went wrong]
**Prevention**: [How to avoid in future]
```

### 5. Commit Changes
```bash
git add -A
git commit -m "Session: [summary]"
```

**IMPORTANT**: Do NOT include "Co-Authored-By" in commit messages. The user is the sole author.

### 6. Optional Push
Ask user if they want to push to remote.

### 7. Session Complete Summary
Present:
- Session summary
- Commit hash
- Push status
- Next session: Run `/resume-session`
