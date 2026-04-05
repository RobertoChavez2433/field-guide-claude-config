# .claude/ Directory Reference

## Directory Structure
| Directory | Purpose |
|-----------|---------|
| plans/ | Implementation plans (active in root, completed in completed/) |
| prds/ | Product Requirements Documents |
| specs/ | Design specifications from brainstorming skill |
| agents/ | Agent definitions (10 agents, all at root level) and `*.memory.md` companion files |
| skills/ | Skill definitions loaded on-demand |
| rules/ | Domain rules with `paths:` frontmatter for lazy loading |
| docs/ | Feature overviews + architecture docs (lazy-loaded by agents) |
| architecture-decisions/ | Feature-specific constraints + shared rules |
| state/ | JSON state files for project tracking |
| defects/ | Per-feature defect tracking (max 5 per feature) |
| memory/ | Detailed project knowledge base (on-demand) |
| autoload/ | Hot session state loaded by `/resume-session` |
| agent-memory/ | Agent-specific persistent memory (auto-managed) |
| logs/ | Archives (state-archive, defects-archive, archive-index) |
| code-reviews/ | Code review reports (auto-saved by code-review-agent) |
| hooks/ | Pre-flight and post-work validation scripts |
| test-results/ | UI test findings per journey run |
| tailor/ | Codebase analysis output from /tailor skill (per-spec structured directories) |
| dependency_graphs/ | Legacy — CodeMunch analysis (superseded by tailor/) |
| adversarial_reviews/ | Spec-level adversarial review reports |
| backlogged-plans/ | Deferred/future implementation plans |
| debug-sessions/ | Session logs from systematic debugging (gitignored, 30-day retention) |
| outputs/ | Audit output reports |
| user-notes/ | Raw user notes |
| context-bundles/ | Pre-built context snapshots for fast agent loading |
| spikes/ | Experimental / proof-of-concept work (not production code) |
| projects/ | Per-project memory directories (auto-managed by Claude) |
| settings.local.json | Local Claude settings override (gitignored) |

## Project-Level Tools
| Directory | Purpose |
|-----------|---------|
| `tools/debug-server/` | Node.js HTTP log server for debug sessions (receives structured JSON from Logger HTTP transport) |

## Documentation System
- `.claude/docs/` — Feature overviews + architecture docs (lazy-loaded by agents)
- `.claude/docs/guides/implementation/shared-analyzer-safe-patterns.md` — Cross-cutting analyzer-zero guidance for `SafeRow`, hook-based `SafeAction`, and repository/copyWith follow-through
- `.claude/architecture-decisions/` — Feature-specific constraints + shared rules
- `.claude/state/` — JSON state files; primary tracking via FEATURE-MATRIX.json (feature status) and PROJECT-STATE.json (blockers and priorities)
- Agents load feature docs on demand via FEATURE-MATRIX.json (feature status and doc paths) and PROJECT-STATE.json (blockers and priorities).

**Note**: `calculator`, `forms`, `gallery`, and `todos` are full standalone features with their own `lib/features/` directories, data layers, and presentation layers. `toolbox` is a navigation hub that routes to them but does not contain their implementation. Each may have separate doc files under `docs/features/`.

## Archives (On-Demand — NOT auto-loaded)
- `.claude/logs/state-archive.md` — Session history
- `.claude/logs/defects-archive.md` — Archived defect entries

## Planning Pipeline
`brainstorming` (spec) → `tailor` (research) → `writing-plans` (plan) → `implement` (execute)
