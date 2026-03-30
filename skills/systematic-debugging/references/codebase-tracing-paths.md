# Codebase Tracing Paths

10 audited tracing paths for the most common debugging scenarios. Each shows the exact class names and files to follow end-to-end.

All paths start from the user-facing layer and trace to the data/system layer.

---

## 1. Sync Flow

**Scenario**: Data not syncing, sync stuck, conflict resolution failure.

```
SyncProvider (lib/features/sync/presentation/providers/sync_provider.dart)
  └─> SyncLifecycleManager (lib/features/sync/application/sync_lifecycle_manager.dart)
      └─> SyncOrchestrator (lib/features/sync/application/sync_orchestrator.dart)
          └─> SyncEngine (lib/features/sync/engine/sync_engine.dart)
              ├─> ChangeTracker (lib/features/sync/engine/change_tracker.dart)
              ├─> IntegrityChecker (lib/features/sync/engine/integrity_checker.dart)
              ├─> OrphanScanner (lib/features/sync/engine/orphan_scanner.dart)
              └─> TableAdapter (lib/features/sync/adapters/{table}_adapter.dart)
                  └─> Supabase client (via supabase_flutter)
```

**Key breakpoints to check:**
- `SyncEngine.push()` — entry to outbound sync
- `SyncEngine.pull()` — entry to inbound sync
- `ChangeTracker.getPendingChanges()` — what's waiting to sync
- `TableAdapter.toSupabaseMap()` — data shape before upload
- `registerSyncAdapters()` — adapter registration order matters

**Logger category**: `sync`

---

## 2. PDF Import Flow

**Scenario**: PDF import fails, wrong data extracted, items missing after import.

```
PdfImportHelper (lib/features/pdf/presentation/helpers/pdf_import_helper.dart)
  └─> PdfImportService (lib/features/pdf/services/pdf_import_service.dart)
      └─> ExtractionPipeline (lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart)
          ├─> Stage: GridLineRemover (lib/features/pdf/services/extraction/stages/grid_line_remover.dart)
          ├─> Stage: TextRecognizerV2 (lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart)
          ├─> Stage: RowClassifierV3 (lib/features/pdf/services/extraction/stages/row_classifier_v3.dart)
          └─> Stage: PostProcessorV2 (lib/features/pdf/services/extraction/stages/post_processor_v2.dart)
              └─> Quantities / BidItems saved to SQLite
```

**Key breakpoints to check:**
- `ExtractionPipeline.run()` — receives raw PDF pages, outputs structured items
- `RowClassifierV3.classify()` — maps text regions to row types
- `PostProcessorV2.process()` — final cleanup and validation
- `PdfImportService.importItems()` — saves extracted items to database

**Logger category**: `pdf`

---

## 3. Auth Flow

**Scenario**: Login fails, user stuck on auth screen, token expiry issues, profile not loading.

```
LoginScreen (lib/features/auth/presentation/screens/login_screen.dart)
  └─> AuthProvider (lib/features/auth/presentation/providers/auth_provider.dart)
      └─> Supabase auth client (supabase_flutter GoTrueClient)
          └─> Profile fetch: profiles table (via Supabase PostgREST)
              └─> AuthProvider state update → GoRouter redirect
```

**Key breakpoints to check:**
- `AuthProvider.signIn()` — handles auth attempt and error
- `AuthProvider._loadProfile()` — fetches user profile after login
- `AuthProvider.state` — reactive state that triggers router redirect
- GoRouter redirect logic: `lib/core/router/app_router.dart`

**Logger category**: `auth`

---

## 4. Database Flow

**Scenario**: Data not saving, wrong data returned, SQLite migration failure.

```
Screen / Provider
  └─> Repository (lib/features/{feature}/data/repositories/{feature}_repository.dart)
      └─> LocalDatasource (lib/features/{feature}/data/datasources/local/{feature}_local_datasource.dart)
          └─> GenericLocalDatasource (lib/shared/datasources/generic_local_datasource.dart)
              └─> DatabaseService (lib/core/database/database_service.dart)
                  └─> SQLite (via sqflite)
```

**Key breakpoints to check:**
- `DatabaseService.database` — getter that initializes and returns DB instance
- `DatabaseService._onCreate()` — schema creation
- `DatabaseService._onUpgrade()` — migration steps
- `GenericLocalDatasource.insert()` / `.getAll()` — common CRUD
- `SchemaVerifier` (lib/core/database/schema_verifier.dart) — validates schema at runtime

**Logger category**: `db`

---

## 5. Navigation Flow

**Scenario**: Wrong screen shown, redirect loop, user lands on wrong route after login.

