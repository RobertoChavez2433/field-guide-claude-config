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

## Design System Structure
`lib/core/design_system/` is organized atomically (~57 components after Phase 1-4 overhaul; see `.claude/state/audit-2026-04-07-phases-1-4.md` for the full audit). Two themes: light + dark (high-contrast removed).

| Subdirectory | Files | Purpose |
|--------------|-------|---------|
| `tokens/` | `design_constants.dart` (legacy fallbacks), `app_colors.dart`, `field_guide_colors.dart`, `field_guide_spacing.dart`, `field_guide_radii.dart`, `field_guide_motion.dart`, `field_guide_shadows.dart` | ThemeExtension tokens accessed via `FieldGuideSpacing.of(context)`, `FieldGuideRadii.of(context)`, `FieldGuideMotion.of(context)`, `FieldGuideShadows.of(context)`, `FieldGuideColors.of(context)` — single source of truth for spacing, radii, motion, shadows, colors |
| `atoms/` (11) | `app_avatar`, `app_badge`, `app_button`, `app_chip`, `app_divider`, `app_icon`, `app_mini_spinner`, `app_progress_bar`, `app_text`, `app_toggle`, `app_tooltip` | Primitive widgets |
| `molecules/` (8) | `app_counter_field`, `app_date_picker`, `app_dropdown`, `app_list_tile`, `app_search_bar`, `app_section_header`, `app_tab_bar`, `app_text_field` | Composed widgets |
| `organisms/` (12) | `app_action_card`, `app_form_field_group`, `app_form_section`, `app_form_section_nav`, `app_form_status_bar`, `app_form_summary_tile`, `app_form_thumbnail`, `app_glass_card`, `app_info_banner`, `app_photo_grid`, `app_section_card`, `app_stat_card` | Complex composed widgets |
| `surfaces/` (6) | `app_bottom_bar`, `app_bottom_sheet`, `app_dialog`, `app_drag_handle`, `app_scaffold`, `app_sticky_header` | Container surfaces |
| `feedback/` (7) | `app_banner`, `app_budget_warning_chip`, `app_contextual_feedback`, `app_empty_state`, `app_error_state`, `app_loading_state`, `app_snackbar` | User feedback widgets |
| `layout/` (5) | `app_adaptive_layout`, `app_breakpoint`, `app_responsive_builder`, `app_responsive_grid`, `app_responsive_padding` | Responsive primitives — Material 3 breakpoints (compact/medium/expanded/large) |
| `animation/` (4 + 4 helpers) | `app_animated_entrance`, `app_container_transform`, `app_staggered_list`, `app_tap_feedback`, `app_value_transition`, `motion_aware`, `shared_axis_transition_page` | Motion components honoring `FieldGuideMotion` and reduce-motion preference |

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
