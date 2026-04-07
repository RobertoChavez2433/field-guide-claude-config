# Session State

**Last Updated**: 2026-04-06 | **Session**: 747

## Current Phase
- **Phase**: Design System Overhaul implementation on branch `ui-design-system-refactor`
- **Status**: Phases 0-4a fully implemented with reviews. Phase 4b partially done (4.8-4.12 + 5 of 10 screens in 4.13). Massive spec-drift cleanup wave executed mid-session after user flagged quality gate failures. Big god-class screens now decomposed. Spec still has real gaps — full re-audit against spec intent is the first action next session.

## HOT CONTEXT - Resume Here

### What Was Done This Session (747)

**Plan**: `.claude/plans/2026-04-06-design-system-overhaul.md` (12,958 lines, 8 phases)
**Spec**: `.claude/specs/2026-04-06-design-system-overhaul-spec.md`
**Branch**: `ui-design-system-refactor` (off main)

**Phases implemented (implementer + completeness + code-review, security batched per user preference):**
- **Phase 0 (Lint Rules)** — 10 rules created, tests, architecture_rules.dart registration. All reviewers APPROVE.
- **Phase 1 (Tokens + Theme + HC Removal + Folder Structure)** — 5 ThemeExtensions, HC theme removed, tokens/ folder created. Fixer addressed silent catch + deprecation annotations.
- **Phase 2 (Responsive + Animation + Navigation + Widgetbook)** — AppBreakpoint, AppAdaptiveLayout, AppResponsiveBuilder, MotionAware-aware animation atoms, NavigationRail shell, Widgetbook skeleton, density reactivity via MaterialApp.builder.
- **Phase 3 (Design System Expansion)** — Split into 4 batches A/B/C/D due to size. All 11 sub-phases done. Atomic folders fully populated (atoms 11, molecules 8, organisms 12, surfaces 6, feedback 7). Shared widget migrations complete with @Deprecated typedef shims (SnackBarHelper, ContextualFeedbackOverlay, SearchBarField). AppDialog.showConfirmation/showDeleteConfirmation/showUnsavedChanges merged.
- **Phase 4a (Decomposition screens 1-6)** — Dispatched as 6 per-screen parallel agents. All 6 screens landed (entry_editor, project_setup, home_screen, mdot_hub, project_list, contractor_editor_widget). Post-phase fixer addressed 2 mediums (hub_proctor_content delegation, sliver-compatible stagger) and 2 lows.
- **Phase 4b partial (sub-phases 4.8-4.12 + 4.13 partial)**:
  - 4.8 todos_screen — DONE
  - 4.9 calculator_screen — DONE
  - 4.10 project_dashboard_screen — DONE
  - 4.11 quantity_calculator_screen — DONE
  - 4.12 form_viewer_screen — DONE
  - 4.13 bulk tokenization — PARTIAL: gallery, entries_list, quantities, pdf_import_preview, admin_dashboard decomposed in parallel. NOT DONE: settings_screen, company_setup, trash_screen, mp_import_preview, personnel_types_screen (these 5 sub-steps of 4.13 remain).
  - 4.14 (Additional Widgets Tokenization) — NOT STARTED
  - 4.15 (Remaining GitHub Issues) — PARTIALLY DONE (issues landed during tokenization/decomposition waves, see below)
  - 4.16 (Shared Widget Replacements) — NOT STARTED
- **Phase 5 (Performance)** — NOT STARTED
- **Phase 6 (Polish)** — PARTIAL (app_theme.dart already reduced, lint severities flipped)

**MID-SESSION SPEC-DRIFT CLEANUP (after user flagged that earlier agents were declaring "done" while skipping spec criteria):**

Comprehensive read-only spec audit was dispatched. Results were brutal: 602 DesignConstants refs across 113 presentation files, 124 raw BorderRadius.circular, 182 raw SizedBox magic numbers, 30 design_system files on theme shim, app_theme.dart 626 lines, broken form_sub_screens_test.dart, 10/11 GitHub issues unfixed, 7 of 10 lint rules still at WARNING.

**Cleanup waves dispatched:**

Wave 1 (small foundation fixes, all verified via direct grep):
1. DS theme shim removal — 31 design_system files migrated from `../../theme/` to `../tokens/` — VERIFIED 0 remaining
2. form_sub_screens_test.dart imports fixed — VERIFIED
3. Deprecated HC testing keys deleted (settingsThemeHighContrast) — VERIFIED
4. Inline TextStyle removed from app_snackbar.dart + app_badge.dart — VERIFIED

