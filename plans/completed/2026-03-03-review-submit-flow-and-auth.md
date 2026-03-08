# Review & Submit Flow + Auth Session Management

**Created**: 2026-03-03 | **Status**: REVIEWED — Adversarial findings incorporated (Rev 2)
**Branch**: TBD (new feature branch off main)

---

## Adversarial Review Summary

Two independent reviews (architecture + security) identified 22 findings. All CRITICAL and HIGH findings have been incorporated into this revision. Key changes from Rev 1:

| Finding | Severity | Resolution |
|---------|----------|------------|
| `submitted` already exists in enum | CRITICAL | Plan corrected — remove `complete`, keep existing `submitted`. Enumerate all 35+ references. |
| `locationId` NOT NULL in SQLite + model | CRITICAL | SQLite table rebuild migration required. Model changes to `String?`. |
| Hardcoded Supabase credentials (pre-existing) | CRITICAL | Added as prerequisite task (remove `defaultValue` fallbacks). |
| `force_reauth` permanent lockout loop | HIGH | Changed to timestamp-based `reauth_before` (auto-expires). |
| No server-side session enforcement | HIGH | Configure Supabase refresh token lifetime to 7 days. |
| Offline bypass of force_reauth | HIGH | Added `last_config_check_at` with 24h max staleness. |
| No server-side status transition validation | HIGH | Added Supabase trigger for status transitions + anti-backdate. |
| Missing 35+ file references to `EntryStatus.complete` | HIGH | Full file list enumerated in Phase 1 tasks. |
| Revision number conflicts | HIGH | Revision number is informational only (last-write-wins). Server trigger manages increment. |
| Batch submit not atomic | MEDIUM | Wrap in SQLite transaction with single batch timestamp. |
| `package_info_plus` platform config | MEDIUM | Added Windows Runner.rc + verification task. |
| DB version bump unspecified | MEDIUM | Specified: bump to version 26. |
| GPS coordinates in debug logs | MEDIUM | Guard with `!kReleaseMode`, reduce precision to 2 decimal places. |
| Version comparison unspecified | MEDIUM | Use `pub_semver` package, try-catch fail-open. |
| `fromMap` crash on unknown status | MEDIUM | Add fallback deserialization (`?? EntryStatus.draft`). |
| Router redirect chain position | MEDIUM | Specified: after auth check, before profile routing. |
| Supabase migration file naming | MEDIUM | Named explicitly. |
| `last_active_at` tamper-prone | MEDIUM | Use `flutter_secure_storage` instead of SharedPreferences. |
| `app_config` schema fragile | MEDIUM | Added CHECK constraints + key whitelist + `updated_at` trigger. |
| Weather GPS prompt timing | LOW | Fetch after form visible, check permission first. |
| Sign-out cleanup pattern fragile | LOW | Clear `last_active_at` + `last_config_check_at` explicitly. |

---

## Overview

### Purpose
Three connected improvements:
1. A review-then-submit workflow so inspectors catch mistakes before entries become permanent records
2. Bug fixes for entry creation (weather, location, routing)
3. Auth session management with version gating, inactivity timeout, and remote kill switch

### Scope

**Included:**
- **Review & Submit Flow**: Drafts list with multi-select → guided review with inline editing → summary → batch submit. Soft-lock submitted entries with undo. Revision tracking.
- **Entry Creation Fixes**: Weather auto-fetch via GPS on create. Location optional for drafts, required at submit, with inline quick-add. Remove submit button from entry editor (draft-only).
- **Routing Fix**: Reset clears local DB + auth session → /login.
- **Auth Session Management**: Supabase `app_config` table with `min_version`, `force_update`, `reauth_before`, `reauth_reason`. 7-day inactivity timeout. `package_info_plus` for real version reading. Supabase refresh token lifetime set to 7 days.
- **Startup Gate**: App checks `app_config` on launch → blocks on version mismatch, signs out if `reauth_before` is in the future, shows update screen as needed.

**Excluded:**
- Supervisor approval workflow (future)
- Revision history browsing UI (data tracked, no UI yet)
- Play Store / App Store update prompts (no store access yet)
- Push notifications for update reminders

### Success Criteria
- Inspector can save drafts all week, then batch review and submit
- Submitted entries show badge, can be undone back to draft
- Weather auto-fills on entry creation, location is optional until submit
- Reset → login screen (clean slate)
- App blocks usage when below `min_version`
- Inactive sessions (7 days) force re-login (client + server enforced)
- Remote `reauth_before` timestamp forces re-login until it expires

---

## Data Model

### Modified Entity: `DailyEntry`

**IMPORTANT**: The `EntryStatus` enum already has three values: `{draft, complete, submitted}`. This plan **removes `complete`** and keeps `{draft, submitted}`. The `_submitEntry()` method and all `EntryStatus.complete` references (35+ across lib + test) must be updated.

