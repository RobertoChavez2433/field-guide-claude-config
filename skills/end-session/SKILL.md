---
name: end-session
description: End session with auto-archiving
user-invocable: true
disable-model-invocation: true
---

# End Session

Complete session with proper handoff and auto-archiving.

## Actions

### 1. Gather Summary
Write Summary:
- Main focus of session
- Completed tasks
- Decisions made
- Next priorities
- Mistakes made (for defects log)

### 2. Run Quality Checks
```bash
flutter analyze lib/ --no-fatal-infos
```

**Check both repos:**
```bash
# App repo
git status
git diff --stat

# Claude config repo
cd .claude && git status && git diff --stat && cd ..
```

### 3. Update State Files

**Update `.claude/autoload/_state.md`:**
- Write compressed session summary (max 5 lines):
```markdown
### Session N (YYYY-MM-DD)
**Work**: Brief 1-line summary
**Commits**: app `abc1234`, config `def5678`
```
- If >10 sessions exist, run rotation (see below)

**Update `.claude/autoload/_defects.md`** (if mistakes were made):
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
2. Append to `.claude/logs/state-archive.md` under appropriate month header
3. Remove from _state.md

**When _defects.md has >15 defects:**
1. Take oldest defect (from bottom of Active Patterns)
2. Append to `.claude/logs/defects-archive.md` with archive date
3. Remove from _defects.md

### 5. Append to Session Log
Append brief entry to `.claude/logs/session-log.md`:
```markdown
### YYYY-MM-DD (Session N)
- [Summary of main work]
```

### 6. Commit Changes (Both Repos)

**App Repository** (main project):
```bash
git add -A
git commit -m "Session: [summary]"
```

**Claude Config Repository** (`.claude` folder):
```bash
cd .claude
git add -A
git commit -m "Session: [summary]"
cd ..
```

**IMPORTANT**: Do NOT include "Co-Authored-By" in commit messages.

### 7. Complete
Present:
- Session summary
- App repo commit hash
- Claude config repo commit hash
- Next session: Run `/resume-session`

---

## Defect Logging Instructions

When you discover bugs, anti-patterns, or issues during testing or review, log them to `.claude/autoload/_defects.md`.

### When to Log
- Test failures caused by known anti-patterns
- Async context issues (missing `mounted` check)
- Dispose errors (async in dispose)
- Recurring anti-patterns found during review
- Architecture violations
- Security vulnerabilities
- Performance issues that caused problems

### Defect Format (Required)
```markdown
### [CATEGORY] YYYY-MM-DD: Brief Title
**Pattern**: What to avoid (1 line)
**Prevention**: How to avoid (1-2 lines)
**Ref**: @path/to/file.dart (optional)
```

### Categories (Required)
| Category | Use For |
|----------|---------|
| [ASYNC] | Context safety, dispose, mounted checks |
| [E2E] | Patrol testing patterns |
| [FLUTTER] | Widget, Provider, state patterns |
| [DATA] | Repository, collection, model patterns |
| [CONFIG] | Supabase, credentials, environment |

### How to Log
1. Add new defects **at the top** of Active Patterns section
2. Include category and date: `### [CAT] 2026-02-01: Title`
3. If >15 defects, move oldest to archive before adding new

### Archives
- Active: `.claude/autoload/_defects.md`
- Archive: `.claude/logs/defects-archive.md`
