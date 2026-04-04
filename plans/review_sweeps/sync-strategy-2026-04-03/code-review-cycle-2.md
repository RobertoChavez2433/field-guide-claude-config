# Code Review — Cycle 2

**Verdict**: REJECT

All 6 Critical Cycle 1 issues are resolved. 7/7 Significant Cycle 1 issues are resolved. However, 2 new Significant issues and 2 new Minor issues were found.

## Cycle 1 Finding Status

| Finding | Status | Notes |
|---------|--------|-------|
| C1: Phantom import `sync_mode.dart` | FIXED | All imports use `sync_types.dart` |
| C2: Maintenance mode drops background push | FIXED | `_push()` included in maintenance case (line 1034) |
| C3: `catch (_)` silent catch in FCM handler | FIXED | Best-effort Logger.sync() wrapped in inner catch |
| C4: `RealtimeHintHandler.initialize()` DNE | FIXED | Replaced with `subscribe(companyId)` |
| C5: Positional arg for named parameter | FIXED | All `isDirty()` calls use `projectId:` named syntax |
| C6: Test mock `super._testOnly()` | FIXED | All mocks use `super.forTesting(dbService)` |
| S1: Phases 3/4/8 duplicate modifications | FIXED | Phase 4 merged into Phase 3, SKIP markers added |
| S2: SyncEngineFactory 3-way redesign | FIXED | Setter approach canonical |
| S3: SyncInitializer return type contradiction | FIXED | Phase 8.1.4 includes realtimeHintHandler |
| S4: FCM test mock new tracker per access | FIXED | Stored as final field |
| S5: Colors.white hardcoded | FIXED | Uses Theme.of(context).colorScheme.onPrimary |
| S6: Extra dirtyScopeTracker param | FIXED | Constructor calls pass only supabaseClient + syncOrchestrator |
| S7: Getter nullability conflicts | FIXED | Consistently nullable DirtyScopeTracker? |
| M1: Duplicate test coverage | ACCEPTED | Different test files serve different purposes |
| M2: Import path style | MITIGATED | Phase 4 duplicate eliminated |
| M3: Ambiguous import instruction | FIXED | Definitive "add this import" |
| M4: SyncStatusIcon not global | ACCEPTED | Dashboard+Calendar cover primary workflow |
| M5: Line numbers drift | FIXED | Warning note at line 766 |

## New Issues Found

**N1 (Significant): DirtyScopeTracker never wired to SyncEngineFactory**
- Phase 3.2 defines `SyncEngineFactory.setDirtyScopeTracker()`. Phase 3.3.2 stores tracker in `SyncOrchestrator._dirtyScopeTracker`. But no step calls `_engineFactory.setDirtyScopeTracker(_dirtyScopeTracker)`. The factory's tracker stays null. Quick sync pull check `_dirtyScopeTracker != null` always fails. Core dirty-scope optimization is dead code.
- Fix: Add to Phase 3.3.2's fromBuilder constructor body: `if (dirtyScopeTracker != null) { _engineFactory.setDirtyScopeTracker(dirtyScopeTracker!); }`

**N2 (Significant): `Supabase.instance.client` in FcmHandler violates lint A1**
- Plan line 2306: uses `Supabase.instance.client.auth.currentUser?.userMetadata?['company_id']`. Violates lint A1 ("No Supabase.instance.client outside DI root"). The file doesn't import supabase_flutter.
- Fix: Add `SupabaseClient? supabaseClient` to FcmHandler constructor. Use `_supabaseClient?.auth.currentUser?.userMetadata?['company_id']`.

**N3 (Minor): Missing shared_preferences import in fcmBackgroundMessageHandler**
- `SharedPreferences.getInstance()` called but import not listed in step 6.1.2.
- Fix: Add import to step 6.1.2.

**N4 (Minor): Step 7.2.5 note references nonexistent `_testOnly()` constructor**
- Note says "depends on _testOnly() constructor" but code uses `forTesting(dbService)`.
- Fix: Update note text.
