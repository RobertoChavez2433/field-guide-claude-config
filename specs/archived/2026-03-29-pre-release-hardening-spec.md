# Pre-Release Hardening Spec

**Date:** 2026-03-29
**Status:** Approved
**Approach:** Unified Integration (all 5 items coordinated with shared consent layer)
**Platforms:** Android, iOS, Windows

---

## Overview

### Purpose
Add pre-release hardening infrastructure to the Field Guide app: legal compliance (ToS/Privacy Policy with consent management), crash reporting (Sentry), anonymous usage analytics (Aptabase), production release signing (Android + iOS project setup), and a polished About/Support section. All integrated through a unified consent-aware initialization flow.

### Scope

**Included:**
- ToS & Privacy Policy (AI-drafted, hosted on GitHub Pages + bundled as markdown for offline)
- Sentry crash reporting (Android, iOS, Windows)
- Aptabase anonymous analytics (Android, iOS, Windows)
- Android release signing (keystore + gradle config)
- iOS project directory creation (signing deferred until Apple Developer account)
- About screen overhaul (version + build number, polished licenses, legal links, support form with log attachment)
- Consent flow: registration checkbox + first-launch gate + re-consent on policy updates
- Supabase `support_tickets` table + `support-logs` Storage bucket

**Excluded:**
- Lawyer review of legal text (AI draft for now)
- Apple Developer account setup / iOS signing
- Play Store / App Store submission
- Deep product analytics (funnels, cohorts, retention)
- Account deletion feature (Apple requirement — deferred to pre-submission)
- Granular opt-in/out toggles for analytics/crash reporting (all-or-nothing consent for now)

### Success Criteria
- App cannot be used without accepting ToS/Privacy Policy on first launch
- Policy version changes trigger re-consent blocking screen
- Crashes on all 3 platforms automatically report to Sentry with PII scrubbed
- Feature usage events track anonymously via Aptabase
- Consent gates Sentry + Aptabase — neither initializes without acceptance
- Release builds sign with production keystore (Android)
- iOS project directory exists and builds
- About section shows version + build number, polished licenses, legal links, and working support form with log attachment

---

## Data Model

### New Table: `user_consent_records`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | String (UUID) | Yes | Primary key |
| user_id | String (UUID) | Yes | FK to auth.users |
| policy_type | String | Yes | `privacy_policy` or `terms_of_service` |
| policy_version | String | Yes | Semver (e.g., "1.0.0") |
| accepted_at | DateTime | Yes | UTC timestamp of acceptance |
| app_version | String | Yes | App version when accepted |

**RLS:** INSERT + SELECT own records only. No UPDATE or DELETE — consent records are immutable for audit compliance.
**Sync:** Local SQLite → Supabase. Upload only (never download consent records back to device).

### New Table: `support_tickets`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | String (UUID) | Yes | Primary key |
| user_id | String (UUID) | Yes | FK to auth.users |
| subject | String | No | Category (Bug Report, Feature Request, General Feedback, Other) |
| message | String | Yes | User's feedback text |
| app_version | String | Yes | App version at time of submission |
| platform | String | Yes | android/ios/windows |
| log_file_path | String | No | Path in Supabase Storage bucket if logs attached |
| created_at | DateTime | Yes | UTC timestamp |
| status | String | Yes | `open`, `acknowledged`, `resolved` |

**RLS:** INSERT + SELECT own records only. Status updates from admin side (future).

### Supabase Storage
- New bucket: `support-logs` — for uploaded log file attachments
- RLS: authenticated users can upload. Only the ticket owner + admin can read.

### Local-Only Storage (PreferencesService)

| Key | Type | Description |
|-----|------|-------------|
| `consent_accepted` | bool | Has user accepted current policy version |
| `consent_policy_version` | String | Last accepted version (for re-consent check) |

### No Changes to Existing Tables

---

## User Flow

### First Launch / New User
```
App Launch → Check consent_accepted + consent_policy_version
    ↓
No consent or outdated version?
    ↓ yes                              ↓ no
Consent Screen                     Normal app flow
(ToS + Privacy summary,
 "I Accept" button)
    ↓ tap accept
Store consent records (2 rows)
Store prefs (consent_accepted, version)
    ↓
Normal app flow
```

### Registration Flow
- Checkbox on sign-up: "I agree to the Terms of Service and Privacy Policy" (links open the documents)
- Cannot register without checking it
- Consent records created at registration time

### Policy Update (Existing User)
```
App Launch → consent_policy_version != current_policy_version
    ↓
Blocking consent screen
("We've updated our policies. Please review and accept to continue.")
    ↓ tap accept
New consent records inserted (immutable history)
Prefs updated with new version
    ↓
Normal app flow
```

