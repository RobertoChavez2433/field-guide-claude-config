# CodeMunch Dart Enhancement Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Bring Dart to first-class status in jcodemunch-mcp with full import graph, dependency tracking, class hierarchy, comprehensive symbol extraction, robust grammar, and real-time file watching.
**Spec:** `.claude/specs/2026-03-30-codemunch-dart-enhancement-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-30-codemunch-dart-enhancement/`

**Architecture:** All changes target the local fork at `C:\Users\rseba\Projects\jcodemunch-mcp`. The parser layer gets a grammar upgrade (nielsenko/tree-sitter-dart), expanded DART_SPEC for new symbol types, and a new regex-based Dart import extractor. The import resolver gains package: URI support via pubspec.yaml reading. Downstream tools (dependency graph, blast radius, importers, class hierarchy) benefit automatically.
**Tech Stack:** Python 3.12+, tree-sitter, tree-sitter-dart (nielsenko), pytest, uv
**Blast Radius:** 5 direct files modified, 2 files created, 10+ dependent files auto-benefit, 3 test files touched

---

## Phase 1: Upstream Sync

### Sub-phase 1.1: Fast-Forward to Latest Upstream

**Files:**
- Modify: (all files via git pull)

**Agent**: general-purpose

#### Step 1.1.1: Add upstream remote and fast-forward

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
git remote add upstream https://github.com/jcodemunch/jcodemunch-mcp.git 2>/dev/null || true
git fetch upstream
git pull upstream main --ff-only
```

> If fast-forward fails, the local clone has diverged and needs manual resolution. The spec confirms zero custom commits, so this should succeed cleanly.

#### Step 1.1.2: Install updated dependencies

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
uv pip install -e ".[dev]"
```

#### Step 1.1.3: Verification

Run:
```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
pytest tests/ -x --timeout=60
```
Expected: All existing tests pass. This confirms the upstream sync is clean.

#### Step 1.1.4: Verify file watcher works for Dart (R13)

Run:
```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
pytest tests/ -k "watch" -x --timeout=60
```
Expected: Watcher tests pass. The watcher is language-agnostic, so Dart files will be picked up automatically once `.dart` is in the recognized extensions. No implementation needed — just confirm it works.

#### Step 1.1.5: Verify expected APIs exist post-sync

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
import inspect
from jcodemunch_mcp.parser.imports import extract_imports, resolve_specifier
from jcodemunch_mcp.parser.extractor import parse_file
from jcodemunch_mcp.tools.find_importers import find_importers
from jcodemunch_mcp.tools.get_dependency_graph import get_dependency_graph
from jcodemunch_mcp.tools.get_blast_radius import get_blast_radius
from jcodemunch_mcp.tools.get_class_hierarchy import get_class_hierarchy
from jcodemunch_mcp.tools.get_file_outline import get_file_outline
from jcodemunch_mcp.tools.index_folder import index_folder

for fn in [extract_imports, resolve_specifier, parse_file, find_importers, get_dependency_graph, get_blast_radius, get_class_hierarchy, get_file_outline, index_folder]:
    print(f'{fn.__module__}.{fn.__name__}{inspect.signature(fn)}')
"
```

Expected: All imports succeed. Review signatures and adjust Phase 6-14 calls if parameter names differ from what the plan assumes.

> **CONTINGENCY:** If any of the above imports fail, the upstream version may not have the expected modules (e.g., `imports.py`, `find_importers.py`, `get_class_hierarchy.py`). In that case:
> - Phases 6, 7 (import extraction + resolution) would need to CREATE `imports.py` from scratch rather than modify it
> - Phase 8 (class hierarchy) would need to CREATE `get_class_hierarchy.py`
> - Phases 12.3 and 14.1.2-14.1.5 (tool docstrings + tool-level validation) must be skipped
> - Check the upstream version tag and compare against v1.3.0+ which introduced import infrastructure

---

## Phase 2: Grammar Upgrade (R12)

### Sub-phase 2.1: Install nielsenko/tree-sitter-dart

**Files:**
- Modify: `pyproject.toml`

**Agent**: general-purpose

#### Step 2.1.1: Add tree-sitter-dart dependency to pyproject.toml

Find the `dependencies` list in `pyproject.toml` and add:

```
"tree-sitter-dart @ git+https://github.com/nielsenko/tree-sitter-dart.git@main",
```

Add it alongside the existing dependencies (e.g., after `tree-sitter-language-pack`).

> **Note:** Pin to a specific commit hash after verifying compatibility in Step 2.2.2.

#### Step 2.1.2: Install the new dependency

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
uv pip install -e ".[dev]"
```

#### Step 2.1.3: Verification

Run a quick Python check:
```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "from tree_sitter_dart import language as dart_language; from tree_sitter import Language; lang = Language(dart_language()); print('Grammar loaded, node_kind_count:', getattr(lang, 'node_kind_count', 'unknown'))"
```
Expected: No ImportError. Grammar loads successfully.

### Sub-phase 2.2: Add Grammar Override in Extractor

**Files:**
- Modify: `src/jcodemunch_mcp/parser/extractor.py`

**Agent**: general-purpose

#### Step 2.2.1: Add nielsenko grammar wrapper and override _parse_with_spec()

`get_parser` is imported from `tree_sitter_language_pack` — it is NOT defined locally and must not be modified. Instead:

1. Add a module-level parser instance near the top of `extractor.py`, after the imports:

```python
# WHY: nielsenko/tree-sitter-dart has better Dart 3.x support than the
# grammar bundled in tree-sitter-language-pack. Graceful fallback if not installed.
try:
    from tree_sitter_dart import language as _dart_language
    from tree_sitter import Language as _TsLanguage, Parser as _TsParser
    _NIELSENKO_DART_PARSER = _TsParser(_TsLanguage(_dart_language()))
except ImportError:
    _NIELSENKO_DART_PARSER = None
```

**Part 2:** Modify `parse_file()` to use the nielsenko parser for Dart.

In `parse_file()`, find the line where the parser is obtained for the generic path (the `else` branch that handles languages not listed in the special-case chain). It looks like:

```python
    else:
        spec = LANGUAGE_REGISTRY[language]
        symbols = _parse_with_spec(source_bytes, filename, language, spec)
```

Or it may be inline:

```python
        parser = get_parser(spec.ts_language)
        tree = parser.parse(source_bytes)
```

Replace the parser acquisition with:

```python
        # WHY: Use nielsenko grammar for Dart if available (better Dart 3.x parse success)
        if spec.ts_language == "dart" and _NIELSENKO_DART_PARSER is not None:
            parser = _NIELSENKO_DART_PARSER
        else:
            parser = get_parser(spec.ts_language)
        tree = parser.parse(source_bytes)
```

> NOTE: After the Phase 1 upstream sync, the exact location may vary. The key is finding wherever `get_parser(spec.ts_language)` is called for the Dart code path and inserting the override there. Use `grep -n 'get_parser' src/jcodemunch_mcp/parser/extractor.py` to find all call sites.

