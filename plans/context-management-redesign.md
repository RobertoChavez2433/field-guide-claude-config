# Context Management System Redesign

## Goal
Restructure `.claude/` directory for optimal context loading with task-aware "expert" rules.

---

## User Requirements Summary

### Always Loaded
- Project CLAUDE.md
- autoload/_state.md
- autoload/_defects.md
- autoload/_tech-stack.md

### On-Demand (Task-Aware)
- Rules with `paths:` frontmatter load when touching matching files
- Docs load only when explicitly referenced

### Workflow Phases (Separate Sessions)
1. **PLAN**: planning-agent + domain expert
2. **CRITIQUE**: User reviews manually with Codex (no Claude review needed)
3. **IMPLEMENT**: Domain agents based on files being modified
4. **REVIEW**: code-review-agent reviews all changes
5. **TEST/VERIFY**: qa-testing-agent + domain expert for domain-specific tests

### Planning Agent Behavior
- Ask many questions during planning
- Provide 3+ options with reasoning/logic for user to choose
- Explain constraints and drawbacks of each approach
- Break plans into PR-sized phases, with subphases and steps

### Agent Selection
- Inferred from file paths during implementation
- Not explicitly stated in plan documents

---

## Proposed New Structure

```
.claude/
├── CLAUDE.md                    # Minimal overview + structure reference
│
├── autoload/                    # Always loaded (no paths: frontmatter)
│   ├── _state.md               # Session state
│   ├── _defects.md             # Active defects (max 15)
│   └── _tech-stack.md          # Core versions/commands
│
├── rules/                       # Task-aware expert rules (with paths:)
│   ├── architecture.md         # Core patterns
│   ├── platform-standards.md   # SDK versions
│   ├── frontend/
│   │   └── flutter-ui.md       # paths: lib/**/presentation/**
│   ├── backend/
│   │   ├── data-layer.md       # paths: lib/**/data/**
│   │   └── supabase-sql.md     # paths: (Supabase work)
│   ├── auth/
│   │   └── supabase-auth.md    # paths: lib/features/auth/**
│   ├── pdf/
│   │   └── pdf-generation.md   # paths: lib/features/pdf/**
│   ├── sync/
│   │   └── sync-patterns.md    # paths: lib/features/sync/**
│   ├── database/
│   │   └── schema-patterns.md  # paths: lib/core/database/**
│   └── testing/
│       └── patrol-testing.md   # paths: integration_test/**, test/**
│
├── agents/                      # Agent definitions (Task tool)
│   ├── auth/auth-agent.md
│   ├── backend/data-layer-agent.md
│   ├── backend/supabase-agent.md
│   ├── frontend/flutter-specialist-agent.md
│   ├── pdf-agent.md
│   ├── code-review-agent.md
│   ├── planning-agent.md
│   └── qa-testing-agent.md
│
├── commands/
│   ├── resume-session.md
│   └── end-session.md
│
├── docs/                        # Reference-only (lazy load)
│   ├── chunked-sync-usage.md
│   ├── column-parser-enhancements.md
│   ├── e2e-test-setup.md
│   ├── manual-testing-checklist.md
│   ├── pagination-widgets-guide.md
│   └── pdf-workflows.md
│
├── logs/
│   ├── session-log.md
│   ├── state-archive.md
│   └── defects-archive.md
│
├── plans/                       # Active plans
│   └── [active-plan].md
│
└── backlogged-plans/            # Deferred/completed plans
    ├── AASHTOWARE_Implementation_Plan.md
    └── OCR-Fallback-Implementation-Plan.md
```

---

## Files to Delete/Move

### Delete
- `.claude/implementation/` folder (entire folder + implementation_plan.md)
- `.claude/memory/standards.md` (just a reference file, content elsewhere)

### Move
| From | To |
|------|----|
| `memory/defects.md` | `autoload/_defects.md` |
| `memory/tech-stack.md` | `autoload/_tech-stack.md` |
| `memory/state-archive.md` | `logs/state-archive.md` |
| `memory/defects-archive.md` | `logs/defects-archive.md` |
| `plans/_state.md` | `autoload/_state.md` |
| `archive/*` | `backlogged-plans/*` |

