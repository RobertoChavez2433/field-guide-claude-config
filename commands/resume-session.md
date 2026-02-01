---
name: resume-session
description: Resume session with minimal context load
---

# Resume Session

Load HOT context only and prepare for work.

## Actions

### 1. Read HOT Memory Only
1. `.claude/plans/_state.md` - Current state (max 10 sessions)
2. `.claude/memory/defects.md` - Active patterns (max 15 defects)
3. `.claude/memory/tech-stack.md` - Current tech stack
4. `.claude/docs/architectural_patterns.md` - Architectural patterns

**DO NOT READ** (lazy load only when needed):
- `.claude/memory/state-archive.md`
- `.claude/memory/defects-archive.md`
- `.claude/logs/session-log.md`

### 2. Check Git
```bash
git status && git log --oneline -3
```

### 3. Present Context

**Session Context Loaded**

**Phase**: [From _state.md]
**Status**: [From _state.md]

**Last Session**: [Summary from _state.md]

**Next Tasks**:
1. [From _state.md]
2. [...]

**Open Questions**: [From _state.md or "None"]

### 4. Ask
"What would you like to focus on this session?"

Do NOT start implementation until user confirms.

## On-Demand References
Read these only when relevant to the task:
- Session history: @.claude/memory/state-archive.md
- Defect history: @.claude/memory/defects-archive.md

## Agent Reference
| Domain | Agent |
|--------|-------|
| UI/Screens | `flutter-specialist-agent` |
| Data/Models | `data-layer-agent` |
| Cloud/Sync | `supabase-agent` |
| Auth | `auth-agent` |
| QA/Testing | `qa-testing-agent` |
| Code Review | `code-review-agent` |
| PDF | `pdf-agent` |