#### Step 2.2.2: Verification

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
try:
    from tree_sitter_dart import language as dart_lang
    from tree_sitter import Language, Parser
    parser = Parser(Language(dart_lang()))
    tree = parser.parse(b'class Foo {}')
    for child in tree.root_node.children:
        print('  Child:', child.type)
    print('nielsenko grammar active')
except ImportError:
    print('WARN: nielsenko grammar not installed, using language-pack fallback')
"
```
Expected: Output shows `class_declaration` (not `class_definition`), confirming nielsenko grammar is active.

#### Step 2.2.3: Pin tree-sitter-dart to verified commit

After confirming Step 2.2.2 passes, pin the dependency to the exact commit:

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
# Get the installed commit hash
COMMIT=$(cd .venv/src/tree-sitter-dart && git rev-parse HEAD)
echo "Pinning to commit: $COMMIT"
# Update pyproject.toml: replace @main with @$COMMIT
```

Update `pyproject.toml` to replace `@main` with `@<commit-hash>`, then run `uv pip install -e ".[dev]"` again to lock it.

> WHY: Pinning to a verified commit prevents silent supply chain changes if the repo is compromised or force-pushed.

---

## Phase 3: Test Fixture (Must Come Before Implementation)

### Sub-phase 3.1: Rewrite Dart Test Fixture

**Files:**
- Modify: `tests/fixtures/dart/sample.dart`

**Agent**: general-purpose

#### Step 3.1.1: Replace sample.dart with comprehensive fixture

Overwrite `tests/fixtures/dart/sample.dart` with:

```dart
// Tests: import forms (R2)
import 'dart:async';
import 'dart:convert' show json, utf8;
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kDebugMode, kIsWeb;
import 'package:flutter/services.dart' hide SystemChrome;
import 'package:provider/provider.dart' as provider;
import '../models/user.dart';
import '../models/project.dart' show Project;
import 'utils.dart';

// Tests: conditional import (R2)
import 'stub_io.dart'
    if (dart.library.io) 'real_io.dart';

// Tests: deferred import (R2)
import 'package:heavy_lib/heavy.dart' deferred as heavy;

// Tests: part/part-of (R2)
part 'sample.g.dart';
part 'sample_part.dart';

// Tests: export / barrel (R7)
export 'package:flutter/widgets.dart' show Widget, State;
export '../shared/constants.dart';

// Tests: top-level constants (R5)
/// App version constant.
const String appVersion = '1.0.0';

/// Maximum retry count.
const int maxRetries = 3;

/// Default timeout duration.
final Duration defaultTimeout = Duration(seconds: 30);

// Tests: top-level function
/// Authenticate a token.
bool authenticate(String token) {
  return token.isNotEmpty;
}

// Tests: enum (existing)
/// Status of a request.
enum Status { pending, active, done }

// Tests: type alias (existing)
/// JSON map alias.
typedef JsonMap = Map<String, dynamic>;

/// Callback alias.
typedef VoidCallback = void Function();

// Tests: annotation-aware indexing (R9)
/// User service for managing users.
@immutable
class UserService {
  // Tests: constructors (R4)
  /// Default constructor.
  const UserService(this.baseUrl);

  /// Named constructor.
  UserService.withDefaults() : baseUrl = 'https://api.example.com';

  /// Factory constructor.
  factory UserService.fromConfig(Map<String, dynamic> config) {
    return UserService(config['baseUrl'] as String);
  }

  /// Redirecting constructor.
  UserService.test() : this('https://test.example.com');

  final String baseUrl;

  /// Get user by ID.
  @visibleForTesting
  String getUser(int userId) {
    return 'user-$userId';
  }

  /// Delete a user.
  @Deprecated('Use removeUser instead')
  bool deleteUser(int userId) {
    return true;
  }

  /// Whether the service is ready.
  bool get isReady => true;

  /// Set the timeout.
  set timeout(int value) {}
}

// Tests: class hierarchy — extends + implements (R6)
/// Extended user service.
class ExtendedUserService extends UserService implements Comparable<ExtendedUserService> {
  ExtendedUserService(super.baseUrl);

  @override
  int compareTo(ExtendedUserService other) => 0;
}

// Tests: mixin + with clause (R6)
/// Scrollable behavior.
mixin Scrollable on UserService {
  /// Scroll to offset.
  void scrollTo(double offset) {}
}

/// Logging mixin.
mixin Logging {
  /// Log a message.
  void log(String message) {}
}

/// Service with mixins.
class AdvancedService extends UserService with Scrollable, Logging {
  AdvancedService(super.baseUrl);
}

// Tests: extension with on-type (R14)
/// Helpers for String manipulation.
extension StringExt on String {
  /// Whether the string is blank.
  bool get isBlank => trim().isEmpty;
}

// Tests: extension type (R11)
/// Id wrapper type.
extension type const UserId(int value) implements int {
  /// Create from string.
  factory UserId.parse(String s) => UserId(int.parse(s));

  /// Display string.
  String get display => 'User#$value';
}

// Tests: abstract class
/// Base repository.
abstract class Repository<T> {
  Future<T?> findById(String id);
  Future<List<T>> findAll();
  Future<void> save(T entity);
}

// Tests: sealed class (Dart 3)
/// Result type.
sealed class Result<T> {
  const Result();
}

/// Success result.
class Success<T> extends Result<T> {
  const Success(this.value);
  final T value;
}

/// Failure result.
class Failure<T> extends Result<T> {
  const Failure(this.error);
  final Object error;
}
```

This fixture exercises every requirement: imports (R2), constructors (R4), constants (R5), class hierarchy with `extends`/`implements`/`with` (R6), exports/barrels (R7), show/hide combinators (R8), annotations (R9), extension types (R11), extension `on` type (R14), and more.

#### Step 3.1.2: Create sample_barrel.dart fixture

Create `tests/fixtures/dart/sample_barrel.dart`:

```dart
// Barrel file — export-only, no symbols
export 'package:flutter/widgets.dart' show Widget, State;
export '../models/user.dart';
export 'utils.dart' hide InternalHelper;
```

#### Step 3.1.3: Create sample_part.dart fixture

Create `tests/fixtures/dart/sample_part.dart`:

```dart
part of 'sample.dart';

/// A method that lives in a part file.
void partMethod() {}
```

---

## Phase 4: DART_SPEC Update (R4, R5, R6, R11, R14)

### Sub-phase 4.1: Update DART_SPEC in languages.py

**Files:**
- Modify: `src/jcodemunch_mcp/parser/languages.py`

**Agent**: general-purpose

#### Step 4.1.1: Replace the DART_SPEC definition

Find the existing `DART_SPEC = LanguageSpec(` block and replace it entirely with:

