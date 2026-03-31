# CodeMunch Dart Enhancement — Plan Review (Round 1)

**Date:** 2026-03-30
**Plan:** `.claude/plans/2026-03-30-codemunch-dart-enhancement.md`

## Reviewers & Verdicts

| Reviewer | Verdict | Summary |
|----------|---------|---------|
| Code Review (Opus) | APPROVE w/conditions | 2 CRITICAL, 3 HIGH, 5 MEDIUM, 4 LOW |
| Security (Opus) | APPROVE | 0 CRITICAL, 0 HIGH, 1 MEDIUM, 3 LOW |
| Completeness (Opus) | INCOMPLETE | 5 significant gaps |

## Critical Findings (Must Fix)

1. **Regex doesn't handle conditional imports** — `import 'a.dart' if (dart.library.io) 'b.dart'` breaks the main regex. Need separate `_DART_CONDITIONAL_IMPORT_RE`.
2. **Regex doesn't handle show+hide combo** — `show A hide B` captures `hide` as a name. Need post-processing to split on `hide` keyword.

## High Findings (Should Fix)

3. **Validation phase missing** — Only 1/10 spec validation criteria covered. No `find_importers`/`get_dependency_graph`/`get_blast_radius` tool-level tests. No Field Guide App indexing.
4. **Barrel file fixture missing** — Analysis mentions `sample_barrel.dart` but plan never creates it.
5. **`_EXTENDS_RE` fix buried in note** — Not a numbered step, implementing agent could miss it.

## Medium Findings

6. **Path traversal defense gap** (Security M1) — `_resolve_dart_package_import()` lacks `normpath` defense-in-depth.
7. **R3 pubspec.yaml not read** — Stubbed `_find_pubspec_package_name()` is dead code (YAGNI, remove).
8. **R9 annotation indexing** — Verification only, no implementation fallback.
9. **Constant extraction may capture class fields** — `initialized_variable_definition` should be in `constant_patterns` only, not `symbol_node_types`.
10. **Missing part/part-of test** with non-generated files.
11. **R16 documentation gaps** — Flutter config guide, tool examples, watcher docs, docstrings.

## Low Findings

12. **Pin tree-sitter-dart** to commit hash (Security L2).
13. **Theoretical ReDoS** in `_WITH_RE` (Security L1).
14. **Duplicate test** — `test_extracts_part_directive` same as `test_filters_generated_code`.
15. **R14 extension `on` type** — verification only, no structured metadata.

## Remediation

All 13+ findings dispatched to sonnet implementation agent for plan fixes. Second review sweep will follow.
