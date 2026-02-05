# Implementation Plan: Comprehensive App-Wide Logging

**Last Updated**: 2026-02-04
**Status**: READY
**Agent**: qa-testing-agent (primary), all agents (integration)

## Overview

Implement always-on, structured file logging across the entire Field Guide App to give Claude complete visibility into app behavior for debugging. Logs will be written to `C:\Users\rseba\Projects\Field Guide App\Troubleshooting\Detailed App Wide Logs` with separate files per category, working on both Windows and mobile platforms.

## Problem Statement

### Current State
- **AppLogger** exists but requires `APP_FILE_LOGGING=true` flag and is rarely used
- **OCR** uses raw `print()` and `debugPrint()`, bypassing structured logging
- **OcrPerformanceLogger** exists but is orphaned (never instantiated)
- **ParserDiagnostics** requires `PDF_PARSER_DIAGNOSTICS=true` flag, uses debugPrint only
- **Auth/Sync/Database/UI** have zero to minimal logging
- No unified logging strategy across 13 features

### Target State
- Always-on file logging (no flags required)
- Category-based log files for easy debugging
- Structured format with timestamps and optional JSON data
- Works on Windows, Android, iOS
- Minimal performance impact
- Easy API for developers to use

## Technical Context

### App Architecture
```
lib/
├── core/           # Router, theme, config, database, logging
├── shared/         # Base classes, utilities
├── features/       # 13 features (auth, pdf, sync, etc.)
└── services/       # Cross-cutting services
```

### Current Logging Infrastructure

**AppLogger** (`lib/core/logging/app_logger.dart`):
- Session-based file logging
- Lifecycle hooks
- debugPrint interception
- BUT: Requires flag, not widely used

**OCR Stack**:
- flusseract package (local in `packages/flusseract/`)
- Tesseract with eng.traineddata
- Image preprocessing: adaptive thresholding, deskew, contrast
- Instance pooling for performance
- Currently uses print() scattered throughout

**PDF Import Pipeline**:
1. Load PDF bytes
2. Extract text (Syncfusion)
3. Decide if OCR needed
4. If OCR: Render → Preprocess → Tesseract → HOCR parse
5. TableExtractor: Locate → Columns → Cells → Parse rows
6. Post-process items
7. Return PdfImportResult

## Phase 1: Core Logger Infrastructure

### Task 1.1: Create DebugLogger Class
**Agent**: qa-testing-agent
**Files**:
- `lib/core/logging/debug_logger.dart` - NEW: Core logging singleton

### Requirements
- Singleton pattern for app-wide access
- Always-on (no flags needed)
- Separate log files per category
- Thread-safe file writes
- Automatic log rotation (size/age limits)
- Platform-aware paths (Windows vs mobile)

### Log Categories
| Category | File | Purpose |
|----------|------|---------|
| Session | `app_session.log` | App lifecycle, initialization |
| OCR | `ocr.log` | All OCR operations, preprocessing |
| PDF | `pdf_import.log` | PDF pipeline, table extraction |
| Sync | `sync.log` | Sync operations, conflicts |
| Database | `database.log` | DB queries, migrations |
| Auth | `auth.log` | Auth flows, token refresh |
| Navigation | `navigation.log` | Screen transitions, deep links |
| Errors | `errors.log` | All errors with stack traces |

### API Design
```dart
class DebugLogger {
  // Category-specific methods
  static void ocr(String message, {Map<String, dynamic>? data});
  static void pdf(String message, {Map<String, dynamic>? data});
  static void sync(String message, {Map<String, dynamic>? data});
  static void db(String message, {Map<String, dynamic>? data});
  static void auth(String message, {Map<String, dynamic>? data});
  static void nav(String message, {Map<String, dynamic>? data});
  static void session(String message, {Map<String, dynamic>? data});

  // Error logging with stack traces
  static void error(
    String message, {
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? data,
  });

  // Lifecycle
  static Future<void> initialize();
  static Future<void> dispose();
  static Future<void> clearLogs();
}
```

### Log Format
```
[CATEGORY] [HH:MM:SS.mmm] message {optional_json_data}
```

Example:
```
[OCR] [14:32:15.123] Starting Tesseract initialization {"language": "eng"}
[OCR] [14:32:15.234] Preprocessing image {"width": 2480, "height": 3508, "dpi": 300}
[PDF] [14:32:16.456] Table extraction started {"page": 1, "tables_found": 2}
```

### Implementation Steps
1. Create `DebugLogger` class with singleton pattern
2. Implement file I/O with platform-aware paths
3. Add category-specific logging methods
4. Implement log rotation (max 50MB per file, keep last 5)
5. Add error handling (logging failures should never crash app)
6. Write unit tests for DebugLogger

