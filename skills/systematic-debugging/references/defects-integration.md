# Defects Integration

How to use and update per-feature defect files during debugging.

## Before Debugging

**ALWAYS check the relevant feature's defect file first.**

The bug you're looking at might be a known pattern.

### Check Process

1. Read `.claude/defects/_defects-{feature}.md` for the feature you're debugging
2. Search for related categories:
   - `[ASYNC]` - Context safety, dispose issues
   - `[E2E]` - Patrol testing patterns
   - `[FLUTTER]` - Widget, Provider patterns
   - `[DATA]` - Repository, collection access
   - `[CONFIG]` - Supabase, credentials, environment
3. If pattern exists, apply the documented prevention

### Example Check

Debugging: "App crashes after saving entry"

1. Open `.claude/defects/_defects-entries.md`
2. Search for "save", "async", "context"
3. Find: `[ASYNC] 2026-01-21: Async Context Safety`
4. Check: Does the crash happen after an `await`?
5. Apply: Add `if (!mounted) return;` check

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
| `[E2E]` | Patrol testing patterns, TestingKeys, waits |
| `[FLUTTER]` | Widget lifecycle, Provider, setState |
| `[DATA]` | Repository, collection access, null safety |
| `[CONFIG]` | Supabase, environment, credentials |

### Example Entry

```markdown
### [ASYNC] 2026-02-01: Timer Callback After Dispose
**Pattern**: Timer.periodic callback runs after widget disposed
**Prevention**: Cancel timer in dispose(); use mounted check in callback
**Ref**: @lib/features/sync/presentation/widgets/sync_status_indicator.dart
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

```bash
# View PDF defects
Read .claude/defects/_defects-pdf.md

# View all feature defect files
Glob .claude/defects/_defects-*.md

# Search for async patterns across all features
Grep "ASYNC" .claude/defects/
```