```python
DART_SPEC = LanguageSpec(
    ts_language="dart",
    symbol_node_types={
        "function_signature": "function",
        # WHY: nielsenko grammar uses class_declaration, not class_definition
        "class_declaration": "class",
        "mixin_declaration": "class",
        "enum_declaration": "type",
        "extension_declaration": "class",
        # WHY: extension_type_declaration is Dart 3 — extension type Foo(int x) implements int {}
        "extension_type_declaration": "class",
        "method_signature": "method",
        "getter_signature": "method",
        # WHY: setter_signature was missing — needed for full symbol extraction
        "setter_signature": "method",
        "type_alias": "type",
        # WHY: constructors (R4) — 4 Dart constructor forms all parse to constructor_signature
        "constructor_signature": "method",
    },
    name_fields={
        "function_signature": "name",
        "class_declaration": "name",
        "enum_declaration": "name",
        "extension_declaration": "name",
        "extension_type_declaration": "name",
        "getter_signature": "name",
        "setter_signature": "name",
        "constructor_signature": "name",
    },
    param_fields={
        "function_signature": "parameters",
        "constructor_signature": "parameters",
    },
    return_type_fields={},
    docstring_strategy="preceding_comment",
    decorator_node_type="annotation",
    container_node_types=[
        "class_declaration",
        "mixin_declaration",
        "extension_declaration",
        "extension_type_declaration",
    ],
    # WHY: top-level const/final — we use initialized_variable_definition in symbol_node_types
    # but also register the pattern here for the constant detection heuristics.
    # NOTE: initialized_variable_definition should be in constant_patterns ONLY, NOT in
    # symbol_node_types at the top level, to prevent class fields from being extracted as
    # constants. The _extract_constant function already guards via parent_symbol is None.
    constant_patterns=["initialized_variable_definition"],
    type_patterns=["type_alias", "enum_declaration"],
)
```

#### Step 4.1.2: Update any references to class_definition for Dart

Search the entire `languages.py` file for any other references to `"class_definition"` that are Dart-specific and update them to `"class_declaration"`. The DART_SPEC change above handles the LanguageSpec itself, but check if there are any hardcoded references elsewhere in the file.

#### Step 4.1.3: Verification

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.parser.languages import LANGUAGE_REGISTRY
spec = LANGUAGE_REGISTRY['dart']
print('ts_language:', spec.ts_language)
print('symbol_node_types:', spec.symbol_node_types)
print('container_node_types:', spec.container_node_types)
assert 'class_declaration' in spec.symbol_node_types
assert 'constructor_signature' in spec.symbol_node_types
assert 'extension_type_declaration' in spec.symbol_node_types
assert 'setter_signature' in spec.symbol_node_types
print('All assertions passed')
"
```
Expected: All assertions pass.

---

## Phase 5: Extractor Updates (R4, R5, R11, R14)

### Sub-phase 5.1: Update _extract_name() for New Node Types

**Files:**
- Modify: `src/jcodemunch_mcp/parser/extractor.py`

**Agent**: general-purpose

#### Step 5.1.1: Update the class_definition references to class_declaration

In `_extract_name()`, find:
```python
if node.type == "mixin_declaration":
```

This existing special case should still work. But search for any `class_definition` string references in the Dart-related code paths of extractor.py and update them to `class_declaration`.

#### Step 5.1.2: Add constructor name extraction

In `_extract_name()`, add a new special case for Dart constructors. Find the section with Dart special cases (near the mixin_declaration handler) and add:

```python
    # WHY: Dart constructors — constructor_signature may have a named child or
    # use the parent class name. Named constructors like Foo.bar() have the name
    # as "bar" in a dot-qualified form. We want "ClassName" for default,
    # "ClassName.named" for named/factory constructors.
    if node.type == "constructor_signature" and spec.ts_language == "dart":
        # Try the name field first (works for named constructors)
        name_node = node.child_by_field_name("name")
        if name_node:
            name = source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
            # For named constructors, the name might just be the suffix.
            # Prefix with class name if we're inside a class.
            return name
        # For default constructors, the name is the class name
        # Walk up to find containing class
        parent = node.parent
        while parent:
            if parent.type in ("class_declaration", "class_body"):
                if parent.type == "class_body":
                    parent = parent.parent
                    continue
                class_name_node = parent.child_by_field_name("name")
                if class_name_node:
                    return source_bytes[class_name_node.start_byte:class_name_node.end_byte].decode("utf-8")
            parent = parent.parent
        return None
```

#### Step 5.1.3: Add `initialized_variable_definition` handler to `_extract_constant()`

Find `_extract_constant()` in `extractor.py`. This function handles constant-pattern nodes. Add a new handler block for Dart's `initialized_variable_definition` node type. Add it before the existing `return None` at the end of the function:

```python
    # WHY: Dart top-level constants use initialized_variable_definition
    # e.g., const String appVersion = '1.0.0'; / final maxRetries = 3;
    if node.type == "initialized_variable_definition" and language == "dart":
        for child in node.children:
            if child.type == "identifier":
                name = source_bytes[child.start_byte:child.end_byte].decode("utf-8")
                break
        else:
            return None
        # WHY: Dart uses camelCase for constants, skip UPPER_CASE heuristic
        sig = source_bytes[node.start_byte:node.end_byte].decode("utf-8").strip()
        docstring = _extract_docstring(node, spec, source_bytes)
        return Symbol(
            id=make_symbol_id(filename, name, "constant"),
            file=filename,
            name=name,
            qualified_name=name,
            kind="constant",
            language=language,
            signature=sig[:100],
            docstring=docstring,
            decorators=[],
            parent=None,
            line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            byte_offset=node.start_byte,
            byte_length=node.end_byte - node.start_byte,
            content_hash=compute_content_hash(source_bytes[node.start_byte:node.end_byte]),
        )
```

> NOTE: After the upstream sync, `_extract_constant()` may have additional parameters or a different signature. Adapt the Symbol construction to match the existing pattern in the function. The key elements are: (1) find the `identifier` child for the name, (2) skip the UPPER_CASE check for Dart, (3) construct and return a Symbol.

#### Step 5.1.4: Add extension_type_declaration name extraction

Check if the nielsenko grammar provides a `name` field for `extension_type_declaration`. If not, add:

```python
    # WHY: Dart extension types (Dart 3) — extension type UserId(int value) implements int {}
    if node.type == "extension_type_declaration" and spec.ts_language == "dart":
        name_node = node.child_by_field_name("name")
        if name_node:
            return source_bytes[name_node.start_byte:name_node.end_byte].decode("utf-8")
        # Fallback: first type_identifier child
        for child in node.children:
            if child.type == "type_identifier":
                return source_bytes[child.start_byte:child.end_byte].decode("utf-8")
        return None
```

#### Step 5.1.5: Verification — parse the fixture

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.parser.extractor import parse_file

with open('tests/fixtures/dart/sample.dart', 'r', encoding='utf-8') as f:
    source = f.read()

symbols = parse_file(source, 'tests/fixtures/dart/sample.dart', 'dart')
for s in symbols:
    print(f'{s.kind:10s} {s.name:30s} line {s.line}')
print(f'\nTotal symbols: {len(symbols)}')
"
```

