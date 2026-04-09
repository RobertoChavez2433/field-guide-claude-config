# Services And Integrations Audit

Date: 2026-03-30
Layer: cross-cutting services, logging, background services, external integrations

## Findings

### 1. High | Confirmed
The logging stack still contains many deliberately swallowed failures, including inside the logger itself.

Evidence:

- `lib/core/logging/logger.dart` is `990` lines.
- Examples of silent catches:
  - `lib/core/logging/logger.dart:388`
  - `lib/core/logging/logger.dart:485`
  - `lib/core/logging/logger.dart:510`
  - `lib/core/logging/logger.dart:544`
  - `lib/core/logging/logger.dart:778-780`
  - `lib/core/logging/logger.dart:815-817`
  - `lib/core/logging/logger.dart:848-850`
  - `lib/core/logging/logger.dart:917-919`
  - `lib/core/logging/logger.dart:995-996`
  - `lib/core/logging/logger.dart:1037-1038`

Why this matters:

- The logger is the fallback observability path, so silent failures inside it are especially expensive.
- Production diagnosis gets weaker exactly when file IO or transport degrades.

### 2. High | Confirmed
`BackgroundSyncHandler` is still a separate static integration surface rather than a thin wrapper over the main sync orchestration path.

Evidence:

- `lib/features/sync/application/background_sync_handler.dart:76-184`
- Static globals own initialization state, timer lifecycle, and DB service storage.
- Mobile and desktop both build sync execution separately instead of delegating through one injected sync boundary.

Why this matters:

- Background behavior is harder to reason about, especially across sign-out and app teardown.
- Static lifecycle plus duplicated engine bootstrap is fragile in pre-production conditions.

### 3. Medium | Confirmed
`PdfImportService` still self-wires metrics persistence through a global DB lookup.

Evidence:

- `lib/features/pdf/services/pdf_import_service.dart:190-195`
- It reaches into `DatabaseService().database` and constructs `ExtractionMetrics(ExtractionMetricsLocalDatasource(db))` inline.

Why this matters:

- The service owns both extraction orchestration and storage composition.
- It bypasses the DI graph and keeps the PDF pipeline harder to substitute or test end-to-end.

### 4. Medium | Confirmed
Support ticket submission is still not an end-to-end completed flow.

Evidence:

- `lib/features/settings/presentation/providers/support_provider.dart:131-133`
- The ticket is saved locally, but the provider still carries `TODO: Sync trigger for support_tickets — deferred`.

Why this matters:

- This appears to be recently implemented but unfinished rather than stale.
- Users can complete the form without the provider owning immediate delivery behavior.

Classification: unfinished recent work from pre-release hardening.

### 5. Medium | Confirmed
Document handling remains local-only in the UI even though the broader documents feature was added for syncable attachments.

Evidence:

- `lib/features/entries/presentation/widgets/entry_forms_section.dart:324-330`
- Missing local file handling falls back to "Re-sync to download" and explicitly leaves remote signed URL support as TODO.

Why this matters:

- The document feature is not fully closed for cross-device recovery/view flows.
- This is acceptable for an internal milestone, but it is not yet production-polished behavior.

### 6. Medium | Confirmed
Silent exception swallowing is spread across multiple integration surfaces, not just the logger.

Evidence:

- `lib/services/image_service.dart:190,204`
- `lib/features/photos/data/datasources/remote/photo_remote_datasource.dart:140`
- `lib/features/forms/data/services/form_pdf_service.dart:1039`
- `lib/features/sync/engine/sync_mutex.dart:39`
- `lib/features/sync/engine/sync_engine.dart:381`

Why this matters:

- These paths include file IO, remote download, PDF generation, and sync coordination.
- When failures are intentionally suppressed in these areas, production debugging depends on secondary side effects rather than explicit failure signals.
- This is a systemic observability gap, not an isolated logging-style choice.

### 7. High | Confirmed
`PdfService` still acts as a local composition root for other export services instead of consuming the app-composed graph.

Evidence:

- `lib/core/di/app_initializer.dart:753-757` constructs `FormPdfService`, `PdfService`, `WeatherService`, `ImageService`, and `PermissionService` at startup.
- `lib/core/di/app_providers.dart:40-41` exposes `PermissionService` through the provider tree.
- `lib/features/entries/presentation/screens/entry_editor_screen.dart:676-705`
  already reads `PdfService` and `PermissionService` from DI and threads the permission service into the export path.
- `lib/features/pdf/services/pdf_service.dart:67-75` creates its own private `PermissionService`.
- `lib/features/pdf/services/pdf_service.dart:552-582` also creates `PhotoPdfService()` and `FormPdfService()` inline during export.
- `lib/features/forms/data/services/form_pdf_service.dart:75-100` then creates another private `PermissionService` internally.

