---
feature: contractors
type: overview
scope: Contractor, Equipment & Personnel Management
updated: 2026-02-13
---

# Contractors Feature Overview

## Purpose

The Contractors feature manages prime contractors, sub-contractors, equipment, and personnel types associated with construction projects. It enables inspectors to track who is on-site, what equipment is deployed, and what roles people fulfill. Contractors are created during project setup and referenced throughout daily entries and project documentation.

## Key Responsibilities

- **Contractor Management**: Create, edit, and delete prime and sub-contractors with contact information
- **Equipment Tracking**: Define equipment types, assign to contractors and projects, track usage hours
- **Personnel Types**: Define personnel categories (e.g., "Foreman", "Laborer"), track counts in daily entries
- **Contractor Association**: Link contractors to specific projects and daily entries
- **Entry Personnel/Equipment**: Manage what personnel and equipment were used on specific job site visits

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/contractors/data/models/contractor.dart` | Contractor model with prime/sub type |
| `lib/features/contractors/data/models/equipment.dart` | Equipment model |
| `lib/features/contractors/data/models/personnel_type.dart` | Personnel category model |
| `lib/features/contractors/data/repositories/contractor_repository.dart` | Contractor CRUD operations |
| `lib/features/contractors/data/repositories/equipment_repository.dart` | Equipment CRUD operations |
| `lib/features/contractors/presentation/providers/contractor_provider.dart` | Contractor state management |
| `lib/features/contractors/presentation/providers/equipment_provider.dart` | Equipment state management |

## Data Sources

- **SQLite**: Persists contractors, equipment, personnel types, and entry-specific assignments
- **Project Setup**: Contractors created during project configuration in `projects` feature
- **Daily Entries**: Personnel and equipment usage recorded during entry creation in `entries` feature

## Integration Points

**Depends on:**
- `core/database` - SQLite schema for contractors, equipment, personnel types
- `projects` - Contractors associated with projects during setup

**Required by:**
- `entries` - Entry detail screen manages personnel, equipment, contractors per entry
- `dashboard` - Project summary shows active contractors and equipment counts
- `sync` - Contractor/equipment/personnel data synced to Supabase

## Offline Behavior

Contractors are **fully offline-capable**. Creation, editing, and assignment to entries occur entirely offline. All data persists in SQLite. Cloud sync (if implemented) handles async push of contractor/equipment updates. Inspectors can manage contractors entirely offline; sync happens during dedicated sync operations.

## Edge Cases & Limitations

- **Contractor Deletion**: Soft-delete only; entries referencing deleted contractor still accessible (no cascade delete)
- **Equipment Hours**: Tracked per entry (hours_used field), no daily rollup
- **Personnel Counts**: Tracked as integer count per type per entry; no individual roster
- **Contact Information**: phone and contactName are optional; no validation of phone format
- **Equipment Assignment**: Can assign same equipment to multiple contractors (many-to-many possible via custom junction table)
- **Type Restrictions**: ContractorType is enum {prime, sub}; cannot add custom types

## Detailed Specifications

See `architecture-decisions/contractors-constraints.md` for:
- Hard rules on contractor deletion and data integrity
- Personnel count validation and range limits
- Equipment hours tracking and rollup semantics

See `rules/database/schema-patterns.md` for:
- SQLite schema for contractors, equipment, personnel types, and junction tables
- Foreign key relationships and cascade behavior

