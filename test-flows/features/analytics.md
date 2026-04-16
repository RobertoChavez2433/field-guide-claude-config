# Feature: analytics

## Purpose
Analytics owns project-level pay application and item drilldown reporting, including inspector-denied access to project-management analytics.

## Screens
- project-analytics: `lib/features/analytics/presentation/screens/project_analytics_screen.dart`

## Preconditions catalog
- `base_data`: seeds the harness project graph.
- `pay_app_draft`: seeds a saved pay application with export artifact metadata.

## Sub-flows
```yaml
- name: forward_happy
  requires: [pay_app_draft]
  appliesTo: { roles: [admin, engineer, officeTechnician], devices: [s21, s10] }
  steps: [ { navigate: /analytics/harness-project-001 }, { find: project_analytics_screen } ]
- name: backward_traversal
  requires: [pay_app_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: project_analytics_screen }, { navigate: / } ]
- name: nav_bar_switch_mid_flow
  requires: [pay_app_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: project_analytics_screen }, { navigate: /settings } ]
- name: back_at_root
  requires: [pay_app_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /analytics/harness-project-001 }, { find: project_analytics_screen } ]
- name: deep_link_entry
  requires: [pay_app_draft]
  appliesTo: { roles: [admin, engineer, officeTechnician], devices: [s21, s10] }
  steps: [ { navigate: /analytics/harness-project-001 }, { find: project_analytics_screen } ]
- name: orientation_change
  requires: [pay_app_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: project_analytics_screen } ]
- name: export_verification
  requires: [pay_app_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: project_analytics_screen }, { tap: analytics_date_filter } ]
- name: role_restriction
  requires: [pay_app_draft]
  appliesTo: { roles: [inspector], devices: [s21, s10] }
  steps: [ { navigate: /analytics/harness-project-001 }, { find: project_dashboard_screen } ]
```

## Retired flow IDs
- T90
