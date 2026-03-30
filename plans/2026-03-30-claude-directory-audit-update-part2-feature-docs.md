# Claude Directory Audit & Update — Part 2: Feature Documentation

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Rewrite all 13 feature architecture docs, update all 13 feature overview docs, and create 8 new docs for 4 undocumented features.
**Spec:** `.claude/specs/2026-03-30-claude-directory-audit-update-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-30-claude-directory-audit-update/analysis.md`

**Blast Radius:** 34 direct files, 0 dependent, 0 tests, 0 cleanup

---

## Phase 5: Feature Architecture Docs — REWRITE (13 existing)

REWRITE all 13 `docs/features/feature-*-architecture.md` files. Each rewritten doc must include: accurate layer structure (data/datasources/local, datasources/remote, models, repositories; domain/repository interfaces, usecases; presentation/providers, screens, widgets, controllers; di/), key class names from ground truth, DI wiring description, architectural patterns specific to that feature, relationships to other features, and frontmatter with updated: 2026-03-30.

### Sub-phase 5.1: Auth Architecture
**Files:**
- Modify: `.claude/docs/features/feature-auth-architecture.md`
**Agent**: general-purpose

#### Step 5.1.1: Read current file and ground truth
Read `.claude/docs/features/feature-auth-architecture.md`. Read `lib/features/auth/di/auth_providers.dart` and scan `lib/features/auth/` directory structure for ground truth.

#### Step 5.1.2: Rewrite architecture doc
Rewrite the file with accurate content from ground truth:
- **Data layer**: Models (Company, CompanyJoinRequest, UserRole, UserProfile). Local DS (CompanyLocalDatasource, UserProfileLocalDatasource). Remote DS (CompanyRemoteDatasource, JoinRequestRemoteDatasource, UserProfileRemoteDatasource, UserProfileSyncDatasource). Repos (CompanyRepository, UserProfileRepository, UserAttributionRepository, AppConfigRepository).
- **Domain layer**: Use cases (SignInUseCase, SignOutUseCase, SignUpUseCase, LoadProfileUseCase, CheckInactivityUseCase, SwitchCompanyUseCase, MigratePreferencesUseCase). Utils (AuthErrorParser).
- **Presentation layer**: Providers (AuthProvider, AppConfigProvider). 10 screens (LoginScreen through UpdateRequiredScreen). Widgets (UserAttributionText).
- **Services**: AuthService, PasswordValidator.
- **DI**: auth_providers.dart — describe what it wires.
- **Patterns**: Multi-company support via SwitchCompanyUseCase, Supabase auth integration, inactivity checking, OTP verification flow, profile+company setup onboarding.
- **Relationships**: Used by sync (user context), settings (profile editing), entries (attribution).

### Sub-phase 5.2: Settings Architecture
**Files:**
- Modify: `.claude/docs/features/feature-settings-architecture.md`
**Agent**: general-purpose

#### Step 5.2.1: Read current file and ground truth
Read `.claude/docs/features/feature-settings-architecture.md`. Scan `lib/features/settings/` directory structure.

#### Step 5.2.2: Rewrite architecture doc
Rewrite with accurate content:
- **Data layer**: Models (SupportTicket, ConsentRecord, UserCertification). DS mixed structure: flat (ConsentLocalDatasource, SupportLocalDatasource), local/ subdir (UserCertificationLocalDatasource), remote/ subdir (LogUploadRemoteDatasource). Repos (TrashRepository, AdminRepository interface/AdminRepositoryImpl, ConsentRepository, SupportRepository).
- **Presentation**: Providers (ThemeProvider, AdminProvider, ConsentProvider, SupportProvider). Screens (SettingsScreen, TrashScreen, AdminDashboardScreen, PersonnelTypesScreen, EditProfileScreen, ConsentScreen, LegalDocumentScreen, OssLicensesScreen, HelpSupportScreen). Widgets (ThemeSection, ClearCacheDialog, SyncSection, SignOutDialog, SectionHeader, MemberDetailSheet).
- **DI**: settings_providers.dart + consent_support_factory.dart — two DI files.
- **Patterns**: Settings now owns consent/legal/support/admin. Consent gating via ConsentProvider. Support ticket submission with log upload. Admin dashboard for company management.
- **Relationships**: Depends on auth (profile), sync (sync section), photos (cache). Required by router (consent gate).

### Sub-phase 5.3: Projects Architecture
**Files:**
- Modify: `.claude/docs/features/feature-projects-architecture.md`
**Agent**: general-purpose

#### Step 5.3.1: Read current file and ground truth
Read `.claude/docs/features/feature-projects-architecture.md`. Scan `lib/features/projects/` directory.

