# .claude Directory Audit & Update Plan
**Date**: 2026-02-19
**Scope**: Full audit and update of .claude/ configuration (agents, skills, rules, CLAUDE.md, memory files)

## Decisions Made

| # | Question | Decision | Rationale |
|---|---|---|---|
| 1 | Approach | Audit first, full comparison | See full picture before changing anything |
| 2 | Sequencing | Do both in one pass | Fix references + update skills in single commit |
| 3 | systematic-debugging structure | Superset (A) | Keep our project-specific sections + add all 6 upstream improvements |
| 4 | pdf-agent memory | Surgical update (B) | Keep valid architectural decisions, update only stale v2 refs |
| 5 | New upstream skills | dispatching-parallel-agents only (C) | Directly fixes "agents reverting each other" pain point |
| 6 | CLAUDE.md audit section | Keep, mark backlogged (B) | Honest about status without losing the intent |
| 7 | code-review-agent memory | Agent self-populates (A) | Read own past reports, extract patterns |
| 8 | brainstorming updates | YAGNI only | Hard gate + writing-plans handoff skipped |

---

## Phase 1: Fix 7 Broken File References

**Agent**: inline (surgical edits, no agent needed)

| # | File | Line(s) | Action |
|---|---|---|---|
| 1 | `rules/architecture.md` | 153 | Remove `lib/data/models/models.dart` reference — `lib/data/` is empty/legacy |
| 2 | `rules/pdf/pdf-generation.md` | 26 | Remove `lib/features/pdf/data/services/form_field_mappings.dart` — mappings inline in pdf_service.dart |
| 3 | `rules/testing/patrol-testing.md` | 33, 84 | Fix `test_bundle.dart` → `test_config.dart` |
| 4 | `agents/qa-testing-agent.md` | 143 | Fix `integration_test/test_bundle.dart` → `integration_test/patrol/test_config.dart` |
| 5 | `CLAUDE.md` | 236–248 | Handled in Phase 5 (audit section rewrite) |
| 6 | `CLAUDE.md` | 231 | Fix "Active plan" → "Backlogged plan", update path to `backlogged-plans/` |
| 7 | `agents/pdf-agent.md` | 23 (frontmatter) | Remove `prd: prds/pdf-extraction-v2-prd-2.0.md` line — file doesn't exist |

**Verification**: After edits, grep for each broken path to confirm removal.

---

## Phase 2: Update systematic-debugging Skill

**Agent**: inline
**File**: `.claude/skills/systematic-debugging/SKILL.md`

**Add** (6 sections from upstream, woven inline):
1. **Phase 1, Step 4**: "Gather Evidence in Multi-Component Systems" — instrument each component boundary before proposing fixes; example with layered echo/logging
2. **Phase 1, Step 5**: "Trace Data Flow" — explicit step referencing `root-cause-tracing.md`
3. **Phase 3, Step 4**: "When You Don't Know" — explicitly say "I don't understand X", don't pretend
4. **Phase 4, Step 4+5**: "If Fix Doesn't Work" formal gate — <3 tries return to Phase 1; ≥3 tries STOP, question architecture protocol
5. **"Red Flags — STOP and Follow Process"** section — list of thought patterns that signal off-track
6. **"Your Human Partner's Signals"** section — signals like "Stop guessing", "Ultrathink this"
7. **"Common Rationalizations" table** — expand from 5 rows to 8 (add "Pattern too long", "One more fix", "I see the problem")
8. **"Quick Reference" table** — Phase → Key Activities → Success Criteria
9. **"When Process Reveals No Root Cause"** — 95% = incomplete investigation
10. **"Real-World Impact"** stats — 15–30 min systematic vs 2–3 hrs thrashing

**Change** (pressure tests):
- Remove eager `@`-references to all 3 pressure test files
- Replace with: `> Pressure test scenarios available in `references/pressure-tests/` — invoke on demand if needed`

**Keep** (project-specific, untouched):
- "Before Starting: Check Per-Feature Defects" section
- "After Fixing: Update Per-Feature Defects" section
- Flutter-Specific Debug Commands section

**Verification**: Skill loads fast (no eager @-includes), all 6 upstream additions present.

---

## Phase 3: Update brainstorming Skill

**Agent**: inline
**File**: `.claude/skills/brainstorming/SKILL.md`

**Add** (1 item):
- YAGNI principle in Core Principles: "**YAGNI** — Ruthlessly remove unnecessary features during design. Don't design for hypothetical requirements."