| Field | Type | Change | Description |
|-------|------|--------|-------------|
| `status` | String (enum) | **MODIFY** | Remove `complete`. Keep `draft`, `submitted`. |
| `locationId` | String? | **MODIFY** | Change from `NOT NULL` to nullable. Drafts can omit location. |
| `submittedAt` | DateTime? | **NEW** | Timestamp of last submission |
| `revisionNumber` | int | **NEW** | Starts at 0. Informational — tracks edit-after-submit cycles. Server-managed via trigger. |

Status flow: `draft` → `submitted` → (undo) → `draft` → `submitted` (revision increments server-side).

### Files referencing `EntryStatus.complete` (must all be updated):

**Lib (12 files):**
- `lib/features/entries/data/models/daily_entry.dart` — enum definition
- `lib/features/entries/presentation/screens/entry_editor_screen.dart` — `_submitEntry()` method
- `lib/features/entries/presentation/widgets/status_badge.dart` — 3 switch cases
- `lib/features/entries/presentation/widgets/entry_action_bar.dart` — switch case
- `lib/features/entries/presentation/providers/daily_entry_provider.dart` — `completeEntries` getter, `markComplete()` method
- `lib/features/entries/data/repositories/daily_entry_repository.dart` — `markComplete()` method
- `lib/features/entries/data/datasources/local/daily_entry_local_datasource.dart` — doc comment
- `lib/core/database/seed_data_service.dart` — hardcoded `'status': 'complete'`
- Additional files found during implementation (grep for `complete` in entries feature)

**Test (7+ files):**
- `daily_entry_repository_test.dart`, `pdf_service_test.dart`, `daily_entry_test.dart`, `daily_entry_provider_test.dart`, `entry_editor_screen_test.dart`, `mock_providers.dart`, `entry_editor_report_test.dart`

### New Entity: `AppConfig` (Supabase-only, not synced to SQLite)

| Field | Type | Description |
|-------|------|-------------|
| key | String | Primary key (whitelisted: `min_version`, `force_update`, `reauth_before`, `reauth_reason`) |
| value | String | The config value |
| updated_at | DateTime | Auto-updated via trigger |

Fetched at startup and on foreground resume (if cache > 5 min stale). Cached locally with timestamp.

### New Local State: Security Tracking

| Storage | Key | Type | Description |
|---------|-----|------|-------------|
| `flutter_secure_storage` | `last_active_at` | ISO8601 string | Updated on foreground. If >7 days stale → sign out. |
| `flutter_secure_storage` | `last_config_check_at` | ISO8601 string | Updated on successful `app_config` fetch. If >24h stale → require connectivity or block. |

Using `flutter_secure_storage` (Android Keystore / iOS Keychain) instead of SharedPreferences to prevent tampering on rooted devices.

### Database Migrations

**SQLite** — bump to **version 26**:
```dart
if (oldVersion < 26) {
  // 1. Add new columns
  await _addColumnIfNotExists(db, 'daily_entries', 'submitted_at', 'TEXT');
  await _addColumnIfNotExists(db, 'daily_entries', 'revision_number', 'INTEGER NOT NULL DEFAULT 0');

  // 2. Migrate 'complete' status to 'submitted'
  await db.execute("UPDATE daily_entries SET status = 'submitted' WHERE status = 'complete'");

  // 3. Rebuild daily_entries to make location_id nullable
  await db.execute('''
    CREATE TABLE daily_entries_new (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      location_id TEXT REFERENCES locations(id) ON DELETE CASCADE,  -- NOW NULLABLE
      date TEXT NOT NULL,
      weather TEXT,
      temp_low REAL,
      temp_high REAL,
      activities TEXT,
      site_safety TEXT,
      sesc_measures TEXT,
      traffic_control TEXT,
      visitors TEXT,
      extras_overruns TEXT,
      signature TEXT,
      status TEXT NOT NULL DEFAULT 'draft',
      submitted_at TEXT,
      revision_number INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now')),
      sync_status TEXT NOT NULL DEFAULT 'pending',
      last_synced_at TEXT,
      is_deleted INTEGER NOT NULL DEFAULT 0
    )
  ''');
  await db.execute('INSERT INTO daily_entries_new SELECT *, NULL, 0 FROM daily_entries');
  // NOTE: actual column mapping must match both old and new schema exactly.
  // Implementation agent must verify column order against actual schema.
  await db.execute('DROP TABLE daily_entries');
  await db.execute('ALTER TABLE daily_entries_new RENAME TO daily_entries');
  // Recreate indexes
  await db.execute('CREATE INDEX IF NOT EXISTS idx_daily_entries_project ON daily_entries(project_id)');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_daily_entries_date ON daily_entries(date)');
  await db.execute('CREATE INDEX IF NOT EXISTS idx_daily_entries_sync ON daily_entries(sync_status)');
}
```

**IMPORTANT**: The table rebuild `INSERT INTO ... SELECT` must be verified against the actual schema columns at implementation time. The columns above are approximate — the implementing agent must read `entry_tables.dart` to get exact column names and order.

