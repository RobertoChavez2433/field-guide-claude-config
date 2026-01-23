Identified multiple outdated keys and mismatches in integration and project management tests, inconsistent login requirements, and incorrect UI references in helpers causing coverage gaps and potential test failures.

 Listing key testing issues

  Found critical test suite gaps: integration_test/test_bundle.dart excludes many e2e tests causing hidden failures;
  numerous key mismatches in helpers and patrol tests lead to flakiness or no-op tests; inconsistent authentication
  gating makes many tests fail when login is required; tests rely on fragile text finders rather than stable keys;
  golden tests lack stable comparators and commit failure images causing noise; outdated docs and helpers create
  confusion.

  Providing a prioritized remediation plan

  1. Enable reliable auth handling by adding a test mode flag (--dart-define=E2E_TEST=true) to auto-login or skip
     gating, and add test helpers to authenticate or skip accordingly, preventing auth-related failures.
  2. Centralize UI test keys in shared constants (e.g., lib/shared/testing_keys.dart) and update both UI (adding missing
     keys where needed) and tests/helpers to use these, resolving key mismatches and fragile text selectors.
  3. Consolidate or retire outdated helper sets like integration_test/helpers/; update PatrolTestHelpers and README to
     reflect current app structure and key names, ensuring proper app startup in tests.
  4. Integrate e2e and isolated tests into the default test bundle and patrol.yaml targets; update run scripts to
     include all relevant tests so coverage matches expectations.
  5. Stabilize golden tests by adding a tolerant golden comparator setup and gitignoring or cleaning up committed
     failure images to reduce flaky or noisy CI results.
  6. Implement deterministic seeded test data or create fixtures so tests that require existing entries or projects do not silently pass or skip due to missing data.
  7. Fix confirmation dialog cancel key mismatches by updating helpers and tests to handle all variants (confirmation_dialog_cancel, cancel_dialog_button, unsaved_changes_cancel) or unify keys in UI.

      Enumerating key testing issues with file references
      - Tests not executed in default runs: integration_test/test_bundle.dart (groups at lines 10, 25, 40) excludes integration_test/patrol/e2e_tests/ and integration_test/patrol/isolated/; run_patrol_batched.ps1 only runs top-level tests, causing major coverage gaps.
      - Key mismatches causing failures/no-ops:
     - integration_test/patrol/project_management_test.dart uses projects_tab (line 45), project_card_ (line 120), and project_edit_menu_item without IDs; correct keys are projects_nav_button in lib/core/router/app_router.dart:35 and project_card_${id} in lib/features/projects/presentation/screens/project_list_screen.dart:88.
      - integration_test/helpers/auth_test_helper.dart uses #nav_settings (line 12) and #settings_sign_out_button (line 20); but actual keys are settings_nav_button in lib/core/router/app_router.dart:42, and settings_sign_out_tile in lib/features/settings/presentation/screens/settings_screen.dart:75. integration_test/helpers/navigation_helper.dart uses #nav_home (line 15), #nav_projects (line 17) absent in UI keys.
  - Entry wizard test keys missing or incorrect in integration_test/patrol/entry_management_test.dart: uses
    entry_wizard_save (line 50), entry_wizard_finalize (line 75), and entry_wizard_complete (line 80) which do not
    exist; UI uses entry_wizard_submit in lib/features/entries/presentation/screens/entry_wizard_screen.dart:120. The
    confirmation dialog uses cancel_dialog_button and unsaved_changes_cancel in lib/shared/widgets/
    confirmation_dialog.dart:45, but tests/PatrolTestHelpers use confirmation_dialog_cancel (e.g., integration_test/
    patrol/helpers/patrol_test_helpers.dart:60).
  - Authentication gating inconsistencies: several tests (e.g., integration_test/patrol/offline_mode_test.dart and
    integration_test/patrol/entry_management_test.dart) run assuming home screen without login checks, leading to
    failures if auth is enabled.
  - Outdated helpers and documentation:
      - integration_test/patrol/helpers/README.md includes invalid PatrolTestHelpers($) constructor example (around line
        10).
      - integration_test/helpers/README.md references obsolete #nav_* keys.
  - Fragile test selectors and delays: multiple tests use text finders like 'Home', 'Settings' (e.g., integration_test/
    patrol/offline_mode_test.dart) instead of stable keys, and rely on arbitrary delays.
  - Golden tests instability: tolerant comparator defined but unused in test/golden/test_helpers.dart; failure images
    committed in test/golden/pdf/failures/.
  - Version mismatch: Patrol docs at integration_test/patrol/README.md:5 mention version 3.11.2, but pubspec.yaml:45
    specifies 3.20.0.

     Findings

  - Critical: default Patrol bundle and batched runner only cover top‑level tests, so e2e_tests and isolated suites
    never run (false sense of coverage). refs integration_test/test_bundle.dart:83 run_patrol_batched.ps1:23
  - High: key drift in project tests (projects_tab, project_card_) doesn’t match actual UI keys, causing no‑ops/
    failures. refs integration_test/patrol/project_management_test.dart:28 lib/core/router/app_router.dart:195 lib/
    features/projects/presentation/screens/project_list_screen.dart:193
  - High: helper key drift (#nav_*, #settings_sign_out_button) doesn’t exist in UI, so helper‑based tests will fail if
    used. refs integration_test/helpers/auth_test_helper.dart:53 integration_test/helpers/navigation_helper.dart:13 lib/
    core/router/app_router.dart:201 lib/features/settings/presentation/screens/settings_screen.dart:211
  - High: entry tests expect non‑existent wizard buttons (entry_wizard_save, entry_wizard_finalize,
    entry_wizard_complete) and treat entry_wizard_save_draft as on‑screen (it’s only in unsaved dialog). refs
    integration_test/patrol/entry_management_test.dart:182 lib/features/entries/presentation/screens/
    entry_wizard_screen.dart:667 lib/shared/widgets/confirmation_dialog.dart:137
  - High: confirmation dialog cancel key mismatch (confirmation_dialog_cancel vs cancel_dialog_button/
    unsaved_changes_cancel) breaks cancel flows. refs integration_test/patrol/helpers/patrol_test_helpers.dart:543 lib/
    shared/widgets/confirmation_dialog.dart:33
  - Medium: auth gating inconsistent; several tests assume home UI and will fail when Supabase auth is enabled. refs
    integration_test/patrol/entry_management_test.dart:21 integration_test/patrol/offline_mode_test.dart:18
  - Medium: docs/helpers out of sync (README shows constructor that doesn’t exist; old nav keys). refs integration_test/
    patrol/helpers/README.md:15 integration_test/helpers/README.md:303
  - Medium: Patrol helper uses text finders that don’t match UI labels with asterisks, making project helpers brittle.
    refs integration_test/patrol/helpers/patrol_test_helpers.dart:336 lib/features/projects/presentation/screens/
    project_setup_screen.dart:175
  - Low: golden stability gaps — tolerant comparator exists but isn’t wired, and failures are tracked under test/golden/
    pdf/failures/ creating noise. refs test/golden/test_helpers.dart:126 test/golden/pdf/failures/
  - Low: Patrol version in docs doesn’t match pubspec. refs integration_test/patrol/README.md:450 pubspec.yaml:103

  AGENTS update: added QA/testing + code‑review summaries in .codex/AGENTS.md.

  Plan

  1. Lock down test mode + auth: decide default E2E mode (offline bypass or test account login) and add a single helper
     to “ensure home or skip/login” so every Patrol test starts from a known state; this prevents auth‑dependent
     failures.
  2. Normalize keys and helpers: create a shared key constants file (e.g., lib/shared/testing_keys.dart) and update UI/
     tests/helpers to use it; remove or update integration_test/helpers to match actual keys and launch behavior to
     avoid drift.
  3. Fix core flow tests: update entry/project tests to use real keys and flows (submit via entry_wizard_submit, draft
     via unsaved dialog); use project_name_field etc instead of label text; create data in‑test before editing to ensure
     assertions are real.
  4. Make the right suite run: either move e2e_tests/isolated to top‑level Patrol directory or add an aggregator target
     and update patrol.yaml + run_patrol_batched.ps1; otherwise your new tests never execute.
  5. Replace hard sleeps with condition‑based waits and add deterministic data setup (seed or on‑the‑fly creation) to
     reduce flakiness and no‑op tests.
  6. Stabilize goldens: wire a global comparator (e.g., test/flutter_test_config.dart), ignore **/failures/, and clean
     tracked failures; this keeps CI stable across platforms.