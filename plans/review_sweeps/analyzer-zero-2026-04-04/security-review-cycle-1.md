# Security Review -- Cycle 1

**Verdict**: APPROVE WITH CONDITIONS

0 Critical, 1 High, 3 Medium, 3 Low findings.

## High Issues

**H1: Blanket `on Exception catch (e)` conversion will miss `StateError`/`ArgumentError` in sync engine**

Sync engine catch blocks at lines 587, 596, 812, 1295, 1385, 1531, 1682, 2214 handle `Error` subclasses (`StateError` from company_id mismatch, `ArgumentError` from invalid storage path, `RangeError` from corrupt image EXIF). Converting to `on Exception catch` would let these propagate unhandled, crashing sync instead of graceful degradation.

Fix: These catch sites must use `catch (Object e)` or remain bare. Alternatively refactor the `throw StateError`/`throw ArgumentError` to throw custom Exception subclasses.

## Medium Issues

**M1: SafeRow `requireString` introduces `StateError` throws** — only safe for NOT NULL columns. Add doc comment.

**M2: `unawaited(_saveIfEditing())` may suppress save errors silently** — verify internal try/catch exists.

**M3: Removing `do_not_use_environment` permanently** — future `fromEnvironment` with real credentials in `defaultValue` won't be flagged.

## Low Issues

L1: ~220 ignore comments create maintenance debt (moot if user rejects ignores).
L2: `unreachable_from_main` deletions should verify no security-sensitive code removed.
L3: `on FormatException` guidance is correct but could be misapplied.
