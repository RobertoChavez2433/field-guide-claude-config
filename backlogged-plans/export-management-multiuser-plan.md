# Export Management & Multi-User Collaboration System

**Date**: 2026-02-02
**Status**: Backlogged - Major Feature
**Priority**: High (next major implementation after OCR)
**Estimated Scope**: 4-6 weeks

---

## Executive Summary

Transform the Construction Inspector App from single-user local-first to a **multi-user cloud-collaborative platform** where:
- Projects live in Supabase and are accessible by multiple authorized users
- Inspectors can share reports to supervisors for review
- Supervisors can comment on or edit reports, triggering push notifications
- Exports are tracked, managed, and cloud-synced
- Easy sharing to laptop/tablet/email without navigating file managers

---

## Vision & Goals

### User Stories

**Inspector Perspective:**
1. "I export a daily report and want to re-access it later without regenerating"
2. "I need to send this report to my supervisor's email right now"
3. "I want to transfer exports to my laptop when I get back to the office"
4. "I can see which reports are pending supervisor review"

**Supervisor Perspective:**
1. "I can see all exports from inspectors on my projects"
2. "I can review a report and add comments or corrections"
3. "When I make changes, the inspector is notified immediately"
4. "I can access project data from any device"

**Company Perspective:**
1. "All project exports are backed up to cloud storage"
2. "We can integrate with our VPN/file system for automatic archival"
3. "We have visibility into project progress across all inspectors"

### Success Criteria
- [ ] Exports tracked in database with full metadata
- [ ] Exports sync to Supabase Storage
- [ ] Multi-user project access with proper authorization
- [ ] Supervisor review workflow with comments
- [ ] Push notifications for review actions
- [ ] Easy device-to-device and email sharing
- [ ] Storage usage reporting and cleanup

---

## Architecture Overview

### Data Flow
```
Inspector generates export
    ↓
Save to local app storage (appDocs/exports/)
    ↓
Register in export_registry table (SQLite)
    ↓
Upload to Supabase Storage (when online)
    ↓
Update export_registry with remote_path
    ↓
Sync export_registry to Supabase (for multi-user visibility)
    ↓
Supervisor sees export in their view
    ↓
Supervisor reviews/comments
    ↓
Push notification to inspector
    ↓
Inspector views changes, signs off
```

