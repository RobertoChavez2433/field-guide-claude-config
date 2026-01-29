# Auto-Fill Architecture

## Component Hierarchy

```
┌──────────────────────────────────────────────────────────────┐
│                         main.dart                             │
│                  (Global Provider Tree)                       │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  Services (Singleton - No State)                              │
│  ├── AutoFillEngine                                           │
│  ├── AutoFillContextBuilder                                   │
│  ├── FormParsingService                                       │
│  ├── FormPdfService                                           │
│  └── FieldRegistryService                                     │
│                                                                │
│  Repositories (Data Access)                                   │
│  ├── InspectorFormRepository                                  │
│  ├── FormResponseRepository                                   │
│  ├── FormFieldRegistryRepository                              │
│  ├── ProjectRepository                                        │
│  ├── ContractorRepository                                     │
│  ├── LocationRepository                                       │
│  └── DailyEntryRepository                                     │
│                                                                │
│  Providers (Global State)                                     │
│  ├── ProjectProvider                                          │
│  ├── ContractorProvider                                       │
│  ├── LocationProvider                                         │
│  ├── DailyEntryProvider                                       │
│  └── PreferencesService                                       │
│                                                                │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ App Navigation
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    FormFillScreen                             │
│               (Screen-Level Provider)                         │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  ChangeNotifierProvider(                                      │
│    create: (context) => FormFillProvider(                     │
│      context.read<InspectorFormRepository>(),     ◄───────────┼── Inject
│      context.read<FormResponseRepository>(),      ◄───────────┼── from
│      context.read<FormFieldRegistryRepository>(), ◄───────────┼── global
│      context.read<AutoFillEngine>(),              ◄───────────┼── tree
│    ),                                                          │
│    child: _FormFillScreenContent(),                           │
│  )                                                             │
│                                                                │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ User Interaction
                            ▼
┌──────────────────────────────────────────────────────────────┐
│               Auto-Fill Flow (Runtime)                        │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  1. User taps "Auto-Fill" button                              │
│                                                                │
│  2. AutoFillContextBuilder.buildContext()                     │
│     ├── Read PreferencesService (inspector data)              │
│     ├── Read ProjectProvider (project data)                   │
│     ├── Read ContractorProvider (contractor data)             │
│     ├── Read LocationProvider (location data)                 │
│     └── Read DailyEntryProvider (entry data)                  │
│     └── Return AutoFillContext                                │
│                                                                │
│  3. FormFillProvider.autoFillAll(context)                     │
│     └── AutoFillEngine.autoFill()                             │
│         ├── Resolve inspector fields                          │
│         ├── Resolve project fields                            │
│         ├── Resolve contractor fields                         │
│         ├── Resolve location fields                           │
│         ├── Resolve weather fields                            │
│         ├── Resolve entry fields                              │
│         └── Apply carry-forward cache                         │
│         └── Return AutoFillResults                            │
│                                                                │
│  4. FormFillProvider applies results                          │
│     ├── Update fieldValues map                                │
│     ├── Track autoFillResults map (provenance)                │
│     ├── Skip userEditedFields (unless force)                  │
│     └── notifyListeners()                                     │
│                                                                │
│  5. UI rebuilds with auto-filled values                       │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌─────────────────┐
│  User Profile   │─┐
│  (Preferences)  │ │
└─────────────────┘ │
                    │
┌─────────────────┐ │
│  Project Data   │─┤
│  (Repository)   │ │
└─────────────────┘ │
                    │
┌─────────────────┐ │         ┌──────────────────┐
│ Contractor Data │─┼────────▶│ Context Builder  │
│  (Repository)   │ │         └──────────────────┘
└─────────────────┘ │                 │
                    │                 │ AutoFillContext
┌─────────────────┐ │                 ▼
│ Location Data   │─┤         ┌──────────────────┐
│  (Repository)   │ │         │  AutoFillEngine  │
└─────────────────┘ │         └──────────────────┘
                    │                 │
┌─────────────────┐ │                 │ AutoFillResults
│   Entry Data    │─┤                 ▼
│  (Repository)   │ │         ┌──────────────────┐
└─────────────────┘ │         │ FormFillProvider │
                    │         └──────────────────┘
┌─────────────────┐ │                 │
│ Carry-Forward   │─┘                 │ Field Values
│     Cache       │                   ▼
└─────────────────┘           ┌──────────────────┐
                              │   UI (Widgets)   │
                              └──────────────────┘
```

## Component Responsibilities

### AutoFillEngine
**Type**: Stateless Service (Singleton)
**Purpose**: Pure logic for resolving field values from context
**Input**: Form, Context, Fields, Existing Values
**Output**: AutoFillResults (with provenance tracking)
**Location**: Global Provider Tree

### AutoFillContextBuilder
**Type**: Stateless Service (Singleton)
**Purpose**: Aggregate data from multiple providers into AutoFillContext
**Input**: BuildContext, projectId, entryId
**Output**: AutoFillContext
**Location**: Global Provider Tree

### FormFillProvider
**Type**: ChangeNotifier (Per-Screen State)
**Purpose**: Manage form state, user edits, auto-fill results
**Input**: Form ID, Response ID (optional)
**Output**: Field values, auto-fill provenance, save/submit actions
**Location**: Screen-Level Provider (NOT global)

