# Feature: dashboard

## Purpose
Dashboard covers the project hub and calendar/home composition. `HomeScreen` is registered under entries and remains owned there; this file tests home-tab composition only.

## Screens
- project-dashboard: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`
- home: `lib/features/entries/presentation/screens/home_screen.dart`

## Preconditions catalog
- `base_data`: seeds the approved harness project and admin profile.

## Sub-flows
```yaml
- name: forward_happy
  requires: [base_data]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: / }, { find: project_dashboard_screen }, { tap: dashboard_toolbox_card }, { find: toolbox_home_screen } ]
- name: backward_traversal
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: / }, { tap: calendar_nav_button }, { find: home_screen }, { back: true } ]
- name: nav_bar_switch_mid_flow
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: / }, { tap: projects_nav_button }, { find: project_list_screen }, { tap: dashboard_nav_button }, { find: project_dashboard_screen } ]
- name: back_at_root
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: / }, { find: project_dashboard_screen }, { back: true } ]
- name: deep_link_entry
  requires: [base_data]
  appliesTo: { roles: [admin, inspector], devices: [s21, s10] }
  steps: [ { navigate: /calendar }, { find: home_screen } ]
- name: orientation_change
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: project_dashboard_screen } ]
```

## Retired flow IDs
- T92
- T93
- T94
- T95
- T96