### Consolidate
- `coding-standards.md` → merge into `architecture.md`
- `quality-checklist.md` → distribute to domain rules
- `defect-logging.md` → move instructions to `end-session.md`

### Delete After Moving
- `.claude/memory/` folder (empty after moves)
- `.claude/archive/` folder (renamed to backlogged-plans/)

---

## Docs Disposition

| Current File | Action | New Location |
|--------------|--------|--------------|
| architectural_patterns.md | Convert to rule | rules/architecture.md |
| 2026-platform-standards-update.md | Convert to rule | rules/platform-standards.md |
| sql-cookbook.md | Convert to rule | rules/backend/supabase-sql.md |
| sync-architecture-diagram.md | Convert to rule | rules/sync/sync-patterns.md |
| testing-guide.md | Convert to rule | rules/testing/patrol-testing.md |
| e2e-test-setup.md | Keep as docs | docs/ (reference) |
| chunked-sync-usage.md | Keep as docs | docs/ (reference) |
| column-parser-enhancements.md | Keep as docs | docs/ (reference) |
| manual-testing-checklist.md | Keep as docs | docs/ (reference) |
| pagination-widgets-guide.md | Keep as docs | docs/ (reference) |
| pdf-workflows.md | Keep as docs | docs/ (reference) |

---

## Autoload Folder Design

Files in `autoload/` will have NO `paths:` frontmatter, so Claude Code loads them always.

### _state.md (always loaded)
```markdown
# Session State
**Session**: 245 | **Date**: 2026-02-01
**Phase**: [current phase or "Ready for new work"]
**Last Session**: [1-line summary]
**Next**: [next action or "None"]
**Plan**: [path to active plan or "None"]
```

### _defects.md (always loaded)
```markdown
# Active Defects
Max 15 - oldest auto-archives to logs/defects-archive.md

### [CATEGORY] YYYY-MM-DD: Title
**Pattern**: What to avoid
**Prevention**: How to prevent
```

### _tech-stack.md (always loaded)
```markdown
# Tech Stack
Flutter 3.38+ | Dart 3.10+ | Android SDK 36 | iOS 15.0+
Key: provider, go_router, supabase_flutter, sqflite, syncfusion_flutter_pdf
```

---

## Expert Rules Design

Each expert rule will have:
1. `paths:` frontmatter for conditional loading
2. Domain-specific patterns and anti-patterns
3. Code references to actual project files
4. Relevant commands for that domain

Example structure:
```markdown
---
paths:
  - "lib/features/pdf/**/*.dart"
---
# PDF Generation Expert

## Quick Reference
[Key patterns, gotchas, commands]

## Patterns
[Detailed patterns with code examples]

## Anti-Patterns
[What to avoid]

## Debugging
[Common issues and solutions]

## References
[Links to docs for deep dives]
```

---

## Commands Redesign

### resume-session.md
```markdown
---
name: resume-session
description: Resume session with context summary
---

# Resume Session

## Actions

### 1. Check Git Status
git status && git log --oneline -3

### 2. Read State (already auto-loaded from autoload/)
- autoload/_state.md shows current phase and last session
- autoload/_defects.md shows active patterns

### 3. Check for Plans
- If plans/ folder has active plan → note the plan and current phase
- If no active plan → check backlogged-plans/ and mention available options
- Do NOT read plan contents, just note existence

### 4. Present Summary
**Session [N] Resume**

**Last Session**: [1-line summary from _state.md]
**Current Phase**: [phase or "Ready for new work"]
**Git Status**: [clean/uncommitted changes]

**Active Plan**: [plan name and phase] or "None"
**Backlogged Plans**: [list if no active plan] or "N/A"

### 5. Ask
"What would you like to focus on this session?"

Never start implementation without user confirmation.
```

