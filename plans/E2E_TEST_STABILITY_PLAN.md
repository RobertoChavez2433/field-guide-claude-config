# E2E Test Stability Plan (Revised)

**Source**: Analysis of `E2E_TEST_STABILITY_PLAN.md` and current test infrastructure
**Status**: Ready for implementation

## Goals
- Unblock execution (no hangs on first test)
- Make results deterministic across devices and CI
- Keep flake rate <= 5% on 3 consecutive runs
- Eliminate brittle waits and uncontrolled background work

## Current Infrastructure (Already Exists)
| Component | Status | Location |
|-----------|--------|----------|
| PatrolTestHelpers | Complete | `patrol/helpers/patrol_test_helpers.dart` (638 lines) |
| TestSeedData | Complete | `patrol/fixtures/test_seed_data.dart` |
| TestDatabaseHelper | Complete | `patrol/helpers/test_database_helper.dart` |
| PatrolTestConfig | Complete | `patrol/test_config.dart` |
| TestingKeys | Complete | `lib/shared/testing_keys.dart` |
| App Test Mode | **MISSING** | `lib/main.dart` |

## pumpAndSettle Usage
- **Helpers**: 30 calls
- **E2E Tests**: 252 calls
- **Total**: 282 calls to migrate

---

## Phase 1: Unblock Test Execution (2 PRs)

### PR-1A: Add Wait Helpers + Fix Helper File
**Goal**: Create replacement utilities and fix the helper file first
**Scope**: Small, low risk

**Files to Modify**:
- `integration_test/patrol/helpers/patrol_test_helpers.dart`

**Changes**:
1. Add `waitForAppReady()` - pumps + waits for navigation bar or login screen
2. Add `waitForScreen(Key screenKey)` - waits for specific screen key
3. Add `waitWithTimeout(finder, {Duration timeout})` - capped retry with diagnostics
4. Replace all 30 `pumpAndSettle` calls in helper methods with new utilities

**Verification**:
```bash
grep -c "pumpAndSettle" integration_test/patrol/helpers/patrol_test_helpers.dart
# Should return 0
```

---

### PR-1B: Migrate app_smoke_test.dart (Unblocks All Testing)
**Goal**: Get first test file running without hangs
**Scope**: Small, critical path
**Depends on**: PR-1A

**Files to Modify**:
- `integration_test/patrol/e2e_tests/app_smoke_test.dart`

**Changes**:
1. Replace all `pumpAndSettle` with `helpers.waitForAppReady()` or explicit waits
2. Use `$.pump()` + `waitUntilVisible()` pattern
3. Add timeout diagnostics on failure

**Verification**:
```bash
patrol test -t integration_test/patrol/e2e_tests/app_smoke_test.dart
# Should complete without hanging
```

---

## Phase 2: App Test Mode (2 PRs)

### PR-2A: Add Test Mode Flag + Timer Control
**Goal**: Let the app know it's being tested and disable problematic timers
**Scope**: Medium
**Depends on**: PR-1B (so we can verify)

**Files to Modify**:
- `lib/main.dart` - Add test mode detection
- `lib/features/sync/presentation/providers/sync_provider.dart` - Guard sync timer
- `lib/features/weather/presentation/providers/weather_provider.dart` - Guard refresh timer

**Changes**:
1. Add `TestModeConfig` class in main.dart:
   ```dart
   class TestModeConfig {
     static bool get isTestMode =>
       const bool.fromEnvironment('PATROL_TEST', defaultValue: false);
   }
   ```
2. Guard `Timer.periodic` calls with `if (!TestModeConfig.isTestMode)`
3. Skip auth heartbeat/presence updates in test mode

**Verification**:
```bash
patrol test -t integration_test/patrol/e2e_tests/app_smoke_test.dart
# Should complete faster than before
```

---

### PR-2B: Disable Animations in Test Mode
**Goal**: Reduce frame callbacks from animations
**Scope**: Small
**Depends on**: PR-2A

**Files to Modify**:
- `lib/main.dart` - Add animation disable
- `lib/core/theme/app_theme.dart` - Conditional animation durations

**Changes**:
1. Set `timeDilation = 0.0` or use `TickerMode.disableFor()` in test mode
2. Replace animated loading indicators with static versions when testing
3. Reduce default animation curves to instant