### Support Ticket Flow
```
Settings > About > Help & Support
    ↓
Feedback form (subject dropdown, message text field)
    ↓
"Attach recent logs?" toggle
    ↓ yes                    ↓ no
Bundle last session logs     Skip
Upload to Storage bucket
    ↓
Insert support_ticket row
    ↓
Confirmation: "Thanks! We'll review your feedback."
```

### Entry Points
- **Consent screen**: automatic on launch when needed (not navigable to manually)
- **ToS / Privacy Policy**: Settings > About > Terms of Service / Privacy Policy
- **Help & Support**: Settings > About > Help & Support
- **Licenses**: Settings > About > Licenses

---

## UI Components

### Consent Screen
- Full-screen, non-dismissable (no back button, no navigation)
- App logo/name at top
- Scrollable summary of what they're agreeing to (plain language, not legalese wall)
- Links to full ToS and Privacy Policy (opens bundled markdown or web version)
- Single "I Accept" button at bottom
- Disabled until user scrolls to bottom (proves they at least saw the content)

### About Section (Enhanced — Settings Screen)
```
+----------------------------------+
| About                            |
+----------------------------------+
| Version          1.0.0 (build 3) |
| Licenses         >               |
| Terms of Service >               |
| Privacy Policy   >               |
| Help & Support   >               |
+----------------------------------+
```

### Licenses Screen (via `oss_licenses` package)
- Clean grouped list of packages
- Tap to expand license text
- Replaces current `showLicensePage()` call

### Legal Document Screen
- Renders bundled markdown via `flutter_markdown`
- "Open in browser" button in app bar to view hosted version
- Used for both ToS and Privacy Policy

### Help & Support Screen
```
+----------------------------------+
| Help & Support                   |
+----------------------------------+
| Subject    [Dropdown v]          |
|   Bug Report                     |
|   Feature Request                |
|   General Feedback               |
|   Other                          |
+----------------------------------+
| Message                          |
| [                              ] |
| [          Text field          ] |
| [                              ] |
+----------------------------------+
| [ ] Attach recent logs           |
+----------------------------------+
|        [Submit Feedback]         |
+----------------------------------+
```

### Testing Keys Required
- `consentScreen`, `consentAcceptButton`
- `aboutVersionTile`, `aboutBuildNumber`
- `aboutLicensesTile`, `aboutTosTile`, `aboutPrivacyTile`
- `aboutHelpSupportTile`
- `supportSubjectDropdown`, `supportMessageField`, `supportAttachLogs`, `supportSubmitButton`

---

## State Management

### ConsentProvider (new)
**Responsibilities:**
- Check consent status on app launch
- Compare local policy version against current version
- Show/dismiss consent screen
- Write consent records to local DB + trigger sync

**Key methods:**
```
checkConsentStatus() → ConsentStatus (accepted, needsConsent, needsReconsent)
acceptPolicies(String policyVersion) → void
getCurrentPolicyVersion() → String
```

**Data flow:**
```
App Launch → ConsentProvider.checkConsentStatus()
    → PreferencesService (quick check)
    → If outdated → show consent screen
    → On accept → Repository → SQLite + Supabase sync
```

### SupportProvider (new)
**Responsibilities:**
- Manage feedback form state
- Bundle log files for attachment
- Submit ticket to local DB + trigger sync
- Upload log files to Supabase Storage

**Key methods:**
```
submitTicket(subject, message, attachLogs) → void
getLogFiles() → List<File>
uploadLogs(ticketId) → String (storage path)
```

### No New Providers for Sentry/Aptabase
- Both initialize in `main.dart._runApp()` — no provider needed
- Sentry hooks into existing Logger (add as transport in `Logger.error()`)
- Aptabase calls are direct: `Aptabase.trackEvent('event_name')` sprinkled at key points
- Both gated by `PreferencesService.consentAccepted` — if no consent yet, neither initializes

### Existing Providers — Minor Changes
- **AppConfigProvider** — add `currentPolicyVersion` (fetched from remote config, bundled fallback)
- **SettingsProvider** — no changes, About section is stateless tiles

---

## Offline Behavior

### Consent
| Action | Offline? | Notes |
|--------|----------|-------|
| Accept policies | Yes | Stored in local SQLite + prefs immediately. Syncs to Supabase when online. |
| View ToS/Privacy | Yes | Bundled markdown always available. "Open in browser" button disabled offline. |
| Re-consent check | Yes | Compares local pref against bundled policy version. No network needed. |

### Crash Reporting (Sentry)
| Action | Offline? | Notes |
|--------|----------|-------|
| Capture crash | Yes | Written to disk immediately by Sentry SDK |
| Send to Sentry | No | Queued on disk, sent automatically when connectivity returns |

