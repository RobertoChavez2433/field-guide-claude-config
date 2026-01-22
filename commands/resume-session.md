---
name: resume-session
description: Resume session - load all context files and create session plan
---

# Resume Session

Load context and prepare for work.

## Actions

### 1. Read Context Files
1. `.claude/plans/_state.md` - Session state, plan, priorities
2. `.claude/memory/defects.md` - Critical patterns to avoid

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
- Tech details: `.claude/memory/tech-stack.md`
- Architecture: `.claude/docs/architectural_patterns.md`
- AASHTOWare plan: `.claude/implementation/AASHTOWARE_Implementation_Plan.md`
- Defect archive: `.claude/memory/defects-archive.md`

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
