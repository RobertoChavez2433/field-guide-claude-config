# Feature: toolbox

## Purpose
Toolbox owns the top-level tool launcher and proves cross-tool navigation remains stable.

## Screens
- toolbox-home: `lib/features/toolbox/presentation/screens/toolbox_home_screen.dart`

## Preconditions catalog
- `base_data`: seeds the harness project graph.

## Sub-flows
```yaml
- name: forward_happy
  requires: [base_data]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /toolbox }, { find: toolbox_home_screen } ]
- name: backward_traversal
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /calculator }, { find: calculator_screen }, { navigate: /toolbox } ]
- name: nav_bar_switch_mid_flow
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: toolbox_home_screen }, { navigate: /settings } ]
- name: back_at_root
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /toolbox }, { find: toolbox_home_screen } ]
- name: deep_link_entry
  requires: [base_data]
  appliesTo: { roles: [admin, inspector], devices: [s21, s10] }
  steps: [ { navigate: /toolbox }, { find: toolbox_home_screen } ]
- name: orientation_change
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: toolbox_home_screen } ]
```

## Retired flow IDs

