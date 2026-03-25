# Sync & Data Integrity Verification — Dependency Graph

## Overview
Three workstreams: (A) Sync Verification via 6 UI-driven flows, (B) PDF Export Verification, (C) UI Additions for edit/delete capabilities.

## Workstream C: UI Additions (Must Be Built First)

### C1: Location Edit Button
**Direct Changes:**
- `lib/features/projects/presentation/widgets/add_location_dialog.dart:8-98` — Add edit mode (optional `existingLocation` param, pre-fill fields, update vs create)
- `lib/features/projects/presentation/screens/project_setup_screen.dart:415-499` — Add edit IconButton in `_buildLocationsTab()` trailing Row
- `lib/shared/testing_keys/locations_keys.dart` — Add `locationEditButton(id)` key

**Dependencies:**
- `LocationProvider.updateLocation()` at `lib/features/locations/presentation/providers/location_provider.dart:73` — EXISTS, ready
- `Location.copyWith()` at `lib/features/locations/data/models/location.dart:30-48` — EXISTS, ready
- `TestingKeys` facade at `lib/shared/testing_keys/testing_keys.dart` — Needs delegation for new key

### C2: Equipment Edit Button
**Direct Changes:**
- `lib/features/projects/presentation/widgets/add_equipment_dialog.dart:8-98` — Add edit mode (optional `existingEquipment` param)
- `lib/features/projects/presentation/screens/project_setup_screen.dart:699-708` — Add edit onTap to EquipmentChip or replace with Card
- `lib/features/projects/presentation/widgets/equipment_chip.dart:6-33` — Add optional `onEdit` callback
- `lib/shared/testing_keys/contractors_keys.dart` — Add `equipmentEditButton(id)` key

**Dependencies:**
- `EquipmentProvider.updateEquipment()` at `lib/features/contractors/presentation/providers/equipment_provider.dart:196` — EXISTS, ready
- `Equipment.copyWith()` at `lib/features/contractors/data/models/equipment.dart:27-36` — EXISTS, ready

### C3: Calculation History Delete Button
**Direct Changes:**
- `lib/features/calculator/presentation/screens/calculator_screen.dart:653-711` — Add delete IconButton to `_HistoryTile` trailing Row
- `lib/shared/testing_keys/toolbox_keys.dart` — Add `calculationHistoryDeleteButton(id)` key

**Dependencies:**
- `CalculatorProvider.deleteCalculation()` at `lib/features/calculator/presentation/providers/calculator_provider.dart:159` — EXISTS, ready
- `CalculationHistoryLocalDatasource.deleteCalculation()` at `lib/features/calculator/data/datasources/local/calculation_history_local_datasource.dart:74` — EXISTS, ready

### C4: Wire DeletionNotificationBanner
**Direct Changes:**
- `lib/features/projects/presentation/screens/project_list_screen.dart:330-340` — Add `DeletionNotificationBanner()` in body Column (above ProjectImportBanner or after it)
- `lib/features/sync/presentation/widgets/deletion_notification_banner.dart:12-18` — Add testing key to widget

**Dependencies:**
- `DeletionNotificationBanner` at `lib/features/sync/presentation/widgets/deletion_notification_banner.dart` — COMPLETE widget, just needs placement
- `_DeletionNotificationBannerState` at line 20-137 — Full implementation exists
- `DatabaseService` — Already available via Provider in ProjectListScreen

## Workstream A+B: Test Infrastructure (JS Files)

### Direct Changes:
- `tools/debug-server/run-tests.js` — Add `--suite=integrity` mode, dual-device config
- `tools/debug-server/test-runner.js` — Rewrite for integrity suite: sequential flow runner, dual-device orchestration
- `tools/debug-server/device-orchestrator.js` — Add UI command methods (tap, text, scroll, wait, navigate, sync)
- `tools/debug-server/supabase-verifier.js` — Add field-value verification, cascade verification, cleanup sweep
- `tools/debug-server/scenario-helpers.js` — Add integrity flow helpers, PDF verification
- NEW: `tools/debug-server/scenarios/integrity/` — 6 flow files + update + delete + pdf + unassign + cleanup

### Dependencies:
- All 17 synced tables in Supabase (verified to exist)
- Driver endpoints in `lib/core/driver/driver_server.dart` — `/driver/tap`, `/driver/text`, `/driver/navigate`, `/driver/sync`, `/driver/wait`, `/driver/local-record`, `/driver/inject-photo-direct`
- `.env.test` — Admin/inspector credentials, Supabase URL, service role key
- ADB forwarding for S21+ on port 4948
- Windows app on port 4949

## Blast Radius Summary

| Category | Count |
|----------|-------|
| Direct (Dart - C1-C4) | 8 files |
| Direct (JS - A+B) | 5 existing + ~12 new scenario files |
| Dependent | 0 (all provider/repo methods exist) |
| Tests (Dart) | 0 new unit tests needed (UI additions are trivial wiring) |
| Cleanup | 58+ L2 scenario files to delete, 10 L3 files to delete |

## Data Flow (Integrity Suite)

```
run-tests.js --suite=integrity
  ├→ Parse .env.test, configure dual-device ports
  ├→ Login both devices via /driver/tap + /driver/text
  └→ Sequential flow execution:
       F1-F6: /driver/tap → /driver/text → /driver/sync
                → supabase-verifier.getRecord() → assert fields
                → /driver/sync (Windows) → /driver/local-record → assert
       Update: /driver/tap → /driver/text → sync → verify push → verify pull
       PDF: /driver/tap (export) → adb pull → pdf-parse → field assertions
       Delete: /driver/tap (cascade) → sync → verify cascade → verify banner
       Unassign: /driver/tap (untoggle) → sync → verify removal
       Cleanup: sweepSynctestRecords() → hard-delete VRF- prefixed
```

## Key Testing Keys (Ground Truth)

### Project Setup (F1):
- `project_name_field`, `project_number_field`, `project_client_field` — ProjectsTestingKeys
- `project_save_button` — ProjectsTestingKeys
- `project_locations_tab`, `project_contractors_tab`, `project_payitems_tab`, `project_assignments_tab` — TestingKeys (facade)
- `project_add_location_button`, `project_add_equipment_button` — TestingKeys
- `location_name_field`, `location_description_field`, `location_dialog_add` — LocationsTestingKeys via TestingKeys
- `contractor_name_field`, `contractor_save_button`, `contractor_add_button` — ContractorsTestingKeys
- `equipment_name_field`, `equipment_description_field`, `equipment_dialog_add` — TestingKeys
- `pay_item_number_field`, `pay_item_description_field` — QuantitiesTestingKeys

### Entry Editor (F2):
- `add_entry_fab` — NavigationTestingKeys
- `entry_wizard_scroll_view` — EntriesTestingKeys
- `entry_wizard_activities` — EntriesTestingKeys
- `entry_wizard_save_draft` — EntriesTestingKeys

### Calculator (F6):
- `calculator_hma_tab`, `calculator_hma_area`, etc. — ToolboxTestingKeys
- `calculator_save_button` — ToolboxTestingKeys

### Project List:
- `project_card(id)` — TestingKeys
- `project_remove_button(id)` — TestingKeys