### end-session.md
```markdown
---
name: end-session
description: End session with state update and archiving
---

# End Session

## Actions

### 1. Quality Checks
flutter analyze lib/ --no-fatal-infos
git status
git diff --stat

### 2. Gather Summary
- Main focus of session
- Completed tasks
- Decisions made
- Next priorities
- New defects discovered (if any)

### 3. Update State Files

**Update autoload/_state.md:**
- Increment session number
- Write 1-line summary
- Update phase/status
- Note commit hash if committed

**Update autoload/_defects.md (if new defects):**
- Add new defect with category and date
- Format: ### [CATEGORY] YYYY-MM-DD: Title

### 4. Archive Rotation
**If _state.md has >10 sessions:**
1. Move oldest session to logs/state-archive.md
2. Add under appropriate month header

**If _defects.md has >15 defects:**
1. Move oldest defect to logs/defects-archive.md
2. Remove from _defects.md

### 5. Session Log
Append to logs/session-log.md:
### YYYY-MM-DD (Session N)
- [Summary]

### 6. Commit (if changes)
git add .claude/
git commit -m "session: [brief summary]"

Do NOT include Co-Authored-By.

### 7. Present Summary
- Session number
- Work completed
- Commit hash (if any)
- Next session: run /resume-session
```

---

## Agent Workflow (Separate Sessions)

### Phase 1: PLAN
**Agents**: planning-agent + domain expert
**Session**: Dedicated planning session
**Behavior**:
- Ask many clarifying questions before proposing solutions
- Provide 3+ options with logic/reasoning for each choice
- Explain constraints and drawbacks of each approach
- Break work into PR-sized phases with subphases and steps
- Domain expert consulted for technical feasibility
**Output**: Plan saved to `plans/[plan-name].md`

### Phase 2: CRITIQUE
**Agents**: None (user-driven)
**Session**: User reviews offline
**Behavior**:
- User reviews plan manually
- User may use external tools (Codex, etc.)
- No Claude review needed in this phase
**Output**: Approved plan ready for implementation

### Phase 3: IMPLEMENT
**Agents**: Domain agents (selected by file paths)
**Session**: Implementation session(s)
**Agent Selection**:
| Files Being Modified | Agent |
|---------------------|-------|
| `lib/**/presentation/**` | flutter-specialist-agent |
| `lib/**/data/**` | data-layer-agent |
| `lib/features/auth/**` | auth-agent |
| `lib/features/pdf/**` | pdf-agent |
| `lib/features/sync/**` | supabase-agent |
| `lib/core/database/**` | data-layer-agent + supabase-agent |
| `integration_test/**`, `test/**` | qa-testing-agent |
**Behavior**: Execute tasks from approved plan

### Phase 4: REVIEW
**Agents**: code-review-agent
**Session**: Review session
**Behavior**:
- Reviews all implemented code changes
- Checks against quality standards
- Identifies issues, suggests improvements
**Output**: Review feedback, approval or revision requests

### Phase 5: TEST/VERIFY/DOCUMENT
**Agents**: qa-testing-agent + domain expert
**Session**: Testing session
**Behavior**:
- qa-testing-agent runs test suite, verifies functionality
- Domain expert consulted for domain-specific test cases
- Creates/updates documentation as needed
**Output**: Test results, verification sign-off

---

## Agent Domain Boundaries

| Agent | Primary Domain | Works With |
|-------|---------------|------------|
| planning-agent | Requirements, plan creation | All domain experts |
| flutter-specialist-agent | UI, widgets, state, theme | data-layer-agent |
| data-layer-agent | Models, repos, providers | supabase-agent |
| supabase-agent | Cloud schema, RLS, SQL | data-layer-agent |
| auth-agent | Auth flows, security | supabase-agent |
| pdf-agent | PDF templates, field mapping | data-layer-agent |
| code-review-agent | Quality gates, architecture | All (read-only) |
| qa-testing-agent | Testing, verification | All domain experts |

---

## Global CLAUDE.md Redesign

### Current (25 lines)
```markdown
# Global Claude Code Settings
## Environment
- Windows via Git Bash, PowerShell via pwsh
## Git Commits
- Never add Co-Authored-By
## Implementation Rules
- Complete all work, ask questions, admit uncertainty
## Build Commands
- Use pwsh for Flutter
```

