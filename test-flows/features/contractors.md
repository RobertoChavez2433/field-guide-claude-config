# Feature: contractors

## Purpose
Contractors covers contractor selection and contractor/equipment/personnel edges that are surfaced from project setup and entries.

## Screens
- contractor-selection: `lib/features/contractors/presentation/screens/contractor_selection_screen.dart`

## Preconditions catalog
- `base_data`: seeds the harness project graph.
- `contractor_a`: seeds a default contractor.

## Sub-flows
```yaml
- name: forward_happy
  requires: [contractor_a]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { find: contractor_selection_screen } ]
- name: backward_traversal
  requires: [contractor_a]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: contractor_selection_screen }, { navigate: /project/harness-project-001/edit } ]
- name: nav_bar_switch_mid_flow
  requires: [contractor_a]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: contractor_selection_screen }, { navigate: /settings } ]
- name: back_at_root
  requires: [contractor_a]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: contractor_selection_screen } ]
- name: deep_link_entry
  requires: [contractor_a]
  appliesTo: { roles: [admin, inspector], devices: [s21, s10] }
  steps: [ { find: contractor_selection_screen } ]
- name: orientation_change
  requires: [contractor_a]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: contractor_selection_screen } ]
```

## Retired flow IDs
- T17
- T18
- T19
- T69
- T70
