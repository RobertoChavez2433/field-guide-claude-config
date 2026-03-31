# CodeMunch Dart Enhancement — Dependency Graph Analysis

**Date:** 2026-03-30
**Target Repo:** `C:\Users\rseba\Projects\jcodemunch-mcp`
**Current Version:** v0.2.14 (local) → v1.13.1 (upstream)

## Direct Changes

### 1. `src/jcodemunch_mcp/parser/imports.py` (549 lines upstream)
**Change type:** ADD new function + MODIFY existing functions
- Add `_DART_IMPORT` regex patterns (import, export, part, part of, conditional, deferred)
- Add `_extract_dart_imports()` function
- Register `"dart": _extract_dart_imports` in `_LANGUAGE_EXTRACTORS` dict (line ~296)
- Add `(".dart",)` to `_ALL_EXTENSIONS` (line ~330)
- Modify `resolve_specifier()` to handle `package:` URIs:
  - New `_dart_package_cache` for pubspec.yaml package name
  - New `_load_dart_package_name()` helper
  - `package:<own_name>/path` → `lib/path`
  - Skip `dart:*` (stdlib)
  - Skip external `package:*` (not in index)

### 2. `src/jcodemunch_mcp/parser/languages.py` (1513 lines upstream)
**Change type:** MODIFY `DART_SPEC` constant (lines 421-448 upstream)
- `class_definition` → `class_declaration` (5 occurrences: symbol_node_types, name_fields, container_node_types)
- Add to `symbol_node_types`:
  - `constructor_signature` → `"method"`
  - `constant_constructor_signature` → `"method"`
  - `factory_constructor_signature` → `"method"`
  - `redirecting_factory_constructor_signature` → `"method"`
  - `extension_type_declaration` → `"class"`
  - `setter_signature` → `"method"` (currently only getter is captured via method_signature)
- Add to `constant_patterns`: top-level const/final declarations
- Add to `container_node_types`: `extension_type_declaration`

### 3. `src/jcodemunch_mcp/parser/extractor.py` (6624 lines upstream)
**Change type:** MODIFY parser loading + ADD constructor name extraction
- Add `try/except` import for `tree_sitter_dart.language`
- Create `_DART_PARSER` singleton at module level
- Modify `parse_file()`: if dart and `_DART_PARSER` available, use it instead of language-pack
- Add constructor name extraction in `_extract_name()`:
  - `constructor_signature` → `ClassName` or `ClassName.namedConstructor`
  - `factory_constructor_signature` → similar
  - `constant_constructor_signature` → similar
- Add Dart constant extraction logic (top-level `const`/`final` with type)

### 4. `src/jcodemunch_mcp/tools/get_class_hierarchy.py` (130 lines upstream)
**Change type:** MODIFY regex patterns
- Add `_WITH_RE` regex: `\bwith\s+([\w$][\w$,\s]*?)(?=\s+implements|\s*[{(<]|$)`
- Modify `_parse_bases()` to extract `with` clause names
- These are treated as ancestors (mixin application = inheritance for hierarchy purposes)

### 5. `pyproject.toml`
**Change type:** MODIFY dependencies
- Add: `"tree-sitter-dart @ git+https://github.com/nielsenko/tree-sitter-dart.git"`

### 6. `tests/fixtures/dart/sample.dart`
**Change type:** REWRITE — expand from 40 lines to comprehensive fixture
- Import statements (all forms: package, relative, dart:, show/hide, as, deferred, conditional)
- Export statements (with show/hide)
- Part / part of directives
- Constructors (default, named, factory, const, redirecting)
- Top-level constants (const, final)
- Classes with extends/with/implements
- Extension types (Dart 3.3+)
- Annotations (@override, @deprecated, @visibleForTesting)
- Barrel file pattern (export-only file, separate fixture)
- Generated code pattern (.g.dart, separate fixture)

