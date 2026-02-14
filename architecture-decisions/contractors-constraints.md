# Contractors Constraints

**Feature**: Contractor Management
**Scope**: All code in `lib/features/contractors/` and contractor-related operations

---

## Hard Rules (Violations = Reject)

### Project-Scoped CRUD
- ✗ No contractor visible across multiple projects
- ✓ Every contractor belongs to exactly one project (contractor.project_id immutable)
- ✓ Deleting project must cascade-delete all associated contractors
- ✓ Querying contractors MUST filter by project_id
- ✗ No listing "all contractors across all projects" without explicit user request + confirmation

**Why**: Contractors are site-specific; prevents data leakage and confusion.

### Personnel Tracking in Entries
- ✗ No creating entries without assigning personnel (contractor reference)
- ✓ Entry can reference 0+ contractors (many-to-many via entry_contractors junction table)
- ✓ Contractor can appear in multiple entries
- ✗ No modifying entry-contractor associations after entry marked SUBMITTED
- ✓ Entry submission captures personnel snapshot (who was on-site)

**Why**: Accurate personnel records for liability and accountability.

### Contractor Immutability
- ✗ No changing contractor.project_id after creation
- ✓ Name, contact, role, phone can be updated
- ✓ Deletion soft-deletes (is_deleted flag, not removed from DB) if contractor referenced in past entries
- ✗ Hard deletion only if no historical reference in entries

**Why**: Audit trail consistency; past entries must reference original contractor data.

### Required Metadata
- ✓ Contractor must include: id, project_id, name, role, email, phone, company, created_at, updated_at
- ✗ No null name/role (required for entry assignment)
- ✓ Email/phone optional (can be omitted for temporary on-site staff)

**Why**: Complete audit trail; personnel identifiable for future audits.

---

## Soft Guidelines (Violations = Discuss)

### Performance Targets
- Load contractors for project: < 200ms (< 500 contractors)
- Create contractor: < 100ms
- Assign contractor to entry: < 100ms
- Query contractor history for project: < 500ms

### Bulk Operations
- Recommend: Bulk-add contractors (CSV import) for project setup
- Limit: Max 1,000 contractors per project (warn user if approached)

### Test Coverage
- Target: >= 85% for contractor workflows
- Scenarios: CRUD, project scoping, soft delete, entry personnel assignment

---

## Integration Points

- **Depends on**:
  - `projects` (root entity, contractors scoped to projects)
  - `entries` (contractors assigned to entries for personnel tracking)
  - `sync` (contractor changes queued for synchronization)

- **Required by**:
  - `entries` (personnel assignment)
  - `sync` (contractors primary data entity to sync)

---

## Performance Targets

- Load contractors for project: < 200ms
- Create contractor: < 100ms
- Assign to entry: < 100ms
- Historical query: < 500ms

---

## Testing Requirements

- >= 85% test coverage for contractor workflows
- Unit tests: Project scoping, immutability, soft delete logic
- Integration tests: CRUD with sync, entry personnel assignment
- Contract tests: Contractor-project relationship immutability, cascade delete
- Project-scoping scenario: Create 2 projects, 10 contractors each, verify no cross-project leakage

---

## Reference

- **Architecture**: `docs/features/feature-contractors-architecture.md`
- **Shared Rules**: `architecture-decisions/data-validation-rules.md`
- **Sync Integration**: `architecture-decisions/sync-constraints.md`
