# Projects Constraints

**Feature**: Project Management
**Scope**: All code in `lib/features/projects/` and project lifecycle logic

---

## Hard Rules (Violations = Reject)

### Root Entity — Gating All Features
- ✗ No creating entries, photos, contractors, locations, quantities WITHOUT a parent project
- ✓ Every feature entity (entry, photo, contractor, location, quantity) MUST have project_id
- ✓ Project is root; all other features scoped to project
- ✗ No feature-specific queries that span multiple projects
- ✓ User context always includes current_project_id (session state)

**Why**: Multi-project support requires strict project isolation; prevents data leakage.

### MDOT vs Local Agency Modes
- ✓ Project has mode: MDOT or LOCAL_AGENCY (enum, set at creation, immutable)
- ✗ No changing mode after project created
- ✓ Mode gates which fields are required/visible:
  - MDOT: Requires bid schedule, route number, funding source (M-roads specific)
  - LOCAL_AGENCY: Requires general contractor, engineer contact, budget (general public works)
- ✓ Project form shows mode-specific fields only

**Why**: Different workflows for state highway (MDOT) vs. local projects.

### Project Lifecycle
- ✓ Project states: PLANNING → ACTIVE → COMPLETE → ARCHIVED (linear progression)
- ✗ No reverting project state (can't go from ACTIVE back to PLANNING)
- ✓ Only ACTIVE projects allow entry/photo creation
- ✓ COMPLETE projects read-only (block all edits)
- ✓ ARCHIVED projects hidden by default (filter query)

**Why**: Lifecycle prevents accidental modifications to closed projects.

### Required Metadata
- ✓ Project must include: id, name, mode (MDOT/LOCAL_AGENCY), location, start_date, status, user_id (owner), created_at, updated_at
- ✓ Mode-specific fields: bid_route (MDOT), general_contractor (LOCAL_AGENCY)
- ✗ No nullable status or owner (required for audit trail)

**Why**: Complete project identity; audit trail tracks project ownership.

### Cascade Delete Rules
- ✓ Deleting project cascades to: entries, photos, contractors, locations, quantities (all scoped entities)
- ✓ Confirm deletion with user (cannot be undone)
- ✗ No hard deletion without explicit confirmation + soft-delete flag check

**Why**: Prevents accidental data loss; soft-delete allows recovery window.

---

## Soft Guidelines (Violations = Discuss)

### Performance Targets
- Load projects for user: < 300ms (< 100 projects)
- Create project: < 200ms
- Switch current project (update session): < 100ms
- Query active projects only: < 200ms

### Bulk Operations
- Recommend: Bulk import projects (CSV with name, mode, location)
- Limit: Max 500 projects per user

### Archive Strategy
- Recommend: Auto-archive projects older than 2 years (configurable)
- Recommend: Show archive count on dashboard

### Test Coverage
- Target: >= 85% for project workflows
- Scenarios: Lifecycle transitions, mode-specific fields, cascade delete

---

## Integration Points

- **Depends on**:
  - `auth` (project ownership verified against user_id)
  - `settings` (current_project_id stored in user preferences)

- **Required by**:
  - ALL features (entries, photos, contractors, locations, quantities, dashboard must filter by project_id)
  - `sync` (projects synced, all other entities dependent)

---

## Performance Targets

- Load projects for user: < 300ms
- Create project: < 200ms
- Switch current project: < 100ms
- Query active projects: < 200ms

---

## Testing Requirements

- >= 85% test coverage for project workflows
- Unit tests: Lifecycle state machine, mode-specific field validation, cascade delete
- Integration tests: Create project→create entries→complete project (read-only test)→archive
- Contract tests: Project-feature relationship (entries always have project_id), cascade integrity
- Multi-project scenario: Create 2 projects, create entries in each, switch projects, verify isolation

---

## Reference

- **Architecture**: `docs/features/feature-projects-architecture.md`
- **Shared Rules**: `architecture-decisions/data-validation-rules.md`
- **Sync Integration**: `architecture-decisions/sync-constraints.md`