### Task 1.2: Initialize in App Lifecycle
**Agent**: qa-testing-agent
**Files**:
- `lib/main.dart` - Initialize DebugLogger before runApp

### Steps
1. Call `DebugLogger.initialize()` in `main()`
2. Log app start with version info
3. Register cleanup in app disposal
4. Add session ID for log correlation

## Phase 2: PDF & OCR Logging

### Task 2.1: OCR Engine Logging
**Agent**: pdf-agent
**Files**:
- `lib/features/pdf/services/ocr/tesseract_ocr_engine.dart` - Replace print() with DebugLogger.ocr()
- `lib/features/pdf/services/ocr/ocr_engine_factory.dart` - Add logging for engine creation/disposal
- `lib/features/pdf/services/ocr/tesseract_initializer.dart` - Log initialization steps

### Critical Logging Points
```dart
// Engine lifecycle
DebugLogger.ocr('Creating Tesseract engine instance', {
  'pool_size': poolSize,
  'language': language,
});

// Initialization
DebugLogger.ocr('Tesseract initialization started', {
  'traineddata_path': traineDataPath,
  'dpi': dpi,
});

// Recognition
DebugLogger.ocr('Starting text recognition', {
  'image_width': width,
  'image_height': height,
  'preprocessed': isPreprocessed,
});

// Performance
DebugLogger.ocr('Recognition completed', {
  'duration_ms': duration.inMilliseconds,
  'text_length': result.length,
  'confidence': confidence,
});

// Errors
DebugLogger.error('Tesseract recognition failed',
  error: e,
  stackTrace: stack,
  data: {'image_path': path},
);
```

### Task 2.2: Image Preprocessing Logging
**Agent**: pdf-agent
**Files**:
- `lib/features/pdf/services/ocr/image_preprocessor.dart` - Add preprocessing logs

### Critical Logging Points
```dart
DebugLogger.ocr('Preprocessing image', {
  'original_width': originalWidth,
  'original_height': originalHeight,
  'target_dpi': targetDpi,
});

DebugLogger.ocr('Applied adaptive threshold', {
  'block_size': blockSize,
  'c_value': cValue,
});

DebugLogger.ocr('Deskew applied', {
  'angle': angle,
  'method': 'projection_profile',
});

DebugLogger.ocr('Preprocessing complete', {
  'final_width': finalWidth,
  'final_height': finalHeight,
  'duration_ms': duration.inMilliseconds,
});
```

### Task 2.3: PDF Page Rendering Logging
**Agent**: pdf-agent
**Files**:
- `lib/features/pdf/services/ocr/pdf_page_renderer.dart` - Add render logs

### Critical Logging Points
```dart
DebugLogger.ocr('Rendering PDF page', {
  'page': pageNumber,
  'scale': scale,
  'target_dpi': dpi,
});

DebugLogger.ocr('Page render complete', {
  'page': pageNumber,
  'image_size_bytes': imageBytes.length,
  'duration_ms': duration.inMilliseconds,
});
```

### Task 2.4: Table Extraction Logging
**Agent**: pdf-agent
**Files**:
- `lib/features/pdf/services/table_extraction/table_extractor.dart` - Add extraction logs

### Critical Logging Points
```dart
DebugLogger.pdf('Table extraction started', {
  'page': page,
  'text_lines': lines.length,
});

DebugLogger.pdf('Table boundaries detected', {
  'table_count': tables.length,
  'boundaries': tables.map((t) => t.bounds).toList(),
});

DebugLogger.pdf('Column detection', {
  'table_index': index,
  'columns_found': columns.length,
  'column_positions': columns,
});

DebugLogger.pdf('Table extraction complete', {
  'rows_extracted': rows.length,
  'columns': columnCount,
  'duration_ms': duration.inMilliseconds,
});
```

### Task 2.5: PDF Import Service Logging
**Agent**: pdf-agent
**Files**:
- `lib/features/pdf/services/pdf_import_service.dart` - Enhanced pipeline logging

### Critical Logging Points
```dart
DebugLogger.pdf('PDF import started', {
  'file_size_bytes': bytes.length,
  'spec_type': specType,
});

DebugLogger.pdf('Text extraction phase', {
  'method': 'syncfusion',
  'text_length': extractedText.length,
});

DebugLogger.pdf('OCR decision', {
  'needs_ocr': needsOcr,
  'reason': reason,
});

DebugLogger.pdf('PDF import complete', {
  'items_extracted': result.items.length,
  'ocr_used': usedOcr,
  'total_duration_ms': duration.inMilliseconds,
});
```

