---
feature: settings
type: overview
scope: Consent, Legal, Help/Support, Admin, Trash, Theme & Profile Management
updated: 2026-03-30
---

# Settings Feature Overview

## Purpose

The Settings feature is the app's configuration and compliance hub. It owns user preferences (theme), profile editing, consent flow and legal documents, help/support ticket submission, admin dashboard (join-request approval, member management), trash management (soft-delete recovery), and personnel type management. It is not limited to "app settings" — it is the primary surface for onboarding consent gating, legal transparency, and company administration.

## Key Responsibilities

- **Theme Management**: Toggle between light and dark themes, persist preference via `PreferencesService`
- **Profile Editing**: Edit inspector name and contact info (`EditProfileScreen`)
- **Consent Flow**: Capture and record user consent (`ConsentScreen`, `ConsentProvider`); acts as a router gate — unauthenticated or un-consented users cannot proceed
- **Legal Documents**: Display Terms of Service, Privacy Policy, and other legal content (`LegalDocumentScreen`, `OssLicensesScreen`)
- **Help & Support**: Submit support tickets and upload diagnostic logs (`HelpSupportScreen`, `SupportProvider`)
- **Admin Dashboard**: Approve/reject join requests, manage company members and roles (`AdminDashboardScreen`, `AdminProvider`)
- **Trash Management**: View and manage soft-deleted records; admin mode shows all users' deletions (`TrashScreen`, `TrashRepository`)
- **Personnel Types**: Create and manage custom personnel categories per project (`PersonnelTypesScreen`)
- **Sync Status Display**: Show pending data and sync history (via `sync_section.dart`)

## Key Files

### Dependency Injection

| File Path | Purpose |
|-----------|---------|
| `lib/features/settings/di/settings_providers.dart` | Registers `ThemeProvider`, `TrashRepository`, `SoftDeleteService` |
| `lib/features/settings/di/consent_support_factory.dart` | Factory wiring `ConsentProvider` and `SupportProvider` with all datasources/repos; returns `ConsentSupportResult` |

### Models

| File Path | Purpose |
|-----------|---------|
| `lib/features/settings/data/models/consent_record.dart` | `ConsentRecord` — local record of user consent events |
| `lib/features/settings/data/models/support_ticket.dart` | `SupportTicket` — support ticket submitted by user |
| `lib/features/settings/data/models/user_certification.dart` | `UserCertification` — certifications synced from Supabase |
| `lib/features/settings/data/models/models.dart` | Barrel export |

### Data Sources

| File Path | Purpose |
|-----------|---------|
| `lib/features/settings/data/datasources/consent_local_datasource.dart` | `ConsentLocalDatasource` — SQLite read/write for consent records |
| `lib/features/settings/data/datasources/support_local_datasource.dart` | `SupportLocalDatasource` — SQLite read/write for support tickets |
| `lib/features/settings/data/datasources/local/user_certification_local_datasource.dart` | `UserCertificationLocalDatasource` — read-only; data synced from Supabase |
| `lib/features/settings/data/datasources/remote/log_upload_remote_datasource.dart` | `LogUploadRemoteDatasource` — uploads diagnostic logs to Supabase storage |

### Repositories

| File Path | Purpose |
|-----------|---------|
| `lib/features/settings/data/repositories/trash_repository.dart` | `TrashRepository` — queries soft-deleted records by table; supports admin and user-scoped modes |
| `lib/features/settings/data/repositories/admin_repository_impl.dart` | `AdminRepositoryImpl` — Supabase-backed implementation of `AdminRepository` |
| `lib/features/settings/domain/repositories/admin_repository.dart` | `AdminRepository` — domain interface for admin operations |
| `lib/features/settings/data/repositories/consent_repository.dart` | `ConsentRepository` — wraps `ConsentLocalDatasource` |
| `lib/features/settings/data/repositories/support_repository.dart` | `SupportRepository` — wraps `SupportLocalDatasource` |

