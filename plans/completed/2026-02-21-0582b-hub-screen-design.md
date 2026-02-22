# 0582B Hub Screen — Detailed Implementation Plan

**Date:** 2026-02-21 (design) / 2026-02-22 (implementation plan)
**Status:** Approved — Ready to build
**Scope:** Rewrite the 0582B form as an accordion dashboard. Delete 4 old screens. All backend logic (calculators, models, repos, providers) stays as-is.
**Mockups:** Prototyped via html-sync + Playwright (Session 438). 5-step flow validated.

---

## Architecture Decisions (from brainstorming)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Screen strategy | **Inline everything** | Build fresh accordion widgets. Delete `form_fill_screen.dart`, `proctor_entry_screen.dart`, `quick_test_entry_screen.dart`, `weights_entry_screen.dart`. No wrapping old screens. |
| State management | **Single StatefulWidget** | `_MdotHubScreenState` owns all local state: expanded section index, field controllers, calc results. Section widgets are stateless, receive data via params + callbacks. |
| Accordion widget | **Custom FormAccordion** | Built from scratch with `AnimatedCrossFade` / `SizeTransition`. Full control over accent colors, letter icons, summary tiles, border styling. No `ExpansionTile`. |
| Send flow | **Auto-advance** | After SEND: collapse current → show summary tiles → auto-expand next section → scroll to it (250ms delay). |
| Multi-test loop | **Stay expanded** | After sending Test #N, fields reset, test_number increments, section stays expanded for next test. "Last Sent" banner appears. User taps another section header to leave. |
| Layout pattern | Accordion (Option C) | Best info density; see proctor data while entering test |
| Section visibility | One expanded at a time | Focused entry + data visibility via summary tiles |
| Color coding | Unique accent per section | Visual distinction, quick section ID |
| Field height | 48dp minimum | Glove-friendly per construction domain |
| Action buttons | All say "SEND TO FORM" | Consistent mental model (except Header: "CONFIRM HEADER") |

---

## File Plan

### New files (all under `lib/features/forms/presentation/`)

| File | Purpose | ~Lines |
|------|---------|--------|
| `screens/mdot_hub_screen.dart` | Main hub StatefulWidget — scaffold, state, section orchestration | 400-500 |
| `widgets/form_accordion.dart` | Reusable accordion shell — letter icon, accent border, expand/collapse animation, summary slot | 120 |
| `widgets/status_pill_bar.dart` | Horizontal scrollable pill row — Pending/Entering/Sent per section | 80 |
| `widgets/summary_tiles.dart` | 3-column grid of bold value + tiny label tiles | 60 |
| `widgets/completion_banner.dart` | "Form Complete" banner with + New Test / Preview PDF buttons | 50 |
| `widgets/hub_header_content.dart` | Header section expanded content — 10 auto-filled fields + confirm button | 120 |
| `widgets/hub_proctor_content.dart` | Proctor section expanded content — 5 inputs + 5 calc fields + send button | 150 |
| `widgets/hub_quick_test_content.dart` | Quick Test expanded content — 16 fields + last-sent banner + send button | 180 |
| `widgets/hub_weights_content.dart` | Weights expanded content — dynamic readings + delta validation + send button | 100 |

**Total new**: ~1,260 lines across 9 files

### Files to delete

| File | Reason |
|------|--------|
| `screens/form_fill_screen.dart` | Replaced by `mdot_hub_screen.dart` |
| `screens/proctor_entry_screen.dart` | Logic inlined into `hub_proctor_content.dart` |
| `screens/quick_test_entry_screen.dart` | Logic inlined into `hub_quick_test_content.dart` |
| `screens/weights_entry_screen.dart` | Logic inlined into `hub_weights_content.dart` |
| `widgets/mdot_0582b_form_widget.dart` | Replaced by accordion sections |
| `widgets/form_header_section.dart` | Replaced by `hub_header_content.dart` |
| `widgets/form_table_section.dart` | Replaced by test section in hub |
| `widgets/form_field_cell.dart` | Replaced by standard TextFormField with theme styling |
| `widgets/calculated_field_cell.dart` | Replaced by styled read-only fields in section content |
| `widgets/smart_input_bar.dart` | Not needed — fields are standard TextFormFields, no cell-tap model |

