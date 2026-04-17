# Manual Role Boundaries And RLS Flows

Use this overlay for role and RLS policy testing. It complements feature files;
it is not parsed by `tools/validate_feature_spec.py`.

## Roles

- `admin`: full company/team/admin/project powers
- `engineer`: project-management and field-data powers; not admin-only powers
- `officeTechnician`: project-management and assignment-related powers; not
  admin-only powers
- `inspector`: field-data edit powers; denied project-management/admin/
  pay-app/analytics/pdf-management surfaces where policy says denied

## Evidence

For each denied path, record:

- UI result
- current route/screen
- debug log slice
- sync state if relevant
- backend/RLS verification when available

Service-role checks are verification-only. They are never the app actor.

## Flow Checklist

- [ ] Project visibility: assigned visible, unassigned denied/hidden,
      cross-company denied/hidden.
- [ ] Project mutations: create, edit, archive, restore, delete, and assignment
      management match role policy.
- [ ] Field data: entries, forms, quantities, to-dos, gallery/photos, and
      contractors work for allowed roles and sync across devices.
- [ ] Pay applications: admin/engineer/officeTechnician allowed; inspector
      denied or read-only according to policy.
- [ ] Analytics: admin/engineer/officeTechnician allowed; inspector denied.
- [ ] PDF imports: admin/engineer/officeTechnician allowed; inspector denied.
- [ ] Admin settings: dashboard, member approval, role change, deactivation,
      personnel types, and trash denied to non-admin roles where policy
      requires.
- [ ] Cross-company isolation: no role can view, deep-link, sync, or export
      another company's private records.
- [ ] Soft-delete/restore: visibility, restore access, and sync propagation
      match role policy.
- [ ] Export/document/form ownership: saved exports and form documents do not
      leak across project or company boundaries.

## Failure Categories

- `rls_policy`
- `permission_boundary`
- `cross_company_leak`
- `role_ui_mismatch`
- `sync_error`
- `sync_stale_state`
- `broken_forward_flow`
- `broken_back_flow`