### System Components
```
┌─────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│  ExportListScreen    │  ExportDetailScreen  │  ReviewScreen     │
│  - List all exports  │  - View/share/delete │  - Comments       │
│  - Filter by status  │  - Download if remote│  - Edit actions   │
│  - Storage usage     │  - Re-share options  │  - Sign-off flow  │
├─────────────────────────────────────────────────────────────────┤
│                         PROVIDER LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  ExportProvider      │  ReviewProvider       │  NotificationProv │
│  - CRUD operations   │  - Comments/edits     │  - Push handling  │
│  - Sync status       │  - Review workflow    │  - Local badges   │
├─────────────────────────────────────────────────────────────────┤
│                        REPOSITORY LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  ExportRepository    │  ReviewRepository     │  UserRepository   │
│  - Local + remote    │  - Comment storage    │  - Role checking  │
├─────────────────────────────────────────────────────────────────┤
│                        DATASOURCE LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│  ExportLocalDS       │  ExportRemoteDS       │  StorageService   │
│  - SQLite registry   │  - Supabase sync      │  - File ops       │
│  - File operations   │  - Storage bucket     │  - Size calc      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

### New Tables

#### `export_registry` (Version 21)
```sql
CREATE TABLE export_registry (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  entry_id TEXT,                    -- NULL for project-level exports

  -- Export metadata
  export_type TEXT NOT NULL,        -- 'idr_pdf', 'photos_pdf', 'form_pdf', 'folder'
  format TEXT NOT NULL,             -- 'pdf', 'zip', 'folder'
  title TEXT NOT NULL,              -- Display name
  description TEXT,                 -- Optional description

  -- File tracking
  local_path TEXT,                  -- Local file path (NULL if deleted locally)
  remote_path TEXT,                 -- Supabase Storage path
  file_hash TEXT,                   -- SHA-256 for integrity
  file_size_bytes INTEGER,          -- For storage reporting

  -- Status tracking
  status TEXT DEFAULT 'local',      -- 'local', 'uploading', 'synced', 'failed'
  sync_status TEXT DEFAULT 'pending', -- Standard sync status

  -- User attribution
  created_by TEXT NOT NULL,         -- User ID who created export
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  synced_at TEXT,                   -- When last synced to cloud

  -- Review tracking
  review_status TEXT DEFAULT 'none', -- 'none', 'pending', 'approved', 'changes_requested'
  reviewed_by TEXT,                  -- Supervisor user ID
  reviewed_at TEXT,

  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (entry_id) REFERENCES daily_entries(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_export_registry_project ON export_registry(project_id);
CREATE INDEX idx_export_registry_entry ON export_registry(entry_id);
CREATE INDEX idx_export_registry_status ON export_registry(status);
CREATE INDEX idx_export_registry_review ON export_registry(review_status);
CREATE INDEX idx_export_registry_created_by ON export_registry(created_by);
CREATE INDEX idx_export_registry_created ON export_registry(created_at);
```

#### `export_comments` (Version 21)
```sql
CREATE TABLE export_comments (
  id TEXT PRIMARY KEY,
  export_id TEXT NOT NULL,
  user_id TEXT NOT NULL,

  -- Comment content
  comment_text TEXT NOT NULL,
  comment_type TEXT DEFAULT 'note', -- 'note', 'correction', 'approval', 'rejection'

  -- Optional: Reference to specific content
  reference_page INTEGER,           -- Page number if applicable
  reference_field TEXT,             -- Field name if applicable

  -- Timestamps
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  sync_status TEXT DEFAULT 'pending',

  FOREIGN KEY (export_id) REFERENCES export_registry(id) ON DELETE CASCADE
);

CREATE INDEX idx_export_comments_export ON export_comments(export_id);
CREATE INDEX idx_export_comments_user ON export_comments(user_id);
```

#### `project_users` (Version 21)
```sql
CREATE TABLE project_users (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  user_id TEXT NOT NULL,

  -- Role and permissions
  role TEXT NOT NULL,               -- 'owner', 'supervisor', 'inspector', 'viewer'
  can_export BOOLEAN DEFAULT TRUE,
  can_review BOOLEAN DEFAULT FALSE,
  can_edit BOOLEAN DEFAULT FALSE,

  -- Status
  status TEXT DEFAULT 'active',     -- 'active', 'invited', 'removed'
  invited_at TEXT,
  joined_at TEXT,

  -- Timestamps
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  sync_status TEXT DEFAULT 'pending',

  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  UNIQUE(project_id, user_id)
);

CREATE INDEX idx_project_users_project ON project_users(project_id);
CREATE INDEX idx_project_users_user ON project_users(user_id);
CREATE INDEX idx_project_users_role ON project_users(role);
```

### Supabase Schema (Mirror + RLS)

```sql
-- export_registry table with RLS
CREATE TABLE export_registry (
  -- Same schema as SQLite
);

-- RLS Policies
ALTER TABLE export_registry ENABLE ROW LEVEL SECURITY;

-- Users can see exports for projects they're members of
CREATE POLICY "Users can view project exports"
  ON export_registry FOR SELECT
  USING (
    project_id IN (
      SELECT project_id FROM project_users
      WHERE user_id = auth.uid() AND status = 'active'
    )
  );

-- Only creator can delete their exports
CREATE POLICY "Users can delete own exports"
  ON export_registry FOR DELETE
  USING (created_by = auth.uid());

-- Supervisors can update review status
CREATE POLICY "Supervisors can review exports"
  ON export_registry FOR UPDATE
  USING (
    project_id IN (
      SELECT project_id FROM project_users
      WHERE user_id = auth.uid()
      AND role IN ('owner', 'supervisor')
      AND status = 'active'
    )
  );
```

---

## Storage Architecture

### Local Storage Paths
```
{getApplicationDocumentsDirectory()}/
├── construction_inspector.db      # SQLite database
├── photos/                        # Photo storage (existing)
└── exports/                       # NEW: Managed exports
    ├── idr/                       # Daily entry reports
    │   └── {export_id}.pdf
    ├── photos/                    # Photo PDFs
    │   └── {export_id}.pdf
    ├── forms/                     # Form response PDFs
    │   └── {export_id}.pdf
    └── folders/                   # Folder exports (zipped)
        └── {export_id}.zip
```

### Supabase Storage Structure
```
exports/
├── {project_id}/
│   ├── {export_id}.pdf
│   └── {export_id}.zip
```

### StoragePathService
```dart
/// Centralized storage path management.
class StoragePathService {
  late final Directory _appDocsDir;
  late final Directory _tempDir;

  Future<void> initialize() async {
    _appDocsDir = await getApplicationDocumentsDirectory();
    _tempDir = await getTemporaryDirectory();
  }

  // Export paths
  Directory get exportsDir => Directory('${_appDocsDir.path}/exports');
  Directory get idrExportsDir => Directory('${_appDocsDir.path}/exports/idr');
  Directory get photoExportsDir => Directory('${_appDocsDir.path}/exports/photos');
  Directory get formExportsDir => Directory('${_appDocsDir.path}/exports/forms');
  Directory get folderExportsDir => Directory('${_appDocsDir.path}/exports/folders');

  // Photo paths (existing)
  Directory get photosDir => Directory('${_appDocsDir.path}/photos');

  // Temp paths
  Directory get thumbnailsDir => Directory('${_tempDir.path}/thumbnails');

  // OCR model paths (for future)
  Directory get ocrModelsDir => Directory('${_appDocsDir.path}/ocr_models');

  /// Get path for new export file
  String getExportPath(String exportId, ExportType type) {
    final subdir = switch (type) {
      ExportType.idrPdf => 'idr',
      ExportType.photosPdf => 'photos',
      ExportType.formPdf => 'forms',
      ExportType.folder => 'folders',
    };
    final ext = type == ExportType.folder ? 'zip' : 'pdf';
    return '${_appDocsDir.path}/exports/$subdir/$exportId.$ext';
  }

  /// Calculate total storage usage
  Future<StorageUsage> calculateUsage() async {
    return StorageUsage(
      exports: await _dirSize(exportsDir),
      photos: await _dirSize(photosDir),
      thumbnails: await _dirSize(thumbnailsDir),
      database: await _fileSize(File('${_appDocsDir.path}/construction_inspector.db')),
    );
  }
}
```

---

## Implementation Phases

### Phase 1: Export Registry Foundation (PR #1-2)

**Files to Create:**
- `lib/core/database/schema/export_tables.dart` - Schema definitions
- `lib/features/exports/data/models/export_record.dart` - Model class
- `lib/features/exports/data/datasources/local/export_registry_local_datasource.dart`
- `lib/features/exports/data/repositories/export_registry_repository.dart`
- `lib/services/storage_path_service.dart` - Centralized paths

**Files to Modify:**
- `lib/core/database/database_service.dart` - Add migration v21
- `lib/core/database/schema/schema.dart` - Export schema barrel
- `lib/features/pdf/services/pdf_service.dart` - Register exports after save
- `lib/features/toolbox/data/services/form_pdf_service.dart` - Register exports

**Database Migration:**
```dart
if (oldVersion < 21) {
  await db.execute(ExportTables.createExportRegistryTable);
  await db.execute(ExportTables.createExportCommentsTable);
  await db.execute(ExportTables.createProjectUsersTable);
  for (final index in ExportTables.indexes) {
    await db.execute(index);
  }
}
```

### Phase 2: Storage Management UI (PR #3-4)

**Files to Create:**
- `lib/features/settings/presentation/widgets/storage_section.dart`
- `lib/features/exports/presentation/screens/export_list_screen.dart`
- `lib/features/exports/presentation/screens/export_detail_screen.dart`
- `lib/features/exports/presentation/widgets/export_list_tile.dart`
- `lib/features/exports/presentation/widgets/storage_usage_card.dart`
- `lib/features/exports/presentation/providers/export_provider.dart`

**UI Components:**
- Settings → Storage section showing usage breakdown
- Export list with filters (by project, date, type, status)
- Export detail with actions (share, delete, download)
- Storage cleanup dialog with selective deletion

### Phase 3: Cloud Sync (PR #5-6)

**Files to Create:**
- `lib/features/exports/data/datasources/remote/export_remote_datasource.dart`
- `lib/features/exports/data/datasources/remote/export_storage_service.dart`

**Sync Flow:**
1. Export created → local_path set, status = 'local'
2. Online detected → upload to Supabase Storage
3. Upload complete → remote_path set, status = 'synced'
4. Sync export_registry record to Supabase table
5. Other users can now see the export

**Conflict Resolution:**
- Last-write-wins for metadata
- Storage files are immutable (new export = new file)

### Phase 4: Sharing Features (PR #7-8)

**Files to Create:**
- `lib/features/exports/services/export_share_service.dart`
- `lib/features/exports/presentation/widgets/share_options_sheet.dart`

**Sharing Options:**
1. **System Share Sheet** - Uses `share_plus` package
   - Share to any app (email, messaging, cloud drives)
   - Easy for tech-savvy users

2. **Direct Email** - Pre-compose email with attachment
   - One-tap "Email to Supervisor"
   - Uses `url_launcher` with mailto:

3. **Device Transfer** - Local network/Bluetooth
   - Uses `nearby_connections` package
   - Discovery of nearby devices
   - Direct file transfer without cloud

**Share Options Sheet:**
```dart
void showShareOptionsSheet(BuildContext context, ExportRecord export) {
  showModalBottomSheet(
    context: context,
    builder: (_) => ShareOptionsSheet(
      export: export,
      onShare: () => _shareViaSystem(export),
      onEmail: () => _shareViaEmail(export),
      onNearby: () => _shareViaNearby(export),
      onDownload: () => _downloadToDevice(export),
    ),
  );
}
```

### Phase 5: Multi-User Access (PR #9-10)

**Files to Create:**
- `lib/features/projects/data/models/project_user.dart`
- `lib/features/projects/data/datasources/local/project_users_local_datasource.dart`
- `lib/features/projects/data/datasources/remote/project_users_remote_datasource.dart`
- `lib/features/projects/presentation/screens/project_team_screen.dart`
- `lib/features/projects/presentation/widgets/invite_user_dialog.dart`

**Role Permissions:**
| Role | View Exports | Create Exports | Review | Edit Project |
|------|--------------|----------------|--------|--------------|
| Owner | ✓ | ✓ | ✓ | ✓ |
| Supervisor | ✓ | ✓ | ✓ | ✗ |
| Inspector | ✓ | ✓ | ✗ | ✗ |
| Viewer | ✓ | ✗ | ✗ | ✗ |

### Phase 6: Review Workflow (PR #11-12)

**Files to Create:**
- `lib/features/exports/data/models/export_comment.dart`
- `lib/features/exports/presentation/screens/review_screen.dart`
- `lib/features/exports/presentation/widgets/comment_thread.dart`
- `lib/features/exports/presentation/widgets/review_actions_bar.dart`
- `lib/features/exports/presentation/providers/review_provider.dart`

**Review Flow:**
1. Inspector exports report → review_status = 'none'
2. Inspector marks "Submit for Review" → review_status = 'pending'
3. Supervisor opens review → sees PDF with comment panel
4. Supervisor adds comments/corrections
5. Supervisor marks "Approved" or "Changes Requested"
6. Push notification sent to inspector
7. Inspector views changes, acknowledges

### Phase 7: Push Notifications (PR #13-14)

**Packages to Add:**
```yaml
dependencies:
  firebase_messaging: ^15.0.0
  flutter_local_notifications: ^18.0.0
```

**Files to Create:**
- `lib/services/push_notification_service.dart`
- `lib/features/notifications/presentation/providers/notification_provider.dart`

**Notification Types:**
- `review_requested` - Export submitted for review
- `review_completed` - Supervisor finished review
- `comment_added` - New comment on export
- `changes_requested` - Supervisor requested changes
- `export_shared` - Someone shared an export with you

---

## Codebase Context (From Session Research)

### Current Storage Architecture
- Photos: `{appDocs}/photos/` - Working well
- Thumbnails: `{tempDir}/thumbnails/` - ImageService with LRU cache
- Exports: NOT tracked - FilePicker saves to user-selected locations
- Clear cache: `clear_cache_dialog.dart` clears temp + non-existent `/exports`

### Current PDF Export Services
- `PdfService.saveEntryExport()` - IDR reports
- `FormPdfService.savePdfWithPicker()` - Form responses
- `PhotoPdfService.photosToMultiPagePdf()` - Photo collections
- All use FilePicker, no tracking

### Current Sync Architecture
- `SyncService` (legacy) handles bidirectional sync
- `SyncOrchestrator` routes based on project mode
- `sync_queue` table for offline operations
- `sync_status` field on syncable entities
- Photos sync to Supabase Storage bucket

### Current Database
- Version 20 with 14 domain tables
- TEXT UUIDs for offline-first
- Foreign key cascading
- Schema files in `lib/core/database/schema/`
- Proven migration patterns

### Current Permissions
- `PermissionService` handles Android storage permissions
- `MANAGE_EXTERNAL_STORAGE` for Android 11+
- FilePicker for user-selected save locations

### Settings UI Patterns
- ListView with sections (SectionHeader + Divider)
- Local state for toggles, Provider for complex state
- SnackBarHelper for feedback
- Async safety: always check `mounted` after await
- TestingKeys for all interactive elements

---

## OCR Dual-Engine Notes (Deferred)

When ML Kit proves insufficient, add PaddleOCR:

### PaddleOCR Integration
```dart
/// PaddleOCR service for high-accuracy OCR.
/// ~20-30MB bundled models.
class PaddleOcrService {
  /// Same interface as MlKitOcrService
  Future<String> recognizeFromBytes(Uint8List imageBytes);
  Future<OcrResult> recognizeWithConfidence(Uint8List imageBytes);
}
```

### Dual-Engine Strategy
```dart
enum OcrEngine { mlKit, paddleOcr, auto }

class OcrOrchestrator {
  Future<OcrResult> processPage(Uint8List imageBytes, {OcrEngine engine = OcrEngine.auto}) async {
    if (engine == OcrEngine.auto) {
      // Try ML Kit first
      final mlKitResult = await _mlKit.recognizeWithConfidence(imageBytes);

      if (mlKitResult.confidence >= 0.70) {
        return mlKitResult;
      }

      // Fall back to PaddleOCR for low confidence
      return await _paddleOcr.recognizeWithConfidence(imageBytes);
    }

    // Use specified engine
    return engine == OcrEngine.mlKit
        ? await _mlKit.recognizeWithConfidence(imageBytes)
        : await _paddleOcr.recognizeWithConfidence(imageBytes);
  }
}
```

### Table Structure Detection
PaddleOCR PP-Structure module can detect:
- Column boundaries
- Row boundaries
- Cell contents with positions

This enables automatic mapping to bid item columns.

---

## Future: VPN Integration

User mentioned eventual integration with company VPN/file system:

### Concept
```
Inspector Phone
    ↓
Supabase Cloud (primary storage)
    ↓
Scheduled Sync Job (company server)
    ↓
Company VPN → File System
```

### Requirements (TBD)
- Company's VPN configuration details
- File system path structure
- Authentication method
- Sync frequency (daily per user requirement)
- Conflict handling with company copies

### Potential Implementation
1. Supabase Edge Function triggered daily
2. Downloads all new exports for company
3. Pushes to company's API/webhook
4. Company's system handles VPN and file placement

---

## Testing Strategy

### Unit Tests
- ExportRegistryRepository: CRUD, filtering, status updates
- StoragePathService: Path generation, size calculation
- ExportShareService: Share intent generation

### Widget Tests
- ExportListScreen: Filtering, empty states
- ExportDetailScreen: Actions, status display
- ShareOptionsSheet: All options visible

### Integration Tests
- Full export flow: Generate → Register → List → Share
- Cloud sync: Local → Upload → Remote visible
- Review flow: Submit → Comment → Notify → Acknowledge

### E2E Tests (Patrol)
- Export IDR and find in exports list
- Share export via email
- Supervisor review workflow

---

## Risk Mitigation

### Risk 1: Storage space on device
**Mitigation**:
- Auto-cleanup of old synced exports
- User-configurable retention period
- Clear warnings when storage low

### Risk 2: Large exports fail to upload
**Mitigation**:
- Chunked upload for files >10MB
- Resume interrupted uploads
- Background upload with progress

### Risk 3: Review conflicts
**Mitigation**:
- Lock export during active review
- Show "being reviewed by X" indicator
- Notification if someone else starts reviewing

### Risk 4: Offline review sync
**Mitigation**:
- Queue review actions in sync_queue
- Sync comments when online
- Show pending sync indicator

---

## Dependencies & Blockers

**Depends on:**
- Nothing (can start immediately)

**Should complete before:**
- VPN integration (needs export system first)
- Advanced reporting features

**Parallel work possible:**
- OCR integration (separate feature)
- UI polish elsewhere

---

## Verification Checklist

Before marking phase complete:

### Phase 1-2 (Registry + UI)
- [ ] Export registry table created
- [ ] Exports appear in list after generation
- [ ] Storage usage displays correctly
- [ ] Delete removes file and record

### Phase 3-4 (Sync + Share)
- [ ] Exports upload to Supabase Storage
- [ ] Share via system sheet works
- [ ] Email share opens mail client
- [ ] Nearby share discovers devices

### Phase 5-6 (Multi-user + Review)
- [ ] Multiple users see same project exports
- [ ] Supervisor can add comments
- [ ] Review status updates correctly
- [ ] Push notifications deliver

### Final
- [ ] All tests pass
- [ ] No analyzer warnings
- [ ] Manual testing complete
- [ ] Documentation updated
