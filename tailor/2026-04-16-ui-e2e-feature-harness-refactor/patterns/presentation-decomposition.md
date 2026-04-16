# Pattern — Presentation Decomposition to 300-Line Ceiling

Rubric item 4 + `scripts/audit_ui_file_sizes.ps1` enforce `MaxLines=300`. Rubric item 5 requires oversized screens to split into composables using the repo's existing `*_mixin.dart` / `*_helpers.dart` / `*_actions.dart` pattern.

## Exemplars (already present in repo)

- `lib/features/entries/presentation/screens/entry_editor_state_mixin.dart` — state mixin lifted from `entry_editor_screen.dart` to keep the screen body thin.
- `lib/features/entries/presentation/widgets/entry_contractors_section_actions.dart` — actions helper for `entry_contractors_section.dart`.
- `lib/features/entries/presentation/controllers/entry_editing_controller.dart` — screen-local controller owning the edit flow.
- `lib/features/forms/presentation/widgets/form_workflow_shell.dart`, `lib/features/forms/presentation/widgets/form_viewer_sections.dart`, `lib/features/forms/presentation/support/form_pdf_action_owner.dart` — sections, shell, and action-owner split for the form viewer.

## Split axes (what the repo already separates)

| Suffix | Contents | Example |
|---|---|---|
| `_screen.dart` | `StatefulWidget` / `StatelessWidget` + `build` only | `entry_editor_screen.dart` |
| `_state_mixin.dart` | `State<…>` lifecycle + state fields | `entry_editor_state_mixin.dart` |
| `_actions.dart` | user-intent → provider calls; no UI | `entry_contractors_section_actions.dart` |
| `_controller.dart` (under `controllers/`) | `ChangeNotifier` + provider plumbing | `entry_editing_controller.dart` |
| `_helpers.dart` | pure-Dart helpers for section rendering | `mp_import_helper.dart` |
| `_sections.dart` / `_card.dart` / `_section.dart` (under `widgets/`) | presentational widgets | `form_viewer_sections.dart` |
| `_shell.dart` | wrapping scaffold with slots | `form_workflow_shell.dart` |
| `_body_content.dart` | inner content widget | `mdot_hub_body_content.dart` |

## Rules

1. **Preserve user-visible behavior.** Decomposition is allowed by spec § Blast Radius Budget; logic changes require a separate commit.
2. **State lives next to the screen.** Mixins + `State` subclasses stay in `presentation/screens/` or `presentation/controllers/`. Do not cross feature boundaries.
3. **Move colors + keys first, split second.** Fixing rubric items 1 and 2 often shrinks a file enough that decomposition becomes optional.
4. **Do not add new dependencies.** `provider` + `ChangeNotifier` only (architecture rule). No Riverpod, no `flutter_bloc`.
5. **Keep `build` methods under ~80 lines.** Hoist conditional branches to widget methods; hoist sections to `_sections.dart`.

## Applied to the biggest offenders

| File | Strategy |
|---|---|
| `mdot_1174r_form_screen.dart` (677) | Split per workflow step into `mdot_1174r_sections.dart`-family; likely a `mdot_1174r_workflow_shell.dart` parallel to the 1126 pattern |
| `entry_review_screen.dart` (565) | Hoist review list rendering to `entry_review_sections.dart`; keep screen as scaffold + controller binding |
| `app_lock_settings_screen.dart` (560) | Split privacy, biometric, pin subsections into dedicated widgets in `settings/presentation/widgets/` |
| `form_gallery_screen.dart` (525) | Hoist saved/responses sections; sentinel keys already exist (`form_gallery_screen`, `form_gallery_saved_section_<formType>`) |
| `consent_screen.dart` (469) | Move markdown body + scroll behavior into a body widget; screen becomes scaffold only |
| `project_analytics_screen.dart` (467) | Chart sub-widgets already exist (`pay_app_comparison_chart`); move remaining sections out |

## Do not

- Add `// coverage:ignore-file` or `// ignore: file_too_long` — project rule forbids ignore comments.
- Introduce a new state management library.
- Move UI code into `domain/` to get it out of the presentation audit.
