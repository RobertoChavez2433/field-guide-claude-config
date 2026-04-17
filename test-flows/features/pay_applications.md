# Feature: pay_applications

## Purpose
Pay applications own saved pay application detail, replacement/blocking cases, contractor comparison, and pay-app export verification.

## Screens
- pay-application-detail: `lib/features/pay_applications/presentation/screens/pay_application_detail_screen.dart`
- contractor-comparison: `lib/features/pay_applications/presentation/screens/contractor_comparison_screen.dart`

## Preconditions catalog
- `base_data`: seeds the harness project graph.
- `pay_app_draft`: seeds a saved pay application.

## Sub-flows
```yaml
- name: forward_happy
  requires: [pay_app_draft]
  appliesTo: { roles: [admin, engineer, officeTechnician], devices: [s21, s10] }
  steps: [ { navigate: /pay-app/harness-pay-app-001 }, { find: pay_app_detail_screen }, { tap: pay_app_compare_button }, { find: contractor_comparison_screen } ]
- name: backward_traversal
  requires: [pay_app_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /pay-app/harness-pay-app-001/compare }, { find: contractor_comparison_screen }, { back: true }, { find: pay_app_detail_screen } ]
- name: nav_bar_switch_mid_flow
  requires: [pay_app_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /pay-app/harness-pay-app-001 }, { find: pay_app_detail_screen }, { tap: pay_app_compare_button }, { find: contractor_comparison_screen }, { navigate: /settings }, { find: settings_screen } ]
- name: back_at_root
  requires: [pay_app_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /pay-app/harness-pay-app-001 }, { find: pay_app_detail_screen }, { back: true } ]
- name: deep_link_entry
  requires: [pay_app_draft]
  appliesTo: { roles: [admin, engineer, officeTechnician], devices: [s21, s10] }
  steps: [ { navigate: /pay-app/harness-pay-app-001 }, { find: pay_app_detail_screen } ]
- name: orientation_change
  requires: [pay_app_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: pay_app_detail_screen } ]
- name: export_verification
  requires: [pay_app_draft]
  appliesTo: { roles: [admin, engineer, officeTechnician], devices: [s21, s10] }
  steps: [ { find: pay_app_detail_screen }, { tap: pay_app_compare_button } ]
- name: role_restriction
  requires: [pay_app_draft]
  appliesTo: { roles: [inspector], devices: [s21, s10] }
  steps: [ { navigate: /pay-app/harness-pay-app-001 }, { find: project_dashboard_screen } ]
```

## Retired flow IDs
- T89
- P01
- P02
- P03
- P04
- P05
