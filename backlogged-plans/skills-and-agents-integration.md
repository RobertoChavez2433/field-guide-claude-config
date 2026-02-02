# Skills & Agents Integration Plan

**Date**: 2026-02-02
**Status**: READY FOR IMPLEMENTATION

---

## Executive Summary

Investigation into why skills (TDD, debugging, etc.) aren't being invoked by agents when spawned via the Task tool. Found multiple issues and solutions.

---

## Critical Findings

### Finding #1: Nested Agents Not Discovered

**Problem**: Agents in subdirectories (e.g., `.claude/agents/backend/`) are NOT discovered by Claude Code.

**Proof**: Running `/agents` shows only root-level agents.

**Fix**: Move all agents to `.claude/agents/` root with naming prefixes.

### Finding #2: Task Tool Doesn't Load Custom Agent Definitions

**Problem**: When spawning `Task` with `subagent_type=pdf-agent`, Claude Code does NOT:
- Load `.claude/agents/pdf-agent.md`
- Inject skills from the `skills:` frontmatter field
- Use the agent's system prompt

**Proof**: Agent transcript shows only my raw task prompt, no skill content.

**Root Cause**: The `subagent_type` parameter only recognizes built-in agents (Explore, Plan, general-purpose). Custom agent names are treated as labels, not file references.

### Finding #3: How Skills ARE Supposed to Work

Per official docs, skills load into agents via:
1. **`skills:` frontmatter field** - Lists skill names that get injected at startup
2. **Full content injection** - "The full content of each skill is injected into the subagent's context"
3. **No inheritance** - "Subagents don't inherit skills from the parent conversation"

---

## How to Get Agents to Invoke Skills

### Method 1: Let Claude Auto-Delegate (Recommended)

Instead of forcing `subagent_type`, describe the task and let Claude decide:

```
Instead of:
  Task(subagent_type=pdf-agent, prompt="Fix PDF rendering")

Do this:
  "Please have the PDF specialist fix the PDF rendering issue"
```

Claude reads agent descriptions and automatically delegates to matching agents. When it does, the agent's `skills:` field is respected.

**Requirements**:
- Agent must be at root `.claude/agents/` level
- Agent description must be clear about when to use it
- Agent must be discovered (verify with `/agents`)

### Method 2: Explicit Skill Invocation in Main Conversation

Before delegating, invoke skills directly:

```
/test-driven-development
Now please implement the PDF rendering fix.
```

The skill content enters YOUR context, then you can delegate normally.

**Limitation**: Skills stay in main conversation, not injected into subagent.

### Method 3: Include Skill Content in Task Prompts

When using Task tool, explicitly include skill instructions:

```python
Task(
  subagent_type="pdf-agent",
  prompt="""
## Required Methodology
Follow TDD: Write failing test → Implement → Refactor

## Task
Fix the PDF rendering issue...
"""
)
```

**Pros**: Works immediately
**Cons**: Verbose, must remember to include

### Method 4: Session-Level Agent Override

Start Claude Code with a specific agent:

```bash
claude --agent pdf-agent
```

The entire session uses `pdf-agent.md` as the agent, including its skills.

**Limitation**: Only one agent per session, not suitable for multi-domain tasks.

### Method 5: Embed Core Skills in CLAUDE.md

Add essential skill content to project CLAUDE.md:

```markdown
## Development Standards

### TDD Workflow (All Code Changes)
1. Write failing test first (RED)
2. Implement minimal code to pass (GREEN)
3. Refactor while tests stay green

### Debugging Workflow
1. Investigate - gather evidence
2. Analyze - identify patterns
3. Hypothesize - form theory
4. Implement - test fix
```

**Pros**: Always available to all agents
**Cons**: Increases context size

---

## Recommended Approach: Hybrid

1. **Move agents to root** - Ensures discovery
2. **Embed core TDD/debugging in CLAUDE.md** - Universal baseline
3. **Let Claude auto-delegate** - Natural skill loading
4. **Add skill reminders in complex Task prompts** - Reinforcement

---

## Action Items

### 1. Move Agents to Root Directory

| Current Location | New Name |
|-----------------|----------|
| `auth/auth-agent.md` | `auth-agent.md` |
| `backend/data-layer-agent.md` | `backend-data-layer-agent.md` |
| `backend/supabase-agent.md` | `backend-supabase-agent.md` |
| `frontend/flutter-specialist-agent.md` | `frontend-flutter-specialist-agent.md` |

Delete empty subdirectories after move.

### 2. Update CLAUDE.md Agent Table

Update agent names to match new prefixed names.

### 3. Add Development Standards to CLAUDE.md

Add a "Development Standards" section with core TDD and debugging principles.

### 4. Verify After Restart

1. Restart Claude Code session
2. Run `/agents` to verify all 8 agents appear
3. Test auto-delegation by asking Claude to "use the PDF agent"
4. Check agent transcript for skill content

---

## Agent-Skill Mapping (Reference)

| Agent | Skills |
|-------|--------|
| `planning-agent` | `brainstorming` |
| `pdf-agent` | `test-driven-development`, `pdf-processing` |
| `qa-testing-agent` | `systematic-debugging`, `test-driven-development`, `verification-before-completion` |
| `code-review-agent` | `verification-before-completion` |
| `frontend-flutter-specialist-agent` | (check file) |
| `backend-data-layer-agent` | (check file) |
| `backend-supabase-agent` | (check file) |
| `auth-agent` | (check file) |

---

## Sources

- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents)
- [GitHub Issue #773 - Nested Directories Not Supported](https://github.com/bmad-code-org/BMAD-METHOD/issues/773)