### Analytics (Aptabase)
| Action | Offline? | Notes |
|--------|----------|-------|
| Track event | Yes | Batched in memory/disk by Aptabase SDK |
| Send to Aptabase | No | Flushed when online |

### Support Tickets
| Action | Offline? | Notes |
|--------|----------|-------|
| Submit ticket | Yes | Saved to local SQLite. Syncs later. |
| Attach logs | Partial | Log files bundled locally. Upload to Supabase Storage requires connectivity. Ticket saves with a pending upload flag, uploads on next sync. |
| Confirmation | Yes | Immediate local confirmation: "Saved. Will send when online." |

### Policy Version Updates
- Current policy version is bundled in the app (fallback)
- Can also be fetched from remote config (AppConfigProvider) when online
- If remote version is newer than bundled, triggers re-consent
- If offline, uses bundled version — user won't see a remote-only policy update until they connect

No complex sync conflicts — consent records are insert-only, support tickets are insert-only, neither are edited after creation.

---

## Edge Cases

### Consent
| Scenario | Handling | UI Feedback |
|----------|----------|-------------|
| User force-closes during consent screen | No consent recorded. Screen shows again on next launch. | Same consent screen |
| User clears app data | Consent prefs wiped. Records still in Supabase. Consent screen shows again. | Re-consent flow |
| Policy version mismatch (remote newer than bundled) | Re-consent triggered with remote version | "We've updated our policies" screen |
| No network + no bundled policy file (shouldn't happen) | Fallback to hardcoded minimum version | Consent screen still functional |

### Crash Reporting
| Scenario | Handling | UI Feedback |
|----------|----------|-------------|
| Crash before consent accepted | Sentry not initialized — crash not reported | None (expected — no consent = no reporting) |
| Sentry DSN missing from .env | Sentry init silently skipped, Logger still works locally | None — degrades gracefully |
| Sentry quota exceeded (5K/month) | Sentry SDK handles rate limiting, drops events | None visible to user |

### Support Tickets
| Scenario | Handling | UI Feedback |
|----------|----------|-------------|
| Submit with empty message | Validation prevents submission | "Please enter a message" |
| Log files too large | Cap at last N session files or X MB total | "Attaching most recent logs (XMB)" |
| Upload fails (offline) | Ticket saved locally, logs queued for upload | "Saved. Logs will upload when online." |
| User submits multiple tickets rapidly | No throttle — each is a valid submission | Normal confirmation each time |

### About Screen
| Scenario | Handling | UI Feedback |
|----------|----------|-------------|
| Package info unavailable | Fallback to pubspec version string | Shows version without build number |
| "Open in browser" tapped offline | `url_launcher` fails gracefully | "No internet connection" snackbar |

---

## Testing Strategy

### Unit Tests
| Component | Test Focus | Priority |
|-----------|-----------|----------|
| ConsentProvider | Check status logic, version comparison, accept flow | HIGH |
| SupportProvider | Ticket creation, log bundling, validation | MED |
| Consent records repository | Immutable insert, correct fields populated | HIGH |
| Support tickets repository | Insert, pending upload flag | MED |

### Widget Tests
| Screen/Widget | Test Focus | Priority |
|--------------|-----------|----------|
| Consent screen | Renders, scroll-to-enable button, accept writes records, blocks navigation | HIGH |
| About section | All tiles present, version + build number display, links navigate correctly | MED |
| Legal document screen | Markdown renders, "open in browser" button present | LOW |
| Help & Support screen | Form validation, subject dropdown, attach logs toggle, submit flow | MED |
| Licenses screen | Renders package list, expand/collapse works | LOW |

### Integration Tests
- [ ] Fresh install → consent screen blocks → accept → app loads → consent records in DB
- [ ] Policy version bump → existing user sees re-consent → accept → new records inserted (old preserved)
- [ ] Support ticket submitted offline → comes online → ticket syncs → logs upload
- [ ] Sentry captures a thrown exception (verify in Sentry dashboard manually)
- [ ] Aptabase tracks event (verify in Aptabase dashboard manually)

### What NOT to Test Automatically
- Sentry/Aptabase SDK internals — trust the packages
- Actual crash scenarios on each platform — manual QA
- Legal text content — changes independently of code

---

## Security Implications

### Authentication & Authorization
- Consent screen appears before full app access — but after authentication (user must be logged in to record consent against their `user_id`)
- Support tickets tied to authenticated user — no anonymous submissions
- Sentry DSN is not a secret (client-side by design) but still stored in `.env` for consistency

### Data Exposure
| Data | Sensitivity | Protection |
|------|------------|------------|
| Consent records | Low (just timestamps + versions) | RLS: user sees own only |
| Support ticket messages | Medium (may contain project details) | RLS: user sees own only. Admin access via service role. |
| Attached log files | Medium (may contain error context) | Storage bucket RLS: uploader + admin only. PII scrubbing applied by Logger before write. |
| Sentry crash data | Medium (stack traces, device info) | PII scrubbed via `beforeSend` callback. EU data residency available. |
| Aptabase events | Low (anonymous, no PII by design) | No user identification possible |

### RLS Policies
- `user_consent_records`: INSERT + SELECT where `user_id = auth.uid()`. No UPDATE, no DELETE.
- `support_tickets`: INSERT + SELECT where `user_id = auth.uid()`. No UPDATE, no DELETE from client.
- `support-logs` bucket: INSERT where authenticated. SELECT where uploader matches `auth.uid()`.

### Sentry-Specific
- `beforeSend` callback strips PII using existing `_scrubSensitive` / `_scrubString` from Logger
- No user emails, names, or project data sent to Sentry
- User identified by anonymous UUID only (Supabase auth ID is fine — not PII itself)

### Keystore Security
- Upload keystore stored outside repo (`C:\Users\rseba\keystores\`)
- `key.properties` gitignored (already in `.gitignore`)
- Keystore password never in code or version control

---

## Migration/Cleanup

### Schema Changes
| Table | Change | Migration Strategy |
|-------|--------|-------------------|
| `user_consent_records` | New table | Supabase migration + local SQLite `CREATE TABLE IF NOT EXISTS` |
| `support_tickets` | New table | Supabase migration + local SQLite `CREATE TABLE IF NOT EXISTS` |
| `support-logs` | New Storage bucket | Create via Supabase dashboard or migration |

### New Dependencies (pubspec.yaml)
| Package | Purpose |
|---------|---------|
| `sentry_flutter` | Crash reporting |
| `aptabase_flutter` | Anonymous analytics |
| `oss_licenses_flutter` | Polished licenses screen |
| `flutter_markdown` | Render bundled legal documents |

### New Files
| File | Purpose |
|------|---------|
| `assets/legal/terms_of_service.md` | Bundled ToS text |
| `assets/legal/privacy_policy.md` | Bundled privacy policy text |
| `android/key.properties` | Signing config (gitignored) |
| `.env` additions | `SENTRY_DSN`, `APTABASE_APP_KEY` |

### Changes to Existing Files
| File | Change |
|------|--------|
| `lib/main.dart` | Add Sentry + Aptabase initialization in `_runApp()` |
| `lib/core/logging/logger.dart` | Add Sentry as third transport in `error()` method |
| `lib/core/database/database_service.dart` | Add new table schemas |
| `lib/features/settings/presentation/screens/settings_screen.dart` | Overhaul About section |
| `android/app/build.gradle.kts` | Replace debug signing with release signing config |
| `pubspec.yaml` | Add 4 new dependencies + legal assets |

### Dead Code Removal
- Remove `showLicensePage()` call from Settings screen (replaced by `oss_licenses` screen)

### iOS Project
- Run `flutter create --platforms=ios .` to generate `ios/` directory
- No signing config until Apple Developer account is ready

---

## Decisions Log

| Decision | Chosen | Rejected | Rationale |
|----------|--------|----------|-----------|
| Crash reporting | Sentry | Firebase Crashlytics, Bugsnag, Datadog | Only option with Windows desktop support |
| Analytics | Aptabase | Firebase Analytics, PostHog, Mixpanel, Amplitude, Custom Supabase | Only third-party with Windows support; privacy-first; basic analytics is sufficient |
| Legal text generation | AI draft + lawyer later | Generator service, write manually, hire lawyer now | Ship now, polish before public release |
| Legal hosting | Hybrid (web + bundled) | Web-only, bundled-only | Store compliance (needs URL) + offline access (bundled) |
| Consent model | All-or-nothing accept | Granular opt-in/out toggles | Simpler for internal rollout; add granularity before public release |
| Consent flow | Registration checkbox + first-launch gate + re-consent | Passive availability, registration only | App collects data from start; must cover new + existing users + policy updates |
| Support system | In-app form + Supabase + log attachment | Email only, external form, placeholder | Full support pipeline with diagnostic data |
| Integration approach | Unified (shared consent layer) | Independent, phased | Consent gates everything; cleaner initialization |
| Keystore storage | Local (`C:\Users\rseba\keystores\`) | Password manager, cloud storage | Simple; backed up manually |
| Licenses screen | `oss_licenses` package | Flutter built-in `showLicensePage()`, custom screen | Cleaner than default, less effort than custom |