### Files to modify

| File | Change |
|------|--------|
| `core/router/app_router.dart` | Update route for `/form/:responseId` to point to `MdotHubScreen`. Remove routes for `/form/:responseId/test`, `/form/:responseId/proctor`, `/form/:responseId/weights`. |
| `presentation/screens/screens.dart` | Update barrel exports |
| `presentation/widgets/widgets.dart` | Update barrel exports |
| `shared/testing_keys/toolbox_keys.dart` | Add new testing keys for hub sections |

### Files unchanged

- `data/models/form_response.dart` — FormResponse model
- `data/services/mdot_0582b_calculator.dart` — Calculations
- `data/services/one_point_calculator.dart` — One-point algorithm
- `data/services/auto_fill_service.dart` — Header auto-fill
- `data/services/form_pdf_service.dart` — PDF generation
- `presentation/providers/inspector_form_provider.dart` — All provider methods
- `presentation/screens/forms_list_screen.dart` — List screen
- `presentation/screens/form_viewer_screen.dart` — Read-only viewer
- `presentation/widgets/form_thumbnail.dart` — Form thumbnail

---

## Widget Hierarchy

```
MdotHubScreen (StatefulWidget)
├── Scaffold
│   ├── AppBar: "MDOT 0582B" + [PDF] [Save] actions
│   └── Body: Column
│       ├── StatusPillBar (sticky below appbar)
│       │   └── SingleChildScrollView(horizontal)
│       │       └── Row of _PillChip widgets (Header, P#1, Test#N, Weights)
│       ├── CompletionBanner (conditional — shown when all sections sent)
│       │   └── Card with checkmark + stats + [+ New Test] [Preview PDF]
│       └── Expanded → ListView
│           ├── FormAccordion(letter:'H', accent:gray, expanded: _exp==0)
│           │   ├── collapsed: subtitle "864130 · John Smith · 02/21/2026"
│           │   └── expanded: HubHeaderContent
│           │       ├── 5 rows × 2 fields (TextFormField, 48dp, dashed border + auto tag)
│           │       └── FilledButton "CONFIRM HEADER"
│           ├── FormAccordion(letter:'P', accent:amber, expanded: _exp==1)
│           │   ├── collapsed: SummaryTiles(MDD, OMC, WetPCF) + "Edit Proctor →"
│           │   └── expanded: HubProctorContent
│           │       ├── DropdownButtonFormField(Chart Type)
│           │       ├── 2 rows × 2 fields (Moisture%, Volume, WetSoil+Mold, Mold)
│           │       ├── Divider
│           │       ├── 5 calculated fields (green bg, read-only, tagged)
│           │       └── FilledButton "SEND TO FORM"
│           ├── FormAccordion(letter:'T', accent:cyan, expanded: _exp==2)
│           │   ├── collapsed: SummaryTiles(Dry, Wet, Comp%) + "Edit Test →"
│           │   └── expanded: HubQuickTestContent
│           │       ├── "Last Sent" banner (conditional, after 1st test)
│           │       ├── 2 dropdowns (Orig/Recheck, Item of Work)
│           │       ├── 7 rows × 2 fields (+ 1 row × 3 for L/R/Grade)
│           │       ├── 2 calculated fields (MaxDensity tagged P#1, %Compaction)
│           │       ├── Station (full width)
│           │       └── FilledButton "SEND TO FORM"
│           └── FormAccordion(letter:'W', accent:blue, expanded: _exp==3)
│               ├── collapsed: SummaryTiles(R1, R2, Δ+Pass/Fail) + "Edit →"
│               └── expanded: HubWeightsContent
│                   ├── N rows × 2 fields (Reading 1, Reading 2)
│                   ├── Δ validation chip ("Δ 8g — Pass (≤10g)")
│                   ├── DashedButton "+ Add Reading" (max 5)
│                   └── FilledButton "SEND TO FORM"
```