**Supabase** — migration file: `supabase/migrations/20260303000000_app_config_and_entry_status.sql`:
```sql
-- 1. app_config table
CREATE TABLE IF NOT EXISTS app_config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT valid_key CHECK (key IN ('min_version', 'force_update', 'reauth_before', 'reauth_reason')),
  CONSTRAINT valid_bool CHECK (key != 'force_update' OR value IN ('true', 'false')),
  CONSTRAINT valid_semver CHECK (key != 'min_version' OR value ~ '^\d+\.\d+\.\d+$')
);

-- RLS: read-only for authenticated users. Writes blocked by default-deny (no INSERT/UPDATE/DELETE policies).
ALTER TABLE app_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated users can read config"
  ON app_config FOR SELECT
  TO authenticated USING (true);
-- NOTE: No write policies. RLS default-deny blocks all client writes.
-- Config changes must be made via SQL console or service_role only.

-- Auto-update updated_at on modification
CREATE OR REPLACE FUNCTION update_app_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER app_config_updated_at
  BEFORE UPDATE ON app_config FOR EACH ROW
  EXECUTE FUNCTION update_app_config_timestamp();

-- Seed initial values
INSERT INTO app_config (key, value) VALUES
  ('min_version', '0.75.0'),
  ('force_update', 'false'),
  ('reauth_before', '2000-01-01T00:00:00Z'),  -- expired = no reauth required
  ('reauth_reason', '');

-- 2. daily_entries schema changes
ALTER TABLE daily_entries ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ;
ALTER TABLE daily_entries ADD COLUMN IF NOT EXISTS revision_number INTEGER NOT NULL DEFAULT 0;
ALTER TABLE daily_entries ALTER COLUMN location_id DROP NOT NULL;

-- Migrate existing 'complete' status to 'submitted'
UPDATE daily_entries SET status = 'submitted' WHERE status = 'complete';

-- 3. Server-side status transition validation
CREATE OR REPLACE FUNCTION validate_entry_status_transition()
RETURNS TRIGGER AS $$
BEGIN
  -- Auto-increment revision on submitted -> draft (undo)
  IF OLD.status = 'submitted' AND NEW.status = 'draft' THEN
    NEW.revision_number := OLD.revision_number + 1;
  END IF;
  -- Prevent submitted_at backdating
  IF NEW.status = 'submitted' AND OLD.submitted_at IS NOT NULL
     AND NEW.submitted_at < OLD.submitted_at THEN
    RAISE EXCEPTION 'Cannot backdate submission timestamp';
  END IF;
  -- Enforce revision_number monotonicity
  IF NEW.revision_number < OLD.revision_number THEN
    NEW.revision_number := OLD.revision_number;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER entry_status_transition
  BEFORE UPDATE ON daily_entries FOR EACH ROW
  EXECUTE FUNCTION validate_entry_status_transition();
```

### Sync Considerations
- `submitted_at` and `revision_number` sync bidirectionally. `revision_number` is server-managed via trigger — client-provided values are clamped to at least the current server value.
- `app_config` is server → client only (read-only from app).
- `last_active_at` and `last_config_check_at` are local-only (`flutter_secure_storage`), never synced.
- **Revision number is informational** — it does NOT affect sync conflict resolution. Last-write-wins by `updated_at` remains the sync strategy. This is a known limitation documented here.

---

## User Flows

### Entry Creation (Updated)

```
Calendar/Dashboard
      │
      ├── Tap date ──> Entry Editor
      │                    │
      │              Check GPS permission (already granted?)
      │              ├── Yes → auto-fetch weather silently
      │              └── No → show "Fetch Weather" button (no prompt in initState)
      │              Location: optional dropdown + [+ Add Location]
      │              Activities, Safety, etc.
      │                    │
      │              [Save Draft] only (no submit button)
      │                    │
      │              Back to calendar
```

Entry editor becomes **draft-only**. Submit button and `_submitEntry()` method removed entirely.
Weather auto-fetch only triggers if GPS permission already granted. If not, shows a button (avoids surprise permission prompt).

### Review & Submit Flow