Expected: Should extract at minimum:
- `function` authenticate
- `class` UserService, ExtendedUserService, AdvancedService, Repository, Result, Success, Failure
- `class` Scrollable (mixin), Logging (mixin)
- `class` StringExt (extension), UserId (extension type)
- `method` getUser, deleteUser, isReady, timeout, scrollTo, log, compareTo, findById, findAll, save, isBlank, display
- `method` UserService (constructor), UserService.withDefaults, UserService.fromConfig, UserService.test, etc.
- `type` Status, JsonMap, VoidCallback
- `constant` appVersion, maxRetries, defaultTimeout

---

## Phase 6: Dart Import Extractor (R2, R7, R8, R10)

### Sub-phase 6.1: Implement _extract_dart_imports()

**Files:**
- Modify: `src/jcodemunch_mcp/parser/imports.py`

**Agent**: general-purpose

#### Step 6.1.1: Add Dart extension to _ALL_EXTENSIONS

Find `_ALL_EXTENSIONS` and add `.dart`:

```python
_ALL_EXTENSIONS = _JS_EXTENSIONS + _PY_EXTENSIONS + _RUBY_EXTENSIONS + (".go", ".dart")
```

#### Step 6.1.2: Add _extract_dart_imports() function

Add this function near the other language-specific extractors (e.g., after `_extract_swift_imports`):

```python
# --- Dart imports (R2, R7, R8, R10) ---

# WHY: Dart has many import forms — package:, dart:, relative, export, part, part of,
# conditional, deferred, show/hide/as. We use regex rather than tree-sitter because
# the import structure is simple and regex matches the pattern used by all other extractors.

_DART_IMPORT_RE = re.compile(
    r"""^[ \t]*(?:import|export)\s+['"]([^'"]+)['"]\s*"""
    r"""(?:deferred\s+)?"""
    r"""(?:as\s+\w+\s*)?"""
    r"""(?:(?:show|hide)\s+([\w\s,]+?))?"""
    r"""\s*;""",
    re.MULTILINE,
)

_DART_PART_RE = re.compile(
    r"""^[ \t]*part\s+['"]([^'"]+)['"]\s*;""",
    re.MULTILINE,
)

_DART_PART_OF_RE = re.compile(
    r"""^[ \t]*part\s+of\s+['"]([^'"]+)['"]\s*;""",
    re.MULTILINE,
)

# Conditional imports: import 'default.dart' if (dart.library.io) 'platform.dart';
_DART_CONDITIONAL_IMPORT_RE = re.compile(
    r"""^[ \t]*import\s+['"]([^'"]+)['"]\s+if\s*\([^)]+\)\s+['"]([^'"]+)['"]"""
    r"""(?:\s*(?:as\s+\w+|show\s+[\w\s,]+|hide\s+[\w\s,]+))*\s*;""",
    re.MULTILINE,
)

# WHY: Generated code files should not pollute the import graph.
# *.g.dart = json_serializable/built_value, *.freezed.dart = freezed,
# *.mocks.dart = mockito (R10)
_DART_GENERATED_SUFFIXES = (".g.dart", ".freezed.dart", ".mocks.dart")


def _is_dart_generated(specifier: str) -> bool:
    """Check if a specifier points to a generated Dart file."""
    return any(specifier.endswith(suffix) for suffix in _DART_GENERATED_SUFFIXES)


def _extract_dart_imports(content: str) -> list[dict]:
    """Extract Dart import/export/part edges from file content."""
    edges: list[dict] = []
    seen: set[str] = set()

    # WHY: Conditional imports have two specifiers — capture both
    for m in _DART_CONDITIONAL_IMPORT_RE.finditer(content):
        for specifier in [m.group(1).strip(), m.group(2).strip()]:
            if specifier.startswith("dart:") or _is_dart_generated(specifier):
                continue
            if specifier not in seen:
                seen.add(specifier)
                edges.append({"specifier": specifier, "names": []})

    for m in _DART_IMPORT_RE.finditer(content):
        specifier = m.group(1).strip()

        # WHY: dart: SDK imports resolve to the SDK, not project files — skip them
        if specifier.startswith("dart:"):
            continue

        # WHY: Generated code filtering (R10) — exclude *.g.dart etc.
        if _is_dart_generated(specifier):
            continue

        # WHY: show/hide combinators (R8) — capture named imports
        names: list[str] = []
        if m.group(2):
            raw_names = m.group(2)
            # WHY: "show A, B hide C" captures "A, B hide C" — split on hide keyword
            hide_idx = re.search(r'\bhide\b', raw_names)
            if hide_idx:
                raw_names = raw_names[:hide_idx.start()]
            names = [n.strip() for n in raw_names.split(",") if n.strip()]

        if specifier not in seen:
            seen.add(specifier)
            edges.append({"specifier": specifier, "names": names})

    # part directives create a tight coupling — the part file is effectively
    # part of this file's compilation unit
    for m in _DART_PART_RE.finditer(content):
        specifier = m.group(1).strip()
        if _is_dart_generated(specifier):
            continue
        if specifier not in seen:
            seen.add(specifier)
            edges.append({"specifier": specifier, "names": []})

    # part-of is the reverse edge — this file is part of the parent
    for m in _DART_PART_OF_RE.finditer(content):
        specifier = m.group(1).strip()
        if specifier not in seen:
            seen.add(specifier)
            edges.append({"specifier": specifier, "names": []})

    return edges
```

#### Step 6.1.3: Register Dart in _LANGUAGE_EXTRACTORS

Find the `_LANGUAGE_EXTRACTORS` dict and add:

```python
    "dart": _extract_dart_imports,
```

#### Step 6.1.4: Verification

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.parser.imports import _extract_dart_imports

content = open('tests/fixtures/dart/sample.dart').read()
edges = _extract_dart_imports(content)
for e in edges:
    print(f'  {e[\"specifier\"]:50s} names={e[\"names\"]}')
print(f'\nTotal edges: {len(edges)}')
# Should NOT include dart:async, dart:convert (SDK imports)
# Should NOT include sample.g.dart (generated code)
assert not any(e['specifier'].startswith('dart:') for e in edges), 'Should skip dart: imports'
print('Assertions passed')
"
```

Expected: Extracts `package:flutter/material.dart`, `package:flutter/foundation.dart` (with names `['kDebugMode', 'kIsWeb']`), relative imports like `../models/user.dart`, exports, conditional imports, deferred imports, and part directives. Does NOT include `dart:async`, `dart:convert`, or `sample.g.dart`.

---

## Phase 7: Package URI Resolution (R3)

### Sub-phase 7.1: Add package: URI Resolution to resolve_specifier()

**Files:**
- Modify: `src/jcodemunch_mcp/parser/imports.py`

**Agent**: general-purpose

#### Step 7.1.1: Add pubspec.yaml reading utility

Add this near the top of `imports.py`, after existing utility functions:

```python
import json as _json

