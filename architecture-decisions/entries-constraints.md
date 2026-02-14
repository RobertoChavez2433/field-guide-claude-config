# Entries Constraints

**Feature**: Entry Management (Daily Inspection Logs)
**Scope**: All code in `lib/features/entries/` and entry lifecycle logic

---

## Hard Rules (Violations = Reject)

### Offline-First Writes
- ✗ No requiring network connection to create/edit entries
- ✓ All entry writes (create, update, delete) must succeed locally first (SQLite)
- ✓ Queued for sync, not immediately pushed to Supabase
- ✗ No "save to draft, upload later" modal — users see success immediately

**Why**: Inspectors work on construction sites with spotty networks; must not block workflow.

### Draft/Complete/Submitted Workflow
- ✗ No skipping workflow states (can't jump from DRAFT to SUBMITTED without COMPLETE)
- ✓ Entry states: DRAFT → COMPLETE → SUBMITTED (three states, one-way transitions)
- ✗ No reverting COMPLETE or SUBMITTED entries to DRAFT
- ✓ SUBMITTED entries read-only (block all edits in UI)

**Why**: Immutable submitted entries prevent audit log corruption; clear workflow prevents confusion.

### Date-Scoped Queries
- ✗ No loading "all entries ever" without date filter
- ✓ All queries must include date range (startDate, endDate) or current_date ±N days
- ✓ Default view: Today's entries only
- ✗ No infinite scroll loading past entries (pagination required)

**Why**: Prevents memory overload and poor UX with 1000+ entries.

### Entry-Project Relationship
- ✗ No moving entry between projects after creation
- ✓ Entry.project_id immutable after creation (set at write time, never updated)
- ✓ Querying entries by project_id must enforce this constraint in repository

**Why**: Prevents sync conflicts and audit trail ambiguity.

### Workflow Metadata
- ✓ Entry must include: id, project_id, created_at, completed_at (nullable), submitted_at (nullable), status
- ✗ No optional metadata (all fields required for validation)
- ✓ Timestamps in UTC, server-side generated on sync validation

**Why**: Audit trail consistency; prevents incomplete state tracking.

---

## Soft Guidelines (Violations = Discuss)

### Performance Targets
- Load today's entries: < 500ms
- Create entry: < 100ms (SQLite write only)
- Transition DRAFT→COMPLETE or COMPLETE→SUBMITTED: < 200ms
- Querying 30-day window: < 1 second

### Bulk Operations
- If bulk-editing 10+ entries: Show loading indicator, queue edits, confirm completion
- Recommend: Limit UI bulk edit to <= 50 entries per operation

### Test Coverage
- Target: >= 85% for entry workflows
- Scenarios: Draft creation, state transitions, date filtering, offline sync

---

## Integration Points

- **Depends on**:
  - `projects` (root entity, entries scoped to projects)
  - `sync` (queue edits for synchronization)
  - `photos` (entries can attach photos, but photos optional)
  - `contractors` (entries can reference contractor personnel)
  - `quantities` (entries can reference bid items)

- **Required by**:
  - `dashboard` (home screen shows recent entries)
  - `quantities` (variance tracking uses entries as source)
  - `sync` (entries primary data entity to sync)

---

## Performance Targets

- Load today's entries: < 500ms
- Create entry: < 100ms (local SQLite)
- State transitions: < 200ms
- Date-range query (7-30 days): < 1 second

---

## Testing Requirements

- >= 85% test coverage for entry workflows
- Unit tests: Workflow state transitions (valid/invalid), date filtering, immutability
- Integration tests: Offline create→sync→verify in Supabase
- Contract tests: Entry-project relationship immutability, workflow state machine
- Offline scenario: Create 10 entries offline, go online, verify all synced in correct state

---

## Reference

- **Architecture**: `docs/features/feature-entries-architecture.md`
- **Shared Rules**: `architecture-decisions/data-validation-rules.md`
- **Sync Integration**: `architecture-decisions/sync-constraints.md`