Why this matters:

- The DI graph is not the authoritative owner of the PDF/export stack.
- Permission behavior and export collaborators are split across app initialization, screen wiring, and nested service self-construction.
- This is not dead code; it is active composition drift left after the DI refactor.

### 8. Medium | Confirmed
`PermissionService` ownership is fragmented across DI-managed and ad hoc call sites.

Evidence:

- `lib/core/di/app_providers.dart:40-41` provides a single `PermissionService`.
- `lib/features/entries/presentation/controllers/pdf_data_builder.dart:37-71`
  accepts a DI-managed `PermissionService` explicitly.
- `lib/shared/widgets/permission_dialog.dart:12-25` ignores the provider tree and creates `PermissionService()` inline.
- `lib/features/pdf/services/pdf_service.dart:67-75` creates `PermissionService()` inline.
- `lib/features/forms/data/services/form_pdf_service.dart:75-100` creates `PermissionService()` inline.

Why this matters:

- Export and permission UX paths no longer share one authoritative permission boundary.
- Test doubles injected through the provider tree do not automatically govern the whole export stack.
- Permission policy changes now require synchronized edits across multiple independent call sites.

### 9. High | Confirmed
Background-sync teardown is platform-divergent: sign-out clears only local handler state, but mobile task registration is left in place.

Evidence:

- `lib/features/sync/application/background_sync_handler.dart:100-107`
  registers the mobile periodic WorkManager task.
- `lib/features/sync/application/background_sync_handler.dart:171-176`
  only `cancelAll()` unregisters the task via `cancelByUniqueName(...)`.
- `lib/features/sync/application/background_sync_handler.dart:180-184`
  `dispose()` only cancels the desktop timer and resets `_isInitialized`.
- Sign-out paths call `dispose()`, not `cancelAll()`:
  - `lib/features/auth/domain/usecases/sign_out_use_case.dart:30-38`
  - `lib/features/auth/presentation/providers/auth_provider.dart:372-382`
  - `lib/features/auth/presentation/providers/auth_provider.dart:396-405`
  - `lib/features/auth/presentation/providers/auth_provider.dart:761-769`

Why this matters:

- Logout semantics differ by platform: desktop timer work is stopped, but mobile OS-managed background work is merely left to no-op later when session checks fail.
- The handler’s local `_isInitialized` flag can be reset while the mobile task remains registered externally.
- For a pre-production audit, this is lifecycle debt around privileged background behavior rather than dead code.

### 10. Medium | Confirmed
The support/help integration still keeps the log-bundling policy in the presentation provider while the factory bypasses the standard DI boundary.

Evidence:

- `lib/features/settings/presentation/providers/support_provider.dart:145-222`
  owns log-directory discovery, file enumeration, size gating, PII scrubbing, ZIP assembly, upload-path construction, and upload failure handling.
- `lib/features/settings/presentation/providers/support_provider.dart:117-132`
  also owns ticket insertion and the still-deferred sync trigger.
- `lib/features/settings/di/consent_support_factory.dart:30-51`
  manually composes `SupportRepository`, `LogUploadRemoteDatasource`, and `SupportProvider`.
- `lib/features/settings/di/consent_support_factory.dart:45-47`
  reaches directly into `Supabase.instance.client` when building the upload datasource.

Why this matters:

- The support flow is not owned by a single service-layer boundary; it is split between a manual factory, a thin datasource, and a stateful presentation provider.
- The recent settings/help work is active and not dead, but the architecture has not fully settled after the refactor.
- This is the same pattern as other service-layer drift in this audit: DI exists, but integration ownership still leaks upward.

### 11. Medium | Confirmed
`ImageService` is still presented as an injected dependency even though the concrete implementation is process-global singleton state.

Evidence:

- `lib/services/image_service.dart:13-16` implements `ImageService` as a singleton via `static final ImageService _instance` and `factory ImageService() => _instance`.
- The service also owns mutable cache state internally:
  - `lib/services/image_service.dart:19`
  - `lib/services/image_service.dart:22`
- App startup still constructs and passes it through DI as if instance ownership matters:
  - `lib/core/di/app_initializer.dart:753-757`
  - `lib/features/photos/di/photos_providers.dart:12-24`
- Test/harness doubles have to target the concrete class contract rather than an explicit abstraction:
  - `lib/test_harness/stub_services.dart:142-158`

Why this matters:

- The provider graph implies scoped ownership, but the concrete production implementation is still shared process state.
- Cache state and side effects can persist across code paths even when the DI graph suggests isolation.
- This is service-boundary integrity drift, not dead code.

