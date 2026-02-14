# Dashboard Constraints

**Feature**: Dashboard & Overview
**Scope**: All code in `lib/features/dashboard/` and home screen presentation logic

---

## Hard Rules (Violations = Reject)

### Read-Only Aggregator
- ✗ No direct edits from dashboard (no buttons to edit entries/photos/contractors)
- ✓ Dashboard reads from: entries, photos, contractors, projects, quantities repositories
- ✓ All edit actions navigate to dedicated feature screens (entries screen, projects screen, etc.)
- ✗ No custom edit widgets on dashboard (preserve separation of concerns)

**Why**: Dashboard is read-only aggregator; edits belong to feature-specific screens.

### No Dashboard-Specific Persistence
- ✗ No dashboard state saved to database (dashboard_state table)
- ✓ Dashboard views are ephemeral (computed from source data)
- ✓ User preferences (refresh interval, widget visibility) stored in settings feature
- ✗ No caching dashboard data (always compute from latest source entities)

**Why**: Source of truth is feature data, not aggregated copies.

### Inherits Dependency Constraints
- ✓ Dashboard MUST respect all constraints from: entries, photos, contractors, projects, quantities, settings
- ✓ If entry workflow changes, dashboard must adapt (no special-casing)
- ✗ No bypassing sync constraints to show "draft entries before synced"

**Why**: Dashboard is read-only view of canonical feature data.

---

## Soft Guidelines (Violations = Discuss)

### Performance Targets
- Dashboard load: < 1 second (pull from cache, 100 recent items max)
- Widget rebuild on data change: < 500ms
- Scroll gallery (50 photos): < 60fps

### Data Limits for Performance
- Recommend: Show only recent 7-14 days of entries
- Recommend: Show only 5-10 most recent photos
- Recommend: Show only top 5 highest-variance quantities

### Offline Behavior
- Recommend: Show cached dashboard data while offline
- Recommend: "Last updated X minutes ago" indicator when stale

### Test Coverage
- Target: >= 80% for dashboard widgets (lower than feature-specific, because read-only)
- Scenarios: Load with 0 items, load with 100+ items, refresh on data change

---

## Integration Points

- **Depends on**:
  - `entries` (recent entries feed)
  - `photos` (recent photos gallery)
  - `contractors` (team summary)
  - `projects` (active project display)
  - `quantities` (variance summary)
  - `settings` (user preferences for widget visibility)
  - `sync` (online/offline status indicator)

- **Required by**:
  - None (dashboard is terminal screen, nothing depends on it)

---

## Performance Targets

- Dashboard load: < 1 second
- Widget rebuild: < 500ms
- Scroll gallery: >= 60fps

---

## Testing Requirements

- >= 80% test coverage for dashboard widgets (read-only, lower bar than features)
- Widget tests: Load states (empty, loading, 100+ items), data refresh
- Integration tests: Pull recent data from all dependencies
- Edge cases: 0 entries, 0 photos, all entries in draft state, network offline

---

## Reference

- **Architecture**: `docs/features/feature-dashboard-architecture.md`
- **Shared Rules**: `architecture-decisions/data-validation-rules.md`
