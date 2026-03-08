# Defects Integration

How to use and update per-feature defect files during debugging.

## Before Debugging

**ALWAYS check the relevant feature's defect file first.**

The bug you're looking at might be a known pattern.

### Check Process

1. Read `.claude/defects/_defects-{feature}.md` for the feature you're debugging
2. Search for related categories:
   - `[ASYNC]` - Context safety, dispose issues
   - `[E2E]` - ADB/UIAutomator testing patterns
   - `[FLUTTER]` - Widget, Provider patterns
   - `[DATA]` - Repository, collection access
   - `[CONFIG]` - Supabase, credentials, environment
   - `[SYNC]` - SyncEngine, adapters, change tracker
   - `[MIGRATION]` - Schema versions, migration steps
   - `[SCHEMA]` - FK constraints, triggers, table structure
3. If pattern exists, apply the documented prevention

### Example Check

Debugging: "Sync adapter pushing wrong column data"

1. Open `.claude/defects/_defects-sync.md`
2. Search for "adapter", "column", "push"
3. Find: `[SYNC] 2026-03-01: Type Converter Mismatch`
4. Check: Does the adapter's toSupabaseMap() strip local-only columns?
5. Apply: Verify TypeConverters alignment

## During Debugging

### Pattern Recognition

As you investigate, note patterns that match existing defects:

```markdown
**Observed**: setState called after await
**Matches**: [ASYNC] Async Context Safety
**Prevention applied**: Added mounted check
```

### New Pattern Discovery

If you discover a pattern NOT in the feature's defect file:

1. Document the pattern immediately (even before fixing)
2. Use the standard format
3. Include prevention strategy

## After Fix

**ALWAYS log new patterns to the relevant feature's defect file.**

### Adding New Defects

Location: `.claude/defects/_defects-{feature}.md`

Format:
```markdown
### [CATEGORY] YYYY-MM-DD: Brief Title
**Pattern**: What causes the issue
**Prevention**: How to avoid it
**Ref**: @path/to/relevant/file.dart (optional)
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

### Example Entry

```markdown
### [ASYNC] 2026-02-01: Timer Callback After Dispose
**Pattern**: Timer.periodic callback runs after widget disposed
**Prevention**: Cancel timer in dispose(); use mounted check in callback
**Ref**: @lib/features/sync/presentation/widgets/sync_status_icon.dart
```

## Defect Lifecycle

```
1. DISCOVER during debugging
   └─> Document pattern immediately

2. VERIFY fix works
   └─> Add to .claude/defects/_defects-{feature}.md

3. PREVENT in future
   └─> Reference in code reviews
   └─> Check before similar work

4. ARCHIVE when limit reached
   └─> Oldest defects archived to .claude/logs/defects-archive.md
```

## Using Defects in Code Review

When reviewing code, cross-reference the feature's defect file:

```markdown
## Code Review Notes

Checked against known defects (_defects-entries.md):
- [ASYNC] Async Context Safety: ✓ Mounted checks present
- [E2E] TestingKeys Defined But Not Wired: ✓ Keys wired to widgets
- [DATA] Unsafe Collection Access: ⚠️ Line 45 uses .first without check
```

## Defects Limit

Each feature defect file has a max of 5 active defects.

When adding new defects:
- If at 5, oldest is auto-archived to `.claude/logs/defects-archive.md`
- Keep most relevant/recent patterns active
- Recurring patterns should stay active longer

## Quick Reference

### Per-Feature Defect Files

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

### Common Commands

```bash
# View PDF defects
Read .claude/defects/_defects-pdf.md

# View all feature defect files
Glob .claude/defects/_defects-*.md

# Search for async patterns across all features
Grep "ASYNC" .claude/defects/

# Search for sync patterns
Grep "SYNC" .claude/defects/
```
