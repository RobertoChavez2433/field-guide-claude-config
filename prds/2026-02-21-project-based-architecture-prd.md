# PRD: Project-Based Multi-Tenant Architecture

**Status**: APPROVED — Ready for Implementation
**Created**: 2026-02-21
**Author**: Roberto Chavez + Claude (brainstorming session 425)
**Priority**: High — Fundamental architectural shift

---

## 1. Problem Statement

### Current State
The Field Guide App is currently **inspector-centric** — all data lives on the individual inspector's device and Supabase account. There is:
- No concept of who owns or can access a project
- No user roles beyond email/ID authentication
- No company or team structure
- No data attribution (who recorded what)
- No mechanism to share project data between users
- No sync guarantees to protect against data loss

### Business Problems This Creates
1. **Engineer blindness** — The construction engineer (boss) cannot log in and view project progress. They have no visibility into field data until the inspector manually generates and sends a PDF report.
2. **Inspector handoff failure** — When an inspector is absent (sick, vacation, reassigned), a covering inspector cannot access the project's existing data. They start blind.
3. **Data loss risk** — If an inspector leaves the company (especially on bad terms), any un-synced data on their device is lost forever.
4. **Scale blocker** — When the app launches to other companies, there is no mechanism to isolate company A's data from company B's data.

### Target State
A **project-centric, multi-tenant** architecture where:
- Data is organized under **projects**, which belong to **companies**
- Multiple users in the same company see all company projects
- Any authorized user can contribute to any project
- Every piece of data tracks who created it
- Sync guarantees ensure data reaches the server within hours, not days

---

## 2. Decisions Made (Brainstorming Session)

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Engineer role = Full access | Engineers need to see AND interact with data, not just view. Same capabilities as inspectors, different role label. |
| 2 | Access model = Company/team-based | Single-company now, but `company_id` scoping makes it multi-tenant ready. Everyone in a company sees all projects. |
| 3 | Project number uniqueness | Validate against existing project numbers within the company on create. Prevents duplicates. |
| 4 | Onboarding = Admin approves | New users request to join a company. Admin approves/denies. Controls who sees company data. |
| 5 | Four roles: Admin, Engineer, Inspector, Viewer | Admin manages company. Engineer + Inspector have full data access (role shows on PDFs). Viewer is read-only for stakeholders. |
| 6 | Audit trail = Track + display author | Every record stores `created_by_user_id`. Displayed in UI ("Recorded by: John D. on 2/21"). |
| 7 | Sync model = Additive-only | Users ADD new records; they don't edit each other's records. Sync merges additions. No conflict resolution needed. |
| 8 | User profile = Progressive | Signup = email + password only. Profile fields (name, cert, phone) are optional, filled in later. Replaces PreferencesService. |
| 9 | Post-login = Remember last project | Auto-open last project on launch. Project switcher in app bar. Falls back to project list if no last project. |
| 10 | 4-layer sync guarantee | Sync-on-save + Firebase silent push (daily) + sync-on-app-open + admin visibility of sync status. |
| 11 | Admin dashboard | Approve users, manage roles, view sync status, deactivate accounts. |

---

## 3. Current Architecture Analysis

### What Already Works (No Changes Needed)
- **Data is project-centric**: All child tables (`daily_entries`, `photos`, `bid_items`, `quantities`) already reference `project_id`
- **Project selection routes**: Routes use `projectId` path parameter — no implicit scoping to untangle
- **Supabase Auth**: Email + password authentication already works

### What's Missing (Must Be Built)

| Gap | Impact | Solution |
|-----|--------|----------|
| No `company_id` on any table | Can't scope data by company | Add `company_id` FK to `projects` table; child tables inherit via project |
| No `user_id` / `created_by` on data | Can't track who recorded data | Add `created_by_user_id` FK to all data tables |
| No user profile model | Only have email + UUID from Supabase Auth | Create `user_profiles` table with name, role, cert, phone |
| No roles / permissions | Everyone is the same | Add `role` field to user_profiles, enforce in RLS + app code |
| No RLS policies | Sync pulls ALL data for ALL companies | Write RLS policies scoped by `company_id` |
| No company model | No way to group users | Create `companies` table |
| `getAll()` returns everything | All projects visible to all users | Filter by `company_id` in repositories |
| No sync guarantees | Data stuck on device indefinitely | 4-layer sync: on-save + FCM push + on-open + admin visibility |

