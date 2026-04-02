# Defects Integration

How to use and create GitHub Issues for defect tracking during debugging. Integrates with the Logger-based investigation workflow.

## Before Debugging

**ALWAYS check GitHub Issues for the relevant feature first.**

The bug you're looking at might be a known pattern.

### Check Process

1. Query open issues for the feature:
   ```bash
   gh issue list --repo RobertoChavez2433/construction-inspector-tracking-app --label "{feature}" --state open --json number,title,body --limit 20
   ```
2. Search for related categories in issue titles: `[ASYNC]`, `[SYNC]`, `[DATA]`, `[CONFIG]`, `[SCHEMA]`, `[FLUTTER]`, `[E2E]`, `[MIGRATION]`
3. If pattern exists, apply the documented prevention from the issue body

### Example Check

Debugging: "Sync adapter pushing wrong column data"

1. `gh issue list --label "sync" --state open --json number,title --limit 20`
2. Find: `#42 [SYNC] Type Converter Mismatch`
3. Read issue body: `gh issue view 42 --json body`
4. Check: Does the adapter's toSupabaseMap() strip local-only columns?
5. Apply: Verify TypeConverters alignment

## During Debugging

### Pattern Recognition

As you investigate, note patterns that match existing issues:

```markdown
**Observed**: setState called after await
**Matches**: GitHub Issue #NN [ASYNC] Async Context Safety
**Prevention applied**: Added mounted check
```

### New Pattern Discovery

If you discover a pattern NOT in existing GitHub Issues:

1. Document the pattern immediately (even before fixing)
2. Create the issue after fix is confirmed (Phase 10)

## After Fix

**ALWAYS create a GitHub Issue for new patterns.**

### Creating Defect Issues

```bash
pwsh -File tools/create-defect-issue.ps1 `
    -Title "[CATEGORY] YYYY-MM-DD: Brief Title" `
    -Feature "{feature}" `
    -Type "defect" `
    -Priority "{priority}" `
    -Layer @("{layer:...}") `
    -Body "**Pattern**: What causes the issue`n**Prevention**: How to avoid it`n**Logger signal**: {relevant Logger call}" `
    -Ref "@path/to/relevant/file.dart"
```

### Categories

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

## Defect Lifecycle

```
1. DISCOVER during debugging
   └─> Note pattern immediately

2. VERIFY fix works
   └─> Create GitHub Issue via create-defect-issue.ps1

3. PREVENT in future
   └─> Reference in code reviews
   └─> Check via gh issue list before similar work

4. CLOSE when resolved
   └─> gh issue close <number> --comment "Fixed in session N"
```

## Quick Reference

```bash
# List all open defects for a feature
gh issue list --repo RobertoChavez2433/construction-inspector-tracking-app --label "{feature}" --state open

# List all open blockers
gh issue list --repo RobertoChavez2433/construction-inspector-tracking-app --label "blocker" --state open

# View a specific issue
gh issue view <number> --repo RobertoChavez2433/construction-inspector-tracking-app

# Close a resolved issue
gh issue close <number> --repo RobertoChavez2433/construction-inspector-tracking-app --comment "Resolved"

# Create a new defect
pwsh -File tools/create-defect-issue.ps1 -Title "..." -Feature "..." -Type defect -Priority medium -Layer @("layer:...") -Body "..." -Ref "..."
```

---

## Log Server Integration

When using the debug server during investigation, cross-reference log evidence with GitHub Issues.

### Connecting defects to log evidence

When the server returns an error log entry, check if it matches a known defect pattern:

```bash
curl "http://127.0.0.1:3947/logs?category=error&last=20"
```

If the error message matches a known `[CATEGORY]` pattern in an open GitHub Issue, apply the documented prevention rather than starting fresh investigation.

### Logger categories map to defect categories

| Logger Category | Defect Category |
|-----------------|-----------------|
| `Logger.sync()` | `[SYNC]` |
| `Logger.db()` | `[SCHEMA]`, `[MIGRATION]`, `[DATA]` |
| `Logger.auth()` | `[CONFIG]` |
| `Logger.error()` | Any category |
| `Logger.lifecycle()` | `[ASYNC]` |

### Recording log patterns in defect issues

When creating a new defect issue, include the Logger call that would have caught it earlier in the body:

```
**Logger signal**: Logger.sync('SyncEngine.push.skipped') missing from error log when pendingCount > 0
```
