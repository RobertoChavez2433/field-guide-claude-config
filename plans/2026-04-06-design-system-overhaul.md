# Design System Overhaul Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Overhaul the app's design system and UI layer to be fully tokenized, responsive across phone/tablet/desktop, and performant — eliminating ~400 magic number violations, collapsing the 1,777-line theme file, decomposing 11+ oversized screens, and establishing a 56-component atomic design system with 10 new lint rules.

**Spec:** `.claude/specs/2026-04-06-design-system-overhaul-spec.md`
**Tailor:** `.claude/tailor/2026-04-06-design-system-overhaul/`

**Architecture:** Bottom-up refactor: lint rules first (P0) to create violation inventory, then tokens + theme collapse (P1), responsive/animation infrastructure (P2), new components + migrations (P3), screen decomposition with full protocol (P4), performance optimization (P5), and polish + enforcement (P6). Each phase maintains zero analyzer errors.

**Tech Stack:** Flutter 3.38.9, Dart 3.10.7, ThemeExtension tokens, provider/ChangeNotifier, GoRouter, custom_lint_builder, Widgetbook

**Blast Radius:** 160 direct (DesignConstants), 114 direct (design_system barrel), 89 direct (FieldGuideColors), 29 direct (AppTheme) — 17 files for HC removal, 11 priority screens, 7 additional screens, 8 additional widgets, 12 golden test files

---

## Phase 0: Lint Rules

### Sub-phase 0.1: Create `no_raw_button` lint rule

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_button.dart`

**Agent**: `code-fixer-agent`

#### Step 0.1.1: Create `no_raw_button.dart`

Create the lint rule that catches `ElevatedButton`, `TextButton`, `OutlinedButton`, and `IconButton` usage outside design system and tests.

```dart
// File: fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_button.dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A25: Flags raw button widget usage in presentation files.
///
/// FROM SPEC: Design System Overhaul Phase 0 - "no raw button"
/// Use AppButton instead of raw ElevatedButton/TextButton/OutlinedButton/IconButton.
/// Severity: WARNING
class NoRawButton extends DartLintRule {
  NoRawButton() : super(code: _code);

  static const _code = LintCode(
    name: 'no_raw_button',
    problemMessage:
        'Avoid using raw button widgets (ElevatedButton, TextButton, '
        'OutlinedButton, IconButton). Use AppButton instead.',
    correctionMessage:
        'Replace with AppButton.primary(), AppButton.secondary(), '
        'AppButton.ghost(), or AppButton.icon() from the design system.',
    errorSeverity: ErrorSeverity.WARNING,
  );

  // WHY: These are the four raw Flutter button types that should be wrapped
  // by the design system AppButton component for consistent theming.
  static const _bannedTypes = {
    'ElevatedButton',
    'TextButton',
    'OutlinedButton',
    'IconButton',
  };

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    // NOTE: Windows path normalization is mandatory — backslashes break contains()
    final filePath = resolver.path.replaceAll('\\', '/');
    // WHY: Only enforce in UI layer where widgets are built
    // FROM SPEC: Scope includes /presentation/, /shared/widgets/, /core/router/
    final isUiLayer = filePath.contains('/presentation/') ||
        filePath.contains('/shared/widgets/') ||
        filePath.contains('/core/router/');
    if (!isUiLayer) return;
    // WHY: Tests legitimately construct raw widgets for testing
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    // WHY: Design system itself wraps these raw widgets
    if (filePath.contains('/core/design_system/')) return;

    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      if (_bannedTypes.contains(typeName)) {
        reporter.atNode(node.constructorName, _code);
      }
    });
  }
}
```

---

### Sub-phase 0.2: Create `no_raw_divider` lint rule

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_divider.dart`

**Agent**: `code-fixer-agent`

#### Step 0.2.1: Create `no_raw_divider.dart`

```dart
// File: fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_divider.dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A26: Flags raw Divider usage in presentation files.
///
/// FROM SPEC: Design System Overhaul Phase 0 - "no raw divider"
/// Use AppDivider instead of raw Divider for consistent theming.
/// Severity: WARNING
class NoRawDivider extends DartLintRule {
  NoRawDivider() : super(code: _code);

  static const _code = LintCode(
    name: 'no_raw_divider',
    problemMessage:
        'Avoid using raw Divider. Use AppDivider from the design system '
        'for consistent spacing and color.',
    correctionMessage:
        'Replace Divider() with AppDivider() from the design system barrel.',
    errorSeverity: ErrorSeverity.WARNING,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    // FROM SPEC: Scope includes /presentation/, /shared/widgets/, /core/router/
    final isUiLayer = filePath.contains('/presentation/') ||
        filePath.contains('/shared/widgets/') ||
        filePath.contains('/core/router/');
    if (!isUiLayer) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;

    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      // NOTE: Catches both Divider and VerticalDivider
      if (typeName == 'Divider' || typeName == 'VerticalDivider') {
        reporter.atNode(node.constructorName, _code);
      }
    });
  }
}
```

---

### Sub-phase 0.3: Create `no_raw_tooltip` lint rule

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_tooltip.dart`

**Agent**: `code-fixer-agent`

#### Step 0.3.1: Create `no_raw_tooltip.dart`

```dart
// File: fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_tooltip.dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A27: Flags raw Tooltip usage in presentation files.
///
/// FROM SPEC: Design System Overhaul Phase 0 - "no raw tooltip"
/// Use AppTooltip instead of raw Tooltip for consistent theming.
/// Severity: WARNING
class NoRawTooltip extends DartLintRule {
  NoRawTooltip() : super(code: _code);

  static const _code = LintCode(
    name: 'no_raw_tooltip',
    problemMessage:
        'Avoid using raw Tooltip. Use AppTooltip from the design system '
        'for consistent styling and positioning.',
    correctionMessage:
        'Replace Tooltip() with AppTooltip() from the design system barrel.',
    errorSeverity: ErrorSeverity.WARNING,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    // FROM SPEC: Scope includes /presentation/, /shared/widgets/, /core/router/
    final isUiLayer = filePath.contains('/presentation/') ||
        filePath.contains('/shared/widgets/') ||
        filePath.contains('/core/router/');
    if (!isUiLayer) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;

    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      if (typeName == 'Tooltip') {
        reporter.atNode(node.constructorName, _code);
      }
    });
  }
}
```

---

### Sub-phase 0.4: Create `no_raw_dropdown` lint rule

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_dropdown.dart`

**Agent**: `code-fixer-agent`

#### Step 0.4.1: Create `no_raw_dropdown.dart`

```dart
// File: fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_dropdown.dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A28: Flags raw DropdownButton usage in presentation files.
///
/// FROM SPEC: Design System Overhaul Phase 0 - "no raw dropdown"
/// Use AppDropdown instead of raw DropdownButton/DropdownButtonFormField.
/// Severity: WARNING
class NoRawDropdown extends DartLintRule {
  NoRawDropdown() : super(code: _code);

  static const _code = LintCode(
    name: 'no_raw_dropdown',
    problemMessage:
        'Avoid using raw DropdownButton or DropdownButtonFormField. '
        'Use AppDropdown from the design system for consistent theming.',
    correctionMessage:
        'Replace with AppDropdown<T>() from the design system barrel.',
    errorSeverity: ErrorSeverity.WARNING,
  );

  static const _bannedTypes = {
    'DropdownButton',
    'DropdownButtonFormField',
  };

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    // FROM SPEC: Scope includes /presentation/, /shared/widgets/, /core/router/
    final isUiLayer = filePath.contains('/presentation/') ||
        filePath.contains('/shared/widgets/') ||
        filePath.contains('/core/router/');
    if (!isUiLayer) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;

    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      if (_bannedTypes.contains(typeName)) {
        reporter.atNode(node.constructorName, _code);
      }
    });
  }
}
```

---

### Sub-phase 0.5: Extend existing `no_direct_snackbar` rule

**Files:**
- Modify: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_direct_snackbar.dart`

**Agent**: `code-fixer-agent`

#### Step 0.5.1: Update `no_direct_snackbar.dart` to also catch `SnackBar` constructor

The existing `no_direct_snackbar` already catches `showSnackBar` method invocations. Rather than creating a duplicate `no_raw_snackbar` rule, extend the existing rule to also catch direct `SnackBar` constructor usage (which would indicate someone building a SnackBar widget without using `SnackBarHelper`).

```dart
// File: fg_lint_packages/field_guide_lints/lib/architecture/rules/no_direct_snackbar.dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A22: Flags direct ScaffoldMessenger.showSnackBar usage AND raw SnackBar
/// construction in presentation files.
///
/// Use SnackBarHelper.show*() instead. Direct snackbar calls are only
/// allowed inside the centralized helper itself.
/// Severity: WARNING
///
/// FROM SPEC: Design System Overhaul Phase 0 - extends existing rule to also
/// catch raw SnackBar constructor usage, avoiding a duplicate no_raw_snackbar rule.
class NoDirectSnackbar extends DartLintRule {
  NoDirectSnackbar() : super(code: _code);

  static const _code = LintCode(
    name: 'no_direct_snackbar',
    problemMessage:
        'Use SnackBarHelper.show*() instead of direct ScaffoldMessenger/'
        'SnackBar calls. The helper provides consistent theming.',
    correctionMessage:
        'Replace with SnackBarHelper.showSuccess/showError/showInfo/showWarning',
    errorSeverity: ErrorSeverity.WARNING,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    // NOTE: This rule deliberately uses broader /lib/ scope (not just UI layer paths)
    // because showSnackBar calls in non-UI code are also a violation. This is
    // intentionally broader than the new P0 rules which scope to presentation only.
    if (!filePath.contains('/lib/')) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;
    // NOTE: Allow inside the helper itself
    if (filePath.contains('snackbar_helper')) return;

    // WHY: Catches ScaffoldMessenger.of(context).showSnackBar(...)
    context.registry.addMethodInvocation((node) {
      if (node.methodName.name == 'showSnackBar') {
        reporter.atNode(node.methodName, _code);
      }
    });

    // WHY: Also catches direct SnackBar(...) construction outside the helper.
    // This prevents building raw SnackBar widgets that bypass theming.
    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      if (typeName == 'SnackBar') {
        reporter.atNode(node.constructorName, _code);
      }
    });
  }
}
```

---

### Sub-phase 0.6: Create `no_hardcoded_spacing` lint rule

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_hardcoded_spacing.dart`

**Agent**: `code-fixer-agent`

#### Step 0.6.1: Create `no_hardcoded_spacing.dart`

This rule catches `EdgeInsets.all(N)`, `EdgeInsets.symmetric(...)`, `SizedBox(width: N, height: N)` with numeric literals. It uses a single `addInstanceCreationExpression` callback for both `EdgeInsets` and `SizedBox` (EdgeInsets named constructors are `InstanceCreationExpression` in the analyzer AST, not method invocations).

```dart
// File: fg_lint_packages/field_guide_lints/lib/architecture/rules/no_hardcoded_spacing.dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A29: Flags hardcoded spacing values in presentation files.
///
/// FROM SPEC: Design System Overhaul Phase 0 - "no hardcoded spacing"
/// Use DesignConstants.space* or FieldGuideSpacing tokens instead of
/// numeric literals in EdgeInsets and SizedBox spacers.
/// Severity: WARNING
class NoHardcodedSpacing extends DartLintRule {
  NoHardcodedSpacing() : super(code: _code);

  static const _code = LintCode(
    name: 'no_hardcoded_spacing',
    problemMessage:
        'Avoid hardcoded spacing values. Use DesignConstants.space* or '
        'FieldGuideSpacing.of(context).* tokens for consistent spacing.',
    correctionMessage:
        'Replace numeric literals with DesignConstants.space2 (8), '
        'DesignConstants.space4 (16), etc.',
    errorSeverity: ErrorSeverity.WARNING,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    // FROM SPEC: Scope includes /presentation/, /shared/widgets/, /core/router/
    final isUiLayer = filePath.contains('/presentation/') ||
        filePath.contains('/shared/widgets/') ||
        filePath.contains('/core/router/');
    if (!isUiLayer) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;

    // WHY: Catches both SizedBox(width: 8, height: 16) spacer patterns
    // AND EdgeInsets.all(8), EdgeInsets.symmetric(...), EdgeInsets.only(...),
    // EdgeInsets.fromLTRB(...) with numeric literal arguments.
    // NOTE: EdgeInsets.all(N) is a named constructor, which the analyzer
    // represents as InstanceCreationExpression, NOT MethodInvocation.
    // A single addInstanceCreationExpression callback handles both types.
    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      if (typeName == 'EdgeInsets' || typeName == 'SizedBox') {
        for (final arg in node.argumentList.arguments) {
          final expr = arg is NamedExpression ? arg.expression : arg;
          if (expr is IntegerLiteral || expr is DoubleLiteral) {
            reporter.atNode(node.constructorName, _code);
            return; // NOTE: Report once per call, not per argument
          }
        }
      }
    });
  }
}
```

The implementing agent MUST add `import 'package:analyzer/dart/ast/ast.dart' show NamedExpression, IntegerLiteral, DoubleLiteral;` at the top of the file.

---

### Sub-phase 0.7: Create `no_hardcoded_radius` lint rule

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_hardcoded_radius.dart`

**Agent**: `code-fixer-agent`

#### Step 0.7.1: Create `no_hardcoded_radius.dart`

```dart
// File: fg_lint_packages/field_guide_lints/lib/architecture/rules/no_hardcoded_radius.dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A30: Flags hardcoded BorderRadius values in presentation files.
///
/// FROM SPEC: Design System Overhaul Phase 0 - "no hardcoded radius"
/// Use DesignConstants.radius* or FieldGuideRadii tokens instead of
/// numeric literals in BorderRadius.circular().
/// Severity: WARNING
class NoHardcodedRadius extends DartLintRule {
  NoHardcodedRadius() : super(code: _code);

  static const _code = LintCode(
    name: 'no_hardcoded_radius',
    problemMessage:
        'Avoid hardcoded radius values in BorderRadius.circular(). '
        'Use DesignConstants.radius* or FieldGuideRadii.of(context).* tokens.',
    correctionMessage:
        'Replace numeric literal with DesignConstants.radiusSmall (8), '
        'DesignConstants.radiusMedium (12), etc.',
    errorSeverity: ErrorSeverity.WARNING,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    // FROM SPEC: Scope includes /presentation/, /shared/widgets/, /core/router/
    final isUiLayer = filePath.contains('/presentation/') ||
        filePath.contains('/shared/widgets/') ||
        filePath.contains('/core/router/');
    if (!isUiLayer) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;

    // WHY: BorderRadius.circular(N) is a constructor call.
    // Also catches BorderRadius.all(Radius.circular(N)).
    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      if (typeName == 'BorderRadius') {
        for (final arg in node.argumentList.arguments) {
          final expr = arg is NamedExpression ? arg.expression : arg;
          if (expr is IntegerLiteral || expr is DoubleLiteral) {
            reporter.atNode(node.constructorName, _code);
            return;
          }
        }
      }
    });
  }
}
```

**IMPORTANT**: The implementing agent must add `import 'package:analyzer/dart/ast/ast.dart' show NamedExpression, IntegerLiteral, DoubleLiteral;` at the top of the file.

---

### Sub-phase 0.8: Create `no_hardcoded_duration` lint rule

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_hardcoded_duration.dart`

**Agent**: `code-fixer-agent`

#### Step 0.8.1: Create `no_hardcoded_duration.dart`

```dart
// File: fg_lint_packages/field_guide_lints/lib/architecture/rules/no_hardcoded_duration.dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A31: Flags hardcoded Duration values in presentation files.
///
/// FROM SPEC: Design System Overhaul Phase 0 - "no hardcoded duration"
/// Use DesignConstants.animation* or FieldGuideMotion tokens instead of
/// inline Duration(milliseconds: N) in presentation code.
/// Severity: WARNING
class NoHardcodedDuration extends DartLintRule {
  NoHardcodedDuration() : super(code: _code);

  static const _code = LintCode(
    name: 'no_hardcoded_duration',
    problemMessage:
        'Avoid hardcoded Duration values in presentation code. '
        'Use DesignConstants.animation* or FieldGuideMotion.of(context).* tokens.',
    correctionMessage:
        'Replace Duration(milliseconds: 300) with '
        'DesignConstants.animationNormal or FieldGuideMotion.of(context).normal.',
    errorSeverity: ErrorSeverity.WARNING,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    // WHY: Only presentation layer — data/domain layers may use Duration legitimately
    // FROM SPEC: Scope includes /presentation/, /shared/widgets/, /core/router/
    final isUiLayer = filePath.contains('/presentation/') ||
        filePath.contains('/shared/widgets/') ||
        filePath.contains('/core/router/');
    if (!isUiLayer) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;

    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      if (typeName == 'Duration') {
        // WHY: Only flag Duration() with numeric literal arguments.
        // Duration(milliseconds: animationFast.inMilliseconds) is fine.
        for (final arg in node.argumentList.arguments) {
          final expr = arg is NamedExpression ? arg.expression : arg;
          if (expr is IntegerLiteral || expr is DoubleLiteral) {
            reporter.atNode(node.constructorName, _code);
            return;
          }
        }
      }
    });
  }
}
```

**IMPORTANT**: The implementing agent must add `import 'package:analyzer/dart/ast/ast.dart' show NamedExpression, IntegerLiteral, DoubleLiteral;` at the top.

---

### Sub-phase 0.9: Create `no_raw_navigator` lint rule

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_navigator.dart`

**Agent**: `code-fixer-agent`

#### Step 0.9.1: Create `no_raw_navigator.dart`

```dart
// File: fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_navigator.dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A32: Flags raw Navigator.push/pop usage in presentation files.
///
/// FROM SPEC: Design System Overhaul Phase 0 - "no raw navigator"
/// Use GoRouter (context.go/context.push) instead of Navigator.push/pop.
/// Severity: INFO (advisory, not blocking — some edge cases need Navigator)
class NoRawNavigator extends DartLintRule {
  NoRawNavigator() : super(code: _code);

  static const _code = LintCode(
    name: 'no_raw_navigator',
    // NOTE: INFO severity, not WARNING — this is advisory because some
    // patterns (e.g., closing dialogs) legitimately use Navigator.pop
    problemMessage:
        'Prefer GoRouter (context.go/context.push) over raw Navigator '
        'for route-level navigation. Navigator.pop is acceptable for '
        'dialogs and bottom sheets.',
    correctionMessage:
        'Replace Navigator.push/pushNamed with context.push/context.go '
        'from GoRouter.',
    errorSeverity: ErrorSeverity.INFO,
  );

  // WHY: These Navigator methods indicate route-level navigation that
  // should use GoRouter instead. We intentionally exclude pop/maybePop
  // since those are used for dialog/sheet dismissal.
  static const _bannedMethods = {
    'push',
    'pushNamed',
    'pushReplacement',
    'pushReplacementNamed',
    'pushAndRemoveUntil',
    'pushNamedAndRemoveUntil',
  };

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    // FROM SPEC: Scope includes /presentation/, /shared/widgets/, /core/router/
    // NOTE: For no_raw_navigator, /core/router/ is EXCLUDED (not included) because
    // router files legitimately use Navigator for transition builders.
    final isUiLayer = filePath.contains('/presentation/') ||
        filePath.contains('/shared/widgets/');
    if (!isUiLayer) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;

    context.registry.addMethodInvocation((node) {
      final target = node.realTarget;
      if (target == null) return;
      // NOTE: Matches Navigator.push(...), Navigator.of(context).push(...)
      // For Navigator.push static calls, target is SimpleIdentifier 'Navigator'
      final targetName = target is SimpleIdentifier ? target.name : '';
      if (targetName == 'Navigator' && _bannedMethods.contains(node.methodName.name)) {
        reporter.atNode(node.methodName, _code);
      }
    });
  }
}
```

**IMPORTANT**: The implementing agent must add `import 'package:analyzer/dart/ast/ast.dart' show SimpleIdentifier;` at the top. KNOWN LIMITATION: This rule only catches `Navigator.push()` static calls, not `Navigator.of(context).push()` -- acceptable at INFO severity.

---

### Sub-phase 0.10: Create `prefer_design_system_banner` lint rule

**Files:**
- Create: `fg_lint_packages/field_guide_lints/lib/architecture/rules/prefer_design_system_banner.dart`

**Agent**: `code-fixer-agent`

#### Step 0.10.1: Create `prefer_design_system_banner.dart`

```dart
// File: fg_lint_packages/field_guide_lints/lib/architecture/rules/prefer_design_system_banner.dart
import 'package:analyzer/error/error.dart' show ErrorSeverity;
import 'package:analyzer/error/listener.dart';
import 'package:custom_lint_builder/custom_lint_builder.dart';

/// A33: Flags feature-specific banner widgets that should compose AppBanner.
///
/// FROM SPEC: Design System Overhaul Phase 0 - "prefer design system banner"
/// Banner-like widgets (MaterialBanner, custom banner patterns) should compose
/// AppBanner or AppInfoBanner from the design system.
/// Severity: WARNING
class PreferDesignSystemBanner extends DartLintRule {
  PreferDesignSystemBanner() : super(code: _code);

  static const _code = LintCode(
    name: 'prefer_design_system_banner',
    problemMessage:
        'Avoid using raw MaterialBanner. Use AppInfoBanner or AppBanner '
        'from the design system for consistent banner styling.',
    correctionMessage:
        'Replace MaterialBanner() with AppInfoBanner() or compose from '
        'AppBanner for feature-specific banners.',
    errorSeverity: ErrorSeverity.WARNING,
  );

  @override
  void run(
    CustomLintResolver resolver,
    ErrorReporter reporter,
    CustomLintContext context,
  ) {
    final filePath = resolver.path.replaceAll('\\', '/');
    // FROM SPEC: Scope includes /presentation/, /shared/widgets/, /core/router/
    final isUiLayer = filePath.contains('/presentation/') ||
        filePath.contains('/shared/widgets/') ||
        filePath.contains('/core/router/');
    if (!isUiLayer) return;
    if (filePath.contains('/test/') || filePath.contains('/integration_test/')) return;
    if (filePath.contains('/core/design_system/')) return;

    context.registry.addInstanceCreationExpression((node) {
      final typeName = node.constructorName.type.name2.lexeme;
      if (typeName == 'MaterialBanner') {
        reporter.atNode(node.constructorName, _code);
      }
    });

    // WHY: Also catch showMaterialBanner method calls
    context.registry.addMethodInvocation((node) {
      if (node.methodName.name == 'showMaterialBanner') {
        reporter.atNode(node.methodName, _code);
      }
    });
  }
}
```

---

### Sub-phase 0.11: Register all new rules in `architecture_rules.dart`

**Files:**
- Modify: `fg_lint_packages/field_guide_lints/lib/architecture/architecture_rules.dart`

**Agent**: `code-fixer-agent`

#### Step 0.11.1: Update `architecture_rules.dart` with new imports and rule registrations

Add imports for all 9 new rule files (the 10th rule is the extended `no_direct_snackbar` which already exists) and add their instances to the `architectureRules` list.

```dart
// File: fg_lint_packages/field_guide_lints/lib/architecture/architecture_rules.dart
//
// ADD these imports after the existing import block (after line 24):
import 'rules/no_raw_button.dart';
import 'rules/no_raw_divider.dart';
import 'rules/no_raw_tooltip.dart';
import 'rules/no_raw_dropdown.dart';
import 'rules/no_hardcoded_spacing.dart';
import 'rules/no_hardcoded_radius.dart';
import 'rules/no_hardcoded_duration.dart';
import 'rules/no_raw_navigator.dart';
import 'rules/prefer_design_system_banner.dart';

// ADD these entries to the architectureRules list (after NoRawTextField() on line 50):
//   NoRawButton(),
//   NoRawDivider(),
//   NoRawTooltip(),
//   NoRawDropdown(),
//   NoHardcodedSpacing(),
//   NoHardcodedRadius(),
//   NoHardcodedDuration(),
//   NoRawNavigator(),
//   PreferDesignSystemBanner(),
```

The final file should look like:

```dart
import 'package:custom_lint_builder/custom_lint_builder.dart';
import 'rules/avoid_supabase_singleton.dart';
import 'rules/no_direct_database_construction.dart';
import 'rules/no_raw_sql_in_presentation.dart';
import 'rules/no_raw_sql_in_di.dart';
import 'rules/no_datasource_import_in_presentation.dart';
import 'rules/no_business_logic_in_di.dart';
import 'rules/single_composition_root.dart';
import 'rules/no_service_construction_in_widgets.dart';
import 'rules/no_silent_catch.dart';
import 'rules/max_file_length.dart';
import 'rules/max_import_count.dart';
import 'rules/no_deprecated_app_theme.dart';
import 'rules/no_hardcoded_colors.dart';
import 'rules/no_hardcoded_form_type.dart';
import 'rules/no_duplicate_service_instances.dart';
import 'rules/no_async_lifecycle_without_await.dart';
import 'rules/no_raw_alert_dialog.dart';
import 'rules/no_raw_show_dialog.dart';
import 'rules/no_raw_bottom_sheet.dart';
import 'rules/no_raw_scaffold.dart';
import 'rules/no_direct_snackbar.dart';
import 'rules/no_inline_text_style.dart';
import 'rules/no_raw_text_field.dart';
// FROM SPEC: Design System Overhaul Phase 0 — 9 new lint rules
import 'rules/no_raw_button.dart';
import 'rules/no_raw_divider.dart';
import 'rules/no_raw_tooltip.dart';
import 'rules/no_raw_dropdown.dart';
import 'rules/no_hardcoded_spacing.dart';
import 'rules/no_hardcoded_radius.dart';
import 'rules/no_hardcoded_duration.dart';
import 'rules/no_raw_navigator.dart';
import 'rules/prefer_design_system_banner.dart';

/// All architecture lint rules (A1-A15, A17-A33). A16 is a built-in lint.
final List<LintRule> architectureRules = [
  AvoidSupabaseSingleton(),
  NoDirectDatabaseConstruction(),
  NoRawSqlInPresentation(),
  NoRawSqlInDi(),
  NoDatasourceImportInPresentation(),
  NoBusinessLogicInDi(),
  SingleCompositionRoot(),
  NoServiceConstructionInWidgets(),
  NoSilentCatch(),
  MaxFileLength(),
  MaxImportCount(),
  NoDeprecatedAppTheme(),
  NoHardcodedColors(),
  NoHardcodedFormType(),
  NoDuplicateServiceInstances(),
  NoAsyncLifecycleWithoutAwait(),
  NoRawAlertDialog(),
  NoRawShowDialog(),
  NoRawBottomSheet(),
  NoRawScaffold(),
  NoDirectSnackbar(),
  NoInlineTextStyle(),
  NoRawTextField(),
  // FROM SPEC: Design System Overhaul Phase 0 — new rules
  NoRawButton(),
  NoRawDivider(),
  NoRawTooltip(),
  NoRawDropdown(),
  NoHardcodedSpacing(),
  NoHardcodedRadius(),
  NoHardcodedDuration(),
  NoRawNavigator(),
  PreferDesignSystemBanner(),
];
```

---

### Sub-phase 0.12: Verify lint rules compile and analyze

**Files:** (no new files)

**Agent**: `code-fixer-agent`

#### Step 0.12.1: Run analyzer on lint package

```
pwsh -Command "cd fg_lint_packages/field_guide_lints && flutter analyze"
```

**Expected**: Zero errors. Warnings about unused imports are acceptable at this stage (the rules reference types like `NamedExpression` that need analyzer imports).

#### Step 0.12.2: Run analyzer on main project to capture violation inventory

```
pwsh -Command "flutter analyze 2>&1 | Select-String 'no_raw_button|no_raw_divider|no_raw_tooltip|no_raw_dropdown|no_hardcoded_spacing|no_hardcoded_radius|no_hardcoded_duration|no_raw_navigator|prefer_design_system_banner'"
```

**Expected**: A list of new warnings from the custom lint rules. This is the baseline violation inventory. The count does NOT need to be zero -- these are intentional warnings that will be resolved in later phases as components are migrated to the design system.

**NOTE**: If `flutter analyze` does not surface custom_lint rules, the implementing agent should use `pwsh -Command "dart run custom_lint"` from the project root instead.

---

### Sub-phase 0.13: Create tests for all new lint rules

**Files:**
- Create: `fg_lint_packages/field_guide_lints/test/architecture/no_raw_button_test.dart`
- Create: `fg_lint_packages/field_guide_lints/test/architecture/no_raw_divider_test.dart`
- Create: `fg_lint_packages/field_guide_lints/test/architecture/no_raw_tooltip_test.dart`
- Create: `fg_lint_packages/field_guide_lints/test/architecture/no_raw_dropdown_test.dart`
- Create: `fg_lint_packages/field_guide_lints/test/architecture/no_hardcoded_spacing_test.dart`
- Create: `fg_lint_packages/field_guide_lints/test/architecture/no_hardcoded_radius_test.dart`
- Create: `fg_lint_packages/field_guide_lints/test/architecture/no_hardcoded_duration_test.dart`
- Create: `fg_lint_packages/field_guide_lints/test/architecture/no_raw_navigator_test.dart`
- Create: `fg_lint_packages/field_guide_lints/test/architecture/prefer_design_system_banner_test.dart`
- Modify: `fg_lint_packages/field_guide_lints/test/architecture/no_direct_snackbar_test.dart`

**Agent**: `code-fixer-agent`

#### Step 0.13.1: Create test files for all 9 new rules and update existing test

Every existing lint rule has a test file in `fg_lint_packages/field_guide_lints/test/architecture/`. Follow the same patterns (e.g., `no_raw_alert_dialog_test.dart`, `no_hardcoded_colors_test.dart`).

Each test file should:
1. Test that the rule flags violations in `/presentation/` paths
2. Test that the rule does NOT flag in `/test/`, `/core/design_system/`, or non-UI paths
3. Test that the rule does NOT flag when design system wrappers are used
4. For `no_direct_snackbar_test.dart`: add test cases for the new `SnackBar()` constructor detection

#### Step 0.13.2: Run lint package tests

```
pwsh -Command "cd fg_lint_packages/field_guide_lints && flutter test"
```

**Expected**: All tests pass.

---

## Phase 1: Tokens + Theme + HC Removal + Folder Structure

### Sub-phase 1.1: Create design system folder structure with barrel files

**Files:**
- Create: `lib/core/design_system/tokens/tokens.dart`
- Create: `lib/core/design_system/atoms/atoms.dart`
- Create: `lib/core/design_system/molecules/molecules.dart`
- Create: `lib/core/design_system/organisms/organisms.dart`
- Create: `lib/core/design_system/surfaces/surfaces.dart`
- Create: `lib/core/design_system/feedback/feedback.dart`
- Create: `lib/core/design_system/layout/layout.dart`
- Create: `lib/core/design_system/animation/animation.dart`

**Agent**: `code-fixer-agent`

#### Step 1.1.1: Create `tokens/tokens.dart` barrel

```dart
// File: lib/core/design_system/tokens/tokens.dart
// WHY: Sub-barrel for design token files. Re-exported by main design_system.dart barrel.
// New ThemeExtension files and moved token files will be exported here.

// NOTE: Exports will be added as files are moved/created in subsequent steps.
// Placeholder barrel to establish directory structure.
```

#### Step 1.1.2: Create `atoms/atoms.dart` barrel

```dart
// File: lib/core/design_system/atoms/atoms.dart
// WHY: Sub-barrel for atomic components (text, chip, toggle, icon, counter, progress).
// These are the smallest, most reusable building blocks.

// NOTE: Exports will be populated when components are moved from flat structure
// in Phase 2. This establishes the directory for future use.
```

#### Step 1.1.3: Create `molecules/molecules.dart` barrel

```dart
// File: lib/core/design_system/molecules/molecules.dart
// WHY: Sub-barrel for molecule components (search bar, list tile, section header).
// Molecules compose multiple atoms into reusable patterns.

// NOTE: Exports will be populated in Phase 2.
```

#### Step 1.1.4: Create `organisms/organisms.dart` barrel

```dart
// File: lib/core/design_system/organisms/organisms.dart
// WHY: Sub-barrel for organism components (section card, photo grid, form sections).
// Organisms are complex components composed of molecules and atoms.

// NOTE: Exports will be populated in Phase 2.
```

#### Step 1.1.5: Create `surfaces/surfaces.dart` barrel

```dart
// File: lib/core/design_system/surfaces/surfaces.dart
// WHY: Sub-barrel for surface/container components (scaffold, bottom sheet, dialog, glass card).
// Surfaces define layout boundaries and visual containers.

// NOTE: Exports will be populated in Phase 2.
```

#### Step 1.1.6: Create `feedback/feedback.dart` barrel

```dart
// File: lib/core/design_system/feedback/feedback.dart
// WHY: Sub-barrel for feedback components (snackbar, banners, empty/error/loading states).
// Feedback components communicate system state to users.

// NOTE: Exports will be populated in Phase 2+.
```

#### Step 1.1.7: Create `layout/layout.dart` barrel

```dart
// File: lib/core/design_system/layout/layout.dart
// WHY: Sub-barrel for responsive layout components (breakpoints, adaptive layouts, grids).
// Layout components handle responsive behavior across screen sizes.

// NOTE: Exports will be populated in Phase 3.
```

#### Step 1.1.8: Create `animation/animation.dart` barrel

```dart
// File: lib/core/design_system/animation/animation.dart
// WHY: Sub-barrel for animation utilities (staggered list, fade-in, transitions).
// Animation components provide consistent motion patterns.

// NOTE: Exports will be populated in Phase 4.
```

---

### Sub-phase 1.2: Move token files to `tokens/` directory

**Files:**
- Move: `lib/core/theme/colors.dart` -> `lib/core/design_system/tokens/app_colors.dart`
- Move: `lib/core/theme/design_constants.dart` -> `lib/core/design_system/tokens/design_constants.dart`
- Move: `lib/core/theme/field_guide_colors.dart` -> `lib/core/design_system/tokens/field_guide_colors.dart`
- Modify: `lib/core/design_system/tokens/tokens.dart`
- Modify: `lib/core/theme/theme.dart` (keep as re-export shim for backward compatibility)
- Modify: `lib/core/theme/app_theme.dart` (update imports)

**Agent**: `code-fixer-agent`

#### Step 1.2.1: Copy `colors.dart` to `tokens/app_colors.dart`

Create `lib/core/design_system/tokens/app_colors.dart` with the exact contents of `lib/core/theme/colors.dart`. Do NOT delete the original yet.

The file content is identical to the current `lib/core/theme/colors.dart` (218 lines). No changes to the class itself at this step.

#### Step 1.2.2: Copy `design_constants.dart` to `tokens/design_constants.dart`

Create `lib/core/design_system/tokens/design_constants.dart` with the exact contents of `lib/core/theme/design_constants.dart` (97 lines). Update the import at line 1:

```dart
// File: lib/core/design_system/tokens/design_constants.dart
import 'package:flutter/material.dart';
// NOTE: No other import changes needed — DesignConstants has no internal deps
```

#### Step 1.2.3: Copy `field_guide_colors.dart` to `tokens/field_guide_colors.dart`

Create `lib/core/design_system/tokens/field_guide_colors.dart` with the contents of `lib/core/theme/field_guide_colors.dart` (220 lines). Update the import on line 2:

```dart
// File: lib/core/design_system/tokens/field_guide_colors.dart
import 'package:flutter/material.dart';
import 'app_colors.dart'; // WHY: Changed from 'colors.dart' — now co-located in tokens/
```

#### Step 1.2.4: Update `tokens/tokens.dart` barrel

```dart
// File: lib/core/design_system/tokens/tokens.dart
// WHY: Sub-barrel for all design token files.
// These are re-exported by the main design_system.dart barrel.

export 'app_colors.dart';
export 'design_constants.dart';
export 'field_guide_colors.dart';
// NOTE: New ThemeExtension files (spacing, radii, motion, shadows) will be added
// in sub-phase 1.6 after they are created.
```

#### Step 1.2.5: Update `lib/core/theme/theme.dart` to re-export from new locations

```dart
// File: lib/core/theme/theme.dart
// WHY: Backward-compatibility shim. Keeps existing imports working during migration.
// NOTE: Once all consumers are updated, this file can be deleted.
export 'app_theme.dart';
export '../design_system/tokens/app_colors.dart';
export '../design_system/tokens/design_constants.dart';
export '../design_system/tokens/field_guide_colors.dart';
```

#### Step 1.2.6: Replace old files with re-export shims

Replace `lib/core/theme/colors.dart` with:

```dart
// File: lib/core/theme/colors.dart
// WHY: Re-export shim — actual file moved to design_system/tokens/app_colors.dart
// NOTE: This shim will be deleted once all direct importers are updated.
export '../design_system/tokens/app_colors.dart';
```

Replace `lib/core/theme/design_constants.dart` with:

```dart
// File: lib/core/theme/design_constants.dart
// WHY: Re-export shim — actual file moved to design_system/tokens/design_constants.dart
export '../design_system/tokens/design_constants.dart';
```

Replace `lib/core/theme/field_guide_colors.dart` with:

```dart
// File: lib/core/theme/field_guide_colors.dart
// WHY: Re-export shim — actual file moved to design_system/tokens/field_guide_colors.dart
// NOTE: All 4 re-export shims (colors.dart, design_constants.dart,
// field_guide_colors.dart, theme.dart) will be cleaned up in Phase 6.
export '../design_system/tokens/field_guide_colors.dart';
```

#### Step 1.2.7: Update `app_theme.dart` imports

In `lib/core/theme/app_theme.dart`, update lines 3-5:

```dart
// FROM:
// import 'colors.dart';
// import 'design_constants.dart';
// import 'field_guide_colors.dart';

// TO:
import 'package:construction_inspector/core/design_system/tokens/app_colors.dart';
import 'package:construction_inspector/core/design_system/tokens/design_constants.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_colors.dart';
```

// WHY: Direct imports to canonical location. The re-export shims in lib/core/theme/ are for external consumers only.

#### Step 1.2.8: Verify with analyzer

```
pwsh -Command "flutter analyze"
```

**Expected**: Zero errors. The re-export shims ensure all existing imports continue working. Warnings from Phase 0 lint rules are expected and acceptable.

---

### Sub-phase 1.3: Delete HC theme from `AppColors`

**Files:**
- Modify: `lib/core/design_system/tokens/app_colors.dart` (lines 84-101 — delete 13 `hc*` constants)

**Agent**: `code-fixer-agent`

#### Step 1.3.1: Remove all `hc*` constants from `AppColors`

In `lib/core/design_system/tokens/app_colors.dart`, delete the entire "HIGH CONTRAST THEME - COLORS" section (lines 84-101 in original, which includes the section comment and all 13 constants):

Delete these lines:
```
  // ==========================================================================
  // HIGH CONTRAST THEME - COLORS
  // ==========================================================================

  static const Color hcBackground = Color(0xFF000000);
  static const Color hcSurface = Color(0xFF121212);
  static const Color hcSurfaceElevated = Color(0xFF1E1E1E);
  static const Color hcBorder = Color(0xFFFFFFFF);
  static const Color hcPrimary = Color(0xFF00FFFF);
  static const Color hcAccent = Color(0xFFFFFF00);
  static const Color hcSuccess = Color(0xFF00FF00);
  static const Color hcError = Color(0xFFFF0000);
  static const Color hcWarning = Color(0xFFFFAA00);
  static const Color hcTextPrimary = Color(0xFFFFFFFF);
  static const Color hcTextSecondary = Color(0xFFCCCCCC);

  // Disabled / inactive states (HC theme)
  static const Color hcDisabledBackground = Color(0xFF333333);
  static const Color hcDisabledForeground = Color(0xFF666666);
```

---

### Sub-phase 1.4: Delete HC theme from `FieldGuideColors`

**Files:**
- Modify: `lib/core/design_system/tokens/field_guide_colors.dart` (delete `highContrast` const instance, lines 123-140 in original)

**Agent**: `code-fixer-agent`

#### Step 1.4.1: Remove `highContrast` instance from `FieldGuideColors`

In `lib/core/design_system/tokens/field_guide_colors.dart`, delete the entire `static const highContrast = FieldGuideColors(...)` block (originally lines 123-140):

Delete this block:
```
  static const highContrast = FieldGuideColors(
    surfaceElevated: AppColors.hcSurfaceElevated,
    surfaceGlass: Color(0xCC121212),
    surfaceBright: Color(0xFF333333),
    textTertiary: Color(0xFF808080),
    textInverse: Color(0xFF000000),
    statusSuccess: AppColors.hcSuccess,
    statusWarning: AppColors.hcWarning,
    statusInfo: AppColors.hcPrimary,
    warningBackground: Color(0x1AFFAA00),
    warningBorder: Color(0x33FFAA00),
    shadowLight: Colors.transparent,
    gradientStart: AppColors.hcPrimary,
    gradientEnd: AppColors.hcPrimary,
    accentAmber: AppColors.hcAccent,
    accentOrange: AppColors.hcWarning,
    dragHandleColor: Color(0xFFFFFFFF),
  );
```

---

### Sub-phase 1.4b: Expand FieldGuideColors with remaining theme-varying semantic colors

**Files:** Modify `lib/core/design_system/tokens/field_guide_colors.dart`
**Agent**: `code-fixer-agent`

#### Step 1.4b.1: Audit AppColors for theme-varying semantic colors not yet in FieldGuideColors

FROM SPEC: "FieldGuideColors: Already exists with 16 fields -- expand to absorb remaining AppColors semantic colors that vary per theme."

The implementing agent must read `app_colors.dart`, identify constants with DIFFERENT values in dark vs light themes (e.g., `surfaceElevated`, `surfaceBright`, `surfaceHighlight`, `textPrimary`, `textSecondary`, `textTertiary`, background colors), check which are NOT already in `FieldGuideColors`, add them as new fields with values in both `dark` and `light` static instances, and keep theme-invariant constants (like `statusSuccess`, `primaryCyan`) in `AppColors`.

#### Step 1.4b.2: Verify with `pwsh -Command "flutter analyze"` -- zero errors expected.

---

### Sub-phase 1.5: Delete HC theme from `AppTheme` and `ThemeProvider`

**Files:**
- Modify: `lib/core/theme/app_theme.dart` (delete `highContrastTheme` getter ~500 lines, delete HC re-exports ~15 lines)
- Modify: `lib/features/settings/presentation/providers/theme_provider.dart` (remove `highContrast` enum, `isHighContrast`, `setHighContrast`)
- Modify: `lib/features/settings/presentation/widgets/theme_section.dart` (remove HC radio option)

**Agent**: `code-fixer-agent`

#### Step 1.5.1: Remove `highContrastTheme` getter from `AppTheme`

In `lib/core/theme/app_theme.dart`:

1. Delete the entire `highContrastTheme` getter (lines 1265-1777 approximately). This is the block starting with:
   ```
   // ==========================================================================
   // HIGH CONTRAST THEME
   // ==========================================================================
   static ThemeData get highContrastTheme {
   ```
   All the way to its closing `}`.

2. Delete the HC color re-exports at the top of the class (lines 67-83 approximately):
   ```
   // High contrast theme
   static const Color hcBackground = AppColors.hcBackground;
   static const Color hcSurface = AppColors.hcSurface;
   static const Color hcSurfaceElevated = AppColors.hcSurfaceElevated;
   static const Color hcBorder = AppColors.hcBorder;
   static const Color hcPrimary = AppColors.hcPrimary;
   static const Color hcAccent = AppColors.hcAccent;
   static const Color hcError = AppColors.hcError;
   static const Color hcWarning = AppColors.hcWarning;
   static const Color hcTextPrimary = AppColors.hcTextPrimary;
   static const Color hcTextSecondary = AppColors.hcTextSecondary;
   static const Color hcDisabledBackground = AppColors.hcDisabledBackground;
   static const Color hcDisabledForeground = AppColors.hcDisabledForeground;
   static const Color hcSuccess = AppColors.hcSuccess;
   ```

#### Step 1.5.2: Update `ThemeProvider` — remove HC enum value and methods

Rewrite `lib/features/settings/presentation/providers/theme_provider.dart`:

```dart
// File: lib/features/settings/presentation/providers/theme_provider.dart
import 'dart:async' show unawaited;

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';

/// FROM SPEC: Design System Overhaul Phase 1 — 2-theme system (dark + light only).
/// HC theme removed per spec Section 9.
enum AppThemeMode {
  light,
  dark,
  // NOTE: highContrast removed. Old persisted 'highContrast' values safely
  // fall back to dark via the .where().firstOrNull pattern in _loadTheme().
}

/// Theme mode provider for managing app-wide theme state.
///
/// Supports 2 themes: Light and Dark (default).
/// Persists theme preference to SharedPreferences.
class ThemeProvider extends ChangeNotifier {
  static const String _themeKey = 'app_theme_mode';

  AppThemeMode _themeMode = AppThemeMode.dark; // WHY: Dark is default for field use
  bool _isLoading = true;

  ThemeProvider() {
    unawaited(_loadTheme());
  }

  /// Current app theme mode.
  AppThemeMode get themeMode => _themeMode;

  /// Whether theme is loading from preferences.
  bool get isLoading => _isLoading;

  /// Whether dark mode is active.
  bool get isDark => _themeMode == AppThemeMode.dark;

  /// Whether light mode is active.
  bool get isLight => _themeMode == AppThemeMode.light;

  /// Get the current ThemeData based on selected mode.
  ThemeData get currentTheme {
    switch (_themeMode) {
      case AppThemeMode.light:
        return AppTheme.lightTheme;
      case AppThemeMode.dark:
        return AppTheme.darkTheme;
    }
  }

  /// Get theme display name for UI.
  String get themeName {
    switch (_themeMode) {
      case AppThemeMode.light:
        return 'Light';
      case AppThemeMode.dark:
        return 'Dark';
    }
  }

  /// Load theme from SharedPreferences.
  Future<void> _loadTheme() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedMode = prefs.getString(_themeKey);

      if (savedMode != null) {
        // NOTE: Safe enum deserialization — defaults to dark if saved value is
        // unrecognized (handles old 'highContrast' gracefully)
        _themeMode = AppThemeMode.values
                .where((mode) => mode.name == savedMode)
                .firstOrNull ??
            AppThemeMode.dark;
      }
    } on Exception catch (e) {
      Logger.ui('[ThemeProvider] loadTheme error: $e');
      _themeMode = AppThemeMode.dark;
    }

    _isLoading = false;
    notifyListeners();
  }

  /// Set theme mode and persist.
  Future<void> setThemeMode(AppThemeMode mode) async {
    if (_themeMode == mode) return;

    _themeMode = mode;
    notifyListeners();

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_themeKey, mode.name);
    } on Exception catch (e) {
      Logger.ui('[ThemeProvider] theme persistence error: $e');
    }
  }

  /// Cycle to the next theme mode.
  Future<void> cycleTheme() async {
    final nextIndex = (_themeMode.index + 1) % AppThemeMode.values.length;
    await setThemeMode(AppThemeMode.values[nextIndex]);
  }

  /// Set to dark mode.
  Future<void> setDark() => setThemeMode(AppThemeMode.dark);

  /// Set to light mode.
  Future<void> setLight() => setThemeMode(AppThemeMode.light);
}
```

#### Step 1.5.3: Update `ThemeSection` — remove HC radio option

```dart
// File: lib/features/settings/presentation/widgets/theme_section.dart
import 'dart:async' show unawaited;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/shared/shared.dart';
import '../providers/theme_provider.dart';

class ThemeSection extends StatelessWidget {
  const ThemeSection({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<ThemeProvider>(
      builder: (context, themeProvider, _) {
        // NOTE: RadioGroup is imported via `shared.dart` barrel (from shared/widgets/).
        // The implementing agent must verify RadioGroup exists and compiles.
        // If it does not exist, use Column + RadioListTile directly.
        return RadioGroup<AppThemeMode>(
          key: TestingKeys.settingsThemeDropdown,
          groupValue: themeProvider.themeMode,
          onChanged: (value) {
            if (value != null) unawaited(themeProvider.setThemeMode(value));
          },
          // FROM SPEC: Phase 1 HC removal — only 2 theme options now
          child: const Column(
            children: [
              RadioListTile<AppThemeMode>(
                key: TestingKeys.settingsThemeDark,
                secondary: Icon(Icons.dark_mode),
                title: Text('Dark Mode'),
                value: AppThemeMode.dark,
              ),
              RadioListTile<AppThemeMode>(
                key: TestingKeys.settingsThemeLight,
                secondary: Icon(Icons.light_mode),
                title: Text('Light Mode'),
                value: AppThemeMode.light,
              ),
            ],
          ),
        );
      },
    );
  }
}
```

#### Step 1.5.4: Verify HC removal compiles

```
pwsh -Command "flutter analyze"
```

**Expected**: Zero errors. If there are errors from references to `AppColors.hc*` or `FieldGuideColors.highContrast` or `AppTheme.highContrastTheme` or `AppThemeMode.highContrast` in other files, those must be fixed before continuing. The blast-radius shows 3 lib files reference `AppTheme.highContrastTheme` — `budget_overview_card.dart` and `project_dashboard_screen.dart` do NOT reference HC directly (only `theme_provider.dart` does via `currentTheme` switch). Any remaining references should be removed.

---

### Sub-phase 1.6: HC test cleanup

**Files:**
- Delete: `test/golden/themes/high_contrast_theme_test.dart`
- Modify: `test/golden/test_helpers.dart` (remove HC from `testWidgetInAllThemes`)
- Modify: `test/core/theme/field_guide_colors_test.dart` (remove HC test cases)
- Modify: `test/golden/components/dashboard_widgets_test.dart` (remove HC variant)
- Modify: `test/golden/components/form_fields_test.dart` (remove HC variant)
- Modify: `test/golden/components/quantity_cards_test.dart` (remove HC variant)
- Modify: `test/golden/states/empty_state_test.dart` (remove HC variant)
- Modify: `test/golden/states/error_state_test.dart` (remove HC variant)
- Modify: `test/golden/states/loading_state_test.dart` (remove HC variant)
- Modify: `test/golden/widgets/confirmation_dialog_test.dart` (remove HC variant)
- Modify: `test/golden/widgets/entry_card_test.dart` (remove HC variant)
- Modify: `test/golden/widgets/project_card_test.dart` (remove HC variant)

**Agent**: `qa-testing-agent`

#### Step 1.6.1: Delete `high_contrast_theme_test.dart`

Delete the file `test/golden/themes/high_contrast_theme_test.dart` entirely.

#### Step 1.6.2: Update `test_helpers.dart` — remove HC from `testWidgetInAllThemes`

In `test/golden/test_helpers.dart`, update the `testWidgetInAllThemes` function (lines 86-121) to remove the HC test block:

```dart
/// Helper to test a widget against a golden file across both themes.
///
/// Creates separate golden files for dark and light themes.
/// FROM SPEC: HC theme removed in Design System Overhaul Phase 1.
Future<void> testWidgetInAllThemes(
  WidgetTester tester,
  Widget widget,
  String baseFileName, {
  Size? size,
}) async {
  // Test dark theme
  await pumpGoldenWidget(
    tester,
    goldenTestWrapper(widget, theme: AppTheme.darkTheme, size: size),
  );
  await expectLater(
    find.byType(Scaffold),
    matchesGoldenFile('../goldens/${baseFileName}_dark.png'),
  );

  // Test light theme
  await pumpGoldenWidget(
    tester,
    goldenTestWrapper(widget, theme: AppTheme.lightTheme, size: size),
  );
  await expectLater(
    find.byType(Scaffold),
    matchesGoldenFile('../goldens/${baseFileName}_light.png'),
  );
  // NOTE: High contrast block removed — HC theme deleted per spec Section 9
}
```

#### Step 1.6.3: Update `field_guide_colors_test.dart` — remove HC test cases

In `test/core/theme/field_guide_colors_test.dart`, remove all test cases that reference `FieldGuideColors.highContrast`. Specifically remove:

- `test('dark and highContrast surfaceGlass differ', ...)` (lines 16-20 approx)
- `test('light and highContrast textTertiary differ', ...)` (lines 22-27 approx)
- `test('HC shadowLight is transparent (no subtle shadows)', ...)` (lines 29-31 approx)
- `test('HC gradientStart equals gradientEnd (no gradient)', ...)` (lines 33-38 approx)

Keep the `test('dark and light surfaceElevated differ', ...)` test and all `of(context)` tests.

#### Step 1.6.4: Remove HC variants from all 9 golden test files

For each of these files, delete the `testWidgets` block that uses `AppTheme.highContrastTheme`:

1. `test/golden/components/dashboard_widgets_test.dart` — delete the `'renders in high contrast theme'` testWidgets block
2. `test/golden/components/form_fields_test.dart` — delete the HC testWidgets block
3. `test/golden/components/quantity_cards_test.dart` — delete the HC testWidgets block
4. `test/golden/states/empty_state_test.dart` — delete the HC testWidgets block
5. `test/golden/states/error_state_test.dart` — delete the HC testWidgets block
6. `test/golden/states/loading_state_test.dart` — delete the HC testWidgets block
7. `test/golden/widgets/confirmation_dialog_test.dart` — delete the HC testWidgets block
8. `test/golden/widgets/entry_card_test.dart` — delete the HC testWidgets block
9. `test/golden/widgets/project_card_test.dart` — delete the HC testWidgets block

Each deletion follows the same pattern: find the testWidgets call containing `AppTheme.highContrastTheme` and remove the entire test, including the `matchesGoldenFile('*_high_contrast.png')` expectation.

#### Step 1.6.5: Verify test cleanup compiles

```
pwsh -Command "flutter analyze"
```

**Expected**: Zero errors. The `AppTheme.highContrastTheme` symbol no longer exists, so any remaining references will show as compile errors.

---

### Sub-phase 1.7: Create new ThemeExtension classes

**Files:**
- Create: `lib/core/design_system/tokens/field_guide_spacing.dart`
- Create: `lib/core/design_system/tokens/field_guide_radii.dart`
- Create: `lib/core/design_system/tokens/field_guide_motion.dart`
- Create: `lib/core/design_system/tokens/field_guide_shadows.dart`
- Modify: `lib/core/design_system/tokens/tokens.dart` (add exports)

**Agent**: `code-fixer-agent`

#### Step 1.7.1: Create `FieldGuideSpacing` ThemeExtension

```dart
// File: lib/core/design_system/tokens/field_guide_spacing.dart
import 'dart:ui' show lerpDouble;
import 'package:flutter/material.dart';

/// FROM SPEC: Design System Overhaul Phase 1 — spacing token ThemeExtension.
///
/// WHY: Replaces hardcoded DesignConstants.space* references with context-aware
/// tokens. Follows the exact same pattern as FieldGuideColors (sentinel copyWith,
/// lerp, static of(context), const variant instances).
///
/// NOTE: Only the 6 primary spacing values are promoted to ThemeExtension fields.
/// Intermediate values (space3=12, space5=20, space10=40, space16=64) remain in
/// DesignConstants as static fallbacks — they are used infrequently and don't
/// need theme-variant behavior.
class FieldGuideSpacing extends ThemeExtension<FieldGuideSpacing> {
  const FieldGuideSpacing({
    required this.xs,
    required this.sm,
    required this.md,
    required this.lg,
    required this.xl,
    required this.xxl,
  });

  /// 4.0 — tight padding, icon gaps, badge margins
  final double xs;

  /// 8.0 — standard internal padding, chip spacing
  final double sm;

  /// 16.0 — section padding, card content insets
  final double md;

  /// 24.0 — section gaps, form field spacing
  final double lg;

  /// 32.0 — large section separators, header spacing
  final double xl;

  /// 48.0 — page-level padding, major section breaks
  final double xxl;

  // ===========================================================================
  // VARIANT INSTANCES
  // ===========================================================================

  /// Standard spacing — default density for medium-sized screens.
  /// WHY: Spacing does not vary by theme brightness — variants are density-based.
  static const standard = FieldGuideSpacing(
    xs: 4.0,   // FROM SPEC: maps to DesignConstants.space1
    sm: 8.0,   // FROM SPEC: maps to DesignConstants.space2
    md: 16.0,  // FROM SPEC: maps to DesignConstants.space4
    lg: 24.0,  // FROM SPEC: maps to DesignConstants.space6
    xl: 32.0,  // FROM SPEC: maps to DesignConstants.space8
    xxl: 48.0, // FROM SPEC: maps to DesignConstants.space12
  );

  /// Compact spacing — tighter density for phone portrait and data-dense screens.
  /// FROM SPEC §2: Density variant mapping — compact for 0-599px breakpoint.
  static const compact = FieldGuideSpacing(
    xs: 2.0,
    sm: 4.0,
    md: 12.0,
    lg: 16.0,
    xl: 24.0,
    xxl: 32.0,
  );

  /// Comfortable spacing — generous whitespace for desktop and large screens.
  /// FROM SPEC §2: Density variant mapping — comfortable for desktop breakpoint.
  static const comfortable = FieldGuideSpacing(
    xs: 6.0,
    sm: 12.0,
    md: 20.0,
    lg: 32.0,
    xl: 40.0,
    xxl: 56.0,
  );

  // ===========================================================================
  // CONVENIENCE ACCESSOR
  // ===========================================================================

  /// WHY: Mirrors FieldGuideColors.of(context) pattern.
  /// Falls back to standard if extension is missing (defensive).
  static FieldGuideSpacing of(BuildContext context) {
    return Theme.of(context).extension<FieldGuideSpacing>() ?? standard;
  }

  // ===========================================================================
  // ThemeExtension OVERRIDES
  // ===========================================================================

  static const _sentinel = Object();

  @override
  FieldGuideSpacing copyWith({
    Object? xs = _sentinel,
    Object? sm = _sentinel,
    Object? md = _sentinel,
    Object? lg = _sentinel,
    Object? xl = _sentinel,
    Object? xxl = _sentinel,
  }) {
    return FieldGuideSpacing(
      xs: identical(xs, _sentinel) ? this.xs : xs! as double,
      sm: identical(sm, _sentinel) ? this.sm : sm! as double,
      md: identical(md, _sentinel) ? this.md : md! as double,
      lg: identical(lg, _sentinel) ? this.lg : lg! as double,
      xl: identical(xl, _sentinel) ? this.xl : xl! as double,
      xxl: identical(xxl, _sentinel) ? this.xxl : xxl! as double,
    );
  }

  @override
  FieldGuideSpacing lerp(FieldGuideSpacing? other, double t) {
    if (other is! FieldGuideSpacing) return this;
    return FieldGuideSpacing(
      xs: lerpDouble(xs, other.xs, t)!,
      sm: lerpDouble(sm, other.sm, t)!,
      md: lerpDouble(md, other.md, t)!,
      lg: lerpDouble(lg, other.lg, t)!,
      xl: lerpDouble(xl, other.xl, t)!,
      xxl: lerpDouble(xxl, other.xxl, t)!,
    );
  }
}
```

#### Step 1.7.2: Create `FieldGuideRadii` ThemeExtension

```dart
// File: lib/core/design_system/tokens/field_guide_radii.dart
import 'dart:ui' show lerpDouble;
import 'package:flutter/material.dart';

/// FROM SPEC: Design System Overhaul Phase 1 — border radius token ThemeExtension.
///
/// WHY: Replaces hardcoded DesignConstants.radius* references with context-aware
/// tokens. Single variant (no density change per theme).
class FieldGuideRadii extends ThemeExtension<FieldGuideRadii> {
  const FieldGuideRadii({
    required this.xs,
    required this.sm,
    required this.compact,
    required this.md,
    required this.lg,
    required this.xl,
    required this.full,
  });

  /// 4.0 — tight chips, badges, inline tags
  final double xs;

  /// 8.0 — standard cards, inputs, buttons
  final double sm;

  /// 10.0 — bottom sheets, action menus (between sm and md)
  final double compact;

  /// 12.0 — dialogs, section cards
  final double md;

  /// 16.0 — large cards, feature panels
  final double lg;

  /// 24.0 — bottom sheet tops, modal headers
  final double xl;

  /// 999.0 — fully round (pills, circular badges)
  final double full;

  // ===========================================================================
  // VARIANT INSTANCES
  // ===========================================================================

  /// Standard radii — used for both dark and light themes.
  /// WHY: Radii do not vary by theme brightness — one instance suffices.
  static const standard = FieldGuideRadii(
    xs: 4.0,     // FROM SPEC: maps to DesignConstants.radiusXSmall
    sm: 8.0,     // FROM SPEC: maps to DesignConstants.radiusSmall
    compact: 10.0, // FROM SPEC: maps to DesignConstants.radiusCompact
    md: 12.0,    // FROM SPEC: maps to DesignConstants.radiusMedium
    lg: 16.0,    // FROM SPEC: maps to DesignConstants.radiusLarge
    xl: 24.0,    // FROM SPEC: maps to DesignConstants.radiusXLarge
    full: 999.0, // FROM SPEC: maps to DesignConstants.radiusFull
  );

  // ===========================================================================
  // CONVENIENCE ACCESSOR
  // ===========================================================================

  static FieldGuideRadii of(BuildContext context) {
    return Theme.of(context).extension<FieldGuideRadii>() ?? standard;
  }

  // ===========================================================================
  // ThemeExtension OVERRIDES
  // ===========================================================================

  static const _sentinel = Object();

  @override
  FieldGuideRadii copyWith({
    Object? xs = _sentinel,
    Object? sm = _sentinel,
    Object? compact = _sentinel,
    Object? md = _sentinel,
    Object? lg = _sentinel,
    Object? xl = _sentinel,
    Object? full = _sentinel,
  }) {
    return FieldGuideRadii(
      xs: identical(xs, _sentinel) ? this.xs : xs! as double,
      sm: identical(sm, _sentinel) ? this.sm : sm! as double,
      compact: identical(compact, _sentinel) ? this.compact : compact! as double,
      md: identical(md, _sentinel) ? this.md : md! as double,
      lg: identical(lg, _sentinel) ? this.lg : lg! as double,
      xl: identical(xl, _sentinel) ? this.xl : xl! as double,
      full: identical(full, _sentinel) ? this.full : full! as double,
    );
  }

  @override
  FieldGuideRadii lerp(FieldGuideRadii? other, double t) {
    if (other is! FieldGuideRadii) return this;
    return FieldGuideRadii(
      xs: lerpDouble(xs, other.xs, t)!,
      sm: lerpDouble(sm, other.sm, t)!,
      compact: lerpDouble(compact, other.compact, t)!,
      md: lerpDouble(md, other.md, t)!,
      lg: lerpDouble(lg, other.lg, t)!,
      xl: lerpDouble(xl, other.xl, t)!,
      full: lerpDouble(full, other.full, t)!,
    );
  }
}
```

#### Step 1.7.3: Create `FieldGuideMotion` ThemeExtension

```dart
// File: lib/core/design_system/tokens/field_guide_motion.dart
import 'package:flutter/material.dart';

/// FROM SPEC: Design System Overhaul Phase 1 — animation/motion token ThemeExtension.
///
/// WHY: Replaces hardcoded DesignConstants.animation* and curve* references.
/// Provides a `reduced` variant for accessibility (reduce-motion preference).
///
/// NOTE: Duration and Curve types cannot be lerped in a meaningful way,
/// so lerp() returns `other` directly when t >= 0.5, else `this`.
class FieldGuideMotion extends ThemeExtension<FieldGuideMotion> {
  const FieldGuideMotion({
    required this.fast,
    required this.normal,
    required this.slow,
    required this.pageTransition,
    required this.curveStandard,
    required this.curveDecelerate,
    required this.curveEmphasized,
    required this.curveAccelerate,
    required this.curveBounce,
    required this.curveSpring,
  });

  /// 150ms — micro-interactions, hover states, icon transitions
  final Duration fast;

  /// 300ms — standard transitions, expand/collapse
  final Duration normal;

  /// 500ms — large transitions, page-level animations
  final Duration slow;

  /// 350ms — page transition duration
  final Duration pageTransition;

  /// Curves.easeInOutCubic — standard motion curve
  final Curve curveStandard;

  /// Curves.easeOut — deceleration curve for entering elements
  final Curve curveDecelerate;

  /// FROM SPEC: Curves.easeInOutCubicEmphasized — emphasized motion curve
  /// for prominent transitions (hero animations, page shifts).
  final Curve curveEmphasized;

  /// Curves.easeIn — acceleration curve for exiting elements
  /// NOTE: Not in spec's FieldGuideMotion table but present in existing
  /// DesignConstants. Intentional spec extension needed for P2 animation work.
  final Curve curveAccelerate;

  /// Curves.elasticOut — bounce effect for attention-grabbing
  /// NOTE: Intentional spec extension from existing DesignConstants, needed for P2.
  final Curve curveBounce;

  /// Curves.easeOutBack — spring overshoot for playful transitions
  /// NOTE: Intentional spec extension from existing DesignConstants, needed for P2.
  final Curve curveSpring;

  // ===========================================================================
  // VARIANT INSTANCES
  // ===========================================================================

  /// Standard motion — default durations and curves.
  static const standard = FieldGuideMotion(
    fast: Duration(milliseconds: 150),           // FROM SPEC: DesignConstants.animationFast
    normal: Duration(milliseconds: 300),         // FROM SPEC: DesignConstants.animationNormal
    slow: Duration(milliseconds: 500),           // FROM SPEC: DesignConstants.animationSlow
    pageTransition: Duration(milliseconds: 350), // FROM SPEC: DesignConstants.animationPageTransition
    curveStandard: Curves.easeInOutCubic,        // FROM SPEC: DesignConstants.curveDefault
    curveDecelerate: Curves.easeOut,             // FROM SPEC: DesignConstants.curveDecelerate
    curveEmphasized: Curves.easeInOutCubicEmphasized, // FROM SPEC: emphasized motion curve
    curveAccelerate: Curves.easeIn,              // FROM SPEC: DesignConstants.curveAccelerate
    curveBounce: Curves.elasticOut,              // FROM SPEC: DesignConstants.curveBounce
    curveSpring: Curves.easeOutBack,             // FROM SPEC: DesignConstants.curveSpring
  );

  /// Reduced motion — for accessibility (prefers-reduced-motion).
  /// WHY: All durations are zero, curves are linear. This ensures
  /// animations complete instantly for users who prefer reduced motion.
  static const reduced = FieldGuideMotion(
    fast: Duration.zero,
    normal: Duration.zero,
    slow: Duration.zero,
    pageTransition: Duration.zero,
    curveStandard: Curves.linear,
    curveDecelerate: Curves.linear,
    curveEmphasized: Curves.linear,
    curveAccelerate: Curves.linear,
    curveBounce: Curves.linear,
    curveSpring: Curves.linear,
  );

  // ===========================================================================
  // CONVENIENCE ACCESSOR
  // ===========================================================================

  static FieldGuideMotion of(BuildContext context) {
    return Theme.of(context).extension<FieldGuideMotion>() ?? standard;
  }

  // ===========================================================================
  // ThemeExtension OVERRIDES
  // ===========================================================================

  static const _sentinel = Object();

  @override
  FieldGuideMotion copyWith({
    Object? fast = _sentinel,
    Object? normal = _sentinel,
    Object? slow = _sentinel,
    Object? pageTransition = _sentinel,
    Object? curveStandard = _sentinel,
    Object? curveDecelerate = _sentinel,
    Object? curveEmphasized = _sentinel,
    Object? curveAccelerate = _sentinel,
    Object? curveBounce = _sentinel,
    Object? curveSpring = _sentinel,
  }) {
    return FieldGuideMotion(
      fast: identical(fast, _sentinel) ? this.fast : fast! as Duration,
      normal: identical(normal, _sentinel) ? this.normal : normal! as Duration,
      slow: identical(slow, _sentinel) ? this.slow : slow! as Duration,
      pageTransition: identical(pageTransition, _sentinel) ? this.pageTransition : pageTransition! as Duration,
      curveStandard: identical(curveStandard, _sentinel) ? this.curveStandard : curveStandard! as Curve,
      curveDecelerate: identical(curveDecelerate, _sentinel) ? this.curveDecelerate : curveDecelerate! as Curve,
      curveEmphasized: identical(curveEmphasized, _sentinel) ? this.curveEmphasized : curveEmphasized! as Curve,
      curveAccelerate: identical(curveAccelerate, _sentinel) ? this.curveAccelerate : curveAccelerate! as Curve,
      curveBounce: identical(curveBounce, _sentinel) ? this.curveBounce : curveBounce! as Curve,
      curveSpring: identical(curveSpring, _sentinel) ? this.curveSpring : curveSpring! as Curve,
    );
  }

  @override
  FieldGuideMotion lerp(FieldGuideMotion? other, double t) {
    // NOTE: Duration and Curve cannot be meaningfully interpolated.
    // Use snap behavior: return other when t >= 0.5, else this.
    if (other is! FieldGuideMotion) return this;
    return t < 0.5 ? this : other;
  }
}
```

#### Step 1.7.4: Create `FieldGuideShadows` ThemeExtension

```dart
// File: lib/core/design_system/tokens/field_guide_shadows.dart
import 'package:flutter/material.dart';

/// FROM SPEC: Design System Overhaul Phase 1 — shadow token ThemeExtension.
///
/// WHY: Replaces hardcoded DesignConstants.elevation* references with context-aware
/// shadow tokens using `List<BoxShadow>` (per spec). Provides a `flat` variant
/// (no shadows) for accessibility or reduced visual complexity preferences.
///
/// NOTE: Fields are `List<BoxShadow>` as required by spec, not double elevation
/// values. This allows direct use in `BoxDecoration(boxShadow: ...)` without
/// Material elevation indirection.
class FieldGuideShadows extends ThemeExtension<FieldGuideShadows> {
  const FieldGuideShadows({
    required this.none,
    required this.low,
    required this.medium,
    required this.high,
    required this.modal,
  });

  /// No shadow — FROM SPEC: empty list for unshadowed surfaces.
  final List<BoxShadow> none;

  /// Subtle lift for cards, list tiles (elevation ~2)
  final List<BoxShadow> low;

  /// Standard elevation for FABs, nav bars (elevation ~4)
  final List<BoxShadow> medium;

  /// Prominent elevation for popovers, menus (elevation ~8)
  final List<BoxShadow> high;

  /// Maximum elevation for dialogs, modals (elevation ~16)
  final List<BoxShadow> modal;

  // ===========================================================================
  // VARIANT INSTANCES
  // ===========================================================================

  /// Standard shadows — default shadow values.
  /// FROM SPEC: Each level maps to DesignConstants.elevation* equivalents.
  static const standard = FieldGuideShadows(
    none: [],
    low: [
      BoxShadow(color: Color(0x33000000), blurRadius: 4, offset: Offset(0, 1)),
      BoxShadow(color: Color(0x1F000000), blurRadius: 2, offset: Offset(0, 1)),
    ],
    medium: [
      BoxShadow(color: Color(0x33000000), blurRadius: 8, offset: Offset(0, 2)),
      BoxShadow(color: Color(0x24000000), blurRadius: 4, offset: Offset(0, 1)),
    ],
    high: [
      BoxShadow(color: Color(0x33000000), blurRadius: 16, offset: Offset(0, 4)),
      BoxShadow(color: Color(0x24000000), blurRadius: 8, offset: Offset(0, 2)),
    ],
    modal: [
      BoxShadow(color: Color(0x33000000), blurRadius: 24, offset: Offset(0, 8)),
      BoxShadow(color: Color(0x24000000), blurRadius: 12, offset: Offset(0, 4)),
    ],
  );

  /// Flat — no shadows. WHY: For accessibility or high-contrast-like modes
  /// where shadows add visual noise without communicating depth.
  static const flat = FieldGuideShadows(
    none: [],
    low: [],
    medium: [],
    high: [],
    modal: [],
  );

  // ===========================================================================
  // CONVENIENCE ACCESSOR
  // ===========================================================================

  static FieldGuideShadows of(BuildContext context) {
    return Theme.of(context).extension<FieldGuideShadows>() ?? standard;
  }

  // ===========================================================================
  // MATERIAL ELEVATION GETTERS
  // ===========================================================================

  // WHY: Material component themes (AppBarTheme, CardTheme, FAB, Dialog, etc.)
  // accept `double elevation` parameters, not List<BoxShadow>. These getters
  // provide numeric elevation values that correspond to each shadow level.
  // Use shadows.low (List<BoxShadow>) for BoxDecoration.boxShadow and
  // shadows.elevationLow (double) for Material elevation parameters.
  double get elevationNone => 0;
  double get elevationLow => 2;
  double get elevationMedium => 4;
  double get elevationHigh => 8;
  double get elevationModal => 16;

  // ===========================================================================
  // ThemeExtension OVERRIDES
  // ===========================================================================

  static const _sentinel = Object();

  @override
  FieldGuideShadows copyWith({
    Object? none = _sentinel,
    Object? low = _sentinel,
    Object? medium = _sentinel,
    Object? high = _sentinel,
    Object? modal = _sentinel,
  }) {
    return FieldGuideShadows(
      none: identical(none, _sentinel) ? this.none : none! as List<BoxShadow>,
      low: identical(low, _sentinel) ? this.low : low! as List<BoxShadow>,
      medium: identical(medium, _sentinel) ? this.medium : medium! as List<BoxShadow>,
      high: identical(high, _sentinel) ? this.high : high! as List<BoxShadow>,
      modal: identical(modal, _sentinel) ? this.modal : modal! as List<BoxShadow>,
    );
  }

  @override
  FieldGuideShadows lerp(FieldGuideShadows? other, double t) {
    if (other is! FieldGuideShadows) return this;
    // NOTE: BoxShadow.lerpList handles per-element interpolation.
    return FieldGuideShadows(
      none: BoxShadow.lerpList(none, other.none, t),
      low: BoxShadow.lerpList(low, other.low, t),
      medium: BoxShadow.lerpList(medium, other.medium, t),
      high: BoxShadow.lerpList(high, other.high, t),
      modal: BoxShadow.lerpList(modal, other.modal, t),
    );
  }
}
```

#### Step 1.7.5: Update `tokens/tokens.dart` barrel with new exports

```dart
// File: lib/core/design_system/tokens/tokens.dart
// WHY: Sub-barrel for all design token files.
// Re-exported by the main design_system.dart barrel.

export 'app_colors.dart';
export 'design_constants.dart';
export 'field_guide_colors.dart';
// FROM SPEC: New ThemeExtension token classes — Phase 1
export 'field_guide_spacing.dart';
export 'field_guide_radii.dart';
export 'field_guide_motion.dart';
export 'field_guide_shadows.dart';
```

#### Step 1.7.6: Verify new extensions compile

```
pwsh -Command "flutter analyze"
```

**Expected**: Zero errors.

---

### Sub-phase 1.8: Theme collapse — data-driven `AppTheme.build()`

**Files:**
- Modify: `lib/core/theme/app_theme.dart` (major refactor: collapse to data-driven builder)

**Agent**: `code-fixer-agent`

#### Step 1.8.1: Refactor `AppTheme` to data-driven builder

This is the largest single step. The current `AppTheme` has ~1,265 lines (after HC deletion). Refactor to a `build()` method that accepts token parameters, with `darkTheme` and `lightTheme` as thin wrappers. Target: <400 lines total.

The implementing agent should:

1. Extract the `ColorScheme` for dark and light into private static const fields (`_darkColorScheme`, `_lightColorScheme`).

2. Create a `static ThemeData build({...})` method that takes `ColorScheme`, `FieldGuideColors`, `FieldGuideSpacing`, `FieldGuideRadii`, `FieldGuideMotion`, `FieldGuideShadows`, `Brightness`, and a scaffold background color. This method builds ALL component themes using the parameters instead of hardcoded values.

3. Convert `darkTheme` and `lightTheme` getters to delegate to `build()`.

4. Keep the deprecated re-exports section at the top UNCHANGED (those will be removed in a separate cleanup phase).

The complete `AppTheme` class structure should be:

```dart
// File: lib/core/theme/app_theme.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:construction_inspector/core/design_system/tokens/app_colors.dart';
import 'package:construction_inspector/core/design_system/tokens/design_constants.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_colors.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_spacing.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_radii.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_motion.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_shadows.dart';

/// FROM SPEC: Design System Overhaul Phase 1 — data-driven theme builder.
/// WHY: Collapsed from 3 monolithic getters (~1,777 lines) to a single build()
/// method (~350 lines) that eliminates duplication across themes.
class AppTheme {
  // ==========================================================================
  // COLOR EXPORTS (for backwards compatibility — will be removed in Phase 6)
  // ==========================================================================

  // [KEEP ALL EXISTING DEPRECATED RE-EXPORTS UNCHANGED]
  // ... (the implementing agent should copy lines 14-168 from the current file,
  //      minus the HC re-exports which were deleted in step 1.5.1)

  // ==========================================================================
  // COLOR SCHEMES
  // ==========================================================================

  static const _darkColorScheme = ColorScheme.dark(
    brightness: Brightness.dark,
    primary: AppColors.primaryCyan,
    onPrimary: AppColors.textInverse,
    primaryContainer: AppColors.primaryDark,
    onPrimaryContainer: AppColors.textPrimary,
    secondary: AppColors.accentAmber,
    onSecondary: AppColors.textInverse,
    secondaryContainer: AppColors.accentOrange,
    onSecondaryContainer: AppColors.textPrimary,
    tertiary: AppColors.primaryBlue,
    onTertiary: AppColors.textInverse,
    tertiaryContainer: AppColors.primaryDark,
    onTertiaryContainer: AppColors.textPrimary,
    error: AppColors.statusError,
    onError: AppColors.textPrimary,
    errorContainer: Color(0xFF8B1A10),
    onErrorContainer: Color(0xFFFFDAD4),
    surface: AppColors.surfaceDark,
    onSurface: AppColors.textPrimary,
    surfaceContainerHighest: AppColors.surfaceHighlight,
    onSurfaceVariant: AppColors.textSecondary,
    outline: AppColors.surfaceHighlight,
    outlineVariant: AppColors.surfaceBright,
    shadow: Colors.black,
    scrim: Colors.black,
    inverseSurface: AppColors.textPrimary,
    onInverseSurface: AppColors.backgroundDark,
    inversePrimary: AppColors.primaryDark,
  );

  // NOTE: The implementing agent must extract the light ColorScheme from the
  // existing lightTheme getter (lines 816-860 approximately) into a similar
  // _lightColorScheme constant.
  static const _lightColorScheme = ColorScheme.light(
    brightness: Brightness.light,
    primary: AppColors.primaryBlue,
    onPrimary: Colors.white,
    // REQUIRED: The implementing agent MUST extract ALL remaining ColorScheme
    // fields from the existing lightTheme getter (~lines 816-860 in current
    // app_theme.dart). Reference _darkColorScheme above for the full field list.
    // Fields needed: primaryContainer, onPrimaryContainer, secondary, onSecondary,
    // secondaryContainer, onSecondaryContainer, tertiary, onTertiary,
    // tertiaryContainer, onTertiaryContainer, error, onError, errorContainer,
    // onErrorContainer, surface, onSurface, surfaceContainerHighest,
    // onSurfaceVariant, outline, outlineVariant, shadow, scrim,
    // inverseSurface, onInverseSurface, inversePrimary.
    // DO NOT leave this as a placeholder — all fields must be specified.
  );

  // ==========================================================================
  // THEME BUILDER
  // ==========================================================================

  /// WHY: Single builder eliminates duplication. Each theme just passes its
  /// token set. Component themes reference parameters, not hardcoded colors.
  static ThemeData build({
    required ColorScheme colorScheme,
    required FieldGuideColors colors,
    required FieldGuideSpacing spacing,
    required FieldGuideRadii radii,
    required FieldGuideMotion motion,
    required FieldGuideShadows shadows,
    required Color scaffoldBackgroundColor,
    required SystemUiOverlayStyle systemOverlayStyle,
  }) {
    final primary = colorScheme.primary;
    final onPrimary = colorScheme.onPrimary;
    final surface = colorScheme.surface;
    final onSurface = colorScheme.onSurface;
    final onSurfaceVariant = colorScheme.onSurfaceVariant;
    final outline = colorScheme.outline;

    return ThemeData(
      useMaterial3: true,
      brightness: colorScheme.brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: scaffoldBackgroundColor,
      extensions: [colors, spacing, radii, motion, shadows],

      // App Bar
      appBarTheme: AppBarTheme(
        backgroundColor: surface,
        foregroundColor: onSurface,
        elevation: 0,
        scrolledUnderElevation: shadows.elevationMedium,
        centerTitle: false,
        titleTextStyle: TextStyle(
          fontFamily: 'Roboto',
          fontSize: 22,
          fontWeight: FontWeight.w700,
          color: onSurface,
          letterSpacing: 0.15,
        ),
        iconTheme: IconThemeData(color: onSurface, size: 24),
        actionsIconTheme: IconThemeData(color: primary, size: 24),
        systemOverlayStyle: systemOverlayStyle,
      ),

      // Cards
      cardTheme: CardThemeData(
        color: colors.surfaceElevated,
        shadowColor: Colors.black.withValues(alpha: 0.3),
        elevation: shadows.elevationLow,
        margin: EdgeInsets.symmetric(vertical: spacing.xs, horizontal: 0),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radii.md),
          side: BorderSide(
            color: outline.withValues(alpha: 0.3),
            width: 1,
          ),
        ),
      ),

      // Input Decoration
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        hoverColor: colors.surfaceElevated,
        contentPadding: EdgeInsets.symmetric(
          horizontal: spacing.md,
          vertical: spacing.md,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radii.sm),
          borderSide: BorderSide(color: outline, width: 1),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radii.sm),
          borderSide: BorderSide(color: outline, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radii.sm),
          borderSide: BorderSide(color: primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radii.sm),
          borderSide: BorderSide(color: colorScheme.error, width: 1),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radii.sm),
          borderSide: BorderSide(color: colorScheme.error, width: 2),
        ),
        disabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(radii.sm),
          borderSide: BorderSide(
            color: outline.withValues(alpha: 0.5),
            width: 1,
          ),
        ),
        labelStyle: TextStyle(
          fontFamily: 'Roboto', fontSize: 14,
          fontWeight: FontWeight.w500, color: onSurfaceVariant,
        ),
        floatingLabelStyle: TextStyle(
          fontFamily: 'Roboto', fontSize: 12,
          fontWeight: FontWeight.w600, color: primary,
        ),
        hintStyle: TextStyle(
          fontFamily: 'Roboto', fontSize: 14,
          fontWeight: FontWeight.w400, color: colors.textTertiary,
        ),
        prefixIconColor: onSurfaceVariant,
        suffixIconColor: onSurfaceVariant,
      ),

      // Elevated Button
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: onPrimary,
          disabledBackgroundColor: colors.surfaceBright,
          disabledForegroundColor: colors.textTertiary,
          elevation: shadows.elevationLow,
          shadowColor: primary.withValues(alpha: 0.3),
          padding: EdgeInsets.symmetric(
            horizontal: spacing.lg, vertical: spacing.md,
          ),
          minimumSize: const Size(88, DesignConstants.touchTargetMin),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radii.md),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Roboto', fontSize: 15,
            fontWeight: FontWeight.w700, letterSpacing: 0.5,
          ),
        ),
      ),

      // Filled Button
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: colors.surfaceElevated,
          foregroundColor: onSurface,
          disabledBackgroundColor: colors.surfaceBright,
          disabledForegroundColor: colors.textTertiary,
          padding: EdgeInsets.symmetric(
            horizontal: spacing.lg, vertical: spacing.md,
          ),
          minimumSize: const Size(88, DesignConstants.touchTargetMin),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radii.md),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Roboto', fontSize: 15,
            fontWeight: FontWeight.w700, letterSpacing: 0.5,
          ),
        ),
      ),

      // Outlined Button
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primary,
          disabledForegroundColor: colors.textTertiary,
          padding: EdgeInsets.symmetric(
            horizontal: spacing.lg, vertical: spacing.md,
          ),
          minimumSize: const Size(88, DesignConstants.touchTargetMin),
          side: BorderSide(color: primary, width: 2),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radii.md),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Roboto', fontSize: 15,
            fontWeight: FontWeight.w700, letterSpacing: 0.5,
          ),
        ),
      ),

      // Text Button
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primary,
          disabledForegroundColor: colors.textTertiary,
          padding: EdgeInsets.symmetric(
            horizontal: spacing.md, vertical: DesignConstants.space3,
          ),
          minimumSize: const Size(64, 40),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(radii.sm),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Roboto', fontSize: 14,
            fontWeight: FontWeight.w600, letterSpacing: 0.5,
          ),
        ),
      ),

      // Icon Button
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          foregroundColor: onSurfaceVariant,
          hoverColor: primary.withValues(alpha: 0.08),
          focusColor: primary.withValues(alpha: 0.12),
          highlightColor: primary.withValues(alpha: 0.12),
          minimumSize: const Size(
            DesignConstants.touchTargetMin, DesignConstants.touchTargetMin,
          ),
          iconSize: 24,
        ),
      ),

      // FAB
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: colorScheme.secondary,
        foregroundColor: onPrimary,
        elevation: shadows.elevationMedium,
        focusElevation: shadows.elevationHigh,
        hoverElevation: shadows.elevationHigh,
        highlightElevation: shadows.elevationHigh,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radii.lg),
        ),
        extendedTextStyle: const TextStyle(
          fontFamily: 'Roboto', fontSize: 15,
          fontWeight: FontWeight.w700, letterSpacing: 0.5,
        ),
        sizeConstraints: const BoxConstraints.tightFor(
          width: DesignConstants.touchTargetComfortable,
          height: DesignConstants.touchTargetComfortable,
        ),
      ),

      // Navigation Bar
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface,
        indicatorColor: primary.withValues(alpha: 0.2),
        surfaceTintColor: Colors.transparent,
        elevation: shadows.elevationMedium,
        height: 80,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        iconTheme: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return IconThemeData(color: primary, size: 28);
          }
          return IconThemeData(color: onSurfaceVariant, size: 24);
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return TextStyle(
              fontFamily: 'Roboto', fontSize: 13,
              fontWeight: FontWeight.w700, color: primary,
              letterSpacing: 0.4,
            );
          }
          return TextStyle(
            fontFamily: 'Roboto', fontSize: 12,
            fontWeight: FontWeight.w600, color: onSurfaceVariant,
            letterSpacing: 0.4,
          );
        }),
      ),

      // Dialog
      dialogTheme: DialogThemeData(
        backgroundColor: colors.surfaceElevated,
        elevation: shadows.elevationModal,
        shadowColor: Colors.black.withValues(alpha: 0.5),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radii.lg),
          side: BorderSide(
            color: outline.withValues(alpha: 0.5),
            width: 1,
          ),
        ),
        titleTextStyle: TextStyle(
          fontFamily: 'Roboto', fontSize: 22,
          fontWeight: FontWeight.w700, color: onSurface,
          letterSpacing: 0.15,
        ),
        contentTextStyle: TextStyle(
          fontFamily: 'Roboto', fontSize: 15,
          fontWeight: FontWeight.w400, color: onSurfaceVariant,
          height: 1.5,
        ),
      ),

      // Bottom Sheet
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: colors.surfaceElevated,
        elevation: shadows.elevationModal,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(radii.xl),
          ),
        ),
        dragHandleColor: colors.surfaceBright,
        dragHandleSize: const Size(40, 4),
      ),

      // Snack Bar
      snackBarTheme: SnackBarThemeData(
        backgroundColor: colors.surfaceElevated,
        contentTextStyle: TextStyle(
          fontFamily: 'Roboto', fontSize: 15,
          fontWeight: FontWeight.w500, color: onSurface,
        ),
        actionTextColor: primary,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radii.md),
          side: BorderSide(
            color: outline.withValues(alpha: 0.5),
            width: 1,
          ),
        ),
        elevation: shadows.elevationMedium,
      ),

      // Divider
      dividerTheme: DividerThemeData(
        color: outline,
        thickness: 1,
        space: 1,
      ),

      // Progress Indicators
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: primary,
        linearTrackColor: colors.surfaceBright,
        circularTrackColor: colors.surfaceBright,
      ),

      // Text Theme
      // NOTE: The implementing agent must extract the full TextTheme from the
      // existing dark theme getter. Text colors should use onSurface/onSurfaceVariant
      // parameters. The text theme is identical structure for dark and light — only
      // the color values change (via colorScheme references).
      textTheme: TextTheme(
        displayLarge: TextStyle(fontFamily: 'Roboto', fontSize: 57, fontWeight: FontWeight.w700, color: onSurface, letterSpacing: -0.25, height: 1.12),
        displayMedium: TextStyle(fontFamily: 'Roboto', fontSize: 45, fontWeight: FontWeight.w600, color: onSurface, letterSpacing: 0, height: 1.16),
        displaySmall: TextStyle(fontFamily: 'Roboto', fontSize: 36, fontWeight: FontWeight.w600, color: onSurface, letterSpacing: 0, height: 1.22),
        headlineLarge: TextStyle(fontFamily: 'Roboto', fontSize: 32, fontWeight: FontWeight.w700, color: onSurface, letterSpacing: 0, height: 1.25),
        headlineMedium: TextStyle(fontFamily: 'Roboto', fontSize: 28, fontWeight: FontWeight.w700, color: onSurface, letterSpacing: 0, height: 1.29),
        headlineSmall: TextStyle(fontFamily: 'Roboto', fontSize: 24, fontWeight: FontWeight.w700, color: onSurface, letterSpacing: 0, height: 1.33),
        titleLarge: TextStyle(fontFamily: 'Roboto', fontSize: 22, fontWeight: FontWeight.w700, color: onSurface, letterSpacing: 0, height: 1.27),
        titleMedium: TextStyle(fontFamily: 'Roboto', fontSize: 16, fontWeight: FontWeight.w700, color: onSurface, letterSpacing: 0.15, height: 1.50),
        titleSmall: TextStyle(fontFamily: 'Roboto', fontSize: 14, fontWeight: FontWeight.w700, color: onSurface, letterSpacing: 0.1, height: 1.43),
        bodyLarge: TextStyle(fontFamily: 'Roboto', fontSize: 16, fontWeight: FontWeight.w400, color: onSurface, letterSpacing: 0.5, height: 1.50),
        bodyMedium: TextStyle(fontFamily: 'Roboto', fontSize: 14, fontWeight: FontWeight.w400, color: onSurface, letterSpacing: 0.25, height: 1.43),
        bodySmall: TextStyle(fontFamily: 'Roboto', fontSize: 12, fontWeight: FontWeight.w400, color: onSurfaceVariant, letterSpacing: 0.4, height: 1.33),
        labelLarge: TextStyle(fontFamily: 'Roboto', fontSize: 14, fontWeight: FontWeight.w700, color: onSurface, letterSpacing: 0.1, height: 1.43),
        labelMedium: TextStyle(fontFamily: 'Roboto', fontSize: 12, fontWeight: FontWeight.w700, color: onSurface, letterSpacing: 0.5, height: 1.33),
        labelSmall: TextStyle(fontFamily: 'Roboto', fontSize: 11, fontWeight: FontWeight.w700, color: onSurfaceVariant, letterSpacing: 0.5, height: 1.45),
      ),

      // List Tile
      listTileTheme: ListTileThemeData(
        tileColor: Colors.transparent,
        selectedTileColor: primary.withValues(alpha: 0.08),
        iconColor: onSurfaceVariant,
        selectedColor: primary,
        textColor: onSurface,
        contentPadding: EdgeInsets.symmetric(
          horizontal: spacing.md, vertical: spacing.xs,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radii.sm),
        ),
        minTileHeight: DesignConstants.touchTargetMin,
      ),

      // Chip
      chipTheme: ChipThemeData(
        backgroundColor: colors.surfaceElevated,
        selectedColor: primary.withValues(alpha: 0.24),
        disabledColor: colors.surfaceBright,
        deleteIconColor: onSurfaceVariant,
        labelStyle: TextStyle(
          fontFamily: 'Roboto', fontSize: 13,
          fontWeight: FontWeight.w600, color: onSurface,
        ),
        padding: EdgeInsets.symmetric(
          horizontal: spacing.sm, vertical: spacing.xs,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(radii.sm),
          side: BorderSide(color: outline),
        ),
        side: BorderSide(color: outline),
        checkmarkColor: primary,
      ),

      // Switch
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return primary;
          return colors.textTertiary;
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return primary.withValues(alpha: 0.5);
          }
          return colors.surfaceBright;
        }),
        trackOutlineColor: WidgetStateProperty.all(Colors.transparent),
      ),

      // Checkbox
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return primary;
          return Colors.transparent;
        }),
        checkColor: WidgetStateProperty.all(onPrimary),
        side: BorderSide(color: onSurfaceVariant, width: 2),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(4),
        ),
      ),

      // Slider
      sliderTheme: SliderThemeData(
        activeTrackColor: primary,
        inactiveTrackColor: colors.surfaceBright,
        thumbColor: primary,
        overlayColor: primary.withValues(alpha: 0.12),
        valueIndicatorColor: primary,
        valueIndicatorTextStyle: TextStyle(
          fontFamily: 'Roboto', fontSize: 14,
          fontWeight: FontWeight.w700, color: onPrimary,
        ),
      ),
    );
  }

  // ==========================================================================
  // THEME GETTERS
  // ==========================================================================

  /// Dark theme — primary field-optimized theme.
  /// FROM SPEC: spacing parameter enables density switching at the app root.
  static ThemeData darkTheme({
    FieldGuideSpacing spacing = FieldGuideSpacing.standard,
  }) => build(
    colorScheme: _darkColorScheme,
    colors: FieldGuideColors.dark,
    spacing: spacing,
    radii: FieldGuideRadii.standard,
    motion: FieldGuideMotion.standard,
    shadows: FieldGuideShadows.standard,
    scaffoldBackgroundColor: AppColors.tVividBackground,
    systemOverlayStyle: const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: AppColors.backgroundDark,
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );

  /// Light theme — clean, high-readability theme.
  /// FROM SPEC: spacing parameter enables density switching at the app root.
  static ThemeData lightTheme({
    FieldGuideSpacing spacing = FieldGuideSpacing.standard,
  }) => build(
    colorScheme: _lightColorScheme,
    colors: FieldGuideColors.light,
    spacing: spacing,
    radii: FieldGuideRadii.standard,
    motion: FieldGuideMotion.standard,
    shadows: FieldGuideShadows.standard,
    scaffoldBackgroundColor: AppColors.lightBackground,
    systemOverlayStyle: const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
      systemNavigationBarColor: AppColors.lightBackground,
      systemNavigationBarIconBrightness: Brightness.dark,
    ),
  );
}
```

**IMPORTANT**: The implementing agent MUST:
1. Extract the full `_lightColorScheme` from the existing `lightTheme` getter before deleting it.
2. Preserve every component theme that exists in the current dark/light getters. The code above covers the major ones but the implementing agent should verify against the full existing source (1,264 lines after HC removal) that no component theme is dropped.
3. Ensure the `TabBarTheme`, `PopupMenuThemeData`, `TooltipTheme`, and any other component themes present in the existing code are included in `build()`. If they exist in the current source, they must be parameterized and included.
4. Keep all deprecated re-exports at the top of the class unchanged.

#### Step 1.8.2: Update all call sites from getter to method syntax

WHY: `darkTheme` and `lightTheme` changed from getters to methods with an optional `spacing` parameter. All call sites that use `AppTheme.darkTheme` or `AppTheme.lightTheme` must append `()`.

The implementing agent MUST:

1. Grep for `AppTheme.darkTheme` and `AppTheme.lightTheme` across all of `lib/` and `test/` (excluding `.claude/`).
2. For each reference NOT already followed by `(`, change `AppTheme.darkTheme` to `AppTheme.darkTheme()` and `AppTheme.lightTheme` to `AppTheme.lightTheme()`.
3. Key files expected to need updates (non-exhaustive):
   - `lib/features/settings/presentation/providers/theme_provider.dart` (already shown in step 1.5.2)
   - `test/golden/test_helpers.dart`
   - Any test file that references `AppTheme.darkTheme` or `AppTheme.lightTheme` directly
   - Any widget that calls these getters for theme-dependent logic

NOTE: The search pattern is `AppTheme.darkTheme` NOT followed by `(` and `AppTheme.lightTheme` NOT followed by `(`.

#### Step 1.8.3: Verify theme collapse compiles

```
pwsh -Command "flutter analyze"
```

**Expected**: Zero errors. The `darkTheme()` and `lightTheme()` methods produce the same `ThemeData` structure as before, just via a shared builder. Both accept an optional `spacing` parameter (defaults to `FieldGuideSpacing.standard`) to enable density switching.

#### Step 1.8.5: Verify app_theme.dart line count

FROM SPEC: `app_theme.dart` must be reduced to <400 lines.

```
pwsh -Command "(Get-Content lib/core/theme/app_theme.dart).Count"
```

**Expected**: Less than 400 lines. If over 400, extract component themes into a helper or reduce deprecated re-exports.

---

### Sub-phase 1.9: Density auto-selection via breakpoint

**Files:**
- Modify: `lib/core/bootstrap/app.dart` (or wherever `MaterialApp` is configured)

**Agent**: `code-fixer-agent`

#### Step 1.9.1: Wire density auto-selection at the app root

FROM SPEC: "Density is selected automatically in the live app from breakpoint/screen context; no user-facing density toggle in Settings."

Modify `lib/core/bootstrap/app.dart` (the file containing `MaterialApp.router`). Use a `Builder` widget above `MaterialApp.router` to access `MediaQueryData` for breakpoint detection:

```dart
// In lib/core/bootstrap/app.dart — wrap MaterialApp.router in a Builder
// that determines density from screen width.
//
// WHY: MediaQuery is not available above MaterialApp, so we use
// MediaQueryData.fromView(View.of(context)) in a Builder placed above it.

@override
Widget build(BuildContext context) {
  return Builder(
    builder: (context) {
      final view = View.of(context);
      final width = MediaQueryData.fromView(view).size.width;

      // FROM SPEC: Density variant mapping table
      final FieldGuideSpacing spacing;
      if (width >= 840) {
        spacing = FieldGuideSpacing.comfortable; // desktop / large tablet
      } else if (width >= 600) {
        spacing = FieldGuideSpacing.standard; // phone landscape / small tablet
      } else {
        spacing = FieldGuideSpacing.compact; // phone portrait
      }

      return Consumer<ThemeProvider>(
        builder: (context, themeProvider, _) {
          return MaterialApp.router(
            theme: themeProvider.currentTheme(spacing: spacing),
            // ... existing router config ...
          );
        },
      );
    },
  );
}
```

The implementing agent MUST also update `ThemeProvider.currentTheme` (or equivalent) to accept and forward the `spacing` parameter to `AppTheme.darkTheme(spacing: spacing)` / `AppTheme.lightTheme(spacing: spacing)`.

Additional context for breakpoint mapping:

1. Map the breakpoint width to a `FieldGuideSpacing` variant:
   - Width 0-599: `FieldGuideSpacing.compact` (phone portrait)
   - Width 600-839: `FieldGuideSpacing.standard` (phone landscape / small tablet)
   - Width 840+: `FieldGuideSpacing.comfortable` (desktop / large tablet)

   NOTE: These breakpoint thresholds align with the spec's density variant mapping table and will be formalized as `AppBreakpoint` in Phase 2. For now, use simple width checks. When Phase 2 introduces `AppBreakpoint`, this code should be updated to use `AppBreakpoint.of(context)`.

3. Pass the selected `FieldGuideSpacing` instance to `AppTheme.darkTheme(spacing: ...)` or `AppTheme.lightTheme(spacing: ...)`.

4. Ensure the `ThemeProvider` calls to `darkTheme`/`lightTheme` are updated from getter syntax (`AppTheme.darkTheme`) to method call syntax (`AppTheme.darkTheme()` or `AppTheme.darkTheme(spacing: selectedSpacing)`).

WHY: This ensures the live app automatically adapts spacing density based on screen size without requiring a user-facing settings toggle. Widgetbook will add explicit density knobs in Phase 2 for design review.

#### Step 1.9.2: Verify density wiring compiles

```
pwsh -Command "flutter analyze"
```

**Expected**: Zero errors. The app root reads screen width, selects a spacing variant, and passes it through the theme. Default behavior is unchanged (standard density) for existing screen sizes.

---

### Sub-phase 1.10: Update design system barrel

**Files:**
- Modify: `lib/core/design_system/design_system.dart`

**Agent**: `code-fixer-agent`

#### Step 1.10.1: Update `design_system.dart` to export tokens sub-barrel

```dart
// File: lib/core/design_system/design_system.dart
// Barrel export for the Field Guide design system.
//
// Usage (single import for all components):
// ```dart
// import 'package:construction_inspector/core/design_system/design_system.dart';
// ```

// FROM SPEC: Phase 1 — tokens sub-barrel (new)
export 'tokens/tokens.dart';

// Atomic layer
export 'app_text.dart';
export 'app_text_field.dart';
export 'app_chip.dart';
export 'app_progress_bar.dart';
export 'app_counter_field.dart';
export 'app_toggle.dart';
export 'app_icon.dart';

// Card layer
export 'app_glass_card.dart';
export 'app_section_header.dart';
export 'app_list_tile.dart';
export 'app_photo_grid.dart';
export 'app_section_card.dart';

// Surface layer
export 'app_scaffold.dart';
export 'app_bottom_bar.dart';
export 'app_bottom_sheet.dart';
export 'app_dialog.dart';
export 'app_sticky_header.dart';
export 'app_drag_handle.dart';

// Composite layer
export 'app_empty_state.dart';
export 'app_error_state.dart';
export 'app_loading_state.dart';
export 'app_budget_warning_chip.dart';
export 'app_info_banner.dart';
export 'app_mini_spinner.dart';

// NOTE: Sub-barrels for atoms/, molecules/, organisms/, surfaces/, feedback/,
// layout/, animation/ will be added as those directories are populated in
// later phases. Empty barrel files exist for directory structure.
```

#### Step 1.10.2: Verify barrel update compiles

```
pwsh -Command "flutter analyze"
```

**Expected**: Zero errors. The tokens barrel re-exports all token files, and the main barrel re-exports the tokens barrel. All 114 consumers of `design_system.dart` now have access to `AppColors`, `DesignConstants`, `FieldGuideColors`, `FieldGuideSpacing`, `FieldGuideRadii`, `FieldGuideMotion`, and `FieldGuideShadows` through the same import.

---

### Sub-phase 1.11: Tokenize existing design system components

**Files:**
- Modify: All 24 existing design system component files in `lib/core/design_system/`

**Agent**: `code-fixer-agent`

#### Step 1.11.1: Update component imports to use co-located tokens

For each of the 24 existing design system components, update their imports. Components that currently import from `lib/core/theme/design_constants.dart` or `lib/core/theme/field_guide_colors.dart` should import from the co-located tokens barrel instead.

The implementing agent should, for each component file in `lib/core/design_system/`:

1. Replace `import 'package:construction_inspector/core/theme/design_constants.dart';` with `import 'tokens/design_constants.dart';` (relative import within design system).
2. Replace `import 'package:construction_inspector/core/theme/field_guide_colors.dart';` with `import 'tokens/field_guide_colors.dart';`.
3. Replace `import 'package:construction_inspector/core/theme/colors.dart';` with `import 'tokens/app_colors.dart';`.

**IMPORTANT**: Do NOT change the actual usage of `DesignConstants.*` within these components yet. Token migration (replacing `DesignConstants.space4` with `FieldGuideSpacing.of(context).md`) will happen as part of screen decomposition in later phases to avoid double-touching files. The components themselves can access the static constants directly since they are inside the design system allowlist.

#### Step 1.11.2: Verify all components compile with updated imports

```
pwsh -Command "flutter analyze"
```

**Expected**: Zero errors. Import paths changed but all symbols resolve via the same classes.

---

### Sub-phase 1.12: Remove unused testing key for HC theme

**Files:**
- Modify: `lib/shared/testing_keys/settings_keys.dart` (line 90 — comment or keep `settingsThemeHighContrast` for now)
- Modify: `lib/shared/testing_keys/testing_keys.dart` (lines 434-435 — comment or keep for backward compat)

**Agent**: `code-fixer-agent`

#### Step 1.12.1: Mark HC testing key as unused

In `lib/shared/testing_keys/settings_keys.dart`, add a deprecation annotation:

```dart
// At line 90, change:
//   static const settingsThemeHighContrast = Key('settings_theme_high_contrast');
// To:
  @Deprecated('HC theme removed in Design System Overhaul Phase 1')
  static const settingsThemeHighContrast = Key('settings_theme_high_contrast');
```

Similarly in `lib/shared/testing_keys/testing_keys.dart`:

```dart
// At lines 434-435, change:
//   static const settingsThemeHighContrast =
//       SettingsTestingKeys.settingsThemeHighContrast;
// To:
  @Deprecated('HC theme removed in Design System Overhaul Phase 1')
  static const settingsThemeHighContrast =
      SettingsTestingKeys.settingsThemeHighContrast;
```

// WHY: Deprecate rather than delete to avoid breaking any driver tests that may reference these keys. The keys will be removed in a later cleanup sweep.

#### Step 1.12.2: Final Phase 1 verification

```
pwsh -Command "flutter analyze"
```

**Expected**: Zero errors. Deprecation warnings for the HC testing keys are acceptable. All Phase 0 lint rule warnings are expected and serve as the violation inventory baseline.


---

### Sub-phase 1.13: Phase 1 cleanup checklist (FROM SPEC)

Verify all 7 items: (1) Zero analyzer errors, (2) Zero new lint violations, (3) All moved files have updated imports, (4) Barrel files reflect current exports, (5) No orphaned files, (6) Documentation updated, (7) GitHub issues closed.

---

## Phase 2: Responsive Infrastructure + Animation + Navigation Adaptation + Widgetbook Skeleton

**Depends on**: Phase 1 (token ThemeExtensions must exist and be registered on `ThemeData.extensions` in `AppTheme.build()`)

**Phase 1 deliverables consumed here**:
- `lib/core/design_system/tokens/field_guide_spacing.dart` — `FieldGuideSpacing` with `of(context)`, variants: `standard`, `compact`, `comfortable`
- `lib/core/design_system/tokens/field_guide_radii.dart` — `FieldGuideRadii` with `of(context)`, single `standard` variant
- `lib/core/design_system/tokens/field_guide_motion.dart` — `FieldGuideMotion` with `of(context)`, variants: `standard`, `reduced`
- `lib/core/design_system/tokens/field_guide_shadows.dart` — `FieldGuideShadows` with `of(context)`, variants: `standard`, `flat`
- `lib/core/design_system/tokens/tokens.dart` — barrel exporting all token files
- `lib/core/design_system/design_system.dart` — updated barrel that re-exports `tokens/tokens.dart`

---

### Sub-phase 2.1: Responsive Breakpoints

**Agent**: `code-fixer-agent`

#### Step 2.1.1: Create `AppBreakpoint` enum and utility

**File**: `lib/core/design_system/layout/app_breakpoint.dart` (NEW)

```dart
import 'package:flutter/material.dart';

/// FROM SPEC: Material 3 canonical breakpoint names.
/// compact (0-599), medium (600-839), expanded (840-1199), large (1200+).
///
/// WHY: Single source of truth for responsive decisions. Every layout widget
/// and the navigation shell read from this instead of raw MediaQuery widths.
enum AppBreakpoint {
  /// Phone portrait (0-599dp)
  compact,

  /// Phone landscape, small tablet (600-839dp)
  medium,

  /// Tablet, small desktop window (840-1199dp)
  expanded,

  /// Desktop, large tablet landscape (1200+dp)
  large;

  /// Returns the current breakpoint based on screen width.
  ///
  /// NOTE: Uses `MediaQuery.sizeOf(context)` (not `.of(context)`) to avoid
  /// rebuilds from non-size MediaQuery changes (e.g., keyboard insets).
  static AppBreakpoint of(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    if (width >= 1200) return AppBreakpoint.large;
    if (width >= 840) return AppBreakpoint.expanded;
    if (width >= 600) return AppBreakpoint.medium;
    return AppBreakpoint.compact;
  }

  /// Whether this breakpoint represents a phone form factor.
  bool get isCompact => this == AppBreakpoint.compact;

  /// Whether this breakpoint is medium or larger (includes phone landscape 600dp+).
  /// WHY: Renamed from isTabletOrLarger -- medium includes phone landscape, not just tablets.
  bool get isMediumOrLarger =>
      this == AppBreakpoint.medium ||
      this == AppBreakpoint.expanded ||
      this == AppBreakpoint.large;

  /// Whether this breakpoint is truly tablet+ (expanded or larger, 840dp+).
  bool get isExpandedOrLarger =>
      this == AppBreakpoint.expanded ||
      this == AppBreakpoint.large;

  /// Whether this breakpoint should show expanded navigation labels.
  /// NOTE: medium shows collapsed rail (icons only), expanded/large show labels.
  bool get showNavigationLabels =>
      this == AppBreakpoint.expanded || this == AppBreakpoint.large;

  /// Recommended column count for grid layouts at this breakpoint.
  /// FROM SPEC: Phone=1-2, tablet=2-3, desktop=3-4.
  int get defaultGridColumns => switch (this) {
    AppBreakpoint.compact => 1,
    AppBreakpoint.medium => 2,
    AppBreakpoint.expanded => 3,
    AppBreakpoint.large => 4,
  };
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/layout/app_breakpoint.dart"`
Expected: No issues found.

---

### Sub-phase 2.2: AppResponsiveBuilder

**Agent**: `code-fixer-agent`

#### Step 2.2.1: Create `AppResponsiveBuilder` widget

**File**: `lib/core/design_system/layout/app_responsive_builder.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/layout/app_breakpoint.dart';

/// Builder widget that provides the current [AppBreakpoint] to its child.
///
/// WHY: Avoids repeating `AppBreakpoint.of(context)` + switch in every screen.
/// Screens provide per-breakpoint builders and this widget handles the plumbing.
///
/// Usage:
/// ```dart
/// AppResponsiveBuilder(
///   compact: (context) => _PhoneLayout(),
///   medium: (context) => _TabletLayout(),
///   expanded: (context) => _DesktopLayout(),
/// )
/// ```
class AppResponsiveBuilder extends StatelessWidget {
  const AppResponsiveBuilder({
    super.key,
    required this.compact,
    this.medium,
    this.expanded,
    this.large,
  });

  /// Builder for compact (phone portrait) breakpoint. Required — serves as fallback.
  final WidgetBuilder compact;

  /// Builder for medium (phone landscape, small tablet). Falls back to [compact].
  final WidgetBuilder? medium;

  /// Builder for expanded (tablet, small desktop). Falls back to [medium] then [compact].
  final WidgetBuilder? expanded;

  /// Builder for large (desktop, large tablet). Falls back to [expanded] then [medium] then [compact].
  final WidgetBuilder? large;

  @override
  Widget build(BuildContext context) {
    final breakpoint = AppBreakpoint.of(context);

    // NOTE: Cascading fallback — each breakpoint falls back to the next smaller
    // one if no explicit builder is provided. This means you only need to define
    // the breakpoints where layout actually changes.
    return switch (breakpoint) {
      AppBreakpoint.large => (large ?? expanded ?? medium ?? compact)(context),
      AppBreakpoint.expanded => (expanded ?? medium ?? compact)(context),
      AppBreakpoint.medium => (medium ?? compact)(context),
      AppBreakpoint.compact => compact(context),
    };
  }
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/layout/app_responsive_builder.dart"`
Expected: No issues found.

---

### Sub-phase 2.3: AppAdaptiveLayout

**Agent**: `code-fixer-agent`

#### Step 2.3.1: Create `AppAdaptiveLayout` container

**File**: `lib/core/design_system/layout/app_adaptive_layout.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/layout/app_breakpoint.dart';

/// Canonical adaptive layout container that auto-switches between single-column,
/// two-pane, and three-region layouts based on the current breakpoint.
///
/// FROM SPEC: Takes `body`, optional `detail` pane, optional `sidePanel`.
/// Auto-switches single-column / two-pane / three-region based on breakpoint.
///
/// Usage:
/// ```dart
/// AppAdaptiveLayout(
///   body: ProjectListView(),
///   detail: selectedProject != null ? ProjectDetail(id: selectedProject) : null,
///   sidePanel: ProjectStats(),
/// )
/// ```
class AppAdaptiveLayout extends StatelessWidget {
  const AppAdaptiveLayout({
    super.key,
    required this.body,
    this.detail,
    this.sidePanel,
    this.bodyFlex = 1,
    this.detailFlex = 1,
    this.sidePanelFlex = 1,
    this.dividerWidth = 1.0,
    this.showDividers = true,
  });

  /// Primary content — always shown.
  final Widget body;

  /// Optional detail pane — shown beside [body] at medium+ breakpoints.
  /// WHY: On compact, detail replaces body via navigation push. On medium+,
  /// detail appears as a side pane. The caller controls which mode via
  /// checking the breakpoint and conditionally providing this widget.
  final Widget? detail;

  /// Optional side panel — shown at large breakpoint only.
  /// WHY: Dashboard stats, navigation helpers, or contextual info that
  /// only makes sense when screen real estate is abundant.
  final Widget? sidePanel;

  /// Flex factor for the body column. Default: 1.
  final int bodyFlex;

  /// Flex factor for the detail column. Default: 1.
  final int detailFlex;

  /// Flex factor for the side panel column. Default: 1.
  final int sidePanelFlex;

  /// Width of dividers between panes. Default: 1.0.
  final double dividerWidth;

  /// Whether to show dividers between panes. Default: true.
  final bool showDividers;

  @override
  Widget build(BuildContext context) {
    final breakpoint = AppBreakpoint.of(context);
    final colorScheme = Theme.of(context).colorScheme;

    // NOTE: On compact, always single-column — detail/sidePanel are ignored.
    // The calling screen should handle compact differently (e.g., navigate to
    // a detail screen instead of showing a pane).
    if (breakpoint.isCompact || (detail == null && sidePanel == null)) {
      return body;
    }

    final divider = showDividers
        ? VerticalDivider(
            width: dividerWidth,
            thickness: dividerWidth,
            color: colorScheme.outlineVariant,
          )
        : const SizedBox.shrink();

    // WHY: medium and expanded show two-pane (body + detail) if detail exists.
    // large shows three-region (body + detail + sidePanel) if all exist.
    final showSidePanel =
        breakpoint == AppBreakpoint.large && sidePanel != null;
    final showDetail = detail != null;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(flex: bodyFlex, child: body),
        if (showDetail) ...[
          divider,
          Expanded(flex: detailFlex, child: detail!),
        ],
        if (showSidePanel) ...[
          divider,
          Expanded(flex: sidePanelFlex, child: sidePanel!),
        ],
      ],
    );
  }
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/layout/app_adaptive_layout.dart"`
Expected: No issues found.

---

### Sub-phase 2.4: AppResponsivePadding

**Agent**: `code-fixer-agent`

#### Step 2.4.1: Create `AppResponsivePadding` widget

**File**: `lib/core/design_system/layout/app_responsive_padding.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/layout/app_breakpoint.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_spacing.dart';

/// Screen-appropriate horizontal padding that adapts per breakpoint.
///
/// FROM SPEC: Phone=16px, tablet=24px, desktop=32px+.
/// Reads from `FieldGuideSpacing.of(context)` tokens so padding respects
/// the current density variant (compact/standard/comfortable).
///
/// WHY: Replaces scattered `EdgeInsets.symmetric(horizontal: DesignConstants.space4)`
/// patterns with a single widget that adapts to screen size and density.
///
/// Usage:
/// ```dart
/// AppResponsivePadding(
///   child: Column(children: [...]),
/// )
/// ```
class AppResponsivePadding extends StatelessWidget {
  const AppResponsivePadding({
    super.key,
    required this.child,
    this.includeVertical = false,
    this.sliver = false,
  });

  /// The widget to wrap with responsive horizontal padding.
  final Widget child;

  /// Whether to also apply vertical padding (top/bottom = spacing.sm).
  /// Default: false — most screens only need horizontal margins.
  final bool includeVertical;

  /// Whether to wrap as a SliverPadding instead of Padding.
  /// WHY: Many screens use CustomScrollView with slivers. This flag
  /// lets them use responsive padding without breaking the sliver protocol.
  final bool sliver;

  /// Returns the horizontal padding value for the given context.
  /// Exposed as static for cases where the padding value is needed
  /// programmatically (e.g., calculating available width).
  static double horizontalOf(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    final breakpoint = AppBreakpoint.of(context);
    // FROM SPEC: Phone=16px (md), tablet=24px (lg), desktop=32px+ (xl)
    return switch (breakpoint) {
      AppBreakpoint.compact => spacing.md,   // 16.0
      AppBreakpoint.medium => spacing.lg,    // 24.0
      AppBreakpoint.expanded => spacing.xl,  // 32.0
      AppBreakpoint.large => spacing.xl,     // 32.0
    };
  }

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    final horizontal = horizontalOf(context);
    final vertical = includeVertical ? spacing.sm : 0.0;

    final padding = EdgeInsets.symmetric(
      horizontal: horizontal,
      vertical: vertical,
    );

    if (sliver) {
      return SliverPadding(padding: padding, sliver: child);
    }

    return Padding(padding: padding, child: child);
  }
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/layout/app_responsive_padding.dart"`
Expected: No issues found.

---

### Sub-phase 2.5: AppResponsiveGrid

**Agent**: `code-fixer-agent`

#### Step 2.5.1: Create `AppResponsiveGrid` widget

**File**: `lib/core/design_system/layout/app_responsive_grid.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/layout/app_breakpoint.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_spacing.dart';

/// Responsive column grid that adapts column count per breakpoint.
///
/// FROM SPEC: Phone=1-2 cols, tablet=2-3, desktop=3-4.
///
/// WHY: Replaces ad-hoc `GridView.count(crossAxisCount: 2)` patterns with
/// a grid that automatically adapts to screen size. Column count can be
/// overridden per breakpoint for screens with specific layout needs.
///
/// Usage:
/// ```dart
/// AppResponsiveGrid(
///   children: items.map((item) => ItemCard(item: item)).toList(),
/// )
/// ```
class AppResponsiveGrid extends StatelessWidget {
  const AppResponsiveGrid({
    super.key,
    required this.children,
    this.compactColumns,
    this.mediumColumns,
    this.expandedColumns,
    this.largeColumns,
    this.childAspectRatio = 1.0,
    this.mainAxisSpacing,
    this.crossAxisSpacing,
    this.shrinkWrap = false,
    this.physics,
    this.padding,
  });

  /// The grid items.
  final List<Widget> children;

  /// Override column count for compact breakpoint. Default: `AppBreakpoint.compact.defaultGridColumns` (1).
  final int? compactColumns;

  /// Override column count for medium breakpoint. Default: `AppBreakpoint.medium.defaultGridColumns` (2).
  final int? mediumColumns;

  /// Override column count for expanded breakpoint. Default: `AppBreakpoint.expanded.defaultGridColumns` (3).
  final int? expandedColumns;

  /// Override column count for large breakpoint. Default: `AppBreakpoint.large.defaultGridColumns` (4).
  final int? largeColumns;

  /// Aspect ratio of each grid cell. Default: 1.0 (square).
  final double childAspectRatio;

  /// Spacing between rows. Default: reads from `FieldGuideSpacing.of(context).sm`.
  final double? mainAxisSpacing;

  /// Spacing between columns. Default: reads from `FieldGuideSpacing.of(context).sm`.
  final double? crossAxisSpacing;

  /// Whether the grid should shrink-wrap its content. Default: false.
  final bool shrinkWrap;

  /// Scroll physics. Default: null (inherits from parent).
  final ScrollPhysics? physics;

  /// Optional external padding around the grid.
  final EdgeInsets? padding;

  @override
  Widget build(BuildContext context) {
    final breakpoint = AppBreakpoint.of(context);
    final spacing = FieldGuideSpacing.of(context);

    final columns = switch (breakpoint) {
      AppBreakpoint.compact => compactColumns ?? breakpoint.defaultGridColumns,
      AppBreakpoint.medium => mediumColumns ?? breakpoint.defaultGridColumns,
      AppBreakpoint.expanded =>
        expandedColumns ?? breakpoint.defaultGridColumns,
      AppBreakpoint.large => largeColumns ?? breakpoint.defaultGridColumns,
    };

    // NOTE: Default spacing uses FieldGuideSpacing.sm (8.0) for grid gaps.
    // This keeps cards visually tight while readable.
    final gapMain = mainAxisSpacing ?? spacing.sm;
    final gapCross = crossAxisSpacing ?? spacing.sm;

    return GridView.count(
      crossAxisCount: columns,
      childAspectRatio: childAspectRatio,
      mainAxisSpacing: gapMain,
      crossAxisSpacing: gapCross,
      shrinkWrap: shrinkWrap,
      physics: physics,
      padding: padding,
      children: children,
    );
  }
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/layout/app_responsive_grid.dart"`
Expected: No issues found.

---

### Sub-phase 2.6: Navigation Adaptation (ScaffoldWithNavBar)

**Agent**: `code-fixer-agent`

#### Step 2.6.1: Refactor `ScaffoldWithNavBar` for responsive navigation

**File**: `lib/core/router/scaffold_with_nav_bar.dart` (MODIFY — full rewrite of 188 lines)

IMPORTANT: This is the highest-risk change in Phase 2. The navigation shell is used on every screen. The rewrite must:
1. Preserve ALL existing banner management (version, stale config, stale sync, offline)
2. Preserve ALL existing testing keys
3. Preserve the `Consumer2<SyncProvider, AppConfigProvider>` pattern for banners
4. Preserve `ExtractionBanner` placement
5. Switch from `NavigationBar` (bottom) to `NavigationRail` (side) at medium+ breakpoints
6. Fix #201 (Android keyboard blocks buttons) by using `resizeToAvoidBottomInset: true` on the inner Scaffold and ensuring the bottom nav respects keyboard insets

```dart
// lib/core/router/scaffold_with_nav_bar.dart
import 'dart:async' show unawaited;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/design_system/layout/app_breakpoint.dart';
import 'package:construction_inspector/core/theme/field_guide_colors.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/projects/presentation/widgets/project_switcher.dart';
import 'package:construction_inspector/features/sync/application/sync_coordinator.dart';
import 'package:construction_inspector/features/sync/presentation/providers/sync_provider.dart';
import 'package:construction_inspector/features/sync/presentation/widgets/sync_status_icon.dart';
import 'package:construction_inspector/features/pdf/presentation/widgets/extraction_banner.dart';
import 'package:construction_inspector/shared/shared.dart';

/// Shell widget providing responsive navigation and status banners.
///
/// FROM SPEC: compact = bottom NavigationBar, medium = collapsed NavigationRail,
/// expanded/large = expanded NavigationRail with labels.
///
/// NOTE: Receives providers via context.watch/context.read from the widget tree
/// (correct for presentation-layer reads).
class ScaffoldWithNavBar extends StatelessWidget {
  final Widget child;

  const ScaffoldWithNavBar({super.key, required this.child});

  /// Routes where the project switcher should appear in the app bar.
  static const _projectContextRoutes = {'/', '/calendar'};

  // WHY: Extracted as a constant list so both NavigationBar destinations and
  // NavigationRail destinations share the same data. Prevents drift.
  static const _destinations = [
    _NavDestination(
      key: TestingKeys.dashboardNavButton,
      icon: Icons.dashboard_outlined,
      selectedIcon: Icons.dashboard,
      label: 'Dashboard',
    ),
    _NavDestination(
      key: TestingKeys.calendarNavButton,
      icon: Icons.calendar_today_outlined,
      selectedIcon: Icons.calendar_today,
      label: 'Calendar',
    ),
    _NavDestination(
      key: TestingKeys.projectsNavButton,
      icon: Icons.folder_outlined,
      selectedIcon: Icons.folder,
      label: 'Projects',
    ),
    _NavDestination(
      key: TestingKeys.settingsNavButton,
      icon: Icons.settings_outlined,
      selectedIcon: Icons.settings,
      label: 'Settings',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final fg = FieldGuideColors.of(context);
    final location = GoRouterState.of(context).uri.path;
    final showProjectSwitcher = _projectContextRoutes.contains(location);
    final breakpoint = AppBreakpoint.of(context);
    final selectedIndex = _calculateSelectedIndex(context);

    final appBar = showProjectSwitcher
        ? AppBar(
            title: const ProjectSwitcher(),
            centerTitle: false,
            automaticallyImplyLeading: false,
            actions: const [SyncStatusIcon()],
          )
        : null;

    // WHY: Banner management is extracted to a method to keep build() readable.
    // The Consumer2 stays in the body to scope rebuilds to banner state changes.
    final bodyWithBanners = Consumer2<SyncProvider, AppConfigProvider>(
      builder: (context, syncProvider, appConfigProvider, innerChild) {
        final syncCoordinator = context.read<SyncCoordinator>();

        // [Phase 6, 3.2] Wire sync error toast callback to ScaffoldMessenger
        syncProvider.onSyncErrorToast ??= (message) {
          unawaited(SnackBarHelper.showErrorWithAction(
            context,
            'Sync error: $message',
            actionLabel: 'Details',
            onAction: () => context.push('/sync/dashboard'),
          ).closed.then((_) {
            syncProvider.clearSyncErrorSnackbarFlag();
          }));
        };

        final banners = <Widget>[];

        // Version update banner (soft nudge)
        if (appConfigProvider.hasUpdateAvailable) {
          banners.add(
            VersionBanner(message: appConfigProvider.updateMessage),
          );
        }

        // Stale config warning (>24h since server check)
        if (appConfigProvider.isConfigStale) {
          banners.add(
            StaleConfigWarning(
              onRetry: () => appConfigProvider.checkConfig(),
            ),
          );
        }

        // Stale sync data warning
        if (syncProvider.isStaleDataWarning) {
          banners.add(
            MaterialBanner(
              content: Text(
                'Data may be out of date — last synced ${syncProvider.lastSyncText}',
              ),
              leading: Icon(Icons.warning_amber, color: fg.accentOrange),
              actions: [
                TextButton(
                  onPressed: () => syncProvider.sync(),
                  child: const Text('Sync Now'),
                ),
              ],
            ),
          );
        }

        // Offline indicator
        if (!syncProvider.isOnline) {
          banners.add(
            MaterialBanner(
              content: const Text(
                'You are offline. Changes will sync when connection is restored.',
              ),
              leading: Icon(Icons.cloud_off, color: fg.accentOrange),
              backgroundColor: fg.accentOrange.withValues(alpha: 0.08),
              actions: [
                TextButton(
                  onPressed: () async {
                    await syncCoordinator.checkDnsReachability();
                  },
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        if (banners.isEmpty) return innerChild!;

        return Column(
          children: [
            ...banners,
            Expanded(child: innerChild!),
          ],
        );
      },
      child: child,
    );

    // FROM SPEC: compact = bottom NavigationBar
    if (breakpoint.isCompact) {
      return Scaffold(
        appBar: appBar,
        // IMPORTANT: resizeToAvoidBottomInset ensures the bottom nav moves up
        // when the keyboard appears, fixing #201 (Android keyboard blocks buttons).
        resizeToAvoidBottomInset: true,
        body: bodyWithBanners,
        bottomNavigationBar: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const ExtractionBanner(),
            NavigationBar(
              key: TestingKeys.bottomNavigationBar,
              selectedIndex: selectedIndex,
              onDestinationSelected: (index) => _onItemTapped(index, context),
              destinations: _destinations
                  .map((d) => NavigationDestination(
                        key: d.key,
                        icon: Icon(d.icon),
                        selectedIcon: Icon(d.selectedIcon),
                        label: d.label,
                      ))
                  .toList(),
            ),
          ],
        ),
      );
    }

    // FROM SPEC: medium = collapsed NavigationRail (icons only)
    // expanded/large = expanded NavigationRail (icons + labels)
    final extended = breakpoint.showNavigationLabels;

    return Scaffold(
      appBar: appBar,
      body: Row(
        children: [
          NavigationRail(
            key: TestingKeys.bottomNavigationBar,
            // NOTE: Reusing bottomNavigationBar key for test compatibility.
            // Driver tests locate nav by this key — changing it would break tests.
            selectedIndex: selectedIndex,
            onDestinationSelected: (index) => _onItemTapped(index, context),
            extended: extended,
            // WHY: labelType is none when extended is true (labels are inline).
            // When collapsed (medium), show labels on selection only.
            labelType: extended
                ? NavigationRailLabelType.none
                : NavigationRailLabelType.selected,
            destinations: _destinations
                .map((d) => NavigationRailDestination(
                      icon: Icon(d.icon, key: d.key),
                      selectedIcon: Icon(d.selectedIcon),
                      label: Text(d.label),
                    ))
                .toList(),
          ),
          const VerticalDivider(thickness: 1, width: 1),
          Expanded(
            child: Column(
              children: [
                const ExtractionBanner(),
                Expanded(child: bodyWithBanners),
              ],
            ),
          ),
        ],
      ),
    );
  }

  int _calculateSelectedIndex(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    if (location.startsWith('/calendar')) return 1;
    if (location.startsWith('/projects')) return 2;
    if (location.startsWith('/settings')) return 3;
    return 0;
  }

  void _onItemTapped(int index, BuildContext context) {
    switch (index) {
      case 0:
        context.goNamed('dashboard');
      case 1:
        context.goNamed('home');
      case 2:
        context.goNamed('projects');
      case 3:
        context.goNamed('settings');
    }
  }
}

/// Internal data class for navigation destination configuration.
/// WHY: Shared between NavigationBar and NavigationRail to prevent drift.
class _NavDestination {
  const _NavDestination({
    required this.key,
    required this.icon,
    required this.selectedIcon,
    required this.label,
  });

  final Key key;
  final IconData icon;
  final IconData selectedIcon;
  final String label;
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/router/scaffold_with_nav_bar.dart"`
Expected: No issues found.

---

### Sub-phase 2.7: Animation Components

**Agent**: `code-fixer-agent`

#### Step 2.7.1: Create `AppAnimatedEntrance`

**File**: `lib/core/design_system/animation/app_animated_entrance.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_motion.dart';

/// Fade + slide-up entrance animation that reads motion tokens.
///
/// FROM SPEC: Widget mount triggers fade + slide-up. Reads duration/curve
/// from `FieldGuideMotion.of(context)`.
///
/// WHY: Replaces ad-hoc `AnimatedOpacity` + `SlideTransition` combos scattered
/// across screens. Centralizes entrance animation with automatic accessibility
/// support (reduced motion = instant appear).
///
/// Usage:
/// ```dart
/// AppAnimatedEntrance(
///   child: MyCard(),
/// )
/// ```
class AppAnimatedEntrance extends StatefulWidget {
  const AppAnimatedEntrance({
    super.key,
    required this.child,
    this.delay = Duration.zero,
    this.slideOffset = 0.1,
  });

  /// The widget to animate in.
  final Widget child;

  /// Optional delay before the animation starts.
  /// WHY: Used by AppStaggeredList to stagger child entrances.
  final Duration delay;

  /// Vertical slide offset as a fraction of the child's height. Default: 0.1 (10%).
  /// NOTE: Positive = slides up from below. Negative = slides down from above.
  final double slideOffset;

  @override
  State<AppAnimatedEntrance> createState() => _AppAnimatedEntranceState();
}

class _AppAnimatedEntranceState extends State<AppAnimatedEntrance>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  // WHY: Not `late final` — didChangeDependencies fires multiple times (e.g.,
  // theme change, MediaQuery change). Using `late final` would throw
  // LateInitializationError on the second call.
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;
  bool _hasAnimated = false;

  @override
  void initState() {
    super.initState();
    // NOTE: Duration is set in didChangeDependencies where we have context.
    // Controller starts at 0ms here and gets updated.
    _controller = AnimationController(vsync: this);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final motion = FieldGuideMotion.of(context);

    // WHY: Check disableAnimations via the motion token's reduced variant.
    // When reduced, duration is Duration.zero so animation completes instantly.
    _controller.duration = motion.normal;

    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: motion.curveDecelerate,
    );

    _slideAnimation = Tween<Offset>(
      begin: Offset(0, widget.slideOffset),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: motion.curveStandard,
    ));

    // WHY: Guard ensures animation only plays once. Without this,
    // didChangeDependencies re-triggering would restart the entrance animation.
    if (!_hasAnimated) {
      _hasAnimated = true;
      // Start animation after optional delay
      if (widget.delay == Duration.zero) {
        _controller.forward();
      } else {
        Future.delayed(widget.delay, () {
          if (mounted) _controller.forward();
        });
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fadeAnimation,
      child: SlideTransition(
        position: _slideAnimation,
        child: widget.child,
      ),
    );
  }
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/animation/app_animated_entrance.dart"`
Expected: No issues found.

#### Step 2.7.2: Create `AppStaggeredList`

**File**: `lib/core/design_system/animation/app_staggered_list.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/animation/app_animated_entrance.dart';

/// Staggers child entrance animations with configurable delay per item.
///
/// FROM SPEC: 50ms delay per item, max 8 staggered then batch remaining.
///
/// WHY: List screens currently have no entrance animation. This provides
/// a polished feel without custom AnimationController per screen.
///
/// Usage:
/// ```dart
/// AppStaggeredList(
///   children: items.map((item) => ItemCard(item: item)).toList(),
/// )
/// ```
class AppStaggeredList extends StatelessWidget {
  const AppStaggeredList({
    super.key,
    required this.children,
    this.staggerDelay = const Duration(milliseconds: 50),
    this.maxStaggered = 8,
  });

  /// The list of widgets to stagger.
  final List<Widget> children;

  /// Delay between each child's entrance animation. Default: 50ms.
  /// FROM SPEC: 50ms delay per item.
  final Duration staggerDelay;

  /// Maximum number of items that get individual stagger delays.
  /// Items beyond this threshold all animate at the max delay (batch entrance).
  /// FROM SPEC: max 8 then batch.
  /// WHY: Prevents absurdly long stagger chains on long lists (e.g., 50 items
  /// would take 2.5 seconds to finish staggering without this cap).
  final int maxStaggered;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int i = 0; i < children.length; i++)
          AppAnimatedEntrance(
            // NOTE: Items 0-7 get increasing delays (0ms, 50ms, 100ms, ..., 350ms).
            // Items 8+ all get the same 400ms delay (batch entrance).
            delay: Duration(
              milliseconds: staggerDelay.inMilliseconds *
                  (i < maxStaggered ? i : maxStaggered),
            ),
            child: children[i],
          ),
      ],
    );
  }
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/animation/app_staggered_list.dart"`
Expected: No issues found.

#### Step 2.7.3: Create `AppTapFeedback`

**File**: `lib/core/design_system/animation/app_tap_feedback.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_motion.dart';

/// Scale-to-0.95 tap feedback animation that reads motion tokens.
///
/// FROM SPEC: Scale-to-0.95 on press, 1.0 on release. 100ms via motion tokens.
///
/// WHY: Provides consistent tactile feedback across all tappable surfaces
/// (cards, tiles, buttons). Replaces InkWell/GestureDetector ripple with
/// a subtle scale that feels more premium on mobile.
///
/// Usage:
/// ```dart
/// AppTapFeedback(
///   onTap: () => navigateToDetail(),
///   child: MyCard(),
/// )
/// ```
class AppTapFeedback extends StatefulWidget {
  const AppTapFeedback({
    super.key,
    required this.child,
    this.onTap,
    this.onLongPress,
    this.pressedScale = 0.95,
    this.enabled = true,
  });

  /// The widget to wrap with tap feedback.
  final Widget child;

  /// Callback when the widget is tapped.
  final VoidCallback? onTap;

  /// Callback when the widget is long-pressed.
  final VoidCallback? onLongPress;

  /// Scale factor when pressed. Default: 0.95.
  /// FROM SPEC: Scale-to-0.95 on press.
  final double pressedScale;

  /// Whether the feedback effect is enabled. Default: true.
  /// WHY: Disabled items should not animate on tap.
  final bool enabled;

  @override
  State<AppTapFeedback> createState() => _AppTapFeedbackState();
}

class _AppTapFeedbackState extends State<AppTapFeedback>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    // NOTE: 100ms is below the smallest token (fast=150ms). Spec says "100ms
    // via motion tokens" but no token that small exists. Using 100ms directly
    // for the snappy tap feel; implementing agent should consider FieldGuideMotion.fast
    // if exact token alignment is preferred over the 100ms spec value.
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 100),
    );
    _scaleAnimation = Tween<double>(
      begin: 1.0,
      end: widget.pressedScale,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOut,
    ));
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final motion = FieldGuideMotion.of(context);
    // WHY: When reduced motion is active, the controller duration becomes zero,
    // making the scale change instant (no animation perceived).
    // We use a fraction of fast for the tap feedback since it should be quicker
    // than standard transitions.
    final baseDuration = motion.fast;
    _controller.duration = Duration(
      milliseconds: (baseDuration.inMilliseconds * 0.67).round(),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onTapDown(TapDownDetails _) {
    if (widget.enabled) _controller.forward();
  }

  void _onTapUp(TapUpDetails _) {
    _controller.reverse();
  }

  void _onTapCancel() {
    _controller.reverse();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.enabled) {
      return widget.child;
    }

    return GestureDetector(
      onTapDown: _onTapDown,
      onTapUp: _onTapUp,
      onTapCancel: _onTapCancel,
      onTap: widget.onTap,
      onLongPress: widget.onLongPress,
      child: ScaleTransition(
        scale: _scaleAnimation,
        child: widget.child,
      ),
    );
  }
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/animation/app_tap_feedback.dart"`
Expected: No issues found.

#### Step 2.7.4: Create `AppValueTransition`

**File**: `lib/core/design_system/animation/app_value_transition.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_motion.dart';

/// Animated counter that slides out old value and slides in new value.
///
/// FROM SPEC: Animated counter — slide-up old, slide-in new.
///
/// WHY: Budget totals, item counts, and amount fields currently jump between
/// values. This provides a polished transition that communicates change.
///
/// Usage:
/// ```dart
/// AppValueTransition(
///   value: totalAmount,
///   builder: (context, value) => AppText.headlineMedium('\$${value.toStringAsFixed(2)}'),
/// )
/// ```
class AppValueTransition extends StatelessWidget {
  const AppValueTransition({
    super.key,
    required this.value,
    required this.builder,
  });

  /// The current value. When this changes, the transition animates.
  /// NOTE: Uses Object so it works with int, double, String, etc.
  final Object value;

  /// Builder that creates the display widget for the current value.
  final Widget Function(BuildContext context, Object value) builder;

  @override
  Widget build(BuildContext context) {
    final motion = FieldGuideMotion.of(context);

    return AnimatedSwitcher(
      duration: motion.fast,
      switchInCurve: motion.curveDecelerate,
      switchOutCurve: motion.curveDecelerate,
      // WHY: SlideTransition (up for new, down for old) gives a "counter tick"
      // feel that's more engaging than a simple crossfade.
      transitionBuilder: (child, animation) {
        // NOTE: Key comparison determines which child is "entering" vs "exiting".
        // The entering child slides up from below, the exiting slides up and out.
        final slideIn = Tween<Offset>(
          begin: const Offset(0, 0.5),
          end: Offset.zero,
        ).animate(animation);

        return FadeTransition(
          opacity: animation,
          child: SlideTransition(
            position: slideIn,
            child: child,
          ),
        );
      },
      child: KeyedSubtree(
        key: ValueKey<Object>(value),
        child: builder(context, value),
      ),
    );
  }
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/animation/app_value_transition.dart"`
Expected: No issues found.

---

### Sub-phase 2.8: Screen Transitions

**Agent**: `code-fixer-agent`

#### Step 2.8.1: Add `animations` package dependency

**File**: `pubspec.yaml` (MODIFY)

Add the following under `dependencies:` (after `go_router:`):

```yaml
  # Material motion transitions (SharedAxis, FadeThrough, ContainerTransform)
  animations: ^2.0.11
```

**Verification**: `pwsh -Command "flutter pub get"`
Expected: Resolves successfully, no version conflicts.

#### Step 2.8.2: Update `app_router.dart` shell page transitions

**File**: `lib/core/router/app_router.dart` (MODIFY lines 1-98)

Replace the import of `design_constants.dart` and the `_shellPage` / `_fadeTransition` methods. The rest of the file is unchanged.

At line 23, change:
```dart
import 'package:construction_inspector/core/theme/design_constants.dart';
```
to:
```dart
import 'package:construction_inspector/core/design_system/tokens/field_guide_motion.dart';
import 'package:animations/animations.dart';
```

Replace lines 82-98 (`_shellPage` and `_fadeTransition` methods) with:

```dart
  /// Builds a consistent fade-through transition page for shell (bottom-nav) routes.
  ///
  /// FROM SPEC: FadeThroughTransition for tab switches, 200ms.
  /// WHY: Material motion FadeThrough is the canonical pattern for tab/peer
  /// screen transitions. Reads duration from FieldGuideMotion tokens.
  static Page<void> _shellPage(LocalKey key, Widget child) =>
      CustomTransitionPage(
        key: key,
        child: child,
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          // NOTE: FadeThroughTransition from the animations package provides
          // the Material 3 canonical tab-switch transition.
          return FadeThroughTransition(
            animation: animation,
            secondaryAnimation: secondaryAnimation,
            child: child,
          );
        },
        // NOTE: CustomTransitionPage needs duration at construction (no context).
        // Cannot use FieldGuideMotion.of(context). Const matches standard token.
        // Reduced motion works via platform AccessibilityFeatures.
        transitionDuration: const Duration(milliseconds: 200),
        reverseTransitionDuration: const Duration(milliseconds: 200),
      );
```

NOTE: The `_fadeTransition` static method at lines 92-98 is no longer needed after this change. Delete it. If any other code in the file references `_fadeTransition`, search for it first.

Before deleting `_fadeTransition`, verify no other references exist in the file:
- Search for `_fadeTransition` in `app_router.dart` — it should only appear in the old `_shellPage` definition.

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/router/app_router.dart"`
Expected: No issues found.

#### Step 2.8.3: Create `SharedAxisTransitionPage` helper

**File**: `lib/core/design_system/animation/shared_axis_transition_page.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:animations/animations.dart';

/// FROM SPEC: SharedAxisTransition (horizontal) for peer screens.
class SharedAxisTransitionPage extends CustomTransitionPage<void> {
  SharedAxisTransitionPage({
    required super.key,
    required super.child,
    SharedAxisTransitionType type = SharedAxisTransitionType.horizontal,
  }) : super(
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            return SharedAxisTransition(
              animation: animation,
              secondaryAnimation: secondaryAnimation,
              transitionType: type,
              child: child,
            );
          },
          // NOTE: Const duration = FieldGuideMotion.pageTransition default. No context at construction.
          transitionDuration: const Duration(milliseconds: 350),
          reverseTransitionDuration: const Duration(milliseconds: 350),
        );
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/animation/shared_axis_transition_page.dart"`
Expected: No issues found.

#### Step 2.8.4: Create `AppContainerTransform` wrapper

**File**: `lib/core/design_system/animation/app_container_transform.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:animations/animations.dart';

/// FROM SPEC: ContainerTransform for card -> detail screen.
class AppContainerTransform extends StatelessWidget {
  const AppContainerTransform({
    super.key,
    required this.closedBuilder,
    required this.openBuilder,
    this.closedElevation = 0,
    // WHY: Use DesignConstants.radiusMedium instead of magic number 12.
    this.closedShape = const RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(DesignConstants.radiusMedium)),
    ),
    this.closedColor,
    // NOTE: Const default matches FieldGuideMotion.pageTransition token value.
    // Cannot read tokens at construction time (no context). Callers can override.
    this.transitionDuration = const Duration(milliseconds: 350),
  });

  final CloseContainerBuilder closedBuilder;
  final OpenContainerBuilder<void> openBuilder;
  final double closedElevation;
  final ShapeBorder closedShape;
  final Color? closedColor;
  final Duration transitionDuration;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return OpenContainer<void>(
      closedBuilder: closedBuilder,
      openBuilder: openBuilder,
      closedElevation: closedElevation,
      closedShape: closedShape,
      closedColor: closedColor ?? cs.surface,
      openColor: cs.surface,
      transitionDuration: transitionDuration,
      transitionType: ContainerTransitionType.fadeThrough,
    );
  }
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/animation/app_container_transform.dart"`
Expected: No issues found.

---

### Sub-phase 2.9: Layout + Animation Barrel Files

**Agent**: `code-fixer-agent`

#### Step 2.9.1: Create layout barrel file

**File**: `lib/core/design_system/layout/layout.dart` (NEW)

```dart
/// Barrel export for the Field Guide responsive layout system.
///
/// WHY: Single import for all layout widgets. Consumed by the main
/// design_system.dart barrel and directly by screens needing layout primitives.
export 'app_breakpoint.dart';
export 'app_responsive_builder.dart';
export 'app_adaptive_layout.dart';
export 'app_responsive_padding.dart';
export 'app_responsive_grid.dart';
```

#### Step 2.9.2: Create animation barrel file

**File**: `lib/core/design_system/animation/animation.dart` (NEW)

```dart
/// Barrel export for the Field Guide animation system.
///
/// WHY: Single import for all animation widgets. Consumed by the main
/// design_system.dart barrel and directly by screens needing animation primitives.
export 'app_animated_entrance.dart';
export 'app_staggered_list.dart';
export 'app_tap_feedback.dart';
export 'app_value_transition.dart';
export 'shared_axis_transition_page.dart';
export 'app_container_transform.dart';
```

#### Step 2.9.3: Update main design system barrel

**File**: `lib/core/design_system/design_system.dart` (MODIFY)

Add the following two export lines. The exact placement depends on what Phase 1 has already added. Add after the existing exports (or after the `tokens/tokens.dart` export if Phase 1 added it):

```dart
export 'layout/layout.dart';
export 'animation/animation.dart';
```

The final barrel file should look like (preserving all existing exports plus Phase 1 additions):

```dart
// Barrel export for the Field Guide design system.
//
// Usage (single import for all components):
// ```dart
// import 'package:construction_inspector/core/design_system/design_system.dart';
// ```

// Token layer (added in Phase 1)
export 'tokens/tokens.dart';

// Layout layer (added in Phase 2)
export 'layout/layout.dart';

// Animation layer (added in Phase 2)
export 'animation/animation.dart';

// Atomic layer
export 'app_text.dart';
export 'app_text_field.dart';
export 'app_chip.dart';
export 'app_progress_bar.dart';
export 'app_counter_field.dart';
export 'app_toggle.dart';
export 'app_icon.dart';

// Card layer
export 'app_glass_card.dart';
export 'app_section_header.dart';
export 'app_list_tile.dart';
export 'app_photo_grid.dart';
export 'app_section_card.dart';

// Surface layer
export 'app_scaffold.dart';
export 'app_bottom_bar.dart';
export 'app_bottom_sheet.dart';
export 'app_dialog.dart';
export 'app_sticky_header.dart';
export 'app_drag_handle.dart';

// Composite layer
export 'app_empty_state.dart';
export 'app_error_state.dart';
export 'app_loading_state.dart';
export 'app_budget_warning_chip.dart';
export 'app_info_banner.dart';
export 'app_mini_spinner.dart';
```

IMPORTANT: The implementing agent MUST read the current state of `design_system.dart` before editing, because Phase 1 may have already modified it. Add the two new exports without removing anything Phase 1 added.

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/"`
Expected: No issues found.

---

### Sub-phase 2.10: Widgetbook Skeleton

**Agent**: `code-fixer-agent`

#### Step 2.10.1: Create Widgetbook `pubspec.yaml`

**File**: `widgetbook/pubspec.yaml` (NEW)

```yaml
name: field_guide_widgetbook
description: Widgetbook for Field Guide design system
publish_to: 'none'

environment:
  sdk: ^3.10.7

dependencies:
  flutter:
    sdk: flutter
  widgetbook: ^3.10.0
  widgetbook_annotation: ^3.2.0

  # WHY: Import the main app's design system to render actual components.
  # Path dependency lets Widgetbook see all design_system exports.
  construction_inspector:
    path: ..

dev_dependencies:
  flutter_test:
    sdk: flutter
  widgetbook_generator: ^3.10.0
  build_runner: ^2.4.0
```

**Verification**: `pwsh -Command "cd C:/Users/rseba/Projects/Field_Guide_App/widgetbook && flutter pub get"`
Expected: Resolves successfully.

#### Step 2.10.2: Create Widgetbook main entry point

**File**: `widgetbook/lib/main.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:widgetbook/widgetbook.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';

/// Widgetbook entry point for the Field Guide design system.
///
/// FROM SPEC: Knobs for theme (dark/light), breakpoint (compact/medium/expanded/large),
/// density (compact/standard/comfortable). Device frames: Phone, Tablet, Desktop.
///
/// WHY: Provides an interactive component catalog for design review, QA, and
/// regression testing without running the full app.
void main() {
  runApp(const FieldGuideWidgetbook());
}

class FieldGuideWidgetbook extends StatelessWidget {
  const FieldGuideWidgetbook({super.key});

  @override
  Widget build(BuildContext context) {
    return Widgetbook.material(
      // NOTE: addons provide global knobs that affect all use cases.
      addons: [
        // Theme addon: switch between dark and light themes.
        MaterialThemeAddon(
          themes: [
            WidgetbookTheme(name: 'Dark', data: AppTheme.darkTheme),
            WidgetbookTheme(name: 'Light', data: AppTheme.lightTheme),
          ],
        ),
        // Device frame addon: test across form factors.
        // FROM SPEC: Phone (Samsung S21), Tablet (iPad 10.9"), Desktop (1440x900).
        DeviceFrameAddon(
          devices: [
            Devices.android.samsungGalaxyS21,
            Devices.ios.iPadAir4,
            Devices.desktop.desktop1440x900,
          ],
        ),
        // Text scale addon: test accessibility text sizes.
        TextScaleAddon(
          scales: [1.0, 1.25, 1.5, 2.0],
        ),
        // FROM SPEC: Density knob (compact/standard/comfortable) for design review.
        // WHY: Custom addon that overrides FieldGuideSpacing ThemeExtension to test
        // how components adapt across density variants without running the full app.
        _DensityAddon(),
      ],
      directories: [
        // WHY: Organized by design system layer (tokens, layout, animation, atoms, etc.)
        // to mirror the code structure.
        WidgetbookFolder(
          name: 'Layout',
          children: [
            WidgetbookComponent(
              name: 'AppResponsiveBuilder',
              useCases: [
                WidgetbookUseCase(
                  name: 'Breakpoint demo',
                  builder: (context) {
                    return AppResponsiveBuilder(
                      compact: (_) => _BreakpointLabel('compact'),
                      medium: (_) => _BreakpointLabel('medium'),
                      expanded: (_) => _BreakpointLabel('expanded'),
                      large: (_) => _BreakpointLabel('large'),
                    );
                  },
                ),
              ],
            ),
            WidgetbookComponent(
              name: 'AppAdaptiveLayout',
              useCases: [
                WidgetbookUseCase(
                  name: 'Two-pane layout',
                  builder: (context) {
                    return AppAdaptiveLayout(
                      body: Container(
                        color: Colors.blue.withValues(alpha: 0.1),
                        child: const Center(child: Text('Body')),
                      ),
                      detail: Container(
                        color: Colors.green.withValues(alpha: 0.1),
                        child: const Center(child: Text('Detail')),
                      ),
                    );
                  },
                ),
                WidgetbookUseCase(
                  name: 'Three-region layout',
                  builder: (context) {
                    return AppAdaptiveLayout(
                      body: Container(
                        color: Colors.blue.withValues(alpha: 0.1),
                        child: const Center(child: Text('Body')),
                      ),
                      detail: Container(
                        color: Colors.green.withValues(alpha: 0.1),
                        child: const Center(child: Text('Detail')),
                      ),
                      sidePanel: Container(
                        color: Colors.orange.withValues(alpha: 0.1),
                        child: const Center(child: Text('Side Panel')),
                      ),
                    );
                  },
                ),
              ],
            ),
            WidgetbookComponent(
              name: 'AppResponsivePadding',
              useCases: [
                WidgetbookUseCase(
                  name: 'Default horizontal padding',
                  builder: (context) {
                    return AppResponsivePadding(
                      child: Container(
                        color: Colors.purple.withValues(alpha: 0.1),
                        height: 200,
                        child: const Center(
                          child: Text('Content with responsive padding'),
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
            WidgetbookComponent(
              name: 'AppResponsiveGrid',
              useCases: [
                WidgetbookUseCase(
                  name: 'Adaptive grid',
                  builder: (context) {
                    return AppResponsiveGrid(
                      shrinkWrap: true,
                      children: List.generate(
                        8,
                        (i) => Card(
                          child: Center(child: Text('Item $i')),
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
          ],
        ),
        WidgetbookFolder(
          name: 'Animation',
          children: [
            WidgetbookComponent(
              name: 'AppAnimatedEntrance',
              useCases: [
                WidgetbookUseCase(
                  name: 'Fade + slide up',
                  builder: (context) {
                    // NOTE: Wrap in a StatefulBuilder to provide a reset button.
                    return StatefulBuilder(
                      builder: (context, setState) {
                        return Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            AppAnimatedEntrance(
                              key: UniqueKey(),
                              child: const Card(
                                child: Padding(
                                  padding: EdgeInsets.all(24),
                                  child: Text('Animated entrance'),
                                ),
                              ),
                            ),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: () => setState(() {}),
                              child: const Text('Replay'),
                            ),
                          ],
                        );
                      },
                    );
                  },
                ),
              ],
            ),
            WidgetbookComponent(
              name: 'AppStaggeredList',
              useCases: [
                WidgetbookUseCase(
                  name: 'Staggered entrance',
                  builder: (context) {
                    return AppStaggeredList(
                      children: List.generate(5, (i) => Card(
                        child: ListTile(title: Text('Item $i')),
                      )),
                    );
                  },
                ),
              ],
            ),
            WidgetbookComponent(
              name: 'AppTapFeedback',
              useCases: [
                WidgetbookUseCase(
                  name: 'Scale on press',
                  builder: (context) {
                    return Center(
                      child: AppTapFeedback(
                        onTap: () {},
                        child: const Card(
                          child: Padding(
                            padding: EdgeInsets.all(24),
                            child: Text('Tap me'),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
            WidgetbookComponent(
              name: 'AppValueTransition',
              useCases: [
                WidgetbookUseCase(
                  name: 'Counter animation',
                  // NOTE: No StatefulBuilder needed -- _ValueTransitionDemo is already StatefulWidget.
                  builder: (context) => _ValueTransitionDemo(),
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }
}

/// Simple label widget for breakpoint demo.
class _BreakpointLabel extends StatelessWidget {
  const _BreakpointLabel(this.label);
  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            label.toUpperCase(),
            style: Theme.of(context).textTheme.headlineLarge,
          ),
          const SizedBox(height: 8),
          Text(
            'Resize window to change breakpoint',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}

/// Stateful demo for AppValueTransition.
class _ValueTransitionDemo extends StatefulWidget {
  @override
  State<_ValueTransitionDemo> createState() => _ValueTransitionDemoState();
}

class _ValueTransitionDemoState extends State<_ValueTransitionDemo> {
  int _counter = 0;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          AppValueTransition(
            value: _counter,
            builder: (context, value) => Text(
              '$value',
              style: Theme.of(context).textTheme.displayLarge,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              IconButton(
                onPressed: () => setState(() => _counter--),
                icon: const Icon(Icons.remove),
              ),
              const SizedBox(width: 16),
              IconButton(
                onPressed: () => setState(() => _counter++),
                icon: const Icon(Icons.add),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
```

Add `_DensityAddon` class after the `_ValueTransitionDemoState` class (before the closing triple-backtick):

```dart
/// FROM SPEC: Custom Widgetbook addon for density switching (compact/standard/comfortable).
class _DensityAddon extends WidgetbookAddon<String> {
  _DensityAddon() : super(name: 'Density');
  @override
  List<Field> get fields => [
    ListField<String>(name: 'density', values: ['compact', 'standard', 'comfortable'],
      initialValue: 'standard', labelBuilder: (v) => v),
  ];
  @override
  String valueFromQueryGroup(Map<String, String> group) => group['density'] ?? 'standard';
  @override
  Widget buildUseCase(BuildContext context, Widget child, String setting) {
    final spacing = switch (setting) {
      'compact' => FieldGuideSpacing.compact,
      'comfortable' => FieldGuideSpacing.comfortable,
      _ => FieldGuideSpacing.standard,
    };
    return Theme(data: Theme.of(context).copyWith(extensions: <ThemeExtension>[spacing]), child: child);
  }
}
```

**Verification**: `pwsh -Command "cd C:/Users/rseba/Projects/Field_Guide_App/widgetbook && flutter analyze --no-pub"`
Expected: No issues found.

---

### Sub-phase 2.11: Accessibility — Reduced Motion Integration

**Agent**: `code-fixer-agent`

#### Step 2.11.1: Create `MotionAwareBuilder` utility

This step ensures all animation components automatically respect the system "reduce motion" accessibility setting. The approach is to provide a utility that animation components can use internally, and to document the pattern for future animation code.

**File**: `lib/core/design_system/animation/motion_aware.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/tokens/field_guide_motion.dart';

/// Resolves the effective [FieldGuideMotion] for the current context,
/// automatically swapping to `FieldGuideMotion.reduced` when the platform
/// requests reduced motion.
///
/// FROM SPEC: When `MediaQuery.of(context).disableAnimations` is true,
/// swap to `FieldGuideMotion.reduced`. Every animation component checks
/// automatically via token.
///
/// WHY: Instead of every animation widget checking `disableAnimations`
/// independently, this central utility provides the correct motion token.
/// Phase 1's `FieldGuideMotion.of(context)` reads from ThemeData.extensions,
/// which returns the app's configured variant (standard). This helper
/// overrides that when the OS accessibility setting demands it.
///
/// IMPORTANT: Animation components created in Phase 2 (AppAnimatedEntrance,
/// AppStaggeredList, AppTapFeedback, AppValueTransition) should use
/// `MotionAware.of(context)` instead of `FieldGuideMotion.of(context)` to
/// get automatic reduced-motion support.
class MotionAware {
  MotionAware._();

  /// Returns [FieldGuideMotion.reduced] when the platform requests reduced
  /// motion, otherwise returns the theme-configured [FieldGuideMotion].
  ///
  /// NOTE: Uses `MediaQuery.disableAnimationsOf(context)` (the specific
  /// InheritedModel selector) to avoid rebuilds from unrelated MediaQuery
  /// changes like keyboard insets or orientation.
  static FieldGuideMotion of(BuildContext context) {
    final disableAnimations = MediaQuery.disableAnimationsOf(context);
    if (disableAnimations) {
      return FieldGuideMotion.reduced;
    }
    return FieldGuideMotion.of(context);
  }
}
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/animation/motion_aware.dart"`
Expected: No issues found.

#### Step 2.11.2: Update animation components to use `MotionAware.of(context)`

**File**: `lib/core/design_system/animation/app_animated_entrance.dart` (MODIFY)

In `_AppAnimatedEntranceState.didChangeDependencies()`, change:
```dart
    final motion = FieldGuideMotion.of(context);
```
to:
```dart
    final motion = MotionAware.of(context);
```

Add import at the top of the file:
```dart
import 'package:construction_inspector/core/design_system/animation/motion_aware.dart';
```

The existing `FieldGuideMotion` import can be removed since `MotionAware` handles it.

**File**: `lib/core/design_system/animation/app_tap_feedback.dart` (MODIFY)

In `_AppTapFeedbackState.didChangeDependencies()`, change:
```dart
    final motion = FieldGuideMotion.of(context);
```
to:
```dart
    final motion = MotionAware.of(context);
```

Replace the import:
```dart
import 'package:construction_inspector/core/design_system/tokens/field_guide_motion.dart';
```
with:
```dart
import 'package:construction_inspector/core/design_system/animation/motion_aware.dart';
```

**File**: `lib/core/design_system/animation/app_value_transition.dart` (MODIFY)

In the `build()` method, change:
```dart
    final motion = FieldGuideMotion.of(context);
```
to:
```dart
    final motion = MotionAware.of(context);
```

Replace the import:
```dart
import 'package:construction_inspector/core/design_system/tokens/field_guide_motion.dart';
```
with:
```dart
import 'package:construction_inspector/core/design_system/animation/motion_aware.dart';
```

#### Step 2.11.3: Update animation barrel to include `motion_aware.dart`

**File**: `lib/core/design_system/animation/animation.dart` (MODIFY)

Add:
```dart
export 'motion_aware.dart';
```

Final barrel contents (all 7 animation exports):
```dart
/// Barrel export for the Field Guide animation system.
export 'app_animated_entrance.dart';
export 'app_container_transform.dart';
export 'app_staggered_list.dart';
export 'app_tap_feedback.dart';
export 'app_value_transition.dart';
export 'motion_aware.dart';
export 'shared_axis_transition_page.dart';
```

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/animation/"`
Expected: No issues found.

---

### Sub-phase 2.12: Full Phase 2 Verification

**Agent**: `general-purpose`

#### Step 2.12.1: Run full analyzer on design system and router

**Verification**: `pwsh -Command "flutter analyze --no-pub lib/core/design_system/ lib/core/router/"`
Expected: No issues found.

#### Step 2.12.2: Run full analyzer on widgetbook

**Verification**: `pwsh -Command "cd C:/Users/rseba/Projects/Field_Guide_App/widgetbook && flutter analyze --no-pub"`
Expected: No issues found.

#### Step 2.12.3: Minimal Widgetbook CI validation

**WHY**: FROM SPEC -- "CI: Build Widgetbook on every PR". Full CI integration deferred to P6, but minimal validation ensures the Widgetbook compiles.

**Verification**: `pwsh -Command "cd C:/Users/rseba/Projects/Field_Guide_App/widgetbook && flutter pub get && flutter analyze"`
Expected: No issues found. This step confirms the Widgetbook can be built in CI.

---

**NOTE -- WIDGET TESTS DEFERRED**: Spec requires tests for every new component. Widget tests for all P2 and P3 components are deferred to Phase 6. Implementing agent should add basic smoke tests (renders without error, responds to key props) for at minimum AppButton, AppBreakpoint, and AppResponsiveBuilder.

### Phase 2 File Summary

**New files created (16)**:
1. `lib/core/design_system/layout/app_breakpoint.dart`
2. `lib/core/design_system/layout/app_responsive_builder.dart`
3. `lib/core/design_system/layout/app_adaptive_layout.dart`
4. `lib/core/design_system/layout/app_responsive_padding.dart`
5. `lib/core/design_system/layout/app_responsive_grid.dart`
6. `lib/core/design_system/layout/layout.dart`
7. `lib/core/design_system/animation/app_animated_entrance.dart`
8. `lib/core/design_system/animation/app_staggered_list.dart`
9. `lib/core/design_system/animation/app_tap_feedback.dart`
10. `lib/core/design_system/animation/app_value_transition.dart`
11. `lib/core/design_system/animation/motion_aware.dart`
12. `lib/core/design_system/animation/animation.dart`
13. `lib/core/design_system/animation/shared_axis_transition_page.dart`
14. `lib/core/design_system/animation/app_container_transform.dart`
15. `widgetbook/pubspec.yaml`
16. `widgetbook/lib/main.dart`

**Files modified (3)**:
1. `lib/core/router/scaffold_with_nav_bar.dart` — responsive navigation (NavigationBar -> NavigationRail at medium+), #201 fix
2. `lib/core/router/app_router.dart` — FadeThroughTransition for shell pages, remove DesignConstants import
3. `lib/core/design_system/design_system.dart` — add layout/layout.dart and animation/animation.dart exports

**Dependency added (1)**:
1. `pubspec.yaml` — `animations: ^2.0.11`


---


## Phase 3: Design System Expansion — New Components + Shared Widget Migrations

**EXECUTION ORDER**: Sub-phases do NOT execute in document order. Move sub-phases precede new-component sub-phases. Order: **3.2, 3.1, 3.4, 3.3, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11**.

**CRITICAL -- IMPORT FIXUP AFTER EVERY MOVE BATCH**: Sub-phases 3.2, 3.4, 3.5, 3.8, and 3.9 relocate files into atomic subdirectories, which breaks ~24 direct consumer imports (14 in `lib/`, 10 in `test/`). After EACH move sub-phase, the implementing agent MUST grep `lib/` and `test/` for direct imports at old paths, replace them with the barrel `import 'package:construction_inspector/core/design_system/design_system.dart';`, deduplicate, and verify with `flutter analyze`.

**Prerequisites**: Phase 2 (token system + sub-directory scaffolding with barrel files) must be complete. The following sub-directory barrel files and token ThemeExtensions must already exist:
- `lib/core/design_system/atoms/atoms.dart`
- `lib/core/design_system/molecules/molecules.dart`
- `lib/core/design_system/organisms/organisms.dart`
- `lib/core/design_system/surfaces/surfaces.dart`
- `lib/core/design_system/feedback/feedback.dart`
- `lib/core/design_system/tokens/tokens.dart` (exporting `FieldGuideSpacing`, `FieldGuideRadii`, `FieldGuideMotion`, `FieldGuideShadows`, `FieldGuideColors`, `DesignConstants`, `AppColors`)
- `lib/core/design_system/design_system.dart` (main barrel re-exporting all sub-barrels)

**Phase 2 token accessors assumed available**:
- `FieldGuideSpacing.of(context)` with fields: `xs` (4), `sm` (8), `md` (16), `lg` (24), `xl` (32), `xxl` (48)
- `FieldGuideRadii.of(context)` with fields: `xs` (4), `sm` (8), `compact` (10), `md` (12), `lg` (16), `xl` (24), `full` (999)
- `FieldGuideMotion.of(context)` with fields: `fast` (150ms), `normal` (300ms), `slow` (500ms), `pageTransition` (350ms), `curveStandard`, `curveDecelerate`
- `FieldGuideShadows.of(context)` with fields: `low`, `medium`, `high`, `modal`

**IMPORTANT**: All new components in this phase continue using `DesignConstants` for spacing/radii (the mass migration to token accessors happens in Phase 4+ decomposition). New components use `DesignConstants` consistently to match existing component style and avoid premature refactoring.

**IMPORT PATH NOTE**: New P3 components must import DesignConstants from the canonical token path `../tokens/design_constants.dart` (NOT `../../theme/design_constants.dart`). The code blocks below may show the old `../../theme/` path -- the implementing agent MUST use `../tokens/` instead. The `theme/` shim exists for backward compatibility but new code should not depend on it.

---

### Sub-phase 3.1: New Atoms

**EXECUTION ORDER**: Sub-phase 3.2 (Move Existing Atoms) MUST execute BEFORE this sub-phase. New atoms like `AppButton` import co-located atoms (`app_icon.dart`, `app_mini_spinner.dart`) via relative imports that only resolve after the existing atoms are moved into the `atoms/` directory.

**Agent**: `code-fixer-agent`

#### Step 3.1.1: Create `AppButton`

Create `lib/core/design_system/atoms/app_button.dart`:

```dart
import 'package:flutter/material.dart';
import '../tokens/design_constants.dart';
import 'app_icon.dart';
import 'app_mini_spinner.dart';

/// Semantic button with variant-based styling that wraps Material buttons.
///
/// Usage:
/// ```dart
/// AppButton.primary(label: 'Save Entry', onPressed: _save)
/// AppButton.secondary(label: 'Cancel', onPressed: _cancel)
/// AppButton.ghost(label: 'Skip', onPressed: _skip)
/// AppButton.danger(label: 'Delete', onPressed: _delete)
/// AppButton.primary(label: 'Syncing...', onPressed: null, isLoading: true)
/// ```
///
/// FROM SPEC: Replaces raw ElevatedButton/TextButton/OutlinedButton usage with
/// consistent spacing, radii, and loading state. New lint rule `no_raw_button`
/// will enforce this wrapper in presentation layer.
enum AppButtonVariant { primary, secondary, ghost, danger }

class AppButton extends StatelessWidget {
  const AppButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.variant = AppButtonVariant.primary,
    this.icon,
    this.isLoading = false,
    this.isExpanded = false,
  });

  /// Primary — filled elevated button (main CTA)
  const factory AppButton.primary({
    Key? key,
    required String label,
    required VoidCallback? onPressed,
    IconData? icon,
    bool isLoading,
    bool isExpanded,
  }) = _PrimaryAppButton;

  /// Secondary — outlined button (secondary action)
  const factory AppButton.secondary({
    Key? key,
    required String label,
    required VoidCallback? onPressed,
    IconData? icon,
    bool isLoading,
    bool isExpanded,
  }) = _SecondaryAppButton;

  /// Ghost — text-only button (tertiary action)
  const factory AppButton.ghost({
    Key? key,
    required String label,
    required VoidCallback? onPressed,
    IconData? icon,
    bool isLoading,
    bool isExpanded,
  }) = _GhostAppButton;

  /// Danger — error-colored filled button (destructive action)
  const factory AppButton.danger({
    Key? key,
    required String label,
    required VoidCallback? onPressed,
    IconData? icon,
    bool isLoading,
    bool isExpanded,
  }) = _DangerAppButton;

  /// Icon-only button — wraps IconButton with consistent sizing.
  ///
  /// WHY: Phase 4 migrations replace raw `IconButton(` with `AppButton.icon()`
  /// to satisfy the `no_raw_button` lint rule while preserving icon-only semantics.
  factory AppButton.icon({
    Key? key,
    required IconData icon,
    required VoidCallback? onPressed,
    String? tooltip,
    double? size,
    Color? color,
  }) {
    return _IconAppButton(
      key: key,
      icon: icon,
      onPressed: onPressed,
      tooltip: tooltip,
      size: size,
      color: color,
    );
  }

  /// Text-only button — ghost variant with text-only styling (no icon).
  ///
  /// WHY: Phase 4 migrations replace raw `TextButton(` with `AppButton.text()`
  /// to satisfy the `no_raw_button` lint rule while preserving text-only semantics.
  const factory AppButton.text({
    Key? key,
    required String label,
    required VoidCallback? onPressed,
    bool isLoading,
    bool isExpanded,
  }) = _GhostAppButton;

  final String label;
  final VoidCallback? onPressed;
  final AppButtonVariant variant;
  final IconData? icon;
  final bool isLoading;

  /// Whether the button expands to fill available width.
  final bool isExpanded;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    // WHY: Disable press while loading to prevent double-submit.
    final effectiveOnPressed = isLoading ? null : onPressed;

    // NOTE: Build the child row with optional icon/spinner + label.
    final child = Row(
      mainAxisSize: isExpanded ? MainAxisSize.max : MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (isLoading) ...[
          AppMiniSpinner(
            color: _spinnerColor(cs),
            size: DesignConstants.iconSizeSmall,
          ),
          const SizedBox(width: DesignConstants.space2),
        ] else if (icon != null) ...[
          AppIcon(icon!, size: AppIconSize.small),
          const SizedBox(width: DesignConstants.space2),
        ],
        Text(label),
      ],
    );

    // WHY: Each variant maps to its Material button wrapper so themes
    // from AppTheme (elevatedButtonTheme, outlinedButtonTheme, etc.)
    // automatically apply without manual color overrides.
    final Widget button;
    switch (variant) {
      case AppButtonVariant.primary:
        button = ElevatedButton(
          onPressed: effectiveOnPressed,
          child: child,
        );
      case AppButtonVariant.secondary:
        button = OutlinedButton(
          onPressed: effectiveOnPressed,
          child: child,
        );
      case AppButtonVariant.ghost:
        button = TextButton(
          onPressed: effectiveOnPressed,
          child: child,
        );
      case AppButtonVariant.danger:
        button = ElevatedButton(
          onPressed: effectiveOnPressed,
          style: ElevatedButton.styleFrom(
            backgroundColor: cs.error,
            foregroundColor: cs.onError,
          ),
          child: child,
        );
    }

    if (isExpanded) {
      return SizedBox(width: double.infinity, child: button);
    }
    return button;
  }

  Color _spinnerColor(ColorScheme cs) {
    return switch (variant) {
      AppButtonVariant.primary => cs.onPrimary,
      AppButtonVariant.secondary => cs.primary,
      AppButtonVariant.ghost => cs.primary,
      AppButtonVariant.danger => cs.onError,
    };
  }
}

// NOTE: Private subclasses for const factory constructors. Each simply
// forwards parameters to the base class with the correct variant value.

class _PrimaryAppButton extends AppButton {
  const _PrimaryAppButton({
    super.key,
    required super.label,
    required super.onPressed,
    super.icon,
    super.isLoading,
    super.isExpanded,
  }) : super(variant: AppButtonVariant.primary);
}

class _SecondaryAppButton extends AppButton {
  const _SecondaryAppButton({
    super.key,
    required super.label,
    required super.onPressed,
    super.icon,
    super.isLoading,
    super.isExpanded,
  }) : super(variant: AppButtonVariant.secondary);
}

class _GhostAppButton extends AppButton {
  const _GhostAppButton({
    super.key,
    required super.label,
    required super.onPressed,
    super.icon,
    super.isLoading,
    super.isExpanded,
  }) : super(variant: AppButtonVariant.ghost);
}

class _DangerAppButton extends AppButton {
  const _DangerAppButton({
    super.key,
    required super.label,
    required super.onPressed,
    super.icon,
    super.isLoading,
    super.isExpanded,
  }) : super(variant: AppButtonVariant.danger);
}

/// Icon-only button subclass. Overrides build() to render IconButton directly.
/// NOTE: isLoading/isExpanded inherited from AppButton are no-ops for icon variant.
class _IconAppButton extends AppButton {
  _IconAppButton({
    super.key,
    required IconData icon,
    required super.onPressed,
    this.tooltip,
    this.size,
    this.color,
  }) : super(label: '', icon: icon);

  final String? tooltip;
  final double? size;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: AppIcon(icon!, size: size != null ? AppIconSize.small : AppIconSize.medium),
      onPressed: onPressed,
      tooltip: tooltip,
      color: color,
      iconSize: size,
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/app_button.dart"
```
Expected: No issues found.

---

#### Step 3.1.2: Create `AppBadge`

Create `lib/core/design_system/atoms/app_badge.dart`:

```dart
import 'package:flutter/material.dart';
import '../tokens/design_constants.dart';

/// Status/count/category badge with color, icon, or letter variants.
///
/// Usage:
/// ```dart
/// AppBadge.count(7, color: cs.primary)
/// AppBadge.icon(Icons.check, color: fg.statusSuccess)
/// AppBadge.letter('A', color: accentColor)
/// AppBadge.dot(color: cs.error)
/// ```
///
/// FROM SPEC: Unified badge component for status indicators, notification counts,
/// category markers. Replaces 15+ inline Container badge patterns.
class AppBadge extends StatelessWidget {
  const AppBadge({
    super.key,
    required this.child,
    required this.backgroundColor,
    required this.foregroundColor,
    this.size = 24.0,
    this.borderRadius,
  });

  /// Count badge — shows a number inside a colored circle.
  factory AppBadge.count(
    int count, {
    Key? key,
    required Color color,
    double size = 24.0,
  }) {
    return AppBadge(
      key: key,
      backgroundColor: color.withValues(alpha: 0.2),
      foregroundColor: color,
      size: size,
      child: Text(
        count > 99 ? '99+' : '$count',
        style: TextStyle(
          fontSize: size * 0.5,
          fontWeight: FontWeight.w700,
          color: color,
        ),
      ),
    );
  }

  /// Icon badge — shows an icon inside a colored container.
  factory AppBadge.icon(
    IconData icon, {
    Key? key,
    required Color color,
    double size = 24.0,
  }) {
    return AppBadge(
      key: key,
      backgroundColor: color.withValues(alpha: 0.2),
      foregroundColor: color,
      size: size,
      child: Icon(icon, size: size * 0.6, color: color),
    );
  }

  /// Letter badge — shows a single letter in a rounded square.
  /// WHY: Extracted from FormAccordion._LetterBadge pattern (form_accordion.dart:117).
  factory AppBadge.letter(
    String letter, {
    Key? key,
    required Color color,
    double size = 36.0,
  }) {
    return AppBadge(
      key: key,
      backgroundColor: color.withValues(alpha: 0.18),
      foregroundColor: color,
      size: size,
      // NOTE: radiusCompact (10) matches the FormAccordion letter badge pattern.
      borderRadius: DesignConstants.radiusCompact,
      child: Text(
        letter,
        style: TextStyle(
          fontSize: size * 0.42,
          fontWeight: FontWeight.w800,
          color: color,
        ),
      ),
    );
  }

  /// Dot badge — small colored dot for status indicators.
  factory AppBadge.dot({
    Key? key,
    required Color color,
    double size = 8.0,
  }) {
    return AppBadge(
      key: key,
      backgroundColor: color,
      foregroundColor: color,
      size: size,
      child: const SizedBox.shrink(),
    );
  }

  final Widget child;
  final Color backgroundColor;
  final Color foregroundColor;
  final double size;
  final double? borderRadius;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: borderRadius != null
            ? BorderRadius.circular(borderRadius!)
            : null,
        // WHY: When no explicit borderRadius, use circle shape for count/icon/dot.
        shape: borderRadius == null ? BoxShape.circle : BoxShape.rectangle,
      ),
      child: child,
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/app_badge.dart"
```
Expected: No issues found.

---

#### Step 3.1.3: Create `AppDivider`

Create `lib/core/design_system/atoms/app_divider.dart`:

```dart
import 'package:flutter/material.dart';
import '../tokens/design_constants.dart';

/// Themed divider using design tokens for consistent spacing and color.
///
/// Usage:
/// ```dart
/// AppDivider()
/// AppDivider(indent: DesignConstants.space4)
/// AppDivider.vertical(height: 24)
/// ```
///
/// FROM SPEC: Wraps raw Divider with consistent color/spacing. New lint rule
/// `no_raw_divider` will enforce this wrapper in presentation layer.
class AppDivider extends StatelessWidget {
  const AppDivider({
    super.key,
    this.indent = 0.0,
    this.endIndent = 0.0,
    this.height,
    this.thickness,
    this.color,
  }) : _isVertical = false;

  /// Vertical divider variant.
  const AppDivider.vertical({
    super.key,
    this.height = 24.0,
    this.thickness,
    this.color,
  })  : indent = 0.0,
        endIndent = 0.0,
        _isVertical = true;

  final double indent;
  final double endIndent;
  final double? height;
  final double? thickness;
  final Color? color;
  final bool _isVertical;

  @override
  Widget build(BuildContext context) {
    // NOTE: DividerThemeData from AppTheme controls default color and thickness.
    // We only override when explicitly provided. This ensures theme consistency.
    if (_isVertical) {
      return SizedBox(
        height: height,
        child: VerticalDivider(
          thickness: thickness,
          color: color,
        ),
      );
    }

    return Divider(
      indent: indent,
      endIndent: endIndent,
      height: height ?? DesignConstants.space4,
      thickness: thickness,
      color: color,
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/app_divider.dart"
```
Expected: No issues found.

---

#### Step 3.1.4: Create `AppAvatar`

Create `lib/core/design_system/atoms/app_avatar.dart`:

```dart
import 'package:flutter/material.dart';
import '../tokens/design_constants.dart';
import '../tokens/field_guide_colors.dart';

/// Circular user avatar with initials fallback.
///
/// Usage:
/// ```dart
/// AppAvatar(initials: 'JS', color: cs.primary)
/// AppAvatar(initials: 'RS', size: AppAvatarSize.large)
/// ```
///
/// FROM SPEC: Token-based sizing with initials fallback for user/inspector
/// identification in personnel lists and entry attribution.
enum AppAvatarSize {
  /// 32px — compact list items
  small(32.0),

  /// 40px — standard list items
  medium(40.0),

  /// 56px — profile headers
  large(56.0);

  const AppAvatarSize(this.value);
  final double value;
}

class AppAvatar extends StatelessWidget {
  const AppAvatar({
    super.key,
    required this.initials,
    this.size = AppAvatarSize.medium,
    this.color,
    this.backgroundColor,
  });

  /// 1-2 character initials to display (e.g., "JS" for John Smith).
  final String initials;

  /// Avatar size tier.
  final AppAvatarSize size;

  /// Foreground text color. Default: colorScheme.onPrimary.
  final Color? color;

  /// Background circle color. Default: colorScheme.primary at 20% alpha.
  final Color? backgroundColor;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    final bgColor = backgroundColor ?? cs.primary.withValues(alpha: 0.2);
    final fgColor = color ?? cs.primary;

    // WHY: Font size scales with avatar size for consistent visual weight.
    final fontSize = size.value * 0.4;

    return Container(
      width: size.value,
      height: size.value,
      decoration: BoxDecoration(
        color: bgColor,
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: Text(
        initials.toUpperCase(),
        style: tt.labelMedium?.copyWith(
          color: fgColor,
          fontSize: fontSize,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/app_avatar.dart"
```
Expected: No issues found.

---

#### Step 3.1.5: Create `AppTooltip`

Create `lib/core/design_system/atoms/app_tooltip.dart`:

```dart
import 'package:flutter/material.dart';

/// Themed tooltip wrapper using design tokens for consistent styling.
///
/// Usage:
/// ```dart
/// AppTooltip(
///   message: 'Sync status: Up to date',
///   child: Icon(Icons.sync),
/// )
/// ```
///
/// FROM SPEC: Wraps raw Tooltip with consistent decoration. New lint rule
/// `no_raw_tooltip` will enforce this wrapper in presentation layer.
class AppTooltip extends StatelessWidget {
  const AppTooltip({
    super.key,
    required this.message,
    required this.child,
    this.preferBelow = true,
    this.waitDuration,
  });

  final String message;
  final Widget child;
  final bool preferBelow;

  /// How long before the tooltip appears. Default: 500ms (Material default).
  final Duration? waitDuration;

  @override
  Widget build(BuildContext context) {
    // NOTE: Tooltip inherits tooltipTheme from ThemeData. We do NOT set
    // colors or decoration manually. All styling comes from the active theme.
    return Tooltip(
      message: message,
      preferBelow: preferBelow,
      waitDuration: waitDuration,
      child: child,
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/app_tooltip.dart"
```
Expected: No issues found.

---

#### Step 3.1.6: Update atoms barrel with new atoms

Edit `lib/core/design_system/atoms/atoms.dart` to add new atom exports. After Phase 2, this barrel should already exist with the moved atoms. Add the 5 new files:

```dart
// lib/core/design_system/atoms/atoms.dart
// WHY: Sub-directory barrel for all atomic design system components.

// Existing atoms (moved from flat design_system/ in Phase 2)
export 'app_text.dart';
export 'app_icon.dart';
export 'app_chip.dart';
export 'app_toggle.dart';
export 'app_progress_bar.dart';
export 'app_mini_spinner.dart';

// New atoms (Phase 3)
export 'app_button.dart';
export 'app_badge.dart';
export 'app_divider.dart';
export 'app_avatar.dart';
export 'app_tooltip.dart';
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/"
```
Expected: No issues found.

---

### Sub-phase 3.2: Move Existing Atoms to `atoms/`

**EXECUTION ORDER**: This sub-phase MUST execute BEFORE Sub-phase 3.1 (New Atoms). New atoms depend on existing atoms being in the `atoms/` directory.

**Agent**: `code-fixer-agent`

**IMPORTANT**: This sub-phase assumes Phase 2 has NOT already moved these files. If Phase 2 already created the atoms/ directory and moved files there, skip this sub-phase entirely. The plan is written defensively.

#### Step 3.2.1: Move `app_text.dart` to `atoms/`

Move `lib/core/design_system/app_text.dart` to `lib/core/design_system/atoms/app_text.dart`.

The file has zero internal design_system imports (it only imports `package:flutter/material.dart`), so no relative import changes needed.

**Action**: Copy content to new path, delete old file.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/app_text.dart"
```
Expected: No issues found.

---

#### Step 3.2.2: Move `app_icon.dart` to `atoms/`

Move `lib/core/design_system/app_icon.dart` to `lib/core/design_system/atoms/app_icon.dart`.

Update internal import — the file imports `../theme/design_constants.dart`. After the move to `atoms/`, the relative import becomes `../../theme/design_constants.dart`.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/app_icon.dart"
```
Expected: No issues found.

---

#### Step 3.2.3: Move `app_chip.dart` to `atoms/`

Move `lib/core/design_system/app_chip.dart` to `lib/core/design_system/atoms/app_chip.dart`.

Update internal imports:
- `../theme/colors.dart` becomes `../../theme/colors.dart`
- `../theme/field_guide_colors.dart` becomes `../../theme/field_guide_colors.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/app_chip.dart"
```
Expected: No issues found.

---

#### Step 3.2.4: Move `app_toggle.dart` to `atoms/`

Move `lib/core/design_system/app_toggle.dart` to `lib/core/design_system/atoms/app_toggle.dart`.

Update import: `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/app_toggle.dart"
```
Expected: No issues found.

---

#### Step 3.2.5: Move `app_progress_bar.dart` to `atoms/`

Move `lib/core/design_system/app_progress_bar.dart` to `lib/core/design_system/atoms/app_progress_bar.dart`.

Update imports:
- `../theme/field_guide_colors.dart` becomes `../../theme/field_guide_colors.dart`
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/app_progress_bar.dart"
```
Expected: No issues found.

---

#### Step 3.2.6: Move `app_mini_spinner.dart` to `atoms/`

Move `lib/core/design_system/app_mini_spinner.dart` to `lib/core/design_system/atoms/app_mini_spinner.dart`.

Update import: `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/app_mini_spinner.dart"
```
Expected: No issues found.

---

#### Step 3.2.7: Update atoms barrel (moved files)

Ensure `lib/core/design_system/atoms/atoms.dart` contains all 6 moved + 5 new exports. (This was already done in Step 3.1.6; verify the barrel is correct.)

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/atoms/"
```
Expected: No issues found.

---

### Sub-phase 3.3: New Molecules

**Agent**: `code-fixer-agent`

#### Step 3.3.1: Create `AppDropdown`

Create `lib/core/design_system/molecules/app_dropdown.dart`:

```dart
import 'package:flutter/material.dart';

/// Themed dropdown wrapping DropdownButtonFormField with consistent styling.
///
/// Usage:
/// ```dart
/// AppDropdown<String>(
///   label: 'Entry Type',
///   value: _selectedType,
///   items: types.map((t) => DropdownMenuItem(value: t.id, child: Text(t.name))).toList(),
///   onChanged: (v) => setState(() => _selectedType = v),
/// )
/// ```
///
/// FROM SPEC: Wraps raw DropdownButtonFormField. New lint rule `no_raw_dropdown`
/// will enforce this wrapper. All styling inherited from inputDecorationTheme.
class AppDropdown<T> extends StatelessWidget {
  const AppDropdown({
    super.key,
    required this.items,
    required this.onChanged,
    this.value,
    this.label,
    this.hint,
    this.prefixIcon,
    this.validator,
    this.enabled = true,
    this.isDense = true,
    this.isExpanded = true,
  });

  final List<DropdownMenuItem<T>> items;
  final ValueChanged<T?>? onChanged;
  final T? value;
  final String? label;
  final String? hint;
  final IconData? prefixIcon;
  final String? Function(T?)? validator;
  final bool enabled;
  final bool isDense;
  final bool isExpanded;

  @override
  Widget build(BuildContext context) {
    // NOTE: DropdownButtonFormField inherits inputDecorationTheme from ThemeData.
    // We do NOT set colors manually. Border, fill, and label styles come from theme.
    return DropdownButtonFormField<T>(
      value: value,
      items: items,
      onChanged: enabled ? onChanged : null,
      validator: validator,
      isDense: isDense,
      isExpanded: isExpanded,
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: prefixIcon != null ? Icon(prefixIcon) : null,
      ),
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/molecules/app_dropdown.dart"
```
Expected: No issues found.

---

#### Step 3.3.2: Create `AppDatePicker`

Create `lib/core/design_system/molecules/app_date_picker.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
// NOTE: DesignConstants import removed -- not used in this widget.

/// Themed date picker field that wraps showDatePicker with consistent styling.
///
/// Usage:
/// ```dart
/// AppDatePicker(
///   label: 'Entry Date',
///   value: _selectedDate,
///   onChanged: (date) => setState(() => _selectedDate = date),
/// )
/// ```
///
/// FROM SPEC: Wraps date picker with theme tokens. All dialog styling inherited
/// from datePickerTheme in ThemeData.
class AppDatePicker extends StatefulWidget { // WHY: StatefulWidget to own/dispose TextEditingController (memory leak fix)
  const AppDatePicker({
    super.key,
    required this.label,
    required this.onChanged,
    this.value,
    this.firstDate,
    this.lastDate,
    this.dateFormat,
    this.prefixIcon = Icons.calendar_today,
    this.enabled = true,
    this.validator,
  });

  final String label;
  final ValueChanged<DateTime?> onChanged;
  final DateTime? value;

  /// Earliest selectable date. Default: 2 years ago.
  final DateTime? firstDate;

  /// Latest selectable date. Default: 2 years from now.
  final DateTime? lastDate;

  /// Date format string. Default: 'MMM d, yyyy'.
  final String? dateFormat;

  final IconData? prefixIcon;
  final bool enabled;
  final String? Function(String?)? validator;

  @override
  Widget build(BuildContext context) {
    final formatter = DateFormat(dateFormat ?? 'MMM d, yyyy');
    final displayText = value != null ? formatter.format(value!) : '';

    return TextFormField(
      readOnly: true,
      controller: TextEditingController(text: displayText),
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: prefixIcon != null ? Icon(prefixIcon) : null,
        suffixIcon: value != null && enabled
            ? IconButton(
                icon: const Icon(Icons.clear),
                onPressed: () => onChanged(null),
              )
            : null,
      ),
      enabled: enabled,
      validator: validator,
      onTap: enabled
          ? () async {
              // NOTE: datePickerTheme from AppTheme controls all dialog styling.
              final picked = await showDatePicker(
                context: context,
                initialDate: value ?? DateTime.now(),
                firstDate: firstDate ?? DateTime.now().subtract(const Duration(days: 730)),
                lastDate: lastDate ?? DateTime.now().add(const Duration(days: 730)),
              );
              if (picked != null) {
                onChanged(picked);
              }
            }
          : null,
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/molecules/app_date_picker.dart"
```
Expected: No issues found.

---

#### Step 3.3.3: Create `AppTabBar`

Create `lib/core/design_system/molecules/app_tab_bar.dart`:

```dart
import 'package:flutter/material.dart';

/// Themed tab bar using design tokens for consistent styling.
///
/// Usage:
/// ```dart
/// AppTabBar(
///   controller: _tabController,
///   tabs: [
///     Tab(text: 'Active'),
///     Tab(text: 'Archived'),
///   ],
/// )
/// ```
///
/// FROM SPEC: Wraps raw TabBar with consistent styling. All colors and indicator
/// styling inherited from tabBarTheme in ThemeData.
class AppTabBar extends StatelessWidget implements PreferredSizeWidget {
  const AppTabBar({
    super.key,
    required this.tabs,
    this.controller,
    this.isScrollable = false,
    this.onTap,
  });

  final List<Widget> tabs;
  final TabController? controller;
  final bool isScrollable;
  final ValueChanged<int>? onTap;

  @override
  Widget build(BuildContext context) {
    // NOTE: TabBar inherits tabBarTheme from ThemeData. We do NOT set
    // indicator color, label color, etc. manually. Theme consistency.
    return TabBar(
      controller: controller,
      tabs: tabs,
      isScrollable: isScrollable,
      onTap: onTap,
    );
  }

  @override
  Size get preferredSize => const Size.fromHeight(kTextTabBarHeight);
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/molecules/app_tab_bar.dart"
```
Expected: No issues found.

---

#### Step 3.3.4: Update molecules barrel with new molecules

Edit `lib/core/design_system/molecules/molecules.dart`:

```dart
// lib/core/design_system/molecules/molecules.dart
// WHY: Sub-directory barrel for all molecule-level design system components.

// Existing molecules (moved from flat design_system/ in Phase 2)
export 'app_text_field.dart';
export 'app_counter_field.dart';
export 'app_list_tile.dart';
export 'app_section_header.dart';

// New molecules (Phase 3)
export 'app_dropdown.dart';
export 'app_date_picker.dart';
export 'app_tab_bar.dart';
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/molecules/"
```
Expected: No issues found.

---

### Sub-phase 3.4: Move Existing Molecules + Migrate SearchBar

**Agent**: `code-fixer-agent`

**IMPORTANT**: Same note as 3.2 — if Phase 2 already moved these, skip the move steps and proceed to 3.4.5 (SearchBar migration).

#### Step 3.4.1: Move `app_text_field.dart` to `molecules/`

Move `lib/core/design_system/app_text_field.dart` to `lib/core/design_system/molecules/app_text_field.dart`.

The file only imports `package:flutter/material.dart` and `package:flutter/services.dart` — no relative import changes needed.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/molecules/app_text_field.dart"
```
Expected: No issues found.

---

#### Step 3.4.2: Move `app_counter_field.dart` to `molecules/`

Move `lib/core/design_system/app_counter_field.dart` to `lib/core/design_system/molecules/app_counter_field.dart`.

Update imports:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`
- `../theme/field_guide_colors.dart` becomes `../../theme/field_guide_colors.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/molecules/app_counter_field.dart"
```
Expected: No issues found.

---

#### Step 3.4.3: Move `app_list_tile.dart` to `molecules/`

Move `lib/core/design_system/app_list_tile.dart` to `lib/core/design_system/molecules/app_list_tile.dart`.

Update imports:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`
- `../theme/field_guide_colors.dart` becomes `../../theme/field_guide_colors.dart`
- `app_glass_card.dart` becomes `../organisms/app_glass_card.dart`

**NOTE**: `app_glass_card.dart` will be in `organisms/` after sub-phase 3.5. If 3.5 has not yet run, use `../app_glass_card.dart` temporarily and update after 3.5. Alternatively, ensure phases run in order: 3.4 before 3.5, and use the barrel import instead:

```dart
// WHY: Use barrel import to avoid fragile relative paths across subdirectories.
import '../organisms/app_glass_card.dart';
```

If the move ordering makes this tricky, the safer approach is to import from the main barrel:
```dart
import 'package:construction_inspector/core/design_system/design_system.dart';
```
But this creates a circular barrel dependency. The correct approach: use a direct relative import to the organisms sub-directory.

**IMPORTANT**: The implementing agent must check whether `app_glass_card.dart` has already been moved to `organisms/` before writing this import. If not yet moved, use `'../app_glass_card.dart'` and flag for update in Step 3.5.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/molecules/app_list_tile.dart"
```
Expected: No issues found.

---

#### Step 3.4.4: Move `app_section_header.dart` to `molecules/`

Move `lib/core/design_system/app_section_header.dart` to `lib/core/design_system/molecules/app_section_header.dart`.

Update import: `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/molecules/app_section_header.dart"
```
Expected: No issues found.

---

#### Step 3.4.5: Migrate `SearchBarField` to `AppSearchBar`

Create `lib/core/design_system/molecules/app_search_bar.dart` based on `lib/shared/widgets/search_bar_field.dart`:

```dart
import 'package:flutter/material.dart';
import '../../theme/design_constants.dart';
import 'app_text_field.dart';

/// Reusable search bar for filtering lists with consistent styling.
///
/// Usage:
/// ```dart
/// AppSearchBar(
///   controller: _searchController,
///   hintText: 'Search projects...',
///   onChanged: (query) => _filterResults(query),
/// )
/// ```
///
/// FROM SPEC: Migrated from lib/shared/widgets/search_bar_field.dart. Class renamed
/// from SearchBarField to AppSearchBar for design system naming consistency.
/// Original had 0 direct importers (barrel-exported only via widgets.dart).
class AppSearchBar extends StatefulWidget {
  final TextEditingController controller;
  final String hintText;
  final ValueChanged<String>? onChanged;
  final VoidCallback? onClear;
  final bool autofocus;
  final Key? fieldKey;

  const AppSearchBar({
    super.key,
    required this.controller,
    this.hintText = 'Search...',
    this.onChanged,
    this.onClear,
    this.autofocus = false,
    this.fieldKey,
  });

  @override
  State<AppSearchBar> createState() => _AppSearchBarState();
}

class _AppSearchBarState extends State<AppSearchBar> {
  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onTextChanged);
    super.dispose();
  }

  void _onTextChanged() {
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    // WHY: Delegates to AppTextField for consistent input decoration theme.
    return AppTextField(
      key: widget.fieldKey,
      controller: widget.controller,
      autofocus: widget.autofocus,
      hint: widget.hintText,
      prefixIcon: Icons.search,
      suffixIcon: widget.controller.text.isNotEmpty
          ? const Icon(Icons.clear)
          : null,
      onSuffixTap: widget.controller.text.isNotEmpty
          ? () {
              widget.controller.clear();
              widget.onClear?.call();
              widget.onChanged?.call('');
            }
          : null,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(DesignConstants.radiusMedium),
      ),
      contentPadding: const EdgeInsets.symmetric(
        horizontal: DesignConstants.space4,
      ),
      onChanged: widget.onChanged,
    );
  }
}

/// Backward-compatibility typedef for consumers still using SearchBarField.
/// WHY: Allows gradual migration without breaking existing code.
@Deprecated('Use AppSearchBar instead')
typedef SearchBarField = AppSearchBar;
```

Delete `lib/shared/widgets/search_bar_field.dart` after creation.

Update molecules barrel — add `export 'app_search_bar.dart';` to `lib/core/design_system/molecules/molecules.dart`.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/molecules/app_search_bar.dart"
```
Expected: No issues found.

---

### Sub-phase 3.5: Move Existing Organisms to `organisms/`

**Agent**: `code-fixer-agent`

#### Step 3.5.1: Move `app_glass_card.dart` to `organisms/`

Move `lib/core/design_system/app_glass_card.dart` to `lib/core/design_system/organisms/app_glass_card.dart`.

Update imports:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`
- `../theme/field_guide_colors.dart` becomes `../../theme/field_guide_colors.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_glass_card.dart"
```
Expected: No issues found.

---

#### Step 3.5.2: Move `app_section_card.dart` to `organisms/`

Move `lib/core/design_system/app_section_card.dart` to `lib/core/design_system/organisms/app_section_card.dart`.

Update imports:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`
- `../theme/field_guide_colors.dart` becomes `../../theme/field_guide_colors.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_section_card.dart"
```
Expected: No issues found.

---

#### Step 3.5.3: Move `app_photo_grid.dart` to `organisms/`

Move `lib/core/design_system/app_photo_grid.dart` to `lib/core/design_system/organisms/app_photo_grid.dart`.

Update import:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_photo_grid.dart"
```
Expected: No issues found.

---

#### Step 3.5.4: Move `app_info_banner.dart` to `organisms/`

Move `lib/core/design_system/app_info_banner.dart` to `lib/core/design_system/organisms/app_info_banner.dart`.

Update imports:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`
- `app_icon.dart` becomes `../atoms/app_icon.dart`
- `app_text.dart` becomes `../atoms/app_text.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_info_banner.dart"
```
Expected: No issues found.

---

#### Step 3.5.5: Update `app_list_tile.dart` cross-reference

After `app_glass_card.dart` is moved to `organisms/`, update `lib/core/design_system/molecules/app_list_tile.dart` import:

Change `app_glass_card.dart` import to:
```dart
import '../organisms/app_glass_card.dart';
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/molecules/app_list_tile.dart"
```
Expected: No issues found.

---

#### Step 3.5.6: Update organisms barrel

Edit `lib/core/design_system/organisms/organisms.dart`:

```dart
// lib/core/design_system/organisms/organisms.dart
// WHY: Sub-directory barrel for all organism-level design system components.

// Existing organisms (moved from flat design_system/)
export 'app_glass_card.dart';
export 'app_section_card.dart';
export 'app_photo_grid.dart';
export 'app_info_banner.dart';
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/"
```
Expected: No issues found.

---

### Sub-phase 3.6: New Organisms — General

**Agent**: `code-fixer-agent`

#### Step 3.6.1: Create `AppStatCard`

Create `lib/core/design_system/organisms/app_stat_card.dart`:

```dart
import 'package:flutter/material.dart';
import '../../theme/design_constants.dart';
import '../atoms/app_icon.dart';
import '../atoms/app_text.dart';
import 'app_glass_card.dart';

/// Animated stat card for dashboard quick stats and summary displays.
///
/// Usage:
/// ```dart
/// AppStatCard(
///   label: 'Active Entries',
///   value: '12',
///   icon: Icons.description,
///   color: cs.primary,
///   onTap: () => navigateToEntries(),
/// )
/// ```
///
/// FROM SPEC: Generalized from DashboardStatCard (dashboard_stat_card.dart).
/// Reusable across dashboard, project summary, and sync dashboard screens.
/// WHY: DashboardStatCard is feature-specific but the pattern repeats across
/// 3+ features. Promoting to design system eliminates duplication.
class AppStatCard extends StatelessWidget {
  const AppStatCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
    this.onTap,
    this.animate = true,
  });

  /// Descriptive label (e.g., "Active Entries", "Photos Taken").
  final String label;

  /// Display value (e.g., "12", "$4,500", "92%").
  final String value;

  /// Leading icon.
  final IconData icon;

  /// Accent color for icon background and value text.
  final Color color;

  /// Optional tap handler.
  final VoidCallback? onTap;

  /// Whether to animate entrance. Default: true.
  final bool animate;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    Widget card = AppGlassCard(
      accentColor: color,
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // WHY: Circle icon container with 15% alpha background matches
          // the DashboardStatCard pattern from dashboard_stat_card.dart.
          Container(
            padding: const EdgeInsets.all(DesignConstants.space2),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.15),
              shape: BoxShape.circle,
            ),
            child: AppIcon(icon, size: AppIconSize.medium, color: color),
          ),
          const SizedBox(height: DesignConstants.space2),
          AppText.titleLarge(
            value,
            color: color,
          ),
          const SizedBox(height: DesignConstants.space1),
          AppText.labelSmall(
            label,
            color: cs.onSurfaceVariant,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );

    if (!animate) return card;

    // WHY: TweenAnimationBuilder provides a one-shot entrance animation
    // matching the existing DashboardStatCard scale+fade pattern.
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.0, end: 1.0),
      duration: DesignConstants.animationNormal,
      curve: DesignConstants.curveSpring,
      builder: (context, animValue, child) {
        return Transform.scale(
          scale: 0.9 + (0.1 * animValue),
          child: Opacity(
            opacity: animValue.clamp(0.0, 1.0),
            child: RepaintBoundary(child: child),
          ),
        );
      },
      child: card,
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_stat_card.dart"
```
Expected: No issues found.

---

#### Step 3.6.2: Create `AppActionCard`

Create `lib/core/design_system/organisms/app_action_card.dart`:

```dart
import 'package:flutter/material.dart';
import '../../theme/design_constants.dart';
import '../atoms/app_icon.dart';
import '../atoms/app_text.dart';
import 'app_glass_card.dart';

/// Tappable card with icon, title, subtitle, and optional trailing widget.
///
/// Usage:
/// ```dart
/// AppActionCard(
///   icon: Icons.add_circle_outline,
///   title: 'New Entry',
///   subtitle: 'Start a daily inspection report',
///   onTap: () => createEntry(),
/// )
/// ```
///
/// FROM SPEC: Generic tappable action card for CTAs, quick actions,
/// and navigation cards. Uses AppGlassCard for consistent glass styling.
class AppActionCard extends StatelessWidget {
  const AppActionCard({
    super.key,
    required this.title,
    required this.onTap,
    this.icon,
    this.subtitle,
    this.trailing,
    this.accentColor,
  });

  final String title;
  final VoidCallback onTap;
  final IconData? icon;
  final String? subtitle;

  /// Optional trailing widget (e.g., chevron icon, badge).
  final Widget? trailing;

  /// Optional left accent border color.
  final Color? accentColor;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return AppGlassCard(
      accentColor: accentColor,
      onTap: onTap,
      child: Row(
        children: [
          if (icon != null) ...[
            // WHY: Icon in a colored circle container for visual hierarchy,
            // consistent with AppStatCard and DashboardStatCard patterns.
            Container(
              padding: const EdgeInsets.all(DesignConstants.space2),
              decoration: BoxDecoration(
                color: (accentColor ?? cs.primary).withValues(alpha: 0.15),
                shape: BoxShape.circle,
              ),
              child: AppIcon(
                icon!,
                size: AppIconSize.medium,
                color: accentColor ?? cs.primary,
              ),
            ),
            const SizedBox(width: DesignConstants.space3),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                AppText.titleSmall(title),
                if (subtitle != null) ...[
                  const SizedBox(height: 2),
                  AppText.bodySmall(
                    subtitle!,
                    color: cs.onSurfaceVariant,
                  ),
                ],
              ],
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: DesignConstants.space2),
            trailing!,
          ] else ...[
            const SizedBox(width: DesignConstants.space2),
            AppIcon(
              Icons.chevron_right,
              size: AppIconSize.medium,
              color: cs.onSurfaceVariant,
            ),
          ],
        ],
      ),
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_action_card.dart"
```
Expected: No issues found.

---

#### Step 3.6.3: Update organisms barrel with general organisms

Add to `lib/core/design_system/organisms/organisms.dart`:

```dart
export 'app_stat_card.dart';
export 'app_action_card.dart';
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/"
```
Expected: No issues found.

---

### Sub-phase 3.7: New Organisms — Form Editor Primitives

**Agent**: `code-fixer-agent`

#### Step 3.7.1: Create `AppFormSection`

Create `lib/core/design_system/organisms/app_form_section.dart`:

```dart
import 'package:flutter/material.dart';
import '../../theme/design_constants.dart';
import '../../theme/field_guide_colors.dart';
import '../atoms/app_badge.dart';

/// Status enum for form section completion tracking.
///
/// WHY: Generalized from HubSectionStatus (form_accordion.dart:5).
/// Uses generic terms instead of form-specific terminology.
enum FormSectionStatus {
  /// Section not yet started.
  notStarted,

  /// Section in progress.
  inProgress,

  /// Section complete/submitted.
  complete,
}

/// Collapsible form section with status indicator, letter badge, and title.
///
/// Usage:
/// ```dart
/// AppFormSection(
///   letter: 'A',
///   title: 'Header Information',
///   subtitle: '3 of 5 fields complete',
///   accentColor: Colors.blue,
///   status: FormSectionStatus.inProgress,
///   expanded: _expandedSection == 'A',
///   onTap: () => setState(() => _expandedSection = 'A'),
///   expandedChild: HeaderFormFields(),
/// )
/// ```
///
/// FROM SPEC: Generalized from FormAccordion (form_accordion.dart).
/// Removes form-specific terminology, uses design tokens.
class AppFormSection extends StatelessWidget {
  const AppFormSection({
    super.key,
    required this.letter,
    required this.title,
    required this.subtitle,
    required this.accentColor,
    required this.status,
    required this.expanded,
    required this.onTap,
    required this.expandedChild,
    this.collapsedChild,
    this.headerKey,
    this.badgeKey,
  });

  /// Single letter identifier (e.g., 'A', 'B', 'C').
  final String letter;

  /// Section title.
  final String title;

  /// Subtitle text (e.g., "3 of 5 fields complete").
  final String subtitle;

  /// Accent color for letter badge and status indicators.
  final Color accentColor;

  /// Current completion status.
  final FormSectionStatus status;

  /// Whether this section is currently expanded.
  final bool expanded;

  /// Tap handler to toggle expansion.
  final VoidCallback onTap;

  /// Widget shown when section is expanded.
  final Widget expandedChild;

  /// Optional widget shown when collapsed.
  final Widget? collapsedChild;

  /// Optional key for header (testing).
  final Key? headerKey;

  /// Optional key for badge (testing).
  final Key? badgeKey;

  @override
  Widget build(BuildContext context) {
    final fg = FieldGuideColors.of(context);
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    // WHY: Left border visibility animates with expansion state,
    // matching the FormAccordion pattern.
    final borderColor = expanded
        ? accentColor.withValues(alpha: 0.3)
        : Colors.transparent;

    return AnimatedContainer(
      duration: DesignConstants.animationNormal,
      curve: DesignConstants.curveDefault,
      decoration: BoxDecoration(
        color: fg.surfaceElevated,
        borderRadius: BorderRadius.circular(DesignConstants.radiusMedium),
        border: Border(left: BorderSide(color: borderColor, width: 1.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Tappable header
          InkWell(
            key: headerKey,
            borderRadius: BorderRadius.circular(DesignConstants.radiusMedium),
            onTap: onTap,
            child: ConstrainedBox(
              constraints: const BoxConstraints(
                minHeight: DesignConstants.touchTargetComfortable,
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DesignConstants.space3,
                  vertical: DesignConstants.space2,
                ),
                child: Row(
                  children: [
                    // WHY: AppBadge.letter reuses the same pattern as
                    // FormAccordion._LetterBadge.
                    AppBadge.letter(letter, color: accentColor),
                    const SizedBox(width: DesignConstants.space2),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            title,
                            style: tt.titleSmall?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            subtitle,
                            style: tt.bodySmall?.copyWith(
                              color: cs.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                    ),
                    _StatusBadge(
                      key: badgeKey,
                      status: status,
                      accentColor: accentColor,
                    ),
                    const SizedBox(width: DesignConstants.space1),
                    Icon(
                      expanded ? Icons.expand_less : Icons.expand_more,
                      color: cs.onSurfaceVariant,
                    ),
                  ],
                ),
              ),
            ),
          ),
          // Collapsible body
          Padding(
            padding: const EdgeInsets.fromLTRB(
              DesignConstants.space3,
              0,
              DesignConstants.space3,
              DesignConstants.space3,
            ),
            child: AnimatedCrossFade(
              firstChild: collapsedChild ?? const SizedBox.shrink(),
              secondChild: expandedChild,
              crossFadeState: expanded
                  ? CrossFadeState.showSecond
                  : CrossFadeState.showFirst,
              duration: DesignConstants.animationNormal,
            ),
          ),
        ],
      ),
    );
  }
}

/// Internal status badge widget.
/// WHY: Extracted from FormAccordion._StatusBadge (form_accordion.dart:144).
/// Uses generalized FormSectionStatus enum instead of HubSectionStatus.
class _StatusBadge extends StatelessWidget {
  final FormSectionStatus status;
  final Color accentColor;

  const _StatusBadge({
    super.key,
    required this.status,
    required this.accentColor,
  });

  @override
  Widget build(BuildContext context) {
    final fg = FieldGuideColors.of(context);
    final cs = Theme.of(context).colorScheme;
    final (text, color) = switch (status) {
      FormSectionStatus.notStarted => ('Not Started', cs.onSurfaceVariant),
      FormSectionStatus.inProgress => ('In Progress', accentColor),
      FormSectionStatus.complete => ('Complete', fg.statusSuccess),
    };

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DesignConstants.space2,
        vertical: DesignConstants.space1,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(DesignConstants.radiusFull),
      ),
      child: Text(
        text,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_form_section.dart"
```
Expected: No issues found.

---

#### Step 3.7.2: Create `AppFormSectionNav`

Create `lib/core/design_system/organisms/app_form_section_nav.dart`:

```dart
import 'package:flutter/material.dart';
import '../../theme/design_constants.dart';
import '../../theme/field_guide_colors.dart';
import 'app_form_section.dart';

/// Data class for a section navigation item.
class FormSectionNavItem {
  const FormSectionNavItem({
    required this.id,
    required this.label,
    required this.status,
    required this.accentColor,
    this.key,
  });

  final String id;
  final String label;
  final FormSectionStatus status;
  final Color accentColor;
  final Key? key;
}

/// Section navigator with completion status pills.
///
/// Usage:
/// ```dart
/// AppFormSectionNav(
///   items: sections.map((s) => FormSectionNavItem(
///     id: s.id, label: s.letter, status: s.status, accentColor: s.color,
///   )).toList(),
///   selectedId: _currentSectionId,
///   onSelected: (id) => _scrollToSection(id),
/// )
/// ```
///
/// FROM SPEC: Generalized from StatusPillBar (status_pill_bar.dart).
/// Provides horizontal scrollable pill navigation with status indicators.
/// WHY: StatusPillBar is tightly coupled to HubSectionStatus. This generalized
/// version uses FormSectionStatus and supports optional onSelected callback.
class AppFormSectionNav extends StatelessWidget {
  const AppFormSectionNav({
    super.key,
    required this.items,
    this.selectedId,
    this.onSelected,
  });

  final List<FormSectionNavItem> items;

  /// Currently selected section ID. If null, no pill is highlighted.
  final String? selectedId;

  /// Callback when a pill is tapped.
  final ValueChanged<String>? onSelected;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          for (final item in items) ...[
            _NavPill(
              item: item,
              isSelected: item.id == selectedId,
              onTap: onSelected != null ? () => onSelected!(item.id) : null,
            ),
            const SizedBox(width: DesignConstants.space2),
          ],
        ],
      ),
    );
  }
}

class _NavPill extends StatelessWidget {
  final FormSectionNavItem item;
  final bool isSelected;
  final VoidCallback? onTap;

  const _NavPill({
    required this.item,
    required this.isSelected,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final fg = FieldGuideColors.of(context);
    final cs = Theme.of(context).colorScheme;

    // WHY: Color logic mirrors StatusPillBar._StatusPill (status_pill_bar.dart:51).
    final color = switch (item.status) {
      FormSectionStatus.notStarted => cs.onSurfaceVariant,
      FormSectionStatus.inProgress => item.accentColor,
      FormSectionStatus.complete => fg.statusSuccess,
    };

    return GestureDetector(
      onTap: onTap,
      child: Container(
        key: item.key,
        padding: const EdgeInsets.symmetric(
          horizontal: DesignConstants.space3,
          vertical: DesignConstants.space2,
        ),
        decoration: BoxDecoration(
          color: isSelected
              ? color.withValues(alpha: 0.15)
              : fg.surfaceElevated,
          borderRadius: BorderRadius.circular(DesignConstants.space5),
          border: Border.all(color: color.withValues(alpha: 0.4)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Status dot
            Container(
              width: 5,
              height: 5,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
            const SizedBox(width: DesignConstants.space2),
            Text(
              item.label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: color,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_form_section_nav.dart"
```
Expected: No issues found.

---

#### Step 3.7.3: Create `AppFormStatusBar`

Create `lib/core/design_system/organisms/app_form_status_bar.dart`:

```dart
import 'package:flutter/material.dart';
import '../../theme/design_constants.dart';
import '../../theme/field_guide_colors.dart';
import '../atoms/app_text.dart';
import 'app_form_section.dart';

/// Form-level completion status bar with validation summary.
///
/// Usage:
/// ```dart
/// AppFormStatusBar(
///   completedCount: 3,
///   totalCount: 5,
///   label: '3 of 5 sections complete',
/// )
/// ```
///
/// FROM SPEC: Generalized from StatusPillBar for form-level completion display.
/// Shows a progress indicator with count and optional validation messages.
class AppFormStatusBar extends StatelessWidget {
  const AppFormStatusBar({
    super.key,
    required this.completedCount,
    required this.totalCount,
    this.label,
    this.validationErrors = const [],
  });

  /// Number of completed sections/fields.
  final int completedCount;

  /// Total number of sections/fields.
  final int totalCount;

  /// Optional label override. Default: "{completed} of {total} complete".
  final String? label;

  /// Optional list of validation error messages.
  final List<String> validationErrors;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final fg = FieldGuideColors.of(context);

    final progress = totalCount > 0 ? completedCount / totalCount : 0.0;
    final isComplete = completedCount >= totalCount;
    final displayLabel = label ?? '$completedCount of $totalCount complete';

    // WHY: Green for complete, primary for in-progress matches status patterns.
    final statusColor = isComplete ? fg.statusSuccess : cs.primary;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Icon(
              isComplete ? Icons.check_circle : Icons.pending,
              color: statusColor,
              size: DesignConstants.iconSizeSmall,
            ),
            const SizedBox(width: DesignConstants.space2),
            Expanded(
              child: AppText.labelMedium(
                displayLabel,
                color: statusColor,
              ),
            ),
          ],
        ),
        const SizedBox(height: DesignConstants.space2),
        // Progress bar
        ClipRRect(
          borderRadius: BorderRadius.circular(DesignConstants.radiusFull),
          child: LinearProgressIndicator(
            value: progress,
            minHeight: 4,
            backgroundColor: fg.surfaceBright.withValues(alpha: 0.3),
            valueColor: AlwaysStoppedAnimation(statusColor),
          ),
        ),
        // Validation errors
        if (validationErrors.isNotEmpty) ...[
          const SizedBox(height: DesignConstants.space2),
          for (final error in validationErrors)
            Padding(
              padding: const EdgeInsets.only(bottom: 2),
              child: Row(
                children: [
                  Icon(Icons.error_outline, color: cs.error, size: 14),
                  const SizedBox(width: DesignConstants.space1),
                  Expanded(
                    child: AppText.bodySmall(error, color: cs.error),
                  ),
                ],
              ),
            ),
        ],
      ],
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_form_status_bar.dart"
```
Expected: No issues found.

---

#### Step 3.7.4: Create `AppFormFieldGroup`

Create `lib/core/design_system/organisms/app_form_field_group.dart`:

```dart
import 'package:flutter/material.dart';
import '../../theme/design_constants.dart';
import '../atoms/app_text.dart';

/// Groups related form fields with label, optional help text, and layout.
///
/// Usage:
/// ```dart
/// AppFormFieldGroup(
///   label: 'Location Details',
///   helpText: 'Enter the intersection or landmark',
///   children: [
///     AppTextField(label: 'Street', controller: _streetCtrl),
///     AppTextField(label: 'City', controller: _cityCtrl),
///   ],
/// )
/// ```
///
/// FROM SPEC: Extracts the common form field grouping pattern from hub content
/// screens. Groups fields with a label header and consistent spacing.
class AppFormFieldGroup extends StatelessWidget {
  const AppFormFieldGroup({
    super.key,
    required this.label,
    required this.children,
    this.helpText,
    this.spacing,
  });

  /// Group label text.
  final String label;

  /// Child widgets (form fields).
  final List<Widget> children;

  /// Optional help text shown below the label.
  final String? helpText;

  /// Spacing between child fields. Default: space3 (12px).
  final double? spacing;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final fieldSpacing = spacing ?? DesignConstants.space3;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Group label
        AppText.labelMedium(
          label.toUpperCase(),
          color: cs.onSurfaceVariant,
        ),
        if (helpText != null) ...[
          const SizedBox(height: DesignConstants.space1),
          AppText.bodySmall(
            helpText!,
            color: cs.onSurfaceVariant,
          ),
        ],
        const SizedBox(height: DesignConstants.space2),
        // Fields with spacing
        for (int i = 0; i < children.length; i++) ...[
          children[i],
          if (i < children.length - 1) SizedBox(height: fieldSpacing),
        ],
      ],
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_form_field_group.dart"
```
Expected: No issues found.

---

#### Step 3.7.5: Create `AppFormSummaryTile`

Create `lib/core/design_system/organisms/app_form_summary_tile.dart`:

```dart
import 'package:flutter/material.dart';
import '../../theme/design_constants.dart';

/// Data class for a summary tile entry.
class FormSummaryTileData {
  const FormSummaryTileData({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;
}

/// Compact read-only display of completed field values in a horizontal row.
///
/// Usage:
/// ```dart
/// AppFormSummaryTile(
///   tiles: [
///     FormSummaryTileData(label: 'Temperature', value: '72F'),
///     FormSummaryTileData(label: 'Moisture', value: '45%'),
///     FormSummaryTileData(label: 'Density', value: '98.2%'),
///   ],
/// )
/// ```
///
/// FROM SPEC: Generalized from SummaryTiles (summary_tiles.dart).
/// Same layout pattern: horizontal row of label:value pairs with equal spacing.
class AppFormSummaryTile extends StatelessWidget {
  const AppFormSummaryTile({
    super.key,
    required this.tiles,
  });

  final List<FormSummaryTileData> tiles;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    // WHY: Row layout with Expanded children matches SummaryTiles pattern
    // (summary_tiles.dart:19-49). Equal-width tiles with consistent styling.
    return Row(
      children: [
        for (int i = 0; i < tiles.length; i++) ...[
          Expanded(
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DesignConstants.space2,
                vertical: DesignConstants.space2,
              ),
              decoration: BoxDecoration(
                color: cs.surface,
                borderRadius: BorderRadius.circular(DesignConstants.radiusCompact),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    tiles[i].value,
                    style: tt.titleSmall?.copyWith(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    tiles[i].label,
                    style: tt.labelSmall?.copyWith(color: cs.onSurfaceVariant),
                  ),
                ],
              ),
            ),
          ),
          if (i != tiles.length - 1)
            const SizedBox(width: DesignConstants.space2),
        ],
      ],
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_form_summary_tile.dart"
```
Expected: No issues found.

---

#### Step 3.7.6: Create `AppFormThumbnail`

Create `lib/core/design_system/organisms/app_form_thumbnail.dart`:

```dart
import 'package:flutter/material.dart';
import '../../theme/design_constants.dart';
import '../../theme/field_guide_colors.dart';

/// Status enum for form thumbnails.
/// WHY: Decoupled from FormResponseStatus to avoid feature-layer dependency.
/// Feature code maps its domain status to this enum when constructing thumbnails.
enum FormThumbnailStatus { open, submitted, exported }

/// Mini preview card for form selection in attachment grids.
///
/// Usage:
/// ```dart
/// AppFormThumbnail(
///   name: '0582B Proctor',
///   status: FormThumbnailStatus.submitted,
///   onTap: () => openForm(response.id),
///   onDelete: () => deleteResponse(response.id),
/// )
/// ```
///
/// FROM SPEC: Generalized from FormThumbnail (form_thumbnail.dart).
/// Removes dependency on FormResponse/InspectorForm domain models.
/// Feature code provides primitive parameters instead.
class AppFormThumbnail extends StatelessWidget {
  const AppFormThumbnail({
    super.key,
    required this.name,
    required this.status,
    this.icon = Icons.description,
    this.onTap,
    this.onDelete,
  });

  /// Display name for the form.
  final String name;

  /// Form completion status.
  final FormThumbnailStatus status;

  /// Center icon. Default: Icons.description.
  final IconData icon;

  /// Tap handler to open the form.
  final VoidCallback? onTap;

  /// Delete handler. If null, delete button is hidden.
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: GestureDetector(
            onTap: onTap,
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: cs.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(DesignConstants.radiusSmall),
                border: Border.all(
                  color: cs.primary.withValues(alpha: 0.3),
                ),
              ),
              child: Stack(
                children: [
                  // Center icon
                  Center(
                    child: Icon(
                      icon,
                      size: DesignConstants.iconSizeXL,
                      color: cs.primary,
                    ),
                  ),
                  // Status badge (top-right)
                  Positioned(
                    top: DesignConstants.space1,
                    right: DesignConstants.space1,
                    child: _buildStatusBadge(context),
                  ),
                  // Delete button (top-left)
                  if (onDelete != null)
                    Positioned(
                      top: DesignConstants.space1,
                      left: DesignConstants.space1,
                      child: _buildDeleteButton(context),
                    ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: DesignConstants.space1),
        Text(
          name,
          style: tt.labelSmall?.copyWith(
            fontWeight: FontWeight.w500,
            color: cs.onSurface,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
      ],
    );
  }

  Widget _buildStatusBadge(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final fg = FieldGuideColors.of(context);

    // WHY: Color/icon mapping matches FormThumbnail._buildStatusBadge
    // (form_thumbnail.dart:84-91).
    final (color, statusIcon) = switch (status) {
      FormThumbnailStatus.open => (cs.primary, Icons.edit),
      FormThumbnailStatus.submitted => (fg.statusSuccess, Icons.check),
      FormThumbnailStatus.exported => (cs.tertiary, Icons.download_done),
    };

    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(DesignConstants.radiusXSmall),
      ),
      child: Icon(statusIcon, size: 14, color: color),
    );
  }

  Widget _buildDeleteButton(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return GestureDetector(
      onTap: onDelete,
      child: Container(
        padding: const EdgeInsets.all(DesignConstants.space1),
        decoration: BoxDecoration(
          color: cs.scrim.withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(DesignConstants.radiusXSmall),
        ),
        child: Icon(
          Icons.close,
          size: 14,
          color: cs.onInverseSurface,
        ),
      ),
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/app_form_thumbnail.dart"
```
Expected: No issues found.

---

#### Step 3.7.7: Update organisms barrel with form editor primitives

Add to `lib/core/design_system/organisms/organisms.dart`:

```dart
// Form editor organisms (Phase 3.7)
export 'app_form_section.dart';
export 'app_form_section_nav.dart';
export 'app_form_status_bar.dart';
export 'app_form_field_group.dart';
export 'app_form_summary_tile.dart';
export 'app_form_thumbnail.dart';
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/organisms/"
```
Expected: No issues found.

---

### Sub-phase 3.8: Move Existing Surfaces to `surfaces/`

**Agent**: `code-fixer-agent`

#### Step 3.8.1: Move `app_scaffold.dart` to `surfaces/`

Move `lib/core/design_system/app_scaffold.dart` to `lib/core/design_system/surfaces/app_scaffold.dart`.

The file only imports `package:flutter/material.dart` — no relative import changes needed.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/surfaces/app_scaffold.dart"
```
Expected: No issues found.

---

#### Step 3.8.2: Move `app_bottom_bar.dart` to `surfaces/`

Move `lib/core/design_system/app_bottom_bar.dart` to `lib/core/design_system/surfaces/app_bottom_bar.dart`.

Update import: `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/surfaces/app_bottom_bar.dart"
```
Expected: No issues found.

---

#### Step 3.8.3: Move `app_bottom_sheet.dart` to `surfaces/`

Move `lib/core/design_system/app_bottom_sheet.dart` to `lib/core/design_system/surfaces/app_bottom_sheet.dart`.

Update imports:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`
- `../theme/field_guide_colors.dart` becomes `../../theme/field_guide_colors.dart`
- `app_drag_handle.dart` becomes `app_drag_handle.dart` (same directory after move)

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/surfaces/app_bottom_sheet.dart"
```
Expected: No issues found.

---

#### Step 3.8.4: Move `app_dialog.dart` to `surfaces/`

Move `lib/core/design_system/app_dialog.dart` to `lib/core/design_system/surfaces/app_dialog.dart`.

Update import: `app_text.dart` becomes `../atoms/app_text.dart`.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/surfaces/app_dialog.dart"
```
Expected: No issues found.

---

#### Step 3.8.5: Move `app_sticky_header.dart` to `surfaces/`

Move `lib/core/design_system/app_sticky_header.dart` to `lib/core/design_system/surfaces/app_sticky_header.dart`.

Update import: `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/surfaces/app_sticky_header.dart"
```
Expected: No issues found.

---

#### Step 3.8.6: Move `app_drag_handle.dart` to `surfaces/`

Move `lib/core/design_system/app_drag_handle.dart` to `lib/core/design_system/surfaces/app_drag_handle.dart`.

Update imports:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`
- `../theme/field_guide_colors.dart` becomes `../../theme/field_guide_colors.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/surfaces/app_drag_handle.dart"
```
Expected: No issues found.

---

#### Step 3.8.7: Update surfaces barrel

Edit `lib/core/design_system/surfaces/surfaces.dart`:

```dart
// lib/core/design_system/surfaces/surfaces.dart
// WHY: Sub-directory barrel for all surface-level design system components.

export 'app_scaffold.dart';
export 'app_bottom_bar.dart';
export 'app_bottom_sheet.dart';
export 'app_dialog.dart';
export 'app_sticky_header.dart';
export 'app_drag_handle.dart';
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/surfaces/"
```
Expected: No issues found.

---

### Sub-phase 3.9: Move Existing Feedback + Migrations + New Banner

**Agent**: `code-fixer-agent`

#### Step 3.9.1: Move `app_empty_state.dart` to `feedback/`

Move `lib/core/design_system/app_empty_state.dart` to `lib/core/design_system/feedback/app_empty_state.dart`.

Update imports:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`
- `../theme/field_guide_colors.dart` becomes `../../theme/field_guide_colors.dart`
- `app_icon.dart` becomes `../atoms/app_icon.dart`
- `app_text.dart` becomes `../atoms/app_text.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/feedback/app_empty_state.dart"
```
Expected: No issues found.

---

#### Step 3.9.2: Move `app_error_state.dart` to `feedback/`

Move `lib/core/design_system/app_error_state.dart` to `lib/core/design_system/feedback/app_error_state.dart`.

Update imports:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`
- `app_icon.dart` becomes `../atoms/app_icon.dart`
- `app_text.dart` becomes `../atoms/app_text.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/feedback/app_error_state.dart"
```
Expected: No issues found.

---

#### Step 3.9.3: Move `app_loading_state.dart` to `feedback/`

Move `lib/core/design_system/app_loading_state.dart` to `lib/core/design_system/feedback/app_loading_state.dart`.

Update imports:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`
- `app_text.dart` becomes `../atoms/app_text.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/feedback/app_loading_state.dart"
```
Expected: No issues found.

---

#### Step 3.9.4: Move `app_budget_warning_chip.dart` to `feedback/`

Move `lib/core/design_system/app_budget_warning_chip.dart` to `lib/core/design_system/feedback/app_budget_warning_chip.dart`.

Update imports:
- `../theme/design_constants.dart` becomes `../../theme/design_constants.dart`
- `../theme/field_guide_colors.dart` becomes `../../theme/field_guide_colors.dart`
- `app_icon.dart` becomes `../atoms/app_icon.dart`
- `app_text.dart` becomes `../atoms/app_text.dart`

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/feedback/app_budget_warning_chip.dart"
```
Expected: No issues found.

---

#### Step 3.9.5: Migrate `SnackBarHelper` to `AppSnackbar`

Create `lib/core/design_system/feedback/app_snackbar.dart` based on `lib/shared/utils/snackbar_helper.dart`:

```dart
import 'package:flutter/material.dart';
import '../../theme/field_guide_colors.dart';

/// Centralized snackbar helper with consistent type-specific styling.
///
/// Usage:
/// ```dart
/// AppSnackbar.showSuccess(context, 'Entry saved');
/// AppSnackbar.showError(context, 'Failed to sync');
/// AppSnackbar.showInfo(context, 'Syncing...');
/// AppSnackbar.showWarning(context, 'Offline mode active');
/// AppSnackbar.showWithAction(context, 'Deleted', 'Undo', () => restore());
/// ```
///
/// FROM SPEC: Migrated from lib/shared/utils/snackbar_helper.dart (140 lines).
/// 3 direct importers to update: pdf_data_builder.dart, consent_screen.dart,
/// legal_document_screen.dart.
///
/// WHY: SnackBarHelper belongs in design system feedback layer, not shared/utils.
/// Class renamed to AppSnackbar for design system naming consistency.
class AppSnackbar {
  AppSnackbar._();

  /// Show a success snackbar with green background.
  ///
  /// Used for completed actions like save, delete, sync, etc.
  static void showSuccess(BuildContext context, String message) {
    final fgc = FieldGuideColors.of(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: TextStyle(color: fgc.textInverse),
        ),
        backgroundColor: fgc.statusSuccess,
      ),
    );
  }

  /// Show an error snackbar with red background.
  ///
  /// Used for failures, validation errors, network errors, etc.
  /// Optional [duration] overrides the default snackbar duration.
  static void showError(
    BuildContext context,
    String message, {
    Duration? duration,
  }) {
    final cs = Theme.of(context).colorScheme;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: TextStyle(color: cs.onError),
        ),
        backgroundColor: cs.error,
        duration: duration ?? const Duration(seconds: 4),
      ),
    );
  }

  /// Show an error snackbar with an action button, returning the controller.
  ///
  /// Used when the caller needs to chain on the snackbar's [closed] future,
  /// e.g. to reset a dedup flag after dismissal.
  static ScaffoldFeatureController<SnackBar, SnackBarClosedReason>
      showErrorWithAction(
    BuildContext context,
    String message, {
    required String actionLabel,
    required VoidCallback onAction,
    Duration duration = const Duration(seconds: 4),
  }) {
    final cs = Theme.of(context).colorScheme;
    return ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: TextStyle(color: cs.onError),
        ),
        backgroundColor: cs.error,
        duration: duration,
        action: SnackBarAction(
          label: actionLabel,
          textColor: cs.onError,
          onPressed: onAction,
        ),
      ),
    );
  }

  /// Show an informational snackbar with blue background.
  ///
  /// Used for neutral notifications, status updates, etc.
  static void showInfo(BuildContext context, String message) {
    final cs = Theme.of(context).colorScheme;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: TextStyle(color: cs.onPrimary),
        ),
        backgroundColor: cs.primary,
      ),
    );
  }

  /// Show a warning snackbar with orange background.
  ///
  /// Used for caution messages, partial completion, pending issues, etc.
  static void showWarning(BuildContext context, String message) {
    final fgc = FieldGuideColors.of(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          message,
          style: TextStyle(color: fgc.textInverse),
        ),
        backgroundColor: fgc.statusWarning,
      ),
    );
  }

  /// Show a snackbar with a custom action button.
  ///
  /// Used when user can take immediate action on the notification.
  /// Example: "Deleted project" with "Undo" action.
  static void showWithAction(
    BuildContext context,
    String message,
    String actionLabel,
    VoidCallback onAction,
  ) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        action: SnackBarAction(
          label: actionLabel,
          onPressed: onAction,
        ),
      ),
    );
  }
}

/// Backward-compatibility typedef for consumers still using SnackBarHelper.
/// WHY: 3 direct importers + barrel-exported. Gradual migration path.
@Deprecated('Use AppSnackbar instead')
typedef SnackBarHelper = AppSnackbar;
```

Now update the 3 direct importers. Change their import from:
```dart
import 'package:construction_inspector/shared/utils/snackbar_helper.dart';
```
to:
```dart
import 'package:construction_inspector/core/design_system/design_system.dart';
```

Files to update:
1. `lib/features/entries/presentation/controllers/pdf_data_builder.dart` — change `SnackBarHelper.showError(` to `AppSnackbar.showError(`
2. `lib/features/settings/presentation/screens/consent_screen.dart` — change all `SnackBarHelper.*` to `AppSnackbar.*`
3. `lib/features/settings/presentation/screens/legal_document_screen.dart` — change all `SnackBarHelper.*` to `AppSnackbar.*`

Delete `lib/shared/utils/snackbar_helper.dart` after all consumers are updated.

**NOTE**: Also check if `lib/shared/utils/utils.dart` barrel exports `snackbar_helper.dart` and remove that export line.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/feedback/app_snackbar.dart"
```
Expected: No issues found.

---

#### Step 3.9.6: Migrate `ContextualFeedbackOverlay` to `AppContextualFeedback`

Create `lib/core/design_system/feedback/app_contextual_feedback.dart` based on `lib/shared/widgets/contextual_feedback_overlay.dart`:

```dart
import 'package:flutter/material.dart';
import '../../theme/design_constants.dart';
import '../../theme/field_guide_colors.dart';
import '../atoms/app_text.dart';

/// Shows an animated contextual feedback popup anchored near a screen position.
///
/// Used for transient action feedback (delete confirmations, status changes)
/// that dismisses automatically after 2 seconds. Avoids snackbars when an
/// action originates from a specific location on screen (e.g. long-press).
///
/// Usage:
/// ```dart
/// AppContextualFeedback.show(
///   context: context,
///   message: 'Entry deleted',
///   isSuccess: true,
///   anchorPosition: _lastLongPressPosition,
///   mounted: () => mounted,
/// );
/// ```
///
/// FROM SPEC: Migrated from lib/shared/widgets/contextual_feedback_overlay.dart.
/// Original had 0 direct importers (barrel-exported only via widgets.dart).
class AppContextualFeedback {
  AppContextualFeedback._();

  static OverlayEntry? _currentOverlay;

  /// Show a feedback toast anchored to [anchorPosition].
  ///
  /// [mounted] is a callback that returns the calling widget's `mounted` state,
  /// used to safely remove the overlay on the auto-dismiss timer.
  static void show({
    required BuildContext context,
    required String message,
    required bool isSuccess,
    required Offset anchorPosition,
    required bool Function() mounted,
  }) {
    _currentOverlay?.remove();
    _currentOverlay = null;

    final overlay = Overlay.of(context);

    _currentOverlay = OverlayEntry(
      builder: (overlayContext) {
        final cs = Theme.of(overlayContext).colorScheme;
        final fg = FieldGuideColors.of(overlayContext);
        final textIconColor = isSuccess ? cs.onPrimary : cs.onError;
        return Positioned(
          left: DesignConstants.space5,
          right: DesignConstants.space5,
          top: anchorPosition.dy - 50,
          child: Material(
            color: Colors.transparent,
            child: Center(
              child: TweenAnimationBuilder<double>(
                tween: Tween(begin: 0.0, end: 1.0),
                duration: DesignConstants.animationFast,
                builder: (overlayContext, value, child) => Opacity(
                  opacity: value,
                  child: Transform.scale(
                    scale: 0.8 + (0.2 * value),
                    child: child,
                  ),
                ),
                child: Container(
                  constraints: BoxConstraints(
                    maxWidth: MediaQuery.sizeOf(overlayContext).width -
                        (DesignConstants.space5 * 2),
                  ),
                  padding: const EdgeInsets.symmetric(
                    horizontal: DesignConstants.space4,
                    vertical: DesignConstants.space3,
                  ),
                  decoration: BoxDecoration(
                    color: isSuccess ? fg.statusSuccess : cs.error,
                    borderRadius:
                        BorderRadius.circular(DesignConstants.radiusSmall),
                    boxShadow: [
                      BoxShadow(
                        color: cs.shadow.withValues(alpha: 0.2),
                        blurRadius: DesignConstants.elevationHigh,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        isSuccess ? Icons.check_circle : Icons.error,
                        color: textIconColor,
                        size: 20,
                      ),
                      const SizedBox(width: DesignConstants.space2),
                      Flexible(
                        child: AppText.labelLarge(
                          message,
                          color: textIconColor,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );

    overlay.insert(_currentOverlay!);

    // Auto-dismiss after 2 seconds
    Future.delayed(const Duration(seconds: 2), () {
      if (_currentOverlay != null && mounted()) {
        _currentOverlay!.remove();
        _currentOverlay = null;
      }
    });
  }

  /// Immediately remove the overlay without waiting for the timer.
  static void dismiss() {
    _currentOverlay?.remove();
    _currentOverlay = null;
  }
}

/// Backward-compatibility typedef for consumers still using ContextualFeedbackOverlay.
@Deprecated('Use AppContextualFeedback instead')
typedef ContextualFeedbackOverlay = AppContextualFeedback;
```

Delete `lib/shared/widgets/contextual_feedback_overlay.dart` after creation.

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/feedback/app_contextual_feedback.dart"
```
Expected: No issues found.

---

#### Step 3.9.7: Create `AppBanner`

Create `lib/core/design_system/feedback/app_banner.dart`:

```dart
import 'package:flutter/material.dart';

/// Severity level for [AppBanner] that maps to colors from the theme.
enum AppBannerSeverity {
  info, warning, error, success;

  /// Resolves this severity to a color from the theme.
  /// WHY: Uses `Theme.of(context).colorScheme` instead of FieldGuideColors
  /// because FieldGuideColors does not have a `statusError` field.
  /// This keeps the component compilable without depending on a Phase 1
  /// FieldGuideColors expansion that may or may not exist yet.
  Color resolve(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return switch (this) {
      AppBannerSeverity.info => cs.primary,
      AppBannerSeverity.warning => cs.tertiary,
      AppBannerSeverity.error => cs.error,
      AppBannerSeverity.success => cs.primary,
    };
  }
}

/// Generic composable banner for status messages, warnings, and notifications.
///
/// Usage:
/// ```dart
/// AppBanner(
///   icon: Icons.wifi_off,
///   message: 'Last server check was over 24 hours ago.',
///   color: fg.statusWarning,
///   actions: [
///     TextButton(onPressed: _retry, child: Text('Retry')),
///   ],
/// )
/// AppBanner(
///   icon: Icons.system_update,
///   message: 'A new version is available.',
///   color: fg.statusInfo,
///   dismissible: true,
///   onDismiss: () => setState(() => _dismissed = true),
/// )
/// ```
///
/// FROM SPEC: Generic composable banner that replaces StaleConfigWarning
/// and VersionBanner (shared/widgets/). Those will be recomposed from AppBanner
/// in Phase 4 (screen decomposition).
///
/// WHY: StaleConfigWarning and VersionBanner are nearly identical — both use
/// MaterialBanner with an icon, message, and optional action. This unifies them
/// into a single parameterized component.
class AppBanner extends StatelessWidget {
  const AppBanner({
    super.key,
    required this.icon,
    required this.message,
    this.color,
    this.severity,
    this.actions = const [],
    this.dismissible = false,
    this.onDismiss,
    this.testingKey,
  });

  /// Leading icon.
  final IconData icon;

  /// Banner message text.
  final String message;

  /// Accent color for icon and background tinting.
  /// If null, resolved from [severity] via [FieldGuideColors].
  final Color? color;

  /// Semantic severity that auto-resolves to a color from [FieldGuideColors].
  /// WHY: Callers can use `severity: AppBannerSeverity.warning` instead of
  /// manually looking up `fg.statusWarning`.
  final AppBannerSeverity? severity;

  /// Action buttons (e.g., Retry, Dismiss).
  final List<Widget> actions;

  /// Whether the banner can be dismissed. If true and no explicit dismiss
  /// action is in [actions], a "Dismiss" button is auto-added.
  final bool dismissible;

  /// Called when the banner is dismissed.
  final VoidCallback? onDismiss;

  /// Optional testing key for E2E test automation.
  final Key? testingKey;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;
    final effectiveColor = severity?.resolve(context) ?? color ?? cs.primary;

    // WHY: Build effective actions list. If dismissible and no actions provided,
    // add a default "Dismiss" button for consistent UX.
    final effectiveActions = [
      ...actions,
      if (dismissible && actions.isEmpty)
        TextButton(
          onPressed: onDismiss,
          child: const Text('Dismiss'),
        ),
    ];

    // NOTE: MaterialBanner handles layout, padding, and divider automatically.
    // We only provide semantic parameters.
    return MaterialBanner(
      key: testingKey,
      backgroundColor: effectiveColor.withValues(alpha: 0.08),
      leading: Icon(icon, color: effectiveColor),
      content: Text(
        message,
        style: tt.bodySmall?.copyWith(color: cs.onSurface),
      ),
      actions: effectiveActions.isEmpty
          ? [const SizedBox.shrink()]
          : effectiveActions,
    );
  }
}
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/feedback/app_banner.dart"
```
Expected: No issues found.

---

#### Step 3.9.8: Merge `EmptyStateWidget` into `AppEmptyState`

`AppEmptyState` already exists (moved to `feedback/` in Step 3.9.1). `EmptyStateWidget` (`lib/shared/widgets/empty_state_widget.dart`) has the same purpose with slightly different API.

Differences:
- `EmptyStateWidget` uses `subtitle` as required String, `actionButton` as Widget
- `AppEmptyState` uses `subtitle` as optional String, `actionLabel`/`onAction` as separate params

The `AppEmptyState` API is already a superset. No code changes to `AppEmptyState` needed.

**Action**: Delete `lib/shared/widgets/empty_state_widget.dart`. The `ContextualFeedbackOverlay` backward-compat typedef and barrel update handle the transition.

**Verification**: Handled in Step 3.10 (barrel update).

---

#### Step 3.9.9: Merge `showConfirmationDialog` functions into `AppDialog`

Add confirmation dialog static methods to `lib/core/design_system/surfaces/app_dialog.dart`. Edit the file to add these methods after the existing `show<T>` method:

```dart
  /// Shows a confirmation dialog with customizable title, message, and actions.
  ///
  /// Returns true if confirmed, false if cancelled or dismissed.
  ///
  /// FROM SPEC: Migrated from lib/shared/widgets/confirmation_dialog.dart.
  /// TestingKeys preserved for E2E test automation.
  ///
  /// IMPORTANT: This method needs access to TestingKeys. Import path:
  /// import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';
  static Future<bool> showConfirmation(
    BuildContext context, {
    required String title,
    required String message,
    String confirmText = 'Confirm',
    String cancelText = 'Cancel',
    bool isDestructive = false,
    IconData? icon,
    Color? iconColor,
  }) async {
    final result = await show<bool>(
      context,
      title: title,
      content: Text(message),
      icon: icon,
      iconColor: iconColor,
      dialogKey: TestingKeys.confirmationDialog,
      actionsBuilder: (ctx) => [
        TextButton(
          key: TestingKeys.cancelDialogButton,
          onPressed: () => Navigator.pop(ctx, false),
          child: Text(cancelText),
        ),
        ElevatedButton(
          key: _getConfirmButtonKey(confirmText),
          onPressed: () => Navigator.pop(ctx, true),
          style: isDestructive
              ? ElevatedButton.styleFrom(
                  backgroundColor: Theme.of(context).colorScheme.error,
                  foregroundColor: Theme.of(context).colorScheme.onError,
                )
              : null,
          child: Text(confirmText),
        ),
      ],
    );
    return result ?? false;
  }

  /// Shows a delete confirmation dialog.
  ///
  /// Specialized version for delete operations.
  static Future<bool> showDeleteConfirmation(
    BuildContext context, {
    required String itemName,
    String? customMessage,
  }) async {
    final result = await show<bool>(
      context,
      title: 'Delete $itemName?',
      content: Text(customMessage ?? 'This action cannot be undone.'),
      icon: Icons.delete_outline,
      iconColor: Theme.of(context).colorScheme.error,
      dialogKey: TestingKeys.confirmationDialog,
      actionsBuilder: (ctx) => [
        TextButton(
          key: TestingKeys.confirmationDialogCancel,
          onPressed: () => Navigator.pop(ctx, false),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          key: TestingKeys.deleteConfirmButton,
          onPressed: () => Navigator.pop(ctx, true),
          style: ElevatedButton.styleFrom(
            backgroundColor: Theme.of(context).colorScheme.error,
            foregroundColor: Theme.of(context).colorScheme.onError,
          ),
          child: const Text('Delete'),
        ),
      ],
    );
    return result ?? false;
  }

  /// Shows an unsaved changes dialog with Save/Discard/Cancel options.
  ///
  /// Returns: true = Save, false = Discard, null = Cancel.
  static Future<bool?> showUnsavedChanges(
    BuildContext context, {
    bool isEditMode = false,
  }) async {
    return show<bool?>(
      context,
      title: isEditMode ? 'Save Changes?' : 'Save Entry?',
      content: Text(isEditMode
          ? 'Would you like to save your changes before leaving?'
          : 'Would you like to save this entry as a draft before leaving?'),
      dialogKey: TestingKeys.unsavedChangesDialog,
      actionsBuilder: (ctx) => [
        TextButton(
          key: TestingKeys.unsavedChangesCancel,
          onPressed: () => Navigator.pop(ctx, null),
          child: const Text('Cancel'),
        ),
        TextButton(
          key: TestingKeys.entryWizardSaveDraft,
          onPressed: () => Navigator.pop(ctx, true),
          child: Text(isEditMode ? 'Save' : 'Save Draft'),
        ),
        TextButton(
          key: TestingKeys.discardDialogButton,
          onPressed: () => Navigator.pop(ctx, false),
          style: TextButton.styleFrom(
              foregroundColor: Theme.of(context).colorScheme.error),
          child: const Text('Discard'),
        ),
      ],
    );
  }

  /// Helper function to determine the correct key for confirm buttons.
  static Key _getConfirmButtonKey(String confirmText) {
    switch (confirmText.toLowerCase()) {
      case 'confirm':
        return TestingKeys.confirmDialogButton;
      case 'archive':
        return TestingKeys.archiveConfirmButton;
      default:
        return Key('confirmation_dialog_${confirmText.toLowerCase().replaceAll(' ', '_')}');
    }
  }
```

**IMPORTANT**: The `app_dialog.dart` file (now in `surfaces/`) must add this import at the top:
```dart
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';
```

After adding these methods, delete `lib/shared/widgets/confirmation_dialog.dart`.

**NOTE**: Any file that currently calls `showConfirmationDialog(...)` (the top-level function from confirmation_dialog.dart) must be updated to call `AppDialog.showConfirmation(...)`. Search for usages:

```
pwsh -Command "flutter analyze lib/core/design_system/surfaces/app_dialog.dart"
```
Expected: No issues found.

---

#### Step 3.9.10: Update feedback barrel

Edit `lib/core/design_system/feedback/feedback.dart`:

```dart
// lib/core/design_system/feedback/feedback.dart
// WHY: Sub-directory barrel for all feedback-level design system components.

// Existing feedback components (moved from flat design_system/)
export 'app_empty_state.dart';
export 'app_error_state.dart';
export 'app_loading_state.dart';
export 'app_budget_warning_chip.dart';

// New/migrated feedback components (Phase 3)
export 'app_snackbar.dart';
export 'app_contextual_feedback.dart';
export 'app_banner.dart';
```

**Verification**:
```
pwsh -Command "flutter analyze lib/core/design_system/feedback/"
```
Expected: No issues found.

---

### Sub-phase 3.10: Update Shared Widgets Barrel

**Agent**: `code-fixer-agent`

#### Step 3.10.1: Update `lib/shared/widgets/widgets.dart`

After all migrations and deletions from Phase 3, the barrel should contain only `permission_dialog.dart`:

```dart
library;

// WHY: All other widgets migrated to lib/core/design_system/ in Phase 3.
// - confirmation_dialog.dart -> AppDialog.showConfirmation() (surfaces/)
// - contextual_feedback_overlay.dart -> AppContextualFeedback (feedback/)
// - empty_state_widget.dart -> merged into AppEmptyState (feedback/)
// - search_bar_field.dart -> AppSearchBar (molecules/)
// - stale_config_warning.dart -> retained here until P4 recomposes from AppBanner
// - version_banner.dart -> retained here until P4 recomposes from AppBanner

export 'permission_dialog.dart';
export 'stale_config_warning.dart';
export 'version_banner.dart';
```

**NOTE**: `stale_config_warning.dart` and `version_banner.dart` are NOT deleted in Phase 3. Per the spec, they will be recomposed from `AppBanner` in Phase 4 (screen decomposition). They remain in shared/widgets for now to avoid breaking `scaffold_with_nav_bar.dart` which directly imports them. Phase 4 will recompose them as thin wrappers around `AppBanner` and then delete the originals.

**Verification**:
```
pwsh -Command "flutter analyze lib/shared/widgets/"
```
Expected: No issues found.

---

#### Step 3.10.2: Update shared utils barrel

Check if `lib/shared/utils/utils.dart` exports `snackbar_helper.dart` and remove that export line.

**Verification**:
```
pwsh -Command "flutter analyze lib/shared/"
```
Expected: No issues found.

---

### Sub-phase 3.11: Full Barrel Update + Analyze

**Agent**: `code-fixer-agent`

#### Step 3.11.1: Update main design_system barrel

Replace `lib/core/design_system/design_system.dart` with the new sub-barrel structure:

```dart
// Barrel export for the Field Guide design system.
//
// Usage (single import for all components):
// ```dart
// import 'package:construction_inspector/core/design_system/design_system.dart';
// ```
//
// WHY: Restructured from flat 24-export barrel to atomic sub-directory barrels.
// Consumer imports remain unchanged because this barrel re-exports everything.

// Token layer (Phase 2)
export 'tokens/tokens.dart';

// Atomic layer — smallest building blocks
export 'atoms/atoms.dart';

// Molecule layer — composed atomic elements
export 'molecules/molecules.dart';

// Organism layer — complex composed widgets
export 'organisms/organisms.dart';

// Surface layer — layout scaffolding
export 'surfaces/surfaces.dart';

// Feedback layer — states, errors, notifications
export 'feedback/feedback.dart';
```

**NOTE**: `layout/` and `animation/` sub-barrels are added in Phase 2 (layout) and Phase 5 (animation). If Phase 2 already added them, include:
```dart
// Layout layer (Phase 2 -- MUST include, already created)
export 'layout/layout.dart';

// Animation layer (Phase 2 -- MUST include, already created)
export 'animation/animation.dart';
```

Phase 2 already created both `layout/layout.dart` and `animation/animation.dart`. These exports are NOT optional -- they MUST be present unconditionally.

---

#### Step 3.11.2: Run `dart fix --apply` for import cleanup

```
pwsh -Command "dart fix --apply --code=directives_ordering lib/core/design_system/"
```

This sorts and cleans up import directives in all moved/new files.

---

#### Step 3.11.3: Full analyzer verification

```
pwsh -Command "flutter analyze"
```

Expected: Zero analyzer errors. Warnings from existing code (not introduced by Phase 3) are acceptable.

If analyzer errors appear:
1. Check for missing imports in moved files (relative path depth changed from `../` to `../../`)
2. Check for circular barrel imports (no sub-barrel should import from the main barrel)
3. Check that deleted files are no longer referenced anywhere
4. Check that the `intl` package dependency exists in `pubspec.yaml` for `AppDatePicker` (it already does — used by other features)

---

#### Step 3.11.4: Verify barrel exports cover all files

Run a quick sanity check that all files in each sub-directory are exported:

```
pwsh -Command "flutter analyze lib/core/design_system/design_system.dart"
```

Expected: No issues found. If there are "unused import" warnings, a file was missed from a barrel.

---

#### Step 3.11.5: Update directory-reference.md

**WHY**: FROM SPEC -- documentation updated per phase.
**File**: `.claude/docs/directory-reference.md` (MODIFY) -- update `design_system/` section for new atomic subdirectory structure (atoms/, molecules/, organisms/, surfaces/, feedback/).

---

### Phase 3 Summary

**Files created** (20 new):
- `lib/core/design_system/atoms/app_button.dart`
- `lib/core/design_system/atoms/app_badge.dart`
- `lib/core/design_system/atoms/app_divider.dart`
- `lib/core/design_system/atoms/app_avatar.dart`
- `lib/core/design_system/atoms/app_tooltip.dart`
- `lib/core/design_system/molecules/app_dropdown.dart`
- `lib/core/design_system/molecules/app_date_picker.dart`
- `lib/core/design_system/molecules/app_tab_bar.dart`
- `lib/core/design_system/molecules/app_search_bar.dart`
- `lib/core/design_system/organisms/app_stat_card.dart`
- `lib/core/design_system/organisms/app_action_card.dart`
- `lib/core/design_system/organisms/app_form_section.dart`
- `lib/core/design_system/organisms/app_form_section_nav.dart`
- `lib/core/design_system/organisms/app_form_status_bar.dart`
- `lib/core/design_system/organisms/app_form_field_group.dart`
- `lib/core/design_system/organisms/app_form_summary_tile.dart`
- `lib/core/design_system/organisms/app_form_thumbnail.dart`
- `lib/core/design_system/feedback/app_snackbar.dart`
- `lib/core/design_system/feedback/app_contextual_feedback.dart`
- `lib/core/design_system/feedback/app_banner.dart`

**Files moved** (24 from flat to sub-dirs):
- 6 atoms: `app_text.dart`, `app_icon.dart`, `app_chip.dart`, `app_toggle.dart`, `app_progress_bar.dart`, `app_mini_spinner.dart`
- 4 molecules: `app_text_field.dart`, `app_counter_field.dart`, `app_list_tile.dart`, `app_section_header.dart`
- 4 organisms: `app_glass_card.dart`, `app_section_card.dart`, `app_photo_grid.dart`, `app_info_banner.dart`
- 6 surfaces: `app_scaffold.dart`, `app_bottom_bar.dart`, `app_bottom_sheet.dart`, `app_dialog.dart`, `app_sticky_header.dart`, `app_drag_handle.dart`
- 4 feedback: `app_empty_state.dart`, `app_error_state.dart`, `app_loading_state.dart`, `app_budget_warning_chip.dart`

**Files deleted** (5):
- `lib/shared/widgets/search_bar_field.dart` (migrated to AppSearchBar)
- `lib/shared/widgets/contextual_feedback_overlay.dart` (migrated to AppContextualFeedback)
- `lib/shared/widgets/empty_state_widget.dart` (merged into AppEmptyState)
- `lib/shared/widgets/confirmation_dialog.dart` (merged into AppDialog static methods)
- `lib/shared/utils/snackbar_helper.dart` (migrated to AppSnackbar)

**Files modified** (6):
- `lib/core/design_system/design_system.dart` (main barrel restructured)
- `lib/core/design_system/surfaces/app_dialog.dart` (added confirmation methods)
- `lib/shared/widgets/widgets.dart` (removed migrated exports)
- `lib/features/entries/presentation/controllers/pdf_data_builder.dart` (SnackBarHelper -> AppSnackbar)
- `lib/features/settings/presentation/screens/consent_screen.dart` (SnackBarHelper -> AppSnackbar)
- `lib/features/settings/presentation/screens/legal_document_screen.dart` (SnackBarHelper -> AppSnackbar)

**Barrel files updated** (7):
- `lib/core/design_system/atoms/atoms.dart`
- `lib/core/design_system/molecules/molecules.dart`
- `lib/core/design_system/organisms/organisms.dart`
- `lib/core/design_system/surfaces/surfaces.dart`
- `lib/core/design_system/feedback/feedback.dart`
- `lib/core/design_system/design_system.dart`
- `lib/shared/widgets/widgets.dart`

**NOT deleted in Phase 3** (deferred to Phase 4):
- `lib/shared/widgets/stale_config_warning.dart` (will be recomposed from AppBanner)
- `lib/shared/widgets/version_banner.dart` (will be recomposed from AppBanner)


---


## Phase 4a: UI Decomposition -- Priority Screens 1-6

**IMPORTANT**: This phase assumes Phases 1-3 are complete. Token ThemeExtensions (`FieldGuideSpacing`, `FieldGuideRadii`, `FieldGuideMotion`, `FieldGuideShadows`) are registered on `ThemeData.extensions` and accessible via `.of(context)`. The `AppResponsiveBuilder` layout widget exists in `lib/core/design_system/layout/`. The design system barrel at `lib/core/design_system/design_system.dart` re-exports all tokens, atoms, molecules, organisms, surfaces, feedback, layout, and animation sub-barrels.

**NOTE**: Each sub-phase follows the 11-step decomposition protocol: (1) component discovery, (2) promote shared patterns, (3) extract private widgets, (4) tokenize, (5) sliver-ify, (6) selector-ify, (7) add motion, (8) responsive layout, (9) close issues, (10) update HTTP driver, (11) update logs. Steps are collapsed where not applicable.

---

### Sub-phase 4.1: entry_editor_screen.dart (1,857 lines -> ~300 + 6 widgets)

**Agent**: `code-fixer-agent`
**File**: `lib/features/entries/presentation/screens/entry_editor_screen.dart`

This is the highest line-count file in the codebase (1,857 lines). It already has 5 extracted section widgets (`EntryActivitiesSection`, `EntryContractorsSection`, `EntryFormsSection`, `EntryPhotosSection`, `EntryQuantitiesSection`). The remaining extractable pieces are: the app bar, the entry header, the safety section card, and the main build orchestration. The screen uses 27 `DesignConstants` references.

#### Step 4.1.0: Formalized component discovery gate

**Action**: Before decomposition, grep for private `_*Card`, `_*Tile`, `_*Row`, `_*Badge`, `_*Banner` widget classes in the batch feature dirs and cross-reference against the design system barrel. If a pattern appears in 2+ features, promote it first. Repeats at start of each batch (4a, 4b, 4.12).

#### Step 4.1.1: Component discovery sweep

Read the file and catalog all private `_build*` methods and private classes.

**Action**: Read `lib/features/entries/presentation/screens/entry_editor_screen.dart` in full. Document:

| Symbol | Line | Target |
|--------|------|--------|
| `_buildAppBar()` | 957 | Extract to `entry_editor_app_bar.dart` |
| `_buildEntryHeader(DailyEntry)` | 1059 | Extract to `entry_header_card.dart` |
| `_buildSafetySection(DailyEntry, DailyEntryProvider)` | 1600 | Keep inline (thin wrapper around `_EditableSafetyCard`) |
| `_EditableSafetyCard` | 1635 | Extract to `editable_safety_card.dart` |
| `_EditableSafetyCardState` | 1655 | Moves with `_EditableSafetyCard` |
| `_buildSections()` | 1395 | Stays in main screen (orchestration logic) |

**Verification**: No verification needed -- this is a read-only discovery step.

#### Step 4.1.2: Extract `_EditableSafetyCard` to standalone widget

**Action**: Create `lib/features/entries/presentation/widgets/editable_safety_card.dart`

```dart
// WHY: Extracted from entry_editor_screen.dart:1635-1857 to reduce main screen
// line count. This is a self-contained stateful widget with its own editing state.
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
import 'package:construction_inspector/features/entries/presentation/controllers/entry_editing_controller.dart';

// NOTE: Made public by removing underscore prefix. Constructor and fields are
// identical to the private version at entry_editor_screen.dart:1642-1649.
class EditableSafetyCard extends StatefulWidget {
  final DailyEntry entry;
  final EntryEditingController controller;
  final Future<void> Function() onSave;
  final bool isViewer;
  final Future<void> Function()? onCopyFromLast;

  const EditableSafetyCard({
    super.key,
    required this.entry,
    required this.controller,
    required this.onSave,
    this.isViewer = false,
    this.onCopyFromLast,
  });

  @override
  State<EditableSafetyCard> createState() => _EditableSafetyCardState();
}

// NOTE: State class body is copied verbatim from entry_editor_screen.dart:1655-1857.
// Only the class name prefix changes from _ to public. All DesignConstants refs
// are tokenized in step 4.1.5.
class _EditableSafetyCardState extends State<EditableSafetyCard> {
  // ... (copy lines 1656-end from entry_editor_screen.dart verbatim,
  //      replacing _EditableSafetyCard -> EditableSafetyCard in type refs)
}
```

**Action**: In `entry_editor_screen.dart`, delete lines 1627-end (the `_EditableSafetyCard` and its state). Add import:
```dart
import 'package:construction_inspector/features/entries/presentation/widgets/editable_safety_card.dart';
```

**Action**: In `_buildSafetySection` (line 1600-1624), replace `_EditableSafetyCard` with `EditableSafetyCard`.

**Action**: Add export to `lib/features/entries/presentation/widgets/widgets.dart`:
```dart
export 'editable_safety_card.dart';
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: No errors related to `EditableSafetyCard` or missing imports.

#### Step 4.1.3: Extract `_buildEntryHeader` to standalone widget

**Action**: Create `lib/features/entries/presentation/widgets/entry_header_card.dart`

```dart
// WHY: Extracted from entry_editor_screen.dart:1059-1309. This 250-line method
// builds the entire entry header card (project name, location, weather, date,
// temperature, copy-from-last button). Standalone extraction enables reuse and
// reduces the main screen to orchestration-only.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
// NOTE: field_guide_colors + design_constants re-exported via design_system barrel above
import 'package:construction_inspector/shared/shared.dart';
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';

/// Displays the entry header card with project name, location, weather, date,
/// and temperature fields. Supports tap-to-edit for location and weather.
class EntryHeaderCard extends StatelessWidget {
  final DailyEntry entry;
  final String? projectName;
  final String? projectNumber;
  final String? locationName;
  final bool isViewer;
  // FROM SPEC: Callbacks for inline editing -- delegated from parent screen state
  final VoidCallback? onEditLocation;
  final VoidCallback? onEditWeather;
  final VoidCallback? onEditDate;
  final Key? sectionKey;

  const EntryHeaderCard({
    super.key,
    required this.entry,
    this.projectName,
    this.projectNumber,
    this.locationName,
    this.isViewer = false,
    this.onEditLocation,
    this.onEditWeather,
    this.onEditDate,
    this.sectionKey,
  });

  @override
  Widget build(BuildContext context) {
    // NOTE: Body is the verbatim content of _buildEntryHeader from
    // entry_editor_screen.dart:1059-1309, with `context.read<AuthProvider>()`
    // calls replaced by the `isViewer` parameter passed from parent.
    // All DesignConstants refs tokenized in step 4.1.5.
    final cs = Theme.of(context).colorScheme;
    final fg = FieldGuideColors.of(context);
    final tt = Theme.of(context).textTheme;
    final dateStr = DateFormat('EEEE, MMMM d, y').format(entry.date);

    return Card(
      key: sectionKey,
      child: Padding(
        padding: const EdgeInsets.all(DesignConstants.space4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ... (copy lines 1075-1306 from entry_editor_screen.dart,
            //      replacing direct context.read<AuthProvider>() with isViewer,
            //      replacing _showLocationEditDialog with onEditLocation,
            //      replacing _showWeatherDialog with onEditWeather,
            //      replacing _showDatePicker with onEditDate)
          ],
        ),
      ),
    );
  }
}
```

**Action**: In `entry_editor_screen.dart`, replace `_buildEntryHeader(entry)` call at line 1425 with:
```dart
EntryHeaderCard(
  entry: entry,
  projectName: _projectName,
  projectNumber: _projectNumber,
  locationName: _locationName,
  isViewer: !context.read<AuthProvider>().canEditEntry(
    createdByUserId: entry.createdByUserId,
  ),
  onEditLocation: _showLocationEditDialog,
  onEditWeather: () => _showWeatherDialog(entry),
  onEditDate: () => _showDatePicker(entry),
  sectionKey: _sectionKeys['basics'],
),
```

Delete the `_buildEntryHeader` method (lines 1059-1309).

**Action**: Add import and export to barrel:
```dart
// In widgets.dart:
export 'entry_header_card.dart';
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.1.4: Extract `_buildAppBar` to standalone widget

**Action**: Create `lib/features/entries/presentation/widgets/entry_editor_app_bar.dart`

```dart
// WHY: Extracted from entry_editor_screen.dart:957-1053. The app bar has
// conditional logic (PDF export spinner, popup menu, draft title) that is
// self-contained and does not need parent state access beyond callbacks.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/shared/shared.dart';
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';

class EntryEditorAppBar extends StatelessWidget implements PreferredSizeWidget {
  final DailyEntry? entry;
  final bool isDraftEntry;
  final bool isGeneratingPdf;
  final bool canWrite;
  // FROM SPEC: Callbacks delegated from parent screen state
  final VoidCallback onExportPdf;
  final VoidCallback? onExportForms;
  final VoidCallback? onDelete;
  final VoidCallback onBack;

  const EntryEditorAppBar({
    super.key,
    required this.entry,
    required this.isDraftEntry,
    required this.isGeneratingPdf,
    required this.canWrite,
    required this.onExportPdf,
    this.onExportForms,
    this.onDelete,
    required this.onBack,
  });

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final title = (isDraftEntry || entry == null)
        ? 'New Entry'
        : DateFormat('MMM d, y').format(entry!.date);

    return AppBar(
      title: Text(title, key: TestingKeys.reportScreenTitle),
      leading: BackButton(onPressed: onBack),
      actions: [
        // NOTE: Copy lines 978-1051 from entry_editor_screen.dart verbatim,
        // replacing _isGeneratingPdf -> isGeneratingPdf,
        // replacing _exportPdf -> onExportPdf,
        // replacing _confirmDelete -> onDelete,
        // replacing _entry -> entry
      ],
    );
  }
}
```

**Action**: In `entry_editor_screen.dart`, replace `_buildAppBar()` usage at line 1360 with:
```dart
appBar: EntryEditorAppBar(
  entry: _entry,
  isDraftEntry: _isDraftEntry,
  isGeneratingPdf: _isGeneratingPdf,
  canWrite: context.read<AuthProvider>().canEditEntry(
    createdByUserId: _entry?.createdByUserId,
  ),
  onExportPdf: _exportPdf,
  onExportForms: _entry != null ? () => _exportAllForms() : null,
  onDelete: () => _confirmDelete(),
  onBack: () => safeGoBack(context, fallbackRouteName: 'entries'),
),
```

Delete the `_buildAppBar` method (lines 957-1053).

**Action**: Add export to barrel.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.1.5: Tokenize all DesignConstants references

**Action**: In all files touched in this sub-phase (`entry_editor_screen.dart`, `entry_header_card.dart`, `editable_safety_card.dart`, `entry_editor_app_bar.dart`), replace every `DesignConstants` reference with the corresponding token accessor:

| Old Reference | New Reference |
|---------------|---------------|
| `DesignConstants.space1` | `FieldGuideSpacing.of(context).xs` |
| `DesignConstants.space2` | `FieldGuideSpacing.of(context).sm` |
| `DesignConstants.space3` | `DesignConstants.space3` |
| `DesignConstants.space4` | `FieldGuideSpacing.of(context).md` |
| `DesignConstants.space6` | `FieldGuideSpacing.of(context).lg` |
| `DesignConstants.space8` | `FieldGuideSpacing.of(context).xl` |
| `DesignConstants.radiusSmall` | `FieldGuideRadii.of(context).sm` |
| `DesignConstants.radiusMedium` | `FieldGuideRadii.of(context).md` |

**IMPORTANT**: `space3` (12.0), `space5` (20.0), `space10` (40.0), `space16` (64.0) are NOT mapped to tokens -- they remain as `DesignConstants.space3` etc. per the ground truth. Only the canonical sizes (4, 8, 16, 24, 32, 48) map to tokens.

**NOTE**: Where `DesignConstants.space*` is used inside a `const` constructor (e.g., `const EdgeInsets.all(DesignConstants.space4)`), the `const` must be removed because `FieldGuideSpacing.of(context)` is not const. Replace:
```dart
// Before:
const EdgeInsets.all(DesignConstants.space4)
// After:
EdgeInsets.all(FieldGuideSpacing.of(context).md)
```

**IMPORTANT**: For `SizedBox` spacers that use tokens, convert from const to non-const:
```dart
// Before:
const SizedBox(height: DesignConstants.space4)
// After (still using DesignConstants since SizedBox is often const):
// WHY: Keep SizedBox const where possible for performance. Only convert to
// token accessor when the widget is not in a const context.
SizedBox(height: FieldGuideSpacing.of(context).md)
```

**Action**: Also replace hardcoded `EdgeInsets.fromLTRB(16, 16, 16, 32)` at line 1370 with token-based padding:
```dart
EdgeInsets.fromLTRB(
  FieldGuideSpacing.of(context).md,
  FieldGuideSpacing.of(context).md,
  FieldGuideSpacing.of(context).md,
  FieldGuideSpacing.of(context).xl,
)
```

**Action**: Replace hardcoded `const SizedBox(height: 16)` spacers in `_buildSections()` (lines 1426, 1438, 1454, 1461, 1480, 1494, 1505) and `const SizedBox(height: 8)` (line 1422, 1513) with token-based:
```dart
SizedBox(height: FieldGuideSpacing.of(context).md), // was 16
SizedBox(height: FieldGuideSpacing.of(context).sm), // was 8
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors. No remaining `DesignConstants.space[1248]` or `DesignConstants.radius*` references in the touched files (check with grep).

#### Step 4.1.6: Responsive layout with AppResponsiveBuilder

**Action**: In `entry_editor_screen.dart`, wrap the `build` method body to support tablet/desktop layout. The current screen already uses `CustomScrollView` with slivers -- no sliver migration needed.

In the `build` method, after the `PopScope` and `AppScaffold`, wrap the body content:

```dart
// FROM SPEC: Canonical layout -- Single column (phone) -> Body + detail pane (tablet/desktop)
// WHY: On tablet, the entry header stays pinned in the left pane while
// sections scroll in the right pane. This uses the list-detail canonical layout.
body: AppResponsiveBuilder(
  compact: (context) => Column(
    children: [
      Expanded(
        child: CustomScrollView(
          key: TestingKeys.entryEditorScroll,
          controller: _scrollController,
          physics: const ClampingScrollPhysics(),
          slivers: [
            SliverPadding(
              padding: EdgeInsets.fromLTRB(
                FieldGuideSpacing.of(context).md,
                FieldGuideSpacing.of(context).md,
                FieldGuideSpacing.of(context).md,
                FieldGuideSpacing.of(context).xl,
              ),
              sliver: SliverList(
                delegate: SliverChildListDelegate(_buildSections()),
              ),
            ),
          ],
        ),
      ),
    ],
  ),
  // WHY: AppAdaptiveLayout (from P2) handles two-pane split, divider, and flex ratios.
  // No magic widths needed -- AppAdaptiveLayout manages proportional sizing internally.
  medium: (context) => AppAdaptiveLayout(
    body: SingleChildScrollView(
          padding: EdgeInsets.all(FieldGuideSpacing.of(context).md),
          child: EntryHeaderCard(
            entry: _entry!,
            projectName: _projectName,
            projectNumber: _projectNumber,
            locationName: _locationName,
            isViewer: !context.read<AuthProvider>().canEditEntry(
              createdByUserId: _entry?.createdByUserId,
            ),
            onEditLocation: _showLocationEditDialog,
            onEditWeather: () => _showWeatherDialog(_entry!),
            onEditDate: () => _showDatePicker(_entry!),
            sectionKey: _sectionKeys['basics'],
          ),
        ),
      ),
    ),
    detail: CustomScrollView(
      key: TestingKeys.entryEditorScroll,
          controller: _scrollController,
          physics: const ClampingScrollPhysics(),
          slivers: [
            SliverPadding(
              padding: EdgeInsets.all(FieldGuideSpacing.of(context).md),
              sliver: SliverList(
                delegate: SliverChildListDelegate(
                  _buildSectionsWithoutHeader(),
                ),
              ),
            ),
          ],
        ),
      ],
    ),
  ),
),
```

**Action**: Add `_buildSectionsWithoutHeader()` method that returns `_buildSections()` minus the `EntryHeaderCard` and the first `SizedBox` spacer.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.1.7: Add Logger calls to extracted widgets

**Action**: In `entry_header_card.dart`, `editable_safety_card.dart`, and `entry_editor_app_bar.dart`, add Logger import and log at key interaction points:

```dart
import 'package:construction_inspector/core/logging/logger.dart';

// In EntryHeaderCard.build:
// WHY: Component-level logging for decomposed widgets
// (No build-time logging needed -- parent logs lifecycle events)

// In EditableSafetyCard._startEditing:
Logger.ui('[EditableSafetyCard] Started editing safety section');

// In EditableSafetyCard._done:
Logger.ui('[EditableSafetyCard] Finished editing safety section');
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

---

### Sub-phase 4.2: project_setup_screen.dart (1,436 lines -> ~300 + 5 widgets)

**Agent**: `code-fixer-agent`
**File**: `lib/features/projects/presentation/screens/project_setup_screen.dart`

This screen has 5 tabs (Details, Locations, Contractors, Pay Items, Assignments). Tabs 1-2 are already extracted (`ProjectDetailsForm`, `AssignmentsStep`). The remaining `_build*Tab` methods for Locations, Contractors, and Pay Items are 120-570 lines each and contain nested `Consumer` widgets. The file has 30 `DesignConstants` references and fixes GitHub issue #165 (RenderFlex overflow).

#### Step 4.2.1: Component discovery sweep

**Action**: Read `lib/features/projects/presentation/screens/project_setup_screen.dart` in full. Catalog:

| Symbol | Line | Target |
|--------|------|--------|
| `_buildDetailsTab()` | 409 | Keep -- thin wrapper around `ProjectDetailsForm` (already extracted) |
| `_buildLocationsTab()` | 466 | Extract to `project_locations_tab.dart` |
| `_buildContractorsTab()` | 590 | Extract to `project_contractors_tab.dart` |
| `_buildBidItemsTab()` | 768 | Extract to `project_bid_items_tab.dart` |
| `_InlineContractorCreationCard` | 1356 | Move to `project_contractors_tab.dart` (private helper for that tab) |

**Verification**: Read-only step.

#### Step 4.2.2: Extract `_buildLocationsTab` to standalone widget

**Action**: Create `lib/features/projects/presentation/widgets/project_locations_tab.dart`

```dart
// WHY: Extracted from project_setup_screen.dart:466-584. Self-contained tab
// content with Consumer<LocationProvider> and location CRUD operations.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
// NOTE: field_guide_colors + design_constants re-exported via design_system barrel above
import 'package:construction_inspector/shared/shared.dart';
import 'package:construction_inspector/features/locations/presentation/providers/location_provider.dart';
import 'package:construction_inspector/features/locations/data/models/location.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import '../widgets/widgets.dart';

class ProjectLocationsTab extends StatelessWidget {
  final String projectId;

  const ProjectLocationsTab({super.key, required this.projectId});

  @override
  Widget build(BuildContext context) {
    final canManageProjects = context.watch<AuthProvider>().canManageProjects;
    // NOTE: Body is verbatim from project_setup_screen.dart:469-583,
    // with _projectId replaced by projectId parameter,
    // and _showAddLocationDialog / _confirmDeleteLocation replaced by
    // local methods or callbacks.
    return Consumer<LocationProvider>(
      builder: (context, locationProvider, _) {
        // ... (copy lines 470-583)
      },
    );
  }

  // NOTE: Location dialog and delete confirmation methods moved here
  // from project_setup_screen.dart
}
```

**Action**: In `project_setup_screen.dart`, replace `_buildLocationsTab()` body with:
```dart
Widget _buildLocationsTab() {
  return ProjectLocationsTab(projectId: _projectId!);
}
```

Or inline the widget directly in the `TabBarView`. Delete the `_buildLocationsTab` method body (lines 466-584) and the `_confirmDeleteLocation` and `_showAddLocationDialog` methods if they only serve this tab.

**Action**: Add export to `lib/features/projects/presentation/widgets/widgets.dart`:
```dart
export 'project_locations_tab.dart';
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

#### Step 4.2.3: Extract `_buildContractorsTab` to standalone widget

**Action**: Create `lib/features/projects/presentation/widgets/project_contractors_tab.dart`

```dart
// WHY: Extracted from project_setup_screen.dart:590-766. Contains Consumer3
// with ContractorProvider, EquipmentProvider, PersonnelTypeProvider. Also
// includes the _InlineContractorCreationCard (lines 1356+) as a private widget.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
// NOTE: field_guide_colors + design_constants re-exported via design_system barrel above
import 'package:construction_inspector/shared/shared.dart';
import 'package:construction_inspector/features/contractors/presentation/providers/contractor_provider.dart';
import 'package:construction_inspector/features/contractors/presentation/providers/equipment_provider.dart';
import 'package:construction_inspector/features/contractors/presentation/providers/personnel_type_provider.dart';
import 'package:construction_inspector/features/contractors/data/models/contractor.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/entries/presentation/widgets/contractor_editor_widget.dart';

class ProjectContractorsTab extends StatefulWidget {
  final String projectId;

  const ProjectContractorsTab({super.key, required this.projectId});

  @override
  State<ProjectContractorsTab> createState() => _ProjectContractorsTabState();
}

class _ProjectContractorsTabState extends State<ProjectContractorsTab> {
  String? _editingContractorId;
  bool _isCreatingContractor = false;
  final _contractorNameController = TextEditingController();
  ContractorType _editingContractorType = ContractorType.prime;

  @override
  void dispose() {
    _contractorNameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // NOTE: Body from project_setup_screen.dart:593-766 verbatim,
    // with state fields moved to this widget's State class.
    // _InlineContractorCreationCard (line 1356) is also moved here.
    return Consumer3<ContractorProvider, EquipmentProvider, PersonnelTypeProvider>(
      builder: (context, contractorProvider, equipmentProvider, personnelTypeProvider, _) {
        // ... (copy lines 598-766)
      },
    );
  }
}

// NOTE: Moved from project_setup_screen.dart:1356
class _InlineContractorCreationCard extends StatelessWidget {
  // ... (copy lines 1356-end of class)
}
```

**Action**: In `project_setup_screen.dart`:
- Remove contractor-specific state fields (`_editingContractorId`, `_isCreatingContractor`, `_contractorNameController`, `_editingContractorType`) from `_ProjectSetupScreenState`
- Replace `_buildContractorsTab()` with `ProjectContractorsTab(projectId: _projectId!)`
- Delete `_InlineContractorCreationCard` class (lines 1356+)
- Delete contractor CRUD methods that only served this tab

**Action**: Add export to widgets barrel.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

#### Step 4.2.4: Extract `_buildBidItemsTab` to standalone widget

**Action**: Create `lib/features/projects/presentation/widgets/project_bid_items_tab.dart`

```dart
// WHY: Extracted from project_setup_screen.dart:768-1354. This is the largest
// tab (~586 lines) with Consumer<BidItemProvider>, inline editing, CSV import,
// and complex list management.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
// NOTE: field_guide_colors + design_constants re-exported via design_system barrel above
import 'package:construction_inspector/shared/shared.dart';
import 'package:construction_inspector/features/quantities/presentation/providers/bid_item_provider.dart';
import 'package:construction_inspector/features/quantities/data/models/bid_item.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/pdf/presentation/helpers/mp_import_helper.dart';
import 'package:construction_inspector/features/pdf/presentation/helpers/pdf_import_helper.dart';
import '../widgets/widgets.dart';

class ProjectBidItemsTab extends StatefulWidget {
  final String projectId;

  const ProjectBidItemsTab({super.key, required this.projectId});

  @override
  State<ProjectBidItemsTab> createState() => _ProjectBidItemsTabState();
}

class _ProjectBidItemsTabState extends State<ProjectBidItemsTab> {
  // NOTE: Bid item editing state moved from _ProjectSetupScreenState.
  // Copy all bid-item-related state fields and methods.

  @override
  Widget build(BuildContext context) {
    return Consumer<BidItemProvider>(
      builder: (context, bidItemProvider, _) {
        // ... (copy lines 771-1354)
      },
    );
  }
}
```

**Action**: In `project_setup_screen.dart`, replace bid-item tab content, remove bid-item state fields and methods.

**Action**: Add export to widgets barrel.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

#### Step 4.2.5: Tokenize all DesignConstants references

**Action**: Across all files touched in this sub-phase, apply the same tokenization mapping as step 4.1.5:

| Old | New |
|-----|-----|
| `DesignConstants.space1` | `FieldGuideSpacing.of(context).xs` |
| `DesignConstants.space2` | `FieldGuideSpacing.of(context).sm` |
| `DesignConstants.space4` | `FieldGuideSpacing.of(context).md` |
| `DesignConstants.space6` | `FieldGuideSpacing.of(context).lg` |
| `DesignConstants.space8` | `FieldGuideSpacing.of(context).xl` |
| `DesignConstants.radiusSmall` | `FieldGuideRadii.of(context).sm` |
| `DesignConstants.radiusMedium` | `FieldGuideRadii.of(context).md` |
| `DesignConstants.radiusLarge` | `FieldGuideRadii.of(context).lg` |

**IMPORTANT**: `DesignConstants.space3` stays as-is (no token mapping for 12.0).

Also tokenize hardcoded literal numbers:
- `const EdgeInsets.all(16)` -> `EdgeInsets.all(FieldGuideSpacing.of(context).md)`
- `const SizedBox(height: 8)` -> `SizedBox(height: FieldGuideSpacing.of(context).sm)`
- `BorderRadius.circular(12)` -> `BorderRadius.circular(FieldGuideRadii.of(context).md)`

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

#### Step 4.2.6: Fix GitHub issue #165 -- RenderFlex overflow

**Action**: The RenderFlex overflow in project_setup_screen occurs when tab content exceeds available height. The fix is to ensure each extracted tab widget uses `Expanded` + `ListView`/`SingleChildScrollView` properly and does not have unbounded `Column` children inside `Flexible` parents.

In each extracted tab widget, verify the root structure follows:
```dart
// WHY: #165 -- RenderFlex overflow fix. Each tab must have a bounded height
// via Expanded wrapping, and internal content must scroll.
return Column(
  children: [
    // Fixed header content (if any)
    Expanded(
      child: ListView.builder(
        // Scrollable content
      ),
    ),
    // Fixed footer content (if any, e.g., Add button)
  ],
);
```

**IMPORTANT**: Check `_buildDetailsTab` too -- the `ProjectDetailsForm` is inside `Expanded` (line 437), which is correct. But if the `UserAttributionText` padding above it grows, it could overflow. Wrap in a `Column` with `Expanded` for the form.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors. The RenderFlex issue is a runtime bug verified by visual testing.

#### Step 4.2.7: Consumer -> Selector conversions

**Action**: In `project_locations_tab.dart`, the `Consumer<LocationProvider>` rebuilds the entire tab on any location change. Convert to `Selector` where possible:

```dart
// Before (in project_locations_tab.dart):
Consumer<LocationProvider>(
  builder: (context, locationProvider, _) {
    final locations = locationProvider.locations;
    // ...
  },
)

// After:
// WHY: Selector rebuilds only when the locations list identity changes,
// not on every notifyListeners() from LocationProvider.
Selector<LocationProvider, List<Location>>(
  selector: (_, p) => p.locations,
  builder: (context, locations, _) {
    // ...
  },
)
```

**Action**: In `project_contractors_tab.dart`, the `Consumer3` is harder to convert. Keep it as-is initially -- the three-provider Consumer is already the minimal set needed. Add a `// TODO: Evaluate Selector3 for surgical rebuilds` comment.

**Action**: In `project_bid_items_tab.dart`, convert `Consumer<BidItemProvider>`:
```dart
Selector<BidItemProvider, List<BidItem>>(
  selector: (_, p) => p.bidItems,
  builder: (context, bidItems, _) {
    // ...
  },
)
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

#### Step 4.2.8: Responsive layout with AppResponsiveBuilder

**Action**: In `project_setup_screen.dart`, the wizard uses a `TabController` with 5 tabs. On tablet/desktop, convert to a side navigation + content layout:

```dart
// FROM SPEC: Canonical layout -- Single column wizard (phone) ->
// Left section nav + content (tablet)
body: AppResponsiveBuilder(
  compact: (context) => Column(
    children: [
      // Existing TabBarView with 5 tabs
      Expanded(
        child: TabBarView(
          controller: _tabController,
          children: [
            _buildDetailsTab(),
            ProjectLocationsTab(projectId: _projectId!),
            ProjectContractorsTab(projectId: _projectId!),
            ProjectBidItemsTab(projectId: _projectId!),
            const AssignmentsStep(),
          ],
        ),
      ),
    ],
  ),
  medium: (context) => Row(
    children: [
      // WHY: NavigationRail-style section nav for tablet layout.
      // NOTE: Unique layout -- AppResponsiveBuilder is correct here (not AppAdaptiveLayout)
      // because NavigationRail is not a standard body/detail pattern.
      SizedBox(
        width: DesignConstants.navigationRailWidth, // WHY: named constant, not magic number
        child: NavigationRail(
          selectedIndex: _tabController.index,
          onDestinationSelected: (index) {
            _tabController.animateTo(index);
          },
          extended: true,
          destinations: const [
            NavigationRailDestination(
              icon: Icon(Icons.info_outline),
              label: Text('Details'),
            ),
            NavigationRailDestination(
              icon: Icon(Icons.location_on_outlined),
              label: Text('Locations'),
            ),
            NavigationRailDestination(
              icon: Icon(Icons.group_outlined),
              label: Text('Contractors'),
            ),
            NavigationRailDestination(
              icon: Icon(Icons.receipt_long_outlined),
              label: Text('Pay Items'),
            ),
            NavigationRailDestination(
              icon: Icon(Icons.assignment_ind_outlined),
              label: Text('Assignments'),
            ),
          ],
        ),
      ),
      const AppDivider.vertical(), // WHY: no_raw_divider lint — use design system divider
      Expanded(
        child: AnimatedSwitcher(
          duration: FieldGuideMotion.of(context).fast,
          child: _buildCurrentTabContent(),
        ),
      ),
    ],
  ),
),
```

**Action**: Add `_buildCurrentTabContent()` that switches on `_tabController.index` and returns the corresponding tab widget.

**NOTE**: The `AppBar.bottom: ProjectTabBar(...)` should be hidden in the medium+ layout since the NavigationRail replaces it. Wrap with `AppResponsiveBuilder` or conditionally null the `bottom` property based on `MediaQuery.sizeOf(context).width`.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

---

### Sub-phase 4.3: home_screen.dart (1,270 lines -> ~300 + 4 widgets)

**Agent**: `code-fixer-agent`
**File**: `lib/features/entries/presentation/screens/home_screen.dart`

This screen has the second-highest `DesignConstants` reference count (47). It contains a calendar section, day cell animation, project header, empty states, and entry list. It has 3 `Consumer` widgets and 2 private widget classes (`_AnimatedDayCell`, `_ModernEntryCard`).

#### Step 4.3.1: Component discovery sweep

| Symbol | Line | Target |
|--------|------|--------|
| `_buildNoProjectsState()` | 324 | Extract to `home_no_projects_state.dart` |
| `_buildSelectProjectState()` | 362 | Merge into `home_no_projects_state.dart` as variant |
| `_buildProjectHeader(Project)` | 400 | Extract to `home_project_header.dart` |
| `_buildCalendarSection(DailyEntryProvider)` | 442 | Extract to `home_calendar_section.dart` |
| `_buildCalendarFormatToggle(CalendarFormatProvider)` | 464 | Move into `home_calendar_section.dart` |
| `_buildFormatButton(...)` | 503 | Move into `home_calendar_section.dart` |
| `_buildCalendar(...)` | 541 | Move into `home_calendar_section.dart` |
| `_buildSelectedDayContent(...)` | 716 | Extract to `home_day_content.dart` |
| `_buildEmptyState()` | 786 | Move into `home_day_content.dart` |
| `_buildEntryList(...)` | 845 | Move into `home_day_content.dart` |
| `_AnimatedDayCell` | 1017 | Extract to `animated_day_cell.dart` |
| `_ModernEntryCard` | 1130 | Extract to `home_entry_card.dart` |

#### Step 4.3.2: Extract `_AnimatedDayCell` and `_ModernEntryCard`

**Action**: Create `lib/features/entries/presentation/widgets/animated_day_cell.dart`

```dart
// WHY: Extracted from home_screen.dart:1017-1128. Self-contained animated
// widget for calendar day cells with entry indicators.
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
// NOTE: field_guide_colors re-exported via design_system barrel above

// NOTE: Made public by removing underscore prefix.
class AnimatedDayCell extends StatefulWidget {
  final DateTime date;
  final bool isSelected;
  final bool isToday;
  final bool hasEntries;
  final int entryCount;

  const AnimatedDayCell({
    super.key,
    required this.date,
    required this.isSelected,
    required this.isToday,
    required this.hasEntries,
    required this.entryCount,
  });

  @override
  State<AnimatedDayCell> createState() => _AnimatedDayCellState();
}

// NOTE: State body copied from home_screen.dart:1036-1128
class _AnimatedDayCellState extends State<AnimatedDayCell>
    with SingleTickerProviderStateMixin {
  // ... (copy verbatim, replacing _AnimatedDayCell -> AnimatedDayCell)
}
```

**Action**: Create `lib/features/entries/presentation/widgets/home_entry_card.dart`

```dart
// WHY: Extracted from home_screen.dart:1130-1270. Entry card for the calendar
// day view list. Contains tap-to-navigate, status badge, location display.
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';

// NOTE: Made public, renamed from _ModernEntryCard to HomeEntryCard.
class HomeEntryCard extends StatelessWidget {
  final DailyEntry entry;
  final String? locationName;
  final VoidCallback? onTap;

  const HomeEntryCard({
    super.key,
    required this.entry,
    this.locationName,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    // ... (copy from home_screen.dart:1130-end, making public)
  }
}
```

**Action**: Add exports to `lib/features/entries/presentation/widgets/widgets.dart`:
```dart
export 'animated_day_cell.dart';
export 'home_entry_card.dart';
```

**Action**: In `home_screen.dart`, delete both private classes and import the new files. Update all references from `_AnimatedDayCell` to `AnimatedDayCell` and `_ModernEntryCard` to `HomeEntryCard`.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.3.3: Extract calendar section

**Action**: Create `lib/features/entries/presentation/widgets/home_calendar_section.dart`

```dart
// WHY: Extracted from home_screen.dart:442-714. Contains calendar widget,
// format toggle, and all calendar-related _build methods.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:table_calendar/table_calendar.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
// NOTE: field_guide_colors + design_constants re-exported via design_system barrel above
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
import 'package:construction_inspector/features/entries/presentation/providers/daily_entry_provider.dart';
import 'package:construction_inspector/features/entries/presentation/providers/calendar_format_provider.dart';
import 'package:construction_inspector/features/entries/presentation/widgets/animated_day_cell.dart';

class HomeCalendarSection extends StatelessWidget {
  final DateTime focusedDay;
  final DateTime? selectedDay;
  final List<DailyEntry> entries;
  final ValueChanged<DateTime> onDaySelected;
  final ValueChanged<DateTime> onPageChanged;

  const HomeCalendarSection({
    super.key,
    required this.focusedDay,
    this.selectedDay,
    required this.entries,
    required this.onDaySelected,
    required this.onPageChanged,
  });

  @override
  Widget build(BuildContext context) {
    // NOTE: Contains _buildCalendarSection, _buildCalendarFormatToggle,
    // _buildFormatButton, and _buildCalendar logic.
    // Moved from home_screen.dart:442-714.
  }
}
```

**Action**: Add export to widgets barrel.

**Action**: In `home_screen.dart`, replace the calendar `Flexible` section in `build` (lines 281-288) with:
```dart
Flexible(
  fit: FlexFit.loose,
  child: HomeCalendarSection(
    focusedDay: _focusedDay,
    selectedDay: _selectedDay,
    entries: context.read<DailyEntryProvider>().entries,
    onDaySelected: (day) {
      setState(() {
        _selectedDay = day;
        _focusedDay = day;
      });
      context.read<DailyEntryProvider>().setSelectedDate(day);
    },
    onPageChanged: (focusedDay) {
      setState(() => _focusedDay = focusedDay);
    },
  ),
),
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.3.4: Extract selected day content

**Action**: Create `lib/features/entries/presentation/widgets/home_day_content.dart`

```dart
// WHY: Extracted from home_screen.dart:716-1015. Contains _buildSelectedDayContent,
// _buildEmptyState, and _buildEntryList. Self-contained widget that shows
// entries for the selected day with create FAB.
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
// NOTE: field_guide_colors + design_constants re-exported via design_system barrel above
import 'package:construction_inspector/shared/shared.dart';
import 'package:construction_inspector/features/entries/data/models/daily_entry.dart';
import 'package:construction_inspector/features/entries/presentation/widgets/home_entry_card.dart';
import 'package:construction_inspector/features/locations/data/models/location.dart';

class HomeDayContent extends StatelessWidget {
  final DateTime? selectedDay;
  final List<DailyEntry> entries;
  final List<Location> locations;
  final String? projectId;
  final VoidCallback? onCreateEntry;
  // FROM SPEC: Callbacks for inline editing (tap-to-edit on entries)
  final void Function(DailyEntry entry)? onTapEntry;

  const HomeDayContent({
    super.key,
    this.selectedDay,
    required this.entries,
    required this.locations,
    this.projectId,
    this.onCreateEntry,
    this.onTapEntry,
  });

  @override
  Widget build(BuildContext context) {
    // NOTE: Body from home_screen.dart:716-1015
  }
}
```

**Action**: Add export. Update `home_screen.dart` to use `HomeDayContent` in place of `_buildSelectedDayContent`.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.3.5: Tokenize all 47 DesignConstants references

**Action**: Apply the standard tokenization mapping across all files in this sub-phase. The 47 references include `space1` through `space8` and `radius*` variants.

Same mapping table as step 4.1.5. Also tokenize hardcoded literals:
- `const EdgeInsets.all(32)` -> `EdgeInsets.all(FieldGuideSpacing.of(context).xl)`
- `BorderRadius.circular(8)` -> `BorderRadius.circular(FieldGuideRadii.of(context).sm)`
- Hardcoded `SizedBox(height: N)` -> token equivalent

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.3.6: Consumer -> Selector conversions

**Action**: In `home_screen.dart` main build method:

```dart
// Before (line 254):
Consumer<ProjectProvider>(
  builder: (context, projectProvider, _) {
    // Uses: selectedProject, isInitializing, isRestoringProject, projects
  },
)

// After:
// WHY: Selector rebuilds only when the project selection/loading state changes,
// not on every ProjectProvider notification (e.g., search query changes).
Selector<ProjectProvider, ({Project? selected, bool isLoading, bool isEmpty})>(
  selector: (_, p) => (
    selected: p.selectedProject,
    isLoading: p.isInitializing || p.isRestoringProject,
    isEmpty: p.projects.isEmpty,
  ),
  builder: (context, state, _) {
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (state.isEmpty) return _buildNoProjectsState();
    if (state.selected == null) return _buildSelectProjectState();
    // ...
  },
)
```

**Action**: Convert inner `Consumer<DailyEntryProvider>` (line 283) and `Consumer2<DailyEntryProvider, LocationProvider>` (line 294) similarly:

```dart
// WHY: The calendar section only needs the entries list, not all provider fields.
Selector<DailyEntryProvider, List<DailyEntry>>(
  selector: (_, p) => p.entries,
  builder: (context, entries, _) {
    return HomeCalendarSection(
      // ...
      entries: entries,
    );
  },
)
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.3.7: Responsive layout with AppResponsiveBuilder

**Action**: In `home_screen.dart`, wrap the body to support tablet layout:

```dart
// FROM SPEC: Canonical layout -- Single column calendar + preview (phone) ->
// Calendar/list + preview pane (tablet)
body: AppResponsiveBuilder(
  compact: (context) => _buildCompactLayout(projectState),
  // WHY: AppAdaptiveLayout (from P2) handles two-pane split, divider, and flex ratios.
  medium: (context) => AppAdaptiveLayout(
    body: Column(
      children: [
        _buildProjectHeader(selectedProject),
        Flexible(
          fit: FlexFit.loose,
          child: HomeCalendarSection(/* ... */),
        ),
        const AppDivider(), // WHY: no_raw_divider lint
        Expanded(child: HomeDayContent(/* ... */)),
      ],
    ),
    detail: _selectedEntryId != null
        ? _buildEntryPreview(_selectedEntryId!)
        : Center(
            child: AppEmptyState(
              icon: Icons.article_outlined,
              title: 'Select an entry',
              subtitle: 'Choose an entry from the list to preview',
            ),
          ),
  ),
),
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.3.8: Add motion to home_screen.dart

**Action**: Wire animation components created in P2 to home_screen:

1. **AppStaggeredList**: Wrap the entry list items in `HomeDayContent` with `AppStaggeredList` so entries animate in with staggered fade+slide when the selected day changes.
2. **AppTapFeedback**: Wrap each `HomeEntryCard` instance with `AppTapFeedback` for scale feedback on tap.
3. **AppAnimatedEntrance**: Wrap the `HomeCalendarSection` and `HomeDayContent` top-level widgets with `AppAnimatedEntrance` so they fade+slide in on initial screen mount.

```dart
// In home_day_content.dart, wrap the entry list builder:
AppStaggeredList(
  // WHY: Staggered entrance for day's entries — 50ms delay per item (max 8)
  // FROM SPEC: "List item appear — All list screens — AppStaggeredList"
  children: entries.map((entry) => AppTapFeedback(
    // WHY: Scale feedback on card tap — FROM SPEC: "Card tap — AppTapFeedback"
    child: HomeEntryCard(entry: entry, onTap: () => _onEntryTap(entry)),
  )).toList(),
),

// In home_screen.dart compact layout, wrap key content:
AppAnimatedEntrance(
  // WHY: Fade+slide entrance for main content area on screen mount
  child: _buildCompactLayout(projectState),
),
```

**Verification**: Visual -- entries should stagger in when switching days; cards should scale on tap.

---

### Sub-phase 4.4: mdot_hub_screen.dart (1,198 lines -> ~300 + 5 screens)

**Agent**: `code-fixer-agent`
**File**: `lib/features/forms/presentation/screens/mdot_hub_screen.dart`

This file contains 6 classes: `MdotHubScreen` (main), `_PdfPreviewScreen`, `FormFillScreen`, `QuickTestEntryScreen`, `ProctorEntryScreen`, `WeightsEntryScreen`. The main hub is already partially decomposed with extracted widgets (`hub_header_content`, `hub_quick_test_content`, `hub_proctor_content`). The task is to split the 5 secondary screen classes into separate files and decompose the main hub further.

#### Step 4.4.1: Extract 5 screen classes to separate files

**Action**: Create `lib/features/forms/presentation/screens/form_fill_screen.dart`:

```dart
// WHY: Extracted from mdot_hub_screen.dart:1153-1163. FormFillScreen delegates
// to MdotHubScreen -- separate file for clean routing imports.
import 'package:flutter/material.dart';
import 'package:construction_inspector/features/forms/presentation/screens/mdot_hub_screen.dart';

class FormFillScreen extends StatelessWidget {
  final String responseId;

  const FormFillScreen({super.key, required this.responseId});

  @override
  // WHY: FormFillScreen is the full-form entry point. The MdotHubScreen
  // already implements the complete fill experience.
  Widget build(BuildContext context) => MdotHubScreen(responseId: responseId);
}
```

**Action**: Create `lib/features/forms/presentation/screens/quick_test_entry_screen.dart`:

```dart
// WHY: Extracted from mdot_hub_screen.dart:1165-1175.
import 'package:flutter/material.dart';
import 'package:construction_inspector/features/forms/presentation/screens/mdot_hub_screen.dart';

class QuickTestEntryScreen extends StatelessWidget {
  final String responseId;

  const QuickTestEntryScreen({super.key, required this.responseId});

  @override
  // WHY: Quick Test Entry jumps directly to the test section.
  Widget build(BuildContext context) =>
      MdotHubScreen(responseId: responseId, initialSection: 2);
}
```

**Action**: Create `lib/features/forms/presentation/screens/proctor_entry_screen.dart`:

```dart
// WHY: Extracted from mdot_hub_screen.dart:1177-1186.
import 'package:flutter/material.dart';
import 'package:construction_inspector/features/forms/presentation/screens/mdot_hub_screen.dart';

class ProctorEntryScreen extends StatelessWidget {
  final String responseId;

  const ProctorEntryScreen({super.key, required this.responseId});

  @override
  // WHY: Proctor Entry jumps directly to the proctor section.
  Widget build(BuildContext context) =>
      MdotHubScreen(responseId: responseId, initialSection: 1);
}
```

**Action**: Create `lib/features/forms/presentation/screens/weights_entry_screen.dart`:

```dart
// WHY: Extracted from mdot_hub_screen.dart:1188-1198.
import 'package:flutter/material.dart';
import 'package:construction_inspector/features/forms/presentation/screens/mdot_hub_screen.dart';

class WeightsEntryScreen extends StatelessWidget {
  final String responseId;

  const WeightsEntryScreen({super.key, required this.responseId});

  @override
  // WHY: Weights entry is part of the proctor workflow (section 1).
  Widget build(BuildContext context) =>
      MdotHubScreen(responseId: responseId, initialSection: 1);
}
```

**Action**: Create `lib/features/forms/presentation/screens/form_pdf_preview_screen.dart`:

```dart
// WHY: Extracted from mdot_hub_screen.dart:1134-1151. The PDF preview was a
// private class (_PdfPreviewScreen) -- now public for direct routing.
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:printing/printing.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';

class FormPdfPreviewScreen extends StatelessWidget {
  final Uint8List bytes;

  const FormPdfPreviewScreen({super.key, required this.bytes});

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      appBar: AppBar(title: const Text('PDF Preview')),
      body: PdfPreview(
        canChangeOrientation: false,
        canChangePageFormat: false,
        canDebug: false,
        build: (_) => bytes,
      ),
    );
  }
}
```

**Action**: In `mdot_hub_screen.dart`, delete all 5 classes after `_MdotHubScreenState` (lines 1133-1199). Update any internal navigation that pushed `_PdfPreviewScreen` to use `FormPdfPreviewScreen` instead.

**Action**: Update any router files that import these screens from `mdot_hub_screen.dart` to import from their new files. Search for imports:
```
grep -r "mdot_hub_screen" lib/core/router/
```
Update import paths accordingly.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/forms/ lib/core/router/"
```
Expected: Zero analyzer errors.

#### Step 4.4.2: Tokenize DesignConstants references

**Action**: The mdot_hub_screen has only 6 `DesignConstants` references. Apply standard tokenization mapping. Also update existing hub content widgets (`hub_header_content.dart`, `hub_proctor_content.dart`, `hub_quick_test_content.dart`) to use P3 form editor organisms: `AppFormSection` for collapsible sections, `AppFormSectionNav` for navigation, `AppFormFieldGroup` for grouping related fields.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/forms/"
```
Expected: Zero analyzer errors.

#### Step 4.4.3: Create spec-mandated NEW widgets for MdotHub

**Action**: Create the 3 NEW widgets specified in the MdotHubScreen decomposition target (FROM SPEC Section 3):

1. **`lib/features/forms/presentation/widgets/hub_section_navigator.dart`**: Section navigator with completion status. Renders sidebar (tablet) or pills (phone). Uses `AppFormSectionNav` organism from P3.

2. **`lib/features/forms/presentation/widgets/hub_status_summary.dart`**: Form-level completion status summary widget. Uses `AppFormStatusBar` organism from P3.

3. **`lib/features/forms/presentation/widgets/hub_field_groups/`**: Directory for domain-specific field clusters extracted from `hub_proctor_content.dart` (e.g., proctor_fields.dart, weight_fields.dart). Uses `AppFormFieldGroup` organism from P3.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/forms/"
```
Expected: Zero analyzer errors.

#### Step 4.4.4: Responsive layout with AppResponsiveBuilder

**Action**: In `mdot_hub_screen.dart`, the hub uses accordion sections with `_expanded` state tracking which section is open. On tablet, convert to a two-pane layout:

```dart
// FROM SPEC: Canonical layout -- Single column accordion (phone) ->
// Two-pane section nav left + content right (tablet)
body: AppResponsiveBuilder(
  compact: (context) => _buildCompactLayout(),
  // WHY: AppAdaptiveLayout (from P2) handles two-pane split, divider, and flex ratios.
  medium: (context) => AppAdaptiveLayout(
    // WHY: Section navigator in left pane for tablet layout.
    // Uses StatusPillBar items rendered vertically.
    body: _buildSectionNav(),
    detail: _buildExpandedSectionContent(),
  ),
),
```

**Action**: Add `_buildSectionNav()` method that renders navigation items for Header, Proctor, Test sections. Add `_buildExpandedSectionContent()` that renders the currently selected section's content without the accordion wrapper.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/forms/"
```
Expected: Zero analyzer errors.

---

### Sub-phase 4.5: project_list_screen.dart (1,196 lines -> ~300 + 4 widgets)

**Agent**: `code-fixer-agent`
**File**: `lib/features/projects/presentation/screens/project_list_screen.dart`

This screen has no `DesignConstants` imports but has 26 hardcoded spacing literals. It uses `Consumer<ProjectProvider>`, `Consumer<ProjectImportRunner>`, and `Consumer<ProjectSyncHealthProvider>`. The `_buildProjectCard` method is 227 lines (816-1043) and should be extracted.

#### Step 4.5.1: Component discovery sweep

| Symbol | Line | Target |
|--------|------|--------|
| `_buildTabBody(...)` | 401 | Keep in main screen (orchestration) |
| `_buildMyProjectsTab(...)` | 432 | Extract to `project_my_projects_tab.dart` |
| `_buildCompanyTab(...)` | 475 | Extract to `project_company_tab.dart` |
| `_buildArchivedTab(...)` | 550 | Extract to `project_archived_tab.dart` |
| `_buildSyncStatusIcon(...)` | 775 | Move into project card widget |
| `_buildProjectCard(...)` | 816 | Extract to `project_card.dart` (227 lines) |
| `_buildSearchField()` | 1064 | Keep (thin wrapper around `SearchBarField`) |
| `_buildErrorState(...)` | 1076 | Keep (small) |
| `_buildLocationBadge(...)` | 1118 | Move into project card |
| `_buildLifecycleBadge(...)` | 1133 | Move into project card |
| `_buildBadge(...)` | 1163 | Move into project card |

#### Step 4.5.2: Extract `_buildProjectCard` to standalone widget

**Action**: Create `lib/features/projects/presentation/widgets/project_card.dart`

```dart
// WHY: Extracted from project_list_screen.dart:816-1043. The largest method
// in the file (227 lines). Self-contained card with sync status, badges,
// download CTA, and action buttons.
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/shared/shared.dart';
import 'package:construction_inspector/features/projects/data/models/merged_project_entry.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_sync_health_provider.dart';

class ProjectCard extends StatelessWidget {
  final MergedProjectEntry entry;
  final ProjectSyncHealthProvider healthProvider;
  final bool canManageProjects;
  final bool canEditFieldData;
  final bool canDownload;
  final DateTime now;
  final VoidCallback? onTap;
  final VoidCallback? onRemove;
  final VoidCallback? onDownload;
  final VoidCallback? onEdit;
  final VoidCallback? onArchiveToggle;

  const ProjectCard({
    super.key,
    required this.entry,
    required this.healthProvider,
    required this.canManageProjects,
    required this.canEditFieldData,
    this.canDownload = true,
    required this.now,
    this.onTap,
    this.onRemove,
    this.onDownload,
    this.onEdit,
    this.onArchiveToggle,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;
    final fg = FieldGuideColors.of(context);
    final project = entry.project;
    final isRemoteOnly = entry.isRemoteOnly;

    return Card(
      key: TestingKeys.projectCard(project.id),
      // NOTE: Body from project_list_screen.dart:843-1043
      // with _handleSelectProject -> onTap callback,
      // _showDownloadConfirmation -> onDownload callback,
      // _buildSyncStatusIcon -> _buildSyncStatusIcon local method,
      // _buildLocationBadge/_buildLifecycleBadge/_buildBadge -> local methods
    );
  }

  // NOTE: Helper methods _buildSyncStatusIcon, _buildLocationBadge,
  // _buildLifecycleBadge, _buildBadge moved from project_list_screen.dart
}
```

**Action**: In `project_list_screen.dart`, replace all `_buildProjectCard(...)` calls with `ProjectCard(...)`, passing callbacks for `onTap`, `onRemove`, `onDownload`, `onEdit`, `onArchiveToggle`.

Delete methods: `_buildProjectCard`, `_buildSyncStatusIcon`, `_buildLocationBadge`, `_buildLifecycleBadge`, `_buildBadge`.

**Action**: Add export to widgets barrel.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

#### Step 4.5.3: Extract tab content methods

**Action**: Create `lib/features/projects/presentation/widgets/project_tab_content.dart` containing the three tab builders. Each tab is structurally similar (filter entries, build list of `ProjectCard`s).

```dart
// WHY: Extracted from project_list_screen.dart. Three tab bodies (~120 lines each)
// are structurally identical: filter entries, build RefreshIndicator + ListView
// of ProjectCard widgets.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/projects/data/models/merged_project_entry.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_provider.dart';
import 'package:construction_inspector/features/projects/presentation/providers/project_sync_health_provider.dart';
import 'package:construction_inspector/features/projects/presentation/widgets/project_card.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

class ProjectTabContent extends StatelessWidget {
  final List<MergedProjectEntry> entries;
  final Future<void> Function() onRefresh;
  final void Function(String id) onSelectProject;
  final void Function(MergedProjectEntry entry) onDownload;
  final void Function(String projectId) onRemoveFromDevice;
  final void Function(MergedProjectEntry entry) onRemoteDelete;
  final Widget? emptyState;

  const ProjectTabContent({
    super.key,
    required this.entries,
    required this.onRefresh,
    required this.onSelectProject,
    required this.onDownload,
    required this.onRemoveFromDevice,
    required this.onRemoteDelete,
    this.emptyState,
  });

  @override
  Widget build(BuildContext context) {
    // NOTE: Shared tab structure from the three _build*Tab methods.
    // Each tab uses the same list-building pattern with ProjectCard.
    // WHY: Use context.select instead of context.watch for surgical rebuilds
    final healthStatuses = context.select<ProjectSyncHealthProvider, Map<String, dynamic>>((p) => p.statuses);
    final canManageProjects = context.select<AuthProvider, bool>((p) => p.canManageProjects);
    final canEditFieldData = context.select<AuthProvider, bool>((p) => p.canEditFieldData);
    // NOTE: DateTime.now() should be passed from parent widget to avoid unnecessary rebuilds

    if (entries.isEmpty) {
      return emptyState ?? const Center(child: Text('No projects'));
    }

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView.builder(
        padding: EdgeInsets.all(FieldGuideSpacing.of(context).md),
        itemCount: entries.length,
        itemBuilder: (context, index) {
          final entry = entries[index];
          return ProjectCard(
            entry: entry,
            healthProvider: healthProvider,
            canManageProjects: authProvider.canManageProjects,
            canEditFieldData: authProvider.canEditFieldData,
            now: now,
            onTap: entry.isRemoteOnly
                ? () => onDownload(entry)
                : () => onSelectProject(entry.project.id),
            onRemove: () => onRemoveFromDevice(entry.project.id),
            onDownload: () => onDownload(entry),
          );
        },
      ),
    );
  }
}
```

**Action**: In `project_list_screen.dart`, replace `_buildMyProjectsTab`, `_buildCompanyTab`, `_buildArchivedTab` with `ProjectTabContent` instances, each passing the appropriate filtered entries list.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

#### Step 4.5.4: Tokenize hardcoded spacing literals

**Action**: In `project_card.dart` and `project_list_screen.dart`, replace all hardcoded spacing:

| Hardcoded | Token |
|-----------|-------|
| `EdgeInsets.all(16)` | `EdgeInsets.all(FieldGuideSpacing.of(context).md)` |
| `EdgeInsets.only(bottom: 12)` | `EdgeInsets.only(bottom: FieldGuideSpacing.of(context).sm) /* NOTE: round 12->sm(8), no token arithmetic */` |
| `SizedBox(width: 10)` | `SizedBox(width: FieldGuideSpacing.of(context).sm) /* NOTE: round 10->sm(8), no token arithmetic */` |
| `SizedBox(width: 6)` | `SizedBox(width: FieldGuideSpacing.of(context).xs) /* NOTE: round 6->xs(4), no token arithmetic */` |
| `SizedBox(height: 12)` | `SizedBox(height: DesignConstants.space3)` |
| `SizedBox(height: 8)` | `SizedBox(height: FieldGuideSpacing.of(context).sm)` |
| `SizedBox(width: 16)` | `SizedBox(width: FieldGuideSpacing.of(context).md)` |
| `SizedBox(width: 8)` | `SizedBox(width: FieldGuideSpacing.of(context).sm)` |
| `BorderRadius.circular(12)` | `BorderRadius.circular(FieldGuideRadii.of(context).md)` |

**NOTE**: For spacings that do not map cleanly to tokens (6, 10, 12), use `DesignConstants.space3` for 12 and leave small gaps (6, 10) as hardcoded for now -- they are visual polish values, not semantic tokens.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

#### Step 4.5.5: Consumer -> Selector conversions

**Action**: In `project_list_screen.dart`, the outer `Consumer<ProjectProvider>` (line 339) rebuilds the entire screen on any project change. Convert:

```dart
// Before:
Consumer<ProjectProvider>(
  builder: (context, provider, _) {
    return AppScaffold(/* ... */);
  },
)

// After:
// WHY: The AppScaffold only needs tab counts and the filtered project lists,
// not every provider field. Use Selector for surgical rebuilds.
Selector<ProjectProvider, ({int myCount, int companyCount, int archivedCount, bool isLoading, String? error})>(
  selector: (_, p) => (
    myCount: p.myProjectsCount,
    companyCount: p.companyProjectsCount,
    archivedCount: p.archivedProjectsCount,
    isLoading: p.isLoading,
    error: p.error,
  ),
  builder: (context, state, _) {
    return AppScaffold(
      appBar: AppBar(
        // ...
        bottom: ProjectTabBar(
          controller: _tabController,
          myProjectsCount: state.myCount,
          companyCount: state.companyCount,
          archivedCount: state.archivedCount,
        ),
      ),
      // ...
    );
  },
)
```

**Action**: Convert `Consumer<ProjectImportRunner>` (line 373):
```dart
Selector<ProjectImportRunner, bool>(
  selector: (_, r) => r.isImporting,
  builder: (context, isImporting, _) {
    if (!isImporting) return const SizedBox.shrink();
    return ProjectImportBanner(runner: context.read<ProjectImportRunner>());
  },
)
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

#### Step 4.5.6: Sliver migration

**Action**: In `project_list_screen.dart`, the current layout uses `Column` with `Expanded(child: TabBarView(...))`. Inside each tab, `ListView.builder` is used. Convert the tab content to use `CustomScrollView` with slivers:

```dart
// FROM SPEC: Sliver migration -- Mixed Column/ListView -> CustomScrollView
// with sliver sections
// NOTE: This is done inside ProjectTabContent.build:
return RefreshIndicator(
  onRefresh: onRefresh,
  child: CustomScrollView(
    slivers: [
      SliverPadding(
        padding: EdgeInsets.all(FieldGuideSpacing.of(context).md),
        sliver: SliverList(
          delegate: SliverChildBuilderDelegate(
            (context, index) {
              final entry = entries[index];
              return ProjectCard(/* ... */);
            },
            childCount: entries.length,
          ),
        ),
      ),
    ],
  ),
);
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

#### Step 4.5.7: Responsive layout with AppResponsiveBuilder

**Action**: In `project_list_screen.dart`, the canonical layout for a list screen on tablet is list-detail:

```dart
// FROM SPEC: Canonical layout -- Single column list (phone) -> List-detail (tablet)
body: AppResponsiveBuilder(
  compact: (context) => Column(
    children: [
      Consumer<ProjectImportRunner>(/* ... */),
      const DeletionNotificationBanner(),
      Expanded(child: _buildTabBody(provider, authProvider)),
    ],
  ),
  // WHY: AppAdaptiveLayout (from P2) handles two-pane split, divider, and flex ratios.
  medium: (context) => AppAdaptiveLayout(
    body: Column(
      children: [
        Consumer<ProjectImportRunner>(/* ... */),
        const DeletionNotificationBanner(),
        Expanded(child: _buildTabBody(provider, authProvider)),
      ],
    ),
    detail: _selectedProjectId != null
        ? _buildProjectDetail(_selectedProjectId!)
        : Center(
            child: AppEmptyState(
              icon: Icons.folder_outlined,
              title: 'Select a project',
              subtitle: 'Choose a project to see details',
            ),
          ),
  ),
),
```

**NOTE**: This requires adding `_selectedProjectId` state and updating `_handleSelectProject` to set it on tablet instead of navigating away.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

#### Step 4.5.8: Add motion to project_list_screen.dart

**Action**: Wire animation components created in P2 to project_list_screen:

1. **AppStaggeredList**: Wrap project list items with `AppStaggeredList` so `ProjectCard` widgets stagger in on tab switch or initial load.
2. **AppTapFeedback**: Wrap each `ProjectCard` with `AppTapFeedback` for scale feedback on tap.

```dart
// In _buildMyProjectsTab / _buildCompanyTab / _buildArchivedTab list builders:
AppStaggeredList(
  // WHY: Staggered entrance for project cards — FROM SPEC: "List item appear — All list screens"
  children: projects.map((entry) => AppTapFeedback(
    // WHY: Scale feedback on project card tap — FROM SPEC: "Card tap — AppTapFeedback"
    child: ProjectCard(entry: entry, /* ... callbacks ... */),
  )).toList(),
),
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/projects/"
```
Expected: Zero analyzer errors.

---

### Sub-phase 4.6: contractor_editor_widget.dart (1,099 lines -> ~300 + 3 widgets + 2 dialogs)

**Agent**: `code-fixer-agent`
**File**: `lib/features/entries/presentation/widgets/contractor_editor_widget.dart`

This file has 37 `DesignConstants` references and contains the main `ContractorEditorWidget` plus two dialog classes (`_PersonnelTypeManagerDialog`, `_EquipmentManagerDialog`). It also has many `_build*` methods for the card internals.

#### Step 4.6.1: Component discovery sweep

| Symbol | Line | Target |
|--------|------|--------|
| `ContractorEditorWidget` | 12 | Keep as main widget, reduce to orchestration |
| `_buildHeader(...)` | 141 | Extract to `contractor_card_header.dart` |
| `_buildPersonnelHeader(...)` | 228 | Move into `contractor_personnel_section.dart` |
| `_buildSectionLabel(...)` | 249 | Keep (utility, 12 lines) |
| `_buildPersonnelSection(...)` | 261 | Extract to `contractor_personnel_section.dart` |
| `_buildSetupPersonnelTypes(...)` | 318 | Move into `contractor_personnel_section.dart` |
| `_buildEquipmentHeader(...)` | 350 | Move into `contractor_equipment_section.dart` |
| `_buildEquipmentSection(...)` | 368 | Extract to `contractor_equipment_section.dart` |
| `_buildTypeBadge(...)` | 440 | Move into header widget |
| `_buildPersonnelCounterCard(...)` | 462 | Extract to `personnel_counter_card.dart` |
| `_buildCounterButton(...)` | 531 | Move into `personnel_counter_card.dart` |
| `_buildHeaderActionButton(...)` | 560 | Move into header widget |
| `_buildHeaderMenu(...)` | 628 | Move into header widget |
| `_PersonnelTypeManagerDialog` | 664 | Extract to `personnel_type_manager_dialog.dart` |
| `_EquipmentManagerDialog` | 824 | Extract to `equipment_manager_dialog.dart` |

#### Step 4.6.2: Extract dialog classes to separate files

**Action**: Create `lib/features/entries/presentation/widgets/personnel_type_manager_dialog.dart`

```dart
// WHY: Extracted from contractor_editor_widget.dart:664-822. Self-contained
// StatefulWidget dialog for managing personnel types (add/delete).
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
// NOTE: field_guide_colors + design_constants re-exported via design_system barrel above
import 'package:construction_inspector/features/contractors/data/models/models.dart';

class PersonnelTypeManagerDialog extends StatefulWidget {
  final List<PersonnelType> types;
  final Future<PersonnelType?> Function(String name) onAdd;
  final Future<bool> Function(String typeId) onDelete;

  const PersonnelTypeManagerDialog({
    super.key,
    required this.types,
    required this.onAdd,
    required this.onDelete,
  });

  @override
  State<PersonnelTypeManagerDialog> createState() =>
      _PersonnelTypeManagerDialogState();
}

class _PersonnelTypeManagerDialogState
    extends State<PersonnelTypeManagerDialog> {
  // NOTE: Body from contractor_editor_widget.dart:680-822
}
```

**Action**: Create `lib/features/entries/presentation/widgets/equipment_manager_dialog.dart`

```dart
// WHY: Extracted from contractor_editor_widget.dart:824-1099. Self-contained
// StatefulWidget dialog for managing equipment (add/delete).
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
// NOTE: field_guide_colors + design_constants re-exported via design_system barrel above
import 'package:construction_inspector/features/contractors/data/models/models.dart';

class EquipmentManagerDialog extends StatefulWidget {
  final List<Equipment> equipment;
  final Future<Equipment?> Function(String name, String? description) onAdd;
  final Future<bool> Function(String equipmentId) onDelete;

  const EquipmentManagerDialog({
    super.key,
    required this.equipment,
    required this.onAdd,
    required this.onDelete,
  });

  @override
  State<EquipmentManagerDialog> createState() => _EquipmentManagerDialogState();
}

class _EquipmentManagerDialogState extends State<EquipmentManagerDialog> {
  // NOTE: Body from contractor_editor_widget.dart:841-end
}
```

**Action**: In `contractor_editor_widget.dart`, delete both dialog classes (lines 664-end). Import the new files. Update any `showDialog` calls that reference the old private classes to use the new public names.

**Action**: Add exports to widgets barrel.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.6.3: Extract `_buildPersonnelCounterCard` to standalone widget

**Action**: Create `lib/features/entries/presentation/widgets/personnel_counter_card.dart`

```dart
// WHY: Extracted from contractor_editor_widget.dart:462-529. The personnel
// counter is a self-contained unit with increment/decrement buttons and count
// display. It's the core interaction element in the contractor editor.
// IMPORTANT: Keep the stepper controls -- see feedback_keep_contractor_controls.md
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
// NOTE: field_guide_colors + design_constants re-exported via design_system barrel above

class PersonnelCounterCard extends StatelessWidget {
  final String typeName;
  final int count;
  final bool isEditing;
  final ValueChanged<int>? onCountChanged;

  const PersonnelCounterCard({
    super.key,
    required this.typeName,
    required this.count,
    this.isEditing = false,
    this.onCountChanged,
  });

  @override
  Widget build(BuildContext context) {
    // NOTE: Body from contractor_editor_widget.dart:462-529
    // including _buildCounterButton (531-558) as a local method
  }
}
```

**Action**: Update `contractor_editor_widget.dart` to use `PersonnelCounterCard`.

**Action**: Add export to widgets barrel.

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.6.4: Tokenize all 37 DesignConstants references

**Action**: Apply standard tokenization mapping across all files in this sub-phase. Same mapping table as step 4.1.5.

Key references in `contractor_editor_widget.dart`:
- `DesignConstants.radiusMedium` at line 98 -> `FieldGuideRadii.of(context).md`
- `DesignConstants.space3` at line 100 -> stays as `DesignConstants.space3` (no token for 12.0)
- All `DesignConstants.space2`, `space4` etc. -> token equivalents

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

#### Step 4.6.5: Add Logger calls

**Action**: In each extracted widget, add Logger import and log at interaction points:

```dart
// In PersonnelTypeManagerDialog, on add:
Logger.ui('[PersonnelTypeManagerDialog] Added type: $name');

// In EquipmentManagerDialog, on add:
Logger.ui('[EquipmentManagerDialog] Added equipment: $name');

// In PersonnelCounterCard, on count change:
// NOTE: No logging needed -- parent handles business logic logging
```

**Verification**:
```
pwsh -Command "flutter analyze lib/features/entries/"
```
Expected: Zero analyzer errors.

---

### Sub-phase 4.7: Final verification and GitHub issue closure

**Agent**: `general-purpose`

#### Step 4.7.1: Full analysis pass

**Action**: Run analyzer across all modified feature directories:
```
pwsh -Command "flutter analyze lib/features/entries/ lib/features/projects/ lib/features/forms/"
```
Expected: Zero errors, zero warnings from touched files.

#### Step 4.7.2: Verify line count reduction

**Action**: Check that the main screen files are now under target:

| File | Before | Target | Check |
|------|--------|--------|-------|
| `entry_editor_screen.dart` | 1,857 | ~300 | Grep for line count |
| `project_setup_screen.dart` | 1,436 | ~300 | Grep for line count |
| `home_screen.dart` | 1,270 | ~300 | Grep for line count |
| `mdot_hub_screen.dart` | 1,198 | ~300 | Grep for line count |
| `project_list_screen.dart` | 1,196 | ~300 | Grep for line count |
| `contractor_editor_widget.dart` | 1,099 | ~300 | Grep for line count |

**Verification**: Read each file and confirm line count. If any file exceeds 400 lines, identify remaining `_build*` methods that can be extracted.

#### Step 4.7.3: Verify no broken imports

**Action**: Run full project analysis:
```
pwsh -Command "flutter analyze"
```
Expected: No new errors introduced by this phase. Pre-existing warnings are acceptable.

#### Step 4.7.4: Close GitHub issue #165

**Action**: Verify that the RenderFlex overflow fix in sub-phase 4.2.6 addresses issue #165. The fix ensures all tab content in `project_setup_screen.dart` uses proper `Expanded` + scrollable patterns. Mark issue as resolved in the PR description:

```
Fixes #165 -- RenderFlex overflow in project setup screen resolved by decomposing
tab content into standalone widgets with proper Expanded + ListView/ScrollView bounds.
```


---


## Phase 4b: UI Decomposition -- Priority Screens 7-11 + Additional Screens/Widgets + Remaining Issues

**Prerequisite**: Phase 4a complete (screens 1-6 decomposed, tokenized, sliver-migrated). All new design system components from P2-P3 are available. Token extensions (`FieldGuideSpacing`, `FieldGuideRadii`, `FieldGuideMotion`, `FieldGuideShadows`) are registered on `ThemeData.extensions` and accessible via `.of(context)`.

**Component discovery gate** (FROM SPEC: "This gate runs at the start of every implementation batch"):
Before starting any P4b sub-phase, grep for private `_*Card`, `_*Tile`, `_*Row`, `_*Badge`, `_*Banner` in P4b feature dirs (`todos/`, `calculator/`, `dashboard/`, `quantities/`, `forms/`). Cross-reference against design system barrel. If a pattern appears in 2+ features, promote it first.

**notifyListeners guard convention** (FROM SPEC Section 4): When performing the Selector-ify step in each sub-phase, also audit the corresponding provider for `notifyListeners()` calls. Add `if (value == _value) return;` guards before all `notifyListeners()` calls where the setter receives a value that may be unchanged.

**HTTP driver convention** (protocol step 10): For each sub-phase, if any TestingKey is renamed during extraction, update the corresponding HTTP driver endpoint mapping. If no keys are renamed, note "No TestingKey changes" explicitly.

**Conventions for all sub-phases below**:
- Every `DesignConstants.space*` reference becomes `FieldGuideSpacing.of(context).*` (e.g., `space2` -> `.sm`, `space4` -> `.md`, `space6` -> `.lg`, `space8` -> `.xl`)
- Every `DesignConstants.radius*` reference becomes `FieldGuideRadii.of(context).*`
- Every `DesignConstants.animation*` reference becomes `FieldGuideMotion.of(context).*`
- Every `DesignConstants.elevation*` reference becomes `FieldGuideShadows.of(context).*`
- Every raw `ElevatedButton`/`TextButton`/`OutlinedButton`/`IconButton` becomes `AppButton.*` variant
- Every raw `Divider` becomes `AppDivider`
- Every raw `EdgeInsets.*(N)` with numeric literal becomes token-based spacing
- Every raw `BorderRadius.circular(N)` with numeric literal becomes token-based radius
- Every `Consumer<T>` that only reads 1-2 fields becomes `Selector<T, FieldType>`
- Each sub-phase ends with `flutter analyze` verification

---

### Sub-phase 4.8: todos_screen.dart (891 lines -> ~300 + 3 extracted widgets)

**File**: `lib/features/todos/presentation/screens/todos_screen.dart`
**DesignConstants refs**: 25
**Current structure**: `_TodosScreenState` (main, lines 34-505), `_TodoCard` (lines 508-613), `_DueDateChip` (lines 615-677), `_TodoDialogBody` (lines 678-891)
**Extraction plan**: Move `_TodoCard` -> `todo_card.dart`, `_DueDateChip` -> `todo_due_date_chip.dart`, `_TodoDialogBody` -> `todo_dialog_body.dart`

**Agent**: `code-fixer-agent`

#### Step 4.8.1: Extract TodoCard widget

Create `lib/features/todos/presentation/widgets/todo_card.dart` by extracting `_TodoCard` (lines 508-613) from `todos_screen.dart`. Make class public, tokenize all spacing/radius references.

```dart
// lib/features/todos/presentation/widgets/todo_card.dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/todos/data/models/todo_item.dart';
import 'package:construction_inspector/shared/shared.dart';
import 'todo_due_date_chip.dart';

// FROM SPEC: Extract private widgets from oversized screens into standalone files
// WHY: Decomposition target is <300 lines per file
class TodoCard extends StatelessWidget {
  final TodoItem todo;
  final VoidCallback onToggle;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const TodoCard({
    super.key,
    required this.todo,
    required this.onToggle,
    required this.onTap,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final spacing = FieldGuideSpacing.of(context);
    final radii = FieldGuideRadii.of(context);

    return Card(
      margin: EdgeInsets.symmetric(
        horizontal: spacing.sm, // WHY: was DesignConstants.space2 (8.0)
        vertical: spacing.xs, // WHY: was DesignConstants.space1 (4.0)
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(radii.md), // WHY: was DesignConstants.radiusMedium (12.0)
      ),
      // NOTE: Remaining build logic copied from _TodoCard.build, lines 527-613
      // Replace all DesignConstants.space* with spacing.* equivalents
      // Replace all DesignConstants.radius* with radii.* equivalents
      // Replace raw TextButton with AppButton.text
      // Replace raw IconButton with AppButton.icon
      child: InkWell(
        borderRadius: BorderRadius.circular(radii.md),
        onTap: onTap,
        child: Padding(
          padding: EdgeInsets.all(spacing.md),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // NOTE: Checkbox + content + actions structure preserved from original
              // Full implementation copies body from lines 534-612
              // replacing every hardcoded constant with token reference
              Checkbox(
                value: todo.isCompleted,
                onChanged: (_) => onToggle(),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    AppText.titleSmall(
                      todo.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: todo.isCompleted
                          ? const TextStyle(decoration: TextDecoration.lineThrough)
                          : null,
                    ),
                    if (todo.description != null && todo.description!.isNotEmpty) ...[
                      SizedBox(height: spacing.xs),
                      AppText.bodySmall(
                        todo.description!,
                        color: cs.onSurfaceVariant,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    if (todo.dueDate != null) ...[
                      SizedBox(height: spacing.sm),
                      TodoDueDateChip(dueDate: todo.dueDate!, isCompleted: todo.isCompleted),
                    ],
                  ],
                ),
              ),
              AppButton.icon(
                icon: Icons.delete_outline,
                onPressed: onDelete,
                // WHY: was raw IconButton
              ),
            ],
          ),
        ),
      ),
    );
  }
}
```

#### Step 4.8.2: Extract TodoDueDateChip widget

Create `lib/features/todos/presentation/widgets/todo_due_date_chip.dart` by extracting `_DueDateChip` (lines 615-677). Make public, tokenize.

```dart
// lib/features/todos/presentation/widgets/todo_due_date_chip.dart
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';

// FROM SPEC: Extract private widgets to standalone files
class TodoDueDateChip extends StatelessWidget {
  final DateTime dueDate;
  final bool isCompleted;

  const TodoDueDateChip({
    super.key,
    required this.dueDate,
    required this.isCompleted,
  });

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    final radii = FieldGuideRadii.of(context);
    final cs = Theme.of(context).colorScheme;
    final now = DateTime.now();
    final isOverdue = dueDate.isBefore(now) && !isCompleted;
    final isDueToday = dueDate.year == now.year &&
        dueDate.month == now.month &&
        dueDate.day == now.day;

    final Color chipColor;
    if (isOverdue) {
      chipColor = cs.error;
    } else if (isDueToday) {
      chipColor = FieldGuideColors.of(context).statusWarning;
    } else {
      chipColor = cs.onSurfaceVariant;
    }

    // NOTE: Full chip rendering logic from lines 621-677 with token replacements
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: spacing.sm, // WHY: was DesignConstants.space2
        vertical: spacing.xs,   // WHY: was DesignConstants.space1
      ),
      decoration: BoxDecoration(
        color: chipColor.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(radii.sm), // WHY: was DesignConstants.radiusSmall
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.calendar_today, size: 14, color: chipColor),
          SizedBox(width: spacing.xs),
          AppText.labelSmall(
            DateFormat('MMM d').format(dueDate),
            color: chipColor,
          ),
        ],
      ),
    );
  }
}
```

#### Step 4.8.3: Extract TodoDialogBody widget

Create `lib/features/todos/presentation/widgets/todo_dialog_body.dart` by extracting `_TodoDialogBody` (lines 678-891). Make public, tokenize.

```dart
// lib/features/todos/presentation/widgets/todo_dialog_body.dart
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/todos/data/models/todo_item.dart';

// FROM SPEC: Extract dialog body for reuse and line count reduction
class TodoDialogBody extends StatefulWidget {
  final TodoItem? existingTodo;
  final TextEditingController titleController;
  final TextEditingController descriptionController;
  final ValueChanged<DateTime?> onDueDateChanged;
  final ValueChanged<TodoPriority> onPriorityChanged;
  final DateTime? initialDueDate;
  final TodoPriority initialPriority;

  const TodoDialogBody({
    super.key,
    this.existingTodo,
    required this.titleController,
    required this.descriptionController,
    required this.onDueDateChanged,
    required this.onPriorityChanged,
    this.initialDueDate,
    this.initialPriority = TodoPriority.normal,
  });

  @override
  State<TodoDialogBody> createState() => TodoDialogBodyState();
}

class TodoDialogBodyState extends State<TodoDialogBody> {
  DateTime? _dueDate;
  TodoPriority _priority = TodoPriority.normal;

  @override
  void initState() {
    super.initState();
    _dueDate = widget.initialDueDate ?? widget.existingTodo?.dueDate;
    _priority = widget.initialPriority;
  }

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    // NOTE: Full dialog body from lines 732-891
    // Replace all DesignConstants.space* with spacing.*
    // Replace raw TextFormField with AppTextField
    // Replace raw TextButton with AppButton.text
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AppTextField(
          controller: widget.titleController,
          labelText: 'Title',
          // NOTE: preserved from original
        ),
        SizedBox(height: spacing.md),
        AppTextField(
          controller: widget.descriptionController,
          labelText: 'Description',
          maxLines: 3,
        ),
        SizedBox(height: spacing.md),
        _buildDueDatePicker(),
        SizedBox(height: spacing.md),
        _buildPrioritySelector(),
      ],
    );
  }

  Widget _buildDueDatePicker() {
    // NOTE: Copy from lines 798-836, tokenize
    final spacing = FieldGuideSpacing.of(context);
    final radii = FieldGuideRadii.of(context);
    return InkWell(
      borderRadius: BorderRadius.circular(radii.sm),
      onTap: () async {
        final picked = await showDatePicker(
          context: context,
          initialDate: _dueDate ?? DateTime.now(),
          firstDate: DateTime.now().subtract(const Duration(days: 365)),
          lastDate: DateTime.now().add(const Duration(days: 365 * 2)),
        );
        if (picked != null) {
          setState(() => _dueDate = picked);
          widget.onDueDateChanged(picked);
        }
      },
      child: Padding(
        padding: EdgeInsets.all(spacing.md),
        child: Row(
          children: [
            const Icon(Icons.calendar_today),
            SizedBox(width: spacing.sm),
            Text(_dueDate != null
                ? DateFormat('MMM d, y').format(_dueDate!)
                : 'Set due date'),
          ],
        ),
      ),
    );
  }

  Widget _buildPrioritySelector() {
    // NOTE: Copy from lines 837-891, tokenize
    final spacing = FieldGuideSpacing.of(context);
    return Wrap(
      spacing: spacing.sm,
      children: TodoPriority.values.map((priority) {
        return ChoiceChip(
          label: Text(priority.name),
          selected: _priority == priority,
          onSelected: (selected) {
            if (selected) {
              setState(() => _priority = priority);
              widget.onPriorityChanged(priority);
            }
          },
        );
      }).toList(),
    );
  }
}
```

#### Step 4.8.4: Update todos_screen.dart main file

Rewrite `lib/features/todos/presentation/screens/todos_screen.dart` to import extracted widgets, remove inlined classes, tokenize remaining references. Target: ~300 lines.

```dart
// NOTE: At top of todos_screen.dart, add imports:
import 'package:construction_inspector/features/todos/presentation/widgets/todo_card.dart';
import 'package:construction_inspector/features/todos/presentation/widgets/todo_dialog_body.dart';

// WHY: Replace all 25 DesignConstants refs in the main screen body:
// - DesignConstants.space2 -> spacing.sm
// - DesignConstants.space3 -> 12.0 (keep as DesignConstants.space3 — fallback value)
// - DesignConstants.space4 -> spacing.md
// - DesignConstants.space6 -> spacing.lg
// - DesignConstants.space8 -> spacing.xl

// NOTE: Replace ListView.builder with CustomScrollView for sliver migration
// Replace Consumer<TodoProvider> with Selector where only specific fields are needed
// Replace inline _TodoCard with TodoCard, _DueDateChip with TodoDueDateChip, _TodoDialogBody with TodoDialogBody
// Delete classes _TodoCard, _DueDateChip, _TodoDialogBody from this file
```

Key changes in the main screen:
1. Add `final spacing = FieldGuideSpacing.of(context);` at top of `build()`
2. Replace `ListView.builder` with `CustomScrollView` + `SliverList`
3. Replace `Consumer<TodoProvider>` with `Selector<TodoProvider, ({bool isLoading, bool hasError, List<TodoItem> todos})>`
4. Replace all `_TodoCard(` with `TodoCard(`
5. Replace `_buildNoQueryMatchState` empty Column with `AppEmptyState`
6. Replace `_buildNoMatchingState` empty Column with `AppEmptyState`
7. Replace raw `TextButton` in `_buildNoMatchingState` with `AppButton.text`
8. Replace raw `ElevatedButton` in FAB area (if any) with `AppButton.primary`

#### Step 4.8.5: Create widgets barrel for todos feature

Create `lib/features/todos/presentation/widgets/widgets.dart`:

```dart
// lib/features/todos/presentation/widgets/widgets.dart
// WHY: Barrel file for extracted todo widgets
export 'todo_card.dart';
export 'todo_dialog_body.dart';
export 'todo_due_date_chip.dart';
```

#### Step 4.8.6: Add motion to todos_screen.dart

**Action**: Wire animation components created in P2 to todos_screen:

1. **AppStaggeredList**: Wrap the todo list items with `AppStaggeredList` so `TodoCard` widgets stagger in on initial load and filter changes.
2. **AppTapFeedback**: Wrap each `TodoCard` with `AppTapFeedback` for scale feedback on tap.

```dart
// In todos_screen.dart, replace the SliverList of TodoCard items with:
AppStaggeredList(
  // WHY: Staggered entrance for todo cards — FROM SPEC: "List item appear — All list screens"
  children: filteredTodos.map((todo) => AppTapFeedback(
    // WHY: Scale feedback on todo card tap — FROM SPEC: "Card tap — AppTapFeedback"
    child: TodoCard(
      todo: todo,
      onToggle: () => provider.toggleTodo(todo.id),
      onTap: () => _editTodo(todo),
      onDelete: () => _deleteTodo(todo),
    ),
  )).toList(),
),
```

**Verification**: Visual -- todo cards should stagger in; cards should scale on tap.

#### Step 4.8.7: Responsive layout for todos_screen.dart

**Action**: Wrap `todos_screen.dart` body with responsive layout for tablet (FROM SPEC: Todos -- single column -> two-column on tablet). Use `AppResponsiveBuilder` with `compact:` for phone single-column and `medium:` with `AppAdaptiveLayout(body: _buildTodoList(), detail: selectedTodoDetail)` for tablet two-column layout.

#### Step 4.8.8: Verify todos_screen decomposition

```
pwsh -Command "flutter analyze lib/features/todos/"
```

Expected: 0 errors, 0 warnings in `lib/features/todos/`.

---

### Sub-phase 4.9: calculator_screen.dart (712 lines -> ~300 + 3 extracted widgets)

**File**: `lib/features/calculator/presentation/screens/calculator_screen.dart`
**DesignConstants refs**: 26
**Current structure**: `_CalculatorScreenState` (lines 23-91), `_HmaCalculator` (lines 93-292), `_ConcreteCalculator` (lines 293-491), `_CalculatorResultCard` (lines 492-580), `_CalculatorHistorySection` (lines 581-617), `_HistoryTile` (lines 618-712)
**Extraction plan**: Move `_HmaCalculator` -> `hma_calculator_tab.dart`, `_ConcreteCalculator` -> `concrete_calculator_tab.dart`, `_CalculatorResultCard` + `_CalculatorHistorySection` + `_HistoryTile` -> `calculator_result_card.dart` + `calculator_history_section.dart`

**Agent**: `code-fixer-agent`

#### Step 4.9.1: Extract HmaCalculatorTab widget

Create `lib/features/calculator/presentation/widgets/hma_calculator_tab.dart` by extracting `_HmaCalculator` (lines 93-292). Make public, tokenize all 26 DesignConstants refs.

```dart
// lib/features/calculator/presentation/widgets/hma_calculator_tab.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/calculator/data/services/calculator_service.dart';
import 'package:construction_inspector/features/calculator/presentation/providers/calculator_provider.dart';
import 'calculator_result_card.dart';

// FROM SPEC: Extract tab content into standalone widget
class HmaCalculatorTab extends StatefulWidget {
  final CalculatorProvider provider;

  const HmaCalculatorTab({super.key, required this.provider});

  @override
  State<HmaCalculatorTab> createState() => _HmaCalculatorTabState();
}

class _HmaCalculatorTabState extends State<HmaCalculatorTab> {
  // NOTE: Copy controllers and state from _HmaCalculatorState (lines 100-178)
  // Tokenize all spacing/radius:
  // - DesignConstants.space2 -> spacing.sm
  // - DesignConstants.space4 -> spacing.md
  // - DesignConstants.radiusMedium -> radii.md
  // Replace all AppTextField usages (already compliant)
  // Replace raw ElevatedButton with AppButton.primary
  // Replace raw TextButton with AppButton.text

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    // NOTE: Full build from lines 179-292, tokenized
    return SingleChildScrollView(
      padding: EdgeInsets.all(spacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Input fields, calculate button, result card
          // All copied from original with token replacements
        ],
      ),
    );
  }
}
```

#### Step 4.9.2: Extract ConcreteCalculatorTab widget

Create `lib/features/calculator/presentation/widgets/concrete_calculator_tab.dart` by extracting `_ConcreteCalculator` (lines 293-491). Same tokenization pattern as Step 4.9.1.

#### Step 4.9.3: Extract CalculatorResultCard and CalculatorHistorySection

Create `lib/features/calculator/presentation/widgets/calculator_result_card.dart` (from lines 492-580) and `lib/features/calculator/presentation/widgets/calculator_history_section.dart` (from lines 581-712, includes `_HistoryTile`). Tokenize all spacing/radius.

#### Step 4.9.4: Update calculator_screen.dart main file

Rewrite `lib/features/calculator/presentation/screens/calculator_screen.dart` to import extracted widgets, keep only `CalculatorScreen` + `_CalculatorScreenState` with TabController management and top-level build. Target: ~100 lines.

```dart
// NOTE: Main screen becomes thin orchestrator:
// - TabController setup
// - AppScaffold with AppTabBar
// - TabBarView with HmaCalculatorTab and ConcreteCalculatorTab
// All DesignConstants.space* replaced with FieldGuideSpacing.of(context).*
```

#### Step 4.9.5: Create widgets barrel for calculator feature

Create `lib/features/calculator/presentation/widgets/widgets.dart`:

```dart
// lib/features/calculator/presentation/widgets/widgets.dart
export 'calculator_history_section.dart';
export 'calculator_result_card.dart';
export 'concrete_calculator_tab.dart';
export 'hma_calculator_tab.dart';
```

#### Step 4.9.6: Add motion to calculator_screen.dart

**Action**: Wire animation components to calculator_screen (FROM SPEC motion targets):
1. **AppTapFeedback**: Wrap `CalculatorResultCard` and history tiles with `AppTapFeedback`.
2. **AppStaggeredList**: Wrap history list items with `AppStaggeredList`.
3. **AppAnimatedEntrance**: Wrap tab content with `AppAnimatedEntrance` for fade+slide on tab switch.

#### Step 4.9.7: Responsive layout for calculator_screen.dart

**Action**: FROM SPEC: Calculator -- single column -> wider input + results side-by-side. Use `AppResponsiveBuilder` with `compact:` for single-column and `medium:` with `AppAdaptiveLayout(body: inputFields, detail: resultCard)`.

#### Step 4.9.8: Verify calculator_screen decomposition

```
pwsh -Command "flutter analyze lib/features/calculator/"
```

Expected: 0 errors, 0 warnings.

---

### Sub-phase 4.10: project_dashboard_screen.dart (696 lines -> ~300 + 3 widgets)

**File**: `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`
**DesignConstants refs**: 51 (highest per-file count)
**Fixes**: #199 (Review Drafts no delete action), #200 (Review Drafts tile-card style), #207 (empty-state button contrast), #208 (gradient out of place), #233 (button consistency)
**Current structure**: `_ProjectDashboardScreenState` (lines 30-696) with `_buildNoProjectSelected` (line 236), `_buildDraftsPill` (line 271), `_buildTodaysEntryCard` (line 294), `_buildQuickStats` (line 320), `_buildBudgetOverview` (line 383), `_buildTrackedItems` (line 431), `_buildApproachingLimit` (line 550)
**Already extracted**: `dashboard_stat_card.dart`, `weather_summary_card.dart`, `budget_overview_card.dart`, `todays_entry_card.dart`
**Extraction plan**: Move `_buildDraftsPill` -> `drafts_pill.dart`, `_buildTrackedItems` + `_buildApproachingLimit` -> `budget_items_section.dart`, inline `_buildQuickStats` stays (short)

**Agent**: `code-fixer-agent`

#### Step 4.10.1: Extract DraftsPill widget

Create `lib/features/dashboard/presentation/widgets/drafts_pill.dart` by extracting `_buildDraftsPill` (lines 271-293). Tokenize, fix #200 (Review Drafts tile-card style).

```dart
// lib/features/dashboard/presentation/widgets/drafts_pill.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/entries/presentation/providers/daily_entry_provider.dart';
import 'package:construction_inspector/shared/shared.dart';

// FROM SPEC: Fix #200 — Review Drafts should use card style, not pill
// WHY: Consistent with other dashboard sections
class DraftsPill extends StatelessWidget {
  final String projectId;

  const DraftsPill({super.key, required this.projectId});

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    final radii = FieldGuideRadii.of(context);

    return Selector<DailyEntryProvider, int>(
      // WHY: Selector instead of Consumer — only needs draft count
      selector: (_, p) => p.draftCount,
      builder: (context, draftCount, _) {
        if (draftCount == 0) return const SizedBox.shrink();

        // FROM SPEC: #200 — Use AppSectionCard style instead of raw Container
        return AppSectionCard(
          // WHY: Use named route, not raw path string
          onTap: () => context.pushNamed('drafts', pathParameters: {'projectId': projectId}),
          child: Padding(
            padding: EdgeInsets.symmetric(
              horizontal: spacing.md,
              vertical: spacing.sm,
            ),
            child: Row(
              children: [
                Icon(Icons.edit_note, color: FieldGuideColors.of(context).statusWarning),
                SizedBox(width: spacing.sm),
                Expanded(
                  child: AppText.bodyMedium(
                    '$draftCount draft${draftCount == 1 ? '' : 's'} pending review',
                  ),
                ),
                const Icon(Icons.chevron_right),
              ],
            ),
          ),
        );
      },
    );
  }
}
```

#### Step 4.10.2: Extract BudgetItemsSection widget

Create `lib/features/dashboard/presentation/widgets/budget_items_section.dart` by extracting `_buildTrackedItems` (lines 431-549) and `_buildApproachingLimit` (lines 550-696). These are closely related budget item displays.

```dart
// lib/features/dashboard/presentation/widgets/budget_items_section.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/quantities/presentation/providers/bid_item_provider.dart';
import 'package:construction_inspector/features/quantities/presentation/providers/entry_quantity_provider.dart';
import 'package:construction_inspector/shared/shared.dart';

// FROM SPEC: Extract oversized _build methods into standalone widgets
class TrackedItemsSection extends StatelessWidget {
  const TrackedItemsSection({super.key});

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    final radii = FieldGuideRadii.of(context);
    final fg = FieldGuideColors.of(context);
    // NOTE: Full implementation from lines 431-549, tokenized
    // Replace all DesignConstants.space* with spacing.*
    // Replace all DesignConstants.radius* with radii.*
    // Replace raw Container decorations with AppSectionCard
    // Replace raw TextButton with AppButton.text
    // ... (copy implementation lines from original, tokenize all spacing/radius/buttons)
  }
}

class ApproachingLimitSection extends StatelessWidget {
  const ApproachingLimitSection({super.key});

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    final fg = FieldGuideColors.of(context);
    // NOTE: Full implementation from lines 550-696, tokenized
    // ... (copy implementation lines from original, tokenize all spacing/radius/buttons)
  }
}
```

#### Step 4.10.3: Update project_dashboard_screen.dart with fixes

Rewrite `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`:

1. Import extracted `DraftsPill`, `TrackedItemsSection`, `ApproachingLimitSection`
2. Tokenize all 51 `DesignConstants` references
3. Fix #207: Replace `_buildNoProjectSelected` empty-state button with `AppButton.primary` for contrast
4. Fix #208: Remove gradient decoration from `_buildNoProjectSelected` (was `AppTheme` import for gradient — remove that import)
5. Fix #233: Ensure all buttons use `AppButton.*` variants consistently
6. Already uses `CustomScrollView` with slivers — keep that structure, just tokenize
7. Replace `Consumer` patterns with `Selector` where specific fields needed

```dart
// IMPORTANT: Fix #207 in _buildNoProjectSelected:
// Replace raw ElevatedButton with:
AppButton.primary(
  key: TestingKeys.dashboardViewProjectsButton,
  label: 'View Projects',
  icon: Icons.folder_outlined,
  onPressed: () => context.goNamed('projects'),
  // WHY: #207 — old ElevatedButton had poor contrast on empty state background
),

// IMPORTANT: Fix #208 — remove gradient container:
// Delete the Container with BoxDecoration gradient wrapping the SliverAppBar flexibleSpace
// Replace with simple themed background from FieldGuideColors.of(context)

// IMPORTANT: Fix #233 — button consistency:
// All buttons in dashboard must use AppButton.* variants
// Replace: ElevatedButton.icon -> AppButton.primary
// Replace: TextButton -> AppButton.text
// Replace: OutlinedButton -> AppButton.secondary
```

#### Step 4.10.4: Remove AppTheme import from project_dashboard_screen.dart

```dart
// WHY: #208 — the gradient was sourced from AppTheme directly
// Remove this import:
// import 'package:construction_inspector/core/theme/app_theme.dart';
// The gradient is now removed entirely, or if still needed, use FieldGuideColors.of(context).gradientStart/gradientEnd
```

#### Step 4.10.5: Add motion to project_dashboard_screen.dart

**Action**: Wire animation components created in P2 to project_dashboard_screen:

1. **AppValueTransition**: Wrap budget amounts, stat counts, and percentage values in `DashboardStatCard` and `BudgetOverviewCard` with `AppValueTransition` so they animate on value changes.
2. **AppAnimatedEntrance**: Wrap the main dashboard content area with `AppAnimatedEntrance` for fade+slide on screen entry.
3. **AppTapFeedback**: Wrap `DraftsPill`, `DashboardStatCard`, and `AppGlassCard` instances with `AppTapFeedback` for scale feedback.

```dart
// In dashboard_stat_card.dart or project_dashboard_screen.dart _buildQuickStats:
AppValueTransition(
  // WHY: Animated counter for stat values — FROM SPEC: "Value change — Budgets, counts, amounts"
  value: statValue,
  builder: (context, displayValue) => AppText.headlineMedium('$displayValue'),
),

// In project_dashboard_screen.dart, wrap main content:
AppAnimatedEntrance(
  // WHY: Fade+slide entrance for dashboard content on screen mount
  child: CustomScrollView(/* ... existing slivers ... */),
),

// Wrap tappable cards:
AppTapFeedback(
  // WHY: Scale feedback on dashboard card tap — FROM SPEC: "Card tap — AppTapFeedback"
  child: DashboardStatCard(/* ... */),
),
```

#### Step 4.10.6: Fix #199 -- Add delete action to review draft tiles

**Action**: In the `DraftsPill` widget or in `project_dashboard_screen.dart` where draft entries are listed, add a delete action for review drafts. If `DraftsPill` only shows a count with a navigation link, the delete action should be available on the destination screen (entries list filtered by draft). However, if individual draft tiles are rendered on the dashboard, add swipe-to-delete or a long-press menu.

```dart
// FROM SPEC: Fix #199 — "Review Drafts no delete action"
// Option A: If drafts are listed individually on dashboard, add Dismissible:
Dismissible(
  key: ValueKey(draft.id),
  direction: DismissDirection.endToStart,
  confirmDismiss: (_) async {
    // WHY: Confirm before deleting a draft entry
    return await AppDialog.show(
      context: context,
      title: 'Delete Draft?',
      content: 'This will permanently remove the draft entry.',
      actionsBuilder: (context) => [
        AppButton.text(label: 'Cancel', onPressed: () => Navigator.pop(context, false)),
        AppButton.primary(label: 'Delete', onPressed: () => Navigator.pop(context, true)),
      ],
    );
  },
  onDismissed: (_) => entryProvider.deleteEntry(draft.id),
  background: Container(
    color: FieldGuideColors.of(context).statusError,
    alignment: Alignment.centerRight,
    padding: EdgeInsets.only(right: FieldGuideSpacing.of(context).md),
    child: Icon(Icons.delete, color: Theme.of(context).colorScheme.onError), // WHY: no hardcoded Colors.white
  ),
  child: DraftTile(draft: draft),
),

// Option B: If DraftsPill only shows count + nav link, ensure the entries_list_screen
// (filtered to drafts) has delete actions on each draft card. Add swipe-to-delete
// to EntryListCard when entry.status == 'draft'.
```

#### Step 4.10.7: Sliver verification for project_dashboard_screen.dart

**Action**: Verify current scroll implementation. The dashboard already uses `CustomScrollView` with slivers (noted in Step 4.10.3). Confirm this is preserved after decomposition. If any extracted widget introduced a nested `ListView`, refactor to return sliver-compatible widgets.

#### Step 4.10.8: Responsive layout for project_dashboard_screen.dart

**Action**: FROM SPEC: Dashboard -- single column -> two-column grid -> three-column with side panel. Use `AppResponsiveBuilder` with:
- `compact:` single column scrollable cards (current layout)
- `medium:` `AppResponsiveGrid(columns: 2)` wrapping dashboard cards
- `large:` `AppAdaptiveLayout(body: AppResponsiveGrid(columns: 2, children: cards), sidePanel: quickStatsPanel)`

#### Step 4.10.9: Verify project_dashboard decomposition

```
pwsh -Command "flutter analyze lib/features/dashboard/"
```

Expected: 0 errors, 0 warnings. Issues #199, #200, #207, #208, #233 addressed.

---

### Sub-phase 4.11: quantity_calculator_screen.dart (656 lines -> ~300 + 2 widgets)

**File**: `lib/features/quantities/presentation/screens/quantity_calculator_screen.dart`
**DesignConstants refs**: 13
**Current structure**: `QuantityCalculatorResult` (lines 16-28), `QuantityCalculatorScreen` (lines 34-168), `_FieldConfig` (lines 170-188), `_CalculatorTabConfig` (lines 189-383), `_CalculatorTab` (lines 384-533), `_FormulaCard` (lines 534-576), `_ResultCard` (lines 577-656)
**Extraction plan**: Move `_CalculatorTab` + `_FieldConfig` + `_CalculatorTabConfig` -> `quantity_calculator_tab.dart`, `_FormulaCard` + `_ResultCard` -> `quantity_calculator_cards.dart`

**Agent**: `code-fixer-agent`

#### Step 4.11.1: Extract QuantityCalculatorTab widget

Create `lib/features/quantities/presentation/widgets/quantity_calculator_tab.dart` by extracting `_CalculatorTab` (lines 384-533), `_FieldConfig` (lines 170-188), `_CalculatorTabConfig` (lines 189-383). Tokenize all DesignConstants refs.

```dart
// lib/features/quantities/presentation/widgets/quantity_calculator_tab.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/calculator/data/services/calculator_service.dart';
import 'quantity_calculator_cards.dart';

// FROM SPEC: Extract tab + config into reusable widget
class FieldConfig {
  // NOTE: made public, copy from lines 170-188
  final String label;
  final String hint;
  final String unit;
  final TextInputType keyboardType;
  final TextEditingController controller;

  const FieldConfig({
    required this.label,
    required this.hint,
    required this.unit,
    required this.keyboardType,
    required this.controller,
  });
}

// NOTE: CalculatorTabConfig and CalculatorTab extracted with full implementations
// Tokenize: DesignConstants.space* -> FieldGuideSpacing.of(context).*
// Replace raw AppTextField usages (already compliant)
// Replace raw ElevatedButton with AppButton.primary
```

#### Step 4.11.2: Extract QuantityCalculatorCards

Create `lib/features/quantities/presentation/widgets/quantity_calculator_cards.dart` from `_FormulaCard` (lines 534-576) and `_ResultCard` (lines 577-656).

#### Step 4.11.3: Update quantity_calculator_screen.dart

Slim main file to ~150 lines. Keep `QuantityCalculatorResult` and `QuantityCalculatorScreen` with tab controller. Import extracted widgets. Tokenize remaining refs.

#### Step 4.11.4: Add motion to quantity_calculator_screen.dart

**Action**: Wire animation components (FROM SPEC motion targets):
1. **AppTapFeedback**: Wrap `FormulaCard` and `ResultCard` with `AppTapFeedback`.
2. **AppAnimatedEntrance**: Wrap tab content with `AppAnimatedEntrance` for fade+slide on tab switch.

#### Step 4.11.5: Responsive layout for quantity_calculator_screen.dart

**Action**: FROM SPEC: Quantities -- single column list -> list + calculator side-by-side. Use `AppResponsiveBuilder` with `compact:` for single-column and `medium:` with `AppAdaptiveLayout(body: quantityList, detail: calculatorPanel)`.

#### Step 4.11.6: Verify quantity_calculator decomposition

```
pwsh -Command "flutter analyze lib/features/quantities/"
```

Expected: 0 errors, 0 warnings.

---

### Sub-phase 4.12: form_viewer_screen.dart (636 lines -> ~300 + 2 widgets)

**File**: `lib/features/forms/presentation/screens/form_viewer_screen.dart`
**DesignConstants refs**: 35
**Current structure**: `_FormViewerScreenState` (lines 31-636) with `_buildQuickActionBar` (line 332), `_buildHeaderSection` (line 373), `_buildTestsSection` (line 398), `_buildProctorsSection` (line 450), `_buildStandardsSection` (line 496), `_buildRemarksSection` (line 530)
**Extraction plan**: Extract `_buildQuickActionBar` -> `form_viewer_action_bar.dart`, group `_buildTestsSection` + `_buildProctorsSection` + `_buildStandardsSection` + `_buildRemarksSection` -> `form_viewer_sections.dart`

**Agent**: `code-fixer-agent`

#### Step 4.12.1: Extract FormViewerActionBar widget

Create `lib/features/forms/presentation/widgets/form_viewer_action_bar.dart` by extracting `_buildQuickActionBar` (lines 332-372). Tokenize.

```dart
// lib/features/forms/presentation/widgets/form_viewer_action_bar.dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/forms/data/registries/form_quick_action_registry.dart';
import 'package:construction_inspector/features/forms/data/models/models.dart';

// FROM SPEC: Extract action bar for line count reduction
class FormViewerActionBar extends StatelessWidget {
  final FormResponse response;
  final Map<String, dynamic> responseData;
  final VoidCallback onAutoFill;
  final VoidCallback onPreview;
  final VoidCallback onSave;
  final bool saving;
  final bool dirty;

  const FormViewerActionBar({
    super.key,
    required this.response,
    required this.responseData,
    required this.onAutoFill,
    required this.onPreview,
    required this.onSave,
    required this.saving,
    required this.dirty,
  });

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    // NOTE: Full quick action bar from lines 332-372, tokenized
    // Replace raw IconButton with AppButton.icon
    // Replace raw TextButton with AppButton.text
    // Replace DesignConstants.space* with spacing.*
    // ... (copy implementation from original lines, tokenize all spacing/radius/buttons)
  }
}
```

#### Step 4.12.2: Extract FormViewerSections widget

Create `lib/features/forms/presentation/widgets/form_viewer_sections.dart` by extracting `_buildTestsSection`, `_buildProctorsSection`, `_buildStandardsSection`, `_buildRemarksSection` (lines 398-636). These all follow the same pattern and use `AppFormSection` organisms from P3.

```dart
// lib/features/forms/presentation/widgets/form_viewer_sections.dart
import 'package:flutter/material.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import 'package:construction_inspector/features/forms/data/models/models.dart';

// FROM SPEC: Form viewer sections use AppFormSection organism
class FormViewerTestsSection extends StatelessWidget {
  final Map<String, dynamic> responseData;
  final ValueChanged<Map<String, dynamic>> onDataChanged;

  const FormViewerTestsSection({
    super.key,
    required this.responseData,
    required this.onDataChanged,
  });

  @override
  Widget build(BuildContext context) {
    final spacing = FieldGuideSpacing.of(context);
    // NOTE: Copy from _buildTestsSection, use AppFormSection organism
    return const SizedBox.shrink();
  }
}

// NOTE: Similar pattern for ProctorsSection, StandardsSection, RemarksSection
// Each receives responseData + onDataChanged callback
// Each uses AppFormSection from design system organisms
```

#### Step 4.12.3: Update form_viewer_screen.dart

Slim to ~300 lines. Keep state management (loading, saving, dirty tracking), lifecycle, and `_load()`/`_save()` methods. Import extracted widgets.

#### Step 4.12.4: Add motion to form_viewer_screen.dart

**Action**: Wire animation components (FROM SPEC motion targets):
1. **AppTapFeedback**: Wrap interactive cards in action bar with `AppTapFeedback`.
2. **AppStaggeredList**: Wrap section list items with `AppStaggeredList`.
3. **AppAnimatedEntrance**: Wrap action bar and main content with `AppAnimatedEntrance`.

#### Step 4.12.5: Verify form_viewer decomposition

```
pwsh -Command "flutter analyze lib/features/forms/"
```

Expected: 0 errors, 0 warnings.

---

### Sub-phase 4.13: Additional Screens Tokenization + Decomposition

**Agent**: `code-fixer-agent`

**Protocol step coverage for additional screens**: These screens follow a lighter decomposition pass. For each screen below, the protocol steps applied are: (1) component discovery (via P4b gate), (2) promote shared patterns (if found), (3) extract private widgets (if >300 lines), (4) tokenize. Skipped steps per screen are noted inline. Screens with `Consumer` patterns or scrollable lists additionally get Selector-ify and/or sliver migration. Screens that are already <300 lines skip extraction.

#### Step 4.13.1: Tokenize gallery_screen.dart (614 lines, 24 DesignConstants refs)

**File**: `lib/features/gallery/presentation/screens/gallery_screen.dart`

Extract `_FilterSheet` (lines 305-467) -> `lib/features/gallery/presentation/widgets/gallery_filter_sheet.dart`.
Extract `_PhotoViewerScreen` (lines 468-614) -> `lib/features/gallery/presentation/widgets/gallery_photo_viewer.dart`.
Tokenize main screen (lines 21-304): all 24 `DesignConstants` -> token equivalents.

```dart
// WHY: gallery_screen has 3 classes in one file
// _FilterSheet -> GalleryFilterSheet (public)
// _PhotoViewerScreen -> GalleryPhotoViewer (public)
// Main screen stays at ~200 lines after extraction
// Replace all DesignConstants.space* -> FieldGuideSpacing.of(context).*
// Replace all DesignConstants.radius* -> FieldGuideRadii.of(context).*
// Replace raw TextButton in filter chips with AppButton.text
// SKIPPED: (5) sliver -- gallery uses GridView, not list; (7) motion -- grid items don't benefit from stagger
// SKIPPED: (8) responsive -- gallery grid already adapts via GridView crossAxisCount
// SKIPPED: (10) HTTP driver -- no TestingKey changes
```

#### Step 4.13.2: Tokenize pdf_import_preview_screen.dart (631 lines, 14 DesignConstants refs)

**File**: `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`

Extract `_BidItemPreviewCard` (lines 350-506) -> `lib/features/pdf/presentation/widgets/bid_item_preview_card.dart`.
Extract `_BidItemEditDialogBody` (lines 507-631) -> `lib/features/pdf/presentation/widgets/bid_item_edit_dialog_body.dart`.
Tokenize main screen. Target: ~250 lines.

#### Step 4.13.3: Tokenize + decompose entries_list_screen.dart (554 lines, 24 DesignConstants refs)

**File**: `lib/features/entries/presentation/screens/entries_list_screen.dart`

Extract `_buildDateGroup` + `_buildEntryCard` (lines 303-554) -> `lib/features/entries/presentation/widgets/entry_list_card.dart` + `lib/features/entries/presentation/widgets/entry_date_group.dart`.
Sliver migration: current `ListView` -> `CustomScrollView` with `SliverList`.
Tokenize all 24 refs.

**Responsive layout** (FROM SPEC: Entries List -- single column list -> list-detail on tablet):

```dart
body: AppResponsiveBuilder(
  compact: (context) => _buildEntryList(),
  // WHY: AppAdaptiveLayout handles list-detail pane split
  medium: (context) => AppAdaptiveLayout(
    body: _buildEntryList(),
    detail: _selectedEntry != null
        ? EntryPreviewPane(entry: _selectedEntry!)
        : const AppEmptyState(
            icon: Icons.article_outlined,
            title: 'Select an entry',
            subtitle: 'Choose an entry from the list to preview',
          ),
  ),
),
```

**Selector-ify**: Convert any `Consumer<DailyEntryProvider>` to `Selector<DailyEntryProvider, List<DailyEntry>>` where only the entries list is needed.

**Motion**: Wire animation components to entries_list_screen:

1. **AppStaggeredList**: Wrap the entry card list items with `AppStaggeredList` so `EntryListCard` widgets stagger in on load and filter changes.
2. **AppTapFeedback**: Wrap each `EntryListCard` with `AppTapFeedback` for scale feedback on tap.
3. **AppAnimatedEntrance**: Wrap the screen content with `AppAnimatedEntrance` for fade+slide on mount.

```dart
// In entries_list_screen.dart SliverList builder:
AppStaggeredList(
  // WHY: Staggered entrance for entry cards — FROM SPEC: "List item appear — All list screens"
  children: entries.map((entry) => AppTapFeedback(
    // WHY: Scale feedback on entry card tap — FROM SPEC: "Card tap — AppTapFeedback"
    child: EntryListCard(entry: entry, onTap: () => _navigateToEntry(entry)),
  )).toList(),
),
```

#### Step 4.13.4: Tokenize quantities_screen.dart (520 lines, 8 DesignConstants refs) + Fix #202, #203

**File**: `lib/features/quantities/presentation/screens/quantities_screen.dart`

Tokenize 8 `DesignConstants` refs.

**Sliver migration**: If current scroll uses `ListView`, migrate to `CustomScrollView` + `SliverList.builder` (FROM SPEC sliver targets).

**Responsive layout**: FROM SPEC: Quantities -- single column list -> list + calculator side-by-side. Add `AppResponsiveBuilder` with `compact:` single-column list and `medium:` with `AppAdaptiveLayout(body: quantityList, detail: calculatorPanel)`.

```dart
// FROM SPEC: Fix #202 — Quantity picker search not cleared on selection
// In the bid item picker/search widget, call searchController.clear() after selection

// FROM SPEC: Fix #203 — Quantities + button workflow
// The "+" button should open the quantity calculator directly, not a picker dialog first
// Simplify the add-quantity flow to reduce taps
```

#### Step 4.13.5: Tokenize admin_dashboard_screen.dart (435 lines, 9 DesignConstants refs)

**File**: `lib/features/settings/presentation/screens/admin_dashboard_screen.dart`

Extract `_ApproveButton` (lines 412-435) -> inline or keep (small).
Tokenize 9 refs. Replace raw `ElevatedButton` in `_ApproveButton` with `AppButton.primary`.
Extract `_buildSectionHeader`, `_buildRequestTile`, `_buildMemberTile`, `_buildRoleBadge`, `_buildSyncIndicator` into a separate `admin_dashboard_widgets.dart` if total remains >300 lines.

#### Step 4.13.6: Tokenize settings_screen.dart (420 lines, 1 DesignConstants ref)

**File**: `lib/features/settings/presentation/screens/settings_screen.dart`

Tokenize the 1 ref. Add canonical layout:

```dart
// FROM SPEC: settings canonical layout: single column (phone) -> left nav + content (tablet)
// Wrap with AppResponsiveBuilder:
// - compact: single scrollable column with sections
// - medium+: NavigationRail on left with section names, content on right
```

Decompose `_buildCertificationsSection` (lines 125-155) if screen exceeds 300 lines after layout wrapper.

#### Step 4.13.7: Tokenize company_setup_screen.dart (442 lines, 17 DesignConstants refs)

**File**: `lib/features/auth/presentation/screens/company_setup_screen.dart`

Extract `_SectionCard` (lines 408-442) — evaluate if it should use `AppSectionCard` from design system instead. If yes, replace all `_SectionCard` usages with `AppSectionCard`. Tokenize 17 refs.

#### Step 4.13.8: Verify all additional screens

```
pwsh -Command "flutter analyze lib/features/gallery/ lib/features/pdf/ lib/features/entries/ lib/features/quantities/ lib/features/settings/ lib/features/auth/"
```

Expected: 0 errors, 0 warnings across all touched features.

---

### Sub-phase 4.14: Additional Widgets Tokenization

**Agent**: `code-fixer-agent`

#### Step 4.14.1: Tokenize entry_contractors_section.dart (585 lines, 17 DesignConstants refs)

**File**: `lib/features/entries/presentation/widgets/entry_contractors_section.dart`

Extract `_InlineContractorChooser` (lines 454-585) -> `lib/features/entries/presentation/widgets/inline_contractor_chooser.dart`.
Tokenize 17 refs in main section. Replace `Consumer` with `Selector` where only contractor list/count needed.
Replace raw `ElevatedButton`/`TextButton`/`IconButton` with `AppButton.*` variants.

#### Step 4.14.2: Tokenize entry_quantities_section.dart (508 lines, 0 DesignConstants refs but uses raw spacing)

**File**: `lib/features/entries/presentation/widgets/entry_quantities_section.dart`

Even though 0 explicit `DesignConstants` refs, scan for raw `EdgeInsets.*(N)`, `SizedBox(width: N)`, `BorderRadius.circular(N)` with numeric literals. Replace with token equivalents. Extract sub-widgets if >300 lines after tokenization.

#### Step 4.14.3: Decompose hub_proctor_content.dart (486 lines, 16 DesignConstants refs -> ~250)

**File**: `lib/features/forms/presentation/widgets/hub_proctor_content.dart`

This is a single `HubProctorContent` class (line 7). Decompose by extracting the main build sections into helper widgets:
- Extract proctor data entry fields -> `proctor_data_fields.dart`
- Extract proctor result display -> `proctor_result_display.dart`
Tokenize 16 refs. Target: ~250 lines in main file.

#### Step 4.14.4: Tokenize entry_forms_section.dart (356 lines, 9 DesignConstants refs)

**File**: `lib/features/entries/presentation/widgets/entry_forms_section.dart`

Tokenize 9 refs. File is near target (356 vs 300) — extract any private widget class if present to bring under 300.

#### Step 4.14.5: Tokenize photo_detail_dialog.dart (328 lines)

**File**: `lib/features/entries/presentation/widgets/photo_detail_dialog.dart`

Tokenize all spacing/radius literals. Replace raw button types with `AppButton.*`.

#### Step 4.14.6: Tokenize member_detail_sheet.dart (334 lines, 8 DesignConstants refs)

**File**: `lib/features/settings/presentation/widgets/member_detail_sheet.dart`

Tokenize 8 refs. Extract sub-widget if >300 lines after.

#### Step 4.14.7: Tokenize entry_photos_section.dart (310 lines)

**File**: `lib/features/entries/presentation/widgets/entry_photos_section.dart`

Tokenize all spacing/radius literals. Minor — near target already.

#### Step 4.14.8: Tokenize photo_name_dialog.dart (297 lines)

**File**: `lib/features/photos/presentation/widgets/photo_name_dialog.dart`

Already under 300 lines. Tokenize any remaining raw literals.

#### Step 4.14.9: Verify all additional widgets

```
pwsh -Command "flutter analyze lib/features/entries/ lib/features/forms/ lib/features/settings/ lib/features/photos/"
```

Expected: 0 errors, 0 warnings.

---

### Sub-phase 4.15: Remaining GitHub Issues

**Agent**: `code-fixer-agent`

#### Step 4.15.1: Fix #209 — Forms list internal ID visible

**File**: `lib/features/forms/presentation/screens/forms_list_screen.dart` (302 lines, 5 DesignConstants refs)

Tokenize the 5 DesignConstants refs. Fix #209 by removing internal ID display from form list tiles.

**Sliver migration**: If current scroll uses `ListView`, migrate to `CustomScrollView` + `SliverList.builder` (FROM SPEC sliver targets).

**Responsive layout**: FROM SPEC: Forms List -- single column -> two-column. Add `AppResponsiveBuilder` with `compact:` single-column and `medium:` with `AppAdaptiveLayout(body: formsList, detail: selectedFormPreview)`.

Fix #209 details:

```dart
// FROM SPEC: Fix #209 — forms_list_screen shows internal form response ID in subtitle
// Find the ListTile or AppListTile that displays the form response
// Remove or hide the internal UUID from the subtitle
// Replace with a meaningful display: form type name, date created, or status
// WHY: Internal IDs are not user-facing information
```

#### Step 4.15.2: Fix #238 — no_inline_text_style 6 violations in pay apps

Scan pay application files for `TextStyle(` in presentation layer:

```
pwsh -Command "flutter analyze lib/features/ 2>&1 | Select-String 'no_inline_text_style'"
```

For each violation found in pay app files, replace inline `TextStyle(` with `AppText.*` factory constructors or `Theme.of(context).textTheme.*` slots.

```dart
// FROM SPEC: Fix #238 — 6 no_inline_text_style violations in pay apps
// Find: TextStyle(fontSize: N, fontWeight: ..., color: ...)
// Replace with: AppText.bodyMedium(...), AppText.titleSmall(...), etc.
// Or use textTheme slots: Theme.of(context).textTheme.bodyMedium
// WHY: Lint rule enforces consistent text styling through design system
```

#### Step 4.15.3: Verify remaining issues fixed

```
pwsh -Command "flutter analyze lib/features/forms/ lib/features/"
```

Expected: 0 errors, 0 warnings. Issues #209, #238 addressed.

---

### Sub-phase 4.16: Shared Widget Replacements

**Agent**: `code-fixer-agent`

**NOTE**: When modifying `scaffold_with_nav_bar.dart` in this sub-phase, ensure all imports use `core/design_system/tokens/` paths (e.g., `core/design_system/tokens/field_guide_colors.dart`) not legacy `core/theme/` paths. Verify and correct any remaining `core/theme/` imports.

**NOTE**: Verify that #201 (Android keyboard blocks buttons) is fully resolved after P2. If `resizeToAvoidBottomInset: true` alone is insufficient (e.g., `AppBottomBar` or bottom buttons are still obscured), add keyboard-aware padding using `MediaQuery.of(context).viewInsets.bottom` to push content above the keyboard.

**Verification for #201**: Concrete test -- launch on Android emulator, navigate to entry editor, focus a text field to raise keyboard, confirm save button remains visible above keyboard. Add a widget test that verifies `MediaQuery.of(context).viewInsets.bottom` is respected by `AppScaffold`'s bottom bar positioning.

#### Step 4.16.1: Replace StaleConfigWarning with AppBanner composition

**File to update**: `lib/core/router/scaffold_with_nav_bar.dart` (line 72)

Replace `StaleConfigWarning(onRetry: ...)` with an `AppBanner` composition:

```dart
// FROM SPEC: Replace StaleConfigWarning with AppBanner composition
// In scaffold_with_nav_bar.dart, replace:
//   banners.add(StaleConfigWarning(onRetry: () => appConfigProvider.checkConfig()));
// With:
banners.add(
  AppBanner(
    // WHY: AppBanner is the new composable banner from design system
    icon: Icons.wifi_off,
    message: 'Last server check was over 24 hours ago. Connect to verify your account status.',
    severity: AppBannerSeverity.warning,
    actionLabel: 'Retry',
    onAction: () => appConfigProvider.checkConfig(),
  ),
);
```

#### Step 4.16.2: Replace VersionBanner with AppBanner composition

**File to update**: `lib/core/router/scaffold_with_nav_bar.dart` (line 64)

Replace `VersionBanner(message: ...)` with `AppBanner`:

```dart
// FROM SPEC: Replace VersionBanner with AppBanner composition
// Replace:
//   banners.add(VersionBanner(message: appConfigProvider.updateMessage));
// With:
banners.add(
  AppBanner(
    icon: Icons.system_update,
    message: appConfigProvider.updateMessage ??
        'A new version is available. Please update when convenient.',
    severity: AppBannerSeverity.info,
    dismissible: true, // WHY: VersionBanner was dismissible via StatefulWidget
  ),
);
```

#### Step 4.16.3: Replace inline MaterialBanner instances in scaffold_with_nav_bar.dart

Replace the stale sync data banner (lines 81-93) and offline indicator (lines 98-114) with `AppBanner`:

```dart
// Stale sync data:
banners.add(
  AppBanner(
    icon: Icons.warning_amber,
    message: 'Data may be out of date \u2014 last synced ${syncProvider.lastSyncText}',
    severity: AppBannerSeverity.warning,
    actionLabel: 'Sync Now',
    onAction: () => syncProvider.sync(),
  ),
);

// Offline indicator:
banners.add(
  AppBanner(
    icon: Icons.cloud_off,
    message: 'You are offline. Changes will sync when connection is restored.',
    severity: AppBannerSeverity.warning,
    actionLabel: 'Retry',
    onAction: () async {
      await syncCoordinator.checkDnsReachability();
    },
  ),
);
```

#### Step 4.16.4: Remove StaleConfigWarning import and delete file

1. Remove `import` of `StaleConfigWarning` from `scaffold_with_nav_bar.dart` (via `shared.dart` barrel)
2. Delete `lib/shared/widgets/stale_config_warning.dart`
3. Remove `export 'stale_config_warning.dart';` from `lib/shared/widgets/widgets.dart`

#### Step 4.16.5: Remove VersionBanner import and delete file

1. Remove `import` of `VersionBanner` from `scaffold_with_nav_bar.dart` (via `shared.dart` barrel)
2. Delete `lib/shared/widgets/version_banner.dart`
3. Remove `export 'version_banner.dart';` from `lib/shared/widgets/widgets.dart`

#### Step 4.16.6: Update shared widgets barrel

Update `lib/shared/widgets/widgets.dart` to reflect deletions:

```dart
// lib/shared/widgets/widgets.dart
library;

// WHY: confirmation_dialog.dart, empty_state_widget.dart already deleted in P2
// contextual_feedback_overlay.dart, search_bar_field.dart moved to design system in P2
// stale_config_warning.dart, version_banner.dart deleted in this sub-phase
export 'permission_dialog.dart';
// NOTE: Only permission_dialog remains — evaluate if this barrel is still needed
```

#### Step 4.16.7: Verify deleted files do not exist

**Action**: Confirm the deleted files are actually gone:
```
# WHY: Verify deletion completed -- files should not exist
pwsh -Command "Test-Path lib/shared/widgets/stale_config_warning.dart"
pwsh -Command "Test-Path lib/shared/widgets/version_banner.dart"
```
Expected: Both return `False`.

Also grep to confirm no remaining imports reference the deleted files:
```
pwsh -Command "Select-String -Path lib/**/*.dart -Pattern 'stale_config_warning|version_banner' -Recurse"
```
Expected: No matches (or only this plan file).

#### Step 4.16.8: Verify shared widget replacements

```
pwsh -Command "flutter analyze lib/core/router/ lib/shared/"
```

Expected: 0 errors, 0 warnings. No references to deleted files remain.

---

## Phase 5: Performance

**Prerequisite**: Phase 4 (all sub-phases) complete. All screens decomposed, tokenized, sliver-migrated.

---

### Sub-phase 5.1: Profiling Protocol

**Agent**: `general-purpose`

#### Step 5.1.1: Document pre-optimization baseline

Create `.claude/plans/performance-baseline-p5.md` (temporary tracking file, deleted in Step 5.3.4):

```markdown
# Performance Baseline

## Profiling Protocol
1. Build Windows debug: `pwsh -Command "flutter run -d windows --profile"`
2. Open Flutter DevTools Performance tab
3. Navigate to each screen, perform standard interactions
4. Record: avg frame build time, avg frame render time, worst frame time, rebuild count

## Target Screens (5 worst expected)
| Screen | Avg Build (ms) | Avg Render (ms) | Worst Frame (ms) | Rebuild Count |
|--------|---------------|-----------------|-------------------|---------------|
| entry_editor | TBD | TBD | TBD | TBD |
| project_setup | TBD | TBD | TBD | TBD |
| home | TBD | TBD | TBD | TBD |
| project_list | TBD | TBD | TBD | TBD |
| mdot_hub | TBD | TBD | TBD | TBD |
```

#### Step 5.1.2: Profile entry_editor_screen

Run the app in profile mode and follow this profiling protocol:

1. Open Flutter DevTools Performance tab (URL printed in console on launch)
2. Navigate to entry editor screen with test data loaded
3. Click "Record" in Performance tab, then scroll through entries list for 10 seconds
4. Stop recording and identify any frames exceeding the 16ms budget
5. For each slow frame, expand the frame detail to find the responsible widget subtree
6. Record avg frame build time, avg frame render time, worst frame time, and rebuild count in the baseline doc

```
pwsh -Command "flutter run -d windows --profile" -timeout 600000
```

#### Step 5.1.3: Profile remaining 4 screens

Profile `project_setup_screen`, `home_screen`, `project_list_screen`, `mdot_hub_screen`. Record baselines.

#### Step 5.1.4: Identify rebuild storms

Use Widget Rebuild Tracker in DevTools to find widgets rebuilding more than expected. Document the top 5 rebuild offenders per screen.

---

### Sub-phase 5.1b: Surgical Bottleneck Fixes

**Agent**: `code-fixer-agent`

<!-- FROM SPEC (Section 6, Profiling Protocol step 4): "Fix top 5 bottlenecks surgically" -->

#### Step 5.1b.1: Fix top 5 rebuild offenders from 5.1.4

Take the top 5 rebuild offenders identified in Step 5.1.4 and apply targeted fixes:

1. **Selector conversion** -- Replace `Consumer<T>` with `Selector<T, U>` where the widget only uses a subset of the provider's state. Select the minimal primitive/value needed.
2. **const constructors** -- Add `const` to static sub-widgets that do not depend on runtime state. This prevents them from being rebuilt when the parent rebuilds.
3. **setState scope reduction** -- Where `setState` rebuilds an entire screen/widget, extract the mutable portion into a smaller `StatefulWidget` so only that sub-tree rebuilds.
4. **Extract static sub-trees** -- Move unchanging widget sub-trees into separate `const` widget classes or final fields.
5. **Avoid expensive computations in build** -- Cache computed values (e.g., filtered lists, formatted strings) in state rather than recomputing each build.

For each fix, add a `// WHY: Reduces rebuilds -- was top-N offender in P5 profiling` comment.

#### Step 5.1b.2: Verify bottleneck fixes compile

```
pwsh -Command "flutter analyze"
```

Expected: 0 errors. Bottleneck fixes are minimal and surgical -- no structural changes.

---

### Sub-phase 5.2: RepaintBoundary Placement

**Agent**: `code-fixer-agent`

#### Step 5.2.1: Add RepaintBoundary to scrolling list items

For each screen that uses `SliverList` or `ListView.builder`, wrap each item builder's return value with `RepaintBoundary`:

```dart
// WHY: RepaintBoundary prevents list item repaints from propagating to siblings
// Apply to: todos_screen (TodoCard), entries_list_screen (EntryListCard),
//           project_list_screen (ProjectCard), gallery_screen (photo grid items),
//           quantities_screen (bid item tiles)

// Pattern:
itemBuilder: (context, index) {
  return RepaintBoundary(
    // NOTE: Each list item gets its own repaint boundary
    child: TodoCard(
      todo: todos[index],
      // ...
    ),
  );
},
```

Files to modify:
- `lib/features/todos/presentation/screens/todos_screen.dart`
- `lib/features/entries/presentation/screens/entries_list_screen.dart`
- `lib/features/projects/presentation/screens/project_list_screen.dart`
- `lib/features/gallery/presentation/screens/gallery_screen.dart`
- `lib/features/quantities/presentation/screens/quantities_screen.dart`

#### Step 5.2.2: Add RepaintBoundary to AppBottomBar

**File**: `lib/core/design_system/atoms/app_bottom_bar.dart` (or wherever AppBottomBar lives after P2 restructure)

```dart
// WHY: AppBottomBar uses BackdropFilter which is expensive
// Wrap the entire AppBottomBar build output with RepaintBoundary
@override
Widget build(BuildContext context) {
  return RepaintBoundary(
    // NOTE: Isolates blur computation from body repaints
    child: ClipRect(
      child: BackdropFilter(
        // ... existing blur + content
      ),
    ),
  );
}
```

#### Step 5.2.3: Add RepaintBoundary to AppGlassCard

**File**: `lib/core/design_system/surfaces/app_glass_card.dart` (or wherever after P2 restructure)

```dart
// WHY: AppGlassCard uses BackdropFilter — expensive repaint
@override
Widget build(BuildContext context) {
  return RepaintBoundary(
    // NOTE: Isolates glass blur from surrounding repaints
    child: ClipRRect(
      // ... existing blur + gradient border
    ),
  );
}
```

#### Step 5.2.4: Add RepaintBoundary to animated widgets

Wrap widgets using `AnimationController` or `AnimatedBuilder`:
- `DashboardStatCard` (animated counter)
- Any widget using `FieldGuideMotion` with `AnimatedContainer`

```dart
// WHY: Animation-driven repaints should not propagate to static siblings
return RepaintBoundary(
  child: AnimatedBuilder(
    animation: _controller,
    builder: (context, child) {
      // ...
    },
  ),
);
```

#### Step 5.2.5: Add RepaintBoundary to ScaffoldWithNavBar body vs navigation

**File**: `lib/core/router/scaffold_with_nav_bar.dart`

```dart
// WHY: Body content changes should not repaint the navigation bar
body: RepaintBoundary(
  // NOTE: Isolates body repaints from nav bar
  child: Consumer2<SyncProvider, AppConfigProvider>(
    // ... existing banner + body logic
  ),
),
bottomNavigationBar: RepaintBoundary(
  // NOTE: Isolates nav bar repaints from body
  child: Column(
    mainAxisSize: MainAxisSize.min,
    children: [
      const ExtractionBanner(),
      NavigationBar(
        // ... existing nav
      ),
    ],
  ),
),
```

#### Step 5.2.6: Verify RepaintBoundary placement

```
pwsh -Command "flutter analyze"
```

Expected: 0 errors across entire codebase.

---

### Sub-phase 5.3: Re-profile and Document

**Agent**: `general-purpose`

#### Step 5.3.1: Re-profile all 5 target screens

Run profile mode again. Navigate to same screens. Record post-optimization frame times.

#### Step 5.3.2: Update baseline document with results

Update `.claude/plans/performance-baseline-p5.md` with "After" columns. Document improvements. Store final frame time baselines in `test/performance/baseline_frame_times.json` for CI regression detection before the temporary file is deleted in Step 5.3.4.

#### Step 5.3.3: Address any remaining >16ms frames

If any screens still show >16ms frames after RepaintBoundary pass:
1. Check for unnecessary `Selector` that returns complex objects (should return primitives)
2. Check for `setState` calls that rebuild too broadly
3. Consider `const` constructors on static sub-widgets
4. Consider `AutomaticKeepAliveClientMixin` for tab views

#### Step 5.3.3b: Create performance regression CI step

<!-- FROM SPEC (Section 8): "Performance tests -- Baseline frame times, fail on regression" -->

Add a step to `.github/workflows/quality-gate.yml` that reads `test/performance/baseline_frame_times.json` and fails the build if any screen's worst frame time exceeds a configurable threshold (default: 20ms). This is a static check against committed baselines, not a live profiling run. If the baseline file is missing, the step should pass with a warning (baselines not yet captured).

Create `tools/check_performance_baselines.dart` -- a simple Dart script that reads the JSON, checks each screen's `worstFrame` against the threshold, and exits non-zero if any exceed it.

#### Step 5.3.4: Delete temporary baseline file

Delete `.claude/plans/performance-baseline-p5.md` — it was only for tracking during this phase.

---

## Phase 6: Polish

**Prerequisite**: Phase 5 complete. All screens performant, decomposed, tokenized.

---

### Sub-phase 6.1: Desktop Hover + Focus States

**Agent**: `code-fixer-agent`

#### Step 6.1.1: Add hover states to AppButton

**File**: `lib/core/design_system/atoms/app_button.dart` (or actual path after P2)

```dart
// FROM SPEC: Desktop hover states + focus indicators on all interactive components
// WHY: Desktop users expect visual feedback on hover

// In AppButton, add MaterialStateProperty-based styling:
style: ButtonStyle(
  overlayColor: WidgetStateProperty.resolveWith((states) {
    if (states.contains(WidgetState.hovered)) {
      return cs.primary.withValues(alpha: 0.08);
    }
    if (states.contains(WidgetState.focused)) {
      return cs.primary.withValues(alpha: 0.12);
    }
    return null;
  }),
  // NOTE: Focus indicator via side property
  side: WidgetStateProperty.resolveWith((states) {
    if (states.contains(WidgetState.focused)) {
      return BorderSide(color: cs.primary, width: 2.0);
    }
    return null;
  }),
),
```

#### Step 6.1.2: Add hover states to AppListTile

**File**: `lib/core/design_system/molecules/app_list_tile.dart` (or actual path)

```dart
// WHY: List tiles should highlight on hover for desktop UX
// Wrap content with Material + InkWell that responds to hover:
return Material(
  color: Colors.transparent,
  child: InkWell(
    onTap: onTap,
    hoverColor: cs.surfaceContainerHighest.withValues(alpha: 0.5),
    focusColor: cs.primary.withValues(alpha: 0.08),
    borderRadius: BorderRadius.circular(radii.md),
    child: // ... existing content
  ),
);
```

#### Step 6.1.3: Add hover states to AppSectionCard

**File**: `lib/core/design_system/surfaces/app_section_card.dart` (or actual path)

Add hover elevation change and subtle color shift when `onTap` is non-null.

#### Step 6.1.4: Add hover states to AppChip

**File**: `lib/core/design_system/atoms/app_chip.dart` (or actual path)

Chips should show hover highlight on desktop.

#### Step 6.1.4b: Add hover states to AppGlassCard

**File**: `lib/core/design_system/surfaces/app_glass_card.dart` (or actual path)

When `onTap` is non-null, add hover state that subtly increases opacity or adds a border glow. Use `MouseRegion` + `AnimatedContainer` with `FieldGuideMotion.of(context).fast`.

#### Step 6.1.4c: Add hover states to AppToggle

**File**: `lib/core/design_system/atoms/app_toggle.dart` (or actual path)

Add hover highlight and focus ring for desktop keyboard navigation. Use `FocusableActionDetector` if not already using Material's built-in focus handling.

<!-- FROM SPEC: Desktop hover states + focus indicators on ALL interactive components -->

#### Step 6.1.4d: Add hover + focus to remaining interactive molecules

Add hover highlight and focus ring to remaining interactive molecules: AppTextField, AppCounterField, AppSearchBar, AppDropdown, AppDatePicker, AppTabBar. Use `WidgetStateProperty` pattern from Step 6.1.1.

#### Step 6.1.4e: Verify all interactive components have hover + focus

Audit: [atoms] AppButton, AppChip, AppToggle; [molecules] AppTextField, AppCounterField, AppSearchBar, AppDropdown, AppDatePicker, AppTabBar, AppListTile; [organisms] AppSectionCard, AppGlassCard (when tappable). Fix gaps.

#### Step 6.1.5: Add focus indicators globally via ThemeData

In `AppTheme.build()`, ensure focus-related properties are set:

```dart
// In the AppTheme.build method:
focusColor: colors.gradientStart.withValues(alpha: 0.12),
hoverColor: colorScheme.onSurface.withValues(alpha: 0.04),
// WHY: Global fallback for any widget that doesn't have explicit hover/focus
```

#### Step 6.1.6: Verify hover + focus states

```
pwsh -Command "flutter analyze"
```

Expected: 0 errors.

---

### Sub-phase 6.2: Widgetbook -- Design System Use Cases

**Agent**: `code-fixer-agent`

<!-- Phase 2 already created widgetbook skeleton. Phase 6 adds use cases only.
     Update main.dart WidgetbookFolder children to register use case components below.
     NOTE: Spec scope is "all design system components + key feature widgets".
     This sub-phase covers design system components. Key feature widget use cases
     (e.g., EntryCard, ProjectCard, ContractorRow) are deferred post-overhaul. -->

#### Step 6.2.1: Add use cases for Atoms layer

Create individual use case files in `widgetbook/lib/atoms/`:

```dart
// widgetbook/lib/atoms/app_button_use_case.dart
// FROM SPEC: Widgetbook catalog covering all design system components
// Each component gets knobs for all configurable properties

WidgetbookComponent(
  name: 'AppButton',
  useCases: [
    WidgetbookUseCase(
      name: 'Primary',
      builder: (context) => AppButton.primary(
        label: context.knobs.string(label: 'Label', initialValue: 'Submit'),
        icon: Icons.check,
        onPressed: context.knobs.boolean(label: 'Enabled', initialValue: true)
            ? () {}
            : null,
      ),
    ),
    WidgetbookUseCase(
      name: 'Secondary',
      builder: (context) => AppButton.secondary(
        label: context.knobs.string(label: 'Label', initialValue: 'Cancel'),
        onPressed: () {},
      ),
    ),
    WidgetbookUseCase(
      name: 'Ghost',
      builder: (context) => AppButton.ghost(
        label: context.knobs.string(label: 'Label', initialValue: 'Skip'),
        onPressed: () {},
      ),
    ),
    WidgetbookUseCase(
      name: 'Danger',
      builder: (context) => AppButton.danger(
        label: context.knobs.string(label: 'Label', initialValue: 'Delete'),
        onPressed: () {},
      ),
    ),
  ],
),
```

#### Step 6.2.2: Add use cases for Molecules, Organisms, Surfaces, Feedback, Layout

Create use case files for each remaining layer. Each component gets at least one use case with relevant knobs.

#### Step 6.2.3: Verify Widgetbook builds

```
pwsh -Command "cd widgetbook; flutter pub get; flutter analyze"
```

Expected: Widgetbook compiles and runs without errors.

#### Step 6.2.4: Add Widgetbook build to CI pipeline

Update `.github/workflows/quality-gate.yml` to add a Widgetbook web build step (`cd widgetbook && flutter pub get && flutter build web`) as a PR check. This ensures Widgetbook stays buildable and catches import/compilation breakage early.

---

### Sub-phase 6.2b: Widget Tests for New Design System Components

**Agent**: `qa-testing-agent`

<!-- FROM SPEC (Section 8 - Testing): Every new component gets tests covering all variants, themes, breakpoints -->

#### Step 6.2b.1: Create widget test files for core new components

Create widget test files for the following key new components. Each test file should cover all variants, both themes (dark + light), and relevant breakpoints. NOTE: Test execution happens in CI only -- create the test files but do NOT run them locally.

Files to create:
1. `test/core/design_system/atoms/app_button_test.dart` -- test primary/secondary/ghost/danger variants, enabled/disabled states, dark/light themes
2. `test/core/design_system/atoms/app_badge_test.dart` -- test all badge types, color variants, dark/light themes
3. `test/core/design_system/layout/app_breakpoint_test.dart` -- test breakpoint detection at compact/medium/expanded/large widths using `MediaQuery` overrides
4. `test/core/design_system/layout/app_responsive_builder_test.dart` -- test that correct builder callback fires at each breakpoint
5. `test/core/design_system/layout/app_adaptive_layout_test.dart` -- test phone vs tablet vs desktop canonical layout patterns
6. `test/core/design_system/tokens/field_guide_spacing_test.dart` -- test standard/compact/comfortable density variants return correct values
7. `test/core/design_system/tokens/field_guide_motion_test.dart` -- test standard vs reduced motion variants, verify reduced durations are zero

Each test file should follow the pattern:

```dart
// test/core/design_system/atoms/app_button_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';

void main() {
  group('AppButton', () {
    for (final brightness in Brightness.values) {
      final theme = brightness == Brightness.dark
          ? AppTheme.darkTheme
          : AppTheme.lightTheme;

      testWidgets('primary variant renders in ${brightness.name} theme',
          (tester) async {
        await tester.pumpWidget(
          MaterialApp(
            theme: theme,
            home: Scaffold(
              body: AppButton.primary(
                label: 'Test',
                onPressed: () {},
              ),
            ),
          ),
        );
        expect(find.text('Test'), findsOneWidget);
      });

      // NOTE: Add tests for secondary, ghost, danger, disabled states
    }
  });
}
```

#### Step 6.2b.2: Verify widget test files compile

```
pwsh -Command "flutter analyze test/core/design_system/"
```

Expected: 0 errors across all new test files. CI will execute the tests.

#### Step 6.2b.3: Add responsive layout tests for key screens

<!-- FROM SPEC (Section 8): "Responsive tests -- Test canonical layouts at each breakpoint" -->

Create `test/core/design_system/layout/responsive_screen_layout_test.dart` testing canonical layout at each breakpoint for key screens (home, entry editor, project list). Use `MediaQuery` overrides to simulate compact/medium/expanded/large widths. Verify layout shell, density variant, content arrangement.

---

### Sub-phase 6.3: Documentation Updates

**Agent**: `general-purpose`

#### Step 6.3.1: Update .claude/CLAUDE.md

Update the project structure section, component count, and design system description:

```markdown
# Changes to .claude/CLAUDE.md:

## Project Structure — update core/ description:
# Before:
# core/       # Cross-cutting: bootstrap, config, database (v50, 36 tables), design_system (24 components), di, driver, logging, router, theme
# After:
# core/       # Cross-cutting: bootstrap, config, database (v50, 36 tables), design_system (56 components, atomic design), di, driver, logging, router, theme

## Add new section after "Data Flow":
## Design System
# ```
# lib/core/design_system/
# +-- tokens/     # FieldGuideColors, FieldGuideSpacing, FieldGuideRadii, FieldGuideMotion, FieldGuideShadows, AppColors, DesignConstants
# +-- atoms/      # AppText, AppIcon, AppChip, AppToggle, AppProgressBar, AppMiniSpinner, AppButton, AppBadge, AppDivider, AppAvatar, AppTooltip
# +-- molecules/  # AppTextField, AppSearchBar, AppDropdown, AppDatePicker, AppTabBar, AppListTile, AppCounterField, AppSectionHeader
# +-- organisms/  # AppGlassCard, AppSectionCard, AppPhotoGrid, AppInfoBanner, AppStatCard, AppActionCard, AppFormSection, AppFormSectionNav, AppFormStatusBar, AppFormFieldGroup, AppFormSummaryTile, AppFormThumbnail
# +-- surfaces/   # AppScaffold, AppBottomBar, AppBottomSheet, AppDialog, AppStickyHeader, AppDragHandle
# +-- feedback/   # AppSnackbar, AppContextualFeedback, AppBanner, AppEmptyState, AppErrorState, AppLoadingState, AppBudgetWarningChip
# +-- layout/     # AppBreakpoint, AppResponsiveBuilder, AppAdaptiveLayout, AppResponsivePadding, AppResponsiveGrid
# +-- animation/  # AppAnimatedEntrance, AppStaggeredList, AppTapFeedback, AppValueTransition
# ```
# Token access: `FieldGuideSpacing.of(context).md`, `FieldGuideRadii.of(context).lg`, etc.
# 2 themes: dark + light (high contrast removed)

## Update Gotchas:
# Add: **Density is automatic** -- selected by breakpoint, no user toggle. Widgetbook has knobs for QA.
# Add: **AppBanner replaces StaleConfigWarning + VersionBanner** -- use AppBanner compositions in scaffold_with_nav_bar.dart
# Update custom lint count from 52 to 62 (10 new rules)

## Update Custom Lint Package:
# `fg_lint_packages/field_guide_lints/` -- 62 rules in 4 categories: architecture (33), data safety (11), sync integrity (10), test quality (8)
```

#### Step 6.3.2: Update .claude/docs/directory-reference.md

Add the new `design_system/` subdirectory structure with all folders and files.

#### Step 6.3.3: Update architecture guide

**File**: `.claude/skills/implement/references/architecture-guide.md`

Add token system documentation, responsive layout patterns, and updated component inventory.

#### Step 6.3.4: Update worker-rules.md

**File**: `.claude/skills/implement/references/worker-rules.md`

Add rules for:
- Always use `FieldGuideSpacing.of(context)` instead of `DesignConstants.space*`
- Always use `AppButton.*` instead of raw Flutter buttons
- Always use `AppBanner` instead of raw `MaterialBanner`
- Always wrap list items with `RepaintBoundary`
- Screen files must stay under 300 lines

#### Step 6.3.5: Update reviewer-rules.md

**File**: `.claude/skills/implement/references/reviewer-rules.md`

Add review checks for:
- Token usage (no magic numbers in presentation)
- Component compliance (no raw widgets where design system wrapper exists)
- File size limits (300 lines)
- RepaintBoundary on list items and expensive widgets

#### Step 6.3.6: Update .claude/rules/architecture.md

Add new anti-patterns to the "Key Anti-Patterns" section:

```markdown
# Add to Key Anti-Patterns:
- No raw `ElevatedButton`, `TextButton`, `OutlinedButton`, `IconButton` -- use `AppButton.*`
- No raw `Divider` -- use `AppDivider`
- No raw `Tooltip` -- use `AppTooltip`
- No raw `DropdownButton` -- use `AppDropdown`
- No raw `MaterialBanner` -- use `AppBanner`
- No hardcoded `EdgeInsets.*(N)` with numeric literals -- use `FieldGuideSpacing.of(context).*`
- No hardcoded `BorderRadius.circular(N)` with numeric literals -- use `FieldGuideRadii.of(context).*`
- No hardcoded `Duration(milliseconds: N)` in presentation -- use `FieldGuideMotion.of(context).*`
- No `Navigator.push`/`Navigator.pop` -- use GoRouter
```

---

### Sub-phase 6.4: HTTP Driver + Logging Updates

**Agent**: `code-fixer-agent`

#### Step 6.4.1: Add TestingKeys for new design system components

**File**: `lib/shared/testing_keys/common_keys.dart` (or create `design_system_keys.dart`)

```dart
// lib/shared/testing_keys/design_system_keys.dart
import 'package:flutter/material.dart';

// FROM SPEC: TestingKeys for all new design system components
class DesignSystemKeys {
  DesignSystemKeys._();

  // Buttons
  static const Key primaryButton = Key('ds_primary_button');
  static const Key secondaryButton = Key('ds_secondary_button');
  static const Key ghostButton = Key('ds_ghost_button');
  static const Key dangerButton = Key('ds_danger_button');

  // Banners
  static const Key appBanner = Key('ds_app_banner');
  static const Key appBannerDismiss = Key('ds_app_banner_dismiss');
  static const Key appBannerAction = Key('ds_app_banner_action');

  // Layout
  static const Key navigationRail = Key('ds_navigation_rail');
  static const Key responsiveBuilder = Key('ds_responsive_builder');

  // Form organisms
  static const Key formSection = Key('ds_form_section');
  static const Key formStatusBar = Key('ds_form_status_bar');
  static const Key formSectionNav = Key('ds_form_section_nav');
}
```

Then add `export 'design_system_keys.dart';` to `lib/shared/testing_keys/testing_keys.dart`.

#### Step 6.4.2: Update HTTP driver screen test flows

**File**: `lib/core/driver/routes/` (relevant route files)

Update any test flows that reference decomposed screen structures. For example, if driver tests tap on specific widgets that were renamed during decomposition, update the key references.

#### Step 6.4.3: Add responsive testing endpoints to driver

```dart
// WHY: HTTP driver needs endpoints to test responsive behavior
// Add to driver route registration:

// GET /diagnostics/breakpoint — returns current breakpoint info
// GET /diagnostics/navigation-mode — returns 'bottom_nav' or 'rail'
// GET /diagnostics/density — returns current density mode

// NOTE: These read from the responsive layout state to verify
// correct breakpoint/density in automated tests

// NOTE: These endpoints MUST be registered within `DriverServer._handleRequest`
// which is gated by `kReleaseMode || kProfileMode`. They are never reachable in production.
```

#### Step 6.4.3b: Add animation-settling utility to driver

<!-- FROM SPEC: Animation-aware waits for staggered entrances -->

Add a utility method to the driver that waits for staggered entrance animations to complete before asserting widget state. This prevents flaky driver tests caused by `AppStaggeredList` or `AppAnimatedEntrance` mid-animation.

```dart
// In lib/core/driver/ -- add helper or endpoint:
// POST /wait/animations-settled -- pumps frames until no pending animations remain
// WHY: AppStaggeredList uses per-item delays; driver must wait for all items to appear
```

#### Step 6.4.4: Create Logger.ui category and add UI lifecycle logging

```dart
// WHY: New logging category for UI component lifecycle events
// In lib/core/logging/logger.dart — create Logger.ui if it doesn't exist (follow Logger.sync pattern):

// Log responsive breakpoint changes:
Logger.ui('Breakpoint changed: compact -> medium');

// Log density switches:
Logger.ui('Density switched: standard -> compact');

// Log animation overrides:
Logger.ui('Motion reduced: accessibility setting detected');

// NOTE: UI lifecycle logs must contain only design system state (breakpoint, density, motion).
// Do NOT log route paths or user/project context in Logger.ui calls.
```

#### Step 6.4.4b: Update debug server with `/ui-diagnostics` endpoint

<!-- FROM SPEC (Section 8): "Debug server UI diagnostics -- Breakpoint, density, theme, animation state" -->

**File**: `tools/debug-server/server.js`

Add a `/ui-diagnostics` endpoint that returns current breakpoint, density, theme mode, and animation state. The app should POST this data to the debug server whenever `Logger.ui` fires a breakpoint/density/motion change, allowing the debug server UI to display live design system state.

#### Step 6.4.5: Verify driver + logging updates

```
pwsh -Command "flutter analyze lib/core/driver/ lib/core/logging/ lib/shared/testing_keys/"
```

Expected: 0 errors.

---

### Sub-phase 6.4c: Integration Test Updates

**Agent**: `qa-testing-agent`

<!-- FROM SPEC (Section 8): "Integration tests -- Update for decomposed widget structure" -->

#### Step 6.4c.1: Audit integration tests for broken finders

Audit all files in `integration_test/` for widget finders that reference:
1. Widgets renamed or decomposed in Phase 4 (e.g., old screen-level keys that now live in extracted sub-widgets)
2. Keys that moved from `shared/testing_keys/common_keys.dart` to `design_system_keys.dart`
3. Widget types that changed (e.g., `ElevatedButton` -> `AppButton`)

Update finders and key references to match the new decomposed structure.

#### Step 6.4c.2: Verify integration test files compile

```
pwsh -Command "flutter analyze integration_test/"
```

Expected: 0 errors. Integration test execution is handled by CI/driver runs.

---

### Sub-phase 6.5: Golden Test Updates

**Agent**: `qa-testing-agent`

#### Step 6.5.1: Delete high contrast golden baselines

Delete `test/golden/themes/high_contrast_theme_test.dart` entirely (if not already deleted in P1).

Remove HC variants from golden test files:
- `test/golden/components/dashboard_widgets_test.dart`
- `test/golden/components/form_fields_test.dart`
- `test/golden/components/quantity_cards_test.dart`
- `test/golden/states/empty_state_test.dart`
- `test/golden/states/error_state_test.dart`
- `test/golden/states/loading_state_test.dart`
- `test/golden/widgets/confirmation_dialog_test.dart`
- `test/golden/widgets/entry_card_test.dart`
- `test/golden/widgets/project_card_test.dart`

```dart
// WHY: HC theme removed — golden tests should only cover dark + light
// In each file, find and remove test cases like:
//   testGolden('widget - high contrast', ...);
// or blocks gated by AppThemeMode.highContrast
```

#### Step 6.5.2: Regenerate golden baselines for updated components

NOTE: Golden baseline regeneration is handled by CI (using the `--update-goldens` flag). Do NOT run tests locally. Verify only via `flutter analyze`.

This regenerates all `.png` baselines to reflect the tokenized, decomposed UI.

#### Step 6.5.3: Add golden baselines for new design system components

Create new golden test files for key new components:

```dart
// test/golden/design_system/app_button_test.dart
// FROM SPEC: Add baselines for new components across dark/light and phone/tablet

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/core/design_system/design_system.dart';
import '../test_helpers.dart';

void main() {
  testWidgetInAllThemes('AppButton primary - dark/light', (tester, theme) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: theme,
        home: Scaffold(
          body: Center(
            child: AppButton.primary(
              label: 'Submit',
              icon: Icons.check,
              onPressed: () {},
            ),
          ),
        ),
      ),
    );
    await expectLater(
      find.byType(Scaffold),
      matchesGoldenFile('goldens/app_button_primary_${theme.brightness.name}.png'),
    );
  });

  // NOTE: Add similar tests for secondary, ghost, danger variants
  // Add tests for AppBanner, AppSearchBar, AppDivider, AppBadge
}
```

#### Step 6.5.4: Verify golden tests pass

NOTE: Golden test execution is handled by CI. Do NOT run tests locally. Run only static analysis:

```
pwsh -Command "flutter analyze test/golden/"
```

Expected: All golden test files pass static analysis. CI will verify baselines match.

---

### Sub-phase 6.6: Flip Lint Rules to Error Severity

**Agent**: `code-fixer-agent`

#### Step 6.6.1: Verify zero violations at WARNING severity

Before flipping to ERROR, confirm zero violations exist:

```
pwsh -Command "flutter analyze 2>&1 | Select-String 'no_raw_button|no_raw_divider|no_raw_tooltip|no_raw_dropdown|no_hardcoded_spacing|no_hardcoded_radius|no_hardcoded_duration|no_direct_snackbar|prefer_design_system_banner'"
```

Expected: 0 matches. If any violations remain, fix them first.

<!-- NOTE: no_raw_navigator stays at INFO severity per spec (Section 5 lint table) -- do NOT include in verification or flip.
     no_direct_snackbar was extended in P0 to cover raw snackbar usage (merged no_raw_snackbar into it) -- include in both verification and flip. -->

#### Step 6.6.2: Update all 9 lint rules to ERROR severity

For each of the 9 lint rules in `fg_lint_packages/field_guide_lints/lib/architecture/rules/`:
<!-- NOTE: no_raw_snackbar is NOT a separate file -- P0 extended existing no_direct_snackbar instead.
     no_raw_navigator stays at INFO per spec -- not included in flip list.
     no_direct_snackbar IS included because it was extended to cover raw snackbar usage (spec: "warning -> error"). -->

```dart
// Change in each rule file:
// Before:
static const _code = LintCode(
  name: 'no_raw_button',
  problemMessage: '...',
  correctionMessage: '...',
  errorSeverity: ErrorSeverity.WARNING, // WHY: was WARNING during migration
);

// After:
static const _code = LintCode(
  name: 'no_raw_button',
  problemMessage: '...',
  correctionMessage: '...',
  errorSeverity: ErrorSeverity.ERROR, // FROM SPEC: flip to ERROR after zero violations confirmed
);
```

Files to update (9 rules):
1. `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_button.dart`
2. `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_divider.dart`
3. `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_tooltip.dart`
4. `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_raw_dropdown.dart`
5. `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_hardcoded_spacing.dart`
6. `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_hardcoded_radius.dart`
7. `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_hardcoded_duration.dart`
8. `fg_lint_packages/field_guide_lints/lib/architecture/rules/no_direct_snackbar.dart` <!-- extended in P0 to cover raw snackbar; flip WARNING -> ERROR per spec -->
9. `fg_lint_packages/field_guide_lints/lib/architecture/rules/prefer_design_system_banner.dart`
<!-- NOTE: no_raw_navigator stays at INFO per spec (Section 5 lint table) -- not included in flip list -->

#### Step 6.6.3: Verify zero violations at ERROR severity

```
pwsh -Command "flutter analyze"
```

Expected: 0 errors, 0 warnings. All new lint rules now enforced at ERROR level.

---

### Sub-phase 6.7: Final Cleanup Checklist

**Agent**: `general-purpose`

#### Step 6.7.1: Full analyzer pass

```
pwsh -Command "flutter analyze"
```

Expected: 0 errors, 0 warnings across entire codebase.

#### Step 6.7.2: Verify no orphaned files

Check that all moved/deleted files have been properly handled:

```dart
// Files that should be DELETED:
// - lib/shared/widgets/stale_config_warning.dart
// - lib/shared/widgets/version_banner.dart
// - lib/shared/widgets/empty_state_widget.dart (merged into AppEmptyState in P2)
// - lib/shared/widgets/confirmation_dialog.dart (merged into AppDialog in P2)
// - test/golden/themes/high_contrast_theme_test.dart

// Files that should be MOVED (originals deleted):
// - lib/core/theme/field_guide_colors.dart -> lib/core/design_system/tokens/
// - lib/core/theme/design_constants.dart -> lib/core/design_system/tokens/
// - lib/core/theme/colors.dart -> lib/core/design_system/tokens/app_colors.dart
// - lib/shared/widgets/search_bar_field.dart -> lib/core/design_system/molecules/
// - lib/shared/widgets/contextual_feedback_overlay.dart -> lib/core/design_system/feedback/
// - lib/shared/utils/snackbar_helper.dart -> lib/core/design_system/feedback/app_snackbar.dart
```

Verify none of the original files still exist at old paths.

#### Step 6.7.3: Verify barrel files reflect current exports

Check:
- `lib/core/design_system/design_system.dart` — exports all sub-barrels
- `lib/core/design_system/tokens/tokens.dart` — exports all token files
- `lib/core/design_system/atoms/atoms.dart` — exports all atoms
- `lib/core/design_system/molecules/molecules.dart` — exports all molecules
- `lib/core/design_system/organisms/organisms.dart` — exports all organisms
- `lib/core/design_system/surfaces/surfaces.dart` — exports all surfaces
- `lib/core/design_system/feedback/feedback.dart` — exports all feedback components
- `lib/core/design_system/layout/layout.dart` — exports all layout components
- `lib/core/design_system/animation/animation.dart` — exports all animation components
- `lib/shared/widgets/widgets.dart` — only exports `permission_dialog.dart`

#### Step 6.7.4: Verify all imports updated after file moves

```
pwsh -Command "flutter analyze"
```

If any "uri doesn't exist" or "undefined class" errors appear, fix the imports. The barrel re-export strategy should prevent most breakage, but verify.

#### Step 6.7.5: Verify all 11 GitHub issues addressed

| Issue | Fix Location | Status |
|-------|-------------|--------|
| #165 | project_setup_screen.dart (P4a) | Verify fixed |
| #200 | project_dashboard_screen.dart DraftsPill (P4.9) | Verify fixed |
| #202 | quantities_screen.dart search clear (P4.12.4) | Verify fixed |
| #203 | quantities_screen.dart + button workflow (P4.12.4) | Verify fixed |
| #207 | project_dashboard_screen.dart empty-state button (P4.9) | Verify fixed |
| #208 | project_dashboard_screen.dart gradient removal (P4.9) | Verify fixed |
| #209 | forms_list_screen.dart internal ID (P4.14.1) | Verify fixed |
| #233 | project_dashboard_screen.dart button consistency (P4.9) | Verify fixed |
| #238 | pay apps TextStyle violations (P4.14.2) | Verify fixed |
| Additional issues from P4a | Verify in P4a plan | Verify fixed |

#### Step 6.7.6: Final analyze confirmation

```
pwsh -Command "flutter analyze"
```

Expected: 0 errors, 0 warnings. Design system overhaul complete.
