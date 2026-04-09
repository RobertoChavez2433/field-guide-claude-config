# Implement Skill Dispatch Refactor

**Work Type:** refactor+
**Date:** 2026-04-09
**Spec Author:** Paired conversation (Claude Opus 4.6 + user)

---

## Intent

**Problem:** The current `/implement` skill dispatches work via headless `claude --bare` subprocesses with a JSON-schema harness, `tee` pipelines, a `stream-filter.py` + `extract-result.py` pair, and a checkpoint file it maintains between phases. Per phase, it runs three reviewers (completeness, code review, security) in parallel and loops fix cycles on the full 3-reviewer fan-out. The infrastructure is heavy, brittle, and expensive, and it defers spec-drift detection into the same review step where code-quality and security noise live, so drift gets buried. We want a thinner, cheaper, Agent-tool-native workflow that catches spec drift immediately per phase and saves the broad quality sweep for the end.

**Who feels it:**
- The user driving `/implement` (slower runs, more tokens burned on infra, harder-to-read review output).
- Future maintainers of `.claude/skills/implement/` (harness residue in `worker-rules.md`, `reviewer-rules.md`, `severity-standard.md`, plus a duplicate `reference/` folder).
- Other skills that want to reuse spec-fidelity review but can't, because `completeness-review-agent` is currently coupled to `/implement`-specific inputs.

**Success criteria (measurable):**
1. `/implement` dispatches every implementer, reviewer, and fixer via the `Agent` tool. There are zero `claude --bare` invocations, zero `--json-schema` flags, and zero uses of `.claude/tools/stream-filter.py` or `.claude/tools/extract-result.py` anywhere in the new `SKILL.md`.
2. The main conversation's context never contains any phase body from the plan file. The orchestrator only reads the plan's header region (plan header region — from line 1 until the last declared phase line-range boundary is captured, or (on grep fallback) until every `## Phase N` heading is located) or `Grep`s for `## Phase N` headings to extract line ranges.
3. No checkpoint file is written at any point during `/implement`. `.claude/state/implement-checkpoint.json` never exists after this refactor. An interrupted `/implement` run restarts from phase 1 with no state recovery.
4. Per-phase review runs the `completeness-review-agent` only (one agent, not three). Any completeness finding at any severity (CRITICAL, HIGH, MEDIUM, or LOW) triggers a fixer cycle. A phase passes only when the completeness reviewer returns zero findings of any severity on that phase's files.
5. After every phase has passed, a single final gate runs `completeness-review-agent` (mode=final-sweep), `code-review-agent`, and `security-agent` as three parallel `Agent` calls in one orchestrator message.
6. The final-gate fixer receives: (every completeness finding regardless of severity) + (CRITICAL/HIGH/MEDIUM code-review findings) + (CRITICAL/HIGH/MEDIUM security findings). LOW code-review findings and LOW security findings are NOT sent to the fixer.
7. At the end of the final gate, `.claude/backlogged_reviews/<plan-name>.md` is created and populated with the LOW code-review findings, the LOW security findings, and any blockers the user chose to accept-as-is during escalation. The file never contains any completeness finding, because completeness findings are always fixed.
8. `completeness-review-agent.md` accepts `mode`, `spec_path`, `plan_path`, `plan_line_range`, and `files_in_scope` as explicit inputs so that any skill — not just `/implement` — can dispatch it.
9. Every dispatched agent (implementer, fixer, every reviewer) runs on `model: opus`. Sonnet and Haiku never appear.
10. Per phase, the review/fix loop has a hard cap of 3 cycles. One cycle = one reviewer pass + (if findings exist) one fixer pass. Cycle 3's reviewer pass is the terminal gate — if it still returns findings, escalate. The final gate has the same 3-cycle cap on its full-sweep re-runs.
11. Cap-hit events escalate to the user with the remaining findings and a prompt (`continue / stop / manual fix` per-phase; `stop / manual fix / accept-as-is and backlog` at final gate). The skill never silently marks a phase or final gate as BLOCKED without that prompt.

**Why now:** The current harness is the biggest tax on token budget and the largest source of friction in the current plan-execution pipeline. The new dispatch model is a strict simplification of the orchestrator and a strict tightening of the spec-fidelity loop, with no user-facing feature change. Landing it before the next large plan (pay applications, sync engine refactor, MDOT 1126) runs `/implement` saves compounding waste on those efforts.

---

## Scope

### In scope (v1)

