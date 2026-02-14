# Quantities Constraints

**Feature**: Quantity Tracking (Bid Items & Measurements)
**Scope**: All code in `lib/features/quantities/` and bid item tracking logic

---

## Hard Rules (Violations = Reject)

### Bid Item Tracking (Reference Data)
- ✗ No creating quantities without referencing a bid schedule item
- ✓ Quantity has: bid_item_id, unit_price, estimated_quantity (from bid schedule), actual_quantity (field data)
- ✓ Bid schedule imported from PDF via pdf feature
- ✗ No manually editing estimated_quantity (readonly, sourced from PDF)
- ✓ Only actual_quantity editable (inspector measures/counts on site)

**Why**: Bid schedule is contract document; actual quantities compared against it.

### Project-Scoped Quantities
- ✗ No quantity visible across multiple projects
- ✓ Every quantity belongs to exactly one project (via entry or direct project_id)
- ✓ Querying quantities MUST filter by project_id
- ✗ No listing "all quantities across all projects"

**Why**: Quantities are project-specific; bid schedule per project.

### Variance Calculation
- ✓ Variance = actual_quantity - estimated_quantity
- ✓ Variance tracked in SQLite (computed field, updated when actual_quantity changes)
- ✗ No computing variance in-app; store as record (enables filtering/sorting)
- ✓ Flag high-variance items (variance > 10% of estimated) for review

**Why**: Inspectors need to identify overage/shortage items quickly.

### Sync via Entries
- ✗ No direct sync of quantities to Supabase
- ✓ Quantities synced indirectly: Entry marks items as observed, quantities updated via entry submission
- ✓ Entry-quantity association: Entry references N quantities (entry_quantities junction table)
- ✓ Variance snapshot captured at entry submission (immutable historical record)

**Why**: Quantities are supporting data; entries are primary (who, what, when, where).

### Immutability After Entry Submission
- ✗ No changing actual_quantity after associated entry marked SUBMITTED
- ✓ Before submission: user can adjust actual_quantity freely
- ✓ After submission: quantity read-only (entry commits variance data)

**Why**: Audit trail; submitted entries capture quantity state at time of observation.

---

## Soft Guidelines (Violations = Discuss)

### Performance Targets
- Load quantities for project: < 200ms (< 1,000 items)
- Calculate variance: < 100ms per item
- Query high-variance items: < 300ms

### Variance Thresholds
- Recommend: Flag as "HIGH_VARIANCE" if > 10% deviation
- Recommend: Flag as "CRITICAL" if > 25% deviation
- Allow: Configurable thresholds in settings

### Test Coverage
- Target: >= 85% for quantity workflows
- Scenarios: Variance calculation, immutability after submission, bid item reference

---

## Integration Points

- **Depends on**:
  - `entries` (quantities associated with entries, captured at submission)
  - `projects` (quantities scoped to projects)
  - `pdf` (bid schedule imported as source data)
  - `sync` (variance data synced as part of entry submission)

- **Required by**:
  - `entries` (entry submission captures quantity variance)
  - `dashboard` (high-variance summary)
  - `sync` (quantities synced indirectly via entries)

---

## Performance Targets

- Load quantities for project: < 200ms
- Variance calculation: < 100ms per item
- Query high-variance items: < 300ms

---

## Testing Requirements

- >= 85% test coverage for quantity workflows
- Unit tests: Variance calculation, immutability after submission, bid item reference
- Integration tests: Import bid schedule→create entries→reference quantities→submit→verify variance immutable
- Contract tests: Quantity-entry relationship, bid item reference integrity
- Variance scenario: Create 10 quantities with estimated values, adjust actual values, verify variance flagging

---

## Reference

- **Architecture**: `docs/features/feature-quantities-architecture.md`
- **Shared Rules**: `architecture-decisions/data-validation-rules.md`
- **Sync Integration**: `architecture-decisions/sync-constraints.md`
