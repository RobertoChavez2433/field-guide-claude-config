# Settings Constraints

**Feature**: App Settings & Configuration
**Scope**: All code in `lib/features/settings/` and user preference persistence

---

## Hard Rules (Violations = Reject)

### Theme-Only Storage
- ✗ No syncing settings to Supabase (except user preferences for display)
- ✓ Settings stored locally in SQLite + SharedPreferences only
- ✓ Supported settings: theme (light/dark), language (en/es), notification_enabled (bool)
- ✗ No storing sensitive data (passwords, tokens) in settings feature

**Why**: Settings are device-specific; each device has independent preferences.

### No Remote Sync for Settings
- ✗ No settings sync orchestration in sync feature
- ✓ Settings remain local and independent across devices
- ✓ If user logs in on 2 devices, each has independent theme/notification settings
- ✗ No "sync settings across devices" feature (out of scope)

**Why**: Simplifies sync logic; users typically have device-specific preferences.

### Current Project Tracking
- ✓ Settings stores: current_project_id (which project user last viewed)
- ✓ Used on app boot to auto-select project
- ✓ Updated whenever user switches projects
- ✗ No persisting "project history" beyond current selection

**Why**: Session continuity; users expect app to remember last context.

### Optional Features Flag
- ✓ Settings can include: offline_mode (bool, user can force offline)
- ✓ Used by auth/sync to respect user preference
- ✗ No feature flags for A/B testing (not in scope for settings)

**Why**: Inspector can manually disable sync for testing/network issues.

---

## Soft Guidelines (Violations = Discuss)

### Performance Targets
- Load settings: < 100ms
- Update setting (theme change): < 100ms
- No disk I/O blocking UI (use background task if needed)

### Storage Limits
- Recommend: Settings file < 10 KB (SharedPreferences is light)
- Recommend: No storing large blobs (use dedicated tables if needed)

### Test Coverage
- Target: >= 80% for settings (simple CRUD)
- Scenarios: Load, update theme/language, switch projects, offline toggle

---

## Integration Points

- **Depends on**:
  - `projects` (stores current_project_id)
  - `auth` (may reference user_id for per-user settings)

- **Required by**:
  - `auth` (offline mode preference)
  - `sync` (offline mode respected)
  - `dashboard` (theme applied globally)

---

## Performance Targets

- Load settings: < 100ms
- Update setting: < 100ms
- No blocking I/O

---

## Testing Requirements

- >= 80% test coverage for settings (simple CRUD, lower bar than complex features)
- Unit tests: CRUD operations, type safety (theme enum, not string)
- Integration tests: Theme change propagates to all widgets
- Edge cases: Settings file corrupted (fallback to defaults), missing keys (use fallback values)

---

## Reference

- **Architecture**: `docs/features/feature-settings-architecture.md`
- **Shared Rules**: `architecture-decisions/data-validation-rules.md`
