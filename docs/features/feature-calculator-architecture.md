---
feature: calculator
type: architecture
updated: 2026-03-30
---

# Calculator Feature Architecture

## Directory Structure

```
lib/features/calculator/
├── calculator.dart                          # Feature barrel export
├── di/
│   └── calculator_providers.dart            # DI wiring (Tier 4 providers)
├── data/
│   ├── models/
│   │   └── calculation_history.dart         # CalculationHistory model + CalculationType enum
│   ├── services/
│   │   └── calculator_service.dart          # CalculatorService — calculation logic + history factories
│   ├── datasources/
│   │   ├── local/
│   │   │   └── calculation_history_local_datasource.dart   # SQLite datasource
│   │   └── remote/
│   │       └── calculation_history_remote_datasource.dart  # Supabase datasource (sync engine)
│   └── repositories/
│       ├── repositories.dart
│       └── calculation_history_repository_impl.dart        # Impl — delegates to local datasource
├── domain/
│   ├── domain.dart
│   └── repositories/
│       ├── repositories.dart
│       └── calculation_history_repository.dart             # Domain interface
└── presentation/
    ├── providers/
    │   └── calculator_provider.dart         # CalculatorProvider (ChangeNotifier)
    └── screens/
        └── calculator_screen.dart           # CalculatorScreen
```

## Data Layer

### Models

| Model | Purpose |
|-------|---------|
| `CalculationHistory` | Saved calculation record — type, JSON-encoded inputs, JSON-encoded result, optional project/entry association, timestamps |
| `CalculationType` | Enum — `hma`, `concrete`, `area`, `volume`, `linear` |

`CalculationHistory` is **append-only** — no `updatedAt`-driven conflict resolution. Records are created or deleted, never modified. This simplifies sync (insert-only push; no conflict resolution needed).

### Input / Result Types (defined in `calculator_service.dart`)

| Class | Purpose |
|-------|---------|
| `HmaInput` | HMA inputs: `areaSqFt`, `thicknessInches`, `densityPcf` (default 145 pcf) |
| `ConcreteInput` | Concrete inputs: `lengthFt`, `widthFt`, `thicknessInches` |
| `AreaInput` | Area inputs: `lengthFt`, `widthFt` |
| `VolumeInput` | Volume inputs: `lengthFt`, `widthFt`, `depthFt` |
| `LinearInput` | Linear input: `lengthFt`, optional `label` |
| `CalculationResult` | Output: `result` (double), `unit` (string), `description` (formula string) |

### Local Datasource

| Class | Responsibility |
|-------|---------------|
| `CalculationHistoryLocalDatasource` | SQLite CRUD for `calculation_history` table; extends `GenericLocalDatasource<CalculationHistory>` |

### Remote Datasource

| Class | Responsibility |
|-------|---------------|
| `CalculationHistoryRemoteDatasource` | Supabase reads for `calculation_history` table; extends `BaseRemoteDatasource<CalculationHistory>`; consumed by sync engine, not by repository impl |

### Repositories

| Class | Responsibility |
|-------|---------------|
| `CalculationHistoryRepository` | Domain interface — `getRecent`, `getByProjectId`, `getByEntryId`, `getByType`, `create`, `deleteCalculation`, `deleteByProjectId` |
| `CalculationHistoryRepositoryImpl` | Concrete implementation — delegates entirely to `CalculationHistoryLocalDatasource`; no direct remote calls |

## Service Layer

| Class | Location | Responsibility |
|-------|----------|---------------|
| `CalculatorService` | `data/services/calculator_service.dart` | Pure calculation logic (no Flutter, no state) — computes HMA tonnage, concrete CY, area SF, volume CF, linear LF; also constructs `CalculationHistory` records from typed inputs |

### Calculation Formulas

| Type | Formula |
|------|---------|
| HMA Tonnage | `(areaSqFt × thicknessInches / 12 × densityPcf) / 2000` → tons |
| Concrete | `(lengthFt × widthFt × thicknessInches / 12) / 27` → CY |
| Area | `lengthFt × widthFt` → SF |
| Volume | `lengthFt × widthFt × depthFt` → CF |
| Linear | `lengthFt` → LF |

## Domain Layer

### Repository Interface

`CalculationHistoryRepository` defines the domain contract. No use cases layer — `CalculatorProvider` calls the repository directly via the service pattern.

## Presentation Layer

### Providers

| Class | Type | Responsibility |
|-------|------|---------------|
| `CalculatorProvider` | `ChangeNotifier` | Holds `history`, `lastResult`, `isLoading`, `error`; delegates calculations to `CalculatorService`; delegates persistence to `CalculationHistoryRepository`; enforces write guard via `canWrite` callback |

`CalculatorProvider` accepts an optional `CalculatorService` in its constructor for testability; defaults to a fresh `CalculatorService()` instance.

### Write Guard

`CalculatorProvider.canWrite` is a `bool Function()` callback, defaulting to `() => true`. In DI (`calculator_providers.dart`) it is wired to `authProvider.canEditFieldData`, blocking saves and deletes for read-only roles without importing `AuthProvider` into the domain layer.

### Screens

| Screen | Purpose |
|--------|---------|
| `CalculatorScreen` | Main calculator UI — type selector, input fields, result display, history list |

## DI Wiring (`di/calculator_providers.dart`)

`calculatorProviders(...)` returns a `List<SingleChildWidget>` (Tier 4):

- `ChangeNotifierProvider` for `CalculatorProvider` — constructed with `CalculationHistoryRepository` and `canWrite` wired from `AuthProvider.canEditFieldData`

`CalculationHistoryRepository` (the concrete `CalculationHistoryRepositoryImpl`) is constructed upstream in `main.dart` and passed in as a parameter.

## Sync Integration

Calculation history participates in the standard change-log sync system:

- SQLite triggers on `calculation_history` auto-populate the `change_log` table on INSERT/DELETE
- The sync engine reads the change log and pushes deltas to Supabase using `CalculationHistoryRemoteDatasource`
- No per-record sync status field; history is append-only so conflict resolution is not needed

## Architectural Patterns

### Service Pattern
`CalculatorService` holds all calculation logic. `CalculatorProvider` composes the service and repository rather than implementing calculation logic itself. This keeps the provider thin and makes calculation logic independently testable.

### No Use Cases Layer
Calculator is a simpler feature with a single provider and no cross-cutting orchestration. The service layer substitutes for a formal use cases layer; this is an intentional simplification.

### Append-Only History
`CalculationHistory` records are never modified after creation. To correct a calculation, the user deletes the old record and saves a new one. This simplifies sync (insert-only push) and provides a complete audit trail.

## Relationships to Other Features

| Feature | Relationship |
|---------|-------------|
| **Toolbox** | Hosts the calculator tab; navigates to `CalculatorScreen` |
| **Auth** | `AuthProvider.canEditFieldData` gates write operations via `canWrite` callback |
| **Sync** | Change-log triggers on `calculation_history` table drive push to Supabase |