### 7. `tests/test_languages.py`
**Change type:** MODIFY — expand `test_parse_dart()`
- Assert constructors extracted
- Assert constants extracted
- Assert correct node types after grammar switch

### 8. New test file: `tests/test_dart_imports.py`
**Change type:** CREATE
- Test `_extract_dart_imports()` with all import forms
- Test `resolve_specifier()` with `package:` URIs
- Test part/part of resolution
- Test show/hide combinator parsing
- Test barrel file detection
- Test generated code filtering
- Test class hierarchy with `with` clause

### 9. `LANGUAGE_SUPPORT.md`
**Change type:** MODIFY — expand Dart section
- Document all supported symbol types including new ones
- Document import graph support
- Document grammar version (nielsenko, Dart 3.11)
- Document known limitations

### 10. New file: `DART_SUPPORT.md` (optional, or section in README)
**Change type:** CREATE
- Package resolution explained
- Flutter project configuration
- Tool examples with Dart output
- File watcher setup

## Dependent Files (affected by changes, not directly modified)

| File | Dependency | Impact |
|------|-----------|--------|
| `src/jcodemunch_mcp/tools/_indexing_pipeline.py` | Calls `extract_imports()` | Will automatically pick up Dart imports — no changes needed |
| `src/jcodemunch_mcp/tools/find_importers.py` | Uses `resolve_specifier()` | Will work for Dart after resolver changes — no changes needed |
| `src/jcodemunch_mcp/tools/get_dependency_graph.py` | Uses `resolve_specifier()` | Same — no changes needed |
| `src/jcodemunch_mcp/tools/get_blast_radius.py` | Uses `resolve_specifier()` + symbol lookup | Same — no changes needed |
| `src/jcodemunch_mcp/tools/find_references.py` | Uses import graph | Same — no changes needed |
| `src/jcodemunch_mcp/tools/check_references.py` | Uses import graph | Same — no changes needed |
| `src/jcodemunch_mcp/tools/get_related_symbols.py` | Uses import graph | Same — no changes needed |
| `src/jcodemunch_mcp/storage/index_store.py` | Stores `imports` dict | Already has `file_imports` field (v1.3.0+) — no changes needed |
| `src/jcodemunch_mcp/watcher.py` | Triggers incremental re-index | Language-agnostic — works for Dart automatically |

## Test Files

| Test | Purpose |
|------|---------|
| `tests/test_languages.py` | Existing — expand for Dart |
| `tests/test_dart_imports.py` | New — comprehensive Dart import tests |
| `tests/fixtures/dart/sample.dart` | Existing — expand |
| `tests/fixtures/dart/sample_barrel.dart` | New — barrel/export file fixture |
| `tests/fixtures/dart/sample_part.dart` | New — part file fixture |
| `tests/fixtures/dart/sample.g.dart` | New — generated code fixture |

## Data Flow

```
Dart file saved
  → watcher.py detects change
  → _indexing_pipeline.py:parse_immediate()
    → extractor.py:parse_file() [uses nielsenko grammar via _DART_PARSER]
      → languages.py:DART_SPEC [updated node types]
      → Returns Symbol[] (including constructors, constants)
    → imports.py:extract_imports() [NEW: _extract_dart_imports]
      → Returns import edges [{specifier, names}]
    → Stored in index (symbols + imports)
  → Tools query the index:
    → find_importers → imports.py:resolve_specifier() [NEW: package: resolution]
    → get_dependency_graph → same resolver
    → get_blast_radius → resolver + symbol name matching
    → get_class_hierarchy → hierarchy regex [NEW: with clause]
```

## Blast Radius Summary

- **Direct changes:** 10 files (6 modify, 2 create, 2 rewrite)
- **Dependent (auto-benefit):** 9 files (no changes needed)
- **Test files:** 6 files (2 modify, 4 create)
- **Risk:** LOW — all changes are additive (new language support), no breaking changes to other languages
- **Grammar swap risk:** LOW — graceful fallback via try/except, only 1 node type name change
