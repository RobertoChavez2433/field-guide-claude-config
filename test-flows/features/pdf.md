# Feature: pdf

## Purpose
PDF import owns bid-item and M&P preview UX. Deep-link entry to preview routes remains collapsed because production routes require `state.extra`; seed data backs post-import consumers instead.

## Screens
- pdf-import-preview: `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`
- mp-import-preview: `lib/features/pdf/presentation/screens/mp_import_preview_screen.dart`

## Preconditions catalog
- `pdf_import_result_staged`: seeds project/bid-item rows for post-import consumer routes.

## Sub-flows
```yaml
- name: forward_happy
  requires: [pdf_import_result_staged]
  appliesTo: { roles: [admin, engineer, officeTechnician], devices: [s21, s10] }
  steps: [ { find: pdf_preview_screen }, { tap: pdf_preview_select_all_button } ]
- name: backward_traversal
  requires: [pdf_import_result_staged]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: mp_preview_screen }, { back: true }, { find: quantities_screen } ]
- name: back_at_root
  requires: [pdf_import_result_staged]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: pdf_preview_screen }, { back: true } ]
- name: orientation_change
  requires: [pdf_import_result_staged]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: pdf_preview_screen } ]
- name: export_verification
  requires: [pdf_import_result_staged]
  appliesTo: { roles: [admin, engineer, officeTechnician], devices: [s21, s10] }
  steps: [ { find: pdf_preview_screen }, { tap: pdf_preview_import_button } ]
- name: role_restriction
  requires: [pdf_import_result_staged]
  appliesTo: { roles: [inspector], devices: [s21, s10] }
  steps: [ { navigate: /projects }, { find: project_list_screen } ]
```

## Retired flow IDs
- M03
- M04
