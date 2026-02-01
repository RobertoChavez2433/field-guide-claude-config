# AASHTOWare OpenAPI Integration Plan

**Created**: 2026-01-19
**Status**: READY FOR IMPLEMENTATION
**Timeline**: 12-17 weeks (Phases 9-15)
**Priority**: Begin when ready, work until blocked by external dependencies

---

## Executive Summary

Integrate the Construction Inspector App with Michigan DOT's AASHTOWare Project Construction & Materials (APCM) system via the AASHTOWare OpenAPI. The app will support **dual-mode operation**:

- **Local Agency Mode** (Current): Supabase backend for in-house projects
- **MDOT Mode** (New): AASHTOWare OpenAPI for official MDOT contracts

**Critical Deadline**: December 2029 - All API access must use AASHTOWare OpenAPI (legacy connections sunset)

---

## Key Information from Research

| Topic | Key Information |
|-------|-----------------|
| **Deadline** | December 2029 - all API access requires OpenAPI (legacy sunset) |
| **Authentication** | MILogin OAuth2/OIDC with mandatory MFA (at least once daily) |
| **MDOT Provision** | Special Provision 20SP-101A-01 - electronic-only workflows |
| **Alliance Program** | Data Alliance path required for third-party integration |
| **Annual Costs** | Non-member: $12,000 (Enhanced) to $18,000 (Premium) |
| **DWR Components** | General, Contractors, Personnel, Equipment, Work Items, Attachments |
| **Offline Requirement** | PWA or native app with local storage mandatory |
| **Terminology** | IDR -> DWR, Contract Modification -> Change Order |

---

## Current State Assessment

### Feature-First Reorganization: COMPLETE
The codebase has been reorganized into 12 feature modules:
- auth, projects, locations, contractors, quantities, entries
- photos, pdf, sync, dashboard, settings, weather

### Data Model Compatibility: 65%

| Category | Status | Gaps |
|----------|--------|------|
| General Tab | Mostly present | Missing `rainfall_amount` |
| Contractors | Present | Missing address, license fields |
| Personnel | Partial | Missing `hours_worked`, `decision_class` |
| Equipment | Partial | Missing `hours_used`, `idle_hours` |
| Work Items | Complete | All fields present |
| Photos | Complete | GPS, captions present |
| Documents | Missing | Only photos, no PDF/XLS attachments |

### Authentication: Not Ready
- Current: Supabase email/password only
- Needed: OAuth2/OIDC with Michigan MILogin + MFA
- No secure token storage (relies on Supabase SDK)
- No subscription key management

### Sync Architecture: Foundation Ready
- SQLite offline-first with 12-table schema (v7)
- Queue-based sync with debounced push/pull
- Connectivity monitoring with automatic retry
- SyncOrchestrator ready for dual-backend routing

---

## Architecture Design

### Dual-Mode Data Flow

```
+------------------------------------------------------------------+
|                    Construction Inspector App                     |
+------------------------------------------------------------------+
|  Project Mode: [Local Agency] or [MDOT]                          |
+------------------------------------------------------------------+
|                                                                   |
|  +-----------------------------------------------------------+   |
|  |                    SyncOrchestrator                        |   |
|  |  Routes sync based on project.mode                         |   |
|  +-----------------------------------------------------------+   |
|                             |                                     |
|              +--------------+--------------+                      |
|              v                             v                      |
|  +---------------------+    +-----------------------------+       |
|  | SupabaseSyncAdapter |    | AASHTOWareSyncAdapter       |       |
|  | (Current logic)     |    | + AASHTOWareApiClient       |       |
|  |                     |    | + AASHTOWareFieldMapper     |       |
|  +----------+----------+    +--------------+--------------+       |
|             |                              |                      |
|             v                              v                      |
|  +---------------------+    +-----------------------------+       |
|  |   Supabase Cloud    |    | AASHTOWare OpenAPI Gateway  |       |
|  |   (Local Agency)    |    | via MILogin OAuth2          |       |
|  +---------------------+    +-----------------------------+       |
|                                                                   |
+-------------------------------------------------------------------+
```

### Authentication Flow

```
LOCAL AGENCY MODE                    MDOT MODE
-----------------                    ---------
Email/Password                       MILogin OAuth2 + MFA
      |                                    |
      v                                    v
Supabase Auth                        PKCE Authorization Flow
      |                                    |
      v                                    v
Session Token                        Access Token + Refresh Token
(Supabase SDK manages)               (SecureStorageService)
      |                                    |
      v                                    v
Supabase API                         AASHTOWare OpenAPI
                                     + Subscription Key Header
```

---

## Implementation Phases

### Phase 9: Data Model Extensions
**Risk: Low-Medium | Dependencies: None**

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

**Database Migration v8:**
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
lib/features/documents/
  data/
    models/document.dart
    datasources/local/document_local_datasource.dart
    repositories/document_repository.dart
  presentation/
    providers/document_provider.dart
