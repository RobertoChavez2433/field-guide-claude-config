# Feature: quantities

## Purpose
Quantities owns bid item import, quantity calculator entry, quantity edits, and quantity export assertions.

## Screens
- quantities: `lib/features/quantities/presentation/screens/quantities_screen.dart`
- quantity-calculator: `lib/features/quantities/presentation/screens/quantity_calculator_screen.dart`

## Preconditions catalog
- `base_data`: seeds the harness project graph.
- `entry_draft`: seeds a draft entry for calculator routes.

## Sub-flows
```yaml
- name: forward_happy
  requires: [base_data]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /quantities }, { find: quantities_screen } ]
- name: backward_traversal
  requires: [entry_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /quantity-calculator/harness-entry-001 }, { find: quantity_calculator_screen }, { navigate: /quantities } ]
- name: nav_bar_switch_mid_flow
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: quantities_screen }, { navigate: /projects } ]
- name: back_at_root
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /quantities }, { find: quantities_screen } ]
- name: deep_link_entry
  requires: [entry_draft]
  appliesTo: { roles: [admin, inspector], devices: [s21, s10] }
  steps: [ { navigate: /quantity-calculator/harness-entry-001 }, { find: quantity_calculator_screen } ]
- name: tab_switch_mid_edit
  requires: [entry_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: quantity_calculator_screen }, { tap: quantity_calculator_calculate_button } ]
- name: orientation_change
  requires: [entry_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: quantity_calculator_screen } ]
- name: export_verification
  requires: [base_data]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /quantities }, { find: quantities_screen }, { tap: pay_app_export_button } ]
```

## Retired flow IDs
- T20
- T21
- T61
- T73
