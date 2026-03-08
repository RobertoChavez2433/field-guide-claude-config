# Systematic Debugging Skill — Full Overhaul

**Date**: 2026-03-07
**Status**: Approved
**Scope**: Complete modernization of `.claude/skills/systematic-debugging/` + `.codex/skills/systematic-debugging.md`

## Goals

1. **Modernize for current stack** — Replace all Patrol references with ADB/UIAutomator, update sync patterns for new SyncEngine architecture
2. **Strengthen behavioral guardrails** — Tighter methodology, better rationalization prevention
3. **Nothing left behind** — Every file reviewed, every stale reference caught

## Decisions Made (Brainstorming Session)

| Decision | Choice |
|----------|--------|
| Pressure tests | Remove all 3 (production-emergency, sunk-cost, authority-pressure) |
| Condition-based-waiting | Rewrite for ADB/UIAutomator |
| Defense-in-depth | Complete rewrite with new 5-layer model including sync/data layer |
| Root-cause tracing | Update existing 5 traces + add 5 sync engine traces, reorder by frequency |
| Debug commands | Update + expand significantly (sync engine, ADB, SQLite queries) |
| Codex wrapper | Keep both files, update wrapper to stay in sync |
| Defects integration | Add SYNC/MIGRATION/SCHEMA categories, reference actual per-feature files |

## What Does NOT Change

- Core 4-phase framework (Iron Law, Phase 1-4)
- Red Flags section
- Stop Conditions section
- Rationalization Prevention table
- "Your Human Partner's Signals" section
- "Before Starting: Use Existing Results" guard
- Anti-Patterns table
- Quick Reference table
- Frontmatter (name, description, context, agent, user-invocable)

---

## Phase 1: SKILL.md Update

**File**: `.claude/skills/systematic-debugging/SKILL.md`
**Agent**: frontend-flutter-specialist-agent (knows the codebase patterns)

### Changes:

1. **Flutter-Specific Debug Commands section** — Replace entirely with:
```bash
# Static analysis
pwsh -Command "flutter analyze"

# Full test suite
pwsh -Command "flutter test"

# Verbose test output
pwsh -Command "flutter test --verbose"

# Specific test with logging
pwsh -Command "flutter test test/path/file.dart -r expanded"

# Sync engine debugging — check pending changes
sqlite3 app.db "SELECT * FROM change_log WHERE synced = 0;"

# Sync engine debugging — inspect sync_queue status
sqlite3 app.db "SELECT table_name, operation, status FROM sync_queue ORDER BY created_at DESC LIMIT 20;"

# Sync engine debugging — verify FK integrity
sqlite3 app.db "PRAGMA foreign_key_check;"

# Sync engine debugging — check adapter registration order
# (trace through SyncRegistry.registerSyncAdapters() in lib/features/sync/engine/sync_registry.dart)

# ADB-based E2E debugging
adb logcat -s flutter | grep -i error
adb shell uiautomator dump /dev/tty
```

2. **Phase 1, step 4** — Update data flow reference from generic to:
   `Screen → Provider → Repository → Datasource → SQLite → SyncEngine → Supabase`

3. **Remove "Pressure Test Scenarios" section** — Delete the entire section that references `references/pressure-tests/`

4. **Keep everything else unchanged** — Iron Law, phases, red flags, stop conditions, anti-patterns, etc.

### Verification:
- No references to `patrol` anywhere in the file
- All `flutter` commands wrapped in `pwsh -Command "..."`
- Pressure test section gone
- Data flow matches actual architecture

---

## Phase 2: Root-Cause Tracing Update

**File**: `.claude/skills/systematic-debugging/references/root-cause-tracing.md`
**Agent**: frontend-flutter-specialist-agent

### Changes:

1. **Keep unchanged**: Five Whys framework, Tracing Template, Evidence Collection table, Red Flags in Tracing table

2. **Update existing trace path #4 (Test Flakiness)** — Rewrite from Patrol context:
```
Symptom: Test passes/fails randomly
  -> Timing-dependent assertion?
    -> Widget not settled before expect?
      -> Missing pumpAndSettle or runAsync?
        -> ROOT: Async operation not awaited before assertion
```

