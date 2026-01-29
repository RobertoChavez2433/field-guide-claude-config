# Chunked Sync Usage Examples

## Basic Usage

### Default Configuration

Most common use case - use default chunk sizes:

```dart
import 'package:construction_inspector/services/sync_service.dart';
import 'package:construction_inspector/core/database/database_service.dart';

final dbService = DatabaseService();
final syncService = SyncService(dbService);

// Sync with default chunk sizes (push: 50, pull: 100)
final result = await syncService.syncAll();

print('Pushed: ${result.pushed}, Pulled: ${result.pulled}');
```

### Custom Configuration

For slower connections or memory-constrained devices:

```dart
final syncService = SyncService(
  dbService,
  config: SyncConfig(
    pushChunkSize: 25,   // Smaller chunks
    pullChunkSize: 50,   // Smaller chunks
  ),
);

final result = await syncService.syncAll();
```

For faster connections with good bandwidth:

```dart
final syncService = SyncService(
  dbService,
  config: SyncConfig(
    pushChunkSize: 100,  // Larger chunks
    pullChunkSize: 200,  // Larger chunks
  ),
);

final result = await syncService.syncAll();
```

## Progress Tracking

### Simple Progress Bar

```dart
final syncService = SyncService(dbService);

// Track progress for UI updates
syncService.onProgressUpdate = (processed, total) {
  if (total != null) {
    // Known total (push operations)
    final percent = (processed / total * 100).toStringAsFixed(1);
    print('Progress: $processed / $total ($percent%)');
  } else {
    // Unknown total (pull operations)
    print('Syncing: $processed records processed...');
  }
};

await syncService.syncAll();
```

### Flutter Provider Integration

```dart
class SyncProvider extends ChangeNotifier {
  final SyncService _syncService;

  int _syncedRecords = 0;
  int? _totalRecords;

  int get syncedRecords => _syncedRecords;
  int? get totalRecords => _totalRecords;

  double? get progress {
    if (_totalRecords == null || _totalRecords == 0) return null;
    return _syncedRecords / _totalRecords!;
  }

  SyncProvider(this._syncService) {
    _syncService.onProgressUpdate = _handleProgress;
  }

  void _handleProgress(int processed, int? total) {
    _syncedRecords = processed;
    _totalRecords = total;
    notifyListeners();
  }

  Future<void> sync() async {
    _syncedRecords = 0;
    _totalRecords = null;
    notifyListeners();

    await _syncService.syncAll();

    // Reset after completion
    _syncedRecords = 0;
    _totalRecords = null;
    notifyListeners();
  }
}
```

### UI with Progress Indicator

```dart
class SyncProgressWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<SyncProvider>(
      builder: (context, provider, _) {
        final progress = provider.progress;

        if (progress == null) {
          // Unknown total - show indeterminate progress
          return Column(
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 8),
              Text('Syncing ${provider.syncedRecords} records...'),
            ],
          );
        }

        // Known total - show determinate progress
        return Column(
          children: [
            LinearProgressIndicator(value: progress),
            SizedBox(height: 8),
            Text('${provider.syncedRecords} / ${provider.totalRecords} records'),
          ],
        );
      },
    );
  }
}
```

## Advanced Usage

### Comprehensive Callbacks

```dart
final syncService = SyncService(dbService);

// Status changes
syncService.onStatusChanged = (status) {
  switch (status) {
    case SyncOpStatus.idle:
      print('Ready to sync');
      break;
    case SyncOpStatus.syncing:
      print('Sync in progress...');
      break;
    case SyncOpStatus.success:
      print('Sync completed successfully');
      break;
    case SyncOpStatus.error:
      print('Sync failed');
      break;
    case SyncOpStatus.offline:
      print('Device is offline');
      break;
  }
};

// Progress updates
syncService.onProgressUpdate = (processed, total) {
  if (total != null) {
    print('Progress: $processed / $total');
  } else {
    print('Processed: $processed');
  }
};

// Completion
syncService.onSyncComplete = (result) {
  print('Sync complete!');
  print('Pushed: ${result.pushed}');
  print('Pulled: ${result.pulled}');
  print('Errors: ${result.errors}');

  if (result.hasErrors) {
    print('Error messages:');
    for (final msg in result.errorMessages) {
      print('  - $msg');
    }
  }
};

await syncService.syncAll();
```

### Logging Example

```dart
class SyncLogger {
  final SyncService syncService;
  final List<String> _log = [];

  SyncLogger(this.syncService) {
    _setupLogging();
  }

  void _setupLogging() {
    syncService.onStatusChanged = (status) {
      _log.add('[${DateTime.now()}] Status: $status');
    };

    syncService.onProgressUpdate = (processed, total) {
      if (total != null) {
        _log.add('[${DateTime.now()}] Progress: $processed/$total');
      } else {
        _log.add('[${DateTime.now()}] Processed: $processed');
      }
    };

    syncService.onSyncComplete = (result) {
      _log.add('[${DateTime.now()}] Complete: ${result.toString()}');
      if (result.hasErrors) {
        for (final msg in result.errorMessages) {
          _log.add('[${DateTime.now()}] ERROR: $msg');
        }
      }
    };
  }

  List<String> get logs => List.unmodifiable(_log);

  void clearLogs() => _log.clear();

  void exportLogs(String filename) {
    final file = File(filename);
    file.writeAsStringSync(_log.join('\n'));
  }
}

// Usage
final logger = SyncLogger(syncService);
await syncService.syncAll();
print(logger.logs.join('\n'));
```

