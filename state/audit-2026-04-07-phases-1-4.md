# Design System Overhaul — Phases 1-4 Spec Compliance Audit
**Date:** 2026-04-07 | **Branch:** ui-design-system-refactor | **Verdict:** PARTIAL ~60%

## Top Blockers
1. custom_lint = 406 violations (388 ERROR). Top: no_raw_button (234), no_hardcoded_spacing (52), no_hardcoded_duration (28), no_raw_divider (22), no_raw_dropdown (13), no_raw_tooltip (6), prefer_design_system_banner (6), no_raw_alert_dialog (1), no_raw_show_dialog (1).
2. DesignConstants.(space|radius|animation|elevation) in widget code: 613 refs in 104 lib/features files + 8 in lib/shared/widgets/permission_dialog.dart. Spec §2 lines 87-90 require migration to FieldGuideSpacing.of(context).* etc. Session 747 missed this entire class.
3. 30 UI files >300 lines (mdot_hub 1104, project_setup 789, contractor_editor 677, home 519, entry_contractors 586, entry_quantities 489, entries_list 462, project_contractors_tab 460, project_dashboard 443, company_setup 442, hub_proctor 432, form_viewer 426, settings 420, trash 397, mp_import_preview 370, entry_forms 356, pdf_import_preview 348, personnel_types 346, pay_app_date_range 337, member_detail 334, photo_detail 328, forms_list 314, quantity_calculator 312, home_calendar 311, entry_photos 311, entry_header 311, budget_items 306, hub_compact_accordion 305, otp_verification 303, gallery 301).
4. 56 files still import legacy theme shim paths (core/theme/{colors,design_constants,field_guide_colors}.dart).
5. Widgetbook skeleton only (8 use cases total — layout + animation only). Missing atoms, molecules, organisms, surfaces, feedback, feature widgets.

## Phase-by-Phase Completion
- P1 Tokens + Theme: ~90% (app_theme 396 lines, HC removed cleanly, 4 leftover DesignConstants inside app_theme)
- P2 Responsive + Animation + Nav + Widgetbook: ~55% (all widgets exist, Widgetbook skeleton, AppStaggeredList used in only 5 files)
- P3 Design system expansion: ~85% (all files present, shim typedefs done, but stale_config_warning.dart + version_banner.dart not deleted)
- P4 UI decomposition + tokenization + sliver-ify + Selector-ify: ~40%

## Success Criteria Status
| # | Criterion | Status |
|---|---|---|
| 1 | Zero hardcoded Colors/BorderRadius/EdgeInsets/TextStyle | PARTIAL (literals clean, but 770 DesignConstants widget refs) |
| 2 | app_theme.dart <400 lines | PASS (396) |
| 3 | All tokens via ThemeExtension with density variants | PARTIAL (tokens exist, not used in widgets) |
| 4 | Density auto, no Settings toggle | PASS |
| 5 | Responsive breakpoint + canonical layouts | PARTIAL (12 of ~13 screens use AppResponsiveBuilder) |
| 6 | No UI file >300 lines | FAIL (30 files) |
| 7 | 11 GitHub issues closed | PARTIAL (5 pass, 3 partial, 1 fail, 2 unverified) |
| 8 | Widgetbook catalog | FAIL (skeleton only) |
| 9 | DevTools no frame budget violations | FAIL (Phase 5, not started) |
| 10 | Atomic folder structure ~56 components | PASS (~57) |
| 11 | Desktop hover/focus | PARTIAL (Phase 6) |
| 12 | 10 new lint rules at error severity in CI | PARTIAL (rules at ERROR in source, but 388 ERRORS currently firing) |
| 13 | .claude/ docs updated | FAIL |
| 14 | HTTP driver + logging updated | FAIL |