3. **Update existing trace path #5 (Supabase Sync Failure)** — Rewrite for new engine:
```
Symptom: Data not syncing
  -> SyncOrchestrator triggering engine?
    -> SyncEngine.push() completing?
      -> TableAdapter.pushChanges() succeeding?
        -> ROOT: RLS policy blocking, or adapter toSupabaseMap() stripping required column
```

4. **Add 5 new trace paths** after the existing 5:

**#6: Sync Adapter Failure**
```
Symptom: Table data not syncing
  -> SyncEngine.push() skipping table?
    -> Adapter registered in SyncRegistry?
      -> FK dependency order correct?
        -> ROOT: Adapter missing from registerSyncAdapters() or wrong order
```

**#7: Migration/Schema Drift**
```
Symptom: App crashes on startup after update
  -> DatabaseService.open() failing?
    -> Schema version mismatch?
      -> Migration step missing or incomplete?
        -> ROOT: v{N} migration doesn't match expected schema
```

**#8: FK Constraint Violation**
```
Symptom: Insert/update fails with FOREIGN KEY constraint
  -> Child record referencing nonexistent parent?
    -> Parent deleted before child? (soft-delete cascade)
      -> Change tracker missed dependency?
        -> ROOT: Cascade delete trigger not covering this relationship
```

**#9: Change Tracker Drift**
```
Symptom: Edits not appearing in sync queue
  -> change_log trigger firing?
    -> Trigger installed on this table?
      -> Column in excluded list?
        -> ROOT: SQLite trigger missing or filtering out the column
```

**#10: Provider State Stale After Sync**
```
Symptom: UI shows old data after sync completes
  -> SyncProvider notifying listeners?
    -> Feature provider listening to sync events?
      -> Provider reloading from DB after sync?
        -> ROOT: Feature provider not calling loadItems() on sync completion
```

### Verification:
- 10 trace paths total (5 existing updated + 5 new)
- No Patrol references
- Sync engine traces reference real classes (SyncEngine, SyncRegistry, TableAdapter, SyncOrchestrator)

---

## Phase 3: Defense-in-Depth Complete Rewrite

**File**: `.claude/skills/systematic-debugging/references/defense-in-depth.md`
**Agent**: frontend-flutter-specialist-agent

### New Structure:

**Title**: Defense in Depth — Five-layer validation strategy to catch bugs before they escape.

**Layer 1: Static Analysis** — Catch bugs at compile time
- `pwsh -Command "flutter analyze"` / `dart fix --apply`
- Catches: type mismatches, null safety violations, unused imports, deprecated API, missing awaits
- Action: Run before every commit. Zero tolerance.

**Layer 2: Unit Tests** — Catch logic bugs in isolation
- Model serialization, repository CRUD, business rules
- Sync adapter tests (16 adapters in `test/features/sync/adapters/`)
- Engine component tests (change_tracker, conflict_resolver, integrity_checker, sync_mutex)
- Schema/migration tests (`test/features/sync/schema/`)
- Trigger behavior tests (`test/features/sync/triggers/`)
- Command: `pwsh -Command "flutter test test/"`
- Coverage targets: Models 100% serialization, adapters 100% mapping, engine components happy + error paths

**Layer 3: Widget Tests** — Catch UI and state management bugs
- Provider state, screen rendering, form validation, navigation
- Mock dependencies (MockDatabase, mock repositories from `test/helpers/`)
- Command: `pwsh -Command "flutter test test/features/"`
- Key patterns: `pumpWidget`, `pumpAndSettle`, mock dependency injection

**Layer 4: ADB-Based E2E Tests** — Catch real-world user flow bugs
- `/test` skill with flow registry
- UIAutomator element finding + Claude vision verification
- Logcat monitoring after every interaction
- Real device, real permissions, real network
- Key patterns: Use TestingKeys (per-feature key classes), never hardcoded strings

**Layer 5: Sync/Data Integrity** — Catch sync engine and data layer bugs
- `PRAGMA foreign_key_check` — FK integrity
- `change_log` inspection — trigger coverage
- `sync_queue` status — pending operations
- IntegrityChecker — orphan detection, constraint validation
- SchemaVerifier — migration correctness
- Adapter integration tests (`test/features/sync/engine/adapter_integration_test.dart`)