### Proposed (cleaned up, project-specific moved)
```markdown
# Global Claude Code Settings

## Environment
- Windows via Git Bash
- PowerShell: `pwsh -Command "..."`

## Rules
- Never add Co-Authored-By to commits
- Complete ALL plan items - only user can postpone
- Ask questions when unsure - never assume
- Admit when you don't know something
```

**Move to project CLAUDE.md:**
- Flutter build commands (project-specific)

---

## Implementation Phases

### Phase 1: Create Folder Structure
**Files**: Create new folders
1. Create `.claude/autoload/`
2. Create `.claude/rules/pdf/`
3. Create `.claude/rules/sync/`
4. Create `.claude/rules/database/`
5. Create `.claude/rules/testing/`
6. Create `.claude/backlogged-plans/`

### Phase 2: Move Autoload Files
**Files**: Move to autoload/
1. `plans/_state.md` → `autoload/_state.md`
2. `memory/defects.md` → `autoload/_defects.md`
3. `memory/tech-stack.md` → `autoload/_tech-stack.md`

### Phase 3: Move Archive Files
**Files**: Move to logs/ and backlogged-plans/
1. `memory/state-archive.md` → `logs/state-archive.md`
2. `memory/defects-archive.md` → `logs/defects-archive.md`
3. `archive/AASHTOWARE_Implementation_Plan.md` → `backlogged-plans/`
4. `archive/OCR-Fallback-Implementation-Plan.md` → `backlogged-plans/`

### Phase 4: Convert Docs to Rules
**Files**: 5 docs become rules with paths: frontmatter
1. `docs/architectural_patterns.md` → `rules/architecture.md`
2. `docs/2026-platform-standards-update.md` → `rules/platform-standards.md`
3. `docs/sql-cookbook.md` → `rules/backend/supabase-sql.md`
4. `docs/sync-architecture-diagram.md` → `rules/sync/sync-patterns.md`
5. `docs/testing-guide.md` → `rules/testing/patrol-testing.md`

### Phase 5: Create New Expert Rules
**Files**: New rule files (extract from docs + web research)
1. `rules/pdf/pdf-generation.md` - from pdf-workflows.md + research
2. `rules/database/schema-patterns.md` - from data-layer.md extraction
3. Add `paths:` frontmatter to all existing rules

### Phase 6: Consolidate Rules
**Files**: Merge redundant content
1. Merge `coding-standards.md` into `rules/architecture.md`
2. Distribute `quality-checklist.md` items to domain rules
3. Move defect-logging instructions to `end-session.md`
4. Delete `coding-standards.md`, `quality-checklist.md`, `defect-logging.md`

### Phase 7: Update CLAUDE.md Files
**Files**: Both global and project
1. Clean up `~/.claude/CLAUDE.md` (remove project-specific)
2. Rewrite `.claude/CLAUDE.md` with new structure references
3. Update all file path references

### Phase 8: Update Commands
**Files**: resume-session.md, end-session.md
1. Rewrite `resume-session.md` for new structure
2. Rewrite `end-session.md` for new paths and archiving

### Phase 9: Update Agents
**Files**: Add workflow phase markers to each agent
1. Add "Use during: [PHASE]" to each agent
2. Clarify domain boundaries
3. Update planning-agent with new behavior requirements

### Phase 10: Cleanup
**Files**: Delete empty/redundant folders
1. Delete `memory/` folder
2. Delete `archive/` folder
3. Delete `implementation/` folder
4. Keep `plans/` for active plans (just move `_state.md` out)

### Phase 11: Verify
**Tests**: Confirm everything works
1. Start fresh conversation
2. Run `/context` - verify autoload files load
3. Edit a PDF file - verify pdf-generation rule loads
4. Edit a sync file - verify sync-patterns rule loads
5. Run `/resume-session` - verify output format
6. Run `/end-session` - verify state updates correctly

---

## Critical Files to Modify