## Phase 3: Sync & Database Logging

### Task 3.1: Sync Orchestrator Logging
**Agent**: supabase-agent
**Files**:
- `lib/features/sync/application/sync_orchestrator.dart` - Add comprehensive sync logs

### Critical Logging Points
```dart
DebugLogger.sync('Sync started', {
  'user_id': userId,
  'trigger': trigger, // 'manual', 'auto', 'background'
});

DebugLogger.sync('Pulling changes from server', {
  'last_sync': lastSyncTimestamp,
});

DebugLogger.sync('Server changes received', {
  'projects': projectCount,
  'entries': entryCount,
  'photos': photoCount,
});

DebugLogger.sync('Conflict detected', {
  'table': table,
  'local_updated': localTimestamp,
  'server_updated': serverTimestamp,
  'resolution': resolution,
});

DebugLogger.sync('Sync complete', {
  'success': success,
  'duration_ms': duration.inMilliseconds,
  'uploaded': uploadedCount,
  'downloaded': downloadedCount,
});
```

### Task 3.2: Database Logging
**Agent**: data-layer-agent
**Files**:
- `lib/core/database/database_service.dart` - Add DB operation logs

### Critical Logging Points
```dart
DebugLogger.db('Database initialization started', {
  'version': version,
});

DebugLogger.db('Running migration', {
  'from_version': oldVersion,
  'to_version': newVersion,
});

DebugLogger.db('Query executed', {
  'table': table,
  'operation': 'SELECT', // or INSERT, UPDATE, DELETE
  'rows_affected': rowCount,
  'duration_ms': duration.inMilliseconds,
});

DebugLogger.db('Transaction started', {
  'isolation_level': isolationLevel,
});

DebugLogger.db('Transaction committed', {
  'operations': operationCount,
  'duration_ms': duration.inMilliseconds,
});
```

## Phase 4: Auth & Navigation Logging

### Task 4.1: Auth Flow Logging
**Agent**: auth-agent
**Files**:
- `lib/features/auth/data/repositories/auth_repository.dart` - Add auth logs
- `lib/features/auth/application/auth_provider.dart` - Add state change logs

### Critical Logging Points
```dart
DebugLogger.auth('Sign in started', {
  'method': 'email', // or 'google', 'apple'
});

DebugLogger.auth('Session restored', {
  'user_id': userId,
  'expires_at': expiresAt,
});

DebugLogger.auth('Token refresh started', {
  'expires_in': expiresIn,
});

DebugLogger.auth('Sign out', {
  'user_id': userId,
  'reason': reason, // 'manual', 'expired', 'error'
});

DebugLogger.auth('Auth error', {
  'code': errorCode,
  'message': errorMessage,
});
```

### Task 4.2: Navigation Logging
**Agent**: frontend-flutter-specialist-agent
**Files**:
- `lib/core/router/app_router.dart` - Enhance AppRouteObserver

### Critical Logging Points
```dart
DebugLogger.nav('Route push', {
  'from': previousRoute,
  'to': newRoute,
});

DebugLogger.nav('Route pop', {
  'from': currentRoute,
  'to': previousRoute,
});

DebugLogger.nav('Deep link handled', {
  'uri': deepLinkUri,
  'route': resolvedRoute,
});

DebugLogger.nav('Route error', {
  'path': path,
  'error': error,
});
```

## Phase 5: Provider State Logging

### Task 5.1: Add State Change Logging to Key Providers
**Agent**: data-layer-agent
**Files**:
- `lib/features/projects/application/project_provider.dart`
- `lib/features/entries/application/entry_provider.dart`
- `lib/features/photos/application/photo_provider.dart`

### Pattern
```dart
// Before state change
DebugLogger.session('Provider state change', {
  'provider': 'ProjectProvider',
  'action': 'loadProjects',
  'previous_state': state.toString(),
});

// After state change
DebugLogger.session('State updated', {
  'provider': 'ProjectProvider',
  'new_state': state.toString(),
  'item_count': projects.length,
});
```

## Phase 6: Error Boundary & Global Error Logging

### Task 6.1: Enhanced Error Logging
**Agent**: qa-testing-agent
**Files**:
- `lib/main.dart` - Add Flutter error handler override

### Implementation
```dart
FlutterError.onError = (FlutterErrorDetails details) {
  DebugLogger.error(
    'Flutter framework error',
    error: details.exception,
    stackTrace: details.stack,
    data: {
      'context': details.context?.toString(),
      'library': details.library,
    },
  );
  // Still call default handler for debug mode
  FlutterError.presentError(details);
};

PlatformDispatcher.instance.onError = (error, stack) {
  DebugLogger.error(
    'Uncaught platform error',
    error: error,
    stackTrace: stack,
  );
  return true;
};
```