### Providers

| File Path | Purpose |
|-----------|---------|
| `lib/features/settings/presentation/providers/theme_provider.dart` | `ThemeProvider` — light/dark theme toggle, app-wide |
| `lib/features/settings/presentation/providers/admin_provider.dart` | `AdminProvider` — join-request approval, member role management |
| `lib/features/settings/presentation/providers/consent_provider.dart` | `ConsentProvider` — consent state, records consent in SQLite |
| `lib/features/settings/presentation/providers/support_provider.dart` | `SupportProvider` — ticket submission and log upload |

### Screens

| File Path | Purpose |
|-----------|---------|
| `lib/features/settings/presentation/screens/settings_screen.dart` | `SettingsScreen` — main settings hub |
| `lib/features/settings/presentation/screens/trash_screen.dart` | `TrashScreen` — soft-delete recovery |
| `lib/features/settings/presentation/screens/admin_dashboard_screen.dart` | `AdminDashboardScreen` — join-request and member management |
| `lib/features/settings/presentation/screens/personnel_types_screen.dart` | `PersonnelTypesScreen` — custom personnel category management |
| `lib/features/settings/presentation/screens/edit_profile_screen.dart` | `EditProfileScreen` — inspector name and contact editing |
| `lib/features/settings/presentation/screens/consent_screen.dart` | `ConsentScreen` — consent capture and acceptance |
| `lib/features/settings/presentation/screens/legal_document_screen.dart` | `LegalDocumentScreen` — display ToS, Privacy Policy, etc. |
| `lib/features/settings/presentation/screens/oss_licenses_screen.dart` | `OssLicensesScreen` — open-source license disclosures |
| `lib/features/settings/presentation/screens/help_support_screen.dart` | `HelpSupportScreen` — support ticket submission |

## Data Sources

- **SQLite**: Consent records, support tickets, personnel types, soft-deleted record recovery
- **Supabase**: User certifications (synced in, read-only locally), log uploads, admin operations (join requests, member roles)
- **Shared Preferences**: Theme preference and user metadata (via `PreferencesService`)
- **Auth**: Current user profile from `auth` feature

## Integration Points

**Depends on:**
- `auth` — Current user profile, `AuthProvider` injected into `ConsentProvider`; sign-out action
- `sync` — Pending data count and sync status display (`sync_section.dart`)
- `photos` — Profile photo handling
- `core/theme` — Theme constants, `FieldGuideColors`
- `shared/services/preferences_service.dart` — Theme persistence

**Required by:**
- All features — `ThemeProvider` drives app-wide styling
- `core/router` — `ConsentScreen` is a router gate; un-consented users are redirected before accessing the app
- `dashboard` — Settings access from main menu

## Offline Behavior

Settings are **fully offline-capable** for theme, profile editing, consent recording, and support ticket creation (tickets queued locally). Admin operations (join-request approval, member management) require a network connection via Supabase. Log uploads require network. Trash browsing and soft-delete recovery are fully local.

## Edge Cases & Limitations

- **Consent Gate**: Router redirects un-consented users to `ConsentScreen`; consent must be recorded before app access is granted
- **Admin Mode in Trash**: When `adminMode=true`, `TrashRepository` returns all users' deleted records; non-admin mode filters by `userId` via `deleted_by` column
- **UserCertification is read-only**: Synced down from Supabase; no local write path
- **Log Upload**: `LogUploadRemoteDatasource` gracefully no-ops when Supabase is not configured (`SupabaseConfig.isConfigured` check)
- **Theme Persistence**: Persists across app kills; default is system theme
- **Personnel Types**: Project-scoped; not shared across projects

## Detailed Specifications

See `rules/frontend/flutter-ui.md` for:
- Theme constants and color palette
- Settings screen layout and component standards

See `rules/auth/supabase-auth.md` for:
- Consent flow requirements and RLS implications