### Key Files to Modify

| File | Current State | Changes Needed |
|------|--------------|----------------|
| `lib/features/auth/services/auth_service.dart` | Wraps Supabase auth (signup, signin, signout) | Add profile loading, company checking |
| `lib/features/auth/presentation/providers/auth_provider.dart` | Holds `_currentUser` (User?) | Add `_userProfile` (UserProfile?), role checks |
| `lib/features/projects/data/models/project.dart` | 17 fields, no `company_id` or `created_by` | Add `companyId`, `createdByUserId` |
| `lib/features/projects/presentation/providers/project_provider.dart` | `loadProjects()` returns ALL | Filter by `companyId` |
| `lib/features/projects/data/repositories/project_repository.dart` | `getAll()` has no filtering | Add `getByCompanyId()` |
| `lib/core/database/schema/core_tables.dart` | Schema v23, no company/user columns | Add columns, bump to v24 |
| `lib/core/database/database_service.dart` | Manages SQLite migrations | Add v23→v24 migration |
| `lib/features/sync/data/adapters/supabase_sync_adapter.dart` | No company filtering, no user attribution | Filter by company_id, include created_by |
| `lib/features/entries/data/models/daily_entry.dart` | No `created_by_user_id` | Add `createdByUserId`, `updatedByUserId` |
| `lib/features/photos/data/models/photo.dart` | No `created_by_user_id` | Add `createdByUserId` |
| `lib/core/router/app_router.dart` | Auth → Dashboard flow | Auth → Profile Setup → Company → Dashboard flow |

---

## 4. Data Model

### 4.1 New Tables

#### `companies`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Company identifier |
| `name` | TEXT | NOT NULL, UNIQUE | Company display name (e.g., "CTT Engineering") |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

#### `user_profiles`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK, FK → auth.users.id | 1:1 with Supabase auth user |
| `company_id` | UUID | FK → companies.id, NULLABLE | Null until approved. Set on approval. |
| `role` | TEXT | NOT NULL, DEFAULT 'inspector' | 'admin' \| 'engineer' \| 'inspector' \| 'viewer' |
| `status` | TEXT | NOT NULL, DEFAULT 'pending' | 'pending' \| 'approved' \| 'rejected' \| 'deactivated' |
| `display_name` | TEXT | NULLABLE | Full name for UI display and PDFs |
| `cert_number` | TEXT | NULLABLE | Inspector certification number |
| `phone` | TEXT | NULLABLE | Contact phone |
| `position` | TEXT | NULLABLE | Job title / position |
| `last_synced_at` | TIMESTAMPTZ | NULLABLE | Updated on each successful sync |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Notes:**
- `id` matches `auth.users.id` — no separate UUID. Created via Supabase trigger on auth.users INSERT.
- `status = 'deactivated'` blocks login without deleting data.
- `last_synced_at` is written by the client on successful sync push. Admin dashboard reads it.

#### `company_join_requests`
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PK | Request identifier |
| `user_id` | UUID | FK → auth.users.id, NOT NULL | Who is requesting |
| `company_id` | UUID | FK → companies.id, NOT NULL | Which company |
| `status` | TEXT | NOT NULL, DEFAULT 'pending' | 'pending' \| 'approved' \| 'rejected' |
| `requested_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `resolved_at` | TIMESTAMPTZ | NULLABLE | When admin acted |
| `resolved_by` | UUID | FK → auth.users.id, NULLABLE | Which admin acted |

### 4.2 Modified Tables

#### `projects` — ADD columns
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `company_id` | UUID | FK → companies.id, NOT NULL | Which company owns this project |
| `created_by_user_id` | UUID | FK → auth.users.id, NULLABLE | Who created this project |

- `company_id` is nullable initially for migration, then made NOT NULL after backfill.
- Unique constraint: `UNIQUE(company_id, project_number)` — project numbers unique within a company.

#### `daily_entries` — ADD columns
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `created_by_user_id` | UUID | FK → auth.users.id, NULLABLE | Who created this entry |
| `updated_by_user_id` | UUID | FK → auth.users.id, NULLABLE | Who last modified |

#### `photos` — ADD column
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `created_by_user_id` | UUID | FK → auth.users.id, NULLABLE | Who uploaded this photo |

#### `bid_items` / `quantities` — ADD column
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `created_by_user_id` | UUID | FK → auth.users.id, NULLABLE | Who recorded this |

### 4.3 RLS Policies (Supabase)

```sql
-- Helper function: get current user's company_id
CREATE OR REPLACE FUNCTION get_my_company_id()
RETURNS UUID AS $$
  SELECT company_id FROM user_profiles WHERE id = auth.uid() AND status = 'approved'
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- Companies: only see your own company
CREATE POLICY "users_see_own_company" ON companies
  FOR SELECT USING (id = get_my_company_id());