---

## State Design

```dart
class _MdotHubScreenState extends State<MdotHubScreen> {
  // === Loading ===
  FormResponse? _response;
  bool _loading = true;

  // === Section control ===
  int _expandedSection = 0; // 0=Header, 1=Proctor, 2=Test, 3=Weights, -1=none
  final _scrollController = ScrollController();
  final _sectionKeys = List.generate(4, (_) => GlobalKey()); // for scroll-to

  // === Section status (derived from _response data) ===
  // headerConfirmed: _response.parsedHeaderData.isNotEmpty && confirmed flag
  // proctorSent: _response.parsedProctorRows.isNotEmpty
  // testsSent: _response.parsedTestRows.isNotEmpty
  // weightsSent: proctor_rows[0]['weights_20_10'] != null

  // === Header fields (10 controllers) ===
  late final Map<String, TextEditingController> _headerControllers;
  bool _headerConfirmed = false;

  // === Proctor fields (5 controllers) ===
  String _chartType = 'T-99'; // dropdown
  late final _moistureCtrl, _volumeCtrl, _wetSoilMoldCtrl, _moldCtrl;
  Map<String, dynamic>? _proctorCalcResult; // from calculateProctorChain()
  int _proctorNumber = 1;
  DateTime? _proctorSentAt;

  // === Quick Test fields (16 controllers) ===
  String _origRecheck = 'Original'; // dropdown
  late final _depthCtrl, _countsMcCtrl, _countsDcCtrl, _dryDensityCtrl,
             _wetDensityCtrl, _moisturePcfCtrl, _moisturePctCtrl,
             _stationCtrl, _leftCtrl, _rightCtrl, _belowGradeCtrl;
  String _itemOfWork = ''; // dropdown
  Map<String, double?>? _testCalcResult; // from calculate()
  int _testNumber = 1;
  Map<String, dynamic>? _lastSentTest; // for "Last Sent" banner
  DateTime? _lastTestSentAt;

  // === Weights fields (dynamic, up to 5 pairs) ===
  List<(TextEditingController, TextEditingController)> _weightPairs = [];
  // Start with 1 pair, "+ Add Reading" adds more (max 5)
  DateTime? _weightsSentAt;

  // === Calculator instances ===
  final _calculator = const Mdot0582BCalculator();
  final _autoFillService = const AutoFillService();
}
```

### Key State Methods

| Method | Trigger | Action |
|--------|---------|--------|
| `_initFromResponse()` | `initState` / after load | Populate controllers from existing `_response` data (resume editing) |
| `_expandSection(int idx)` | Tap accordion header | `setState(() => _expandedSection = idx)` + scroll-to via `_sectionKeys[idx]` |
| `_confirmHeader()` | Tap CONFIRM HEADER | Collect header fields → `provider.updateResponse()` → set `_headerConfirmed = true` → `_expandSection(1)` |
| `_recalcProctor()` | Any proctor field onChange | Call `_calculator.calculateProctorChain()` → update `_proctorCalcResult` |
| `_sendProctor()` | Tap SEND TO FORM (proctor) | Collect proctor map → `provider.appendMdot0582bProctorRow()` → set `_proctorSentAt` → `_expandSection(2)` |
| `_recalcTest()` | Wet density or moisture onChange | Call `_calculator.calculate()` → update `_testCalcResult` |
| `_sendTest()` | Tap SEND TO FORM (test) | Collect test map → `provider.appendMdot0582bTestRow()` → save to `_lastSentTest` → reset fields → increment `_testNumber` → stay expanded |
| `_sendWeights()` | Tap SEND TO FORM (weights) | Collect weights list → `provider.updateMdot0582bProctorWeights()` → set `_weightsSentAt` → `_expandSection(-1)` (all collapsed, completion) |
| `_addWeightPair()` | Tap + Add Reading | Add controller pair (max 5) |
| `_startNewTest()` | Tap + New Test (completion) | Reset test fields + `_expandSection(2)` |
| `_previewPdf()` | Tap Preview PDF | Same logic as current — `FormPdfService.generatePreviewPdf()` → navigate to viewer |

