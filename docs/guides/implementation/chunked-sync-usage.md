# Chunked Sync Usage Guide

> **Used By**: [backend-supabase-agent](../../../agents/backend-supabase-agent.md) for large dataset sync, progress tracking, and performance optimization during offline-to-online transitions

## Overview

Phase 13.4 adds chunked sync capabilities to handle large datasets efficiently. The sync service now processes data in configurable chunks to avoid overwhelming the server and provide progress feedback.

## Key Features

- **Chunked Push**: Splits large local datasets into batches before uploading
- **Chunked Pull**: Uses Supabase `.range()` to fetch data in pages
- **Progress Tracking**: Optional callbacks report sync progress
- **Sequential Processing**: Chunks are processed one at a time to prevent server overload
- **Configurable**: Chunk sizes can be adjusted per use case

## Configuration

### Default Configuration

```dart
const SyncConfig.defaultConfig = SyncConfig(
  pushChunkSize: 50,    // Records per push batch
  pullChunkSize: 100,   // Records per pull page
  maxConcurrentChunks: 1, // Sequential processing
);
```

### Custom Configuration

```dart
import 'package:construction_inspector/services/sync_service.dart';

final customConfig = SyncConfig(
  pushChunkSize: 25,   // Smaller chunks for slower networks
  pullChunkSize: 200,  // Larger pages for faster networks
);

final syncService = SyncService(
  databaseService,
  config: customConfig,
);
```

## Progress Tracking

### Setup Progress Callback

```dart
syncService.onProgressUpdate = (int processed, int? total) {
  if (total != null) {
    final percent = (processed / total * 100).toStringAsFixed(0);
    print('Sync progress: $processed/$total ($percent%)');
  } else {
    print('Sync progress: $processed records processed');
  }
};
```

### Using with Orchestrator

```dart
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';

final orchestrator = SyncOrchestrator(databaseService);
await orchestrator.initialize();

orchestrator.onProgressUpdate = (processed, total) {
  // Update UI progress indicator
  setState(() {
    _syncProgress = total != null ? processed / total : null;
    _syncProcessed = processed;
  });
};

await orchestrator.syncLocalAgencyProjects();
```

### UI Progress Indicator Example

```dart
class SyncProgressWidget extends StatefulWidget {
  @override
  State<SyncProgressWidget> createState() => _SyncProgressWidgetState();
}

class _SyncProgressWidgetState extends State<SyncProgressWidget> {
  int _processed = 0;
  int? _total;

  @override
  void initState() {
    super.initState();

    // Wire up progress callback
    context.read<SyncProvider>().syncOrchestrator.onProgressUpdate =
      (processed, total) {
        if (mounted) {
          setState(() {
            _processed = processed;
            _total = total;
          });
        }
      };
  }

  @override
  Widget build(BuildContext context) {
    if (_total != null) {
      return Column(
        children: [
          LinearProgressIndicator(value: _processed / _total!),
          Text('Syncing: $_processed / $_total records'),
        ],
      );
    } else if (_processed > 0) {
      return Column(
        children: [
          CircularProgressIndicator(),
          Text('Syncing: $_processed records processed'),
        ],
      );
    }
    return SizedBox.shrink();
  }
}
```

## How It Works

### Push Operations

1. Query local database for records to sync
2. Split records into chunks using `_chunkList()`
3. Process each chunk sequentially:
   - Convert to remote format
   - Upsert to Supabase
   - Report progress
4. Continue with next chunk on error

### Pull Operations

1. Query remote table with `.range(start, end)`
2. Fetch chunk of records
3. Merge into local database
4. Report progress
5. Continue until no more records

### Example Flow

```
Push 250 records with pushChunkSize=50:
  Chunk 1: 50/250 (20%)
  Chunk 2: 100/250 (40%)
  Chunk 3: 150/250 (60%)
  Chunk 4: 200/250 (80%)
  Chunk 5: 250/250 (100%)

Pull with pullChunkSize=100:
  Page 1: range(0, 99)   -> 100 records
  Page 2: range(100, 199) -> 100 records
  Page 3: range(200, 299) -> 50 records (last page)
  Done (total: 250 records)
```

## Performance Considerations

### Chunk Size Guidelines

| Network | Push Size | Pull Size | Notes |
|---------|-----------|-----------|-------|
| Fast (WiFi) | 100 | 200 | Maximize throughput |
| Medium (4G) | 50 | 100 | Default balanced |
| Slow (3G) | 25 | 50 | Minimize timeouts |
| Large records | 10 | 20 | Photos, complex data |

### Memory Usage

- Larger chunks = more memory but fewer requests
- Smaller chunks = less memory but more overhead
- Default settings balance both concerns

### Error Handling

- Failed chunks don't block subsequent chunks
- Each chunk is logged separately
- Errors are aggregated in `SyncResult.errorMessages`

## Migration Notes

### Existing Code

The existing sync functionality remains unchanged. Chunking is additive:

```dart
// This still works exactly as before
final result = await syncService.syncAll();
```

### No Breaking Changes

- Default chunk sizes preserve existing behavior
- Progress callbacks are optional
- Existing tests continue to pass

## Implementation Details

### Key Files

| File | Changes |
|------|---------|
| `lib/services/sync_service.dart` | Added `SyncConfig`, chunking methods |
| `lib/features/sync/domain/sync_adapter.dart` | Added `onProgressUpdate` callback |
| `lib/features/sync/data/adapters/supabase_sync_adapter.dart` | Wired progress to legacy service |
| `lib/features/sync/data/adapters/mock_sync_adapter.dart` | Added progress stub |
| `lib/features/sync/application/sync_orchestrator.dart` | Added progress passthrough |

### Key Methods

```dart
// Split list into chunks
List<List<T>> _chunkList<T>(List<T> list, int chunkSize)

// Push records in batches
Future<int> _pushRecordsInChunks(String tableName, List<Map<String, dynamic>> records)

// Pull records in pages
Future<List<Map<String, dynamic>>> _pullRemoteRecordsInChunks(String tableName)
```

## Testing

### Unit Test Example

```dart
test('should chunk large datasets', () async {
  final config = SyncConfig(pushChunkSize: 10);
  final service = SyncService(dbService, config: config);

  int progressCalls = 0;
  service.onProgressUpdate = (processed, total) {
    progressCalls++;
    expect(processed, lessThanOrEqualTo(total!));
  };

  await service.syncAll();

  expect(progressCalls, greaterThan(0));
});
```

### E2E Test Consideration

In test mode (`MOCK_DATA=true`), chunking is bypassed for speed:
- Progress callbacks still fire
- No actual network pagination occurs
- Tests remain fast and deterministic

## Future Enhancements

- Concurrent chunk processing (requires server capacity)
- Adaptive chunk sizing based on network speed
- Compression for large payloads
- Delta sync (only changed records)
- Conflict resolution UI