# WHY: Dart package: URIs map to lib/ directories. A `package:foo/bar.dart` import
# resolves to `lib/bar.dart` within the package named `foo`. For the current project,
# we read pubspec.yaml to discover the package name, then map package:self/ → lib/.
# External packages are unresolvable within the project source tree.

_PUBSPEC_CACHE: dict[str, str | None] = {}  # project_root -> package_name

# NOTE: _find_pubspec_package_name() has been removed (YAGNI — it was stubbed out,
# returned None, and was never called). Resolution is handled by _resolve_dart_package_import.


def _resolve_dart_package_import(specifier: str, source_files: set[str]) -> str | None:
    """Resolve a package: URI to a source file path.

    Strategy: package:foo/bar.dart → look for lib/bar.dart in source files.
    This works for self-package imports (the most common case in a single-repo).
    """
    if not specifier.startswith("package:"):
        return None

    # package:foo/bar/baz.dart → bar/baz.dart (strip package:foo/)
    parts = specifier[len("package:"):].split("/", 1)
    if len(parts) < 2:
        return None
    _package_name, rest = parts[0], parts[1]

    # Try lib/<rest> in source files
    # WHY: Defense-in-depth — reject path traversal attempts like package:foo/../../etc/passwd
    import posixpath
    candidate = posixpath.normpath(f"lib/{rest}")
    if candidate.startswith("..") or posixpath.isabs(candidate):
        return None
    for sf in source_files:
        norm = sf.replace("\\", "/")
        if norm == candidate or norm.endswith(f"/{candidate}"):
            return sf

    return None
```

#### Step 7.1.2: Update resolve_specifier() for Dart

Find the `resolve_specifier()` function. Add a Dart package: check BEFORE the relative import check:

```python
def resolve_specifier(specifier, importer_path, source_files, alias_map=None):
    # WHY: Dart package: URIs need special resolution — they map to lib/ directories
    if specifier.startswith("package:"):
        result = _resolve_dart_package_import(specifier, source_files)
        if result:
            return result
        return None  # External package — not in our source tree

    # ... existing code continues unchanged ...
```

Also, ensure `.dart` extensions are tried in the `_candidates()` function. Find `_candidates()` and check if it tries `.dart`. If not, the `_ALL_EXTENSIONS` addition from Step 6.1.1 should handle this since `_candidates()` likely uses `_ALL_EXTENSIONS`. Verify this.

#### Step 7.1.3: Verification

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.parser.imports import resolve_specifier

# Simulate a source file set
source_files = {
    'lib/main.dart',
    'lib/models/user.dart',
    'lib/models/project.dart',
    'lib/shared/constants.dart',
    'lib/features/auth/login.dart',
}

# Test package: resolution
result = resolve_specifier('package:myapp/models/user.dart', 'lib/features/auth/login.dart', source_files)
print(f'package: resolved to: {result}')
assert result == 'lib/models/user.dart', f'Expected lib/models/user.dart, got {result}'

# Test relative resolution
result2 = resolve_specifier('../models/user.dart', 'lib/features/auth/login.dart', source_files)
print(f'relative resolved to: {result2}')

print('All assertions passed')
"
```

---

## Phase 8: Class Hierarchy Update (R6)

### Sub-phase 8.1: Add Dart `with` Clause Support

**Files:**
- Modify: `src/jcodemunch_mcp/tools/get_class_hierarchy.py`

**Agent**: general-purpose

#### Step 8.1.1: Update _EXTENDS_RE to stop at `with` keyword

Find the existing `_EXTENDS_RE` pattern and update it so it stops at `with` (not just `implements` or `{`). This prevents `extends UserService with Scrollable` from capturing `UserService with Scrollable` as the extends match:

```python
_EXTENDS_RE = re.compile(
    r'\bextends\s+([\w$][\w$,\s]*?)(?=\s+implements|\s+with|\s*[{(<]|$)', re.IGNORECASE
)
```

#### Step 8.1.2: Add _WITH_RE regex pattern

Find the existing `_EXTENDS_RE` and `_IMPLEMENTS_RE` patterns and add after them:

```python
# WHY: Dart mixins use `with` clause — class Foo extends Bar with Mixin1, Mixin2 {}
# This is distinct from extends/implements and captures mixin relationships.
_WITH_RE = re.compile(
    r'\bwith\s+([\w$][\w$,\s]*?)(?=\s+implements|\s*[{(<]|$)', re.IGNORECASE
)
```

#### Step 8.1.3: Update _parse_bases() to include `with` matches

Find the `_parse_bases()` function and add `with` handling after the `implements` block:

```python
def _parse_bases(signature: str) -> list[str]:
    bases = []
    m = _EXTENDS_RE.search(signature)
    if m:
        bases += [n.strip() for n in m.group(1).split(",") if n.strip()]
    m = _IMPLEMENTS_RE.search(signature)
    if m:
        bases += [n.strip() for n in m.group(1).split(",") if n.strip()]
    # WHY: Dart `with` clause for mixins (R6)
    m = _WITH_RE.search(signature)
    if m:
        bases += [n.strip() for n in m.group(1).split(",") if n.strip()]
    if not bases:
        m = _PAREN_BASES_RE.search(signature)
        if m:
            candidates = [n.strip() for n in m.group(1).split(",") if n.strip()]
            bases += [c for c in candidates if re.match(r'^[A-Z][\w.]*$', c)]
    return bases
```

#### Step 8.1.4: Verification

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
import re
# Inline test of the updated _parse_bases logic
_EXTENDS_RE = re.compile(r'\bextends\s+([\w\$][\w\$,\s]*?)(?=\s+implements|\s+with|\s*[{(<]|\$)', re.IGNORECASE)
_IMPLEMENTS_RE = re.compile(r'\bimplements\s+([\w\$][\w\$,\s]*?)(?=\s*[{(<]|\$)', re.IGNORECASE)
_WITH_RE = re.compile(r'\bwith\s+([\w\$][\w\$,\s]*?)(?=\s+implements|\s*[{(<]|\$)', re.IGNORECASE)