### Derived Status (for pill bar)

```dart
SectionStatus get _headerStatus => _headerConfirmed ? SectionStatus.sent : SectionStatus.entering;
SectionStatus get _proctorStatus => _proctorSentAt != null ? SectionStatus.sent
    : _expandedSection == 1 ? SectionStatus.entering : SectionStatus.pending;
SectionStatus get _testStatus => _lastSentTest != null ? SectionStatus.sent
    : _expandedSection == 2 ? SectionStatus.entering : SectionStatus.pending;
SectionStatus get _weightsStatus => _weightsSentAt != null ? SectionStatus.sent
    : _expandedSection == 3 ? SectionStatus.entering : SectionStatus.pending;
bool get _isComplete => _headerConfirmed && _proctorSentAt != null
    && _lastSentTest != null && _weightsSentAt != null;
```

---

## Provider Wiring (existing methods — no changes needed)

| Action | Provider Method | Data Flow |
|--------|----------------|-----------|
| Load response | `provider.loadResponseById(responseId)` | → `_response` |
| Save header | `provider.updateResponse(response.copyWith(headerData: jsonEncode(data)))` | headerControllers → JSON → FormResponse |
| Send proctor | `provider.appendMdot0582bProctorRow(responseId: id, row: proctorMap)` | 10 fields → Map → responseData.proctor_rows |
| Send test | `provider.appendMdot0582bTestRow(responseId: id, row: testMap)` | 19 fields → Map → responseData.test_rows |
| Send weights | `provider.updateMdot0582bProctorWeights(responseId: id, proctorNumber: n, weights: list)` | weight strings → proctor_rows[n].weights_20_10 |
| Preview PDF | `FormPdfService.generatePreviewPdf(response)` | response → PDF bytes → viewer |

---

## Build Phases

### Phase 1: Scaffold + FormAccordion + StatusPillBar

**Files created**:
- `widgets/form_accordion.dart`
- `widgets/status_pill_bar.dart`
- `screens/mdot_hub_screen.dart` (skeleton)

**What to build**:
1. `FormAccordion` — Custom widget with:
   - 36×36 letter icon with rounded rect (10px radius) + accent background
   - Title + subtitle text
   - Status badge (Pending/Entering/Sent) with accent color
   - `AnimatedCrossFade` between collapsed content (summary slot) and expanded content (child slot)
   - Accent-colored left border (1.5px at 0.3 opacity) when expanded
   - `surfaceElevated` background, 14px radius
   - Tap header to toggle → calls `onTap`
2. `StatusPillBar` — Horizontal scrollable row:
   - Each pill: 5px colored dot + 11px label, 20px radius chip
   - Colors: gray (pending), accent (entering), green (sent)
3. `MdotHubScreen` skeleton — Scaffold + AppBar + StatusPillBar + ListView with 4 empty `FormAccordion` shells
4. Update `app_router.dart` — Point form route to `MdotHubScreen`

**Acceptance criteria**:
- [ ] 4 accordion panels render with correct letter icons and accent colors
- [ ] Tapping a header expands it and collapses others
- [ ] Status pill bar shows 4 pills all in "Pending" state
- [ ] `flutter analyze` passes with 0 issues
- [ ] Route `/form/:responseId` loads the new hub screen

---

### Phase 2: Header Section

**Files created**:
- `widgets/hub_header_content.dart`

**What to build**:
1. 10 `TextFormField` widgets in 2-per-row `Row` layout (48dp height)
2. Each field shows dashed border + "auto" tag when auto-filled, solid border when user-edited
3. Auto-fill via `AutoFillService.buildHeaderData()` sourced from `ProjectProvider` + `PreferencesService`
4. "CONFIRM HEADER" green `FilledButton` (48dp, 12px radius, full width)
5. On confirm: save header → collapse → show subtitle with job# + name + date
6. Auto-advance to Proctor section