#### Step 5.3.2: Rewrite architecture doc
Rewrite with accurate content:
- **Data layer**: Models (Project, ProjectMode, ProjectAssignment, AssignableMember, MergedProjectEntry). Services (ProjectLifecycleService). DS (ProjectLocalDatasource, ProjectRemoteDatasourceImpl). Repos (ProjectRepositoryImpl, ProjectAssignmentRepository, SyncedProjectRepository, CompanyMembersRepository).
- **Domain**: Repos interfaces (ProjectRepository, ProjectRemoteDatasource — note remote DS interface lives in domain). Use cases (DeleteProjectUseCase, LoadAssignmentsUseCase, FetchRemoteProjectsUseCase, LoadCompanyMembersUseCase).
- **Presentation**: Providers (ProjectProvider, ProjectAssignmentProvider, ProjectSettingsProvider, ProjectSyncHealthProvider, ProjectImportRunner). Screens (ProjectListScreen, ProjectSetupScreen). 13 widgets (ProjectFilterChips through AssignmentsStep).
- **DI**: projects_providers.dart.
- **Patterns**: ProjectMode (personal vs company). SyncedProjectRepository for remote project fetching. ProjectLifecycleService for create/archive/delete orchestration. Import runner for PDF-extracted pay items.
- **Relationships**: Central entity — entries, quantities, contractors, locations, photos all belong to a project.

### Sub-phase 5.4: Entries Architecture
**Files:**
- Modify: `.claude/docs/features/feature-entries-architecture.md`
**Agent**: general-purpose

#### Step 5.4.1: Read current file and ground truth
Read `.claude/docs/features/feature-entries-architecture.md`. Scan `lib/features/entries/` directory.

#### Step 5.4.2: Rewrite architecture doc
Rewrite with accurate content:
- **Data layer**: Models (DailyEntry, EntryExport, Document). Presentation models (ContractorUiState). Local DS (DailyEntryLocalDatasource, EntryExportLocalDatasource, DocumentLocalDatasource). Remote DS (DailyEntryRemoteDatasource, DocumentRemoteDatasource, EntryExportRemoteDatasource). Repos (DailyEntryRepositoryImpl, EntryExportRepositoryImpl, DocumentRepositoryImpl).
- **Domain**: Use cases (SubmitEntryUseCase, UndoSubmitEntryUseCase, BatchSubmitEntriesUseCase, ExportEntryUseCase, ManageEntryUseCase, CalendarEntriesUseCase, LoadEntriesUseCase).
- **Presentation**: Controllers (EntryEditingController, ContractorEditingController, PhotoAttachmentManager, FormAttachmentManager, PdfDataBuilder). Providers (DailyEntryProvider, EntryExportProvider, CalendarFormatProvider). 6 screens. Report widgets sub-directory with 10+ dialog/sheet widgets.
- **DI**: entries_providers.dart.
- **Patterns**: Editor uses controller pattern (EntryEditingController) not provider-direct. Report widgets are a sub-module for PDF report generation UI. Photo and form attachment managers handle cross-feature coordination. Submit/undo submit workflow with batch support.
- **Relationships**: Depends on projects, contractors, quantities, locations, photos, weather, forms. Required by sync, pdf.

### Sub-phase 5.5: Sync Architecture
**Files:**
- Modify: `.claude/docs/features/feature-sync-architecture.md`
**Agent**: general-purpose

#### Step 5.5.1: Read current file and ground truth
Read `.claude/docs/features/feature-sync-architecture.md`. Scan `lib/features/sync/` directory.

#### Step 5.5.2: Rewrite architecture doc
Rewrite with accurate content:
- **Engine layer**: SyncEngine, ChangeTracker, ConflictResolver, IntegrityChecker, SyncMutex, SyncRegistry, OrphanScanner, StorageCleanup, ScopeType.
- **Application layer**: SyncOrchestrator, SyncLifecycleManager, BackgroundSyncHandler, FcmHandler.
- **Adapters**: TableAdapter base class + 20+ concrete adapters (one per synced table).
- **Config**: SyncConfig.
- **Domain**: SyncTypes.
- **Presentation**: SyncProvider. Screens (SyncDashboardScreen, ConflictViewerScreen). Widgets (SyncStatusIcon, DeletionNotificationBanner).
- **DI**: sync_providers.dart.
- **Patterns**: Adapter pattern — each table has a TableAdapter that knows how to push/pull/resolve conflicts for that entity. SyncMutex prevents concurrent syncs. OrphanScanner detects orphaned records. IntegrityChecker validates referential integrity post-sync. Background sync via BackgroundSyncHandler + FCM push triggers.
- **Relationships**: Depends on every syncable feature's repositories. Required by settings (sync section), projects (sync health).

