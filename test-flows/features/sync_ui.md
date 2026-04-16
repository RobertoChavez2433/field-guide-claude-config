# Feature: sync_ui

## Purpose
Sync UI covers dashboard/conflict viewer navigation only. Transport state and dual-device mutation proofs stay in the existing S01-S21 sync harness.

## Screens
- sync-dashboard: `lib/features/sync/presentation/screens/sync_dashboard_screen.dart`
- conflict-viewer: `lib/features/sync/presentation/screens/conflict_viewer_screen.dart`

## Preconditions catalog
- `base_data`: seeds the harness project graph.

## Sub-flows
```yaml
- name: forward_happy
  requires: [base_data]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /sync/dashboard }, { find: sync_dashboard_screen } ]
- name: backward_traversal
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /sync/conflicts }, { find: conflict_viewer_screen }, { navigate: /sync/dashboard } ]
- name: nav_bar_switch_mid_flow
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: sync_dashboard_screen }, { navigate: /settings } ]
- name: back_at_root
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /sync/dashboard }, { find: sync_dashboard_screen } ]
- name: deep_link_entry
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /sync/conflicts }, { find: conflict_viewer_screen } ]
- name: orientation_change
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: sync_dashboard_screen } ]
```

## Retired flow IDs
- T78
- T79
- T80
- T81
- T82
- T83
- T84