```

---

### Phase 10: AASHTOWare API Client
**Risk: Medium | Dependencies: Phase 9**

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
lib/features/sync/data/api/
  aashtoware_api_client.dart
  api_rate_limiter.dart
  retry_policy.dart
  aashtoware_exceptions.dart
lib/core/config/aashtoware_config.dart
```

#### 10.2 Field Mapping Layer
- [ ] Create `AASHTOWareFieldMapper`:
  - `entryToDwr()` - Local -> AASHTOWare
  - `dwrToEntry()` - AASHTOWare -> Local
  - Weather condition mapping
  - Personnel type mapping
  - Equipment mapping
- [ ] Validate against AASHTOWare JSON schemas

**Files to Create:**
```
lib/features/sync/data/mappers/aashtoware_field_mapper.dart
```

#### 10.3 AASHTOWare Sync Adapter
- [ ] Implement `SyncAdapter` interface
- [ ] Push entries to DWR endpoint
- [ ] Pull DWRs to local entries
- [ ] Handle sync status updates
- [ ] Integrate with SyncOrchestrator

**Files to Create:**
```
lib/features/sync/data/adapters/aashtoware_sync_adapter.dart
```

---

### Phase 11: MILogin OAuth2 (HIGH RISK)
**Risk: HIGH | Dependencies: Phases 9, 10**

> **Critical Path**: Michigan MILogin requires PKCE OAuth2 flow with mandatory MFA. Budget 2-3 week buffer.

#### 11.1 Pre-requisites (External)
- [ ] Register app with Michigan MILogin (get client_id)
- [ ] Obtain client_secret via secure channel
- [ ] Request AASHTOWare API access (get subscription key)
- [ ] Get access to MDOT sandbox/test environment

#### 11.2 Project Mode Infrastructure
- [ ] Create `ProjectMode` enum (`localAgency`, `mdot`)
- [ ] Add `mode` column to projects table (migration v8)
- [ ] Add MDOT fields to Project model:
  - `mdotContractId` - AASHTOWare contract reference
  - `mdotProjectCode` - MDOT project code
  - `mdotCounty`, `mdotDistrict` - Location info
- [ ] Update `ProjectSetupScreen` with mode selector

**Files to Create/Modify:**
```
lib/features/projects/data/models/project_mode.dart (new)
lib/features/projects/data/models/project.dart (modify)
lib/core/database/database_service.dart (migration v8)
lib/features/projects/presentation/screens/project_setup_screen.dart
```

#### 11.3 Secure Storage Service
- [ ] Add `flutter_secure_storage: ^9.0.0` to pubspec.yaml
- [ ] Create `SecureStorageService` for tokens/keys
- [ ] Platform-specific configuration (Android/iOS/Windows)

**Files to Create:**
```
lib/services/secure_storage_service.dart
```

#### 11.4 OAuth2 Infrastructure
- [ ] Create `MILoginAuthService`:
  - PKCE code challenge generation
  - Authorization URL builder
  - Token exchange (`code` -> `access_token`)
  - Token refresh logic
  - Userinfo endpoint integration
- [ ] Create `OAuthCredentials` model
- [ ] Update deep link handler for `oauth-callback`
- [ ] Add MILogin scheme to AndroidManifest.xml

**Files to Create:**
```
lib/features/auth/services/milogin_auth_service.dart
lib/features/auth/data/models/oauth_credentials.dart
android/app/src/main/AndroidManifest.xml (modify intent-filter)
```

#### 11.5 Auth Manager
- [ ] Create `AuthManager` for parallel providers:
  - `getAuthType()` - Supabase or MILogin
  - `getCurrentSession()` - Mode-aware session
  - `logout()` - Mode-aware logout
- [ ] Update `AuthProvider` to use AuthManager
- [ ] Update route guards for dual-mode

**Files to Create/Modify:**
```
lib/features/auth/services/auth_manager.dart
lib/features/auth/presentation/providers/auth_provider.dart (modify)
lib/core/router/app_router.dart (modify)
```

---

