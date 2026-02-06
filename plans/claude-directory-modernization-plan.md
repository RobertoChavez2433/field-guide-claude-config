# Claude Directory Modernization Plan (v2 — Finalized)

Update `.claude/` configuration to leverage Claude Code 2.1.32 features, optimize token usage, clean up stale files, enable agent memory, and add 15 quick-reference commands.

**Decided during brainstorming session 2026-02-05.**

---

## Phase 1: Cleanup (Delete Deprecated/Stale Files)

### Files to Delete
| File | Reason |
|------|--------|
| `.claude/settings.local.json.backup` | Outdated backup from 2026-02-01 |
| `.claude/phase0-completion-summary.md` | Orphaned at root; content captured in plans/ |
| `lib/features/pdf/services/ocr/PHASE5_VERIFICATION.md` | Untracked markdown in production code |

### Files to KEEP (user decision)
| File | Reason |
|------|--------|
| `.claude/logs/session-log.md` | Historical record of the project |

### Directories to Delete
| Directory | Reason |
|-----------|--------|
| `lib/data/` | Empty legacy directories (0 dart files) |
| `lib/presentation/` | Empty legacy directories (0 dart files) |

### Stale Docs to Delete
| File | Lines | Reason |
|------|-------|--------|
| `.claude/docs/phase-4-completion-report.md` | 412 | Completed historical work |
| `.claude/docs/phase-4-implementation-summary.md` | 265 | Duplicate of above |
| `.claude/docs/tesseract-phase4-summary.md` | 245 | Third file about same completed phase |
| `.claude/docs/column-parser-enhancements.md` | 229 | Historical completed enhancements |

### Backlogged Plans to Delete
| File | Lines | Reason |
|------|-------|--------|
| `.claude/backlogged-plans/skills-and-agents-integration.md` | 192 | Superseded by this modernization |
| `.claude/backlogged-plans/Full-Session-Analysis-Instructions.md` | 123 | One-off stale instructions |

### Files to Clean
| File | Action |
|------|--------|
| `.claude/settings.local.json` line ~50 | Remove legacy Session 248 git commit permission |

---

## Phase 2: Token Optimization — Trim architecture.md

**Goal**: Reduce `architecture.md` from ~260 lines (~2,045 tokens) to ~180 lines (~1,425 tokens) by moving all 6 UI-specific sections to `flutter-ui.md`.

### Move TO `rules/frontend/flutter-ui.md` (loads only for `lib/**/presentation/**`):
1. **Screen Structure** (lines 87-95): StatefulWidget template, _build methods
2. **Card-Based Lists** (lines 98-104): Tappable cards with leading icons
3. **Split View / Master-Detail** (lines 106-132): 27-line ASCII diagram
4. **Form Organization** (lines 134-141): Stepper widget usage
5. **Theming Pattern** (lines 143-155): Color naming, Theme usage
6. **Clickable Stat Cards** (lines 204-220): InkWell dashboard pattern

### Keep IN `architecture.md` (core patterns for ALL dart files):
- Layer Architecture (project structure)
- Model Pattern (data model conventions)
- Database Pattern (table naming, indexing)
- Navigation Pattern (routing)
- State Management (Provider patterns)
- Anti-Patterns table (essential safety net)
- Offline-First Pattern (sync status, photo storage)
- Barrel Exports / Enum Handling (conventions)

### Result
- `architecture.md`: ~180 lines (~1,425 tokens) — **saves ~620 tokens per .dart file edit**
- `flutter-ui.md`: gains ~80 lines but only loads when editing presentation files

---

## Phase 3: context: fork for Verbose Skills

Add `context: fork` to skills that generate verbose output. Forked skills run in isolated subagent contexts — keeps main conversation clean.

### pdf-processing/SKILL.md
```yaml
---
name: pdf-processing
description: PDF template filling, OCR extraction, and CLI analysis tools
context: fork
agent: pdf-agent
---
```

### systematic-debugging/SKILL.md
```yaml
---
name: systematic-debugging
description: Root cause analysis framework that prevents guess-and-check debugging
context: fork
agent: qa-testing-agent
user-invocable: true
---
```

**Why**: pdf-processing has 4 reference docs; systematic-debugging has 7 reference docs + 3 pressure tests. Forking isolates this verbose content.

---

## Phase 4: Migrate Commands to Skills

