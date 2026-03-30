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

## Coverage Gaps

- No direct tests exist for `PdfImportService` or `BackgroundSyncHandler`.
- Logger has direct tests, but the swallowed-failure branches above are still a maintainability concern because they intentionally suppress escalation.
- No direct test files exist for `SupportProvider` or `log_upload_remote_datasource`, despite both sitting on user-visible support/help flows added in the recent settings work.
