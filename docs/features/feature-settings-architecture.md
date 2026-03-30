---
feature: settings
type: architecture
scope: User Preferences, Consent, Support, Admin & Legal
updated: 2026-03-30
---

# Settings Feature Architecture

Settings has grown well beyond theme management. It now owns consent/legal compliance,
support ticket submission, admin company management, soft-delete trash recovery, and
user profile editing. It is one of the larger feature modules.

## Directory Structure

```
lib/features/settings/
├── data/
│   ├── datasources/
│   │   ├── consent_local_datasource.dart       # SQLite CRUD for consent_records
│   │   ├── support_local_datasource.dart        # SQLite CRUD for support_tickets
│   │   ├── local/
│   │   │   └── user_certification_local_datasource.dart
│   │   └── remote/
│   │       └── log_upload_remote_datasource.dart  # Supabase Storage upload
│   ├── models/
│   │   ├── models.dart
│   │   ├── consent_record.dart     # ConsentRecord, ConsentAction, ConsentPolicyType
│   │   ├── support_ticket.dart     # SupportTicket, SupportTicketStatus
│   │   └── user_certification.dart # UserCertification (read-only sync mirror)
│   └── repositories/
│       ├── admin_repository_impl.dart  # Supabase RPC-backed admin ops
│       ├── consent_repository.dart     # Thin wrapper over ConsentLocalDatasource
│       ├── support_repository.dart     # Thin wrapper over SupportLocalDatasource
│       └── trash_repository.dart       # Soft-deleted record queries (SQLite)
├── domain/
│   ├── domain.dart
│   └── repositories/
│       └── admin_repository.dart    # Abstract interface for admin operations
├── presentation/
│   ├── providers/
│   │   ├── providers.dart
│   │   ├── theme_provider.dart      # ThemeProvider (AppThemeMode: light/dark/highContrast)
│   │   ├── admin_provider.dart      # AdminProvider (join requests, member management)
│   │   ├── consent_provider.dart    # ConsentProvider (GDPR consent gating)
│   │   └── support_provider.dart    # SupportProvider (ticket form + log upload)
│   ├── screens/
│   │   ├── screens.dart
│   │   ├── settings_screen.dart
│   │   ├── trash_screen.dart
│   │   ├── admin_dashboard_screen.dart
│   │   ├── personnel_types_screen.dart
│   │   ├── edit_profile_screen.dart
│   │   ├── consent_screen.dart
│   │   ├── legal_document_screen.dart
│   │   ├── oss_licenses_screen.dart
│   │   └── help_support_screen.dart
│   ├── widgets/
│   │   ├── widgets.dart
│   │   ├── theme_section.dart
│   │   ├── sync_section.dart
│   │   ├── clear_cache_dialog.dart
│   │   ├── sign_out_dialog.dart
│   │   ├── section_header.dart
│   │   └── member_detail_sheet.dart
│   └── presentation.dart
├── di/
│   ├── settings_providers.dart        # Tier-4 provider list
│   └── consent_support_factory.dart   # Factory for ConsentProvider + SupportProvider
└── settings.dart
```

## Data Layer

### Models

| Class | File | Notes |
|-------|------|-------|
| `ConsentRecord` | `consent_record.dart` | Append-only audit record. Fields: id, userId, policyType, policyVersion, acceptedAt, appVersion, action. Table: `user_consent_records`. |
| `ConsentAction` | `consent_record.dart` | Enum: `accepted`, `revoked`. Used for GDPR audit trail. |
| `ConsentPolicyType` | `consent_record.dart` | Enum: `privacyPolicy`, `termsOfService`. |
| `SupportTicket` | `support_ticket.dart` | Fields: id, userId, subject, message, appVersion, platform, logFilePath, createdAt, status. Table: `support_tickets`. No `copyWith` — status is server-managed. |
| `SupportTicketStatus` | `support_ticket.dart` | Enum: `open`, `acknowledged`, `resolved`. |
| `UserCertification` | `user_certification.dart` | Read-only sync mirror. Fields: id, userId, certType, certNumber, expiryDate, createdAt, updatedAt. Managed server-side; client is view-only. |

### Datasources

