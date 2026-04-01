# Ground Truth

All literals verified against codebase on 2026-03-31.

## Route Paths (from `lib/core/router/app_router.dart`)

| Route Path | Name | Line | Status |
|------------|------|------|--------|
| `/login` | login | 356 | VERIFIED |
| `/register` | register | 361 | VERIFIED |
| `/forgot-password` | forgotPassword | 366 | VERIFIED |
| `/verify-otp` | verifyOtp | 371 | VERIFIED |
| `/update-password` | updatePassword | 379 | VERIFIED |
| `/update-required` | updateRequired | 384 | VERIFIED |
| `/consent` | consent | 389 | VERIFIED |
| `/profile-setup` | profileSetup | 396 | VERIFIED |
| `/company-setup` | companySetup | 401 | VERIFIED |
| `/pending-approval` | pendingApproval | 406 | VERIFIED |
| `/account-status` | accountStatus | 417 | VERIFIED |
| `/` | dashboard | 430 | VERIFIED |
| `/calendar` | home | 435 | VERIFIED |
| `/projects` | projects | 440 | VERIFIED |
| `/settings` | settings | 445 | VERIFIED |
| `/settings/trash` | trash | 454 | VERIFIED |
| `/edit-profile` | editProfile | 460 | VERIFIED |
| `/admin-dashboard` | admin-dashboard | 465 | VERIFIED |
| `/help-support` | help-support | 470 | VERIFIED |
| `/legal-document` | legal-document | 477 | VERIFIED |
| `/oss-licenses` | oss-licenses | 487 | VERIFIED |
| `/entry/:projectId/:date` | entry | 492 | VERIFIED |
| `/report/:entryId` | report | 504 | VERIFIED |
| `/project/new` | project-new | 512 | VERIFIED |
| `/project/:projectId/edit` | project-edit | 517 | VERIFIED |
| `/quantities` | quantities | 530 | VERIFIED |
| `/quantity-calculator/:entryId` | quantity-calculator | 535 | VERIFIED |
| `/entries` | entries | 546 | VERIFIED |
| `/drafts/:projectId` | drafts | 551 | VERIFIED |
| `/review` | review | 558 | VERIFIED |
| `/review-summary` | review-summary | 570 | VERIFIED |
| `/personnel-types/:projectId` | personnel-types | 585 | VERIFIED |
| `/import/preview/:projectId` | import-preview | 592 | VERIFIED |
| `/mp-import/preview/:projectId` | mp-import-preview | 623 | VERIFIED |
| `/toolbox` | toolbox | 652 | VERIFIED |
| `/forms` | forms | 658 | VERIFIED |
| `/form/:responseId` | form-fill | 664 | VERIFIED |
| `/calculator` | calculator | 697 | VERIFIED |
| `/gallery` | gallery | 702 | VERIFIED |
| `/todos` | todos | 707 | VERIFIED |
| `/sync/dashboard` | sync-dashboard | 712 | VERIFIED |
| `/sync/conflicts` | sync-conflicts | 717 | VERIFIED |

## Onboarding Routes (from `_kOnboardingRoutes`, line 43)

| Route | Status |
|-------|--------|
| `/profile-setup` | VERIFIED |
| `/company-setup` | VERIFIED |
| `/pending-approval` | VERIFIED |
| `/account-status` | VERIFIED |

## Non-Restorable Routes (from `_kNonRestorableRoutes`, line 59)

| Route | Status |
|-------|--------|
| `/login` | VERIFIED |
| `/register` | VERIFIED |
| `/forgot-password` | VERIFIED |
| `/verify-otp` | VERIFIED |
| `/update-password` | VERIFIED |
| `/consent` | VERIFIED |
| `/profile-setup` | VERIFIED |
| `/company-setup` | VERIFIED |
| `/pending-approval` | VERIFIED |
| `/account-status` | VERIFIED |
| `/update-required` | VERIFIED |
| `/admin-dashboard` | VERIFIED |

## DB Tables Referenced in sync_providers.dart

| Table | Usage | Line | Status |
|-------|-------|------|--------|
| `project_assignments` | Query for enrollment | 110-116 | VERIFIED |
| `synced_projects` | Insert/update for enrollment | 120-170 | VERIFIED |

## Supabase.instance.client Direct Accesses (in app_initializer.dart)