sig = 'class AdvancedService extends UserService with Scrollable, Logging {'
bases = []
m = _EXTENDS_RE.search(sig)
if m: bases += [n.strip() for n in m.group(1).split(',') if n.strip()]
m = _IMPLEMENTS_RE.search(sig)
if m: bases += [n.strip() for n in m.group(1).split(',') if n.strip()]
m = _WITH_RE.search(sig)
if m: bases += [n.strip() for n in m.group(1).split(',') if n.strip()]
print('Bases:', bases)
assert 'UserService' in bases
assert 'Scrollable' in bases
assert 'Logging' in bases
print('Assertions passed')
"
```

---

## Phase 9: Tests (R15)

### Sub-phase 9.1: Update Existing Dart Tests

**Files:**
- Modify: `tests/test_languages.py`

**Agent**: general-purpose

#### Step 9.1.1: Expand test_parse_dart

Find the existing `test_parse_dart` function in `test_languages.py` and expand it. The exact modifications depend on the current test structure, but add assertions for:

```python
def test_parse_dart():
    """Test Dart symbol extraction with comprehensive fixture."""
    from jcodemunch_mcp.parser.extractor import parse_file

    fixture = Path(__file__).parent / "fixtures" / "dart" / "sample.dart"
    source = fixture.read_text(encoding='utf-8')
    symbols = parse_file(source, str(fixture), "dart")
    names = {s.name for s in symbols}
    kinds = {s.name: s.kind for s in symbols}

    # Classes (including grammar change: class_declaration)
    assert "UserService" in names
    assert "ExtendedUserService" in names
    assert "AdvancedService" in names
    assert "Repository" in names
    assert kinds.get("UserService") == "class"

    # Mixins (reported as class)
    assert "Scrollable" in names
    assert "Logging" in names
    assert kinds.get("Scrollable") == "class"

    # Extensions
    assert "StringExt" in names

    # Extension types (R11)
    assert "UserId" in names
    assert kinds.get("UserId") == "class"

    # Methods
    assert "getUser" in names
    assert "deleteUser" in names
    assert "isReady" in names
    assert kinds.get("getUser") == "method"

    # Setters (new)
    assert "timeout" in names

    # Constructors (R4) — names depend on extraction strategy
    # At minimum, verify some constructor-related symbols exist

    # Types
    assert "Status" in names
    assert "JsonMap" in names
    assert kinds.get("Status") == "type"

    # Functions
    assert "authenticate" in names
    assert kinds.get("authenticate") == "function"

    # Constants (R5)
    assert "appVersion" in names or any("appVersion" in s.name for s in symbols)

    # Sealed classes (Dart 3)
    assert "Result" in names
    assert "Success" in names
    assert "Failure" in names
```

### Sub-phase 9.2: Create Dart Import Tests

**Files:**
- Create: `tests/test_dart_imports.py`

**Agent**: general-purpose

#### Step 9.2.1: Write test_dart_imports.py

```python
"""Tests for Dart import extraction and resolution."""
from pathlib import Path

import pytest

from jcodemunch_mcp.parser.imports import extract_imports, resolve_specifier


@pytest.fixture
def dart_fixture_content():
    fixture = Path(__file__).parent / "fixtures" / "dart" / "sample.dart"
    return fixture.read_text()


class TestDartImportExtraction:
    """Test _extract_dart_imports via the public extract_imports interface."""

    def test_extracts_package_imports(self, dart_fixture_content):
        edges = extract_imports(dart_fixture_content, "sample.dart", "dart")
        specifiers = {e["specifier"] for e in edges}
        assert "package:flutter/material.dart" in specifiers
        assert "package:provider/provider.dart" in specifiers

    def test_extracts_relative_imports(self, dart_fixture_content):
        edges = extract_imports(dart_fixture_content, "sample.dart", "dart")
        specifiers = {e["specifier"] for e in edges}
        assert "../models/user.dart" in specifiers
        assert "utils.dart" in specifiers

    def test_skips_dart_sdk_imports(self, dart_fixture_content):
        edges = extract_imports(dart_fixture_content, "sample.dart", "dart")
        specifiers = {e["specifier"] for e in edges}
        assert not any(s.startswith("dart:") for s in specifiers)

    def test_captures_show_combinators(self, dart_fixture_content):
        """R8: show/hide combinator names."""
        edges = extract_imports(dart_fixture_content, "sample.dart", "dart")
        edge_map = {e["specifier"]: e for e in edges}
        flutter_foundation = edge_map.get("package:flutter/foundation.dart", {})
        assert "kDebugMode" in flutter_foundation.get("names", [])
        assert "kIsWeb" in flutter_foundation.get("names", [])

    def test_extracts_exports(self, dart_fixture_content):
        """R7: export directives should appear as edges."""
        edges = extract_imports(dart_fixture_content, "sample.dart", "dart")
        specifiers = {e["specifier"] for e in edges}
        # export 'package:flutter/widgets.dart' show Widget, State;
        assert "package:flutter/widgets.dart" in specifiers
        # export '../shared/constants.dart';
        assert "../shared/constants.dart" in specifiers

    def test_extracts_conditional_import(self, dart_fixture_content):
        """R2: conditional imports."""
        edges = extract_imports(dart_fixture_content, "sample.dart", "dart")
        specifiers = {e["specifier"] for e in edges}
        # The primary specifier is stub_io.dart
        assert "stub_io.dart" in specifiers or "real_io.dart" in specifiers

    def test_extracts_deferred_import(self, dart_fixture_content):
        """R2: deferred imports."""
        edges = extract_imports(dart_fixture_content, "sample.dart", "dart")
        specifiers = {e["specifier"] for e in edges}
        assert "package:heavy_lib/heavy.dart" in specifiers

    def test_filters_generated_code(self, dart_fixture_content):
        """R10: *.g.dart files should be excluded."""
        edges = extract_imports(dart_fixture_content, "sample.dart", "dart")
        specifiers = {e["specifier"] for e in edges}
        assert "sample.g.dart" not in specifiers

    def test_extracts_non_generated_part(self, dart_fixture_content):
        """Part directives for non-generated files create edges."""
        edges = extract_imports(dart_fixture_content, "sample.dart", "dart")
        specifiers = {e["specifier"] for e in edges}
        assert "sample_part.dart" in specifiers


class TestDartPackageResolution:
    """Test resolve_specifier for Dart package: URIs."""

    def test_resolves_package_to_lib(self):
        source_files = {"lib/models/user.dart", "lib/main.dart"}
        result = resolve_specifier(
            "package:myapp/models/user.dart",
            "lib/features/auth/login.dart",
            source_files,
        )
        assert result == "lib/models/user.dart"

    def test_returns_none_for_external_package(self):
        source_files = {"lib/main.dart"}
        result = resolve_specifier(
            "package:http/http.dart",
            "lib/main.dart",
            source_files,
        )
        assert result is None

    def test_resolves_relative_dart_import(self):
        source_files = {"lib/models/user.dart", "lib/features/auth/login.dart"}
        result = resolve_specifier(
            "../models/user.dart",
            "lib/features/auth/login.dart",
            source_files,
        )
        # Should resolve to lib/models/user.dart
        assert result is not None
```

#### Step 9.2.2: Verification — run all Dart tests

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
pytest tests/test_languages.py -k dart -v --timeout=60
pytest tests/test_dart_imports.py -v --timeout=60
```

Expected: All tests pass.

---

## Phase 10: Annotation and Extension Verification (R9, R14)

### Sub-phase 10.1: Verify Annotation Extraction (R9)

**Agent**: general-purpose

