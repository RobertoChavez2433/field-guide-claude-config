# Pattern: custom_lint Framework

## How We Do It
This is a NEW pattern — no existing exemplar in our codebase. The spec prescribes using Remi Rousselet's `custom_lint` package which provides VS Code squiggles + CLI analysis for custom rules.

## Package Structure (from spec)
```
fg_lint_packages/
└── field_guide_lints/
    ├── pubspec.yaml           ← depends on custom_lint_builder, analyzer
    ├── analysis_options.yaml
    ├── lib/
    │   ├── field_guide_lints.dart         ← plugin entry, registers all rules
    │   ├── architecture/
    │   │   ├── rules/                     ← individual rule files
    │   │   └── architecture_rules.dart    ← barrel export
    │   ├── data_safety/
    │   │   ├── rules/
    │   │   └── data_safety_rules.dart
    │   ├── sync_integrity/
    │   │   ├── rules/
    │   │   └── sync_integrity_rules.dart
    │   └── test_quality/
    │       ├── rules/
    │       └── test_quality_rules.dart
    └── test/                              ← tests for the lint rules themselves
```

## Key Integration Points
1. **App pubspec.yaml**: Add `custom_lint` to dev_dependencies + path dependency to `fg_lint_packages/field_guide_lints`
2. **App analysis_options.yaml**: Add `analyzer: plugins: [custom_lint]`
3. **Pre-commit hook**: Run `dart run custom_lint` as a check
4. **CI workflow**: Run `dart run custom_lint` in analyze-and-test job

## Rule Severity Mapping
- ERROR → hard blocks commit and CI
- WARNING → hard blocks commit and CI (clean slate — all warnings must be zero)
- INFO → does not block (informational only)

## Rule Counts by Package
| Package | Rules | Key Focus |
|---------|-------|-----------|
| Architecture | 17 | DI, layering, color system, file size, imports |
| Data Safety | 12 | Soft-delete, mounted checks, nullable guards, schema consistency |
| Sync Integrity | 9 | ConflictAlgorithm, change_log, sync_control, RLS |
| Test Quality | 8 | TestingKeys, hardcoded delays, skip annotations, stale imports |
| **Total** | **46** | |

## Dependencies for Lint Package
```yaml
# fg_lint_packages/field_guide_lints/pubspec.yaml
dependencies:
  custom_lint_builder: ^0.7.0
  analyzer: ^6.0.0
  analyzer_plugin: ^0.11.0
```

## No Existing Exemplar
This pattern does not exist in the codebase yet. The plan writer should reference:
- custom_lint documentation: https://pub.dev/packages/custom_lint
- custom_lint_builder: https://pub.dev/packages/custom_lint_builder
- Example rules in the custom_lint repo
