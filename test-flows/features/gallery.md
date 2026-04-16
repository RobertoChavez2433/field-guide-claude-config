# Feature: gallery

## Purpose
Gallery owns browsing project photos from the toolbox/gallery surface across phone and tablet.

## Screens
- gallery: `lib/features/gallery/presentation/screens/gallery_screen.dart`

## Preconditions catalog
- `base_data`: seeds the harness project graph.

## Sub-flows
```yaml
- name: forward_happy
  requires: [base_data]
  appliesTo: { roles: [admin, engineer, officeTechnician, inspector], devices: [s21, s10] }
  steps: [ { navigate: /gallery }, { find: gallery_screen } ]
- name: backward_traversal
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: gallery_screen }, { navigate: /toolbox } ]
- name: nav_bar_switch_mid_flow
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: gallery_screen }, { navigate: /settings } ]
- name: back_at_root
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { navigate: /gallery }, { find: gallery_screen } ]
- name: deep_link_entry
  requires: [base_data]
  appliesTo: { roles: [admin, inspector], devices: [s21, s10] }
  steps: [ { navigate: /gallery }, { find: gallery_screen } ]
- name: orientation_change
  requires: [base_data]
  appliesTo: { roles: [admin], devices: [s21, s10] }
  steps: [ { find: gallery_screen } ]
```

## Retired flow IDs
- T40