Migrate `end-session` and `resume-session` to skills format. Delete `session-checklist.md` (unused).

### Migration Map
| Source | Destination |
|--------|-------------|
| `.claude/commands/end-session.md` | `.claude/skills/end-session/SKILL.md` |
| `.claude/commands/resume-session.md` | `.claude/skills/resume-session/SKILL.md` |

### Frontmatter for Both
```yaml
user-invocable: true
disable-model-invocation: true
```

### Post-Migration
- Delete `session-checklist.md`
- Delete `.claude/commands/` directory
- Verify `/end-session` and `/resume-session` still work as slash commands

---

## Phase 5: Agent Modernization

### code-review-agent.md
```yaml
disallowedTools: Write, Edit, Bash    # Read-only enforcement (belt-and-suspenders)
memory: project                        # Cross-session learning
```

### planning-agent.md
```yaml
model: opus                            # Better architectural analysis (was: sonnet)
disallowedTools: Edit                  # Can Write plans but not edit source code
```
Note: planning-agent already has `skills: [brainstorming]` and `permissionMode: plan`.

### pdf-agent.md
```yaml
memory: project                        # Remember column layouts, OCR quirks, extraction patterns
```

### qa-testing-agent.md
```yaml
memory: project                        # Remember test failures, debugging patterns, defect history
```

### frontend-flutter-specialist-agent.md
```yaml
memory: project                        # Remember widget patterns, performance optimizations
```

### Other agents (backend-data-layer, backend-supabase, auth)
No changes needed.

---

## Phase 6: Add Frontmatter to All Skills

All 6 skills currently have NO YAML frontmatter. Add frontmatter for discovery and features:

| Skill | Frontmatter |
|-------|-------------|
| **brainstorming** | `name`, `description: Collaborative design through structured questioning`, `agent: planning-agent`, `user-invocable: true` |
| **systematic-debugging** | `name`, `description: Root cause analysis framework`, `context: fork`, `agent: qa-testing-agent`, `user-invocable: true` |
| **test-driven-development** | `name`, `description: Red-Green-Refactor TDD cycle` |
| **verification-before-completion** | `name`, `description: Evidence-based verification gate` |
| **interface-design** | `name`, `description: Flutter design system and UI tokens`, `agent: frontend-flutter-specialist-agent` |
| **pdf-processing** | `name`, `description: PDF template filling, OCR extraction, CLI tools`, `context: fork`, `agent: pdf-agent` |

---

## Phase 7: Update CLAUDE.md

### 7a. Remove Legacy Directory References
Remove `data/` and `presentation/` from Project Structure section.

### 7b. Replace Build Commands with 15-Command Quick Reference

```markdown
## Quick Reference Commands

**CRITICAL**: Git Bash silently fails on Flutter. ALWAYS use pwsh wrapper.

### Build & Run
1. `pwsh -Command "flutter run -d windows"`                                    — Run on desktop
2. `pwsh -Command "flutter clean && flutter build apk --release"`              — Build APK
3. `pwsh -Command "flutter clean"`                                             — Clean build artifacts

### Testing
4. `pwsh -Command "flutter test"`                                              — All tests
5. `pwsh -Command "flutter test test/features/pdf/table_extraction/"`          — PDF extraction tests
6. `pwsh -Command "flutter test test/features/pdf/services/ocr/"`              — OCR tests
7. `pwsh -Command "flutter test <path/to/specific_test.dart>"`                 — Single test file
8. `pwsh -Command "flutter test --dart-define=PDF_PARSER_DIAGNOSTICS=true"`    — Tests with diagnostics

### Process Management
9. `pwsh -Command "Stop-Process -Name 'construction_inspector' -Force -ErrorAction SilentlyContinue; Stop-Process -Name 'dart' -Force -ErrorAction SilentlyContinue"`

### Dependencies & Diagnostics
10. `pwsh -Command "flutter pub get"`       — Get dependencies
11. `pwsh -Command "flutter pub upgrade"`   — Upgrade dependencies
12. `pwsh -Command "flutter analyze"`       — Static analysis
13. `pwsh -Command "flutter doctor"`        — Environment diagnostics

### Git
14. `git log --oneline -10`                 — Recent commits
15. `git diff --stat`                       — Change summary

### Common Mistakes (from 577+ errors across 30+ sessions)
- NEVER run flutter/dart directly in Git Bash — ALWAYS use `pwsh -Command "..."`
- NEVER use wc, sed, awk, grep as Bash — use Read/Edit/Grep tools instead
- ALWAYS use `-ErrorAction SilentlyContinue` on Stop-Process
- ALWAYS set `timeout: 600000` on `flutter run` commands (default 120s is too short)
- ALWAYS quote paths with spaces: `"C:\Users\rseba\Projects\Field Guide App"`
- 164 quoting errors found — Windows paths with spaces cause unexpected EOF
- 128 permission errors found — kill stale dart.exe before rebuilds
```

