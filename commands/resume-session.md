---
name: resume-session
description: Resume session - load all context files and create session plan
---

# Resume Session Command

Start a new Claude Code session with full context.

## Automatic Actions

### 1. Read All Context Files (IN ORDER)
1. `.claude/plans/_state.md` - Current state
2. `.claude/docs/latest-session.md` - Last session work
3. `.claude/docs/current-plan.md` - Active plan
4. `.claude/rules/project-status.md` - Project phase
5. `.claude/memory/tech-stack.md` - Technology
6. `.claude/memory/standards.md` - Coding standards
7. `.claude/memory/defects.md` - Mistakes to avoid
8. `.claude/implementation/implementation_plan.md` - Latest implementation plan. 

### 2. Check Git Status
```bash
git status
git log --oneline -5
```
s
### 3. Analyze State
From `_state.md`:
- Current phase/subphase
- Open questions
- Recent decisions

From `latest-session.md`:
- What was done last session
- Next priorities identified
- Any blockers

From `current-plan.md`:
- Plan status (READY/IN PROGRESS/COMPLETED)
- Remaining tasks

From `implementation_plan.md`:
- Check for current phase/subphase to ensure no lost context
- Ask any pertinent questions
- Give suggestions

### 4. Present Session Context

**Session Context Loaded**

**Last Session**: [Date]
- Summary: [What was done]
- Files Modified: [List]

**Current State**:
- Phase: [From _state.md]
- Plan Status: [From current-plan.md]

**Active Plan**: [Brief summary or "None"]

**Priorities**:
1. [From project-status.md or latest-session.md]
2. [Priority 2]

**Open Questions**: [From _state.md]

**Recommended Focus**:
- Task: [Suggested task]
- Agent: [Suggested agent and why]

### 5. Wait for User Direction
Ask: "What would you like to focus on this session?"

Do NOT start implementation until user confirms.

## Agent Reference
| Domain | Agent |
|--------|-------|
| UI/Screens | `flutter-specialist-agent` |
| Data/Models | `data-layer-agent` |
| Cloud/Sync | `supabase-agent` |
| Auth | `auth-agent` |
| Testing | `testing-agent` |
| PDF | `pdf-agent` |