-- User profiles: see all members of your company
CREATE POLICY "see_company_members" ON user_profiles
  FOR SELECT USING (company_id = get_my_company_id());

-- User profiles: users can update their own profile
CREATE POLICY "update_own_profile" ON user_profiles
  FOR UPDATE USING (id = auth.uid());

-- Projects: scoped by company
CREATE POLICY "company_projects" ON projects
  FOR ALL USING (company_id = get_my_company_id());

-- Viewer restriction: SELECT only on data tables
CREATE POLICY "viewer_read_only" ON daily_entries
  FOR INSERT WITH CHECK (
    (SELECT role FROM user_profiles WHERE id = auth.uid()) != 'viewer'
  );
-- (Repeat for UPDATE, DELETE, and for photos, bid_items, etc.)

-- Join requests: users can create their own
CREATE POLICY "create_own_request" ON company_join_requests
  FOR INSERT WITH CHECK (user_id = auth.uid());

-- Join requests: admins can update status
CREATE POLICY "admin_resolve_requests" ON company_join_requests
  FOR UPDATE USING (
    company_id = get_my_company_id()
    AND (SELECT role FROM user_profiles WHERE id = auth.uid()) = 'admin'
  );
```

### 4.4 Local SQLite Changes

- **Schema version**: 23 → 24
- Add same columns to local tables (nullable, no FK enforcement in SQLite)
- New local tables: `user_profiles` (cache), `companies` (cache)
- Migration: `onUpgrade` adds columns via `ALTER TABLE ... ADD COLUMN`
- On first sync after upgrade, pull company/profile data from Supabase

---

## 5. Auth & Onboarding Flow

### 5.1 Flow Diagram

```
[App Launch]
     │
     ▼
[Supabase Auth Check]
     │
     ├── Not logged in → [Login / Register Screen]
     │                         │
     │                    [Supabase Auth signup/signin]
     │                         │
     ▼                         ▼
[Check user_profiles]
     │
     ├── No profile row → [Profile Setup Screen]
     │                         │
     │                    [Enter display name, optional fields]
     │                         │
     │                    [Company Step]
     │                    ├── "Create New Company" → [Enter company name]
     │                    │       → Auto-admin, status=approved
     │                    │       → Proceed to app
     │                    │
     │                    └── "Join Existing" → [Search/enter company name]
     │                            → Submit join request
     │                            → [Pending Approval Screen]
     │                            → Wait for admin to approve
     │
     ├── Profile exists, status=pending → [Pending Approval Screen]
     │
     ├── Profile exists, status=rejected → [Rejected Screen + retry option]
     │
     ├── Profile exists, status=deactivated → [Account Deactivated Screen]
     │
     └── Profile exists, status=approved → [Load last project → App]