### Sub-phase 5.6: Toolbox Architecture
**Files:**
- Modify: `.claude/docs/features/feature-toolbox-architecture.md`
**Agent**: general-purpose

#### Step 5.6.1: Read current file and ground truth
Read `.claude/docs/features/feature-toolbox-architecture.md`. Scan `lib/features/toolbox/` directory.

#### Step 5.6.2: Rewrite architecture doc
Rewrite with accurate content:
- **Structure**: presentation/screens only + domain barrel. No DI, no data layer.
- **Screen**: ToolboxHomeScreen — hub linking to calculator, forms, gallery, todos.
- **Patterns**: Pure navigation hub. No business logic. Routes to sub-features.
- **Relationships**: Depends on calculator, forms, gallery, todos (navigates to their screens).

### Sub-phase 5.7: Contractors Architecture
**Files:**
- Modify: `.claude/docs/features/feature-contractors-architecture.md`
**Agent**: general-purpose

#### Step 5.7.1: Read current file and ground truth
Read `.claude/docs/features/feature-contractors-architecture.md`. Scan `lib/features/contractors/` directory.

#### Step 5.7.2: Rewrite architecture doc
Rewrite with accurate content:
- **Data layer**: Models (Contractor, Equipment, PersonnelType, EntryPersonnel, EntryEquipment). Local DS (ContractorLocalDatasource, EquipmentLocalDatasource, PersonnelTypeLocalDatasource, EntryPersonnelCountsLocalDatasource, EntryEquipmentLocalDatasource, EntryContractorsLocalDatasource). Remote DS (ContractorRemoteDatasource, EquipmentRemoteDatasource, PersonnelTypeRemoteDatasource, EntryEquipmentRemoteDatasource). Domain repo interfaces (ContractorRepository, EquipmentRepository, PersonnelTypeRepository). Impl repos (ContractorRepositoryImpl, EquipmentRepositoryImpl, PersonnelTypeRepositoryImpl).
- **Presentation**: Providers (ContractorProvider, EquipmentProvider, PersonnelTypeProvider). No screens — UI embedded in entries/projects.
- **DI**: contractors_providers.dart.
- **Patterns**: Data-only feature — no screens. Provides domain entities consumed by entries and projects. Entry-scoped junction tables (EntryPersonnel, EntryEquipment) for per-entry contractor/equipment tracking.
- **Relationships**: Required by entries (contractor editing), projects (contractor/equipment setup). Depends on projects (project-scoped data).

### Sub-phase 5.8: Dashboard Architecture
**Files:**
- Modify: `.claude/docs/features/feature-dashboard-architecture.md`
**Agent**: general-purpose

#### Step 5.8.1: Read current file and ground truth
Read `.claude/docs/features/feature-dashboard-architecture.md`. Scan `lib/features/dashboard/` directory.

#### Step 5.8.2: Rewrite architecture doc
Rewrite with accurate content:
- **Structure**: presentation/screens + presentation/widgets + domain barrel. No DI, no data layer, no providers.
- **Screen**: ProjectDashboardScreen.
- **Widgets**: TrackedItemRow, AlertItemRow, BudgetOverviewCard, DashboardStatCard.
- **Patterns**: Presentation-only feature. Reads data from other features' providers (projects, quantities, entries). No own state management.
- **Relationships**: Depends on projects, quantities, entries for data display.

### Sub-phase 5.9: Locations Architecture
**Files:**
- Modify: `.claude/docs/features/feature-locations-architecture.md`
**Agent**: general-purpose

#### Step 5.9.1: Read current file and ground truth
Read `.claude/docs/features/feature-locations-architecture.md`. Scan `lib/features/locations/` directory.

#### Step 5.9.2: Rewrite architecture doc
Rewrite with accurate content:
- **Data layer**: Model (Location). DS (LocationLocalDatasource, LocationRemoteDatasource). Domain repo interface (LocationRepository). Impl (LocationRepositoryImpl).
- **Presentation**: Provider (LocationProvider). No screens — UI embedded in entries/projects.
- **DI**: locations_providers.dart.
- **Patterns**: Simple CRUD feature. Single model, single repo. Project-scoped locations.
- **Relationships**: Required by entries (location selection), projects (location management). Depends on projects.

### Sub-phase 5.10: PDF Architecture
**Files:**
- Modify: `.claude/docs/features/feature-pdf-architecture.md`
**Agent**: general-purpose

#### Step 5.10.1: Read current file and ground truth
Read `.claude/docs/features/feature-pdf-architecture.md`. Scan `lib/features/pdf/` directory.