**Rewritten:**
- `.claude/skills/implement/SKILL.md` — full rewrite describing the new Agent-tool dispatch orchestrator, the per-phase completeness-only loop, the final 3-agent parallel sweep, the fixer scope rules, the backlogged-reviews file, and the iron-law constraints on the orchestrator.
- `.claude/agents/completeness-review-agent.md` — refactored to a generic form that accepts `mode` (`per-phase` vs `final-sweep`), `spec_path`, `plan_path`, `plan_line_range`, and `files_in_scope` as explicit inputs in the inline prompt and is not coupled to `/implement`.

**Edited (surgical, strip harness-specific language only):**
- `.claude/skills/implement/references/worker-rules.md` — strip the header note that says it is "appended via `--append-system-prompt-file`".
- `.claude/skills/implement/references/reviewer-rules.md` — strip the trailing section that says findings are returned via `--json-schema` structured output.
- `.claude/skills/implement/references/severity-standard.md` — strip the line referencing the checkpoint's `low_findings` array and the line directing reviewers to output via `--json-schema` / `findings-schema.json`.
- `.claude/skills/writing-plans/SKILL.md` — update the plan-writing flow so newly generated plans declare per-phase line ranges in a machine-readable header block. Exact header format is implementation-detail, not spec-level; the requirement is that a downstream orchestrator can extract `(phase number, phase name, start line, end line)` tuples from the header without reading any phase body.

**Deleted:**
- `.claude/tools/stream-filter.py`
- `.claude/tools/extract-result.py`
- `.claude/skills/implement/references/headless-commands.md`
- `.claude/skills/implement/references/checkpoint-template.json`
- `.claude/skills/implement/references/findings-schema.json`
- `.claude/skills/implement/reference/` — the entire singular-named duplicate folder (confirmed during scope grep: identical copies of the plural `references/` folder, cruft).

**Created at runtime:**
- `.claude/backlogged_reviews/` — directory, created lazily by `/implement` at the final gate via one allowed `Bash` call (`mkdir -p .claude/backlogged_reviews`).
- `.claude/backlogged_reviews/<plan-name>.md` — a markdown file written at the final gate with LOW code-review findings, LOW security findings, and any accepted-as-is blockers. Completeness findings never appear here.

### Deferred (not v1, not out of scope forever)

- Introducing a cross-skill shared-rules directory (e.g. `.claude/skills/_shared/`) so `worker-rules.md` / `reviewer-rules.md` can live outside `implement/references/` and be cleanly referenced by other skills. The generic `completeness-review-agent` could benefit from this, but it's not required for v1 — the agent can reference the files at their current path.
- Documenting the new Agent-tool dispatch pattern inside `code-review-agent.md` and `security-agent.md` headers. They already work as Agent-tool subagents today; the documentation update is cosmetic and can wait.
- Back-migrating old plans (under `.claude/plans/completed/` and any open drafts) to declare per-phase line ranges in their headers. Grep fallback handles back-compat indefinitely.

### Out of scope

- `.claude/agents/code-review-agent.md` (unchanged)
- `.claude/agents/security-agent.md` (unchanged)
- `.claude/agents/plan-writer-agent.md` (unchanged)
- `.claude/agents/debug-research-agent.md` (unchanged)
- `.claude/skills/brainstorming/`, `.claude/skills/tailor/`, `.claude/skills/audit-docs/`, `.claude/skills/end-session/`, `.claude/skills/resume-session/`, `.claude/skills/systematic-debugging/`, `.claude/skills/test/` (all unchanged)
- `.claude/skills/implement/references/*guide*.md` (the 10 domain-context guide files: architecture, auth, data-layer, flutter-ui, pdf, platform-standards, schema-patterns, supabase-sql, sync-patterns, testing) — unchanged. These are loaded on-demand by the worker/reviewer routing tables and are not harness-coupled.
- `.claude/CLAUDE.md` — reviewed, has no stale headless references. Untouched.
- `.claude/plans/completed/2026-02-27-implement-skill-design.md` — historical plan, frozen as-is.
- `.claude/state/PROJECT-STATE.json` — unrelated, untouched.
- All of `lib/`, `test/`, `supabase/`, `tools/` (except the two Python scripts being deleted), `packages/`, `fg_lint_packages/`, `android/`, `ios/`, `windows/`.

### Constraints

