# Locations Constraints

**Feature**: Location & GPS Tagging
**Scope**: All code in `lib/features/locations/` and location-based operations

---

## Hard Rules (Violations = Reject)

### Project-Scoped Locations
- ✗ No location visible across multiple projects
- ✓ Every location belongs to exactly one project (location.project_id immutable)
- ✓ Querying locations MUST filter by project_id
- ✗ No listing "all locations across all projects"
- ✓ Deleting project must cascade-delete all associated locations

**Why**: Locations are site-specific; prevents data leakage.

### GPS Optional (Not Required)
- ✗ No blocking location creation without GPS coordinates
- ✓ Location can be created with name/description only (latitude/longitude nullable)
- ✓ GPS capture optional (user can add coordinates later)
- ✓ Location-based filtering (map view, radius search) only works if GPS present

**Why**: Offline users can create locations; GPS added when available.

### Location-Entry Association
- ✗ No orphan locations (unused across all entries)
- ✓ Location can reference 0+ entries (many-to-many via entry_locations junction table)
- ✓ Location can appear in multiple entries
- ✗ No modifying entry-location associations after entry marked SUBMITTED

**Why**: Entries tagged with site location for audit trail.

### Simple CRUD (No Complex Hierarchy)
- ✗ No nested locations (parent-child relationships)
- ✗ No location categorization (residential, commercial, etc.) — store as flat list
- ✓ Location attributes: id, project_id, name, description, latitude (nullable), longitude (nullable), created_at, updated_at

**Why**: Construction sites are typically flat geometry; no hierarchy needed.

---

## Soft Guidelines (Violations = Discuss)

### Performance Targets
- Load locations for project: < 200ms (< 500 locations)
- Create location: < 100ms
- Geo-query (radius search): < 500ms
- Map tile render (50 locations): < 1 second

### GPS Accuracy
- Recommend: Accept GPS accuracy >= 50 meters
- Warn user if accuracy worse (may indicate poor signal)

### Bulk Operations
- Recommend: Bulk import locations (CSV with lat/lon)
- Limit: Max 500 locations per project

### Test Coverage
- Target: >= 85% for location workflows
- Scenarios: GPS optional, project scoping, entry association

---

## Integration Points

- **Depends on**:
  - `projects` (root entity, locations scoped to projects)
  - `entries` (locations tagged in entries for context)
  - `sync` (location changes queued for synchronization)

- **Required by**:
  - `entries` (optional location tagging)
  - `dashboard` (location summary)
  - `sync` (locations primary data entity to sync)

---

## Performance Targets

- Load locations for project: < 200ms
- Create location: < 100ms
- Geo-query (radius search): < 500ms
- Map render (50 locations): < 1 second

---

## Testing Requirements

- >= 85% test coverage for location workflows
- Unit tests: Project scoping, GPS optional, immutability
- Integration tests: CRUD with sync, entry location tagging, geo-queries
- Contract tests: Location-project relationship, cascade delete
- Offline scenario: Create locations without GPS, sync later, verify metadata preserved

---

## Reference

- **Architecture**: `docs/features/feature-locations-architecture.md`
- **Shared Rules**: `architecture-decisions/data-validation-rules.md`
- **Sync Integration**: `architecture-decisions/sync-constraints.md`