```
GoRouter (lib/core/router/app_router.dart)
  └─> redirect callback
      ├─> AuthProvider.state (check: authenticated? profile loaded?)
      └─> route definitions → Screen widget
```

**Key breakpoints to check:**
- `AppRouter.redirect()` — all redirect logic lives here
- `AuthProvider.isAuthenticated` + `AuthProvider.isLoading` — redirect depends on both
- `AppRouteObserver` (lib/core/logging/app_route_observer.dart) — logs route transitions

**Logger category**: `nav`

---

## 6. Photo Flow

**Scenario**: Photo not saving, upload fails, photo not appearing in gallery.

```
PhotoWidget / capture trigger
  └─> PhotoService (lib/services/photo_service.dart)
      ├─> ImageService (lib/services/image_service.dart) — resize/compress
      ├─> File system (local storage)
      └─> Supabase Storage (upload via supabase_flutter)
          └─> Photo record saved to SQLite → sync'd via SyncEngine
```

**Key breakpoints to check:**
- `PhotoService.capturePhoto()` / `PhotoService.pickPhoto()` — entry
- `ImageService.processImage()` — compression and format conversion
- `PhotoService.uploadPhoto()` — Supabase storage upload
- Permission check: `PermissionService` (lib/services/permission_service.dart)

**Logger category**: `photo`

---

## 7. Background Sync Flow

**Scenario**: Background sync not running, WorkManager task not firing, offline changes not syncing when app returns to foreground.

```
WorkManager task registration (lib/main.dart or background setup)
  └─> backgroundSyncCallback (lib/features/sync/application/background_sync_handler.dart)
      └─> SyncEngine (same path as Sync Flow above)
```

**Key breakpoints to check:**
- `BackgroundSyncHandler.backgroundSyncCallback()` — entry point for WorkManager task
- Task registration: check WorkManager constraints (network, battery)
- `SyncLifecycleManager.onAppResume()` — foreground sync trigger
- App lifecycle events: `AppLifecycleLogger` (lib/core/logging/logger.dart)

**Logger category**: `bg`

---

## 8. Error Flow

**Scenario**: Unhandled exception, crash, error not surfaced to user.

```
FlutterError.onError (set in lib/main.dart)
  └─> Logger.error() → error.log file + HTTP server
      └─> ErrorProvider or SnackBar (feature-specific error handling)
```

**Key breakpoints to check:**
- `main.dart` — `FlutterError.onError` and `PlatformDispatcher.instance.onError` handlers
- `runZonedGuarded` wrapper in `main()`
- Feature-level try/catch blocks: check if errors are swallowed silently

**Logger category**: `error`

---

## 9. App Lifecycle Flow

**Scenario**: State not preserved on background/foreground, session data lost, app misbehaves after resume.

```
WidgetsBindingObserver.didChangeAppLifecycleState
  └─> AppLifecycleLogger (lib/core/logging/logger.dart) — logs transitions
      └─> SyncLifecycleManager — triggers sync on resume
          └─> AuthProvider — validates session on resume
```

**Key breakpoints to check:**
- Which providers implement `WidgetsBindingObserver`
- `SyncLifecycleManager.onAppResume()` and `onAppPause()`
- State that is NOT re-initialized on resume (check `initState` vs `didChangeDependencies`)

**Logger category**: `lifecycle`

---

## 10. Form / Calculator Flow

**Scenario**: Form data not saving, calculator result wrong, toolbox item not appearing.

```
ToolboxHub (lib/features/toolbox/ — hub screen)
  ├─> CalculatorProvider (lib/features/calculator/presentation/providers/)
  │   └─> Calculator logic → local datasource → SQLite
  ├─> FormsProvider (lib/features/forms/presentation/providers/)
  │   └─> Form repository → local datasource → SQLite
  ├─> GalleryProvider (lib/features/gallery/presentation/providers/)
  └─> TodosProvider (lib/features/todos/presentation/providers/)
```

**Key breakpoints to check:**
- Provider `state` immediately after user action (did state update?)
- Local datasource `insert()` / `update()` — did SQLite row change?
- Cross-feature dependencies: some toolbox items reference `projects` or `locations` data

**Logger category**: `ui` (form interactions) or `db` (persistence)

---

## How to Use These Paths

1. Identify which of the 10 scenarios best matches your bug
2. Start at the top (user-facing layer) and trace downward
3. Use Grep to find the exact files: `Grep "ClassName" lib/ --output_mode=files_with_matches`
4. Check Logger coverage in each file along the path (Phase 2 of the skill)
5. Place hypothesis markers at the first boundary with no existing Logger call
