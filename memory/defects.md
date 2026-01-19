# Defects Log

Track Claude's mistakes to prevent repetition. Read before every session.

## Format
### YYYY-MM-DD: [Title]
**Issue**: What went wrong
**Root Cause**: Why
**Prevention**: How to avoid

---

## Logged Defects

@.claude/rules/defects.md

### 2026-01-19: Async in dispose()
**Issue**: Called async `_saveIfEditing()` in `dispose()` - context already deactivated
**Fix**: Use `WidgetsBindingObserver.didChangeAppLifecycleState` for lifecycle saves
**Ref**: @lib/features/entries/presentation/screens/home_screen.dart:154-166

### 2026-01-19: Test sort order with same timestamps
**Issue**: Test expected specific sort order but all entries had same `updatedAt`
**Fix**: Use different timestamps in test data when testing sort behavior

<!-- Add new defects above this line -->