| Class | Location | Backend |
|-------|----------|---------|
| `ConsentLocalDatasource` | `datasources/` (flat) | SQLite |
| `SupportLocalDatasource` | `datasources/` (flat) | SQLite |
| `UserCertificationLocalDatasource` | `datasources/local/` | SQLite |
| `LogUploadRemoteDatasource` | `datasources/remote/` | Supabase Storage (`support-logs` bucket) |

Note: The datasource directory is mixed — `ConsentLocalDatasource` and
`SupportLocalDatasource` sit flat in `datasources/`, while `UserCertificationLocalDatasource`
is under `datasources/local/` and `LogUploadRemoteDatasource` under `datasources/remote/`.

### Repositories

| Class | Interface | Notes |
|-------|-----------|-------|
| `TrashRepository` | None (concrete only) | Queries soft-deleted rows across SQLite tables. Takes `DatabaseService`. Supports admin mode (all deleted) and user mode (deleted_by filter). |
| `AdminRepository` | `domain/repositories/admin_repository.dart` | Abstract interface. Operations: getPendingJoinRequests, approveJoinRequest, rejectJoinRequest, getCompanyMembers, updateMemberRole, deactivateMember, reactivateMember, promoteToAdmin. |
| `AdminRepositoryImpl` | Implements `AdminRepository` | Supabase-backed. All mutating operations use SECURITY DEFINER RPCs — no direct table writes. Requires `companyId` for runtime privilege guard. |
| `ConsentRepository` | None (concrete only) | Thin wrapper over `ConsentLocalDatasource`. Append-only (no update/delete). Methods: recordConsent, getConsentHistory, hasAcceptedPolicy, getLatestConsent. |
| `SupportRepository` | None (concrete only) | Thin wrapper over `SupportLocalDatasource`. Methods: submitTicket, getTickets, getTicketById, getTicketsByStatus, updateTicketStatus. |

## Presentation Layer

### Providers

| Class | Type | Key Responsibilities |
|-------|------|---------------------|
| `ThemeProvider` | `ChangeNotifier` | Manages `AppThemeMode` (light / dark / highContrast). Persists to SharedPreferences. Default: dark. Exposes `currentTheme`, `isDark`, `isLight`, `isHighContrast`, `cycleTheme()`. |
| `AdminProvider` | `ChangeNotifier` | Loads pending join requests and company members via `AdminRepository`. Lazy repository creation keyed by `companyId` (solves stale-ID bug). Exposes approve/reject/role/deactivate/reactivate/promoteToAdmin actions. Also exposes static `syncHealth(UserProfile)`. |
| `ConsentProvider` | `ChangeNotifier` | GDPR-compliant consent gating. Stores consent in SharedPreferences (fast gate checks) AND `ConsentRepository` (SQLite audit trail). Supports `acceptConsent`, `revokeConsent`, `clearOnSignOut`, `writeDeferredAuditRecordsIfNeeded`. Policy version sourced from `AppConfigProvider` (remote config), falls back to `'1.0.0'`. |
| `SupportProvider` | `ChangeNotifier` | Support ticket form state. On submit: optionally zips and uploads log files via `LogUploadRemoteDatasource`, then inserts a `SupportTicket` into local SQLite via `SupportRepository`. PII scrubbing via `Logger.scrubString()` before upload. |

### Screens

| Screen | Purpose |
|--------|---------|
| `SettingsScreen` | Main hub; surfaces profile, theme, sync, legal, admin entry points, sign-out |
| `TrashScreen` | Browse and restore soft-deleted records |
| `AdminDashboardScreen` | Company admin: pending join requests + member management |
| `PersonnelTypesScreen` | Manage inspector personnel type taxonomy |
| `EditProfileScreen` | User profile editing |
| `ConsentScreen` | Privacy policy / ToS consent gate shown pre-app-use |
| `LegalDocumentScreen` | Renders a named legal document (ToS / Privacy Policy) |
| `OssLicensesScreen` | Open-source license listing |
| `HelpSupportScreen` | Support ticket submission form (driven by SupportProvider) |

### Widgets