#### Step 10.1.1: Verify annotations are captured

This is a verification step only. The existing `_extract_decorators()` function + `decorator_node_type="annotation"` in DART_SPEC should already capture `@override`, `@deprecated`, `@visibleForTesting`, `@immutable`.

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.parser.extractor import parse_file

with open('tests/fixtures/dart/sample.dart', 'r', encoding='utf-8') as f:
    source = f.read()

symbols = parse_file(source, 'tests/fixtures/dart/sample.dart', 'dart')
for s in symbols:
    if s.decorators:
        print(f'{s.name}: decorators={s.decorators}')
"
```

Expected: `UserService` shows `@immutable`, `getUser` shows `@visibleForTesting`, `deleteUser` shows `@Deprecated(...)`. If decorators are empty, investigate `_extract_decorators()` and the `annotation` node type in the nielsenko grammar.

#### Step 10.1.2: Fix annotation extraction if needed

If Step 10.1.1 shows empty decorators, the nielsenko grammar may use a different node structure for annotations. In that case:

1. Dump the AST for an annotated method:
```bash
python -c "
from tree_sitter_dart import language as dart_lang
from tree_sitter import Language, Parser
parser = Parser(Language(dart_lang()))
tree = parser.parse(b'@override void foo() {}')
def show(n, depth=0):
    print(' '*depth + f'{n.type} [{n.start_byte}:{n.end_byte}]')
    for c in n.children: show(c, depth+2)
show(tree.root_node)
"
```

2. If the annotation node type differs from `annotation`, update `DART_SPEC.decorator_node_type` to match.
3. If annotations are children of the declaration (not preceding siblings), set `decorator_from_children=True` in DART_SPEC.

### Sub-phase 10.2: Verify Extension `on` Type (R14)

#### Step 10.2.1: Verify signature capture

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.parser.extractor import parse_file

with open('tests/fixtures/dart/sample.dart', 'r', encoding='utf-8') as f:
    source = f.read()

symbols = parse_file(source, 'tests/fixtures/dart/sample.dart', 'dart')
for s in symbols:
    if s.name == 'StringExt':
        print(f'StringExt signature: {getattr(s, \"signature\", \"NONE\")}')
    if s.name == 'Scrollable':
        print(f'Scrollable signature: {getattr(s, \"signature\", \"NONE\")}')
"
```

Expected: The signature should contain `on String` / `on UserService`. If not, the `_build_signature()` function may need a tweak to capture the `on` clause from the extension node's text.

---

## Phase 11: Generated Code Filtering (R10)

### Sub-phase 11.1: Verify or Add Generated Code Filtering

**Agent**: general-purpose

#### Step 11.1.1: Check existing ignore patterns

Check if the indexing pipeline already has an `extra_ignore_patterns` or similar mechanism. If so, Dart generated code filtering just needs `.g.dart`, `.freezed.dart`, `.mocks.dart` added to that list.

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
# Check if index_repo or index_folder has ignore patterns
import inspect
from jcodemunch_mcp.tools import index_repo
print(inspect.getsource(index_repo))
" 2>&1 | head -50
```

If there's already a pattern-based ignore mechanism, add the Dart generated suffixes there. If not, the import extractor's `_is_dart_generated()` filter (added in Phase 6) handles the import graph side. For the symbol indexing side, generated files would still be indexed but this is acceptable — they contain valid symbols that users may want to find.

---

## Phase 12: Documentation (R16)

### Sub-phase 12.1: Update LANGUAGE_SUPPORT.md

**Files:**
- Modify: `LANGUAGE_SUPPORT.md`

**Agent**: general-purpose

#### Step 12.1.1: Expand the Dart section

Find the Dart row/section in `LANGUAGE_SUPPORT.md` and update it to reflect first-class support:

```markdown
| Dart | Full | classes, mixins, extensions, extension types, enums, functions, methods, getters, setters, constructors, constants, type aliases | import, export, part/part of, package:, relative, conditional, deferred, show/hide | nielsenko/tree-sitter-dart | @override, @deprecated, @visibleForTesting, @immutable | *.g.dart, *.freezed.dart, *.mocks.dart filtered |
```

### Sub-phase 12.2: Create DART_SUPPORT.md

**Files:**
- Create: `DART_SUPPORT.md` (in the project root of jcodemunch-mcp)

**Agent**: general-purpose

#### Step 12.2.1: Write DART_SUPPORT.md

```markdown
# Dart Support in jcodemunch-mcp

## Overview

Dart has first-class support in jcodemunch-mcp, matching the depth of Python/JS/TS/Go/Rust/C#.

## Grammar

