# Settings PRD

## Purpose
Settings provides a centralized place for inspectors to configure their profile, app behavior, and account management. Inspector profile data (name, initials, certification number) flows into PDF reports, form auto-fill, and daily entry headers, making accurate settings critical for document generation. Settings also hosts legal/consent flows, help/support ticket submission, admin tooling, and data lifecycle management (trash).

## Core Capabilities
- Manage inspector profile: name, initials, phone, certification number, agency
- Configure appearance: light/dark/system theme selection
- Toggle form auto-fill behavior: enable/disable auto-fill, use last values carry-forward
- Configure project behavior: auto-load last project on startup
- Manage account: view authenticated email, sign out
- Configure cloud sync: manual sync trigger, auto-sync on WiFi toggle, view sync status and pending count
- Configure weather: select API provider (Open-Meteo), toggle auto-fetch on entry creation
- Configure PDF export: view active template, set default signature name
- Manage personnel types for daily entry workforce tracking
- Data management: backup, restore, clear cached exports, trash/restore deleted records
- View app version, licenses (OSS), and legal documents
- Submit help/support tickets
- Review and re-accept consent records
- Admin dashboard for privileged users

## Data Model

### Device-Local Settings (SharedPreferences only)
Device-local key-value pairs not synced to cloud. SharedPreferences is used **only** for these preferences:
- `theme_mode` — appearance preference
- `gauge_number` — gauge display setting
- Any other strictly device-local UI preferences

### SQLite Tables (synced via change_log triggers)
> **Note:** `sync_status` columns are DEPRECATED. Sync state is tracked exclusively via `change_log` trigger-based rows. Do not add or rely on `sync_status` columns in any settings-related table.

| Table | Purpose |
|-------|---------|
| `user_profiles` | Inspector profile data: name, initials, phone, cert number, agency. Source of truth for PDF/form data. |
| `user_consent_records` | Consent audit trail: which version accepted, timestamp, device info. |
| `support_tickets` | Help/support requests submitted by the user. |

### Models
| Model | File | Maps To |
|-------|------|---------|
| `UserProfile` | `lib/shared/` or auth feature | `user_profiles` table |
| `ConsentRecord` | `lib/features/settings/data/models/consent_record.dart` | `user_consent_records` table |
| `SupportTicket` | `lib/features/settings/data/models/support_ticket.dart` | `support_tickets` table |
| `UserCertification` | `lib/features/settings/data/models/user_certification.dart` | Certification data |

### Storage Clarification
Inspector profile fields (name, initials, cert number, agency, phone) are stored in the **`user_profiles` SQLite table** and synced to Supabase — NOT in SharedPreferences. SharedPreferences is limited to truly device-local preferences (theme, gauge number).

## Screens

### SettingsScreen
Main settings hub. Organized into collapsible sections: Appearance, Inspector Profile, Form Auto-Fill, Project, Account, Cloud Sync, PDF Export, Weather, Personnel Types, Data, and About. Each setting persists immediately on change. Profile edits navigate to EditProfileScreen.

### EditProfileScreen
`lib/features/settings/presentation/screens/edit_profile_screen.dart`
Dedicated screen for editing inspector profile fields. Reads/writes `user_profiles` table via provider/repository. Not a modal dialog — navigates as a full screen.

### ConsentScreen
`lib/features/settings/presentation/screens/consent_screen.dart`
Displays current Terms of Service / Privacy Policy for review and acceptance. Creates a `ConsentRecord` on acceptance. Required on first launch and on policy version change.

### HelpSupportScreen
`lib/features/settings/presentation/screens/help_support_screen.dart`
Allows users to submit support tickets. Writes `SupportTicket` records to local SQLite, synced to Supabase. May include log upload via `LogUploadRemoteDatasource`.

### LegalDocumentScreen
`lib/features/settings/presentation/screens/legal_document_screen.dart`
Renders static legal documents (Terms of Service, Privacy Policy) in-app. Accepts a document type parameter to determine which document to display.

### OssLicensesScreen
`lib/features/settings/presentation/screens/oss_licenses_screen.dart`
Displays open-source software license acknowledgments for all third-party packages used by the app.

### AdminDashboardScreen
`lib/features/settings/presentation/screens/admin_dashboard_screen.dart`
Privileged screen for admin users. Exposes admin-only operations. Access is gated by role check in `AdminProvider`.

### TrashScreen
`lib/features/settings/presentation/screens/trash_screen.dart`
Lists soft-deleted records eligible for permanent deletion or restoration. Reads from local SQLite `deleted_at`-flagged rows via `TrashRepository`.

### PersonnelTypesScreen
`lib/features/settings/presentation/screens/personnel_types_screen.dart`
Manage personnel types for daily entry workforce tracking. Backed by the `personnel_types` SQLite table.

## Providers

| Provider | File | Responsibility |
|----------|------|---------------|
| `ThemeProvider` | `presentation/providers/theme_provider.dart` | Theme mode state, persisted in SharedPreferences |
| `ConsentProvider` | `presentation/providers/consent_provider.dart` | Consent acceptance state, delegates to ConsentRepository |
| `SupportProvider` | `presentation/providers/support_provider.dart` | Support ticket submission state, delegates to SupportRepository |
| `AdminProvider` | `presentation/providers/admin_provider.dart` | Admin role check, admin operations state, delegates to AdminRepository |

## Repositories

| Repository | Interface | Implementation | Datasource |
|------------|-----------|----------------|------------|
| ConsentRepository | `domain/repositories/` (implicit) | `data/repositories/consent_repository.dart` | `consent_local_datasource.dart` |
| SupportRepository | `domain/repositories/` (implicit) | `data/repositories/support_repository.dart` | `support_local_datasource.dart` |
| AdminRepository | `domain/repositories/admin_repository.dart` | `data/repositories/admin_repository_impl.dart` | Supabase direct |
| TrashRepository | — | `data/repositories/trash_repository.dart` | SQLite soft-delete queries |

## Dependency Injection
`lib/features/settings/di/settings_providers.dart` — main DI registrations for settings feature.
`lib/features/settings/di/consent_support_factory.dart` — factory wiring for consent and support dependencies.

## User Flow
Inspectors access Settings from the bottom navigation bar. The screen is organized into collapsible sections. Profile edits navigate to EditProfileScreen (full screen, not a dialog). Personnel types management navigates to PersonnelTypesScreen. Consent review, legal docs, OSS licenses, help/support, admin dashboard, and trash each navigate to their dedicated screens.

## Offline Behavior
Fully functional offline. Device-local preferences (theme, gauge) are read synchronously from SharedPreferences. Profile data and consent/support records are read from local SQLite. Sync of `user_profiles`, `user_consent_records`, and `support_tickets` to Supabase occurs via the change_log sync engine when connectivity is available. Sign out clears the local session.

## Sync Pattern
Settings tables (`user_profiles`, `user_consent_records`, `support_tickets`) participate in sync via the **change_log trigger pattern** — SQLite triggers write to `change_log` on insert/update/delete, and the sync engine reads that table to push changes to Supabase. There are no `sync_status` columns on these tables (deprecated pattern — do not use).

## Dependencies
- Features: auth (sign out, email display, user_profiles), sync (manual trigger, change_log engine), projects (auto-load setting)
- Packages: `shared_preferences`, `provider`, `supabase_flutter` (auth state, admin repo), `package_info_plus` (app version)

## Primary Implementation Context
Implement workers using `rules/frontend/flutter-ui.md` for presentation and `rules/backend/data-layer.md` for repositories/datasources/SQLite schema