| Line | Usage | Status |
|------|-------|--------|
| 337 | `AppDependencies.supabaseClient` getter | VERIFIED |
| 470 | `ProjectLifecycleService` constructor | VERIFIED |
| 529 | `ProjectRemoteDatasourceImpl` constructor | VERIFIED |
| 550 | `CompanyMembersRepository` constructor | VERIFIED |
| 590 | `UserProfileRemoteDatasource` constructor | VERIFIED |
| 599 | `AuthService` constructor | VERIFIED |
| 644 | `AuthProvider` constructor | VERIFIED |
| 681 | `AppConfigRepository` constructor | VERIFIED |
| 694 | `SyncProviders.initialize()` call | VERIFIED |

**Count: 9 occurrences** (spec says 7 — the getter at line 337 and the SyncProviders pass-through at 694 are 2 additional)

## Widget Keys (from `lib/shared/testing_keys/testing_keys.dart`)

| Key | Delegated To | Line | Status |
|-----|--------------|------|--------|
| `TestingKeys.bottomNavigationBar` | `NavigationTestingKeys.bottomNavigationBar` | 70 | VERIFIED |
| `TestingKeys.dashboardNavButton` | `NavigationTestingKeys.dashboardNavButton` | 71 | VERIFIED |
| `TestingKeys.calendarNavButton` | `NavigationTestingKeys.calendarNavButton` | 72 | VERIFIED |
| `TestingKeys.projectsNavButton` | `NavigationTestingKeys.projectsNavButton` | 74 | VERIFIED |
| `TestingKeys.settingsNavButton` | `NavigationTestingKeys.settingsNavButton` | 75 | VERIFIED |

## ConsentProvider API (from `lib/features/settings/presentation/providers/consent_provider.dart`)

| Method/Property | Line | Status |
|-----------------|------|--------|
| `hasConsented` (getter) | 61-62 | VERIFIED |
| `hasEverConsented` (getter) | 65 | VERIFIED |
| `loadConsentState()` | 79 | VERIFIED |
| `clearOnSignOut()` | 195 | VERIFIED |
| `writeDeferredAuditRecordsIfNeeded()` | 212 | VERIFIED |

## SyncLifecycleManager Callbacks (from `lib/features/sync/application/sync_lifecycle_manager.dart`)

| Field | Type | Line | Status |
|-------|------|------|--------|
| `isReadyForSync` | `bool Function()?` | 22 | VERIFIED |
| `onStaleDataWarning` | `void Function(bool)?` | 25 | VERIFIED |
| `onForcedSyncInProgress` | `void Function(bool)?` | 28 | VERIFIED |
| `onAppResumed` | `Future<void> Function()?` | 32 | VERIFIED |

## SyncOrchestrator Callbacks (from `lib/features/sync/application/sync_orchestrator.dart`)

| Field | Type | Line | Status |
|-------|------|------|--------|
| `onPullComplete` | `Future<void> Function(String, int)?` | 94 | VERIFIED |
| `onNewAssignmentDetected` | `void Function(String)?` | 98 | VERIFIED |

## Sentry Consent Gate (from `lib/core/config/sentry_consent.dart`)

| Symbol | Type | Line | Status |
|--------|------|------|--------|
| `sentryConsentGranted` | `bool` getter | 13 | VERIFIED |
| `enableSentryReporting()` | `void` function | 16 | VERIFIED |

## Files to Delete

| File | Exists | Status |
|------|--------|--------|
| `lib/driver_main.dart` | Yes | VERIFIED |
| `lib/test_harness.dart` | Yes | VERIFIED |
| `flutter_driver` in pubspec.yaml | Line 119 | VERIFIED |

## Test Harness Files (from `lib/test_harness/`)

| File | Status |
|------|--------|
| `lib/test_harness/stub_router.dart` | VERIFIED exists |
| `lib/test_harness/flow_registry.dart` | VERIFIED exists |
| `lib/test_harness/screen_registry.dart` | VERIFIED exists |
| `lib/test_harness/harness_seed_data.dart` | VERIFIED exists |
| `lib/test_harness/stub_services.dart` | VERIFIED exists (100% dead code) |
| `lib/test_harness/harness_providers.dart` | VERIFIED exists |

## BackgroundSyncHandler

| File | Line | Status |
|------|------|--------|
| `lib/features/sync/application/background_sync_handler.dart` | 76 | VERIFIED (class exists) |
| Called from `app_initializer.dart` | 706 | VERIFIED |