| Widget | Purpose |
|--------|---------|
| `ThemeSection` | Theme picker (light / dark / high contrast) |
| `SyncSection` | Sync status display with trigger button |
| `ClearCacheDialog` | Confirmation dialog for cache clearing |
| `SignOutDialog` | Confirmation dialog for sign-out |
| `SectionHeader` | Consistent styled section label |
| `MemberDetailSheet` | Bottom sheet for viewing/managing a company member's details |

## Dependency Injection

Two DI files handle settings registration:

### `di/settings_providers.dart` — Tier 4 provider list
Registers: `PreferencesService` (value), `ThemeProvider` (created), `TrashRepository` (value), `SoftDeleteService` (value).
Called from `main.dart` / `main_driver.dart` as part of the top-level `MultiProvider`.

### `di/consent_support_factory.dart` — Consent + Support factory
Exports `ConsentSupportResult` (holds `ConsentProvider` + `SupportProvider`) and the factory function `createConsentAndSupportProviders(dbService, preferencesService, authProvider)`.
Wires the full chain: `ConsentLocalDatasource` → `ConsentRepository` → `ConsentProvider` and
`SupportLocalDatasource` + `LogUploadRemoteDatasource` → `SupportRepository` → `SupportProvider`.
Called once from `main.dart` / `main_driver.dart` before provider registration. Eliminates wiring duplication between entrypoints.

`AdminProvider` is registered separately (not in settings_providers.dart) because it requires a repository factory that depends on `SupabaseClient` and `AuthProvider`, which are wired at app startup.

## Key Patterns

### Consent Gating
`ConsentProvider.hasConsented` is checked by the router guard before granting access to
the main app shell. If false, the router redirects to `ConsentScreen`. Consent is dual-stored:
SharedPreferences for in-process gate speed, SQLite (`user_consent_records`) for GDPR audit trail.

### Append-Only Audit Trail
`ConsentRecord` and `SupportTicket` are append-only — no UPDATE or DELETE from the client.
Revocations are new rows with `action: ConsentAction.revoked`, not modifications to existing rows.

### Admin Security
All mutating admin operations go through Supabase SECURITY DEFINER RPCs, not direct table writes.
`AdminRepositoryImpl` performs a runtime `companyId` null-check before every call (`_requireCompanyId()`).
RLS enforces the same constraints server-side as a defense-in-depth measure.

### Theme: 3 Modes
`AppThemeMode` (defined in `theme_provider.dart`) has three values: `light`, `dark`, `highContrast`.
This replaces the old Flutter `ThemeMode` (which only had light/dark/system). Default is `dark`
for outdoor field use.

### Offline Behavior
- Theme: fully local (SharedPreferences), no network required.
- Consent: accept/revoke writes to SQLite locally; sync to Supabase via `ConsentRecordAdapter` in SyncRegistry (push-only, no pull/conflict).
- Support tickets: inserted into local SQLite first (offline-first); Supabase sync deferred via SyncRegistry `SupportTicketAdapter`.
- Log upload: direct to Supabase Storage at submit time; skipped gracefully if offline or no auth session.
- Admin operations: require network (Supabase RPC calls); errors surfaced via `AdminProvider.error`.

## Relationships

```
Settings depends on:
    auth/            — AuthProvider (user identity, sign-out), AppConfigProvider (policy version)
    sync/            — SyncProvider (sync section status display)
    photos/          — SoftDeleteService, cache clearing
    shared/          — PreferencesService

Settings is required by:
    core/router/     — ConsentProvider (consent gate redirect)
    main.dart        — ThemeProvider (MaterialApp theme), ConsentProvider (startup gate)
```

## File Locations (Quick Reference)

| Category | Path |
|----------|------|
| Models | `lib/features/settings/data/models/` |
| Datasources | `lib/features/settings/data/datasources/` |
| Repositories (impl) | `lib/features/settings/data/repositories/` |
| Repository interfaces | `lib/features/settings/domain/repositories/` |
| Providers | `lib/features/settings/presentation/providers/` |
| Screens | `lib/features/settings/presentation/screens/` |
| Widgets | `lib/features/settings/presentation/widgets/` |
| DI | `lib/features/settings/di/` |