```
Dashboard
   │
   └── "Review Drafts" card (shows count: "5 drafts to review")
          │
          v
   Drafts List Screen
   ┌──────────────────────────────────────┐
   │ ☐ Mon 2/24 - Bridge Deck      DRAFT │
   │ ☐ Tue 2/25 - Retaining Wall   DRAFT │
   │ ☐ Wed 2/26 - Bridge Deck      DRAFT │
   │ ☐ Thu 2/27 - Abutment #2      DRAFT │
   │ ☐ Fri 2/28 - Bridge Deck      DRAFT │
   │                                      │
   │ [Select All]    [Review Selected (0)]│
   └──────────────────────────────────────┘
          │
          Select entries, tap [Review Selected]
          │
          v
   Review Screen (Entry 1 of 3)
   ┌──────────────────────────────────────┐
   │ ◄ 1/3                    [Skip]      │
   │──────────────────────────────────────│
   │ Mon 2/24 - Bridge Deck              │
   │                                      │
   │ Location: Station 125+00     [edit]  │
   │ Weather:  Sunny 72°F/45°F   [edit]  │
   │ Activities: Poured deck...  [edit]   │
   │ Safety: Hard hats, vest...  [edit]   │
   │                                      │
   │ ⚠ Missing: SESC Measures             │
   │                                      │
   │           [Mark Ready]               │
   └──────────────────────────────────────┘
          │
          After reviewing all selected...
          │
          v
   Summary Screen
   ┌──────────────────────────────────────┐
   │ Review Complete                      │
   │                                      │
   │ ✓ Mon 2/24 - Bridge Deck     READY  │
   │ ✓ Tue 2/25 - Retaining Wall  READY  │
   │ ─ Wed 2/26 - Bridge Deck    SKIPPED │
   │                                      │
   │ [Submit 2 Entries]                   │
   └──────────────────────────────────────┘
          │
          Confirmation dialog: "Submit 2 entries?"
          │
          v
   Back to Drafts List (submitted entries gone,
   skipped entries still show)
```

### Undo Submission

```
Calendar ──> tap submitted entry ──> Entry Editor (read-only badge)
   │
   │  Banner: "Submitted on Mar 3 · Revision #1"
   │  [Undo Submission]
   │        │
   │   Confirmation: "Revert to draft? You can re-submit later."
   │        │
   │   Status → draft (revision increments server-side on next sync)
   │   Entry becomes editable, shows in drafts list again
```

### Startup Gate (Auth & Version)

```
App Launch
   │
   ├── Check last_active_at in flutter_secure_storage
   │   └── > 7 days? ──> Sign out ──> /login
   │
   ├── Authenticated? ──> No ──> /login
   │
   ├── Fetch app_config from Supabase (best-effort, 5s timeout)
   │   │
   │   ├── Success → update last_config_check_at
   │   │   ├── reauth_before > now()? ──> Sign out ──> /login (show reason)
   │   │   ├── app version < min_version?
   │   │   │   ├── force_update = true ──> /update-required (blocking)
   │   │   │   └── force_update = false ──> dismissable banner
   │   │   └── All clear → proceed
   │   │
   │   └── Fetch fails (offline)?
   │       ├── last_config_check_at > 24h stale? ──> Show warning banner
   │       │   "Last server check was X days ago. Connect to verify."
   │       │   (does NOT block — but informs user)
   │       └── last_config_check_at < 24h? ──> Skip, proceed normally
   │
   ├── Router checks profile/company as usual
   │   (version/reauth gate AFTER auth check, BEFORE profile routing)
   │
   └── Dashboard
```

**`reauth_before` replaces `force_reauth` boolean.** When admin sets `reauth_before` to a future timestamp (e.g., `2026-03-10T00:00:00Z`), all users who launch the app before that date are signed out. After the date passes, the check naturally stops firing — no manual reset needed. No lockout loop.

### Also check on foreground resume

```
App resumes from background
   │
   ├── Update last_active_at
   │
   └── If last_config_check_at > 5 minutes stale + online
       └── Re-fetch app_config (non-blocking, background)
           └── If reauth_before/version changed → apply on next navigation
```

### Post-Reset Flow (BUG-1 Fix)

```
Settings ──> Sign Out
   │
   Clear auth session (Supabase SDK)
   Clear all 22 SQLite tables
   Clear SharedPreferences (last_project, recent_projects, inspector keys)
   Clear flutter_secure_storage (last_active_at, last_config_check_at)
   │
   └──> /login (clean slate)
```

---

## UI Components

### New Screens

| Screen | Location | Purpose |
|--------|----------|---------|
| `DraftsListScreen` | `lib/features/entries/presentation/screens/` | Multi-select list of draft entries with [Review Selected] |
| `EntryReviewScreen` | `lib/features/entries/presentation/screens/` | Read-only summary with inline edit, [Mark Ready] / [Skip] |
| `ReviewSummaryScreen` | `lib/features/entries/presentation/screens/` | Ready vs skipped tally, [Submit X Entries] |
| `UpdateRequiredScreen` | `lib/features/auth/presentation/screens/` | Blocking screen when app version < min_version with force_update |

### New Widgets

| Widget | Location | Purpose |
|--------|----------|---------|
| `DraftEntryTile` | `lib/features/entries/presentation/widgets/` | Checkbox + date + location + status badge for drafts list |
| `ReviewFieldRow` | `lib/features/entries/presentation/widgets/` | Read-only field display with inline [edit] tap target |
| `ReviewMissingWarning` | `lib/features/entries/presentation/widgets/` | Warning chip for missing required fields |
| `SubmittedBanner` | `lib/features/entries/presentation/widgets/` | "Submitted on Mar 3 · Revision #1" banner with [Undo Submission] |
| `VersionBanner` | `lib/shared/widgets/` | Dismissable banner for soft update nudge |
| `StaleConfigWarning` | `lib/shared/widgets/` | "Last server check was X days ago" warning banner |