## SyncOrchestrator Integration

The SyncOrchestrator wraps the SyncService and provides a unified interface:

```dart
import 'package:construction_inspector/features/sync/application/sync_orchestrator.dart';

final orchestrator = SyncOrchestrator(dbService);
await orchestrator.initialize();

// Wire up callbacks
orchestrator.onProgressUpdate = (processed, total) {
  print('Progress: $processed / ${total ?? "?"}');
};

orchestrator.onSyncComplete = (result) {
  print('Sync result: $result');
};

// Sync all local agency projects (uses chunking automatically)
final result = await orchestrator.syncLocalAgencyProjects();
```

## Performance Tuning

### Network Speed Detection

```dart
class AdaptiveSyncService {
  final DatabaseService dbService;
  late SyncService _syncService;

  Future<void> initialize() async {
    final config = await _detectOptimalConfig();
    _syncService = SyncService(dbService, config: config);
  }

  Future<SyncConfig> _detectOptimalConfig() async {
    // Measure network speed
    final startTime = DateTime.now();

    try {
      // Test with small request
      final response = await http.get(Uri.parse('https://supabase.co'));
      final duration = DateTime.now().difference(startTime);

      if (duration.inMilliseconds < 500) {
        // Fast connection
        return SyncConfig(pushChunkSize: 100, pullChunkSize: 200);
      } else if (duration.inMilliseconds < 2000) {
        // Medium connection
        return SyncConfig.defaultConfig;
      } else {
        // Slow connection
        return SyncConfig(pushChunkSize: 25, pullChunkSize: 50);
      }
    } catch (e) {
      // Offline or very slow - use conservative defaults
      return SyncConfig(pushChunkSize: 10, pullChunkSize: 25);
    }
  }
}
```

### Memory-Constrained Devices

For devices with limited RAM:

```dart
final syncService = SyncService(
  dbService,
  config: SyncConfig(
    pushChunkSize: 10,   // Very small chunks
    pullChunkSize: 25,   // Very small chunks
  ),
);
```

### High-Performance Scenarios

For devices with good connectivity and memory:

```dart
final syncService = SyncService(
  dbService,
  config: SyncConfig(
    pushChunkSize: 200,  // Large chunks
    pullChunkSize: 500,  // Large chunks
  ),
);
```

## Error Handling

### Retry Logic

```dart
Future<SyncResult> syncWithRetry({int maxRetries = 3}) async {
  for (var attempt = 1; attempt <= maxRetries; attempt++) {
    final result = await syncService.syncAll();

    if (!result.hasErrors) {
      return result;
    }

    if (attempt < maxRetries) {
      print('Sync failed (attempt $attempt/$maxRetries), retrying...');
      await Future.delayed(Duration(seconds: attempt * 2)); // Exponential backoff
    }
  }

  throw Exception('Sync failed after $maxRetries attempts');
}
```

### Partial Sync Recovery

```dart
syncService.onSyncComplete = (result) {
  if (result.hasErrors) {
    // Log errors but continue
    for (final error in result.errorMessages) {
      logger.error('Sync error: $error');
    }

    // Schedule retry for next app launch
    scheduleSyncOnNextLaunch();
  } else {
    // Clear retry flag
    clearScheduledSync();
  }
};
```

## Testing

### Mock Configuration

```dart
// Test with small chunks for faster tests
final testSyncService = SyncService(
  dbService,
  config: SyncConfig(
    pushChunkSize: 5,
    pullChunkSize: 10,
  ),
);
```

### Progress Tracking Test

```dart
test('progress updates are received', () async {
  final progressUpdates = <(int, int?)>[];

  syncService.onProgressUpdate = (processed, total) {
    progressUpdates.add((processed, total));
  };

  await syncService.syncAll();

  // Verify we received updates
  expect(progressUpdates, isNotEmpty);

  // Verify progress is monotonically increasing
  for (var i = 1; i < progressUpdates.length; i++) {
    expect(
      progressUpdates[i].$1 >= progressUpdates[i - 1].$1,
      isTrue,
      reason: 'Progress should increase',
    );
  }
});
```

## Best Practices

1. **Use Default Config First**: Start with `SyncConfig.defaultConfig` and only customize if needed
2. **Monitor Progress**: Always wire up `onProgressUpdate` for user feedback
3. **Handle Errors Gracefully**: Check `result.hasErrors` and log error messages
4. **Don't Block UI**: Run sync in background, show progress indicator
5. **Test With Large Datasets**: Verify performance with realistic data volumes
6. **Adjust for Network**: Consider adaptive chunk sizing based on connection speed
7. **Memory Awareness**: Use smaller chunks on memory-constrained devices
