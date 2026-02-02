# Skills Implementation Plan (Simplified)

**Last Updated**: 2026-02-01
**Status**: DRAFT

---

## Overview

This plan adds **2 new skills** and fixes dead references:
1. **End-session enhancement** - Dual-repo commit
2. **Interface-design** - UI consistency for Flutter
3. **Cleanup** - Fix dead skill refs in flutter-specialist-agent

---

## Part 1: End-Session Enhancement

### Requirements
- Commit BOTH repos (app + claude-config) if changes exist
- Different commit messages per repo based on actual changes
- Skip silently if no changes

### Repos
1. App: `C:\Users\rseba\Projects\Field Guide App`
2. Config: `C:\Users\rseba\Projects\Field Guide App\.claude`

### Skill Structure
```
.claude/skills/end-session/
├── SKILL.md
└── scripts/
    └── rotate.ps1  # Optional: automate rotation
```

### SKILL.md Key Changes
```yaml
---
name: end-session
description: End session with auto-archiving and dual-repo commit
disable-model-invocation: true
---
```

**Dual-Repo Commit Logic:**
```bash
# App repo - commit only if changes
cd "C:\Users\rseba\Projects\Field Guide App"
if [ -n "$(git status --porcelain)" ]; then
  # Analyze changes and create appropriate message
  git add -A && git commit -m "[message based on actual changes]"
fi

# Claude-config repo - commit only if changes
cd "C:\Users\rseba\Projects\Field Guide App\.claude"
if [ -n "$(git status --porcelain)" ]; then
  # Analyze changes and create appropriate message
  git add -A && git commit -m "[message based on actual changes]"
fi
```

---

## Part 2: Interface-Design Skill

### Source
https://github.com/Dammyjay93/interface-design

### What It Does
- Creates design system (`.interface-design/system.md`)
- Audits code against design tokens
- Extracts patterns from existing code
- Ensures Claude states design choices before components

### Commands
- `/interface-design:init` - Start building with design principles
- `/interface-design:audit <path>` - Check code against system
- `/interface-design:extract` - Pull patterns from existing code
- `/interface-design:status` - Show current system

### Adaptation for Flutter
- Replace CSS tokens with Flutter ThemeData tokens
- Pre-populate construction inspection domain:
  - **Domain**: Field work, clipboards, hard hats, weather, concrete, steel
  - **Colors**: Safety orange, concrete gray, blueprint blue, caution yellow
  - **Signature**: Large touch targets for gloved hands, outdoor-readable

### Skill Structure
```
.claude/skills/interface-design/
├── SKILL.md
└── references/
    ├── flutter-tokens.md        # Flutter ThemeData guide
    └── construction-domain.md   # Pre-populated domain exploration
```

### Wiring to flutter-specialist-agent
Update frontmatter:
```yaml
skills:
  - interface-design
```

---

## Part 3: Cleanup - Fix Dead References

### Current (broken)
In `.claude/agents/frontend/flutter-specialist-agent.md`:
```yaml
skills:
  - /frontend-design:frontend-design
  - /ui-consistency
```

### Fixed
```yaml
skills:
  - interface-design
```

---

## Part 4: Implementation Phases

### Phase 1: Create end-session Skill
1. Create `.claude/skills/end-session/SKILL.md` with dual-repo logic
2. Copy content from current command, add enhancements
3. Test that it works

### Phase 2: Create interface-design Skill
1. Create `.claude/skills/interface-design/SKILL.md` (adapted from Dammyjay93)
2. Create `references/flutter-tokens.md`
3. Create `references/construction-domain.md`

### Phase 3: Update flutter-specialist-agent
1. Replace dead skill refs with `interface-design`
2. Verify agent loads skill correctly

### Phase 4: Cleanup
1. Delete `.claude/commands/end-session.md` (migrated to skill)
2. Optionally migrate `/resume-session` to skill

---

## Part 5: Files Summary

### Create (5 files)
| Path | Source |
|------|--------|
| `.claude/skills/end-session/SKILL.md` | Current command + enhancements |
| `.claude/skills/end-session/scripts/rotate.ps1` | NEW (optional) |
| `.claude/skills/interface-design/SKILL.md` | Dammyjay93 (adapted) |
| `.claude/skills/interface-design/references/flutter-tokens.md` | NEW |
| `.claude/skills/interface-design/references/construction-domain.md` | NEW |

### Modify (1 file)
| Path | Changes |
|------|---------|
| `.claude/agents/frontend/flutter-specialist-agent.md` | Fix skills: frontmatter |

### Delete (1 file)
| Path | Reason |
|------|--------|
| `.claude/commands/end-session.md` | Migrated to skill |

---

## Part 6: Verification

- [ ] `/end-session` commits app repo when it has changes
- [ ] `/end-session` commits config repo when it has changes
- [ ] `/end-session` skips repos with no changes
- [ ] Commit messages reflect actual changes in each repo
- [ ] `/interface-design:status` shows system
- [ ] `/interface-design:audit lib/features/entries/` works
- [ ] flutter-specialist-agent loads interface-design skill
- [ ] Dead skill references removed

---

## Sources

- [interface-design](https://github.com/Dammyjay93/interface-design) - UI consistency
- [Claude Code Skills Docs](https://code.claude.com/docs/en/skills) - Official docs
