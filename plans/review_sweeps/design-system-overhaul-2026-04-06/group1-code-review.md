# Code Review -- Group 1 (Phase 0 + Phase 1)

**Plan**: `.claude/plans/2026-04-06-design-system-overhaul.md`
**Spec**: `.claude/specs/2026-04-06-design-system-overhaul-spec.md`
**Review date**: 2026-04-06
**Reviewer**: code-review-agent

## Verdict: NEEDS_FIXES

## Spec Alignment

Phase 0 and Phase 1 are largely faithful to the spec. Three areas of drift are identified below (findings 1, 2, 6).

## Findings

### 1. FieldGuideShadows type mismatch with Material elevation parameters
- **Severity**: blocking
- **Phase**: P1
- **Location**: Plan lines 2154, 2172, 2242, 2336-2339, 2358, 2386, 2410, 2437 (Sub-phase 1.8, `AppTheme.build()`)
- **Issue**: `FieldGuideShadows` fields are typed `List<BoxShadow>` (per spec), but the plan passes them directly to `elevation:` parameters on `AppBarTheme.scrolledUnderElevation`, `CardThemeData.elevation`, `ElevatedButton.styleFrom(elevation:)`, `FloatingActionButtonThemeData.elevation/.focusElevation/.hoverElevation/.highlightElevation`, `NavigationBarThemeData.elevation`, `DialogThemeData.elevation`, `BottomSheetThemeData.elevation`, and `SnackBarThemeData.elevation`. These all expect `double`, not `List<BoxShadow>`. This will not compile.
- **Fix**: Either (a) keep `FieldGuideShadows` as `List<BoxShadow>` for use in `BoxDecoration.boxShadow` and add a separate set of `double` elevation fields (e.g., `elevationLow`, `elevationMedium`, etc.) for Material component themes, or (b) define the shadow values but continue using `double` elevation values in `AppTheme.build()` by referencing `DesignConstants.elevation*` or new numeric constants for Material component themes.

### 2. Lint rule path scoping misses spec-required directories
- **Severity**: critical
- **Phase**: P0
- **Location**: Plan lines 74, 132, 190, 250, 384, 496, 566, 646, 714 (all new lint rules)
- **Issue**: All 9 new lint rules scope to `filePath.contains('/presentation/')` only. The spec (Section 4) states: "Rules apply across presentation screens, presentation widgets, `shared/widgets/`, and router-owned UI surfaces. Allowlist remains `design_system/` itself." The path filter `/presentation/` misses `lib/shared/widgets/` (7 widget files with hardcoded spacing/radius), `lib/core/router/` (UI surfaces), and any future UI code outside `/presentation/`.
- **Fix**: Change the scope check from `if (!filePath.contains('/presentation/')) return;` to a broader check that matches the spec: include `/presentation/`, `/shared/widgets/`, and `/core/router/` paths while continuing to exclude `/core/design_system/`, tests, and non-UI layers.

### 3. Getter-to-method migration breaks 70+ call sites
- **Severity**: critical
- **Phase**: P1
- **Location**: Plan lines 2563-2600 (Sub-phase 1.8, `darkTheme()` / `lightTheme()`)
- **Issue**: `AppTheme.darkTheme` and `AppTheme.lightTheme` are currently getters (no parentheses). The plan converts them to methods with optional `spacing` parameter. This breaks every call site that uses `AppTheme.darkTheme` without `()`. Grep found 80+ references across lib and test files. The plan only updates `ThemeProvider` (Sub-phase 1.5) and `test_helpers.dart` (Sub-phase 1.6).
- **Fix**: Add a step to Sub-phase 1.8 that updates all remaining call sites from `AppTheme.darkTheme` to `AppTheme.darkTheme()` and `AppTheme.lightTheme` to `AppTheme.lightTheme()`.

### 4. EdgeInsets.all / EdgeInsets.symmetric dual-implementation confusion
- **Severity**: critical
- **Phase**: P0
- **Location**: Plan lines 405-448 (Sub-phase 0.6, `no_hardcoded_spacing`)
- **Issue**: The plan provides two conflicting implementations. The first uses `addMethodInvocation` for `EdgeInsets.all/symmetric/only/fromLTRB`, the second uses `addInstanceCreationExpression`. The plan leaves this ambiguity for the implementer.
- **Fix**: Remove the `addMethodInvocation` approach. Provide a single implementation using `addInstanceCreationExpression` which correctly catches both `SizedBox` and `EdgeInsets` constructors.

### 5. `no_raw_navigator` does not catch `Navigator.of(context).push()`
- **Severity**: minor
- **Phase**: P0
- **Location**: Plan lines 653-662 (Sub-phase 0.9)
- **Issue**: The implementation only checks if `target is SimpleIdentifier` with name `Navigator`. For `Navigator.of(context).push(route)`, the target is a `MethodInvocation`, not a `SimpleIdentifier`. The rule will only catch static calls.
- **Fix**: Document as known limitation since rule is INFO severity.

### 6. FieldGuideMotion has 3 extra curve fields not in spec
- **Severity**: minor
- **Phase**: P1
- **Location**: Plan lines 1758-1760, 1785-1792 (`curveAccelerate`, `curveBounce`, `curveSpring`)
- **Issue**: The spec defines 7 fields. The plan adds 3 extra: `curveAccelerate`, `curveBounce`, `curveSpring`. Scope creep.
- **Fix**: Either remove the 3 extra fields or amend the spec explicitly.

### 7. Empty barrel files with no exports
- **Severity**: minor
- **Phase**: P1
- **Location**: Plan lines 893-973 (Sub-phase 1.1)
- **Issue**: Eight barrel files created with only comments and no exports. Acceptable for establishing directory structure.
- **Fix**: No action needed.

### 8. Re-export shim cleanup not scheduled
- **Severity**: minor
- **Phase**: P1
- **Location**: Plan lines 1041-1066 (Sub-phase 1.2.6)
- **Issue**: 4 transient shim files created for backward compatibility with no scheduled cleanup.
- **Fix**: Add a cleanup note to P6 to delete shim files and update consumers.

### 9. Density auto-selection is underspecified
- **Severity**: critical
- **Phase**: P1
- **Location**: Plan lines 2619-2654 (Sub-phase 1.9)
- **Issue**: This sub-phase provides no code -- only prose. Key questions unanswered: `MediaQuery` is not available above `MaterialApp`. Changing theme on resize causes full app rebuild.
- **Fix**: Provide concrete implementation using `MediaQueryData.fromView(View.of(context))`.

### 10. `ThemeSection` rewrite uses non-existent `RadioGroup` widget
- **Severity**: minor
- **Phase**: P1
- **Location**: Plan lines 1346-1370 (Sub-phase 1.5.3)
- **Issue**: `RadioGroup<AppThemeMode>` -- zero grep results for `class RadioGroup`. May be from a package import. Existing code already compiles with it, likely false alarm.
- **Fix**: Implementing agent should verify compilation.

## Summary

**2 blocking** and **3 critical** issues:
1. **Blocking**: `FieldGuideShadows` type mismatch -- `List<BoxShadow>` passed to `double elevation` parameters
2. **Blocking**: Getter-to-method migration breaks 70+ call sites
3. **Critical**: Lint rule scoping misses `shared/widgets/` and `core/router/`
4. **Critical**: `no_hardcoded_spacing` dual-implementation confusion
5. **Critical**: Density auto-selection has no implementation code