#### Step 5.10.2: Rewrite architecture doc
Rewrite with accurate content:
- **Services (massive)**: Top-level (PdfService, PdfImportService, PhotoPdfService). OCR sub-system (TesseractInitializer, TesseractConfig, TesseractConfigV2, TesseractEngineV2, OcrEngineV2). Pipeline (ExtractionPipeline, PipelineContext, ExtractionMetrics + 20 extraction stages). MP sub-system (MpExtractionService).
- **Data layer**: Models only (no datasources/repos — PDF is a service-oriented feature).
- **Presentation**: Screens (PdfImportPreviewScreen, MpImportPreviewScreen). Widgets (ExtractionBanner, ExtractionDetailSheet). Helpers (PdfImportHelper, MpImportHelper).
- **DI**: pdf_providers.dart.
- **Patterns**: Pipeline architecture — ExtractionPipeline runs 20+ sequential stages. OCR via Tesseract FFI (native bindings). Two import paths: standard PDF and MP (material producer) extraction. Service-oriented, not repository-pattern.
- **Relationships**: Required by entries (report PDF generation), projects (pay item import), forms (form PDF filling). Depends on projects, quantities, entries for data.

### Sub-phase 5.11: Photos Architecture
**Files:**
- Modify: `.claude/docs/features/feature-photos-architecture.md`
**Agent**: general-purpose

#### Step 5.11.1: Read current file and ground truth
Read `.claude/docs/features/feature-photos-architecture.md`. Scan `lib/features/photos/` directory.

#### Step 5.11.2: Rewrite architecture doc
Rewrite with accurate content:
- **Data layer**: Model (Photo). DS (PhotoLocalDatasource, PhotoRemoteDatasource). Domain repo interface (PhotoRepository). Impl (PhotoRepositoryImpl).
- **Presentation**: Provider (PhotoProvider). Widgets (PhotoSourceDialog, PhotoThumbnail, PhotoNameDialog). No screens — used within entries/gallery.
- **DI**: photos_providers.dart.
- **Patterns**: File-backed model — Photo records reference local file paths + remote storage URLs. Sync uploads/downloads actual image files. Thumbnail generation.
- **Relationships**: Required by entries (photo attachment), gallery (photo browsing), settings (cache clearing). Depends on projects (project-scoped).

### Sub-phase 5.12: Quantities Architecture
**Files:**
- Modify: `.claude/docs/features/feature-quantities-architecture.md`
**Agent**: general-purpose

#### Step 5.12.1: Read current file and ground truth
Read `.claude/docs/features/feature-quantities-architecture.md`. Scan `lib/features/quantities/` directory.

#### Step 5.12.2: Rewrite architecture doc
Rewrite with accurate content:
- **Data layer**: Models (BidItem, EntryQuantity). Domain model (ImportBatchResult). DS (BidItemLocalDatasource, EntryQuantityLocalDatasource, BidItemRemoteDatasource, EntryQuantityRemoteDatasource). Domain repo interfaces (BidItemRepository, EntryQuantityRepository). Impl (BidItemRepositoryImpl, EntryQuantityRepositoryImpl).
- **Presentation**: Providers (BidItemProvider, EntryQuantityProvider). Screens (QuantitiesScreen, QuantityCalculatorScreen). Widgets (QuantitySummaryHeader, BidItemCard, BidItemDetailSheet).
- **Utils**: BudgetSanityChecker.
- **DI**: quantities_providers.dart.
- **Patterns**: Two-tier model — BidItems are project-level pay items, EntryQuantities are per-entry quantities against those items. BudgetSanityChecker validates totals. Import from PDF extraction.
- **Relationships**: Required by entries (quantity entry), dashboard (budget overview), projects (bid item management). Depends on projects, pdf (import).

### Sub-phase 5.13: Weather Architecture
**Files:**
- Modify: `.claude/docs/features/feature-weather-architecture.md`
**Agent**: general-purpose

#### Step 5.13.1: Read current file and ground truth
Read `.claude/docs/features/feature-weather-architecture.md`. Scan `lib/features/weather/` directory.

#### Step 5.13.2: Rewrite architecture doc
Rewrite with accurate content:
- **Domain**: WeatherServiceInterface (interface).
- **Services**: WeatherService (calls Open-Meteo API — real implementation, not placeholder).
- **DI**: weather_providers.dart.
- **Patterns**: Service-only feature. No data layer, no presentation. Domain interface + service impl. External API integration.
- **Relationships**: Required by entries (weather data for daily entries).

---

## Phase 6: Feature Overview Docs — UPDATE (13 existing)

UPDATE all 13 `docs/features/feature-*-overview.md` files. Fix Key Files tables, purpose/scope, screen lists, provider lists, feature relationships, and set frontmatter updated: 2026-03-30.

### Sub-phase 6.1: Auth Overview
**Files:**
- Modify: `.claude/docs/features/feature-auth-overview.md`
**Agent**: general-purpose