**Layer Priority During Debug** (decision tree):
```
1. Does it pass static analysis?
   NO → Fix analysis errors first

2. Do unit/adapter tests pass?
   NO → Bug is in business logic or sync mapping

3. Do widget tests pass?
   NO → Bug is in UI/state layer

4. Do E2E flows pass on device?
   NO → Bug is in integration/real-world flow

5. Does data integrity hold after sync?
   NO → Bug is in sync engine, triggers, or schema
```

**Defensive Coding Patterns** — 4 examples:
1. Null Safety Defense (keep existing Dart example)
2. Async Safety Defense (keep existing Dart example)
3. State Mutation Defense (keep existing Dart example)
4. **NEW — Sync Safety Defense**:
```dart
// Layer 1: Adapter validates before push
Map<String, dynamic> toSupabaseMap(Map<String, dynamic> row) {
  assert(row['id'] != null, 'Cannot sync row without id');
  return {...row}..remove('change_log_id');
}

// Layer 2: Engine checks FK order
// SyncRegistry enforces push order: projects → locations → daily_entries → ...

// Layer 3: IntegrityChecker post-sync
await integrityChecker.checkOrphans(db);
```

**Regression Prevention** (keep existing 4 steps)

### Verification:
- 5 layers clearly defined
- No Patrol references
- All test paths reference real directories
- Sync layer references real classes and files

---

## Phase 4: Condition-Based Waiting Rewrite

**File**: `.claude/skills/systematic-debugging/references/condition-based-waiting.md`
**Agent**: frontend-flutter-specialist-agent

### New Structure:

**Keep**: Iron Law ("NEVER USE HARDCODED DELAYS. WAIT FOR CONDITIONS.")

**Sections**:

1. **ADB Element Polling** — Wait for UI elements via uiautomator dump
```bash
# Poll for element by text
while ! adb shell uiautomator dump /dev/tty | grep -q "Save"; do
  sleep 1
done

# Poll for element by content-desc (Flutter Key)
while ! adb shell uiautomator dump /dev/tty | grep -q 'content-desc="save_button"'; do
  sleep 1
done
```

2. **Screenshot-Based Verification** — Wait for visual state via Claude vision
```bash
# Capture and verify screen state
adb exec-out screencap -p > screenshot.png
# Pass to Claude vision for verification
```

3. **Logcat-Based Waiting** — Wait for Flutter log output
```bash
# Wait for specific log message
adb logcat -s flutter | grep -m 1 "Sync completed"

# Wait for error absence (no new errors for 3s)
timeout 3 adb logcat -s flutter | grep -i error
```

4. **Widget Test Patterns** (kept from current, still relevant)
```dart
await tester.pumpAndSettle();
await tester.pump(Duration(milliseconds: 300));
expect(find.byType(LoadingIndicator), findsNothing);
```

5. **Async Operation Patterns** (generalized)
```dart
await tester.runAsync(() async {
  await provider.syncData();
});
await tester.pumpAndSettle();
```

6. **Common Waiting Scenarios** — Rewritten for ADB context:
   - Loading states: poll logcat for "loaded" / screenshot check
   - Navigation transitions: poll uiautomator for new screen element
   - Form submission: poll for success element after tap

7. **Debugging Flaky Waits** — Rewritten for ADB:
   - Check element exists in XML dump
   - Increase poll interval temporarily
   - Add intermediate logcat checkpoints

8. **Anti-Patterns table** — Updated:
   | Anti-Pattern | Problem | Solution |
   |---|---|---|
   | `sleep N` in test scripts | Arbitrary, slow, flaky | Poll for condition |
   | Very long ADB timeouts | Hides real problems | Find what's slow |
   | Retry loops without limits | Infinite hang risk | Add max attempts |
   | Ignoring logcat errors | Misses Flutter exceptions | Check logcat after every ADB action |

9. **When Delays Are Acceptable** (kept, still valid)

### Verification:
- Zero Patrol references ($, waitUntilVisible, waitUntilGone, scrollTo all gone)
- ADB patterns match what the /test skill actually does
- Widget test patterns still present for unit/widget test debugging

---

## Phase 5: Defects Integration Update

