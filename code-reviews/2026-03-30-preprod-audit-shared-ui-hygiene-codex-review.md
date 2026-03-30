# Shared UI And Cross-Cutting Hygiene Audit

Date: 2026-03-30
Layer: shared theme/UI utilities, common hygiene debt, dead/stale surface area

## Findings

### 1. Medium | Confirmed
The design-token migration is incomplete and still depends on a large deprecated compatibility layer.

Evidence:

- `lib/core/theme/app_theme.dart` is `1670` lines and still exports many deprecated aliases.
- Deprecated aliases are actively marked in source:
  - `lib/core/theme/app_theme.dart:15-18`
  - `lib/core/theme/app_theme.dart:28-35`
  - `lib/core/theme/app_theme.dart:40-56`
  - `lib/core/theme/app_theme.dart:114-118`
- Current analyzer output contains `135` `deprecated_member_use_from_same_package` findings, heavily concentrated in golden tests.

Why this matters:

- The migration path is still wide enough that stale token usage keeps accumulating.
- The shared theme surface is larger and noisier than it needs to be for a pre-production stabilization phase.

### 2. Medium | Confirmed
The codebase still carries meaningful analyzer-visible hygiene debt in handwritten code, not just in generated or archive files.

Evidence:

- Current analyzer output shows `39` issues in the `unused/unnecessary import/unused field/unused element` bucket.
- Representative active-source examples:
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart:99` unused field
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart:480` unused element
  - `lib/features/forms/di/forms_providers.dart` multiple unnecessary imports
  - `lib/features/auth/presentation/screens/company_setup_screen.dart:11` unnecessary import

Why this matters:

- This is precisely the kind of “general hygiene rot” that slows future fix passes.
- The debt is current and handwritten, not just legacy or generated output.

### 3. Medium | Confirmed
Silent exception swallowing remains a broad cross-cutting pattern.

Evidence:

- There are `32` silent `catch (_) / catch(_)` blocks in `lib/`.
- The pattern appears in logging, sync UI, PDF/OCR utilities, and other cross-cutting files.

Why this matters:

- Silent fallback patterns are hard to distinguish from intentional resilience.
- This reduces debuggability in precisely the areas that already have large surface area.

### 4. Low | Confirmed
Large shared utility files remain maintenance hotspots.

Evidence:

- `lib/shared/testing_keys/testing_keys.dart` is `1069` lines.
- `lib/core/logging/logger.dart` is `990` lines.
- `lib/core/theme/app_theme.dart` is `1670` lines.

Why this matters:

- These files accumulate unrelated concerns and make targeted cleanup slower.
- They are not immediate blockers, but they are part of the broader hygiene burden.

### 5. Medium | Confirmed
Dead-or-stale form screen surface still leaks through shared exports and harness infrastructure.

Evidence:

- `lib/features/forms/presentation/screens/screens.dart:3` still exports `forms_list_screen.dart`.
- Test harness files still treat `FormsListScreen` as a supported screen.

Why this matters:

- Shared exports and harness registries are preserving stale surface area instead of helping the old path die off.

### 6. Medium | Confirmed
The shared testing-key surface still preserves obsolete form-list assumptions as if they were current product contracts.

Evidence:

- `lib/shared/testing_keys/toolbox_keys.dart:19-49` defines a dedicated `forms_list_screen` key family and related saved-response keys for the old list screen.
- Those keys still line up with the stale screen and harness references rather than the current production router flow.

Why this matters:

- Shared testing utilities are part of the maintained API of the codebase.
- Keeping stale screen contracts alive in shared helpers makes drift harder to remove and easier to accidentally preserve in new tests.

## Coverage Gaps

- Shared theme behavior is well represented by golden tests, but the analyzer results show the golden suite itself still depends on deprecated theme tokens.
- There is no single hygiene gate today that prevents deprecated theme aliases from continuing to spread.