### 12. Medium | Confirmed
The weather integration still carries a dormant abstraction layer: `WeatherServiceInterface` exists, but the production graph and harness bind the concrete `WeatherService` directly.

Evidence:

- The interface exists at `lib/features/weather/domain/weather_service_interface.dart:1-8`.
- Repo-wide search found only `2` references to `WeatherServiceInterface`: the interface definition and the `implements` clause in `lib/features/weather/services/weather_service.dart:27`.
- Production and harness wiring use the concrete type instead:
  - `lib/features/weather/di/weather_providers.dart:6-10`
  - `lib/core/di/app_initializer.dart:755`
  - `lib/features/entries/presentation/screens/entry_editor_screen.dart:483-486`
  - `lib/test_harness/stub_services.dart:123-139`
- The targeted analyzer pass also reported contract-hygiene drift in the concrete implementation:
  - `lib/features/weather/services/weather_service.dart:110`
  - `lib/features/weather/services/weather_service.dart:188`

Why this matters:

- The interface is currently compatibility surface without actual architectural leverage.
- Consumers, providers, and test doubles are all coupled to the concrete service anyway, so the abstraction can silently drift out of sync.
- For a pre-production audit, this is stale service-boundary scaffolding rather than a finished dependency contract.

### 13. Medium | Confirmed
Geolocation and permission flow is duplicated across `PhotoService` and `WeatherService` instead of being owned by one integration boundary.

Evidence:

- `lib/features/weather/services/weather_service.dart:47-107` implements GPS service checks, permission checks, denied/denied-forever handling, and `Geolocator.getCurrentPosition(...)`.
- `lib/services/photo_service.dart:185-239` repeats the same geolocation sequence with equivalent permission and timeout handling.
- Repo-wide search for `Geolocator.isLocationServiceEnabled`, `checkPermission`, `requestPermission`, and `getCurrentPosition` only found these two service files in production code.

Why this matters:

- Permission behavior, timeout policy, and logging can now diverge between photo capture and weather autofill.
- A service-level fix to location handling has to be applied in multiple places, which is exactly how cross-feature integration behavior drifts after refactors.
- This is duplicated service logic, not unfinished feature work.

## Coverage Gaps

- No direct tests exist for `PdfImportService` or `BackgroundSyncHandler`.
- Logger has direct tests, but the swallowed-failure branches above are still a maintainability concern because they intentionally suppress escalation.
- No direct test files exist for `SupportProvider` or `log_upload_remote_datasource`, despite both sitting on user-visible support/help flows added in the recent settings work.

- `test/services/pdf_service_test.dart:11-27`
  instantiates `PdfService`, but the test file is centered on filename/data shaping and does not exercise `generateIdrPdf()`, nested `PhotoPdfService` / `FormPdfService` composition, or permission handling.
- `test/features/forms/services/form_pdf_service_test.dart:10-118`
  and `test/features/forms/services/form_pdf_service_cache_test.dart:10-120`
  cover template/cache behavior, but there are still no tests for the service’s inline `PermissionService` path.
- `test/features/settings/about_section_test.dart:16-114`
  covers validation and local insert behavior with `LogUploadRemoteDatasource(null)`, but not log bundling, PII scrubbing, ZIP size limits, upload-path construction, or remote upload failure branches.
- `test/services/image_service_test.dart:6-45`
  explicitly avoids calling the real `ImageService.getThumbnail()` path, so the actual isolate wiring, cache tiers, and temp-directory behavior are not exercised.
- `test/services/weather_service_test.dart:5-120`
  only covers static conversion helpers; there are no direct tests for `getCurrentLocation()`, `fetchWeather()`, permission handling, timeout/error branches, or HTTP response parsing.
- `test/services/photo_service_test.dart:5-120`
  is named as a service test but is primarily a `Photo` model behavior test, so the actual camera/gallery/file-system service surface is still unverified here.
- No direct tests were found for `PermissionService` or `DocumentService`, despite both sitting on user-visible file/export flows.
- `test/services/image_service_test.dart:6-37` explicitly avoids the real `ImageService.getThumbnail()` integration path and instead re-tests resize logic in isolation, so singleton cache state, provider-injected usage, and temp-directory behavior remain unverified.
- No tests were found for `createConsentAndSupportProviders(...)` in `lib/features/settings/di/consent_support_factory.dart`, so the manual service/provider factory path has no direct parity coverage.
- No tests were found that bind or assert against `WeatherServiceInterface`; the existing weather tests cover helper/static conversions, while production wiring still depends on the concrete `WeatherService`.