**Acceptance criteria**:
- [ ] Header expands on load with 10 auto-filled fields
- [ ] Fields show "auto" tag with dashed border
- [ ] Tapping CONFIRM saves headerData to provider and collapses section
- [ ] Collapsed header shows "864130 · John Smith · 02/21/2026" subtitle format
- [ ] Proctor section auto-expands after confirm
- [ ] Status pill updates Header → green

---

### Phase 3: Proctor Section

**Files created**:
- `widgets/hub_proctor_content.dart`
- `widgets/summary_tiles.dart`

**What to build**:
1. `SummaryTiles` — Reusable 3-column grid: bold value + tiny label, `surface` bg, 10px radius
2. Chart Type dropdown (T-99 / T-180 / Cone)
3. 4 input fields: Moisture%, Volume Mold, Wet Soil+Mold, Mold (2-per-row, 48dp)
4. Divider
5. 5 calculated fields (green `statusSuccess` bg at 0.06 opacity, read-only):
   - Wet Soil (g), Wet Soil (lbs), Compacted Wet PCF — from `calculateProctorChain()`
   - Max Density (pcf) tagged "1-pt", Optimum Moisture % tagged "1-pt" — from `OnePointCalculator`
6. Live recalc on any input change
7. Validation: if out of bounds → MDD/OMC show "--", SEND disabled
8. "SEND TO FORM" amber button
9. On send: `appendMdot0582bProctorRow()` → collapse → show SummaryTiles(MDD, OMC, WetPCF) + "Edit Proctor →"
10. Auto-advance to Quick Test

**Acceptance criteria**:
- [ ] Proctor section shows 5 input fields + dropdown
- [ ] Calculations update live as user types
- [ ] Max Density and OMC show values from OnePointCalculator with "1-pt" tag
- [ ] Out-of-bounds inputs show "--" and disable SEND
- [ ] SEND saves proctor row and collapses to summary tiles
- [ ] SummaryTiles show MDD | OMC | Wet PCF values
- [ ] "Edit Proctor →" re-expands section
- [ ] Quick Test auto-expands after send
- [ ] Status pill updates P#1 → green

---

### Phase 4: Quick Test Section

**Files created**:
- `widgets/hub_quick_test_content.dart`

**What to build**:
1. "Using Proctor #1 · MDD 103.4" subtitle (from proctor data)
2. "Last Sent" banner (conditional, after first test): mini card with Dry/Wet/Comp% + Edit button
3. 2 dropdowns: Orig/Recheck, Item of Work
4. 12 text fields in 2-per-row layout:
   - Depth, Counts MC, Counts DC, Dry Density, Wet Density, Moisture PCF, Moisture %
   - Station (full width)
   - Left ft, Right ft, Below Grade ft (3-per-row)
5. 2 calculated fields: Max Density (from proctor, tagged "P#1"), % Compaction
6. Calc triggers on wet density or moisture change → `_calculator.calculate()`
7. Validation: proctor must be sent + wet density present
8. "SEND TO FORM" cyan button
9. On send: `appendMdot0582bTestRow()` → snackbar → reset fields → increment test_number → stay expanded
10. "Last Sent" banner shows previous test summary

**Acceptance criteria**:
- [ ] Quick Test section locked ("Requires proctor") until proctor sent
- [ ] After proctor sent, shows 16 fields + proctor reference
- [ ] Calculations run live (Moisture PCF, % Compaction)
- [ ] Max Density copied from proctor, tagged "P#1"
- [ ] SEND appends test row, shows snackbar "Test #1 sent to 0582B"
- [ ] Fields reset for next test, test_number increments
- [ ] Section stays expanded (no collapse)
- [ ] "Last Sent" banner appears with previous test data
- [ ] Status pill shows "Test #1" green, "Test #2" entering

---

### Phase 5: Weights Section

**Files created**:
- `widgets/hub_weights_content.dart`

