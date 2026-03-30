---
feature: calculator
type: overview
scope: Construction calculation tools with history
updated: 2026-03-30
---

# Calculator Feature Overview

## Purpose

The Calculator feature provides construction-specific calculation tools for inspectors: HMA (Hot Mix Asphalt) tonnage, concrete cubic yards, area (SF), volume (CF), and linear (LF) measurements. Results can be saved to a calculation history that is persisted locally and synced to Supabase via the change-log trigger system.

## Key Responsibilities

- **Construction Calculations**: HMA tonnage, concrete cubic yards, area, volume, and linear measurements via `CalculatorService`
- **Calculation History**: Persist and retrieve past calculations (append-only — no updates, only creates and deletes)
- **Write Gating**: `CalculatorProvider.canWrite` is wired to `AuthProvider.canEditFieldData`; saves and deletes are blocked for read-only roles
- **Project/Entry Association**: Calculations can be optionally linked to a project or entry via `projectId` / `entryId`

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/calculator/di/calculator_providers.dart` | DI wiring — registers `CalculatorProvider`, wires `canWrite` from `AuthProvider` |
| `lib/features/calculator/data/models/calculation_history.dart` | `CalculationHistory` model + `CalculationType` enum |
| `lib/features/calculator/data/services/calculator_service.dart` | `CalculatorService` — all calculation logic and history record factories |
| `lib/features/calculator/data/datasources/local/calculation_history_local_datasource.dart` | `CalculationHistoryLocalDatasource` — SQLite reads/writes |
| `lib/features/calculator/data/datasources/remote/calculation_history_remote_datasource.dart` | `CalculationHistoryRemoteDatasource` — Supabase reads (used by sync engine) |
| `lib/features/calculator/data/repositories/calculation_history_repository_impl.dart` | `CalculationHistoryRepositoryImpl` — delegates to local datasource |
| `lib/features/calculator/domain/repositories/calculation_history_repository.dart` | `CalculationHistoryRepository` — domain interface |
| `lib/features/calculator/presentation/providers/calculator_provider.dart` | `CalculatorProvider` — state management, delegates to service + repository |
| `lib/features/calculator/presentation/screens/calculator_screen.dart` | `CalculatorScreen` — main UI |

## Screens (1)

| Screen | Route Trigger |
|--------|--------------|
| `CalculatorScreen` | Navigated from Toolbox hub |

## Providers (1)

| Provider | Responsibility |
|----------|---------------|
| `CalculatorProvider` | Calculation execution, history loading/saving/deleting, last result state, write gating |

## Data Sources

- **SQLite**: Local history persistence via `CalculationHistoryLocalDatasource`
- **Supabase**: Remote sync via `CalculationHistoryRemoteDatasource` (consumed by sync engine; not directly by repository impl)

## Integration Points

**Depends on:**
- `auth` — `AuthProvider.canEditFieldData` gates write operations
- `core/database` — SQLite via `DatabaseService`

**Required by:**
- `toolbox` — Navigation entry point for the calculator tab

## Offline Behavior

Fully offline-capable. All reads and writes go through SQLite. Sync to Supabase is handled automatically by the change-log trigger system — no network required for calculations or history access.

## Edge Cases & Limitations

- **Append-Only History**: `CalculationHistory` has no `updatedAt`-driven conflict resolution. Records are never modified; only created or deleted.
- **No Use Cases Layer**: Calculator is a simpler feature — logic lives in `CalculatorService` consumed directly by `CalculatorProvider`. No separate use case classes.
- **Remote Datasource Not Wired to Repository**: `CalculationHistoryRepositoryImpl` delegates only to the local datasource. The remote datasource is used exclusively by the sync engine.
