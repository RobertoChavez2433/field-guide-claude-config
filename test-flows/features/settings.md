# Feature: settings

## Purpose
Settings owns profile, saved exports, app lock, legal/help surfaces, admin dashboard, personnel types, trash, and admin-only restrictions.

## Screens
- settings: `lib/features/settings/presentation/screens/settings_screen.dart`
- edit-profile: `lib/features/settings/presentation/screens/edit_profile_screen.dart`
- saved-exports: `lib/features/settings/presentation/screens/settings_saved_exports_screen.dart`
- admin-dashboard: `lib/features/settings/presentation/screens/admin_dashboard_screen.dart`
- personnel-types: `lib/features/settings/presentation/screens/personnel_types_screen.dart`
- trash: `lib/features/settings/presentation/screens/trash_screen.dart`

## Preconditions catalog
- `base_data`: seeds the approved harness account and project graph.
- `pay_app_draft`: seeds saved-export metadata.

## Sub-flows
```yaml
- name: forward_happy
  requires: [base_data]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /settings }, { find: settings_screen }, { tap: settings_edit_profile_tile }, { find: edit_profile_screen } ]
- name: backward_traversal
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /settings/trash }, { find: trash_screen }, { back: true }, { find: settings_screen } ]
- name: nav_bar_switch_mid_flow
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /settings }, { find: settings_screen }, { tap: projects_nav_button }, { find: project_list_screen } ]
- name: back_at_root
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /settings }, { find: settings_screen }, { back: true } ]
- name: deep_link_entry
  requires: [pay_app_draft]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /settings/saved-exports }, { find: settings_saved_exports_screen } ]
- name: orientation_change
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: settings_screen } ]
- name: export_verification
  requires: [pay_app_draft]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /settings }, { find: settings_screen }, { tap: settings_saved_exports_tile }, { find: settings_saved_exports_screen } ]
- name: role_restriction
  requires: [base_data]
  appliesTo: { roles: [engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /admin-dashboard }, { find: settings_screen } ]
```

## Retired flow IDs
- T44
- T45
- T46
- T47
- T48
- T49
- T50
- T51
- T52
- T54
- T55
- T56
- T57
- T60
- T67
- T76
- T77
- T91
- M08
- M10
- M11
