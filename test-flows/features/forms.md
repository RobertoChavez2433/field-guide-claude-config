# Feature: forms

## Purpose
Forms owns gallery, MDOT form workflows, section-by-section completion, and editable AcroForm export verification through `PdfAcroFormInspector`.

## Screens
- form-gallery: `lib/features/forms/presentation/screens/form_gallery_screen.dart`
- mdot-hub: `lib/features/forms/presentation/screens/mdot_hub_screen.dart`
- form-viewer: `lib/features/forms/presentation/screens/form_viewer_screen.dart`
- form-pdf-preview: `lib/features/forms/presentation/screens/form_pdf_preview_screen.dart`

## Preconditions catalog
- `base_data`: seeds the harness project graph.
- `form_response_draft`: seeds an open form response.

## Sub-flows
```yaml
- name: forward_happy
  requires: [form_response_draft]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /forms }, { find: form_gallery_screen }, { navigate: /form/harness-response-001 }, { find: mdot_hub_screen } ]
- name: backward_traversal
  requires: [form_response_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: mdot_hub_screen }, { navigate: /forms } ]
- name: nav_bar_switch_mid_flow
  requires: [form_response_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /form/harness-response-001 }, { find: mdot_hub_screen }, { navigate: /settings } ]
- name: back_at_root
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /forms }, { find: form_gallery_screen } ]
- name: deep_link_entry
  requires: [form_response_draft]
  appliesTo: { roles: [admin, inspector], devices: [s21, s10] }
  steps: [ { navigate: /form/harness-response-001 }, { find: mdot_hub_screen } ]
- name: tab_switch_mid_edit
  requires: [form_response_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: mdot_hub_screen }, { tap: mdot_hub_save_button } ]
- name: orientation_change
  requires: [form_response_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: mdot_hub_screen } ]
- name: form_completeness
  requires: [form_response_draft]
  appliesTo: { roles: [admin, inspector], devices: [s21, s10] }
  steps: [ { find: mdot_hub_screen }, { tap: mdot_hub_save_button } ]
  assertions: [ { pdf_fields_populated: true }, { pdf_is_acroform: true } ]
- name: export_verification
  requires: [form_response_draft]
  appliesTo: { roles: [admin, inspector], devices: [s21, s10] }
  steps: [ { find: mdot_hub_screen }, { tap: mdot_hub_pdf_button } ]
```

## Retired flow IDs
- T35
- T36
- T37
- T43
- T74
- M09