```

### 5.2 Profile Setup Screen

**Fields (all optional except display name prompt):**
| Field | Input Type | Placeholder | Source (current) |
|-------|-----------|-------------|-----------------|
| Display Name | TextField | "John Doe" | NEW |
| Certification Number | TextField | "MDOT-12345" | PreferencesService.inspectorCertNumber |
| Phone | TextField | "(555) 123-4567" | PreferencesService.inspectorPhone |
| Position / Title | TextField | "Field Inspector" | NEW |

- "Skip for now" button always available
- Fields can be edited later from Settings
- On save, creates/updates `user_profiles` row in Supabase

### 5.3 Company Join Flow

**"Create New Company":**
1. User enters company name
2. App checks uniqueness against Supabase
3. Creates `companies` row
4. Sets `user_profiles.company_id`, `role = 'admin'`, `status = 'approved'`
5. Proceeds to app immediately

**"Join Existing Company":**
1. User searches for company by name (autocomplete from Supabase)
2. Creates `company_join_requests` row with `status = 'pending'`
3. Shows "Waiting for approval" screen with company name
4. App polls or listens (Supabase Realtime) for status change
5. On approval → `user_profiles.company_id` set, `status = 'approved'` → app unlocks

### 5.4 Pending Approval Screen

```
┌─────────────────────────────────┐
│                                 │
│      Waiting for Approval       │
│                                 │
│  You've requested to join:      │
│  [CTT Engineering]              │
│                                 │
│  An admin will review your      │
│  request. You'll be notified    │
│  when approved.                 │
│                                 │
│  [Cancel Request]               │
│                                 │
└─────────────────────────────────┘
```

---

## 6. Project Switcher UX

### 6.1 App Bar Integration

```
┌─────────────────────────────────────────┐
│ [Menu]  CTT Engineering          [Sync] │
│ ┌─────────────────────────────────────┐ │
│ │ Project: I-94 Resurfacing        ▼  │ │  ← Tap opens switcher
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│                                         │
│            [Page Content]               │
│                                         │
├─────────────────────────────────────────┤
│  [Home] [Calendar] [Projects] [Settings]│
└─────────────────────────────────────────┘
```

### 6.2 Project Switcher Dropdown

```
┌───────────────────────────────────┐
│ RECENT PROJECTS                   │
│ ┌───────────────────────────────┐ │
│ │ ● I-94 Resurfacing  (active) │ │  ← Currently selected
│ │   M-59 Bridge Repair         │ │
│ │   US-23 Widening             │ │
│ └───────────────────────────────┘ │
│ ─────────────────────────────────│
│ [+ New Project]                   │
│ [View All Projects]               │
└───────────────────────────────────┘
```

### 6.3 Behavior

- **On login**: Auto-load last selected project (stored per-user in local prefs or user_profile)
- **First time / no last project**: Show full project list
- **Tap project in switcher**: Set as active, reload dashboard/data for that project
- **"View All Projects"**: Navigate to full project list screen (existing, with search/filter)
- **"+ New Project"**: Navigate to project creation screen

### 6.4 Project Creation Changes

Current project creation stays the same, with additions:
- `company_id` auto-set from current user's profile (not user-visible)
- `created_by_user_id` auto-set from current user
- **Uniqueness check**: Before save, query `projects WHERE company_id = mine AND project_number = input`. If exists → show error "Project number already exists in your company."

---

## 7. Sync Architecture

### 7.1 Current State

```
App opens → Manual sync button → Pull ALL from Supabase → Push ALL to Supabase
```
- No automatic sync
- No company filtering
- No user attribution on records

### 7.2 New State: 4-Layer Sync Guarantee

#### Layer 1: Sync on Save (Immediate)
- **Trigger**: Every time a record is saved to local SQLite
- **Behavior**: If online, immediately push the record to Supabase
- **If offline**: Record queued in `sync_queue` table (existing pattern), pushed when connectivity returns
- **Implementation**: Add `_pushToRemote(record)` call in each repository's `save()` method

#### Layer 2: Firebase Silent Push (Daily Background Sync)
- **Server-side**: Supabase Edge Function runs on daily cron (e.g., 2:00 AM local time)
- **Action**: Sends FCM silent/data notification to all active users via Firebase Cloud Messaging
- **Android**: `workmanager` receives the push, starts a background Dart isolate, runs sync
- **iOS**: `BGProcessingTask` receives the push, runs sync in background
- **Fallback**: If push fails to deliver, Layer 3 catches it on next app open

#### Layer 3: Sync on App Open (Stale Check)
- **Trigger**: App opens (comes to foreground)
- **Check**: `DateTime.now() - lastSyncTimestamp > 24 hours`
- **If stale AND online**: Force full sync before showing app content
- **If stale AND offline**: Show warning banner "Data may be out of date. Connect to sync."
- **UI**: Progress indicator during forced sync, non-dismissible

#### Layer 4: Admin Sync Visibility
- **Data**: Each successful sync updates `user_profiles.last_synced_at` in Supabase
- **Admin Dashboard**: Shows per-user last sync timestamp
- **Flagging**: Users with `last_synced_at > 48 hours ago` shown with warning indicator
- **Action**: Admin can follow up manually (call, text, etc.)

### 7.3 Sync Scoping

All Supabase queries now include company filter:
```dart
// Before
final response = await supabase.from('projects').select();