Wave 2 (5 large feature tokenization passes, parallel, verified via grep):
- entries — clean (4 categories 0 raw)
- forms — clean
- projects — clean
- contractors — clean
- pay_applications — needed round-2 (dialog BorderRadius missed first pass) — eventually clean

Wave 3 (9 remaining features + shared/widgets, parallel, verified):
- pay_applications r2 — clean
- quantities + pdf — clean
- settings + dashboard — clean
- auth + todos + gallery — clean
- photos + sync + calculator + toolbox + locations + weather + shared/widgets — clean

Final repo-wide grep confirmed every Flutter widget file is free of raw `BorderRadius.circular(N)`, raw `EdgeInsets.*(N)`, raw `SizedBox(w/h: N)`, inline `TextStyle(`. Remaining matches are:
- `lib/core/theme/app_theme.dart` TextStyles inside actual ThemeData builder — legitimate theme construction
- 6 tiny 2px nudges in design_system tiles (SizedBox height:2, EdgeInsets.all(2), BorderRadius.circular(2) drag handle)
- `contractor_comparison_pdf_exporter.dart` — uses `pw.` prefix (package:pdf, not Flutter widgets) — false positive

Wave 4 (7 parallel agents: 5 god-class decompositions + app_theme cleanup + lint severity flip):
- entry_editor_screen.dart: 1384 → **205 lines** ✅ (extracted 8 files: mixins, dialogs, helpers, actions, body)
- project_list_screen.dart: 892 → **247 lines** ✅ (project_card 371 → 266)
- quantities_screen.dart: 577 → **235 lines** ✅ (github #202/#203 addressed)
- todos_screen.dart: 505 → **285 lines** ✅
- mdot_hub_screen.dart: 1304 → **1104 lines** — STILL OVER CAP; agent says remaining bulk is state logic and recommends MdotHubController/ChangeNotifier extraction
- app_theme.dart: 626 → **396 lines** ✅ (split AppColorSchemes out; deleted 63 deprecated re-exports)
- Lint severity flip: 7 rules WARNING → ERROR. no_raw_navigator stays INFO per spec line 271. `dart run custom_lint` has NOT been run to verify zero new violations surface from the flip — MUST DO NEXT SESSION.

### GitHub Issues Status

| # | Topic | Status |
|---|---|---|
| 238 | Inline TextStyle in pay_applications | **CLOSED** (verified by grep) |
| 165 | RenderFlex overflow in project setup | **ADDRESSED** by project decomposition |
| 202 | Quantity picker search not cleared | **ADDRESSED** in quantities decomp (per-invocation search controller) |
| 203 | Quantities `+` button workflow | **ADDRESSED** in quantities decomp (AppButton.secondary + showBidItemPickerSheet) |
| 209 | Forms list shows internal ID | **ADDRESSED** in forms tokenization (entry/date labeling) |
| 208 | Dashboard gradient out of place | **ADDRESSED** in 4.10 (colorScheme.surface replacement) |
| 207 | Dashboard empty-state contrast | **ADDRESSED** in 4.10 (AppButton.primary) |
| 233 | Dashboard/calendar/projects button consistency | **PARTIALLY ADDRESSED** — needs final verification |
| 199 | Review Drafts no delete action | **NOT DONE** — deferred by 4.10 agent (noted as entries-feature scope) |
| 200 | Review Drafts tile-card style | **PARTIALLY** — DraftsPill extracted in 4.10 |
| 201 | Android keyboard blocks buttons | **ADDRESSED** by Phase 2 responsive layout (resizeToAvoidBottomInset) |

### What Needs to Happen Next (SESSION 748+)

**PRIORITY 1 — Spec re-audit of Phases 1-4**
- Dispatch a read-only audit agent against `.claude/specs/2026-04-06-design-system-overhaul-spec.md` checking ALL Phase 1-4 intent:
  - Tokens (Section 2): every ThemeExtension wired, density variants correct, static fallback boundary respected
  - Responsive (Section 3): breakpoints, canonical layouts, component discovery gate
  - State/Performance (Section 4): Selector usage, sliver migration coverage, RepaintBoundary placement
  - Animation (Section 5): MotionAware honored, all 7 animation components present and used
  - Decomposition (Section 6): every priority file under 300 lines, protocol followed, GitHub issues closed
  - Components (Section 7): ~56 components present, atomic folder structure matches target exactly
  - Docs (Section 8): architecture.md, directory-reference.md, driver updates, logging updates, golden tests, widgetbook
  - Cleanup checklist per phase
- Re-run the violation inventory grep (Colors/BorderRadius/EdgeInsets/SizedBox/TextStyle/DesignConstants)
- Cross-check every "ADDRESSED" / "PARTIAL" claim in the table above against the actual code

**PRIORITY 2 — Finish remaining god-class decompositions (target < 300 lines each)**
Remaining UI files > 300 lines (post wave 4):
- mdot_hub_screen.dart (1104) — needs MdotHubController state extraction
- contractor_editor_widget.dart (677)
- entry_contractors_section.dart (586)
- home_screen.dart (519) — was 520 pre-cleanup; verify
- entry_quantities_section.dart (~489, was 512)
- entries_list_screen.dart (462)
- project_contractors_tab.dart (460)
- project_dashboard_screen.dart (443)
- company_setup_screen.dart (442)
- hub_proctor_content.dart (432)
- form_viewer_screen.dart (426)
- settings_screen.dart (420)
- trash_screen.dart (397)
- mp_import_preview_screen.dart (370)
- entry_forms_section.dart (356)
- pdf_import_preview_screen.dart (348)
- personnel_types_screen.dart (346)
- member_detail_sheet.dart (334)
- photo_detail_dialog.dart (328)
- forms_list_screen.dart (314)
- quantity_calculator_screen.dart (312)
- home_calendar_section.dart (311)
- entry_photos_section.dart (311)
- entry_header_card.dart (311)
- budget_items_section.dart (306)
- otp_verification_screen.dart (303)
- gallery_screen.dart (301)

**NEW QUALITY GATE (user directive, 2026-04-06 session 747):** during further decomposition, NO method or helper may exceed 400 lines. Apply this as a hard cap on extracted widgets/mixins too — if an extraction produces a 400+ line method, it must be re-extracted.

**PRIORITY 3 — Finish Phase 4b sub-phases**
- 4.13 remaining screens: settings_screen, company_setup, trash_screen, mp_import_preview, personnel_types_screen (these overlap with Priority 2 decomposition work — kill two birds)
- 4.14 Additional Widgets Tokenization
- 4.15 Remaining GitHub Issues — #199, #200, #233 need final verification; #199 draft-delete-action still open
- 4.16 Shared Widget Replacements

**PRIORITY 4 — Verify lint severity flip doesn't surface new custom_lint errors**
- Run `dart run custom_lint` in the app directory after all decomposition completes
- Any new violations from the flipped rules must be fixed (no rolling back severity)

**PRIORITY 5 — Phase 5 Performance**
- Profile 5 worst screens with DevTools
- Fix bottlenecks, systematic pattern pass, re-profile

**PRIORITY 6 — Phase 6 Polish**
- Widgetbook completion (full component catalog + key feature widgets)
- Desktop hover/focus indicators on all interactive components
- Architecture documentation updates (.claude/docs/)
- HTTP driver + logging updates for new component structure
- Golden baselines regenerated for all components
- ONE comprehensive security pass (user deferred security reviews to end)

### Active Agent Checkpoint

`.claude/state/implement-checkpoint.json` was initialized at the start of session but has not been updated for mid-session cleanup waves. Treat `_state.md` as the authoritative source.

### User Preferences (critical — do NOT violate in session 748+)

- **NO headless mode** — do NOT use `claude --bare` / `claude -p` headless dispatches for the implement skill. The implement skill's default headless pattern is explicitly disabled for this run. Use the Agent tool (subagent_type: general-purpose, code-fixer-agent, completeness-review-agent, code-review-agent) for ALL dispatches (implementers, fixers, reviewers, audits). Headless redirection was unreliable on Windows AND the user wants visibility in the live session.
- **NO security reviews until implementation complete** — one comprehensive security pass at the very end of Phase 6. Do not dispatch security-agent per-phase.
- **SPEC AUDITING until implementation complete** — run a read-only spec audit after each major wave (tokenization, decomposition, phase completion) and compare results against `.claude/specs/2026-04-06-design-system-overhaul-spec.md` Section 1 Success Criteria + Section 10 Cleanup Checklist + Section 12 Violation Inventory. Do NOT rely on agent self-reports for spec compliance.
- **NO more reviews mid-phase EXCEPT spec audits** — implementer + fixer + spec audit loop only. No completeness/code-review/security reviews during implementation.
- **NO more agents declaring "done" without verification** — every agent claim must be verified with direct grep by the orchestrator before being accepted.
- **NO 400+ line methods or helpers** — hard cap on extracted code (new this session)
- **NO // ignore lint comments**
- **NO destructive git commands** on directories
- **Commit every session** — even WIP on feature branch
- **All review findings must be fixed**, not just blocking
- **Fresh test projects only** during test runs
- **Verify before editing** — root cause, not speculative

### Key File Locations

- Branch: `ui-design-system-refactor`
- Plan: `.claude/plans/2026-04-06-design-system-overhaul.md`
- Spec: `.claude/specs/2026-04-06-design-system-overhaul-spec.md`
- Token files: `lib/core/design_system/tokens/{app_colors,design_constants,field_guide_colors,field_guide_spacing,field_guide_radii,field_guide_motion,field_guide_shadows}.dart`
- Theme shim (still present for feature-layer consumers): `lib/core/theme/{colors,design_constants,field_guide_colors,theme,app_theme}.dart`
- Atomic folders: `lib/core/design_system/{atoms,molecules,organisms,surfaces,feedback,layout,animation}/`
- Lint rules: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_*.dart`
- Widgetbook: `widgetbook/` (skeleton only — Phase 6 expansion)

## Blockers

### BLOCKER-37: Delete orchestration drift (sync-engine-refactor branch, different feature)
**Status**: OPEN — paused while design system overhaul is in flight

### BLOCKER-34: Item 38 — Superscript `th` → `"` (#91) — OPEN (parked)
### BLOCKER-36: Item 130 — Whitewash destroys `y` descender (#92) — OPEN (parked)
### BLOCKER-28: SQLite Encryption (sqlcipher) (#89) — OPEN

## Recent Sessions

### Session 747 (2026-04-06) — Design System Overhaul implementation (this session)
**Work**: Phases 0-4a fully implemented with review/fix loops. Phase 4b partial (4.8-4.12 + 4.13 partial). User flagged mid-session that agents were declaring "done" while skipping spec criteria — dispatched comprehensive spec audit then 4 cleanup waves (foundation + 2 tokenization + 5 decomposition). Cleared all raw Colors/BorderRadius/EdgeInsets/SizedBox/TextStyle violations across all features. app_theme.dart 626→396. 7 lint rules flipped to ERROR. Massive god-class reductions: entry_editor 1384→205, project_list 892→247, quantities 577→235, todos 505→285. mdot_hub partially (1304→1104, needs controller extraction).
**Decisions**: Spec is the authoritative quality gate, not agent self-reports. Every agent claim must be verified with direct grep. NO 400+ line method/helper cap applied going forward. Security reviews batched to end of run.
**Next**: Full spec re-audit Phases 1-4, finish remaining god-class decompositions under new 400-line-method cap, finish Phase 4b, run custom_lint to verify flipped severities, Phase 5, Phase 6.

### Session 746 (2026-04-06, Codex) — Sync delete-orchestration (different branch, paused)
### Session 745 (2026-04-06, Codex) — OCR runtime page-local bottleneck (different branch)
### Session 744 (2026-04-06, Codex) — Pay-app/sync hardening migration (different branch)
### Session 743 (2026-04-06, Codex) — OCR runtime worker refactor (different branch)
### Session 742 (2026-04-06) — 12-agent adversarial review of design system plan
### Session 741 (2026-04-06, Codex) — Android PDF diagnostics

## Test Results

### Flutter Unit Tests (last known good, S726)
- **Full suite**: 3784 pass / 2 fail (pre-existing: OCR test + DLL lock)
- **Analyze**: 0 issues
- **Database tests**: 65 pass, drift=0
- **Sync tests**: 704 pass

### Session 747 analyzer status
- `flutter analyze` on individual feature folders: 0 errors throughout cleanup waves
- Full-repo analyze NOT run after final wave 4 — should be first verification next session
- `dart run custom_lint` NOT run after severity flip — MUST run next session to verify zero new violations

## Reference
- **PR #140**: OPEN (7-issue fix)
- **GitHub Issues**: #89 (sqlcipher), #91-#92 (OCR), #127-#129 (enhancements); design system issues see table above