#### Step 6.1.1: Read and update
Read `.claude/docs/features/feature-auth-overview.md`. Update against ground truth:
- Key Files table must include: `di/auth_providers.dart`, `data/models/` (Company, CompanyJoinRequest, UserRole, UserProfile), `domain/usecases/` (7 use cases), `presentation/providers/` (AuthProvider, AppConfigProvider), `presentation/screens/` (10 screens), `services/` (AuthService, PasswordValidator). Remove any files that don't exist.
- Purpose: Authentication, authorization, company management, profile management, onboarding.
- Screens: LoginScreen, RegisterScreen, ForgotPasswordScreen, OtpVerificationScreen, UpdatePasswordScreen, ProfileSetupScreen, CompanySetupScreen, PendingApprovalScreen, AccountStatusScreen, UpdateRequiredScreen.
- Providers: AuthProvider, AppConfigProvider.
- Integration: Depends on nothing (root feature). Required by all features (auth context).
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.2: Settings Overview
**Files:**
- Modify: `.claude/docs/features/feature-settings-overview.md`
**Agent**: general-purpose

#### Step 6.2.1: Read and update
Read `.claude/docs/features/feature-settings-overview.md`. Update against ground truth:
- Purpose/scope: Now owns consent flow, legal documents, help/support, admin dashboard, trash management, theme, profile editing — not just "app settings."
- Key Files: `di/settings_providers.dart`, `di/consent_support_factory.dart`, models (SupportTicket, ConsentRecord, UserCertification), DS (ConsentLocalDatasource, SupportLocalDatasource, UserCertificationLocalDatasource, LogUploadRemoteDatasource), repos (TrashRepository, AdminRepository/Impl, ConsentRepository, SupportRepository).
- Screens: SettingsScreen, TrashScreen, AdminDashboardScreen, PersonnelTypesScreen, EditProfileScreen, ConsentScreen, LegalDocumentScreen, OssLicensesScreen, HelpSupportScreen.
- Providers: ThemeProvider, AdminProvider, ConsentProvider, SupportProvider.
- Integration: Depends on auth, sync, photos. Required by router (consent gate).
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.3: Projects Overview
**Files:**
- Modify: `.claude/docs/features/feature-projects-overview.md`
**Agent**: general-purpose

#### Step 6.3.1: Read and update
Read `.claude/docs/features/feature-projects-overview.md`. Update against ground truth:
- Key Files: Include ProjectLifecycleService, SyncedProjectRepository, CompanyMembersRepository, ProjectImportRunner, ProjectSyncHealthProvider, ProjectAssignmentProvider, ProjectSettingsProvider. All 13 widgets. Remove nonexistent files.
- Screens: ProjectListScreen, ProjectSetupScreen.
- Providers: ProjectProvider, ProjectAssignmentProvider, ProjectSettingsProvider, ProjectSyncHealthProvider, ProjectImportRunner.
- Models: Project, ProjectMode, ProjectAssignment, AssignableMember, MergedProjectEntry.
- Integration: Central entity. Required by entries, quantities, contractors, locations, photos, sync, dashboard.
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.4: Entries Overview
**Files:**
- Modify: `.claude/docs/features/feature-entries-overview.md`
**Agent**: general-purpose

#### Step 6.4.1: Read and update
Read `.claude/docs/features/feature-entries-overview.md`. Update against ground truth:
- Key Files: Include all 7 use cases, 5 controllers (EntryEditingController, ContractorEditingController, PhotoAttachmentManager, FormAttachmentManager, PdfDataBuilder), 3 providers, Document model, report_widgets sub-directory.
- Screens: HomeScreen, EntryEditorScreen, EntryReviewScreen, ReviewSummaryScreen, EntriesListScreen, DraftsListScreen.
- Providers: DailyEntryProvider, EntryExportProvider, CalendarFormatProvider.
- Integration: Depends on projects, contractors, quantities, locations, photos, weather, forms. Required by sync, pdf.
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.5: Sync Overview
**Files:**
- Modify: `.claude/docs/features/feature-sync-overview.md`
**Agent**: general-purpose

#### Step 6.5.1: Read and update
Read `.claude/docs/features/feature-sync-overview.md`. Update against ground truth:
- Key Files: Engine components (SyncEngine, ChangeTracker, ConflictResolver, IntegrityChecker, SyncMutex, SyncRegistry, OrphanScanner, StorageCleanup). Application layer (SyncOrchestrator, SyncLifecycleManager, BackgroundSyncHandler, FcmHandler). 20+ adapters. SyncConfig.
- Screens: SyncDashboardScreen, ConflictViewerScreen.
- Providers: SyncProvider.
- Integration: Depends on all syncable features. Required by settings, projects.
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.6: Toolbox Overview
**Files:**
- Modify: `.claude/docs/features/feature-toolbox-overview.md`
**Agent**: general-purpose