- The orchestrator (the main `/implement` conversation) may only use these tools: `Read` (plan header region only — never phase bodies), `Write` (only the backlogged-reviews file, only at the final gate), `Bash` (only `mkdir -p .claude/backlogged_reviews`, nothing else), `Grep` (only to fall back on `## Phase N` heading extraction when the plan header lacks line ranges), `Agent` (all real work).
- The orchestrator may NEVER: edit any source file, run `flutter analyze`, run `flutter test`, run `dart run custom_lint`, run any build command, run `flutter clean`, run `git` commands, or read plan phase bodies.
- Every dispatched agent prompt MUST instruct the agent to begin by reading the appropriate rules file (`worker-rules.md` for implementers and fixers, `reviewer-rules.md` for all reviewers) and to follow every rule in it.
- Every dispatched agent MUST run on `model: opus` (per the standing `feedback_opus_agents_only` memory).
- No checkpoint file may be written anywhere. The phrase "checkpoint" does not appear as a behavior anywhere in the new `SKILL.md`. Interrupted runs have no recovery state — they restart from phase 1.
- Findings returned by an agent are captured by the orchestrator from the agent's final reply text (a `STATUS` / `FILES_CREATED` / `FILES_MODIFIED` / `LINT` / `NOTES` block for implementers and fixers; a severity-tagged findings list for reviewers). No JSON schema, no stdout parsing pipeline.
- The fixer (both per-phase and final-gate) is narrow: it receives the `worker-rules.md` reference and the inline findings list and nothing else. No spec path, no plan path, no line range. The findings themselves carry `file:line` and `fix_guidance` — that is the complete input.
- The per-phase LOW-completeness-finding rule is: always fix, never discard, never backlog. Per-phase reviewers do not emit LOW findings "for later" — every severity is equally blocking for a completeness reviewer.
- At the final gate, completeness findings at any severity go to the fixer. LOW code-review findings and LOW security findings go to the backlogged-reviews file. CRITICAL/HIGH/MEDIUM code-review and security findings go to the fixer.
- `Co-Authored-By` lines and "Generated with Claude Code" marketing text are prohibited everywhere in this refactor (per standing global and project rules).

### Non-goals

- Adding any new feature to `/implement`.
- Changing what the `code-review-agent` or `security-agent` looks for.
- Changing severity definitions in `severity-standard.md` beyond the mechanical strip of the two harness-coupled lines.
- Introducing parallelism into the per-phase loop (it remains strictly sequential: phase 1 fully closes before phase 2 starts).
- Adding retries, timeouts, or backoff logic beyond the existing 3-cycle caps.
- Building a resume mechanism for interrupted runs.
- Touching any skill other than `implement` and `writing-plans`.

---

## Vision

**User journey:**
1. User runs `/implement <plan-path> [phase-numbers]`. If bare filename, orchestrator resolves under `.claude/plans/`.
2. Orchestrator reads the plan's header region only (plan header region — from line 1 until the last declared phase line-range boundary is captured, or (on grep fallback) until every `## Phase N` heading is located), extracts `**Spec:**` → spec path and the per-phase line-range declarations. If no header declarations exist, orchestrator `Grep`s the plan for `## Phase N` headings and infers ranges from those line numbers.
3. Orchestrator prints a phase list and asks `Start implementation? (yes / no / adjust)`. User replies `yes` (or narrows via `adjust`).
4. For each phase in sequence:
   a. Orchestrator dispatches an **implementer** via `Agent` (`subagent_type: general-purpose`, `model: opus`) with an inline prompt that points at `worker-rules.md`, the plan path + exact line range for this phase, the spec path, and a STATUS/FILES_CREATED/FILES_MODIFIED/LINT/NOTES reply contract. The implementer runs `flutter analyze` and `dart run custom_lint` itself and reports clean before returning.
   b. Orchestrator captures the agent's reply fields in-context and dispatches a **completeness reviewer** via `Agent` (`subagent_type: completeness-review-agent`, `model: opus`) with `mode: per-phase`, the spec path, the plan path, the plan line range, and `files_in_scope`.
   c. If the reviewer returns zero findings at any severity, the phase PASSES and the orchestrator advances. If it returns one or more findings (at any severity), orchestrator dispatches a **fixer** via `Agent` (`subagent_type: general-purpose`, `model: opus`) with a narrow prompt — `worker-rules.md` reference + the inline findings list only — and loops back to step 4b.
   d. Per-phase cap: 3 review/fix cycles maximum (one cycle = reviewer pass + fixer pass if findings exist). Cycle 3's reviewer pass is the terminal gate — if it still returns findings, print the remaining findings and ask `continue / stop / manual fix`.
   e. Orchestrator prints a terse per-phase status block (phase name, review cycle count, file-created count, file-modified count, lint status) and moves to the next phase.