**Skip**: Hard gate against implementation, writing-plans handoff.

**Verification**: YAGNI appears in Core Principles section.

---

## Phase 4: Add dispatching-parallel-agents Skill

**Agent**: inline (fetch from upstream, adapt frontmatter)
**Source**: `https://raw.githubusercontent.com/obra/superpowers/main/skills/dispatching-parallel-agents/SKILL.md`
**Target**: `.claude/skills/dispatching-parallel-agents/SKILL.md`

**Adaptations**:
- Add frontmatter: `name`, `description`, `context: fork`, `agent: planning-agent`, `user-invocable: true`
- Register in `CLAUDE.md` Skills table
- Add to `planning-agent.md` skills frontmatter

**Addresses**: "Agents sometimes revert each other's changes" pain point (MEMORY.md:37)

**Verification**: File exists, frontmatter valid, CLAUDE.md updated.

---

## Phase 5: Fix CLAUDE.md Audit Section

**Agent**: inline
**File**: `.claude/CLAUDE.md`, lines 229–249

**Changes**:
- Line 231: Change `**Active plan**` → `**Backlogged plan**`
- Line 231: Fix path `plans/2026-02-15-audit-system-design.md` → `backlogged-plans/2026-02-15-audit-system-design.md`
- Lines 236, 247, 248: Add note `(not yet implemented)` next to pre-commit.sh and setup-hooks.sh references
- Add sentence: "Hook scripts do not yet exist on disk. Run setup-hooks.sh once they are created."

**Verification**: No reference to a non-existent file without a qualifying note.

---

## Phase 6: Surgical pdf-agent Memory Update

**Agent**: general-purpose subagent
**File**: `.claude/agent-memory/pdf-agent/MEMORY.md`

**Stale entries to update** (v2 → v3):
- Stage 4A: `row_classifier_v2.dart` → `row_classifier_v3.dart`
- Stage 4E: Add new stages: `row_parser_v3.dart`, `field_confidence_scorer.dart`, `header_consolidator.dart`, `numeric_interpreter.dart`
- Models: Add `interpretation_rule.dart`, `interpreted_value.dart`, `rules/` directory
- Test paths: Update `stage_4a_row_classifier_test.dart` → `row_classifier_v3_test.dart`
- Add new test files: `field_confidence_scorer_test.dart`, `header_consolidator_test.dart`, `numeric_interpreter_test.dart`, `whitespace_inset_test.dart`
- Current baseline: Update to `51 OK / 4 LOW / 0 BUG`, quality `0.970`, parsed `131/131`, bid_amount `124/131`

**Keep** (still valid):
- Font encoding corruption patterns
- DocumentQualityProfiler design
- StructurePreserver design
- CellExtractorV2 design (Stage 4D)
- RegionDetectorV2 design (Stage 4B)
- Build/INSTALL.vcxproj gotcha
- All architectural decisions

**Verification**: No v2 file references remain for stages that have v3 replacements.

---

## Phase 7: code-review-agent Memory Self-Population

**Agent**: code-review-agent
**Task**: Read all 8 reports in `.claude/code-reviews/`, extract recurring patterns, architectural rules, and frequently reviewed files. Write to `.claude/agent-memory/code-review-agent/MEMORY.md`.

**Source reports**:
- `2026-02-14-full-codebase-review.md`
- `2026-02-14-v2-extraction-pipeline-review.md`
- `2026-02-16-dead-code-prunekit-report.md`
- `2026-02-16-extraction-pipeline-dry-kiss-review.md`
- `2026-02-18-edgepos-alignment-cluster-centers-review.md`
- `2026-02-18-scan-whitespace-inset-root-cause-analysis.md`
- `2026-02-18-springfield-fixture-regen-stage-trace-upstream-scorecard.md`
- `2026-02-19-per-line-dynamic-whitespace-inset-implementation-review.md`

**Extract**:
- Recurring anti-patterns caught across multiple reviews
- Architectural rules enforced (data-accounting assertions, no pixel values, etc.)
- Frequently reviewed files/directories
- Patterns unique to this codebase

**Verification**: Memory file has content in all 4 sections (Patterns, Gotchas, Architectural Decisions, Frequently Referenced Files).

---

## Commit Strategy

Single commit covering all phases:
```
chore(.claude): audit and update — fix 7 broken refs, update skills, add dispatching-parallel-agents
```

All changes are in `.claude/` only — no production code touched.
