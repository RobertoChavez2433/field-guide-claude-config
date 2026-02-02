# Session Workflow Checklist

Single reference for starting and ending sessions.

---

## Starting a Session

### 1. Load Context
Read these files (in order):
1. `.claude/autoload/_state.md` - Current state
2. `.claude/autoload/_defects.md` - Active patterns
3. `.claude/autoload/_tech-stack.md` - Tech reference

### 2. Check Git Status
```bash
git status && git log --oneline -3
```

### 3. Review Defects
Before starting work, scan defects for patterns matching your task:
- PDF work? Watch for async context issues
- E2E tests? Remember scrollTo() before tap()
- Forms? Check auto-fill patterns

### 4. Confirm Focus
Ask user: "What would you like to focus on this session?"

---

## Ending a Session

### 1. Quality Checks
```bash
pwsh -Command "flutter analyze"
git status
git diff --stat
```

### 2. Update State
Add to `_state.md`:
```markdown
### Session N (YYYY-MM-DD)
**Work**: [1-2 sentence summary]
**Commits**: `abc1234` or "Pending"
**Ref**: @path/to/relevant/file
```

### 3. Log New Defects
If patterns discovered, add to `_defects.md`:
```markdown
### [CATEGORY] YYYY-MM-DD: Title
**Pattern**: What to avoid
**Prevention**: How to prevent
**Ref**: @path/to/file.dart
```

### 4. Check Rotation
- `_state.md` has >10 sessions? Move oldest to `state-archive.md`
- `_defects.md` has >15 entries? Move oldest to `defects-archive.md`
- Update `archive-index.md` with new locations

### 5. Commit
```bash
git add -A && git commit -m "session N: summary"
```
