# CodeMunch Dart Enhancement Spec

**Date:** 2026-03-30
**Status:** Approved (conversation-derived)
**Scope:** Local fork of jcodemunch-mcp at `C:\Users\rseba\Projects\jcodemunch-mcp`

## Goal

Bring Dart to first-class status in jcodemunch-mcp — matching or exceeding the support level of Python/JS/TS/Go/Rust/C#. This means full import graph, dependency tracking, class hierarchy, comprehensive symbol extraction, a more robust grammar, and real-time file watching. The result is an extensive local tool that provides cheap, direct context to AI agents working on Dart/Flutter codebases.

## Current State

- **Local clone:** v0.2.14 (11 tools, no import infrastructure)
- **Upstream:** v1.13.1 (37 tools, full import graph for 21 languages — Dart NOT included)
- **Local has zero custom commits** — clean fast-forward possible
- **Dart symbol extraction:** Partial — functions, classes, mixins, extensions, methods, getters, enums, type aliases
- **Missing for Dart:** Import graph, constructors, constants, part/part of, class hierarchy (extends/with/implements), barrel files, show/hide combinators, annotation awareness, generated code handling, extension type awareness
- **File watcher:** Already exists upstream (897 lines, language-agnostic) — Dart gets it for free after pull
- **Grammar:** Currently uses UserNobody14/tree-sitter-dart (less robust, parse failures on some files); nielsenko/tree-sitter-dart achieves 100% parse success on Dart corpus

## Requirements

### R1: Sync with Upstream
- Fast-forward local clone from v0.2.14 to latest upstream (v1.13.1+)
- Verify all existing tools work after update
- Re-install/activate the updated MCP server

### R2: Dart Import Extractor (Tier 1 — Critical)
Add `_extract_dart_imports()` to `src/jcodemunch_mcp/parser/imports.py`:
- `import 'package:foo/bar.dart';`
- `import '../relative.dart';`
- `import 'dart:async';`
- `export 'package:foo/bar.dart';`
- `export 'bar.dart' show Foo, Bar;`
- `import 'package:foo/bar.dart' as prefix;`
- `import 'package:foo/bar.dart' show A hide B;`
- `part 'file.freezed.dart';`
- `part of 'library.dart';`
- Conditional imports: `import 'stub.dart' if (dart.library.io) 'real.dart';`
- Deferred imports: `import 'package:foo/bar.dart' deferred as bar;`

Register `"dart": _extract_dart_imports` in `_LANGUAGE_EXTRACTORS`.

### R3: Package URI Resolution (Tier 1 — Critical)
Extend `resolve_specifier()` in `imports.py`:
- Read `pubspec.yaml` to get project package name
- `package:<own_package>/path.dart` -> `lib/path.dart`
- `dart:*` -> skip (stdlib, unresolvable)
- External `package:*` -> skip (not in index)
- Relative imports -> existing logic works, but add `.dart` to `_ALL_EXTENSIONS`
- `part`/`part of` -> resolve relative to declaring file

### R4: Constructor Extraction (Tier 1)
Add to `DART_SPEC.symbol_node_types`:
- `constructor_signature` -> `"method"`
- `constant_constructor_signature` -> `"method"`
- `factory_constructor_signature` -> `"method"`
- `redirecting_factory_constructor_signature` -> `"method"`

Add corresponding name extraction logic in `extractor.py`.

### R5: Top-Level Constants (Tier 1)
Add `constant_patterns` to `DART_SPEC` for top-level `const` and `final` declarations.

### R6: Class Hierarchy — Mixin Support (Tier 2)
Add `with` clause regex to `get_class_hierarchy.py`:
- Current regex handles `extends` and `implements` but NOT `with`
- Dart mixins via `with` are critical for Flutter class hierarchies (e.g., `class MyWidget extends StatelessWidget with AutomaticKeepAliveClientMixin`)

### R7: Barrel/Export File Handling (Tier 2)
- Files containing only `export` directives currently return empty symbols
- These should be detected as Dart files and included in the dependency graph
- At minimum: include them in import graph via their export directives

### R8: Show/Hide Combinator Parsing (Tier 2)
- Extract `show`/`hide` names into the `names` field of import edges
- `import 'foo.dart' show Bar, Baz;` -> `{"specifier": "...", "names": ["Bar", "Baz"]}`

### R9: Annotation-Aware Indexing (Tier 3)
- `@override` — method overrides parent
- `@deprecated` — avoid recommending to agents
- `@visibleForTesting` — internal API, test-only usage
- `@immutable` — class is immutable
- Store in symbol metadata/decorators field

### R10: Generated Code Filtering (Tier 3)
- `*.g.dart`, `*.freezed.dart`, `*.mocks.dart` patterns
- Option to exclude from indexing or mark as generated
- Prevents noise in search results

### R11: Extension Type Support (Tier 3)
- `extension_type_declaration` (Dart 3.3+) — add to `DART_SPEC.symbol_node_types`

### R12: Grammar Upgrade — nielsenko/tree-sitter-dart (Tier 3)
- Replace UserNobody14/tree-sitter-dart with nielsenko/tree-sitter-dart
- nielsenko grammar: 100% parse success on 4,135 real-world Dart files, supports Dart through 3.11
- Includes records, patterns, sealed classes, class modifiers, extension types, null-aware elements
- Ships with `highlights.scm`, `tags.scm`, AND `locals.scm` (scope/variable resolution)
- **Breaking:** Uses `class_declaration` instead of `class_definition` — requires updating `DART_SPEC` node type names
- Implementation approach: Either override in tree-sitter-language-pack install, fork tree-sitter-language-pack, or install nielsenko grammar separately and modify parser init code
- Investigate which approach is least disruptive during planning

### R13: Real-Time File Watching for Dart
- Upstream watcher (897 lines in `watcher.py`) is language-agnostic and already supports incremental re-indexing
- After R1 (sync with upstream), Dart files will be watched automatically
- Verify watcher correctly detects `.dart` file changes and triggers re-index
- Verify `package:` resolution works during incremental re-index (pubspec.yaml must be read)

### R14: Extension Method Type Awareness (Tier 4 — Nice to Have)
- Extract the `on` type from `extension StringExt on String { ... }`
- Include in symbol metadata so agents know what types an extension applies to

### R15: Updated Tests
- Expand `tests/fixtures/dart/sample.dart` to cover ALL new features
- Update `tests/test_languages.py` with assertions for:
  - Import extraction (all forms)
  - Constructor extraction
  - Top-level constants
  - Part/part of
  - Show/hide combinators
  - Annotations
  - Extension types
  - Grammar-specific node types (if grammar is switched)

### R16: Documentation
- Update `LANGUAGE_SUPPORT.md` with comprehensive Dart section
- Update `README.md` or add `DART_SUPPORT.md` with:
  - All supported Dart features
  - How `package:` resolution works
  - How to configure for a Flutter project
  - Examples of each tool with Dart output
  - Grammar version and capabilities
  - File watcher setup for Dart projects
- Update tool docstrings where Dart-specific behavior exists

## Validation
- Index the Field Guide App codebase (`C:\Users\rseba\Projects\Field_Guide_App`)
- Verify `find_importers` returns results for key Dart files
- Verify `get_dependency_graph` traces full import chains
- Verify `get_blast_radius` identifies affected files when changing a symbol
- Verify `get_class_hierarchy` resolves mixin chains (extends + with + implements)
- Verify barrel files appear in dependency graph
- Verify constructors appear in `get_file_outline`
- Verify file watcher triggers re-index on `.dart` file save
- Run full test suite: `pytest tests/`
- If grammar switched: verify previously-failing files now parse correctly