**File**: `.claude/skills/systematic-debugging/references/defects-integration.md`
**Agent**: frontend-flutter-specialist-agent

### Changes:

1. **Update categories table** — Add 3 new categories:
   | Category | Use For |
   |----------|---------|
   | `[ASYNC]` | Context safety, dispose issues, Future handling |
   | `[E2E]` | ADB/UIAutomator testing patterns, TestingKeys, waits |
   | `[FLUTTER]` | Widget lifecycle, Provider, setState |
   | `[DATA]` | Repository, collection access, null safety |
   | `[CONFIG]` | Supabase, environment, credentials |
   | `[SYNC]` | SyncEngine, adapters, change tracker, conflict resolution |
   | `[MIGRATION]` | Schema versions, migration steps, DatabaseService upgrades |
   | `[SCHEMA]` | FK constraints, trigger behavior, table structure, SchemaVerifier |

2. **Update `[E2E]` description** — Change from "Patrol testing patterns" to "ADB/UIAutomator testing patterns"

3. **Add actual per-feature defect file listing** to Quick Reference:
```bash
# All 15 active per-feature defect files:
.claude/defects/_defects-auth.md
.claude/defects/_defects-contractors.md
.claude/defects/_defects-dashboard.md
.claude/defects/_defects-database.md
.claude/defects/_defects-entries.md
.claude/defects/_defects-forms.md
.claude/defects/_defects-locations.md
.claude/defects/_defects-pdf.md
.claude/defects/_defects-photos.md
.claude/defects/_defects-projects.md
.claude/defects/_defects-quantities.md
.claude/defects/_defects-settings.md
.claude/defects/_defects-sync.md
.claude/defects/_defects-toolbox.md
.claude/defects/_defects-weather.md
```

4. **Update example in "Before Debugging"** — Replace Patrol-era example:
```markdown
Debugging: "Sync adapter pushing wrong column data"

1. Open `.claude/defects/_defects-sync.md`
2. Search for "adapter", "column", "push"
3. Find: `[SYNC] 2026-03-01: Type Converter Mismatch`
4. Check: Does the adapter's toSupabaseMap() strip local-only columns?
5. Apply: Verify TypeConverters alignment
```

### Verification:
- 8 categories total (5 original + 3 new)
- E2E category updated from Patrol to ADB
- All 15 real defect files listed
- Example uses current architecture terminology

---

## Phase 6: Deletions

**Agent**: frontend-flutter-specialist-agent (or inline)

### Delete files:
1. `.claude/skills/systematic-debugging/references/pressure-tests/production-emergency.md`
2. `.claude/skills/systematic-debugging/references/pressure-tests/sunk-cost-exhaustion.md`
3. `.claude/skills/systematic-debugging/references/pressure-tests/authority-pressure.md`
4. `.claude/skills/systematic-debugging/references/pressure-tests/` (directory)

### Verification:
- No files remain in `references/pressure-tests/`
- No references to pressure tests in SKILL.md
- No broken `@` references anywhere

---

## Phase 7: Codex Wrapper Update

**File**: `.codex/skills/systematic-debugging.md`
**Agent**: frontend-flutter-specialist-agent

### Changes:
- Light sync pass — ensure the wrapper's "Behavior Rules", "Required Context First", and "Preferred Workflow" sections align with any SKILL.md changes
- Verify "Upstream Reference" still points to correct path
- No structural changes — wrapper stays thin by design

### Verification:
- Wrapper references match SKILL.md structure
- No stale Patrol or old sync references leaked into wrapper

---

## Cross-Cutting Verification (All Phases Complete)

After all phases:
1. `grep -r "patrol" .claude/skills/systematic-debugging/` → zero results
2. `grep -r "patrol" .codex/skills/systematic-debugging.md` → zero results
3. `grep -r "waitUntilVisible\|waitUntilGone\|\$(" .claude/skills/systematic-debugging/` → zero results (Patrol API)
4. All `@` references in SKILL.md point to files that exist
5. Every `flutter` command wrapped in `pwsh -Command "..."`
6. Sync engine classes referenced match actual codebase (SyncEngine, SyncRegistry, TableAdapter, SyncOrchestrator, ChangeTracker, ConflictResolver, IntegrityChecker)