### Phase 12: UI Integration
**Risk: Low | Dependencies: Phases 9-11**

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
lib/features/projects/presentation/screens/project_setup_screen.dart
lib/features/entries/presentation/screens/entry_wizard_screen.dart
lib/features/settings/presentation/screens/settings_screen.dart
lib/shared/widgets/mode_indicator.dart (new)
```

---

### Phase 13: Alliance Program Application
**Risk: Medium | Dependencies: Phases 9-12 complete**

> **Business Requirement**: To officially integrate with AASHTOWare, you must apply for Data Alliance status.

#### 13.1 Alliance Program Steps
- [ ] Contact Shakita Battle-Morrow (sbattlemorrow@aashto.org)
- [ ] Complete Data Alliance application
- [ ] Demonstrate product to AASHTO (requires working prototype)
- [ ] Obtain official API access and marketing guidelines
- [ ] Budget for annual fees ($12,000-$18,000 for enhanced/premium access)

#### 13.2 MDOT-Specific Configuration
- [ ] Apply Special Provision 20SP-101A-01 terminology:
  - "Inspector's Daily Report (IDR)" -> "Daily Work Report (DWR)"
  - "Contract Modification" -> "Change Order"
- [ ] Configure MDOT-specific roles (INSPECTOR, MDOT_OFFICETECH, etc.)
- [ ] Validate against MDOT Form 5638 requirements

---

### Phase 14: Testing & Polish
**Risk: Medium | Dependencies: All prior phases**

#### 14.1 Integration Testing
- [ ] Test sync to both backends simultaneously
- [ ] Test auth flow switching (Supabase <-> MILogin)
- [ ] Test field mapping accuracy with real DWR data
- [ ] Test offline -> online sync for MDOT projects

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

### Phase 15: Documentation & Deployment
**Risk: Low | Dependencies: Phase 14**

- [ ] Update CLAUDE.md with MDOT integration docs
- [ ] Create MDOT Setup Guide for end users
- [ ] Update project-status.md
- [ ] Run `flutter analyze` and fix any issues
- [ ] Run all tests (target: 400+ tests passing)
- [ ] Build release APK/Windows installer

---

## External Dependency Timeline

These should be initiated during Phase 9-10 to minimize blocking time:

| Dependency | Contact | Action | Lead Time |
|------------|---------|--------|-----------|
| MILogin Registration | Michigan DTMB | Request OAuth2 client_id for app | 2-4 weeks |
| Alliance Program | Shakita Battle-Morrow (sbattlemorrow@aashto.org) | Explore Data Alliance vs Direct Integration | 4-8 weeks |
| MDOT Sandbox | MDOT AASHTOWare Wiki team | Request test environment access | 1-2 weeks |
| Subscription Key | AASHTOWare Developer Portal | Register at developer.aashtoware.org | Same-day (self-service) |

---

## Risk Mitigation Strategies

| Risk | Severity | Mitigation |
|------|----------|------------|
| MILogin OAuth2 complexity | HIGH | 2-3 week buffer, OAuth2 test harness |
| AASHTOWare API schema mismatch | MEDIUM | Sandbox testing, comprehensive mapper tests |
| Alliance Program approval delay | MEDIUM | Start application early (Phase 13 parallel) |
| Token refresh edge cases | MEDIUM | Detailed logging, background refresh task |
| Data migration issues | LOW | Nullable fields, tested migration scripts |

---

## MDOT-Specific Requirements (SP 20SP-101A-01)

### Terminology Mapping

| App Term | MDOT/AASHTOWare Term |
|----------|---------------------|
| Inspector's Daily Report (IDR) | Daily Work Report (DWR) |
| Contract Modification | Change Order |
| Bid Item | Pay Item |
| Entry | DWR |

### Required Fields for MDOT Projects
- Rainfall amount (inches)
- Decision class code
- Personnel hours worked
- Equipment hours used/idle
- DBE status for contractors
- Document attachments (PDF/XLS)

### Workflow Requirements
- Electronic-only submissions (no paper)
- MFA required at least once daily
- Real-time or near-real-time sync to AASHTOWare

---

## Key Files Summary

| File | Purpose |
|------|---------|
| `lib/features/projects/data/models/project_mode.dart` | Enum: localAgency, mdot |
| `lib/features/sync/application/sync_orchestrator.dart` | Routes sync to correct backend |
| `lib/features/auth/services/auth_manager.dart` | Manages parallel auth providers |
| `lib/features/auth/services/milogin_auth_service.dart` | OAuth2 PKCE with MILogin |
| `lib/features/sync/data/api/aashtoware_api_client.dart` | HTTP client for OpenAPI |
| `lib/features/sync/data/mappers/aashtoware_field_mapper.dart` | Local <-> AASHTOWare transformations |
| `lib/features/sync/data/adapters/aashtoware_sync_adapter.dart` | Sync implementation for MDOT |
| `lib/services/secure_storage_service.dart` | Secure token/key storage |

---

## Dependencies to Add (pubspec.yaml)

```yaml
dependencies:
  # Secure storage for tokens
  flutter_secure_storage: ^9.0.0
```

---

## Verification Checklist

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

## Estimated Timeline

| Phase | Weeks | Status |
|-------|-------|--------|
| Phase 9: Data Model Extensions | 1-2 | Not Started |
| Phase 10: API Client | 3-5 | Not Started |
| Phase 11: MILogin OAuth2 | 6-10 | Not Started |
| Phase 12: UI Integration | 11-12 | Not Started |
| Phase 13: Alliance Program | 12-14 | Not Started |
| Phase 14: Testing | 14-16 | Not Started |
| Phase 15: Documentation | 17 | Not Started |

**Total: 12-17 weeks** (depending on Alliance Program timing)

---

## Notes

- This plan preserves ALL existing Local Agency functionality
- MDOT mode is additive, not a replacement
- Existing projects default to `localAgency` mode
- Alliance Program application can run parallel to development
- December 2029 is the hard deadline for legacy connection sunset
