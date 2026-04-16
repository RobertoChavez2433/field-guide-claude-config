# Feature Flow Taxonomy

## Feature Taxonomy

| Feature | Primary screens | Role gating |
|---|---|---|
| auth | login, register, forgot-password, otp-verification, update-password, update-required, profile-setup, company-setup, pending-approval, account-status | all |
| dashboard | project-dashboard, home | all |
| projects | project-list, project-setup | admin, engineer, officeTechnician mutate; inspector denied project-management mutations |
| entries | entries-list, drafts-list, entry-editor, entry-review, review-summary, entry-pdf-preview | all, with inspector restriction checks for management-only edges |
| forms | mdot-hub, form-new-dispatcher, form screens, form-gallery, form-pdf-preview | all |
| pay_applications | pay-application-detail, contractor-comparison | admin, engineer, officeTechnician; inspector denied |
| quantities | quantities, quantity-calculator | all |
| analytics | project-analytics | admin, engineer, officeTechnician; inspector denied |
| pdf | pdf-import-preview, mp-import-preview | admin, engineer, officeTechnician; inspector denied |
| gallery | gallery | all |
| toolbox | toolbox-home | all |
| calculator | calculator | all |
| todos | todos | all |
| settings | settings, saved-exports, admin-dashboard, personnel-types, trash, profile/help/legal/app-lock | admin-only subset; rest all |
| sync_ui | sync-dashboard, conflict-viewer | all; conflict viewer debug-only |
| contractors | contractor-selection | all |

## Sub-flow Catalog

| Name | Purpose |
|---|---|
| forward_happy | Forward happy path through a feature |
| backward_traversal | Return from terminal surface to feature entry |
| nav_bar_switch_mid_flow | Switch shell tabs mid-flow and prove state/redirect |
| back_at_root | Back at the feature root resolves predictably |
| deep_link_entry | Cold entry into a nested route |
| tab_switch_mid_edit | Tab switch during edit/discard states |
| orientation_change | Rotate device without crash or data loss |
| form_completeness | Fill and inspect all form fields |
| export_verification | Export and verify file/PDF integrity |
| role_restriction | Assert role-gated denial/allowance |

## Retired Flow ID Index

- T01 -> auth.md
- T02 -> auth.md
- T03 -> auth.md
- T04 -> auth.md
- T05 -> projects.md
- T06 -> projects.md
- T07 -> projects.md
- T08 -> projects.md
- T09 -> projects.md
- T10 -> projects.md
- T11 -> projects.md
- T12 -> projects.md
- T13 -> projects.md
- T14 -> projects.md
- T15 -> entries.md
- T16 -> entries.md
- T17 -> contractors.md
- T18 -> contractors.md
- T19 -> contractors.md
- T20 -> quantities.md
- T21 -> quantities.md
- T22 -> entries.md
- T23 -> entries.md
- T24 -> entries.md
- T25 -> entries.md
- T26 -> entries.md
- T27 -> entries.md
- T28 -> entries.md
- T29 -> entries.md
- T30 -> entries.md
- T31 -> todos.md
- T32 -> todos.md
- T33 -> todos.md
- T34 -> todos.md
- T35 -> forms.md
- T36 -> forms.md
- T37 -> forms.md
- T38 -> calculator.md
- T39 -> calculator.md
- T40 -> gallery.md
- T41 -> entries.md
- T42 -> entries.md
- T43 -> forms.md
- T44 -> settings.md
- T45 -> settings.md
- T46 -> settings.md
- T47 -> settings.md
- T48 -> settings.md
- T49 -> settings.md
- T50 -> settings.md
- T51 -> settings.md
- T52 -> settings.md
- T53 -> projects.md
- T54 -> settings.md
- T55 -> settings.md
- T56 -> settings.md
- T57 -> settings.md
- T58 -> projects.md
- T59 -> projects.md
- T60 -> settings.md
- T61 -> quantities.md
- T62 -> entries.md
- T63 -> entries.md
- T64 -> entries.md
- T65 -> projects.md
- T66 -> projects.md
- T67 -> settings.md
- T68 -> entries.md
- T69 -> contractors.md
- T70 -> contractors.md
- T71 -> projects.md
- T72 -> projects.md
- T73 -> quantities.md
- T74 -> forms.md
- T75 -> projects.md
- T76 -> settings.md
- T77 -> settings.md
- T78 -> sync_ui.md
- T79 -> sync_ui.md
- T80 -> sync_ui.md
- T81 -> sync_ui.md
- T82 -> sync_ui.md
- T83 -> sync_ui.md
- T84 -> sync_ui.md
- T85 -> projects.md
- T86 -> entries.md
- T87 -> entries.md
- T88 -> todos.md
- T89 -> pay_applications.md
- T90 -> analytics.md
- T91 -> settings.md
- T92 -> dashboard.md
- T93 -> dashboard.md
- T94 -> dashboard.md
- T95 -> dashboard.md
- T96 -> dashboard.md
- P01 -> pay_applications.md
- P02 -> pay_applications.md
- P03 -> pay_applications.md
- P04 -> pay_applications.md
- P05 -> pay_applications.md
- P06 -> out-of-scope sync harness
- M01 -> auth.md
- M02 -> auth.md
- M03 -> pdf.md
- M04 -> pdf.md
- M05 -> entries.md
- M06 -> out-of-scope removed placeholder
- M07 -> projects.md
- M08 -> settings.md
- M09 -> forms.md
- M10 -> settings.md
- M11 -> settings.md
- M12 -> entries.md
- M13 -> entries.md
