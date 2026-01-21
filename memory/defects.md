# Defects Log

Track Claude's mistakes to prevent repetition. Read before every session.

## Format
### YYYY-MM-DD: [Title]
**Issue**: What went wrong
**Root Cause**: Why
**Prevention**: How to avoid

---

## Logged Defects

### 2026-01-19: Async in dispose()
**Issue**: Called async `_saveIfEditing()` in `dispose()` - context already deactivated
**Fix**: Use `WidgetsBindingObserver.didChangeAppLifecycleState` for lifecycle saves
**Ref**: @lib/features/entries/presentation/screens/home_screen.dart:154-166

### 2026-01-19: Test sort order with same timestamps
**Issue**: Test expected specific sort order but all entries had same `updatedAt`
**Fix**: Use different timestamps in test data when testing sort behavior

### 2026-01-20: Context Used After Async Without Mounted Check
**Issue**: Entry wizard and report screen use context.read() after async gaps
**Root Cause**: Auto-save triggered by lifecycle observer after disposal
**Prevention**: Always check mounted before context after await
**Ref**: @lib/features/entries/presentation/screens/entry_wizard_screen.dart:143

### 2026-01-20: Silent Failure on Entry Creation
**Issue**: Entry creation failure doesn't notify user
**Root Cause**: No error handling in else branch of null check
**Prevention**: Always handle both success and failure branches
**Ref**: @lib/features/entries/presentation/screens/entry_wizard_screen.dart:217

### 2026-01-20: ProjectProvider Unsafe firstWhere
**Issue**: selectProject() and toggleActive() use unsafe .first and unchecked firstWhere
**Root Cause**: .first on empty list throws, unchecked firstWhere throws
**Prevention**: Always check isNotEmpty before .first, add orElse to firstWhere
**Ref**: @lib/features/projects/presentation/providers/project_provider.dart:118-121,229

### 2026-01-20: Hardcoded Supabase Credentials
**Issue**: Supabase URL and anon key committed to git
**Root Cause**: Config stored as const instead of environment variables
**Prevention**: Use --dart-define or environment variables
**Ref**: @lib/core/config/supabase_config.dart:6-7

### 2026-01-20: Sync Queue Silent Deletion
**Issue**: Items deleted after max retries without persistent record
**Root Cause**: No dead letter queue for permanently failed syncs
**Prevention**: Always preserve failed operations for manual review
**Ref**: @lib/services/sync_service.dart:283-291

### 2026-01-20: Migration ALTER TABLE Without Error Handling
**Issue**: v7→v8 migration crashes if columns already exist
**Root Cause**: SQLite doesn't support IF NOT EXISTS for columns
**Prevention**: Check column existence before ALTER TABLE
**Ref**: @lib/core/database/database_service.dart:435-443

### 2026-01-20: _pushBaseData Queries All Tables Every Sync
**Issue**: Makes 11 remote queries EVERY sync even after initial seed
**Root Cause**: No flag to track "initial seed complete"
**Prevention**: Use metadata table to track initialization state
**Ref**: @lib/services/sync_service.dart:302-473

<!-- Add new defects above this line -->