### Modified Screens

| Screen | Change |
|--------|--------|
| `EntryEditorScreen` | Remove submit button + `_submitEntry()` method. Draft-only. Add `SubmittedBanner` with undo when viewing submitted entry. |
| `HomeScreen` / Dashboard | Add "Review Drafts" card with draft count |
| `EntryBasicsSection` | Location optional + [+ Add Location] inline. Weather auto-fetches on create (permission-gated). |
| `SettingsScreen` | Version tile reads real version via `package_info_plus` |

### Layout: Drafts List Screen

```
┌──────────────────────────────────┐
│ ← Review Drafts                  │
│──────────────────────────────────│
│ Project: Springfield DWSRF       │
│ 5 drafts · Feb 24 – Feb 28      │
│──────────────────────────────────│
│ ☐ Mon 2/24                       │
│   Bridge Deck · Sunny 72°F      │
│   ✓ Activities  ⚠ No SESC       │
│                                  │
│ ☐ Tue 2/25                       │
│   Retaining Wall · Cloudy 58°F  │
│   ✓ All fields complete          │
│                                  │
│ ☐ Wed 2/26                       │
│   Bridge Deck · Rainy 51°F      │
│   ⚠ No location                 │
│──────────────────────────────────│
│ [Select All]  [Review Selected 0]│
└──────────────────────────────────┘
```

### Layout: Review Screen

```
┌──────────────────────────────────┐
│ ← 1/3              [Skip ▸]     │
│──────────────────────────────────│
│ Monday, February 24, 2026       │
│ Bridge Deck Rd · Station 125+00 │
│──────────────────────────────────│
│                                  │
│ LOCATION          Station 125+00│
│                          [edit] │
│ WEATHER              Sunny 72°F │
│                          [edit] │
│ TEMP              72°F / 45°F   │
│                          [edit] │
│ ACTIVITIES                      │
│ Poured deck section 3, set     │
│ forms for section 4...          │
│                          [edit] │
│ SITE SAFETY                     │
│ Hard hats, vests required...    │
│                          [edit] │
│ SESC MEASURES                   │
│ ⚠ Not filled in         [add]  │
│                                  │
│──────────────────────────────────│
│        [Mark Ready]              │
└──────────────────────────────────┘
```

### TestingKeys Required
- `TestingKeys.draftsListScreen`, `TestingKeys.reviewScreen`, `TestingKeys.reviewSummaryScreen`
- `TestingKeys.draftEntryTile`, `TestingKeys.reviewFieldRow`, `TestingKeys.markReadyButton`
- `TestingKeys.submitBatchButton`, `TestingKeys.undoSubmissionButton`
- `TestingKeys.updateRequiredScreen`, `TestingKeys.versionBanner`

---

## State Management

### Modified Provider: `EntryProvider`

**New methods:**
```dart
Future<List<DailyEntry>> getDraftEntries(String projectId);
Future<void> batchSubmit(List<String> entryIds);  // SQLite transaction, single timestamp
Future<void> undoSubmission(String entryId);       // status=draft, revision increments server-side
```

`batchSubmit` wraps all status changes in a **SQLite transaction** with a **single batch timestamp**:
```dart
await db.transaction((txn) async {
  final batchTimestamp = DateTime.now().toUtc();
  for (final id in entryIds) {
    await txn.update('daily_entries', {
      'status': 'submitted',
      'submitted_at': batchTimestamp.toIso8601String(),
      'sync_status': 'pending',
      'updated_at': batchTimestamp.toIso8601String(),
    }, where: 'id = ?', whereArgs: [id]);
  }
});
```

All-or-nothing. No partial failure states.

`markReady` is ephemeral — held in review screen's local state (`Set<String>`), not persisted.

### New Provider: `AppConfigProvider`

```dart
Future<void> checkConfig();           // called at startup + foreground resume (if stale)
bool get requiresUpdate;              // app version < min_version && force_update
bool get requiresReauth;              // reauth_before > now()
bool get hasUpdateAvailable;          // app version < min_version && !force_update
bool get isConfigStale;               // last_config_check_at > 24h
String? get updateMessage;
String? get reauthReason;
```

Version comparison uses `pub_semver` package with try-catch:
```dart
bool isVersionBelowMinimum(String appVersion, String minVersion) {
  try {
    return Version.parse(appVersion) < Version.parse(minVersion);
  } catch (e) {
    debugPrint('Version parse error: $e');
    return false; // Fail open — do not block users on bad config
  }
}
```

### Modified Provider: `AuthProvider`

**New methods:**
```dart
void updateLastActive();               // called on AppLifecycleState.resumed
Future<bool> checkInactivityTimeout(); // > 7 days → sign out, return true
Future<void> handleForceReauth(String? reason);
```

`updateLastActive()` writes to `flutter_secure_storage` on foreground resume.