#### Step 6.6.1: Read and update
Read `.claude/docs/features/feature-toolbox-overview.md`. Update against ground truth:
- Purpose: Navigation hub for calculator, forms, gallery, todos.
- Key Files: `presentation/screens/toolbox_home_screen.dart`, domain barrel.
- Screens: ToolboxHomeScreen.
- No providers, no DI, no data layer.
- Integration: Depends on calculator, forms, gallery, todos.
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.7: Contractors Overview
**Files:**
- Modify: `.claude/docs/features/feature-contractors-overview.md`
**Agent**: general-purpose

#### Step 6.7.1: Read and update
Read `.claude/docs/features/feature-contractors-overview.md`. Update against ground truth:
- Key Files: 6 local DS, 4 remote DS, 3 domain repo interfaces, 3 impl repos, 3 providers, 5 models.
- No screens — explicitly note UI is embedded in entries/projects.
- Providers: ContractorProvider, EquipmentProvider, PersonnelTypeProvider.
- Integration: Required by entries, projects. Depends on projects.
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.8: Dashboard Overview
**Files:**
- Modify: `.claude/docs/features/feature-dashboard-overview.md`
**Agent**: general-purpose

#### Step 6.8.1: Read and update
Read `.claude/docs/features/feature-dashboard-overview.md`. Update against ground truth:
- Key Files: ProjectDashboardScreen, 4 widgets (TrackedItemRow, AlertItemRow, BudgetOverviewCard, DashboardStatCard).
- No DI, no providers, no data layer.
- Screens: ProjectDashboardScreen.
- Integration: Depends on projects, quantities, entries.
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.9: Locations Overview
**Files:**
- Modify: `.claude/docs/features/feature-locations-overview.md`
**Agent**: general-purpose

#### Step 6.9.1: Read and update
Read `.claude/docs/features/feature-locations-overview.md`. Update against ground truth:
- Key Files: Location model, LocationLocalDatasource, LocationRemoteDatasource, LocationRepository (interface), LocationRepositoryImpl, LocationProvider, locations_providers.dart.
- No screens — UI embedded in entries/projects.
- Providers: LocationProvider.
- Integration: Required by entries, projects. Depends on projects.
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.10: PDF Overview
**Files:**
- Modify: `.claude/docs/features/feature-pdf-overview.md`
**Agent**: general-purpose

#### Step 6.10.1: Read and update
Read `.claude/docs/features/feature-pdf-overview.md`. Update against ground truth:
- Key Files: PdfService, PdfImportService, PhotoPdfService, OCR sub-system (TesseractInitializer, TesseractEngineV2, OcrEngineV2), ExtractionPipeline + 20 stages, MpExtractionService, PdfImportHelper, MpImportHelper.
- Screens: PdfImportPreviewScreen, MpImportPreviewScreen.
- Widgets: ExtractionBanner, ExtractionDetailSheet.
- Integration: Required by entries, projects, forms. Depends on projects, quantities, entries.
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.11: Photos Overview
**Files:**
- Modify: `.claude/docs/features/feature-photos-overview.md`
**Agent**: general-purpose

#### Step 6.11.1: Read and update
Read `.claude/docs/features/feature-photos-overview.md`. Update against ground truth:
- Key Files: Photo model, PhotoLocalDatasource, PhotoRemoteDatasource, PhotoRepository (interface), PhotoRepositoryImpl, PhotoProvider, 3 widgets (PhotoSourceDialog, PhotoThumbnail, PhotoNameDialog).
- No screens — used within entries/gallery.
- Providers: PhotoProvider.
- Integration: Required by entries, gallery, settings. Depends on projects.
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.12: Quantities Overview
**Files:**
- Modify: `.claude/docs/features/feature-quantities-overview.md`
**Agent**: general-purpose

#### Step 6.12.1: Read and update
Read `.claude/docs/features/feature-quantities-overview.md`. Update against ground truth:
- Key Files: BidItem + EntryQuantity models, ImportBatchResult domain model, 4 DS, 2 domain repo interfaces, 2 impl repos, 2 providers, 2 screens, 3 widgets, BudgetSanityChecker.
- Screens: QuantitiesScreen, QuantityCalculatorScreen.
- Providers: BidItemProvider, EntryQuantityProvider.
- Integration: Required by entries, dashboard, projects. Depends on projects, pdf.
- Set frontmatter `updated: 2026-03-30`.

### Sub-phase 6.13: Weather Overview
**Files:**
- Modify: `.claude/docs/features/feature-weather-overview.md`
**Agent**: general-purpose

