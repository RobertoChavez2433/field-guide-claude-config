# Feature: todos

## Purpose
Todos owns task creation, edits, completion, deletion, and tab-switch preservation.

## Screens
- todos: `lib/features/todos/presentation/screens/todos_screen.dart`

## Preconditions catalog
- `base_data`: seeds the harness project graph.

## Sub-flows
```yaml
- name: forward_happy
  requires: [base_data]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /todos }, { find: todos_screen }, { tap: todos_add_button } ]
- name: backward_traversal
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: todos_screen }, { navigate: /toolbox } ]
- name: nav_bar_switch_mid_flow
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: todos_screen }, { navigate: /settings } ]
- name: back_at_root
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /todos }, { find: todos_screen } ]
- name: deep_link_entry
  requires: [base_data]
  appliesTo: { roles: [admin, inspector], devices: [s21, s10] }
  steps: [ { navigate: /todos }, { find: todos_screen } ]
- name: tab_switch_mid_edit
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: todos_screen }, { tap: todos_add_button } ]
- name: orientation_change
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: todos_screen } ]
```

## Retired flow IDs
- T31
- T32
- T33
- T34
- T88