// After (plus RLS enforces this server-side too)
final response = await supabase
    .from('projects')
    .select()
    .eq('company_id', currentUserProfile.companyId);
```

All writes include user attribution:
```dart
// Before
await supabase.from('daily_entries').insert(entry.toJson());

// After
await supabase.from('daily_entries').insert({
  ...entry.toJson(),
  'created_by_user_id': currentUserProfile.id,
});
```

### 7.4 Conflict Strategy: Additive-Only

- Users only ADD new records (entries, tests, photos)
- Users edit their OWN records only (enforce via `updated_by_user_id` check)
- No two users edit the same record → no conflicts possible
- Sync is simple MERGE: push local inserts, pull remote inserts
- If a record exists both locally and remotely with same ID → skip (already synced)

---

## 8. Migration Strategy

### 8.1 Supabase Migration (Server-Side, Run Once)

**Step 1: Create new tables**
```sql
-- 1. Companies
CREATE TABLE companies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. User Profiles
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  company_id UUID REFERENCES companies(id),
  role TEXT NOT NULL DEFAULT 'inspector',
  status TEXT NOT NULL DEFAULT 'pending',
  display_name TEXT,
  cert_number TEXT,
  phone TEXT,
  position TEXT,
  last_synced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Company Join Requests
CREATE TABLE company_join_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  company_id UUID NOT NULL REFERENCES companies(id),
  status TEXT NOT NULL DEFAULT 'pending',
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  resolved_by UUID REFERENCES auth.users(id)
);

