---
name: end-session
description: End session with auto-archiving
user-invocable: true
disable-model-invocation: true
---

# End Session

Complete session with proper handoff and auto-archiving.

**CRITICAL**: NO git commands anywhere in this skill. All analysis comes from conversation context.

## Actions

### 1. Gather Summary (From Conversation Context)
Review the current conversation and collect:
- Main focus of session
- Completed tasks
- Decisions made
- Next priorities
- Defects discovered (mistakes, anti-patterns, bugs found)

Do NOT run git commands. Use only what you observed during the session.

### 2. Update _state.md
**File**: `.claude/autoload/_state.md`

Write compressed session summary (max 5 lines):
```markdown
### Session N (YYYY-MM-DD)
**Work**: Brief 1-line summary
**Decisions**: Key decisions made
**Next**: Top 1-3 priorities
```

If >5 sessions exist, run rotation:
1. Take oldest session
2. Append to `.claude/logs/state-archive.md` under appropriate month header
3. Remove from _state.md

### 3. File Defects to GitHub Issues

For each feature where defects were discovered during this session, create a GitHub Issue:

```bash
pwsh -File tools/create-defect-issue.ps1 `
    -Title "[CATEGORY] YYYY-MM-DD: Brief Title" `
    -Feature "{feature}" `
    -Type "defect" `
    -Priority "{critical|high|medium|low|parked}" `
    -Layer @("{layer:...}") `
    -Body "**Pattern**: What to avoid (1 line)`n**Prevention**: How to avoid (1-2 lines)" `
    -Ref "@path/to/file.dart"
```

### Categories
| Category | Use For |
|----------|---------|
| [ASYNC] | Context safety, dispose, mounted checks |
| [E2E] | Patrol testing patterns |
| [FLUTTER] | Widget, Provider, state patterns |
| [DATA] | Repository, collection, model patterns |
| [CONFIG] | Supabase, credentials, environment |

### 4. Update JSON State Files

**PROJECT-STATE.json** (`state/PROJECT-STATE.json`):
- Update `session_notes` with brief session summary
- Update `active_blockers` if blockers were resolved or discovered
- If a blocker was resolved: `gh issue close <number> --comment "Resolved in session N"` and update `_state.md` status
- If a new blocker was discovered: create via `create-defect-issue.ps1` with `-Type blocker`, add `(#NN)` to `_state.md`
- Update `release_cycle` dates if milestones were hit
- Do NOT duplicate session narrative here (that belongs in _state.md)

**feature-{name}.json** (`state/feature-{name}.json`) — only for features touched this session:
- Update `status` if feature status changed (e.g., stable -> in_progress)
- Update `metrics.last_updated` timestamp
- Update `constraints_summary` if constraints were added/changed
- Update `current_phase` if feature has active development phase

### 5. Display Summary
Present:
- Session summary (what was accomplished)
- Features touched
- Defects filed to GitHub Issues (if any, with issue URLs)
- Next priorities
- Reminder: Run `/resume-session` to start next session

---

## Rules
- **NO git commands** - not `git status`, not `git diff`, not `git add`, not `git commit`
- All analysis from conversation context only
- Zero user input required
- Files defects to GitHub Issues via `tools/create-defect-issue.ps1`
- Defect tracking uses GitHub Issues with feature/type/priority/layer labels