### 7c. Leave end-session reference as-is
User decision: no change to end-session's session-log.md reference.

---

## Phase 8: Update Supporting Files

### _tech-stack.md
- Add `syncfusion_flutter_pdfviewer: ^32.1.25` (missing from Key Packages)
- Clarify flusseract: "Replaces flutter_tesseract_ocr (migration Session 280)"

### settings.local.json
- Remove legacy line ~50 (Session 248 one-off commit permission)

### logs/README.md
- Update to reflect current file state

### MEMORY.md
- Update to note this modernization session

---

## Phase 9: Agent Memory Setup

Create persistent memory directories for 4 agents:

```
.claude/agent-memory/
  pdf-agent/MEMORY.md
  qa-testing-agent/MEMORY.md
  code-review-agent/MEMORY.md
  frontend-flutter-specialist-agent/MEMORY.md
```

Each MEMORY.md initialized with:
```markdown
# Agent Memory — [Agent Name]

## Patterns Discovered

## Gotchas & Quirks

## Architectural Decisions

## Frequently Referenced Files
```

Agent reads first 200 lines on every invocation, and can write notes during sessions.

---

## Summary

| Phase | What | Files Changed | Impact |
|-------|------|---------------|--------|
| 1 | Cleanup | 3 deleted + 4 docs + 2 backlog + 2 dirs + 1 edit | Hygiene |
| 2 | Trim architecture.md | 2 edited | **-620 tokens/conversation** |
| 3 | Fork verbose skills | 2 edited | Isolates verbose content |
| 4 | Commands to Skills | 2 created, 3 deleted | Better format + disable-model-invocation |
| 5 | Agent modernization | 5 edited | Memory, restrictions, opus model |
| 6 | Skill frontmatter | 6 edited (includes Phase 3) | Enables discovery + fork |
| 7 | CLAUDE.md | 1 edited | 15 commands + common mistakes |
| 8 | Supporting files | 4 edited | Accuracy updates |
| 9 | Agent memory setup | 4 created | Cross-session learning |
| **Total** | | **~35 operations** | **~620 tokens saved + agent memory + safety** |

---

## Verification

1. `/resume-session` loads context correctly
2. `/end-session` works (dry run)
3. Spot-check 2-3 agents via Task tool (verify memory loads)
4. `.claude/commands/` directory is gone
5. No broken `@` imports in CLAUDE.md
6. `architecture.md` is leaner, UI patterns in `flutter-ui.md`
7. Agent memory directories exist and are writable
8. code-review-agent cannot Write/Edit/Bash
9. planning-agent cannot Edit, uses opus model
10. `/brainstorming` and `/systematic-debugging` are invocable from / menu

---

## Decisions Log

All decisions made during brainstorming session 2026-02-05:

| Decision | User Choice |
|----------|-------------|
| Overall goal | Full modernization |
| session-log.md | Keep as historical record |
| architecture.md trim | Move all 6 UI sections |
| context: fork | Both pdf-processing + systematic-debugging |
| Commands migration | Migrate end-session + resume-session, delete session-checklist |
| Agent memory | pdf-agent, qa-testing, code-review, frontend-flutter (project scope) |
| Agent tool restrictions | code-review: disallowedTools Write/Edit/Bash; planning: disallowedTools Edit |
| Planning model | Upgrade to opus |
| Skill invocability | brainstorming + systematic-debugging user-invocable; rest agent-only |
| verification-before-completion | NOT user-invocable |
| Stale docs | Delete all 4 phase-4/column-parser docs |
| Backlogged plans | Delete skills-and-agents-integration + Full-Session-Analysis |
| CLAUDE.md commands | 15 commands + Common Mistakes section |
| end-session session-log ref | Leave as-is |