### AutoFillContext
**Type**: Immutable Data Class
**Purpose**: Snapshot of all data sources for auto-filling
**Contains**: Inspector, Project, Contractor, Location, Entry, Weather, Cache
**Lifetime**: Single auto-fill operation

### AutoFillResult
**Type**: Immutable Data Class
**Purpose**: Tracks value, source, confidence for a single field
**Contains**: fieldName, value, source, confidence, sourceDescription, isUserEdited
**Lifetime**: Until field is cleared or overwritten

## Dependency Injection

```
Global Services (Provided by main.dart):
├── AutoFillEngine               (singleton)
├── AutoFillContextBuilder       (singleton)
├── InspectorFormRepository      (singleton)
├── FormResponseRepository       (singleton)
├── FormFieldRegistryRepository  (singleton)
└── Data Providers               (singletons)

Screen-Level Provider (Injected from global):
└── FormFillProvider(
      context.read<InspectorFormRepository>(),
      context.read<FormResponseRepository>(),
      context.read<FormFieldRegistryRepository>(),
      context.read<AutoFillEngine>(),
    )
```

## State Management

### Global State
- Project list, selected project
- Contractor list for project
- Location list for project
- Entry list for project
- Inspector profile preferences

### Screen State (FormFillProvider)
- Current form
- Current response (if editing)
- Field values (Map<String, String>)
- Auto-fill results (Map<String, AutoFillResult>)
- User-edited fields (Set<String>)
- Loading/error state

### Immutable State
- AutoFillContext (data snapshot)
- AutoFillResult (provenance record)
- FormFieldEntry (field metadata)

## Auto-Fill Sources

```
┌────────────────────────────────────────────┐
│          Auto-Fill Source Types            │
├────────────────────────────────────────────┤
│                                            │
│  1. inspectorProfile                       │
│     - Name, Phone, Cert, Agency, Initials  │
│                                            │
│  2. project                                │
│     - Number, Name, Client, MDOT fields    │
│                                            │
│  3. contractor                             │
│     - Prime/Sub name, contact, phone       │
│                                            │
│  4. location                               │
│     - Name, description, lat/lng           │
│                                            │
│  5. entry                                  │
│     - Date, activities                     │
│                                            │
│  6. weather                                │
│     - Description, temp high/low           │
│                                            │
│  7. calculated                             │
│     - Formula-based fields                 │
│                                            │
│  8. carryForward                           │
│     - Previous value (fallback)            │
│                                            │
└────────────────────────────────────────────┘
```

## Semantic Name Matching

The AutoFillEngine uses fuzzy semantic matching to resolve fields:

```
Field Name: "inspector"
Matches: inspector, inspector_name, technician, representative

Field Name: "project_number"
Matches: project_number, project_no, job_number, control_section

Field Name: "contractor"
Matches: contractor, contractor_name, prime_contractor, general_contractor

Field Name: "date"
Matches: date, report_date, test_date, inspection_date
```

## Confidence Levels

```
High    - Direct match from primary source (e.g., inspector profile)
Medium  - Indirect match or composite field (not yet implemented)
Low     - Carry-forward from previous value (fallback)
```

## User Edit Protection

```
Auto-Fill Behavior:
├── Field has no value          → Fill
├── Field has auto-filled value → Fill (overwrite)
├── Field has user-edited value → Skip (unless forceOverwrite)
└── Force overwrite enabled     → Fill (always)

User Edit Tracking:
├── setFieldValue(..., markAsEdited: true)  → Add to userEditedFields
├── setFieldValue(..., markAsEdited: false) → Allow auto-fill overwrite
└── clearAutoFilledField(...)               → Remove from both sets
```

## Best Practices

1. **Global vs Screen-Level**
   - Services and repositories: Global
   - Form state: Screen-level

2. **Dependency Injection**
   - Use `context.read<T>()` in screen provider create
   - Don't access providers in constructor

3. **State Isolation**
   - Each form fill session = new FormFillProvider
   - No shared state between forms

4. **Error Handling**
   - Context builder handles missing data gracefully
   - Engine returns null for unresolvable fields
   - Provider tracks errors in state

5. **Performance**
   - AutoFillEngine is O(n) where n = number of fields
   - Context building is async (reads from multiple sources)
   - Only rebuild UI when field values change

## Testing Strategy

### Unit Tests
- AutoFillEngine field resolution
- AutoFillContextBuilder data aggregation
- FormFillProvider state transitions

### Integration Tests
- Full auto-fill flow
- User edit protection
- Save/submit workflow

### E2E Tests
- Complete form fill journey
- Auto-fill UX
- Error handling

## See Also

- `lib/main.dart` - Global provider wiring
- `lib/features/toolbox/data/services/auto_fill_engine.dart` - Core logic
- `lib/features/toolbox/data/services/auto_fill_context_builder.dart` - Context building
- `lib/features/toolbox/presentation/providers/form_fill_provider.dart` - State management
- `.claude/docs/form-fill-provider-usage.md` - Usage guide
- `.claude/docs/phase-5-wiring-summary.md` - Wiring summary