**What to build**:
1. "For Proctor #1" subtitle
2. Dynamic reading pairs: Reading 1 + Reading 2 (2-per-row, 48dp)
3. Live delta validation chip per pair: "Δ 8g — Pass (≤ 10g)" green / "Δ 15g — Fail (> 10g)" red
4. "+ Add Reading" dashed outline button (max 5 pairs)
5. "SEND TO FORM" blue button
6. On send: `updateMdot0582bProctorWeights()` → collapse → SummaryTiles(R1, R2, Δ+Pass/Fail)
7. Section locked until proctor sent

**Acceptance criteria**:
- [ ] Weights section locked until proctor sent
- [ ] 1 reading pair shown by default, + Add Reading adds more (max 5)
- [ ] Delta calculates live: |R1 - R2| with pass/fail threshold ≤ 10g
- [ ] SEND saves weights to proctor row
- [ ] Collapsed shows SummaryTiles with readings + delta
- [ ] "Edit →" re-expands section

---

### Phase 6: Completion Banner

**Files created**:
- `widgets/completion_banner.dart`

**What to build**:
1. "Form Complete" banner with checkmark icon
2. Summary text: "1 proctor, N tests, weights verified"
3. Two buttons: "+ New Test" (secondary outlined) | "Preview PDF" (primary filled cyan)
4. + New Test: resets test fields, expands test section
5. Preview PDF: calls `FormPdfService.generatePreviewPdf()` → navigate to viewer
6. Banner appears at top (between pill bar and accordions) when `_isComplete`

**Acceptance criteria**:
- [ ] Banner hidden until all 4 sections sent
- [ ] Shows correct counts (proctor, tests, weights)
- [ ] "+ New Test" resets and opens test section
- [ ] "Preview PDF" generates and shows PDF
- [ ] All accordions collapsed with green "Sent" badges
- [ ] All status pills green

---

### Phase 7: Polish + Cleanup

**What to build**:
1. Scroll-to animation: after auto-advance, smooth scroll to newly expanded section via `Scrollable.ensureVisible()`
2. Accordion expand/collapse animation: `AnimatedCrossFade` with `AppTheme.animationNormal` (300ms)
3. Snackbar styling: accent-colored snackbar for each section's SEND
4. Save button in AppBar: saves current field state to response without SEND
5. Unsaved changes guard: `PopScope` with confirmation dialog
6. Resume state on re-open: if `_response` has partial data, populate controllers and expand correct section
7. **Delete old files**: `form_fill_screen.dart`, `proctor_entry_screen.dart`, `quick_test_entry_screen.dart`, `weights_entry_screen.dart`, `mdot_0582b_form_widget.dart`, `form_header_section.dart`, `form_table_section.dart`, `form_field_cell.dart`, `calculated_field_cell.dart`, `smart_input_bar.dart`
8. Update barrel exports (`screens.dart`, `widgets.dart`)
9. Add testing keys to `toolbox_keys.dart`
10. Run `flutter analyze` — 0 issues
11. Run `flutter test` — all green

**Acceptance criteria**:
- [ ] Smooth scroll animation on section transitions
- [ ] Accordion expand/collapse animates at 300ms
- [ ] Snackbars show on SEND with section accent color
- [ ] Save button persists draft state
- [ ] PopScope warns on unsaved changes
- [ ] Re-opening a partially filled form resumes at correct section
- [ ] All old files deleted, no dead imports
- [ ] `flutter analyze` 0 issues
- [ ] `flutter test` all passing
- [ ] All new widgets have testing keys

---

## Testing Keys (new)