Uses [nielsenko/tree-sitter-dart](https://github.com/nielsenko/tree-sitter-dart) for parsing, which achieves 100% parse success on the Dart corpus. Falls back to the language-pack grammar if the nielsenko package is not installed.

## Symbol Extraction

| Symbol Type | Node Type | Example |
|-------------|-----------|---------|
| Class | `class_declaration` | `class UserService {}` |
| Mixin | `mixin_declaration` | `mixin Scrollable on Widget {}` |
| Extension | `extension_declaration` | `extension StringExt on String {}` |
| Extension Type | `extension_type_declaration` | `extension type UserId(int value) {}` |
| Enum | `enum_declaration` | `enum Status { active, done }` |
| Function | `function_signature` | `void main() {}` |
| Method | `method_signature` | `String getUser(int id) {}` |
| Getter | `getter_signature` | `bool get isReady => true;` |
| Setter | `setter_signature` | `set timeout(int v) {}` |
| Constructor | `constructor_signature` | `const Foo(this.x);` |
| Type Alias | `type_alias` | `typedef JsonMap = Map<String, dynamic>;` |
| Constant | `initialized_variable_definition` | `const appVersion = '1.0.0';` |

## Import Graph

All Dart import forms are supported:

- `import 'package:foo/bar.dart';` — package imports (resolved to `lib/` for self-package)
- `import '../models/user.dart';` — relative imports
- `import 'dart:async';` — SDK imports (skipped in graph — not project code)
- `export 'package:foo/bar.dart';` — re-exports (appear as edges in dependency graph)
- `part 'foo_part.dart';` / `part of 'foo.dart';` — part directives
- `import 'foo.dart' if (dart.library.io) 'bar.dart';` — conditional imports
- `import 'foo.dart' deferred as foo;` — deferred imports
- `import 'foo.dart' show Foo, Bar;` — show combinators (names captured)
- `import 'foo.dart' hide Baz;` — hide combinators

## Class Hierarchy

Supports all Dart class relationship keywords:
- `extends` — single inheritance
- `implements` — interface implementation
- `with` — mixin application

## Generated Code Filtering

Files matching these patterns are excluded from the import graph:
- `*.g.dart` — json_serializable, built_value
- `*.freezed.dart` — freezed
- `*.mocks.dart` — mockito

## Annotations

The following annotations are captured as decorators on symbols:
- `@override`
- `@deprecated` / `@Deprecated('message')`
- `@visibleForTesting`
- `@immutable`
- Any custom annotation

## Flutter Project Configuration

- Point `index_folder` at the project root (where `pubspec.yaml` lives), not `lib/`.
- `package:` imports are resolved via the `lib/` directory convention — `package:myapp/foo.dart` maps to `lib/foo.dart`.
- Mono-repo support: index each package separately (each `pubspec.yaml` root is one repo).

## Tool Examples

### get_file_outline on a Dart file

```json
{
  "file": "lib/services/user_service.dart",
  "symbols": [
    {"name": "UserService", "kind": "class", "line": 12, "decorators": ["@immutable"]},
    {"name": "UserService", "kind": "method", "line": 15, "parent": "UserService"},
    {"name": "getUser", "kind": "method", "line": 20, "parent": "UserService", "decorators": ["@visibleForTesting"]}
  ]
}
```

### find_importers for a Dart file

```json
{
  "file": "lib/core/database/database_service.dart",
  "importer_count": 8,
  "importers": [
    "lib/features/auth/data/auth_repository.dart",
    "lib/features/entries/data/entry_repository.dart"
  ]
}
```

### get_class_hierarchy with mixin chains

```json
{
  "class": "AdvancedService",
  "extends": "UserService",
  "implements": [],
  "with": ["Scrollable", "Logging"],
  "ancestors": ["UserService", "Object"]
}
```

## File Watcher

The watcher auto-detects `.dart` file changes (add/modify/delete) and triggers incremental re-indexing. No extra configuration needed.
```

### Sub-phase 12.3: Update tool docstrings for Dart

**Files:**
- Modify: `src/jcodemunch_mcp/tools/find_importers.py`
- Modify: `src/jcodemunch_mcp/tools/get_dependency_graph.py`
- Modify: `src/jcodemunch_mcp/tools/get_blast_radius.py`

**Agent**: general-purpose

#### Step 12.3.1: Add Dart/package: URI mention to tool docstrings

In each of the three tool files, find the module or function docstring and add a note that Dart and `package:` URIs are supported. Example addition for `find_importers.py`:

```
Supports all indexed languages including Dart. For Dart projects, package: URIs
are resolved to lib/ paths automatically.
```

---

## Phase 13: Final Integration Test

### Sub-phase 13.1: Full Test Suite

**Agent**: general-purpose

#### Step 13.1.1: Run complete test suite

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
pytest tests/ -v --timeout=120
```

Expected: All tests pass, including the new Dart tests and all existing tests for other languages (no regressions).

#### Step 13.1.2: End-to-end verification with index_repo

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
# Quick smoke test: index the fixture directory and check Dart files are indexed
from jcodemunch_mcp.parser.extractor import parse_file
from jcodemunch_mcp.parser.imports import extract_imports

fixture = 'tests/fixtures/dart/sample.dart'
with open(fixture, 'r', encoding='utf-8') as f:
    source = f.read()

symbols = parse_file(source, fixture, 'dart')
imports = extract_imports(source, fixture, 'dart')

print(f'Symbols: {len(symbols)}')
print(f'Imports: {len(imports)}')
print()
print('Symbol summary:')
for kind in ['class', 'method', 'function', 'type', 'constant']:
    count = sum(1 for s in symbols if s.kind == kind)
    print(f'  {kind}: {count}')
print()
print('Import summary:')
for e in imports:
    print(f'  {e[\"specifier\"]}')
"
```

---

## Phase 14: Spec Validation (Real-World Verification)

### Sub-phase 14.1: Index the Field Guide App

**Agent**: general-purpose

#### Step 14.1.1: Index the real Flutter project

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.tools.index_folder import index_folder
import asyncio
result = asyncio.run(index_folder(path='C:\\\\Users\\\\rseba\\\\Projects\\\\Field_Guide_App', incremental=False, use_ai_summaries=False))
print(f'Files: {result.get(\"file_count\", 0)}')
print(f'Symbols: {result.get(\"symbol_count\", 0)}')
print(f'Languages: {result.get(\"languages\", {})}')
"
```

Expected: Dart files indexed with symbols > 0.

#### Step 14.1.2: Verify find_importers

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.tools.find_importers import find_importers
result = find_importers(repo='local/Field_Guide_App', file_path='lib/core/database/database_service.dart')
print(result)
assert result.get('importer_count', 0) > 0, 'find_importers should return results'
"
```

#### Step 14.1.3: Verify get_dependency_graph

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.tools.get_dependency_graph import get_dependency_graph
result = get_dependency_graph(repo='local/Field_Guide_App', file_path='lib/main.dart', depth=2)
print(f'Nodes: {result.get(\"node_count\", 0)}')
assert result.get('node_count', 0) > 0, 'dependency graph should have nodes'
"
```

#### Step 14.1.4: Verify get_blast_radius

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.tools.get_blast_radius import get_blast_radius
result = get_blast_radius(repo='local/Field_Guide_App', symbol='DatabaseService')
print(result)
assert 'error' not in result, 'blast_radius should not error'
"
```

#### Step 14.1.5: Verify get_class_hierarchy with mixins

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.tools.get_class_hierarchy import get_class_hierarchy
result = get_class_hierarchy(repo='local/Field_Guide_App', class_name='BaseRepository')
print(result)
"
```

#### Step 14.1.6: Verify constructors in get_file_outline

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.tools.get_file_outline import get_file_outline
result = get_file_outline(repo='local/Field_Guide_App', file_path='lib/core/database/database_service.dart')
symbols = result.get('symbols', [])
kinds = [s['kind'] for s in symbols]
print(f'Symbol kinds: {set(kinds)}')
print(f'Total: {len(symbols)}')
"
```

#### Step 14.1.7: Verify previously-failing files now parse

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
python -c "
from jcodemunch_mcp.tools.get_file_outline import get_file_outline
# These files returned empty in the old grammar
test_files = [
    'lib/features/sync/data/sync_repository.dart',
    'lib/core/database/database_service.dart',
]
for f in test_files:
    result = get_file_outline(repo='local/Field_Guide_App', file_path=f)
    count = len(result.get('symbols', []))
    print(f'{f}: {count} symbols')
    assert count > 0, f'{f} should have symbols with nielsenko grammar'
"
```

#### Step 14.1.8: Commit

```bash
cd C:\Users\rseba\Projects\jcodemunch-mcp
git add -A
git commit -m "feat(dart): first-class Dart support — grammar, imports, symbols, hierarchy

- Upgrade to nielsenko/tree-sitter-dart (100% parse success)
- Add regex-based import extractor (all Dart import forms)
- Add package: URI resolution via lib/ mapping
- Expand DART_SPEC: constructors, constants, setters, extension types
- Add with-clause support to class hierarchy
- Filter generated code (*.g.dart, *.freezed.dart, *.mocks.dart)
- Comprehensive test fixture and test coverage"
```