## GitHub Issue Status
| # | Title | Status |
|---|---|---|
| 165 | RenderFlex overflow in project setup | PARTIAL (project_setup still 789 lines, decomp incomplete) |
| 199 | Review Drafts no delete action | FAIL (never implemented) |
| 200 | Review Drafts tile-card style | PARTIAL |
| 201 | Android keyboard blocks buttons | PASS (claimed) |
| 202 | Quantity picker search not cleared | PASS (claimed) |
| 203 | Quantities + button workflow | PASS (claimed) |
| 207 | Dashboard empty-state contrast | PASS (code cited) |
| 208 | Dashboard gradient out of place | PASS (code cited) |
| 209 | Forms list shows internal ID | NOT VERIFIED |
| 233 | Dashboard/calendar/projects button consistency | PARTIAL |
| 238 | no_inline_text_style 6 violations | PARTIAL (still reports 6) |

## custom_lint Top Offending Files
1. manual_match_editor.dart — 12
2. company_setup_screen.dart — 9 (owned by agent 5)
3. trash_screen.dart — 8 (owned by agent 5)
4. entry_forms_section.dart — 7 (owned by agent 4)
5. settings_screen.dart — 7 (owned by agent 5)
6. pay_application_detail_screen.dart — 6
7. member_detail_sheet.dart — 6 (owned by agent 5)
8. sign_out_dialog.dart — 6
9. otp_verification_screen.dart — 6 (owned by agent 5)
10. forms_list_screen.dart — 6 (owned by agent 1)
11. entry_quantities_section.dart — 6 (owned by agent 4)
12. entries_list_screen.dart — 6 (owned by agent 3)
13. personnel_types_screen.dart — 6 (owned by agent 5)
14. contractor_editor_widget.dart — 5 (owned by agent 4)
15. scaffold_with_nav_bar.dart — 5 (core/router, NOT owned)
16. mdot_hub_screen.dart — 5 (owned by agent 1)
17. permission_dialog.dart — 5 (shared/widgets, NOT owned)
18. pay_applications/contractor_comparison_pdf_exporter.dart — 6 (pw. package, false positive)

## Outstanding Work Outside In-Flight Agents
- Wave B1 core infra: scaffold_with_nav_bar.dart, app_router.dart, permission_dialog.dart, stale_config_warning.dart, version_banner.dart
- Wave B2 pay_applications feature
- Wave B3 pdf presentation (pdf_import_preview, mp_import_preview, helpers, widgets)
- Wave B4 quantities feature (bid_item_detail_sheet, quantity_calculator_screen, bid_item_card, etc.)
- Wave B5 forms widgets not owned (hub_compact_accordion 305, hub_header_content, hub_quick_test_content, form_accordion, form_thumbnail, form_viewer_sections, form_viewer_action_bar, forms_list_screen if not owned)
- Wave B6 dashboard widgets not owned (budget_overview_card, weather_summary_card, tracked_item_row, dashboard_stat_card, drafts_pill, alert_item_row, todays_entry_card)
- Wave B7 auth screens not owned (login, register, forgot_password, profile_setup, account_status, pending_approval, update_password, update_required, legal_document)
- Wave B8 settings not owned (consent_screen, help_support, edit_profile, admin_dashboard, sync_section, admin_dashboard_widgets, section_header, sign_out_dialog, clear_cache_dialog)
- Wave B9 calculator + todos + contractors + gallery + photos + toolbox + sync presentation + analytics + locations + weather widgets
- Wave C docs: CLAUDE.md, directory-reference.md, architecture.md, architecture-guide, worker-rules, reviewer-rules
- Wave D Widgetbook population for all atomic dirs + key feature widgets
- Wave E HTTP driver breakpoint/density/animation-aware diagnostics
- Wave F Logger.ui category + instrumentation
- Wave G golden test README cleanup + obsolete HC baselines
- Wave H Selector migration across features (Consumer 37 vs Selector 23)
- Wave I stale import migration (56 files)
- Wave J app_router.dart 2 hardcoded Duration fix
- Wave K dart run custom_lint to zero + verify NO // ignore / suppressions added
- Wave L flutter analyze to zero (136 info, 0 errors — mostly prefer_const + unnecessary_import for stale shims)