```dart
// Hub screen
TestingKeys.mdotHubScreen
TestingKeys.mdotHubScrollView
TestingKeys.mdotHubSaveButton
TestingKeys.mdotHubPdfButton

// Status pill bar
TestingKeys.statusPillBar
TestingKeys.statusPill(String section) // 'header', 'proctor', 'test_1', 'weights'

// Accordion sections
TestingKeys.hubSection(String name)        // 'header', 'proctor', 'test', 'weights'
TestingKeys.hubSectionHeader(String name)  // tap target
TestingKeys.hubSectionBadge(String name)   // status badge

// Header
TestingKeys.hubHeaderField(String field)   // 'date', 'job_number', etc.
TestingKeys.hubConfirmHeaderButton

// Proctor
TestingKeys.hubProctorChartType
TestingKeys.hubProctorField(String field)  // 'moisture_pct', 'volume_mold', etc.
TestingKeys.hubProctorSendButton
TestingKeys.hubProctorSummaryTiles

// Quick Test
TestingKeys.hubTestField(String field)     // 'depth', 'counts_mc', etc.
TestingKeys.hubTestSendButton
TestingKeys.hubTestLastSentBanner
TestingKeys.hubTestSummaryTiles

// Weights
TestingKeys.hubWeightsReading(int index)   // 0-4
TestingKeys.hubWeightsAddButton
TestingKeys.hubWeightsSendButton
TestingKeys.hubWeightsDeltaChip(int index)
TestingKeys.hubWeightsSummaryTiles

// Completion
TestingKeys.hubCompletionBanner
TestingKeys.hubNewTestButton
TestingKeys.hubPreviewPdfButton
```

---

## Design Tokens Reference

| Element | Token | Value |
|---------|-------|-------|
| Quick Test accent | `AppTheme.primaryCyan` | #00E5FF |
| Proctor accent | `AppTheme.accentAmber` | #FFB300 |
| Weights accent | `AppTheme.statusInfo` | #2196F3 |
| Header accent | `AppTheme.surfaceBright` | #444C56 |
| Active border | accent.withValues(alpha: 0.3) | 1.5px |
| Accordion bg | `AppTheme.surfaceElevated` | #1C2128 |
| Accordion radius | 14.0 | `BorderRadius.circular(14)` |
| Accordion icon | 36×36, radius 10 | Letter in accent bg |
| Accordion header | minHeight 56dp | Touch-friendly |
| Calc fields | `AppTheme.statusSuccess` | green, 0.06 bg opacity |
| Auto-fill tag | `AppTheme.surfaceHighlight` bg | "auto"/"calc"/"1-pt"/"P#1" |
| Input height | 48dp | `AppTheme.touchTargetMin` |
| Button height | 48dp, radius 12 | Full width, bold |
| Field layout | 2-per-row default | 3-per-row for L/R/Grade only |
| Summary tiles | 3-col grid, radius 10 | `AppTheme.surfaceDark` bg |
| Status pills | radius 20, dot 5px | 11px text |
| Card spacing | 10px | Between accordions |
| Content padding | 12px horizontal | Inside accordion body |
| Animations | `AppTheme.animationNormal` | 300ms |

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Scroll jank with 4 accordion sections + many fields | Medium | Use `ListView.builder` for test field rows. Profile with DevTools if needed. |
| TextEditingController leak (30+ controllers) | Low | Dispose all in `dispose()`. Group in maps for easy cleanup. |
| Resume state complexity (re-opening partial form) | Medium | On load: parse `_response` data → populate controllers → derive which section to expand. Test this explicitly in Phase 7. |
| "Last Sent" banner state lost on hot reload | Low | Derive from `_response.parsedTestRows` — last row is last sent. |
| OnePointCalculator edge cases (out-of-bounds) | Low | Already handled — returns error, UI shows "--". |
| Weights delta threshold confusion (grams vs other) | Low | Hardcode ≤ 10g threshold. Display units clearly. |

---

## Agent Assignments

| Phase | Agent | Notes |
|-------|-------|-------|
| Phase 1 | `frontend-flutter-specialist-agent` | Scaffold, FormAccordion, StatusPillBar, routing |
| Phase 2 | `frontend-flutter-specialist-agent` | Header fields, auto-fill wiring |
| Phase 3 | `frontend-flutter-specialist-agent` | Proctor fields, calc wiring, SummaryTiles |
| Phase 4 | `frontend-flutter-specialist-agent` | Test fields, multi-test loop |
| Phase 5 | `frontend-flutter-specialist-agent` | Weights, delta validation |
| Phase 6 | `frontend-flutter-specialist-agent` | Completion banner, PDF wiring |
| Phase 7 | `code-review-agent` → `qa-testing-agent` | Review + cleanup + test |
