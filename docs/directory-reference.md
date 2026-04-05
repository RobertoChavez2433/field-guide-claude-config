# .claude/ Directory Reference

## Directory Structure
| Directory | Purpose |
|-----------|---------|
| plans/ | Implementation plans (active in root, completed in completed/) |
| prds/ | Product Requirements Documents |
| specs/ | Design specifications from brainstorming skill |
| agents/ | Role-based agent definitions (10 files, all at root level) |
| skills/ | Skill definitions loaded on-demand |
| rules/ | Domain rules with `paths:` frontmatter for lazy loading |
| docs/ | Feature overviews, architecture docs, and guides loaded on demand |
| architecture-decisions/ | Feature-specific constraints + shared rules |
| state/ | JSON state files for project tracking |
| memory/ | Detailed project knowledge base (on-demand) |
| autoload/ | Hot session state loaded by `/resume-session` |
| agent-memory/ | Agent-specific persistent memory (auto-managed) |
| logs/ | Archives (state-archive, defects-archive, archive-index) |
| code-reviews/ | Code review reports (auto-saved by code-review-agent) |
| hooks/ | Pre-flight and post-work validation scripts |
| test-results/ | UI test findings per journey run |
| tailor/ | Codebase analysis output from /tailor skill (per-spec structured directories) |
| adversarial_reviews/ | Spec-level adversarial review reports |
| backlogged-plans/ | Deferred/future implementation plans |
| debug-sessions/ | Session logs from systematic debugging (gitignored, 30-day retention) |
| outputs/ | Audit output reports |
| user-notes/ | Raw user notes |
| spikes/ | Experimental / proof-of-concept work (not production code) |
| projects/ | Per-project memory directories (auto-managed by Claude) |
| settings.local.json | Local Claude settings override (gitignored) |

## Project-Level Tools
| Directory | Purpose |
|-----------|---------|
| `tools/debug-server/` | Node.js HTTP log server for debug sessions (receives structured JSON from Logger HTTP transport) |

## Documentation System
- `.claude/docs/` — Feature overviews + architecture docs loaded on demand after slim rule context
- `.claude/docs/guides/implementation/shared-analyzer-safe-patterns.md` — Cross-cutting analyzer-zero guidance for `SafeRow`, hook-based `SafeAction`, and repository/copyWith follow-through
- `.claude/architecture-decisions/` — Feature-specific constraints + shared rules
- `.claude/state/` — JSON state files; primary tracking via FEATURE-MATRIX.json (feature status) and PROJECT-STATE.json (blockers and priorities)
- Implementers and reviewers load slim domain rules first via `.claude/skills/implement/references/worker-rules.md` and `.claude/skills/implement/references/reviewer-rules.md`, then pull feature docs and PRDs as needed.

**Note**: `calculator`, `forms`, `gallery`, and `todos` are full standalone features with their own `lib/features/` directories, data layers, and presentation layers. `toolbox` is a navigation hub that routes to them but does not contain their implementation. Each may have separate doc files under `docs/features/`.

## Archives (On-Demand — NOT auto-loaded)
- `.claude/logs/state-archive.md` — Session history
- `.claude/logs/defects-archive.md` — Archived defect entries

## Planning Pipeline
`brainstorming` (spec) → `tailor` (research) → `writing-plans` (plan) → `implement` (execute)