#### Step 6.13.1: Read and update
Read `.claude/docs/features/feature-weather-overview.md`. Update against ground truth:
- Key Files: WeatherServiceInterface (domain), WeatherService (services), weather_providers.dart (DI).
- No screens, no data layer.
- Integration: Required by entries. No dependencies.
- Set frontmatter `updated: 2026-03-30`.

---

## Phase 7: Feature Docs — CREATE (4 missing features)

CREATE 8 new files for the 4 undocumented features: forms, calculator, gallery, todos. Follow the standard overview and architecture doc formats.

### Sub-phase 7.1: Forms Documentation
**Files:**
- Create: `.claude/docs/features/feature-forms-overview.md`
- Create: `.claude/docs/features/feature-forms-architecture.md`
**Agent**: general-purpose

#### Step 7.1.1: Create forms overview
Create `.claude/docs/features/feature-forms-overview.md` using the overview format. Content from ground truth:
- Purpose: Inspection form management — built-in form templates, form response data entry, form PDF generation/export.
- Key Responsibilities: Form template registry, form response CRUD, auto-fill calculations, PDF filling, form export.
- Key Files: `di/forms_providers.dart`, `di/forms_init.dart`, models (InspectorForm, FormResponse, FormExport, AutoFillResult), services (AutoFillService, OnePointCalculator, FormStateHasher, Mdot0582bCalculator, FormPdfService), registries (BuiltinFormConfig, BuiltinForms, FormScreenRegistry, FormQuickActionRegistry, FormPdfFillerRegistry, FormValidatorRegistry, FormCalculatorRegistry, FormInitialDataFactory, Mdot0582bFormCalculator, Mdot0582bRegistrations), validators (Mdot0582bValidator), PDF filler (Mdot0582bPdfFiller), 3 local DS, 3 remote DS, 3 domain repo interfaces, 3 impl repos, 9 use cases.
- Screens: FormsListScreen, FormGalleryScreen, MdotHubScreen, FormViewerScreen.
- Providers: InspectorFormProvider, FormExportProvider, DocumentProvider.
- Widgets: FormAccordion, HubHeaderContent, FormThumbnail, HubQuickTestContent, HubProctorContent, StatusPillBar, SummaryTiles.
- Integration: Depends on entries (form attachment), projects (project-scoped), pdf (PDF filling). Required by entries (form attachment manager), toolbox (navigation).
- Frontmatter: feature: forms, type: overview, scope: Inspection form management and PDF generation, updated: 2026-03-30.