### Data Flow

```
Startup:
  main.dart → AuthProvider.checkInactivityTimeout()
            → AppConfigProvider.checkConfig()
            → Router evaluates: timeout? reauth? version block?
            → Proceed or redirect

Foreground resume:
  AuthProvider.updateLastActive()
  AppConfigProvider.checkConfig() if > 5 min stale

Review Flow:
  DraftsListScreen → EntryProvider.getDraftEntries(projectId)
  ReviewScreen → local Set<String> readyIds (ephemeral)
  ReviewSummaryScreen → EntryProvider.batchSubmit(readyIds.toList())

Undo:
  EntryEditorScreen → EntryProvider.undoSubmission(entryId)

Weather Auto-Fetch:
  EntryEditorScreen.initState() → check GPS permission status
    → already granted? → WeatherService.fetchWeatherForCurrentLocation(date)
    → not granted? → show "Fetch Weather" button (user taps → request permission → fetch)
```

### Error Handling

| Scenario | Handling | UI Feedback |
|----------|----------|-------------|
| Weather fetch fails | Fields stay blank | User fills manually, no error |
| Batch submit fails | Transaction rolls back entirely | Snackbar: "Submit failed, please try again" |
| app_config fetch fails (offline) | Use cached values, check staleness | Warning banner if > 24h stale |
| Undo fails | Entry stays submitted | Snackbar with retry |
| Inactivity timeout | Silent sign-out | Login screen, "Please sign in" |
| Version parse error | Fail open (do not block) | Log warning, proceed normally |

---

## Offline Behavior

### Capabilities

| Action | Offline? | Notes |
|--------|----------|-------|
| Create draft entry | Yes | SQLite, syncs later |
| Weather auto-fetch | No | Needs GPS + API. Fields stay blank. |
| Add location inline | Yes | SQLite, syncs later |
| View/review drafts | Yes | All local SQLite |
| Mark ready | Yes | Ephemeral local state |
| Batch submit | Yes | Local status change (transaction), syncs later |
| Undo submission | Yes | Local status revert, syncs later. Revision increments server-side on sync. |
| Startup version check | No | Skipped gracefully offline. Warning banner if config > 24h stale. |
| Startup reauth check | No | Skipped gracefully offline. Same staleness warning. |
| Inactivity timeout | Yes | flutter_secure_storage only |

**Key principle**: Entire review-and-submit flow works fully offline.

### Known Limitations (from adversarial review)

**Offline bypass of reauth**: A user who stays offline and keeps using the app daily bypasses both the `reauth_before` check and the inactivity timeout. Mitigations:
1. Supabase refresh token lifetime set to 7 days (server-side enforcement)
2. `last_config_check_at` staleness warning after 24h
3. For emergency revocation (compromised credentials): use Supabase `auth.admin.deleteUser()` or set `banned_until` — this invalidates the JWT server-side immediately

**Revision numbers are informational**: In multi-device scenarios, `revision_number` can appear inconsistent due to last-write-wins sync. The server trigger prevents the number from going backwards, but it does not resolve device-A vs device-B conflicts. This is a documented limitation.

---

## Edge Cases

| Scenario | Handling | UI Feedback |
|----------|----------|-------------|
| No drafts to review | Empty state | "All caught up! No drafts to review." |
| Entry missing location at submit | Blocked from [Mark Ready] | Warning: "Location required" with [Add Location] |
| All entries skipped | Summary shows 0 ready | [Submit] disabled, "No entries marked ready" |
| Submit while another device edits | Last-write-wins on sync | No special handling |
| App killed mid-review | readyIds are ephemeral | Re-enter review, start fresh. Drafts untouched. |
| app_config table doesn't exist | Fetch returns error | All flags permissive, startup proceeds |
| Malformed min_version in app_config | `pub_semver` parse fails | Fail open (no block), log warning |
| Weather for past dates (>16 days) | Open-Meteo may not have data | Fields stay blank |
| Rapid undo-then-submit | Each action is full SQLite write | Transaction ensures consistency |
| Unknown status in SQLite (e.g., stale 'complete') | `fromMap` fallback | Deserialize as `EntryStatus.draft` |

### Boundaries
- Max entries in review session: No hard limit (list scrolls)
- Revision number: Unbounded integer, server-enforced monotonic
- Inactivity timer: Checked at startup only, not background timer
- app_config fetch timeout: 5 seconds
- app_config cache staleness: re-fetch after 5 minutes on foreground resume

### Permission Edge Cases
- RLS on app_config: Read-only for all authenticated users. Write blocked by RLS default-deny. Key whitelist via CHECK constraint.
- Entry submission by non-owner: Current RLS allows project members to edit any entry. Submission follows same rule. Owner-only submission is a future RLS change.
- Status transition validation: Server trigger prevents backdating `submitted_at` and enforces monotonic `revision_number`.

---

## Implementation Phases