**Verification**:
- Visual: App should appear instant in test mode
- Functional: Tests complete faster

---

## Phase 3: Migrate Remaining Tests (4 PRs)

### PR-3A: Migrate Auth + Navigation Tests
**Scope**: ~50 pumpAndSettle calls
**Depends on**: PR-2A

**Files**:
- `integration_test/patrol/e2e_tests/auth_flow_test.dart`
- `integration_test/patrol/e2e_tests/navigation_flow_test.dart`

---

### PR-3B: Migrate Entry Tests
**Scope**: ~80 pumpAndSettle calls
**Depends on**: PR-3A

**Files**:
- `integration_test/patrol/e2e_tests/entry_lifecycle_test.dart`
- `integration_test/patrol/e2e_tests/entry_management_test.dart`

---

### PR-3C: Migrate Project + Contractor Tests
**Scope**: ~50 pumpAndSettle calls
**Depends on**: PR-3B

**Files**:
- `integration_test/patrol/e2e_tests/project_management_test.dart`
- `integration_test/patrol/e2e_tests/contractors_flow_test.dart`
- `integration_test/patrol/e2e_tests/quantities_flow_test.dart`

---

### PR-3D: Migrate Remaining Tests
**Scope**: ~40 pumpAndSettle calls
**Depends on**: PR-3C

**Files**:
- `integration_test/patrol/e2e_tests/settings_theme_test.dart`
- `integration_test/patrol/e2e_tests/offline_sync_test.dart`
- `integration_test/patrol/e2e_tests/photo_flow_test.dart`

**Verification** (all Phase 3):
```bash
grep -rn "pumpAndSettle" integration_test/patrol/e2e_tests/
# Should return 0 results
patrol test -t integration_test/patrol/e2e_tests/
# Full suite should run without hanging
```

---

## Phase 4: Deterministic State (2 PRs)

### PR-4A: State Reset + SharedPreferences Cleanup
**Goal**: Ensure clean slate for each test run
**Scope**: Small
**Depends on**: Phase 3 complete

**Files to Modify**:
- `integration_test/patrol/helpers/test_database_helper.dart` - Add prefs clearing
- `integration_test/patrol/test_config.dart` - Add global setup

**Changes**:
1. Add `clearSharedPreferences()` to test helper
2. Add `resetAllState()` method combining DB clear + prefs clear
3. Call in `setUpAll` of each test file

**Note**: TestSeedData and TestDatabaseHelper already exist and are comprehensive. This PR adds missing state (SharedPreferences, cache directories).

---

### PR-4B: Fixed Clock/Time Provider
**Goal**: Eliminate date-dependent test failures
**Scope**: Small
**Depends on**: PR-4A

**Files to Create/Modify**:
- `lib/shared/time_provider.dart` - Abstract time provider
- `lib/main.dart` - Inject time provider

**Changes**:
1. Create `TimeProvider` interface with `now()` method
2. Create `RealTimeProvider` and `FixedTimeProvider` implementations
3. Use `FixedTimeProvider` in test mode with deterministic timestamp

---

## Phase 5: Service Stubs (3 PRs)

### PR-5A: Mock Supabase Auth
**Goal**: Run auth tests without network
**Scope**: Medium
**Depends on**: PR-2A

**Files to Create**:
- `integration_test/patrol/mocks/mock_supabase_auth.dart`

**Changes**:
1. Create mock auth client with pre-configured responses
2. Auto-login functionality for test mode
3. Mock session management

---

### PR-5B: Mock Weather API
**Goal**: Eliminate weather API flakiness
**Scope**: Small
**Depends on**: PR-5A

**Files to Create**:
- `integration_test/patrol/mocks/mock_weather_service.dart`

**Changes**:
1. Return deterministic weather data
2. No network calls

---

### PR-5C: Mock Supabase Data
**Goal**: Full offline capability for tests
**Scope**: Medium
**Depends on**: PR-5B

**Files to Create**:
- `integration_test/patrol/mocks/mock_supabase_client.dart`

**Changes**:
1. Mock data queries
2. Mock sync operations
3. Return seed data

---

## Phase 6: Device/Permissions (2 PRs)

