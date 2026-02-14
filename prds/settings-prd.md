# Settings PRD

## Purpose
Settings provides a centralized place for inspectors to configure their profile, app behavior, and account management. Inspector profile data (name, initials, certification number) flows into PDF reports, form auto-fill, and daily entry headers, making accurate settings critical for document generation.

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
- Data management: backup, restore, clear cached exports
- View app version, licenses, and help/support info

## Data Model
- Primary storage: `SharedPreferences` (no SQLite table -- settings are device-local key-value pairs)
- Key preferences: `inspector_name`, `inspector_initials`, `inspector_phone`, `inspector_cert_number`, `inspector_agency`, `auto_fetch_weather`, `auto_sync_wifi`, `auto_fill_enabled`, `use_last_values`, `theme_mode`, `auto_load_last_project`
- Sync: Local Only (settings are per-device and not synced to cloud)
- Related: `personnel_types` table (managed from settings but stored in SQLite)

## User Flow
Inspectors access Settings from the bottom navigation bar. The screen is organized into collapsible sections: Appearance, Inspector Profile, Form Auto-Fill, Project, Account, Cloud Sync, PDF Export, Weather, Data, and About. Each setting is immediately persisted when changed. Profile edits use modal dialogs with save/cancel. Personnel types management navigates to a dedicated sub-screen.

## Offline Behavior
Fully functional offline. All settings are stored locally in SharedPreferences and read synchronously. The sync section shows cached status and pending count from local SQLite. Sign out clears local session data. Backup/restore features (planned Phase 6) will operate on local files.

## Dependencies
- Features: auth (sign out, email display), sync (sync status, manual trigger), projects (auto-load setting)
- Packages: `shared_preferences`, `provider`, `supabase_flutter` (auth state)

## Owner Agent
frontend-flutter-specialist-agent (all presentation), backend-data-layer-agent (PreferencesService)