### Phase 0: Prerequisites
**Scope**: Address pre-existing security issues and add dependencies.

**Tasks**:
0.1. Remove hardcoded `defaultValue` fallbacks from `lib/core/config/supabase_config.dart` for Supabase URL and anon key. Require `--dart-define` for all builds.
0.2. Add `package_info_plus` dependency to `pubspec.yaml`. Verify it returns correct version on both Android and Windows. Update `windows/runner/Runner.rc` if needed.
0.3. Add `pub_semver` dependency to `pubspec.yaml` (for version comparison).
0.4. Configure Supabase refresh token lifetime to 7 days in Supabase Dashboard → Auth → Settings.
0.5. Reduce GPS coordinate precision in `WeatherService` debug logs: guard with `!kReleaseMode`, reduce to 2 decimal places for API calls.

**Agents**: `backend-supabase-agent` (0.4), `backend-data-layer-agent` (0.1–0.3), `frontend-flutter-specialist-agent` (0.5)

**Verify**: `flutter analyze` clean. `package_info_plus` returns `0.75.0` on Windows. Supabase refresh token lifetime confirmed at 7 days. Weather service debug logs guarded.

### Phase 1: Data Model + Auth Infrastructure
**Scope**: Foundation. Migrations, providers, startup gate.

**Tasks**:
1.1. **SQLite migration** (version 26): Add `submitted_at`, `revision_number` columns. Rebuild `daily_entries` table to make `location_id` nullable. Migrate `complete` → `submitted` status. See exact SQL in Data Model section.
1.2. **Supabase migration** (`20260303000000_app_config_and_entry_status.sql`): `app_config` table with RLS + CHECK constraints + `updated_at` trigger. `daily_entries` columns + `location_id` DROP NOT NULL + status migration + status transition trigger. See exact SQL in Data Model section.
1.3. **Update `DailyEntry` model**: `locationId` from `String` to `String?`. Add `submittedAt` (DateTime?), `revisionNumber` (int, default 0). Remove `EntryStatus.complete` from enum.
1.4. **Defensive deserialization** in `DailyEntry.fromMap`: fallback for unknown status values:
    ```dart
    status: EntryStatus.values.asNameMap()[map['status'] as String] ?? EntryStatus.draft,
    ```
1.5. **Update `toMap`/`fromMap`/`copyWith`** for new fields and nullable `locationId`.
1.6. **Update sync adapter** column mappings for `submitted_at`, `revision_number`, nullable `location_id`.
1.7. **Update ALL `EntryStatus.complete` references** (35+ files — see enumerated list in Data Model section):
    - Remove `completeEntries` getter and `markComplete()` from provider + repository
    - Update switch cases in `status_badge.dart`, `entry_action_bar.dart`
    - Update seed data in `seed_data_service.dart`
    - Update all test files
1.8. **Create `AppConfigProvider`**: fetch `app_config`, cache with timestamp, `pub_semver` comparison with try-catch fail-open, expose `requiresUpdate`, `requiresReauth`, `isConfigStale`.
1.9. **`AuthProvider` additions**: `updateLastActive()`, `checkInactivityTimeout()`, `handleForceReauth()`. Use `flutter_secure_storage` for `last_active_at` and `last_config_check_at`. Clear both on sign-out.
1.10. **Wire startup gate** in `main.dart`: inactivity check → app_config fetch → router evaluation. Position in router redirect chain: after auth check, before profile routing. Add `/update-required` to exempt route set.
1.11. **Create `UpdateRequiredScreen`** (blocking, shows version + message + update instructions).
1.12. **Fix `SettingsScreen`** version tile: read from `PackageInfo.fromPlatform()` instead of hardcoded "1.0.0".
1.13. **Foreground resume hook**: in `WidgetsBindingObserver`, call `updateLastActive()` + conditionally re-fetch `app_config` if cache > 5 min stale.

**Agents**: `backend-data-layer-agent` (1.1, 1.3–1.7), `backend-supabase-agent` (1.2), `auth-agent` (1.8–1.10, 1.13), `frontend-flutter-specialist-agent` (1.11–1.12)

**Verify**:
- [ ] `flutter analyze` clean
- [ ] `flutter test` — all tests pass (with updated `complete` → `submitted` references)
- [ ] Manual: set `reauth_before` to future in Supabase → app signs out on next launch
- [ ] Manual: set `last_active_at` to 8 days ago → app signs out
- [ ] Manual: set `min_version` above current + `force_update: true` → UpdateRequiredScreen
- [ ] Manual: malformed `min_version` → app proceeds (fail-open)
- [ ] Settings shows real version from `package_info_plus`
- [ ] Entries save with `locationId = null` (draft)

### Phase 2: Entry Creation Bug Fixes
**Scope**: Fix BUG-1, BUG-2, BUG-3. No new screens.

