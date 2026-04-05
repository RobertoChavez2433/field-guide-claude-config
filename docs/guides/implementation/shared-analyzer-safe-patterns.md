---
type: implementation-guide
scope: Shared analyzer-safety abstractions
updated: 2026-04-04
---

# Shared Analyzer-Safe Patterns

This guide preserves the cross-cutting abstractions that came out of the analyzer-zero work so future sessions do not have to rediscover them from code.

## Landed Patterns

### `SafeRow`

File: `lib/shared/utils/safe_row.dart`

Use `SafeRow` only for raw SQLite query rows typed as `Map<String, Object?>`.

- Preferred for database query results where analyzer-safe non-null access is needed
- Keep it scoped to SQLite row maps
- Do not route general JSON parsing or `Map<String, dynamic>` model decoding through it

Available helpers include:
- `requireString`
- `requireInt`
- `requireDouble`
- `requireBool`
- `optionalString`
- `optionalInt`
- `optionalBool`
- `intOrDefault`

The intent is narrow: replace repetitive row casts and null assertions without inventing a general-purpose map parsing layer.

### `SafeAction`

File: `lib/shared/providers/safe_action_mixin.dart`

`SafeAction` landed as a hook-based mixin over provider-owned state.

- Providers keep their own `_isLoading`, `_error`, and any secondary state flags
- Providers expose that state through `safeActionIsLoading`, `safeActionError`, and `safeActionLogTag`
- The mixin owns the async action lifecycle, logging, and listener notifications
- It does not own private provider fields directly

Use `SafeAction` when a provider has the common start/error/finally/notify pattern and the action lifecycle is genuinely shared. Keep manual handling when a provider has multiple loading channels, custom timing, or domain-specific branches that would be distorted by the helper.

### Shared Provider Bases

Files:
- `lib/shared/providers/base_list_provider.dart`
- `lib/shared/providers/paged_list_provider.dart`

These base providers now sit on top of `SafeAction`. Feature providers that extend them inherit the standardized action flow without losing provider-owned state.

## Repository Guidance

`RepositoryResult<T>` remains the shared success/failure wrapper in `lib/shared/repositories/base_repository.dart`.

The analyzer-zero plan explored a `RepositoryResult.safeCall` / `safeEmptyCall` helper, but that abstraction did not become a branch-wide invariant. The repository layer in this codebase still has meaningful variation:

- different logger categories (`Logger.db`, `Logger.photo`, `Logger.sync`, `Logger.error`)
- domain validation before datasource calls
- row-count / not-found branching
- file-system side effects
- repository-specific user-facing failure text

Treat manual repository handling as normal in this repo unless a future refactor introduces a helper that clearly preserves those semantics.

## CopyWith Guidance

The analyzer-zero plan originally included a shared copyWith helper phase for sentinel-based `copyWith` methods.

That phase did not land, and it is not part of the current architectural baseline.

- Do not assume a shared `_resolveParam<T>()` helper exists across the codebase
- Do not introduce a `Value<T>` wrapper opportunistically
- If copyWith ergonomics need work later, handle that as a separate modeling refactor, not as analyzer-zero follow-up

The branch reached zero analyzer issues without standardizing copyWith around a new wrapper type.

## Documentation Boundary

When updating docs that mention shared provider or repository bases:

- link back to this guide instead of duplicating helper behavior
- keep feature docs focused on feature-specific rules
- keep cross-cutting analyzer-safety conventions centralized here