### PR-6A: Permission Automation
**Goal**: Auto-grant permissions in tests
**Scope**: Small
**Depends on**: Phase 3 complete

**Files to Modify**:
- `integration_test/patrol/helpers/patrol_test_helpers.dart`

**Changes**:
1. Add `autoGrantAllPermissions()` helper using Patrol native
2. Call in test setup before app launch
3. Handle camera, location, storage, photos

---

### PR-6B: Preflight Checklist + Documentation
**Goal**: Document device setup requirements
**Scope**: Small, documentation
**Depends on**: PR-6A

**Files to Create**:
- `integration_test/README.md` or `.claude/docs/e2e-test-setup.md`

**Changes**:
1. Device animation scale settings
2. Battery saver/power mode
3. Locale/timezone requirements
4. Clean run instructions (kill app, clear data, remove lock files)

---

## Phase 7: Test Hygiene (2 PRs)

### PR-7A: Enforce Key-Only Selectors
**Goal**: Eliminate brittle text/icon selectors
**Scope**: Medium
**Depends on**: Phase 3 complete

**Files to Modify**:
- All E2E test files

**Changes**:
1. Replace `find.text()` with `$(TestingKeys.xxx)` for actions
2. Keep `find.text()` only for content assertions
3. Add missing keys to `TestingKeys` as needed

**Verification**:
```bash
grep -rn "find\.text" integration_test/patrol/e2e_tests/ | grep -v "expect"
# Should return 0 (only assertion usage remains)
```

---

### PR-7B: Test Independence Audit
**Goal**: Ensure tests don't depend on each other
**Scope**: Small
**Depends on**: PR-7A

**Changes**:
1. Verify each test file has its own setup/teardown
2. Remove shared mutable state between tests
3. Run tests in random order to verify

**Verification**:
```bash
patrol test -t integration_test/patrol/e2e_tests/ --shuffle
# All tests should pass
```

---

## Phase 8: CI Integration (1 PR)

### PR-8: CI Guardrails
**Goal**: Prevent regression and track flakes
**Scope**: Medium
**Depends on**: All previous phases

**Files to Create/Modify**:
- `.github/workflows/e2e-tests.yml` (or equivalent CI config)

**Changes**:
1. Lint rule to fail on new `pumpAndSettle` in E2E tests
2. Run smoke test on every PR
3. Nightly full suite with 3x repetition
4. Screenshot capture on failure
5. Flake rate tracking

---

## PR Dependency Graph

```
PR-1A (Wait Helpers)
  └── PR-1B (Smoke Test) ← UNBLOCKS TESTING
        ├── PR-2A (Test Mode Flag)
        │     ├── PR-2B (Animations)
        │     └── PR-5A (Mock Auth)
        │           └── PR-5B (Mock Weather)
        │                 └── PR-5C (Mock Data)
        └── PR-3A (Auth/Nav Tests)
              └── PR-3B (Entry Tests)
                    └── PR-3C (Project Tests)
                          └── PR-3D (Remaining Tests)
                                ├── PR-4A (State Reset)
                                │     └── PR-4B (Fixed Clock)
                                ├── PR-6A (Permissions)
                                │     └── PR-6B (Docs)
                                └── PR-7A (Key Selectors)
                                      └── PR-7B (Independence)
                                            └── PR-8 (CI)
```

## Priority Order

| Priority | PR | Why |
|----------|-----|-----|
| 1 | PR-1A | Foundation for all other work |
| 2 | PR-1B | **Unblocks all testing** |
| 3 | PR-2A | Makes remaining migration easier |
| 4 | PR-3A-3D | Core test migration |
| 5 | PR-2B, PR-4A-4B | Quality improvements |
| 6 | PR-5A-5C | Network independence |
| 7 | PR-6A-6B, PR-7A-7B | Polish |
| 8 | PR-8 | CI guardrails |

## Success Criteria
- `app_smoke_test.dart` completes consistently on real device
- Full suite completes 3x in a row with <= 5% failure rate
- No `pumpAndSettle` in E2E tests or helpers
- All E2E selectors use `TestingKeys`
- Tests pass in random order

## Total PRs: 17
**Critical Path**: PR-1A → PR-1B → PR-2A → PR-3A-3D (7 PRs to full migration)