-- 4. Auto-create user_profile on signup (trigger)
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO user_profiles (id) VALUES (NEW.id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();
```

**Step 2: Add columns to existing tables**
```sql
ALTER TABLE projects ADD COLUMN company_id UUID REFERENCES companies(id);
ALTER TABLE projects ADD COLUMN created_by_user_id UUID REFERENCES auth.users(id);

ALTER TABLE daily_entries ADD COLUMN created_by_user_id UUID REFERENCES auth.users(id);
ALTER TABLE daily_entries ADD COLUMN updated_by_user_id UUID REFERENCES auth.users(id);

ALTER TABLE photos ADD COLUMN created_by_user_id UUID REFERENCES auth.users(id);

ALTER TABLE bid_items ADD COLUMN created_by_user_id UUID REFERENCES auth.users(id);
-- (repeat for all data tables)
```

**Step 3: Seed + backfill**
```sql
-- Create your company
INSERT INTO companies (id, name) VALUES ('<your-company-uuid>', 'CTT Engineering');

-- Create your profile as admin
UPDATE user_profiles
SET company_id = '<your-company-uuid>', role = 'admin', status = 'approved',
    display_name = 'Roberto Chavez'
WHERE id = '<your-auth-user-id>';

-- Backfill existing projects
UPDATE projects SET company_id = '<your-company-uuid>', created_by_user_id = '<your-auth-user-id>'
WHERE company_id IS NULL;

-- Backfill existing entries
UPDATE daily_entries SET created_by_user_id = '<your-auth-user-id>'
WHERE created_by_user_id IS NULL;

-- (Repeat for photos, bid_items, etc.)
```

**Step 4: Add constraints + indexes**
```sql
ALTER TABLE projects ALTER COLUMN company_id SET NOT NULL;
CREATE UNIQUE INDEX idx_project_number_company ON projects(company_id, project_number);
CREATE INDEX idx_projects_company ON projects(company_id);
CREATE INDEX idx_user_profiles_company ON user_profiles(company_id);
CREATE INDEX idx_entries_created_by ON daily_entries(created_by_user_id);
```

**Step 5: Enable RLS** (see Section 4.3)

### 8.2 Local SQLite Migration (App-Side)

```dart
// In database_service.dart, onUpgrade:
if (oldVersion < 24) {
  // Add company/user columns to existing tables
  await db.execute('ALTER TABLE projects ADD COLUMN company_id TEXT');
  await db.execute('ALTER TABLE projects ADD COLUMN created_by_user_id TEXT');
  await db.execute('ALTER TABLE daily_entries ADD COLUMN created_by_user_id TEXT');
  await db.execute('ALTER TABLE daily_entries ADD COLUMN updated_by_user_id TEXT');
  await db.execute('ALTER TABLE photos ADD COLUMN created_by_user_id TEXT');
  await db.execute('ALTER TABLE bid_items ADD COLUMN created_by_user_id TEXT');

  // Create local cache tables
  await db.execute('''
    CREATE TABLE IF NOT EXISTS user_profiles (
      id TEXT PRIMARY KEY,
      company_id TEXT,
      role TEXT NOT NULL DEFAULT 'inspector',
      status TEXT NOT NULL DEFAULT 'pending',
      display_name TEXT,
      cert_number TEXT,
      phone TEXT,
      position TEXT,
      last_synced_at TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  ''');

  await db.execute('''
    CREATE TABLE IF NOT EXISTS companies (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    )
  ''');
}
```

### 8.3 App Code Migration (Gradual)

- Update Dart model classes to include new fields (nullable for backwards compatibility)
- Update repositories to include new fields in queries
- Update providers to pass user context
- Feature flag: `useNewOnboarding` — when off, skip company/profile flow and go straight to app (legacy behavior during development)

---

## 9. Admin Dashboard

### 9.1 Access
- Settings tab → "Admin Dashboard" (only visible when `userProfile.role == 'admin'`)

### 9.2 Layout

```
┌─────────────────────────────────────────┐
│ Admin Dashboard              [Back]     │
├─────────────────────────────────────────┤
│                                         │
│ PENDING REQUESTS (2)                    │
│ ┌─────────────────────────────────────┐ │
│ │ jane@email.com                      │ │
│ │ Requested: Feb 21, 2026             │ │
│ │ [Approve as ▼ Inspector] [Reject]   │ │
│ ├─────────────────────────────────────┤ │
│ │ bob@email.com                       │ │
│ │ Requested: Feb 20, 2026             │ │
│ │ [Approve as ▼ Inspector] [Reject]   │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ TEAM MEMBERS (4)                        │
│ ┌─────────────────────────────────────┐ │
│ │ Roberto Chavez (You)                │ │
│ │ Admin · Synced: just now            │ │
│ ├─────────────────────────────────────┤ │
│ │ John Doe                            │ │
│ │ Inspector · Synced: 2 hours ago     │ │
│ ├─────────────────────────────────────┤ │
│ │ Mike Smith                          │ │
│ │ Engineer · Synced: 1 day ago [!]    │ │  ← stale flag
│ ├─────────────────────────────────────┤ │
│ │ Sara Kim                            │ │
│ │ Viewer · Synced: 5 minutes ago      │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Tap any member to:                      │
│ · Change role                           │
│ · Deactivate account                    │
│                                         │
└─────────────────────────────────────────┘
```

### 9.3 Admin Actions

| Action | Behavior |
|--------|----------|
| Approve request | Set `user_profiles.status = 'approved'`, `company_id = my_company`, assign selected role |
| Reject request | Set `company_join_requests.status = 'rejected'` |
| Change role | Update `user_profiles.role`. Cannot demote yourself from admin if you're the only admin. |
| Deactivate user | Set `user_profiles.status = 'deactivated'`. User can't log in. Data preserved. |
| Reactivate user | Set `user_profiles.status = 'approved'`. User regains access. |

### 9.4 Sync Stale Flagging

- `last_synced_at` checked against `now()`
- **< 24h**: Green / normal display
- **24-48h**: Yellow / warning icon
- **> 48h**: Red / alert icon with `[!]` marker
- **Never synced**: "Never synced" text in red

---

## 10. Implementation Phases

### Phase 1: Foundation (Supabase + Data Models)
**Scope**: Server-side schema + Dart models + local SQLite migration
**Agent**: `backend-supabase-agent` + `backend-data-layer-agent`

- [ ] Create Supabase tables (companies, user_profiles, company_join_requests)
- [ ] Add columns to existing Supabase tables
- [ ] Write RLS policies + helper function
- [ ] Create auto-profile trigger on auth.users
- [ ] Seed CTT Engineering company + Roberto admin profile
- [ ] Backfill existing data
- [ ] Add indexes + constraints
- [ ] SQLite schema migration v23 → v24
- [ ] Create Dart models: `Company`, `UserProfile`, `CompanyJoinRequest`
- [ ] Update existing models: `Project`, `DailyEntry`, `Photo`, `BidItem` with new fields
- [ ] Add `workmanager` and `firebase_messaging` to pubspec.yaml

**Acceptance Criteria**:
- Supabase tables exist with correct schema
- RLS policies block cross-company access (test with 2 users)
- Existing data backfilled with company_id + user_id
- Local SQLite migrates cleanly from v23 → v24
- Dart models compile with new fields

### Phase 2: Auth & User Profile
**Scope**: Onboarding flow, profile management, company creation/joining
**Agent**: `auth-agent` + `frontend-flutter-specialist-agent`

- [ ] Profile Setup screen (display name, cert, phone, position)
- [ ] Company creation flow ("Create new company")
- [ ] Company join flow ("Join existing" with search)
- [ ] Pending Approval screen (waiting state)
- [ ] Rejected / Deactivated screen
- [ ] Update AuthProvider: load user_profile on login, expose role
- [ ] Update router: redirect to profile setup if no profile
- [ ] Migrate PreferencesService inspector fields to user_profile
- [ ] Settings: "Edit Profile" screen

**Acceptance Criteria**:
- New user signup → profile setup → company create → lands in app as admin
- Second user signup → join request → pending screen → approved by admin → lands in app
- Deactivated user cannot access app
- Profile fields auto-fill forms (replaces PreferencesService)

### Phase 3: Sync Scoping + On-Save Sync
**Scope**: Company-scoped sync + immediate push on save
**Agent**: `backend-data-layer-agent` + `backend-supabase-agent`

- [ ] Update sync adapter: filter all queries by company_id
- [ ] Include created_by_user_id on all writes
- [ ] Sync user_profiles for company members (cache locally)
- [ ] Implement sync-on-save: push to Supabase after each SQLite write (when online)
- [ ] Implement sync-on-app-open: check last_synced_at, force sync if >24h stale
- [ ] Update last_synced_at on user_profiles after successful sync
- [ ] Test with 2 accounts in same company: verify data visibility

**Acceptance Criteria**:
- User A creates entry → syncs → User B sees it
- Sync only pulls company's data (not other companies)
- created_by_user_id populated on all new records
- Stale sync detection works (>24h triggers forced sync)

### Phase 4: Firebase + Background Sync
**Scope**: FCM integration + background sync handlers
**Agent**: `backend-data-layer-agent`

- [ ] Firebase project setup (console.firebase.google.com)
- [ ] Add `firebase_core`, `firebase_messaging` to app
- [ ] Android: Configure FCM + `workmanager` background handler
- [ ] iOS: Configure FCM + `BGProcessingTask` handler
- [ ] Supabase Edge Function: daily cron sends silent FCM push
- [ ] Background sync handler: runs full sync in isolate
- [ ] Test: kill app → wait for push → verify sync happened

**Acceptance Criteria**:
- Android: daily background sync runs without app open
- iOS: background sync runs (best-effort per Apple constraints)
- last_synced_at updates even from background sync
- No battery/data abuse (single daily sync, not continuous)

### Phase 5: Project Switcher
**Scope**: Project selection UX overhaul
**Agent**: `frontend-flutter-specialist-agent`

- [ ] Project switcher dropdown in app bar
- [ ] "Remember last project" persistence (local prefs, per-user)
- [ ] Auto-load last project on login
- [ ] Fall back to project list if no last project
- [ ] "View All Projects" link in switcher
- [ ] "New Project" link in switcher
- [ ] Project creation: add company_id, created_by_user_id, uniqueness check

**Acceptance Criteria**:
- App opens → last project auto-loads → user can start working immediately
- Tap switcher → see recent projects → tap to switch
- New project validates uniqueness within company
- Switching projects reloads all data (dashboard, entries, etc.)

### Phase 6: Admin Dashboard
**Scope**: Admin-only management screen
**Agent**: `frontend-flutter-specialist-agent` + `backend-data-layer-agent`

- [ ] Admin Dashboard screen (Settings → Admin Dashboard, admin-only)
- [ ] Pending requests list with approve/reject actions
- [ ] Role selector on approve (dropdown: Inspector, Engineer, Viewer)
- [ ] Team members list with role + last_synced_at display
- [ ] Stale sync flagging (color-coded: green/yellow/red)
- [ ] Tap member → change role dialog
- [ ] Tap member → deactivate/reactivate toggle
- [ ] Guard: cannot remove last admin

**Acceptance Criteria**:
- Only admins see the "Admin Dashboard" menu item
- Can approve request → user gains access
- Can reject request → user sees rejected screen
- Can change roles → role updates in Supabase
- Can deactivate → user blocked from app
- Stale sync flags show correctly per user

### Phase 7: Audit Trail UI
**Scope**: Display who recorded what
**Agent**: `frontend-flutter-specialist-agent` + `pdf-agent`

- [ ] Display "Recorded by: [Name]" on daily entry cards
- [ ] Display "Recorded by: [Name]" on photo details
- [ ] Display "Created by: [Name]" on project details
- [ ] Resolve user_id → display_name via cached user_profiles
- [ ] Update PDF generation: include author name on entries
- [ ] Fallback: if display_name is null, show email prefix

**Acceptance Criteria**:
- Entry created by User A shows "Recorded by: John Doe" when User B views it
- Works offline (uses cached user_profiles)
- PDFs include author attribution
- Graceful fallback for users without display names

### Phase 8: Viewer Role Enforcement
**Scope**: Read-only mode for Viewer role
**Agent**: `frontend-flutter-specialist-agent`

- [ ] Check `userProfile.role` in providers — block write operations for viewers
- [ ] Hide FABs, create buttons, edit buttons when role == 'viewer'
- [ ] Show non-intrusive "View-only mode" indicator
- [ ] Server-side: RLS blocks INSERT/UPDATE/DELETE for viewers
- [ ] Graceful error: if viewer somehow triggers write, show friendly message

**Acceptance Criteria**:
- Viewer can browse all projects, entries, photos — read everything
- Viewer sees no create/edit/delete buttons
- Viewer cannot modify data even via direct API call (RLS blocks it)
- Non-viewers see no changes to their experience

---

## 11. Dependencies & New Packages

| Package | Purpose | Phase |
|---------|---------|-------|
| `workmanager` | Android background task scheduling | Phase 4 |
| `firebase_core` | Firebase initialization | Phase 4 |
| `firebase_messaging` | FCM silent push notifications | Phase 4 |

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Existing data has no company_id | Migration could break queries | Backfill ALL existing data before enabling RLS. Make columns nullable first. |
| iOS background sync unreliable | Data may not sync daily on iOS | Layer 3 (sync-on-open) catches this. Admin visibility flags stale users. |
| RLS misconfiguration | Users see wrong company's data | Test RLS with 2 separate company accounts before production. |
| User never opens app | Data stuck on device forever | No technical solution. Admin dashboard shows stale users for manual follow-up. |
| Large company = lots of data | Sync takes too long | Pagination, incremental sync (only changed records since last sync). |
| Profile replaces PreferencesService | Existing prefs lost on migration | One-time migration: read PreferencesService values → write to user_profile on first login after update. |

---

## 13. Out of Scope (Future)

- Per-project access control (invite-only projects)
- Cross-company project sharing
- In-app messaging / chat
- Push notifications for non-sync events (e.g., "entry approved")
- Audit log (full history of who changed what, when)
- Multi-company membership (user belongs to >1 company)
- Data export / analytics dashboard
