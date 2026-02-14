# Sync Conflict Strategy Constraints

## Hard Rules (Violations = Reject Proposal)
- ✗ MUST use last-write-wins conflict resolution ONLY (no merge attempts)
- ✗ MUST implement bidirectional sync (push & pull in same cycle)
- ✗ MUST validate checksum (SHA256) on all synced records
- ✗ MUST NOT attempt partial sync (all-or-nothing per feature)
- ✗ MUST NOT retry indefinitely (max 3 attempts per operation)

## Soft Guidelines (Violations = Discuss)
- ⚠ Use exponential backoff on sync retry (100ms → 300ms → 900ms)
- ⚠ Batch sync operations to reduce API calls (max 100 records/batch)
- ⚠ Log all conflicts (timestamp, feature, record_id, local vs. remote)
- ⚠ Performance target: < 5 seconds for 100-record sync

## Integration Points
- **Depends on**: All features with sync_status field (entries, photos, contractors, quantities, locations, projects)
- **Required by**: All synced features need SyncOrchestrator to manage push/pull

## Performance Targets
- Single record sync: < 500ms
- Batch sync (100 records): < 5 seconds
- Conflict detection: < 100ms per record
- Retry backoff: 100ms + exponential (max 3 attempts = 1.3 seconds)

## Testing Requirements
- >= 85% test coverage
- Unit tests: last-write-wins decision logic, checksum validation
- Integration tests: offline queue → sync → error recovery
- Conflict scenario: simultaneous edits on two devices
- Batch scenario: 100+ records with mixed success/failure

## References
- See `feature-sync-architecture.md` for SyncAdapter pattern
- See `feature-sync-overview.md` for integration points
- See `sync-patterns.md` for implementation details
