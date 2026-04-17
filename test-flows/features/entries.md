# Feature: entries

## Purpose
Entries owns daily entry creation, editing, review/submit lifecycle, entry PDF export, attached photos, and field-data navigation edges.

## Screens
- entries-list: `lib/features/entries/presentation/screens/entries_list_screen.dart`
- drafts-list: `lib/features/entries/presentation/screens/drafts_list_screen.dart`
- entry-editor: `lib/features/entries/presentation/screens/entry_editor_screen.dart`
- entry-review: `lib/features/entries/presentation/screens/entry_review_screen.dart`
- review-summary: `lib/features/entries/presentation/screens/review_summary_screen.dart`
- entry-pdf-preview: `lib/features/entries/presentation/screens/entry_pdf_preview_screen.dart`

## Preconditions catalog
- `base_data`: seeds the harness project graph.
- `entry_draft`: seeds a draft daily entry.
- `entry_submitted`: seeds a submitted daily entry.

## Sub-flows
```yaml
- name: forward_happy
  requires: [entry_draft]
  appliesTo: { roles: [admin, engineer, officeTechnician], devices: [s21, s10] }
  steps: [ { navigate: /entries }, { find: entries_list_screen }, { tap: entries_list_filter_button }, { navigate: /entry/harness-project-001/2026-04-16 }, { find: entry_editor_screen } ]
- name: backward_traversal
  requires: [entry_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /review-summary }, { find: review_summary_screen }, { back: true }, { find: entries_list_screen } ]
- name: nav_bar_switch_mid_flow
  requires: [entry_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /entry/harness-project-001/2026-04-16 }, { find: entry_editor_screen }, { tap: entry_wizard_save_draft }, { navigate: /settings }, { find: settings_screen } ]
- name: back_at_root
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /entries }, { find: entries_list_screen }, { back: true } ]
- name: deep_link_entry
  requires: [entry_draft]
  appliesTo: { roles: [admin, engineer, officeTechnician], devices: [s21, s10] }
  steps: [ { navigate: /entry/harness-project-001/2026-04-16 }, { find: entry_editor_screen } ]
- name: tab_switch_mid_edit
  requires: [entry_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /entry/harness-project-001/2026-04-16 }, { find: entry_editor_screen }, { tap: entry_wizard_save_draft }, { navigate: /projects }, { find: project_list_screen } ]
- name: orientation_change
  requires: [entry_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: entry_editor_screen } ]
- name: export_verification
  requires: [entry_submitted]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /report/harness-entry-001 }, { find: entry_editor_screen }, { tap: report_export_pdf_button } ]
- name: role_restriction
  requires: [entry_draft]
  appliesTo: { roles: [inspector], devices: [s21, s10] }
  steps: [ { navigate: /entries }, { find: entries_list_screen } ]
```

## Retired flow IDs
- T15
- T16
- T22
- T23
- T24
- T25
- T26
- T27
- T28
- T29
- T30
- T41
- T42
- T62
- T63
- T64
- T68
- T86
- T87
- M05
- M12
- M13
