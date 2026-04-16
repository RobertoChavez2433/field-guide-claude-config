# Feature: calculator

## Purpose
Calculator owns HMA/concrete tabs and quantity-calculator tab preservation.

## Screens
- calculator: `lib/features/calculator/presentation/screens/calculator_screen.dart`

## Preconditions catalog
- `base_data`: seeds the harness project graph.

## Sub-flows
```yaml
- name: forward_happy
  requires: [base_data]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /calculator }, { find: calculator_screen } ]
- name: backward_traversal
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: calculator_screen }, { navigate: /toolbox } ]
- name: nav_bar_switch_mid_flow
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: calculator_screen }, { navigate: /settings } ]
- name: back_at_root
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /calculator }, { find: calculator_screen } ]
- name: deep_link_entry
  requires: [base_data]
  appliesTo: { roles: [admin, inspector], devices: [s21, s10] }
  steps: [ { navigate: /calculator }, { find: calculator_screen } ]
- name: tab_switch_mid_edit
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { tap: calculator_hma_tab }, { tap: calculator_concrete_tab } ]
- name: orientation_change
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: calculator_screen } ]
```

## Retired flow IDs
- T38
- T39
