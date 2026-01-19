# AASHTOWare OpenAPI Integration Plan

**Created**: 2026-01-17
**Status**: READY FOR IMPLEMENTATION
**Timeline**: 12-16 weeks (Phases 8-15 in production roadmap)
**Priority**: Work on AASHTOWare phases until blocked by external dependencies, then continue existing Phase 1-7 work

---

## Priority Strategy

Since AASHTOWare integration depends on external factors (MILogin registration, Alliance Program application, MDOT sandbox access), we'll use this approach:

1. **Start Phase 8** (Foundation) immediately - no external dependencies
2. **Start Phase 9** (Data Model) - no external dependencies
3. **Start Phase 10** (API Client) - can build against OpenAPI spec
4. **Initiate external contacts** during Phases 8-10:
   - Contact Michigan DTMB for MILogin OAuth2 registration
   - Contact AASHTOWare Alliance Program Manager
   - Request MDOT sandbox/test environment access
5. **When blocked** waiting for responses, continue existing work:
   - Phase 1: Code Quality (DRY violations, dead code)
   - Phase 3-7: Performance, UI, Testing, Security, Deployment
6. **Resume AASHTOWare** when external dependencies are resolved

This dual-track approach ensures continuous progress regardless of external timelines.

---

## Overview

Integrate the Construction Inspector App with Michigan DOT's AASHTOWare Project Construction & Materials (APCM) system via the AASHTOWare OpenAPI. The app will support **dual-mode operation**:

- **Local Agency Mode** (Current): Supabase backend for in-house projects
- **MDOT Mode** (New): AASHTOWare OpenAPI for official MDOT contracts

**Key Deadline**: All API access must use AASHTOWare OpenAPI by December 2029 (legacy connections sunset).

---

## Current State Analysis

### Data Model Compatibility: 65%

| Category | Status | Gaps |
|----------|--------|------|
| General Tab | ✓ Mostly present | Missing `rainfall_amount` |
| Contractors | ✓ Present | Missing address, license fields |
| Personnel | ⚠ Partial | Missing `hours_worked`, `decision_class` |
| Equipment | ⚠ Partial | Missing `hours_used`, `idle_hours` |
| Work Items | ✓ Complete | All fields present |
| Photos | ✓ Complete | GPS, captions present |
| Documents | ✗ Missing | Only photos, no PDF/XLS attachments |

### Authentication: Not Ready

- Current: Supabase email/password only
- Needed: OAuth2/OIDC with Michigan MILogin + MFA
- No secure token storage (relies on Supabase SDK)
- No subscription key management

### Sync Architecture: Foundation Ready

- SQLite offline-first with 12-table schema (v7)
- Queue-based sync with debounced push/pull
- Connectivity monitoring with automatic retry
- Needs abstraction layer for dual-backend routing

---

## Architecture Design

### Dual-Mode Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Construction Inspector App                    │
├─────────────────────────────────────────────────────────────────┤
│  Project Mode: [Local Agency] or [MDOT]                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    SyncOrchestrator                       │   │
│  │  Routes sync based on project.mode                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                             │                                    │
│              ┌──────────────┴──────────────┐                    │
│              ▼                             ▼                    │
│  ┌─────────────────────┐    ┌─────────────────────────────┐    │
│  │ SupabaseSyncAdapter │    │ AASHTOWareSyncAdapter       │    │
│  │ (Current logic)     │    │ + AASHTOWareApiClient       │    │
│  │                     │    │ + AASHTOWareFieldMapper     │    │
│  └──────────┬──────────┘    └──────────────┬──────────────┘    │
│             │                              │                    │
│             ▼                              ▼                    │
│  ┌─────────────────────┐    ┌─────────────────────────────┐    │
│  │   Supabase Cloud    │    │ AASHTOWare OpenAPI Gateway  │    │
│  │   (Local Agency)    │    │ via MILogin OAuth2          │    │
│  └─────────────────────┘    └─────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
LOCAL AGENCY MODE                    MDOT MODE
─────────────────                    ─────────
Email/Password                       MILogin OAuth2 + MFA
      │                                    │
      ▼                                    ▼
