# Completeness Review — Group 4 (Phase 5 + Phase 6)

**Plan**: `.claude/plans/2026-04-06-design-system-overhaul.md`
**Spec**: `.claude/specs/2026-04-06-design-system-overhaul-spec.md`
**Review date**: 2026-04-06
**Reviewer**: completeness-review-agent

## Verdict: NEEDS_FIXES

7 findings: 1 critical, 2 high, 3 medium, 1 low

## Spec Coverage Analysis

### Requirements mapped to P5

| Req | Spec Source | Description | Status |
|-----|------------|-------------|--------|
| R1 | S4 Profiling Protocol | Profile 5 worst screens, capture frame times, identify >16ms frames | MET |
| R2 | S4 RepaintBoundary | Add RepaintBoundary to list items, AppBottomBar, AppGlassCard, animated widgets, scaffold body/nav | MET |
| R3 | S4 Provider Rebuild | notifyListeners guard pattern (if value == _value return) | PARTIALLY MET |
| R4 | S8 Testing | Performance tests -- baseline frame times, fail on regression | PARTIALLY MET |

### Requirements mapped to P6

| Req | Spec Source | Description | Status |
|-----|------------|-------------|--------|
| R5 | Success Criteria | Desktop hover + focus on ALL interactive components | PARTIALLY MET |
| R6 | S8 Widgetbook | All design system components + key feature widgets | PARTIALLY MET |
| R7 | S8 Documentation | 6 architecture doc files updated | DRIFTED |
| R8 | S8 HTTP Driver | TestingKeys, screen flows, responsive endpoints, density/nav diagnostics, animation-aware waits | PARTIALLY MET |
| R9 | S8 Logging | Logger.ui, breakpoint/density/motion logs, debug server UI diagnostics | PARTIALLY MET |
| R10 | S8 Golden Tests | Delete HC baselines, regenerate, add new baselines | MET |
| R11 | S4 Lint Rules | Flip warnings to errors at end of refactor | DRIFTED |
| R12 | S8 Testing | Integration tests updated for decomposed widget structure | NOT MET |
| R13 | S8 Testing | Responsive tests -- test canonical layouts at each breakpoint | PARTIALLY MET |
| R14 | S8 Testing | Widget tests for new components covering variants/themes/breakpoints | MET |
| R15 | S11 Issues | All 11 GitHub issues verified closed | MET |

## Findings

### 1. CLAUDE.md documentation has wrong component names and scrambled categories

