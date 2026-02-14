# Shared Data Validation Rules

**Applied to ALL features.** Feature-specific constraints are in `[feature]-constraints.md` files in this directory.

---

## Mandatory Rules

### User Input Validation
- [ ] All user input (text, numbers, dates, selections) validated before persistence
- [ ] Validation happens at **form level** (UI feedback) AND **repository level** (data integrity)
- [ ] Error messages are user-friendly, actionable, and field-specific
- [ ] Null/empty checks before any string operations

### Null Safety & Type Correctness
- [ ] No nullable types used for required business logic fields
- [ ] Late initialization (`late` keyword) only where unavoidable with documented rationale
- [ ] All `?` types (nullable) must have explicit null-handling code
- [ ] Never assume deserialized data is non-null without validation

### API & Network Boundaries
- [ ] All external API calls wrapped in try-catch with specific exception types
- [ ] Network errors reported to UI with user-friendly messaging (SnackBar or ErrorWidget)
- [ ] Timeouts enforced (default: 30 seconds unless documented otherwise)
- [ ] Retry logic with exponential backoff for transient failures
- [ ] Failed requests logged with timestamp + error details

### Database Access Patterns
- [ ] No raw SQL in Dart code — use repository pattern exclusively
- [ ] Multi-step operations wrapped in transactions
- [ ] Cascade deletes documented and tested (prevent orphaned records)
- [ ] Foreign key constraints enforced in schema
- [ ] Queries indexed for common filters (avoid table scans)

### Testing Requirements (Minimum)
- [ ] All public methods/functions have unit tests
- [ ] Happy path + error cases tested
- [ ] Edge cases tested (empty lists, null values, boundary conditions)
- [ ] Test coverage >= 85% for feature-critical code
- [ ] Integration tests for repository/API layer (use real DB)

### Code Quality
- [ ] `dart analyze` runs clean (0 errors, warnings must be addressed)
- [ ] No hardcoded strings outside of constants (use `const String kName = ...`)
- [ ] No magic numbers (use named constants with rationale comments)
- [ ] All enum values updated consistently across codebase (no partial updates)
- [ ] Deprecated code clearly marked with @deprecated + migration path

### Async & Concurrency
- [ ] All async operations use `await` (no fire-and-forget unless documented)
- [ ] Streams properly disposed in `dispose()` or use `asyncMap` to prevent leaks
- [ ] No callback hell — prefer async/await over `.then()` chains
- [ ] Race conditions prevented (use locks/queues for concurrent access)
- [ ] Null-coalescing operators used with care (understand fallback semantics)

---

## Why These Rules Exist

| Rule Category | Problems Prevented |
|---|---|
| Input Validation | Data corruption, SQL injection, invalid state |
| Null Safety | Crashes, confusing bugs, data loss |
| API/Network | Silent failures, user confusion, retry storms |
| Database | Orphaned records, consistency violations, slow queries |
| Testing | Regressions, edge case bugs, code rot |
| Code Quality | Maintenance burden, hardcoding, inconsistency |
| Async | Memory leaks, dropped updates, race conditions |

---

## Feature Owners: Adapt as Needed

These are **mandatory minimums**. Each feature in `[feature]-constraints.md` may add stricter rules for its specific context.

Example: PDF extraction may require:
- OCR-only routing (no hybrid strategies)
- Zero legacy V1 imports
- Benchmark performance targets

Example: Sync engine may require:
- Last-write-wins conflict resolution (no merge attempts)
- Bidirectional sync with checksum verification
- Offline-first write ordering

**Each feature's specific constraints override these shared rules if stricter.**
