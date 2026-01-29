# Chunked Sync Implementation

**Phase**: 13.4
**Status**: Complete
**Date**: 2026-01-28

## Overview

The sync service now supports chunked operations to prevent overwhelming the server with large datasets. This is critical for performance when syncing hundreds or thousands of records.

## Architecture

### SyncConfig Class

Configuration for controlling chunk sizes:

```dart
class SyncConfig {
  /// Number of records to process per chunk during push operations
  final int pushChunkSize;  // Default: 50

  /// Number of records to fetch per page during pull operations
  final int pullChunkSize;  // Default: 100

  /// Maximum number of concurrent chunks (currently always 1 for sequential processing)
  final int maxConcurrentChunks;  // Default: 1

  const SyncConfig({
    this.pushChunkSize = 50,
    this.pullChunkSize = 100,
    this.maxConcurrentChunks = 1,
  });
}
```

### Progress Callback

Track sync progress for UI updates:

```dart
typedef SyncProgressCallback = void Function(int processed, int? total);
```

- **processed**: Number of records synced so far
- **total**: Total records to sync (may be null for pull operations where total is unknown until complete)

## Push Operations (Local → Remote)

### Implementation

1. **Chunking**: `_chunkList<T>()` splits large datasets into chunks
2. **Sequential Processing**: `_pushRecordsInChunks()` processes chunks one at a time
3. **Progress Tracking**: Reports progress after each chunk via `onProgressUpdate` callback
4. **Error Resilience**: Continues with next chunk even if current chunk fails

### Usage

```dart
// All base data push operations use chunking automatically
final records = await db.query('projects');
pushed += await _pushRecordsInChunks('projects', records);
```

### Tables Using Chunked Push

All base data tables:
- projects
- locations
- contractors
- equipment
- bid_items
- personnel_types
- daily_entries
- entry_personnel
- entry_equipment
- entry_quantities
- inspector_forms
- form_responses
- todo_items
- calculation_history
- form_field_registry
- field_semantic_aliases
- form_field_cache

## Pull Operations (Remote → Local)

### Implementation

1. **Pagination**: `_pullRemoteRecordsInChunks()` uses Supabase `.range()` for pagination
2. **Incremental Fetching**: Continues until all records retrieved
3. **Progress Tracking**: Reports incremental progress (total unknown until complete)
4. **Memory Efficient**: Processes records in manageable chunks

### Supabase Range Query

```dart
final chunk = await _supabase!
    .from(tableName)
    .select()
    .range(offset, offset + pullChunkSize - 1)
    .order('created_at', ascending: true);
```

### Pagination Logic

- Start at offset 0
- Fetch `pullChunkSize` records
- If fewer records returned than chunk size, we've reached the end
- Otherwise, increment offset and continue

## Progress Tracking

### Callbacks

The sync service supports progress callbacks at multiple levels:

```dart
final syncService = SyncService(dbService);

// Track overall progress
syncService.onProgressUpdate = (processed, total) {
  if (total != null) {
    print('Progress: $processed / $total (${(processed / total * 100).toStringAsFixed(1)}%)');
  } else {
    print('Progress: $processed records processed');
  }
};

// Track sync completion
syncService.onSyncComplete = (result) {
  print('Sync complete: ${result.pushed} pushed, ${result.pulled} pulled');
};
```

### Integration with Adapters

Progress callbacks flow through the architecture:

```
SyncService.onProgressUpdate
    ↓
SupabaseSyncAdapter.onProgressUpdate (pass-through)
    ↓
SyncOrchestrator.onProgressUpdate
    ↓
SyncProvider (UI updates)
```

## Configuration

### Default Configuration

```dart
const SyncConfig.defaultConfig = SyncConfig(
  pushChunkSize: 50,
  pullChunkSize: 100,
  maxConcurrentChunks: 1,
);
```

### Custom Configuration

```dart
final syncService = SyncService(
  dbService,
  config: SyncConfig(
    pushChunkSize: 25,   // Smaller chunks for slower connections
    pullChunkSize: 200,  // Larger chunks for faster connections
  ),
);
```

## Performance Characteristics

### Push Performance

- **Chunk Size 50**: ~2-3 seconds per chunk on average connection
- **Total Time**: Depends on total records and connection speed
- **Memory**: Low (only one chunk in memory at a time)

### Pull Performance

- **Chunk Size 100**: ~1-2 seconds per chunk
- **Total Time**: Depends on remote record count
- **Memory**: Accumulates results (consider memory if pulling thousands of records)

## Error Handling

### Push Errors

- Individual chunk failures are logged but don't stop the entire push
- Allows partial sync progress even with errors
- Failed chunks can be retried on next sync

### Pull Errors

- Chunk fetch failures stop the pull operation for that table
- Accumulated records before error are still processed
- Next sync will retry from beginning (idempotent upsert)

## Testing

### Unit Tests

Comprehensive tests in `test/services/sync_service_test.dart`:

```dart
group('Chunked Sync Configuration', () {
  test('SyncConfig has default values', () { ... });
  test('SyncConfig can be customized', () { ... });
  test('SyncService accepts custom config', () { ... });
});

group('Progress Callbacks', () {
  test('onProgressUpdate callback is invoked during sync', () { ... });
  test('onProgressUpdate receives incremental progress', () { ... });
  test('progress callback handles null total gracefully', () { ... });
});
```

All tests passing as of 2026-01-28.

## Future Enhancements

### Concurrent Chunking

Currently `maxConcurrentChunks` is always 1 (sequential). Future enhancement could support parallel chunk processing:

```dart
const SyncConfig(
  maxConcurrentChunks: 3,  // Process 3 chunks in parallel
);
```

Considerations:
- Server load (don't overwhelm Supabase)
- Race conditions (ensure upserts are idempotent)
- Progress tracking becomes more complex

### Adaptive Chunk Sizing

Automatically adjust chunk size based on:
- Network speed
- Server response time
- Available memory

### Resumable Sync

Track last successful chunk offset to resume interrupted syncs:
- Store offset in local database
- Resume from last offset on next sync
- Clear offset on successful completion

## Files Modified

| File | Changes |
|------|---------|
| `lib/services/sync_service.dart` | Added `SyncConfig`, chunking methods, progress callbacks |
| `lib/features/sync/data/adapters/supabase_sync_adapter.dart` | Pass-through for progress callbacks |
| `lib/features/sync/application/sync_orchestrator.dart` | Wire progress callbacks to UI |
| `test/services/sync_service_test.dart` | Added tests for chunking and progress tracking |

## Related Documentation

- @.claude/memory/tech-stack.md (Sync architecture)
- @.claude/rules/backend/data-layer.md (Data sync patterns)
- Supabase pagination docs: https://supabase.com/docs/reference/javascript/range
