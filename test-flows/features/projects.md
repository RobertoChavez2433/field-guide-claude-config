# Feature: projects

## Purpose
Projects owns project list/setup, project-scoped configuration, archive/remove flows, and inspector-denied management mutations.

## Screens
- project-list: `lib/features/projects/presentation/screens/project_list_screen.dart`
- project-setup: `lib/features/projects/presentation/screens/project_setup_screen.dart`

## Preconditions catalog
- `base_data`: seeds an approved harness account and project graph.
- `project_draft`: seeds a draft project.
- `location_a`: seeds a default location.
- `contractor_a`: seeds a default contractor.

## Sub-flows
```yaml
- name: forward_happy
  requires: [project_draft, location_a, contractor_a]
  appliesTo: { roles: [admin, engineer, officeTechnician], devices: [s21, s10] }
  steps: [ { navigate: /projects }, { find: project_list_screen }, { navigate: /project/new }, { find: project_setup_screen } ]
- name: backward_traversal
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /project/harness-project-001/edit }, { find: project_setup_screen }, { navigate: /projects } ]
- name: nav_bar_switch_mid_flow
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /project/harness-project-001/edit }, { find: project_setup_screen }, { navigate: /settings }, { find: settings_screen } ]
- name: back_at_root
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /projects }, { find: project_list_screen } ]
- name: deep_link_entry
  requires: [base_data]
  appliesTo: { roles: [admin, engineer, officeTechnician], devices: [s21, s10] }
  steps: [ { navigate: /project/harness-project-001/edit }, { find: project_setup_screen } ]
- name: tab_switch_mid_edit
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: project_setup_screen }, { tap: project_locations_tab }, { tap: project_contractors_tab } ]
- name: orientation_change
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: project_setup_screen } ]
- name: role_restriction
  requires: [base_data]
  appliesTo: { roles: [inspector], devices: [s21, s10] }
  steps: [ { navigate: /project/harness-project-001/edit }, { find: project_list_screen } ]
```

## Retired flow IDs
- T05
- T06
- T07
- T08
- T09
- T10
- T11
- T12
- T13
- T14
- T53
- T58
- T59
- T65
- T66
- T71
- T72
- T75
- T85
- M07
