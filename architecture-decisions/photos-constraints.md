# Photos Constraints

**Feature**: Photo Capture & Management
**Scope**: All code in `lib/features/photos/` and photo lifecycle logic

---

## Hard Rules (Violations = Reject)

### Offline Capture + Storage
- ✗ No requiring network to take photos
- ✓ All photos captured to local device storage (Documents/construction-inspector/)
- ✓ Photo metadata (filename, location, timestamp) written to SQLite immediately
- ✗ No preventing photo capture due to network unavailability
- ✓ Sync job processes photos asynchronously (move to Supabase, update status)

**Why**: Inspectors must photograph site conditions regardless of connectivity.

### Sync Status Tracking
- ✗ No ambiguity about which photos are synced vs. pending
- ✓ Photo record includes: local_path, sync_status (PENDING, IN_PROGRESS, SYNCED), sync_error (nullable)
- ✓ UI must display sync status visually (spinner for pending, checkmark for synced, error icon for failures)
- ✗ No deleting photos while sync_status = IN_PROGRESS
- ✓ Retry failed syncs with exponential backoff (1s, 2s, 4s, 8s, max 3 attempts)

**Why**: Inspectors know what's safe to delete; prevents partial uploads.

### File Lifecycle Management
- ✗ No keeping original high-res photo after upload to Supabase
- ✓ After successful sync (sync_status = SYNCED): Delete local file from device storage
- ✓ Metadata (photo record in SQLite) persists (reference to Supabase URL)
- ✗ No re-uploading if local file deleted

**Why**: Conserves device storage; Supabase is source of truth.

### Photo-Entry Association
- ✗ No orphan photos (photos not attached to entries)
- ✓ Every photo must have entry_id (required, not nullable)
- ✓ Entry can have multiple photos
- ✗ No moving photos between entries after creation (entry_id immutable)

**Why**: Audit trail clarity; photos must be associated with inspection context.

### Metadata Requirements
- ✓ Photo must include: id, entry_id, local_path (until synced), supabase_url (after synced), timestamp (UTC), location (nullable), caption (nullable), sync_status
- ✗ No optional metadata (all required fields present)
- ✓ Geolocation optional (user can capture without GPS)

**Why**: Complete audit trail; timestamp proves when photo taken.

---

## Soft Guidelines (Violations = Discuss)

### Performance Targets
- Photo capture (UI + file write): < 500ms
- Thumbnail generation (150px square): < 100ms
- Sync photo to Supabase: < 5 seconds per photo (on 4G)
- Load photo gallery (20-100 photos): < 1 second

### Image Optimization
- Recommend: Compress photos to max 2MP before upload
- Recommend: Generate thumbnails for gallery view (not full resolution)

### Test Coverage
- Target: >= 85% for photo workflows
- Scenarios: Capture offline, sync online, failed sync retry, delete after sync

---

## Integration Points

- **Depends on**:
  - `entries` (photos must be attached to entries)
  - `sync` (photos queued for synchronization)
  - `locations` (optional: geotag photo with GPS)

- **Required by**:
  - `entries` (photo reference in entries UI)
  - `dashboard` (recent photos preview)
  - `sync` (photos primary data entity to sync)

---

## Performance Targets

- Photo capture: < 500ms
- Thumbnail generation: < 100ms
- Sync per photo: < 5 seconds (4G)
- Gallery load (20-100 photos): < 1 second

---

## Testing Requirements

- >= 85% test coverage for photo workflows
- Unit tests: Sync status transitions, file lifecycle, metadata validation
- Integration tests: Capture offline→sync online→verify Supabase URL
- Contract tests: Entry-photo relationship immutability, sync status state machine
- Offline scenario: Capture 10 photos, lose network, go online, verify all synced and local files deleted

---

## Reference

- **Architecture**: `docs/features/feature-photos-architecture.md`
- **Shared Rules**: `architecture-decisions/data-validation-rules.md`
- **Sync Integration**: `architecture-decisions/sync-constraints.md`