**Tasks**:
2.1. **BUG-2 (Weather)**: In `EntryEditorScreen`, check GPS permission status on create mode init. If already granted → auto-fetch via `WeatherService.fetchWeatherForCurrentLocation(date)` and pre-fill fields. If not granted → show "Fetch Weather" button that requests permission then fetches. Replace no-op `onAutoFetchWeather` callback.
2.2. **BUG-3 (Location)**: Update `_persistCreateEntry()` to allow `locationId = null` for draft saves. Add [+ Add Location] inline create in `EntryBasicsSection` (opens a quick-add bottom sheet or inline fields). Location required check applies only in review flow's [Mark Ready].
2.3. **BUG-1 (Routing)**: Verify sign-out clears auth session fully. Add `last_active_at` and `last_config_check_at` to sign-out cleanup. Test reset → `/login` → sign in → profile-setup/company-setup/dashboard path.
2.4. **Remove submit from editor**: Delete `_submitEntry()` method and submit button from `EntryEditorScreen`. Remove any reference to `EntryStatus.complete` in this file (should be done in 1.7 but verify).
2.5. **Add `SubmittedBanner`** widget to `EntryEditorScreen` — shown when viewing a submitted entry (read-only badge with date + revision + [Undo Submission]).

**Agents**: `frontend-flutter-specialist-agent` (2.1–2.2, 2.4–2.5), `auth-agent` (2.3)

**Verify**:
- [ ] New entry auto-fetches weather (if GPS permission granted)
- [ ] New entry shows "Fetch Weather" button if GPS not yet granted
- [ ] Entry saves as draft without location
- [ ] [+ Add Location] creates location inline
- [ ] Sign out → /login with clean state (all secure storage cleared)
- [ ] Re-sign-in → correct routing
- [ ] No submit button in entry editor
- [ ] Submitted entry shows SubmittedBanner

### Phase 3: Review & Submit Flow
**Scope**: New screens and workflow.

**Tasks**:
3.1. `EntryProvider` new methods: `getDraftEntries(projectId)`, `batchSubmit(entryIds)` (SQLite transaction), `undoSubmission(entryId)`.
3.2. `DraftsListScreen`: project-filtered draft list, checkboxes, [Select All], [Review Selected (N)], completeness hints per tile.
3.3. `DraftEntryTile` widget: checkbox + date + location + weather + completeness indicators.
3.4. `EntryReviewScreen`: progress indicator (1/N), entry summary with `ReviewFieldRow` widgets, inline edit on tap, `ReviewMissingWarning` for required fields, [Mark Ready] / [Skip] buttons.
3.5. `ReviewFieldRow` widget: label + value + [edit] tap target. Expands to inline input on tap.
3.6. `ReviewSummaryScreen`: ready/skipped tally, [Submit X Entries] with confirmation dialog.
3.7. Register routes: `/drafts/:projectId`, `/review`, `/review-summary` in `app_router.dart`.
3.8. Dashboard "Review Drafts" card on `HomeScreen` / `ProjectDashboardScreen` showing draft count.

**Agents**: `frontend-flutter-specialist-agent` (3.2–3.6, 3.8), `backend-data-layer-agent` (3.1), `frontend-flutter-specialist-agent` (3.7)

**Verify**:
- [ ] Dashboard shows "Review Drafts" card with count
- [ ] Drafts list shows only draft entries for current project
- [ ] Multi-select works, [Review Selected] starts review
- [ ] Review screen shows entry summary with inline edit
- [ ] Missing required fields show warnings
- [ ] [Mark Ready] / [Skip] advance to next entry
- [ ] Summary shows ready/skipped tally
- [ ] [Submit N Entries] changes status to `submitted` with `submittedAt` (single timestamp)
- [ ] Submitted entries no longer appear in drafts list
- [ ] Transaction: if 1 entry fails, none are submitted (all-or-nothing)

### Phase 4: Polish & Submitted Entry UX
**Scope**: Post-submit experience + polish.

**Tasks**:
4.1. Wire [Undo Submission] in `SubmittedBanner` → `EntryProvider.undoSubmission()` with confirmation dialog.
4.2. Calendar/list visual distinction for submitted vs draft entries (color/icon badge).
4.3. `VersionBanner` widget: dismissable soft-update nudge when `hasUpdateAvailable` but not `requiresUpdate`.
4.4. `StaleConfigWarning` widget: shown when `isConfigStale` (>24h since last server check).
4.5. Wire `VersionBanner` and `StaleConfigWarning` into app shell.
4.6. Empty state for drafts list: "All caught up!" illustration.
4.7. Add all `TestingKeys` for new widgets and screens.

**Agents**: `frontend-flutter-specialist-agent` (all tasks)

**Verify**:
- [ ] [Undo Submission] reverts to draft with confirmation
- [ ] Re-submit after undo: `revisionNumber` increments (verify server-side trigger)
- [ ] Calendar shows visual distinction for submitted entries
- [ ] Version banner shows when soft update available, dismisses correctly
- [ ] Stale config warning shows after 24h offline
- [ ] All TestingKeys registered
- [ ] Full regression: `flutter test` green