5. After every phase has closed, orchestrator runs the **final gate**:
   a. Dispatches three reviewers in parallel in a single orchestrator message: `completeness-review-agent` (mode=final-sweep, full spec against the union of every phase's files), `code-review-agent`, `security-agent`. All three on `model: opus`, all three foreground.
   b. Consolidates findings across the three replies (no deduplication — if multiple reviewers flag the same issue, that's a signal worth preserving; the fixer sees all of them).
   c. Splits findings into fixer-bound and backlog-bound: fixer-bound = (all completeness findings regardless of severity) + (CRITICAL/HIGH/MEDIUM code-review findings) + (CRITICAL/HIGH/MEDIUM security findings); backlog-bound = (LOW code-review findings) + (LOW security findings).
   d. If the fixer-bound set is non-empty, dispatches a narrow fixer (`Agent`, `general-purpose`, `opus`, worker-rules + inline findings only) and re-runs the full 3-reviewer parallel sweep. Same 3-cycle cap (one cycle = full parallel sweep + fixer pass if findings exist). Cycle 3's sweep is the terminal gate — if it still returns fixer-bound findings, prompt `stop / manual fix / accept-as-is and backlog`.
   e. `Bash`es `mkdir -p .claude/backlogged_reviews` and `Write`s `.claude/backlogged_reviews/<plan-name>.md` containing the LOW findings (grouped by reviewer) and any user-accepted blockers in a separate section.
6. Orchestrator prints a final summary: per-phase cycle counts, final-gate reviewer statuses, final-gate fix cycle count, backlog count + path, and a deduped union of every file created or modified across the whole run.

**Key interactions:**
- `Start implementation?` confirmation gate at the top (one yes/no/adjust message).
- Per-phase status line after every phase closes (terse, predictable, easy to scan).
- Escalation prompts on cap-hit, surfaced in the main conversation with the remaining findings inlined.
- Final summary at the end listing everything modified and pointing at the backlogged-reviews file.
- The user is never asked to run analyzer, tests, or git commands on behalf of the orchestrator. Analyzer/lint is owned by the implementer and fixer agents. Git is owned by the user after the run.

**Acceptance-by-feel:**
- A single `/implement` run feels noticeably faster and cheaper than the current headless-based run for the same plan, because per-phase review is one agent instead of three.
- Spec drift caught per-phase surfaces as completeness findings, not as a flood of mixed code-review/security noise. Drift gets fixed in the same phase that introduced it, not at the end.
- When the final gate runs, it reads as "the single quality sweep of the whole run" — the user can scan its three reviewer outputs and understand the state of the codebase at end-of-plan.
- The backlogged-reviews file reads as a to-do list for later, not as a failure record. LOW findings are a real deliverable, not lost work.
- A future skill that wants to run "did this phase satisfy the spec?" review can dispatch `completeness-review-agent` directly without knowing anything about `/implement`.

---

## Pain Point

The current `/implement` orchestrator couples five heavyweight mechanisms that all need to cooperate for a phase to complete: headless `claude --bare` subprocess management, `--json-schema` structured output, a `tee`-piped `stream-filter.py` + `extract-result.py` pair, a JSON checkpoint file on disk, and a 3-reviewer parallel fan-out every single phase. Each mechanism has its own failure modes (subprocess crash, schema validation error, pipeline redirection breakage on certain shells, checkpoint drift vs plan identity, reviewer disagreement loops). The infrastructure cost of this coordination is high in tokens, high in wall-clock time, and high in cognitive load when any step fails. On top of that, the per-phase fan-out drowns completeness findings under code-quality and security findings — which is exactly the opposite of the priority ordering we want, because spec drift is the one class of finding that represents a broken *promise to the user* and should be surfaced and fixed immediately, before quality-of-implementation concerns are even evaluated.

## Target Shape

The new `/implement` is a thin dispatch orchestrator. The main conversation reads only plan metadata (phase names and line ranges from the header, or a `Grep` fallback for `## Phase N`), then dispatches every implementer, reviewer, and fixer via the `Agent` tool. There is no subprocess management, no JSON schema, no stdout pipeline, no checkpoint. Per phase, the orchestrator runs one reviewer — `completeness-review-agent` — and fixes every completeness finding of any severity until the reviewer returns clean. After every phase closes, a single final gate runs `completeness-review-agent`, `code-review-agent`, and `security-agent` in parallel as one orchestrator message; a narrow fixer receives every completeness finding plus the CRITICAL/HIGH/MEDIUM code-review and security findings; LOW code-review and LOW security findings are written to `.claude/backlogged_reviews/<plan-name>.md` as a deliverable for the user to handle later. Completeness findings are treated as sacred and never backlogged. The orchestrator's `Write` budget is one file (the backlogged-reviews file), its `Bash` budget is one command (`mkdir -p` the backlogged-reviews directory), and its `Read` budget is the plan header region only.

## Ambition Level

**Option:** Single skill, cleaned end-to-end (Option B from the options phase)
**Why this over the others:** Option A (surgical minimum) leaves harness residue visible in `worker-rules.md`, `reviewer-rules.md`, and `severity-standard.md` and leaves the duplicate `reference/` folder rotting, which creates a persistent confusion tax on every future contributor who reads those files. Option C (whole subsystem) drags `code-review-agent.md`, `security-agent.md`, `.claude/CLAUDE.md`, and a new cross-skill shared-rules directory into scope, which is broader than the actual problem — those agents already work fine as Agent-tool subagents today, and introducing a new directory convention invites scope creep toward a wider `.claude/` reorganization that the user didn't ask for. Option B touches exactly the files that need to change for the new workflow to land internally consistent, plus one neighbor skill (`writing-plans`) that has to know about the new plan-header requirement for the grep fallback to be a transitional path rather than a permanent one.
**Phase scope:** This spec is a single unit of work, not a multi-phase initiative. Writing-plans will decide whether to split it across phases for implementer dispatching, but the spec itself is one effort.

## Blast Radius Budget

- **Files touched:** 6 rewritten or edited, 5 files deleted + 1 folder deleted, 2 Python scripts under `.claude/tools/` deleted. The "In scope (v1)" list above is closed — touching anything not on that list is out of scope and should raise a review flag.
- **Behavior changes allowed:** Only the documented changes to how `/implement` executes. Implementer behavior inside a phase (what it reads, what it writes, how it runs lint) is not allowed to change. `completeness-review-agent`'s severity calibration is not allowed to change. `code-review-agent` and `security-agent` behavior is not allowed to change. `writing-plans` plan content format (phase bodies) is not allowed to change — only the plan header gains a new machine-readable line-range declaration block.

## Test Coverage Floor

- No automated test floor. `/implement` is not code that runs inside the app's test suite — it is a Claude Code skill definition file and supporting agent and rules files. Validation is by direct exercise: after the refactor lands, run `/implement` on a small, already-approved plan end-to-end and verify:
  - No `claude --bare` subprocess is launched.
  - No checkpoint file appears in `.claude/state/`.
  - The orchestrator never includes a plan phase body in its own context.
  - Per-phase review uses the completeness agent only.
  - The final gate runs three parallel reviewers.
  - The backlogged-reviews file is produced correctly and contains no completeness findings.
  - All dispatched agents run on `model: opus`.
- Cross-check that `Grep` on `.claude/` returns zero matches for `--bare`, `--json-schema`, `stream-filter`, `extract-result`, `implement-checkpoint`, `checkpoint-template`, or `findings-schema` (except inside `.claude/plans/completed/2026-02-27-implement-skill-design.md`, which is frozen historical content).

## Open Questions / Deferred to Tailor

- Exact machine-readable format for the plan-header phase-range block that `writing-plans` will emit. Options: a markdown table, a fenced YAML block, or a fenced JSON block. The orchestrator's header parser has to match whatever shape `writing-plans` emits, so `tailor` should look at how `writing-plans` currently composes its plan header and pick the format that fits most naturally.
- Whether the `completeness-review-agent.md` refactor should move worker-rules and reviewer-rules to a shared location for genuine cross-skill reuse, or whether referencing them at their current `implement/references/` path is acceptable for v1. Defer to `tailor` to look at how many skills will actually dispatch the generic agent and how path-coupled that feels.
- The exact on-disk shape of the backlogged-reviews markdown file (section ordering, heading levels, whether to group LOW findings by file path or by reviewer). The spec fixes the content categories; `tailor` + `writing-plans` can pick the exact markdown layout.
- Whether `severity-standard.md`'s edits should be limited to the two harness-coupled lines, or whether a broader pass is warranted to reflect that LOW completeness findings are always fixed (a concept the file doesn't currently express). Defer to `tailor`.