| File | Action |
|------|--------|
| `~/.claude/CLAUDE.md` | Clean up, remove project-specific |
| `.claude/CLAUDE.md` | Rewrite with new structure |
| `.claude/commands/resume-session.md` | Rewrite |
| `.claude/commands/end-session.md` | Rewrite |
| `.claude/agents/planning-agent.md` | Add behavior requirements |
| `.claude/agents/*.md` | Add workflow phase markers |
| `.claude/rules/*.md` | Add/update paths: frontmatter |

---

## Tools & Permissions Optimization

### Current State (Messy)
- 99 individual permission entries in `settings.local.json`
- Many one-off specific commands that should use wildcards
- Notion MCP configured but underutilized
- No DCM or Dart MCP servers

### Proposed MCP Servers

| Server | Purpose | Priority |
|--------|---------|----------|
| **DCM MCP** | Code quality (475+ rules), auto-fix, format | HIGH |
| **Dart/Flutter MCP** | Official SDK tooling, analyzer integration | HIGH |
| **Notion MCP** | Already configured - optimize usage | MEDIUM |

### Permission Cleanup Strategy

**Before (99 entries):**
```json
"Bash(flutter --version:*)",
"Bash(flutter pub get:*)",
"Bash(flutter analyze:*)",
"Bash(flutter test:*)",
"Bash(flutter clean:*)",
"Bash(flutter build:*)",
// ... 90+ more specific commands
```

**After (consolidated):**
```json
{
  "permissions": {
    "deny": [
      "Bash(rm -rf *)",
      "Read(.env*)",
      "Read(**/secrets/**)"
    ],
    "allow": [
      "Bash(flutter *)",
      "Bash(dart *)",
      "Bash(git *)",
      "Bash(adb *)",
      "Bash(patrol *)",
      "Bash(pwsh *)",
      "Bash(gh *)",
      "Bash(npm *)",
      "WebFetch(domain:github.com)",
      "WebFetch(domain:pub.dev)",
      "WebFetch(domain:dart.dev)",
      "WebFetch(domain:docs.patrol.dev)",
      "Skill(end-session)",
      "Skill(resume-session)",
      "mcp__notion__*",
      "mcp__dcm__*",
      "mcp__dart__*"
    ]
  }
}
```

### MCP Configuration (mcp.json or settings)

```json
{
  "mcpServers": {
    "dcm": {
      "command": "dcm",
      "args": ["mcp-server"],
      "enabled": true
    },
    "dart": {
      "command": "dart",
      "args": ["mcp-server"],
      "enabled": true
    }
  }
}
```

### Implementation Phases for Tools

**Phase 12: Permissions Cleanup**
1. Backup current `settings.local.json`
2. Consolidate 99 permissions into ~20 wildcard patterns
3. Add deny rules for sensitive operations (.env, secrets, rm -rf)
4. Test common workflows (flutter, git, adb, patrol)

**Phase 13: MCP Server Setup**
1. Install/configure DCM MCP server
2. Configure Dart/Flutter MCP server (requires Dart SDK 3.9+)
3. Add MCP permissions to settings
4. Test DCM analyze/fix workflow
5. Test Dart analyzer integration

**Phase 14: CODEX Production Readiness Plan Extraction**
1. Review deleted CODEX.md content (via git show)
2. Extract still-pending items:
   - Widget extraction from mega-screens
   - Service injection for parsing/PDF services
   - Sliverization for performance
   - Data layer pagination
   - DRY/KISS utilities
3. Create new focused plan in `plans/production-readiness.md`
4. Prioritize by impact and effort

---

## Verification Checklist

- [ ] `/context` shows autoload files loaded at startup
- [ ] Rules load conditionally based on file being edited
- [ ] `/resume-session` shows correct summary format
- [ ] `/end-session` updates state correctly
- [ ] Archiving rotation works (>10 sessions, >15 defects)
- [ ] No broken file path references
- [ ] All agents have workflow phase markers
- [ ] planning-agent asks questions and gives 3+ options
- [ ] Permissions work with wildcard patterns
- [ ] DCM MCP server responds to commands
- [ ] Dart MCP server integrates with analyzer