Supabase Auth                        PKCE Authorization Flow
      │                                    │
      ▼                                    ▼
Session Token                        Access Token + Refresh Token
(Supabase SDK manages)               (SecureStorageService)
      │                                    │
      ▼                                    ▼
Supabase API                         AASHTOWare OpenAPI
                                     + Subscription Key Header
```

---

## Implementation Phases

### Phase 8: Foundation (Weeks 1-2)
**Risk: Low | Dependencies: None**

#### 8.1 Project Mode Infrastructure
- [ ] Create `ProjectMode` enum (`localAgency`, `mdot`)
- [ ] Add `mode` column to projects table (migration v8)
- [ ] Add MDOT fields to Project model:
  - `mdotContractId` - AASHTOWare contract reference
  - `mdotProjectCode` - MDOT project code
  - `mdotCounty`, `mdotDistrict` - Location info
- [ ] Update `ProjectSetupScreen` with mode selector

**Files to Create/Modify:**
```
lib/data/models/project_mode.dart (new)
lib/data/models/project.dart (modify)
lib/services/database_service.dart (migration v8)
lib/presentation/screens/project/project_setup_screen.dart
```

#### 8.2 Secure Storage Service
- [ ] Add `flutter_secure_storage: ^9.0.0` to pubspec.yaml
- [ ] Create `SecureStorageService` for tokens/keys
- [ ] Platform-specific configuration (Android/iOS/Windows)

**Files to Create:**
```
lib/services/secure_storage_service.dart
```

#### 8.3 Sync Abstraction Layer
- [ ] Create `SyncAdapter` interface
- [ ] Wrap existing SyncService as `SupabaseSyncAdapter`
- [ ] Create `SyncOrchestrator` (routes based on project.mode)
- [ ] Update providers to use SyncOrchestrator

**Files to Create:**
```
lib/services/sync/sync_adapter.dart
lib/services/sync/supabase_sync_adapter.dart
lib/services/sync/sync_orchestrator.dart
```

---

### Phase 9: Data Model Extensions (Weeks 3-4)
**Risk: Low-Medium | Dependencies: Phase 8**

#### 9.1 AASHTOWare DWR Compliance Fields
- [ ] Add to `DailyEntry`:
  - `rainfallAmount` (REAL) - Precipitation in inches
  - `decisionClass` (TEXT) - DWR decision code (W/N/etc.)
  - `mdotDwrId` (TEXT) - AASHTOWare DWR reference
  - `mdotSubmittedAt` (TEXT) - When submitted to MDOT
- [ ] Add to `entry_personnel_counts`:
  - `hoursWorked` (REAL) - Hours per personnel type
- [ ] Add to `entry_equipment`:
  - `hoursUsed` (REAL) - Equipment operating hours
  - `idleHours` (REAL) - Equipment idle hours
- [ ] Add to `contractors`:
  - `address`, `city`, `state`, `zipCode` (TEXT)
  - `licenseNumber` (TEXT)
  - `dbeStatus` (TEXT) - Disadvantaged Business Enterprise

**Database Migration v8 (continuation):**
```sql
ALTER TABLE daily_entries ADD COLUMN rainfall_amount REAL;
ALTER TABLE daily_entries ADD COLUMN decision_class TEXT;
ALTER TABLE daily_entries ADD COLUMN mdot_dwr_id TEXT;
ALTER TABLE daily_entries ADD COLUMN mdot_submitted_at TEXT;
ALTER TABLE entry_personnel_counts ADD COLUMN hours_worked REAL;
ALTER TABLE entry_equipment ADD COLUMN hours_used REAL;
ALTER TABLE entry_equipment ADD COLUMN idle_hours REAL;
ALTER TABLE contractors ADD COLUMN address TEXT;
ALTER TABLE contractors ADD COLUMN city TEXT;
ALTER TABLE contractors ADD COLUMN state TEXT;
ALTER TABLE contractors ADD COLUMN zip_code TEXT;
ALTER TABLE contractors ADD COLUMN license_number TEXT;
ALTER TABLE contractors ADD COLUMN dbe_status TEXT;
```

#### 9.2 Document Attachments Table
- [ ] Create `Document` model (PDF/XLS support)
- [ ] Create `documents` table
- [ ] Create `DocumentLocalDatasource`
- [ ] Create `DocumentRepository`
- [ ] Create `DocumentProvider`
- [ ] Add document picker to entry wizard

**Files to Create:**
```
lib/data/models/document.dart
lib/data/datasources/local/document_local_datasource.dart
lib/data/repositories/document_repository.dart
lib/presentation/providers/document_provider.dart
```

---

### Phase 10: AASHTOWare API Client (Weeks 5-7)
**Risk: Medium | Dependencies: Phase 8**

#### 10.1 API Client Infrastructure
- [ ] Create `AASHTOWareApiClient` with all endpoints:
  - DWR CRUD operations
  - Pay item operations
  - Contractor operations
- [ ] Implement rate limiter (60 req/min)
- [ ] Implement exponential backoff retry policy
- [ ] Create custom exception classes

**Files to Create:**
```
lib/services/api/aashtoware_api_client.dart
lib/services/api/api_rate_limiter.dart
lib/services/api/retry_policy.dart
lib/services/api/aashtoware_exceptions.dart
lib/core/config/aashtoware_config.dart
```

#### 10.2 Field Mapping Layer
- [ ] Create `AASHTOWareFieldMapper`:
  - `entryToDwr()` - Local → AASHTOWare
  - `dwrToEntry()` - AASHTOWare → Local
  - Weather condition mapping
  - Personnel type mapping
  - Equipment mapping
- [ ] Validate against AASHTOWare JSON schemas

**Files to Create:**
```
lib/services/sync/aashtoware_field_mapper.dart
```

#### 10.3 AASHTOWare Sync Adapter
- [ ] Implement `SyncAdapter` interface
- [ ] Push entries to DWR endpoint
- [ ] Pull DWRs to local entries
- [ ] Handle sync status updates
- [ ] Integrate with SyncOrchestrator

**Files to Create:**
```
lib/services/sync/aashtoware_sync_adapter.dart
```

---

### Phase 11: MILogin OAuth2 (Weeks 8-12)
**Risk: HIGH | Dependencies: Phases 8, 10**

> **Critical Path**: This is the highest-risk phase. Michigan MILogin requires PKCE OAuth2 flow with mandatory MFA. Budget 2-3 week buffer.

#### 11.1 Pre-requisites (External)
- [ ] Register app with Michigan MILogin (get client_id)
- [ ] Obtain client_secret via secure channel
- [ ] Request AASHTOWare API access (get subscription key)
- [ ] Get access to MDOT sandbox/test environment

#### 11.2 OAuth2 Infrastructure
- [ ] Create `MILoginAuthService`:
  - PKCE code challenge generation
  - Authorization URL builder
  - Token exchange (`code` → `access_token`)
  - Token refresh logic
  - Userinfo endpoint integration
- [ ] Create `OAuthCredentials` model
- [ ] Update deep link handler for `oauth-callback`
- [ ] Add MILogin scheme to AndroidManifest.xml

**Files to Create:**
```
lib/services/auth/milogin_auth_service.dart
lib/services/auth/oauth_credentials.dart
android/app/src/main/AndroidManifest.xml (modify intent-filter)
```

#### 11.3 Auth Manager
- [ ] Create `AuthManager` for parallel providers:
  - `getAuthType()` - Supabase or MILogin
  - `getCurrentSession()` - Mode-aware session
  - `logout()` - Mode-aware logout
- [ ] Update `AuthProvider` to use AuthManager
- [ ] Update route guards for dual-mode

**Files to Create/Modify:**
```
lib/services/auth/auth_manager.dart
lib/presentation/providers/auth_provider.dart (modify)
lib/core/router/app_router.dart (modify)
```

#### 11.4 MILogin UI
- [ ] Create `MILoginSettingsScreen`:
  - Connect/disconnect MILogin account
  - Display connection status
  - Subscription key input (secure)
- [ ] Add to Settings navigation

**Files to Create:**
```
lib/presentation/screens/settings/milogin_settings_screen.dart
lib/presentation/widgets/milogin_status_widget.dart
```

---

### Phase 12: UI Integration (Weeks 13-14)
**Risk: Low | Dependencies: Phases 8-11**

#### 12.1 Project Setup Mode Selection
- [ ] Add mode dropdown to `ProjectSetupScreen`
- [ ] Conditional MDOT fields (contract ID, county, district)
- [ ] Mode indicator badge in project list/dashboard
- [ ] Create `ModeIndicatorWidget`

#### 12.2 Entry Wizard MDOT Features
- [ ] Conditional hours input for personnel (MDOT only)
- [ ] Conditional hours input for equipment (MDOT only)
- [ ] Rainfall amount field
- [ ] Decision class selector (W/N/etc.)
- [ ] Document attachment picker

#### 12.3 Settings Screen Updates
- [ ] MILogin connection section
- [ ] Subscription key management
- [ ] Per-mode sync status display
- [ ] Help/documentation links

**Files to Modify:**
```
lib/presentation/screens/project/project_setup_screen.dart
lib/presentation/screens/entry_wizard/entry_wizard_screen.dart
lib/presentation/screens/settings/settings_screen.dart
lib/presentation/widgets/mode_indicator.dart (new)
```

---

### Phase 13: Alliance Program Application (Weeks 14-16)
**Risk: Medium | Dependencies: Phases 8-12 complete**

> **Business Requirement**: To officially integrate with AASHTOWare, you must apply for Data Alliance status.

#### 13.1 Alliance Program Steps
- [ ] Contact Shakita Battle-Morrow (sbattlemorrow@aashto.org)
- [ ] Complete Data Alliance application
- [ ] Demonstrate product to AASHTO (requires working prototype)
- [ ] Obtain official API access and marketing guidelines
- [ ] Budget for annual fees ($12,000-$18,000 for enhanced/premium access)

#### 13.2 MDOT-Specific Configuration
- [ ] Apply Special Provision 20SP-101A-01 terminology:
  - "Inspector's Daily Report (IDR)" → "Daily Work Report (DWR)"
  - "Contract Modification" → "Change Order"
- [ ] Configure MDOT-specific roles (INSPECTOR, MDOT_OFFICETECH, etc.)
- [ ] Validate against MDOT Form 5638 requirements

---

### Phase 14: Testing & Polish (Weeks 15-16)
**Risk: Medium | Dependencies: All prior phases**

#### 14.1 Integration Testing
- [ ] Test sync to both backends simultaneously
- [ ] Test auth flow switching (Supabase ↔ MILogin)
- [ ] Test field mapping accuracy with real DWR data
- [ ] Test offline → online sync for MDOT projects

#### 14.2 Error Handling
- [ ] User-friendly error messages for API failures
- [ ] Offline fallback behaviors for MDOT mode
- [ ] Token expiry handling and refresh
- [ ] Rate limit exceeded handling

#### 14.3 Security Hardening
- [ ] Audit token storage implementation
- [ ] Verify subscription key not in logs/analytics
- [ ] Test MFA requirement enforcement
- [ ] Validate HTTPS everywhere

---

### Phase 15: Documentation & Deployment (Week 17)
**Risk: Low | Dependencies: Phase 14**

- [ ] Update CLAUDE.md with MDOT integration docs
- [ ] Create MDOT Setup Guide for end users
- [ ] Update project-status.md
- [ ] Run `flutter analyze` and fix any issues
- [ ] Run all tests (target: 300+ tests passing)
- [ ] Build release APK/Windows installer

---

## Key Files Summary

| File | Purpose |
|------|---------|
| `lib/data/models/project_mode.dart` | Enum: localAgency, mdot |
| `lib/services/sync/sync_orchestrator.dart` | Routes sync to correct backend |
| `lib/services/auth/auth_manager.dart` | Manages parallel auth providers |
| `lib/services/auth/milogin_auth_service.dart` | OAuth2 PKCE with MILogin |
| `lib/services/api/aashtoware_api_client.dart` | HTTP client for OpenAPI |
| `lib/services/sync/aashtoware_field_mapper.dart` | Local ↔ AASHTOWare transformations |
| `lib/services/sync/aashtoware_sync_adapter.dart` | Sync implementation for MDOT |
| `lib/services/secure_storage_service.dart` | Secure token/key storage |

---

## Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|------------|
| MILogin OAuth2 complexity | HIGH | 2-3 week buffer, OAuth2 test harness |
| AASHTOWare API schema mismatch | MEDIUM | Sandbox testing, comprehensive mapper tests |
| Alliance Program approval delay | MEDIUM | Start application early (Phase 13 parallel) |
| Token refresh edge cases | MEDIUM | Detailed logging, background refresh task |
| Data migration issues | LOW | Nullable fields, tested migration scripts |

---

## Estimated Timeline

| Phase | Weeks | Status |
|-------|-------|--------|
| Phase 8: Foundation | 1-2 | Not Started |
| Phase 9: Data Model | 3-4 | Not Started |
| Phase 10: API Client | 5-7 | Not Started |
| Phase 11: MILogin OAuth2 | 8-12 | Not Started |
| Phase 12: UI Integration | 13-14 | Not Started |
| Phase 13: Alliance Program | 14-16 | Not Started |
| Phase 14: Testing | 15-16 | Not Started |
| Phase 15: Documentation | 17 | Not Started |

**Total: 12-17 weeks** (depending on Alliance Program timing)

---

## Verification Steps

1. **Unit Tests**: Add tests for field mapper, API client, sync adapters
2. **Integration Tests**: Test dual-mode sync with mock backends
3. **Manual Testing**:
   - Create Local Agency project, verify Supabase sync
   - Create MDOT project, verify AASHTOWare sync (sandbox)
   - Test offline mode for both
   - Test mode switching within app
4. **Security Audit**: Verify token storage, API key handling
5. **Build Verification**: `flutter analyze`, `flutter test`, release builds

---

## Dependencies to Add (pubspec.yaml)

```yaml
dependencies:
  # Secure storage for tokens
  flutter_secure_storage: ^9.0.0
```

---

## External Dependencies (Initiate Early!)

These should be initiated during Phase 8-10 to minimize blocking time:

| Dependency | Contact | Action |
|------------|---------|--------|
| MILogin Registration | Michigan DTMB | Request OAuth2 client_id for app |
| Alliance Program | Shakita Battle-Morrow (sbattlemorrow@aashto.org) | Explore Data Alliance vs Direct Integration |
| MDOT Sandbox | MDOT AASHTOWare Wiki team | Request test environment access |
| Subscription Key | AASHTOWare Developer Portal | Register at developer.aashtoware.org |

**Lead Time Estimates:**
- MILogin registration: 2-4 weeks
- Alliance Program: 4-8 weeks for initial approval
- Sandbox access: 1-2 weeks
- Developer portal: Same-day (self-service)

---

## Notes

- This plan preserves ALL existing Local Agency functionality
- MDOT mode is additive, not a replacement
- Existing projects default to `localAgency` mode
- Alliance Program application can run parallel to development
- December 2029 is the hard deadline for legacy connection sunset