- **Severity**: critical
- **Phase**: P6
- **Location**: lines 12105-12113 (Step 6.3.1)
- **Spec reference**: Section 7 (Design System Component Inventory), Section 8 (Documentation Updates)
- **Issue**: The CLAUDE.md documentation update in step 6.3.1 has multiple errors compared to the spec's canonical component inventory:
  - **animation/** lists `AppFadeIn, AppSlideIn, AppScaleIn` -- these don't exist. The spec and the plan's own P2 implementation create `AppAnimatedEntrance, AppTapFeedback, AppValueTransition`.
  - **atoms/** is missing `AppIcon, AppProgressBar, AppToggle, AppMiniSpinner` (4 existing components that the spec lists).
  - **molecules/** is missing `AppCounterField` and `AppSectionHeader` (both existing, spec Section 7).
  - **organisms/** lists only form primitives but is missing `AppGlassCard, AppSectionCard, AppPhotoGrid, AppInfoBanner, AppStatCard, AppActionCard` (all spec organisms).
  - **surfaces/** lists `AppSectionCard, AppGlassCard, AppActionCard, AppStatCard` which are organisms per spec, not surfaces. The spec's surfaces are `AppScaffold, AppBottomBar, AppBottomSheet, AppDialog, AppStickyHeader, AppDragHandle`.
  - **feedback/** includes `AppDialog, AppBottomSheet` which are surfaces per spec, and `AppInfoBanner` which is an organism per spec.
  - **layout/** includes `AppScaffold, AppBottomBar, AppStickyHeader` which are surfaces per spec.
  - `AppPhotoGrid` is absent entirely.
  - `AppDragHandle` is absent entirely.
- **Fix**: Rewrite the CLAUDE.md component inventory to exactly match spec Section 7's folder structure and component assignments. Use the target folder structure from spec lines 418-489 as the source of truth.

### 2. no_raw_navigator flipped to ERROR but spec says it stays at info severity

- **Severity**: high
- **Phase**: P6
- **Location**: line 12393 (Step 6.6.2)
- **Spec reference**: Section 4 Lint Rules table, row for `no_raw_navigator`
- **Issue**: The spec explicitly sets `no_raw_navigator` at `info` severity (no arrow notation indicating it should change), unlike all other rules which show `warning -> error`. The plan includes `no_raw_navigator` in the list of 9 rules to flip to ERROR severity. This contradicts the spec.
- **Fix**: Remove `no_raw_navigator.dart` from the list of files to flip in step 6.6.2 (reduce to 8 files). The rule should remain at its P0-set severity. Separately, ensure the `no_direct_snackbar` extension (which absorbed the spec's `no_raw_snackbar` functionality) is verified to be at ERROR severity or added to the flip list.

### 3. no_direct_snackbar severity not addressed in lint flip step

- **Severity**: high
- **Phase**: P6
- **Location**: lines 12362-12395 (Step 6.6.2)
- **Spec reference**: Section 4 Lint Rules table, `no_raw_snackbar` row: `warning -> error`
- **Issue**: The spec lists 10 rules to flip to error. The plan merged `no_raw_snackbar` into the existing `no_direct_snackbar` rule in P0 (step 0.5). However, step 6.6.2 only lists 9 new rule files and explicitly notes "no_raw_snackbar is NOT a separate file." But it never addresses whether `no_direct_snackbar` itself needs its severity confirmed/flipped to ERROR. If it was already at ERROR, fine -- but the plan should verify this explicitly.
- **Fix**: Add `no_direct_snackbar.dart` to the verification list in step 6.6.1. If its severity is not already ERROR, add it to the flip list. Add a note explaining the merged rule situation.

### 4. Integration test updates completely missing

- **Severity**: medium
- **Phase**: P6
- **Location**: N/A (absent from plan)
- **Spec reference**: Section 8 Testing table: "Integration tests | Update for decomposed widget structure"
- **Issue**: The spec requires updating integration tests for the decomposed widget structure. No step in P5 or P6 addresses this. The plan's P6 sub-phase 6.4.2 mentions updating HTTP driver screen test flows but this is driver routes, not integration tests (which live in `integration_test/`).
- **Fix**: Add a sub-phase (e.g., 6.2c) or step to audit and update integration test files under `integration_test/` for any widget key, finder, or structural changes resulting from P4 decomposition. At minimum, verify they still compile after all P4 changes.

### 5. Desktop hover/focus coverage incomplete -- missing interactive molecules

- **Severity**: medium
- **Phase**: P6
- **Location**: lines 11848-11944 (Sub-phase 6.1)
- **Spec reference**: Success Criteria: "Desktop hover states + focus indicators on all interactive components"
- **Issue**: Sub-phase 6.1 adds hover/focus to 6 components (AppButton, AppListTile, AppSectionCard, AppChip, AppGlassCard, AppToggle) plus a global ThemeData fallback. However, the spec says "ALL interactive components." Missing explicit treatment for: `AppTextField`, `AppCounterField`, `AppSearchBar`, `AppDropdown`, `AppDatePicker`, `AppTabBar`. While some of these wrap Material widgets that may inherit hover states from ThemeData, the plan should explicitly verify or address each interactive component. `AppDropdown` and `AppDatePicker` are entirely new components built in P3 and deserve explicit hover/focus steps.
- **Fix**: Add steps 6.1.4d through 6.1.4f (or a batch step) for the remaining interactive molecules. At minimum, add a verification step that audits all interactive components for hover/focus behavior on desktop and documents which ones rely on ThemeData fallback vs. explicit implementation.

### 6. Widgetbook missing key feature widgets

- **Severity**: medium
- **Phase**: P6
- **Location**: lines 11947-12016 (Sub-phase 6.2)
- **Spec reference**: Section 8 Widgetbook Setup: "Scope | All design system components + key feature widgets"
- **Issue**: Steps 6.2.1 and 6.2.2 only cover design system layer components (atoms, molecules, organisms, surfaces, feedback, layout). The spec explicitly scopes Widgetbook to include "key feature widgets" as well -- these would be extracted feature-level widgets from P4 decomposition that are reused or significant (e.g., entry cards, project cards, contractor editor sections, dashboard stat cards). The plan has no step for adding feature widget use cases.
- **Fix**: Add a step 6.2.2b that identifies key feature widgets (e.g., from the P4 decomposition outputs) and creates Widgetbook use cases for them. Alternatively, add a tracking note that feature widget use cases are added incrementally post-overhaul, but this should be an explicit decision, not a silent omission.

### 7. Debug server UI diagnostics endpoint not addressed

- **Severity**: low
- **Phase**: P6
- **Location**: lines 12237-12251 (Step 6.4.4)
- **Spec reference**: Section 8 Logging Updates: "Debug server UI diagnostics | Breakpoint, density, theme, animation state"
- **Issue**: The spec calls for the debug server (Node.js tool at `tools/debug-server/server.js`) to surface UI diagnostics including breakpoint, density, theme, and animation state. Step 6.4.4 creates `Logger.ui` and logs these events, but doesn't update the debug server itself to expose a diagnostics endpoint or dashboard panel showing current UI state. The driver gets endpoints (step 6.4.3) but the debug server is a separate concern.
- **Fix**: Add a step (e.g., 6.4.4b) to update the debug server to consume and display the new `Logger.ui` events, or at minimum add a `/ui-diagnostics` view/endpoint that reports current breakpoint, density, theme, and animation state.

## Summary

- Requirements: 15 total, 6 met, 5 partially met, 1 not met, 3 drifted
- P5 is solid overall -- profiling protocol and RepaintBoundary placement are thorough. Minor gap on notifyListeners guard pattern (implicit in "fix bottlenecks" but not explicit) and performance test harness for CI regression.
- P6 has the bulk of the issues. The CLAUDE.md documentation update (step 6.3.1) is the most concerning finding -- the component inventory it would write is significantly wrong (3 fabricated animation names, ~15 components in wrong categories or missing). This would create persistent documentation drift.
- The lint severity flip has two issues: flipping `no_raw_navigator` to ERROR contradicts the spec's `info` designation, and the merged `no_direct_snackbar` rule is not verified/flipped.
- Testing coverage has gaps: integration tests are unaddressed, responsive layout tests exist only as driver endpoints (not test files), and the performance baseline JSON has no test harness to enforce regression detection.