#### Step 7.1.2: Create forms architecture
Create `.claude/docs/features/feature-forms-architecture.md` using the architecture format. Content from ground truth:
- Data Model: InspectorForm (template definition), FormResponse (user's filled response), FormExport (exported PDF record), AutoFillResult.
- Layer structure: data/ (datasources/local, datasources/remote, models, repositories, services, registries, validators, pdf), domain/ (repositories, usecases), presentation/ (providers, screens, widgets, utils), di/.
- State Management: InspectorFormProvider, FormExportProvider, DocumentProvider.
- Repository Pattern: 3 interfaces (InspectorFormRepository, FormResponseRepository, FormExportRepository) + 3 impls.
- DI: forms_providers.dart (providers/repos) + forms_init.dart (registry initialization).
- Patterns: Registry pattern — FormScreenRegistry, FormPdfFillerRegistry, FormValidatorRegistry, FormCalculatorRegistry allow extensible form types. Currently MDOT 0582b is the primary registered form. Calculator pattern for field auto-computation. Two-phase init via forms_init.dart.

### Sub-phase 7.2: Calculator Documentation
**Files:**
- Create: `.claude/docs/features/feature-calculator-overview.md`
- Create: `.claude/docs/features/feature-calculator-architecture.md`
**Agent**: general-purpose

#### Step 7.2.1: Create calculator overview
Create `.claude/docs/features/feature-calculator-overview.md` using the overview format. Content from ground truth:
- Purpose: Construction calculation tools — HMA tonnage, concrete cubic yards, area/volume/linear calculations, with calculation history.
- Key Responsibilities: Construction-specific calculations, calculation history persistence/sync.
- Key Files: `di/calculator_providers.dart`, CalculationHistory model, CalculatorService, CalculationHistoryLocalDatasource, CalculationHistoryRemoteDatasource, CalculationHistoryRepository (interface), CalculationHistoryRepositoryImpl.
- Screens: CalculatorScreen.
- Providers: CalculatorProvider.
- Integration: Standalone feature. Required by toolbox (navigation).
- Frontmatter: feature: calculator, type: overview, scope: Construction calculation tools with history, updated: 2026-03-30.

#### Step 7.2.2: Create calculator architecture
Create `.claude/docs/features/feature-calculator-architecture.md` using the architecture format. Content from ground truth:
- Data Model: CalculationHistory (stores past calculations).
- Layer structure: data/ (datasources/local, datasources/remote, models, services, repositories), domain/ (repositories), presentation/ (providers, screens), di/.
- State Management: CalculatorProvider.
- Repository Pattern: CalculationHistoryRepository (interface) + CalculationHistoryRepositoryImpl.
- DI: calculator_providers.dart.
- Patterns: Service pattern — CalculatorService holds the calculation logic (HMA tonnage, concrete cubic yards, area/volume/linear). History is persisted via repository pattern with local+remote datasources for sync.

### Sub-phase 7.3: Gallery Documentation
**Files:**
- Create: `.claude/docs/features/feature-gallery-overview.md`
- Create: `.claude/docs/features/feature-gallery-architecture.md`
**Agent**: general-purpose

#### Step 7.3.1: Create gallery overview
Create `.claude/docs/features/feature-gallery-overview.md` using the overview format. Content from ground truth:
- Purpose: Photo gallery browsing — grid view, date filtering, full-screen viewer.
- Key Responsibilities: Photo browsing across project, date-based filtering, full-screen photo viewing.
- Key Files: `di/gallery_providers.dart`, GalleryProvider, GalleryScreen, domain barrel.
- Screens: GalleryScreen.
- Providers: GalleryProvider.
- Integration: Depends on photos (data source). Required by toolbox (navigation).
- Frontmatter: feature: gallery, type: overview, scope: Photo gallery browsing and viewing, updated: 2026-03-30.

#### Step 7.3.2: Create gallery architecture
Create `.claude/docs/features/feature-gallery-architecture.md` using the architecture format. Content from ground truth:
- Data Model: Uses Photo model from photos feature (no own models).
- Layer structure: presentation/ (screens, providers), domain/ (barrel only), di/.
- State Management: GalleryProvider (manages grid view state, date filters, viewer state).
- No repository pattern — reads from photos feature's PhotoRepository.
- DI: gallery_providers.dart.
- Patterns: Lightweight presentation feature. No data layer — delegates to photos feature for data access. Gallery-specific view state (grid layout, date filtering, full-screen mode) managed by GalleryProvider.

### Sub-phase 7.4: Todos Documentation
**Files:**
- Create: `.claude/docs/features/feature-todos-overview.md`
- Create: `.claude/docs/features/feature-todos-architecture.md`
**Agent**: general-purpose

#### Step 7.4.1: Create todos overview
Create `.claude/docs/features/feature-todos-overview.md` using the overview format. Content from ground truth:
- Purpose: Task management — create, track, and prioritize to-do items.
- Key Responsibilities: Todo CRUD, priority levels (low/normal/high), due date tracking.
- Key Files: `di/todos_providers.dart`, TodoItem model, TodoItemLocalDatasource, TodoItemRemoteDatasource, TodoItemRepository (interface), TodoItemRepositoryImpl, TodoProvider, TodosScreen.
- Screens: TodosScreen.
- Providers: TodoProvider.
- Integration: Standalone feature. Required by toolbox (navigation).
- Frontmatter: feature: todos, type: overview, scope: Task management with priorities, updated: 2026-03-30.

#### Step 7.4.2: Create todos architecture
Create `.claude/docs/features/feature-todos-architecture.md` using the architecture format. Content from ground truth:
- Data Model: TodoItem (title, description, due date, priority: low/normal/high).
- Layer structure: data/ (datasources/local, datasources/remote, models, repositories), domain/ (repositories), presentation/ (providers, screens), di/.
- State Management: TodoProvider.
- Repository Pattern: TodoItemRepository (interface) + TodoItemRepositoryImpl.
- DI: todos_providers.dart.
- Patterns: Standard clean architecture CRUD feature. Single model, single repo, local+remote datasources for sync. Priority enum for task importance.

---

## Verification

After all phases complete, run grep checks for phantom references:
- Grep all `.claude/docs/features/` files for class names that don't exist in `lib/features/`
- Grep for file paths referenced in Key Files tables that don't exist on disk
- Verify all 34 files exist (13 architecture + 13 overview + 8 new)

---

## Dispatch Groups

| Group | Phases | Parallelism | Notes |
|-------|--------|-------------|-------|
| 1 | 5.1–5.6 | 6 parallel agents | High-priority rewrites: auth, settings, projects, entries, sync, toolbox |
| 2 | 5.7–5.13 | 7 parallel agents | Remaining rewrites: contractors, dashboard, locations, pdf, photos, quantities, weather |
| 3 | 6.1–6.13 | 13 parallel agents | All overview updates |
| 4 | 7.1–7.4 | 4 parallel agents | New feature doc pairs |
| Verify | Verification | 1 agent | Grep checks after all groups complete |