## Verification

### Automated Tests
1. `flutter analyze` - No issues
2. `flutter test` - All pass
3. Unit tests for DebugLogger:
   - Log file creation
   - Category routing
   - Log rotation
   - Thread safety
   - Platform path handling

### Manual Testing
- [ ] Logs created in correct directory on Windows
- [ ] Logs created on Android device
- [ ] Logs created on iOS device (if applicable)
- [ ] All 8 log files generated
- [ ] Log format is correct (timestamp, category, message)
- [ ] JSON data properly serialized
- [ ] Stack traces captured in errors.log
- [ ] Log rotation works (create >50MB log, verify rotation)
- [ ] Performance impact minimal (measure FPS during heavy logging)

### Integration Testing
- [ ] Import Springfield PDF - verify OCR logs show preprocessing steps
- [ ] Trigger sync - verify sync.log shows pull/push operations
- [ ] Sign in/out - verify auth.log shows flow
- [ ] Navigate between screens - verify navigation.log
- [ ] Create/edit project - verify db.log shows queries

### Springfield PDF Test Case
Run with verbose logging enabled:
```bash
pwsh -Command "flutter run"
```

Expected logs:
1. **ocr.log**: Tesseract init → Page render → Preprocessing (threshold, deskew) → Recognition → Results
2. **pdf_import.log**: Import started → Text extraction → OCR decision → Table extraction → Items parsed → Complete
3. **database.log**: INSERT queries for imported items
4. **navigation.log**: Navigate to preview screen
5. **errors.log**: Empty (no errors)

## Performance Considerations

### File I/O Strategy
- Buffer writes (flush every 100 messages or 1 second)
- Async file writes to avoid blocking UI
- Isolate for heavy logging scenarios

### Size Management
- Max 50MB per log file
- Keep last 5 rotated files per category
- Auto-cleanup logs older than 7 days

### Conditional Verbosity
While always-on, consider verbosity levels for future:
```dart
enum LogLevel { minimal, normal, verbose }
```

## Migration Notes

### Replacing Existing Logging
- `print()` → `DebugLogger.session()` or appropriate category
- `debugPrint()` → `DebugLogger.session()` or appropriate category
- `ParserDiagnostics.log*()` → `DebugLogger.pdf()`
- Raw error prints → `DebugLogger.error()`

### Coexistence with AppLogger
- Keep AppLogger for user-facing logs (if needed)
- DebugLogger is for Claude/developer debugging only
- No flags required for DebugLogger

## Future Enhancements

### Phase 7 (Optional)
- [ ] Log viewer UI in app (Settings > Developer > View Logs)
- [ ] Export logs as ZIP for bug reports
- [ ] Remote log upload to Supabase for cloud debugging
- [ ] Log filtering by timestamp/category
- [ ] Performance profiling logs (frame times, memory usage)

## Reference Files

### Current Logging Infrastructure
- `lib/core/logging/app_logger.dart` - Existing logger (flag-gated)
- `lib/features/pdf/services/parsers/parser_diagnostics.dart` - PDF diagnostics (flag-gated)
- `lib/core/router/app_router.dart` - AppRouteObserver (basic)

### Key Integration Points
- `lib/main.dart` - App entry, error handlers
- `lib/features/pdf/services/ocr/tesseract_ocr_engine.dart` - OCR entry point
- `lib/features/pdf/services/table_extraction/table_extractor.dart` - Table logic
- `lib/features/sync/application/sync_orchestrator.dart` - Sync entry point
- `lib/core/database/database_service.dart` - DB entry point

## Success Metrics

1. **Coverage**: Every major subsystem has structured logging
2. **Discoverability**: Claude can diagnose issues from logs alone
3. **Performance**: <5% overhead on average use cases
4. **Reliability**: No crashes due to logging failures
5. **Usability**: Logs are human-readable and machine-parseable

## Related Plans
- Springfield PDF extraction debugging (in progress)
- OCR performance optimization (completed - flusseract migration)
- Sync conflict resolution improvements (future)

## Notes
- This plan is **CRITICAL** for ongoing Claude-assisted debugging
- Logs give Claude "eyes" into runtime behavior
- Prioritize OCR/PDF logging (Phase 2) as it's actively being debugged
- Auth/Sync logging (Phases 3-4) can follow
- Consider this infrastructure work, not feature work
- Budget 2-3 days for full implementation and testing
