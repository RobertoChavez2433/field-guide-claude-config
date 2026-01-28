# Phase 7: Live Preview + Form Entry UX Cleanup
**Implementation Plan**

**Last Updated**: 2026-01-28
**Status**: READY
**Assigned Agent**: `flutter-specialist-agent`

---

## Overview

Phase 7 enhances the form filling experience by adding a live PDF preview alongside form fields, improving discoverability, and supporting non-text field types. This eliminates guesswork when filling complex forms like MDOT 0582B and 1174R.

**Key Benefits**:
- See exactly how data appears in the final PDF while filling
- Reduce errors by visualizing field placement
- Access previous test values for faster data entry
- Support checkbox/radio/dropdown PDF fields

---

## Prerequisites

- [x] Phase 6 complete (Calculation Engine + FormCalculationService)
- [x] FormPdfService exists and generates PDFs successfully
- [x] FormFieldEntry model has `pdfFieldType` enum
- [x] Current form fill screen uses single-page scroll layout

---

## Task 1: Tab-Based Layout with Preview (CRITICAL)

### Summary
Split form fill screen into tabbed layout with "Fields" and "Preview" tabs. On tablets/desktop, support split-view mode to show both simultaneously.

### Complexity: MEDIUM

### Steps

#### 1.1 Create FormFieldsTab widget (file: `lib/features/toolbox/presentation/widgets/form_fields_tab.dart`)
- Extract form fields section from `form_fill_screen.dart` lines 1006-1098
- Move all field rendering logic into new widget
- Accept parameters:
  - `List<Map<String, dynamic>> fields`
  - `Map<String, TextEditingController> fieldControllers`
  - `Map<String, AutoFillResult> autoFillResults`
  - `Set<String> userEditedFields`
  - `List<FormFieldEntry> fieldEntries`
  - `Set<String> manualOverrideFields`
  - `bool isEditable`
  - Callbacks: `onFieldChanged`, `onDateTap`, `onClearAutoFill`, `onToggleOverride`, `recalculateDependentFields`
- Render fields in scrollable column with proper padding
- Pattern: Extract existing DynamicFormField rendering loop

#### 1.2 Create FormPreviewTab widget (file: `lib/features/toolbox/presentation/widgets/form_preview_tab.dart`)
- Accept parameters:
  - `FormResponse response`
  - `InspectorForm form`
  - `String? projectNumber`
  - `VoidCallback onRefresh` (regenerate preview)
- Use `FutureBuilder` to generate preview on first load
- Display PDF using `pdf_render` or `syncfusion_pdfviewer_flutter` package
- Show loading state while generating
- Show error state if template missing or generation fails
- Add floating action button to refresh preview (recalculates with current data)
- Cache preview bytes in widget state to avoid regeneration on rebuild

#### 1.3 Update form_fill_screen to use TabBarView (file: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`)
- Add `TabController` with 2 tabs: "Fields" and "Preview"
- Replace body with `TabBarView` containing `FormFieldsTab` and `FormPreviewTab`
- Keep quick entry section + parsing preview + table rows in Fields tab
- Add tab bar to AppBar bottom
- Maintain all existing state management (no logic changes)
- Add TestingKeys for tabs: `formFieldsTab`, `formPreviewTab`

#### 1.4 Add responsive split-view for large screens (file: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`)
- Detect screen width using `MediaQuery.of(context).size.width`
- If width >= 840px (tablet landscape threshold), show split view:
  - Left: FormFieldsTab (60% width)
  - Right: FormPreviewTab (40% width)
  - Use `Row` with `Flexible` widgets
- If width < 840px, use TabBarView (existing mobile layout)
- Add preference toggle in settings for "Auto split-view" (default: true)

### Files to Modify
| File | Changes |
|------|---------|
| `lib/features/toolbox/presentation/screens/form_fill_screen.dart` | Add TabController, split layout logic |
| `lib/features/toolbox/presentation/widgets/form_fields_tab.dart` | NEW: Extract form fields rendering |
| `lib/features/toolbox/presentation/widgets/form_preview_tab.dart` | NEW: PDF preview with caching |
| `lib/features/toolbox/presentation/widgets/widgets.dart` | Add exports for new tabs |
| `pubspec.yaml` | Add `syncfusion_flutter_pdfviewer: ^28.1.38` (if not present) |

### Verification
- [ ] Tabs render correctly on mobile (can swipe between tabs)
- [ ] Split view activates on tablet/desktop
- [ ] Preview shows current form data
- [ ] Preview updates when refresh button tapped
- [ ] All existing functionality works (auto-fill, calculations, quick entry)

---

## Task 2: Preview Byte Caching + Error Handling (IMPORTANT)

### Summary
Implement smart caching for preview PDFs to avoid redundant generation. Show clear error states when template is missing or generation fails.

### Complexity: MEDIUM

### Steps

#### 2.1 Add preview cache to FormPdfService (file: `lib/features/toolbox/data/services/form_pdf_service.dart`)
- Add method: `Future<Uint8List> generatePreviewPdf(FormPdfData data, {String? cacheKey})`
- Use in-memory LRU cache: `Map<String, ({Uint8List bytes, DateTime timestamp})>`
- Cache key format: `"${form.id}_${response.id}_${_hashResponseData(data)}"`
- Hash response data using simple string hash of sorted field values
- Cache size limit: 5 previews max (FIFO eviction)
- Cache TTL: 5 minutes (regenerate if older)
- Add method: `void clearPreviewCache()` for manual invalidation

#### 2.2 Create FormStateHasher utility (file: `lib/features/toolbox/data/services/form_state_hasher.dart`)
- Method: `String hashFormState(Map<String, dynamic> fieldValues)`
- Sort keys alphabetically
- Concatenate key=value pairs
- Return simple string hash (hashCode.toString())
- Exclude metadata fields (timestamp, raw_text)
- Unit test with identical data -> same hash, different data -> different hash

#### 2.3 Update FormPreviewTab error handling (file: `lib/features/toolbox/presentation/widgets/form_preview_tab.dart`)
- Catch `TemplateLoadException` specifically
- Show error UI with:
  - Error icon (Icons.error_outline)
  - Error message from exception
  - Template path attempted
  - "Retry" button
  - "Open without preview" button (goes back to fields)
- Style error container with theme.colorScheme.error background
- Add TestingKeys: `formPreviewError`, `formPreviewRetryButton`

#### 2.4 Add cache metrics logging (file: `lib/features/toolbox/data/services/form_pdf_service.dart`)
- Log cache hits/misses in debug mode
- Format: `"[FormPDF Cache] HIT/MISS for key {key}"`
- Track cache size: `"[FormPDF Cache] Size: {count}/5"`
- Log evictions: `"[FormPDF Cache] Evicted oldest entry: {key}"`

### Files to Modify
| File | Changes |
|------|---------|
| `lib/features/toolbox/data/services/form_pdf_service.dart` | Add preview cache + generatePreviewPdf method |
| `lib/features/toolbox/data/services/form_state_hasher.dart` | NEW: Hash form state for cache keys |
| `lib/features/toolbox/presentation/widgets/form_preview_tab.dart` | Error UI + retry logic |
| `test/features/toolbox/services/form_state_hasher_test.dart` | NEW: Unit tests for hasher |

### Verification
- [ ] Preview generates only once per form state
- [ ] Changing a field value invalidates cache
- [ ] Error UI shows when template missing
- [ ] Retry button regenerates preview
- [ ] Cache evicts oldest entries when full

---

## Task 3: Form Header with Test History (IMPORTANT)

### Summary
Add collapsible header section showing recent test submissions for the current form+project. Allow quick copying of previous non-project values.

### Complexity: MEDIUM

### Steps

#### 3.1 Add test history query to FormFieldRegistryRepository (file: `lib/features/toolbox/data/repositories/form_field_registry_repository.dart`)
- Method: `Future<List<FormResponse>> getRecentResponses({required String formId, required String projectId, int limit = 5})`
- Query `form_responses` where:
  - `form_id = formId`
  - `project_id = projectId`
  - `status IN ('submitted', 'exported')`
  - Order by `updated_at DESC`
  - Limit to `limit` records
- Return list of FormResponse models

#### 3.2 Create FormTestHistoryCard widget (file: `lib/features/toolbox/presentation/widgets/form_test_history_card.dart`)
- Accept parameters:
  - `List<FormResponse> recentResponses`
  - `VoidCallback(FormResponse) onCopyValues`
- Show ExpansionTile with:
  - Title: "Recent Tests ({count})"
  - Leading: Icons.history
  - Collapsed: Show count only
  - Expanded: List of recent responses with:
    - Date/time of submission
    - Status badge (submitted/exported)
    - "Copy Values" IconButton
- Style with Card elevation
- Add TestingKeys: `formTestHistoryCard`, `formTestHistoryCopyButton`

#### 3.3 Implement "copy previous values" logic (file: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`)
- Method: `void _copyFromPrevious(FormResponse previousResponse)`
- Get previous response data: `previousResponse.parsedResponseData`
- For each field in current form:
  - Skip if current field already has user-edited value
  - Skip if field is project-specific (project_number, project_name)
  - Skip if field is auto-calculated
  - Copy value from previous response to current controller
  - Mark as auto-filled (add to `_autoFillResults` with source: `AutoFillSource.carryForward`)
- Show snackbar: "Copied {count} values from previous test"
- Set `_hasUnsavedChanges = true`

#### 3.4 Integrate test history into form fill screen (file: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`)
- Load recent responses in `_loadData()` using new repository method
- Add state variable: `List<FormResponse> _recentResponses = []`
- Add FormTestHistoryCard above form fields section (inside FormFieldsTab)
- Only show if `_recentResponses.isNotEmpty`
- Pass `_copyFromPrevious` as callback

### Files to Modify
| File | Changes |
|------|---------|
| `lib/features/toolbox/data/repositories/form_field_registry_repository.dart` | Add getRecentResponses method |
| `lib/features/toolbox/presentation/widgets/form_test_history_card.dart` | NEW: History card with copy button |
| `lib/features/toolbox/presentation/screens/form_fill_screen.dart` | Load history, implement copy logic |
| `lib/features/toolbox/presentation/widgets/widgets.dart` | Export FormTestHistoryCard |

### Verification
- [ ] Recent tests load correctly for current form+project
- [ ] Copy button fills empty fields from previous response
- [ ] Project-specific fields are NOT copied
- [ ] Calculated fields are NOT copied
- [ ] User-edited fields are NOT overwritten
- [ ] Snackbar shows count of copied fields

---

## Task 4: Non-Text Field Fill Support (IMPORTANT)

### Summary
Extend PDF filling to support checkbox, radio, and dropdown field types. Map boolean/enum values from FormFieldEntry to PDF field types.

### Complexity: MEDIUM

### Steps

#### 4.1 Extend PDF field filling logic (file: `lib/features/toolbox/data/services/form_pdf_service.dart`)
- Update `_setField` method to handle multiple field types:
  - `PdfTextBoxField` (existing - text values)
  - `PdfCheckBoxField` (new - boolean values)
  - `PdfRadioButtonListField` (new - single selection from list)
  - `PdfComboBoxField` (new - dropdown selection)
- Add type detection before filling
- Map value appropriately:
  - Checkbox: "true"/"1"/"yes" -> checked, else unchecked
  - Radio: value must match one of the button names
  - Dropdown: value must match one of the items

#### 4.2 Add checkbox/radio/dropdown rendering to DynamicFormField (file: `lib/features/toolbox/presentation/widgets/dynamic_form_field.dart`)
- Add new field type cases in `build()`:
  - `checkbox`: Render `CheckboxListTile` with controller value as boolean
  - `radio`: Render `RadioListTile` group with options from field['options']
  - `dropdown`: Render `DropdownButtonFormField` with options from field['options']
- Store checkbox/radio/dropdown values as strings in controller.text:
  - Checkbox: "true" or "false"
  - Radio: selected option value
  - Dropdown: selected item value
- Add validation for required fields

#### 4.3 Update FormFieldEntry to track field options (file: `lib/features/toolbox/data/models/form_field_entry.dart`)
- Add field: `List<String>? options` (for radio/dropdown choices)
- Add to `toMap()` and `fromMap()` with JSON encoding
- Update copyWith to include options
- Add getter: `bool hasOptions => options != null && options!.isNotEmpty`

#### 4.4 Update MDOT 1174R form definition with checkbox examples (file: `lib/features/toolbox/data/services/form_seed_service.dart`)
- Add checkbox field example: `weather_am` (clear/partly cloudy/overcast)
- Add as radio group with options: `['clear', 'partly_cloudy', 'overcast']`
- Set `pdfFieldType: PdfFieldType.radio`
- Set `valueType: FieldValueType.enumeration`
- Similar for `weather_pm`

### Files to Modify
| File | Changes |
|------|---------|
| `lib/features/toolbox/data/services/form_pdf_service.dart` | Extend _setField for checkbox/radio/dropdown |
| `lib/features/toolbox/presentation/widgets/dynamic_form_field.dart` | Add checkbox/radio/dropdown UI |
| `lib/features/toolbox/data/models/form_field_entry.dart` | Add options field |
| `lib/features/toolbox/data/services/form_seed_service.dart` | Add 1174R checkbox examples |
| `test/features/toolbox/services/form_pdf_service_test.dart` | Add tests for non-text fields |

### Verification
- [ ] Checkbox fields render and toggle correctly
- [ ] Radio groups select single option
- [ ] Dropdown menus show all options
- [ ] Non-text values fill PDF correctly
- [ ] Required validation works for all field types
- [ ] Values persist when saving form

---

## Execution Order

### Critical Path (Implement First)
1. **Task 1** - Tab-Based Layout (1.1 -> 1.2 -> 1.3 -> 1.4)
   - Unblocks preview functionality
   - Foundation for all UX improvements
   - Estimated: 6-8 hours

2. **Task 2** - Preview Caching (2.1 -> 2.2 -> 2.3 -> 2.4)
   - Depends on: Task 1.2 (FormPreviewTab)
   - Improves performance significantly
   - Estimated: 4-6 hours

### Important (Implement Second)
3. **Task 3** - Test History (3.1 -> 3.2 -> 3.3 -> 3.4)
   - Depends on: Task 1.1 (FormFieldsTab)
   - User-facing feature
   - Estimated: 4-5 hours

4. **Task 4** - Non-Text Fields (4.1 -> 4.2 -> 4.3 -> 4.4)
   - Independent of other tasks
   - Required for MDOT 1174R weather fields
   - Estimated: 5-7 hours

### Total Estimated Time: 19-26 hours

---

## Architecture Patterns

### State Management
- Continue using StatefulWidget for form fill screen
- Use FutureBuilder for async preview generation
- Cache at service level (FormPdfService), not widget level
- Pass callbacks down to child widgets (no context.read in widgets)

### Widget Composition
```
FormFillScreen (StatefulWidget)
├── AppBar with TabBar (mobile) or title only (tablet split)
├── Body (conditional)
│   ├── Mobile: TabBarView
│   │   ├── FormFieldsTab
│   │   │   ├── FormTestHistoryCard (collapsible)
│   │   │   ├── DynamicFormField (list)
│   │   │   ├── QuickEntrySection
│   │   │   ├── ParsingPreview
│   │   │   └── TableRowsSection
│   │   └── FormPreviewTab (PDF viewer + refresh)
│   └── Tablet: Row (split view)
│       ├── Flexible(flex: 6) -> FormFieldsTab
│       └── Flexible(flex: 4) -> FormPreviewTab
```

### Error Handling
- Wrap PDF generation in try-catch
- Catch `TemplateLoadException` specifically
- Show user-friendly error UI (not just snackbar)
- Provide retry and fallback actions
- Log errors for debugging but don't crash

### Testing Strategy
- Widget tests for new tabs and history card
- Unit tests for FormStateHasher
- Unit tests for non-text field PDF filling
- Integration test: fill form -> preview -> verify PDF content
- E2E test: copy previous values -> save -> verify data

---

## Dependencies

### New Packages Required
```yaml
dependencies:
  syncfusion_flutter_pdfviewer: ^28.1.38  # For PDF preview rendering
```

### Existing Dependencies (Verify Present)
- `syncfusion_flutter_pdf` - PDF generation (already present)
- `provider` - State management (already present)
- `go_router` - Navigation (already present)

---

## Breaking Changes

**None** - This phase is purely additive. All existing functionality remains unchanged.

### Migration Notes
- Existing form fill screens automatically get tabs
- Users can still fill forms without using preview
- Split view is opt-in via screen size detection

---

## Testing Checklist

### Unit Tests
- [ ] FormStateHasher produces consistent hashes
- [ ] FormStateHasher handles empty/null values
- [ ] PDF cache evicts oldest entries correctly
- [ ] PDF cache respects TTL
- [ ] Non-text field PDF filling (checkbox/radio/dropdown)
- [ ] Copy previous values skips project fields
- [ ] Copy previous values skips calculated fields

### Widget Tests
- [ ] FormFieldsTab renders all fields
- [ ] FormPreviewTab shows loading state
- [ ] FormPreviewTab shows error state
- [ ] FormTestHistoryCard expands/collapses
- [ ] Tab switching preserves state
- [ ] Split view activates at correct breakpoint

### Integration Tests
- [ ] Fill form -> preview -> verify content
- [ ] Change field -> preview updates
- [ ] Copy previous -> fields populate correctly
- [ ] Checkbox/radio/dropdown save correctly
- [ ] Preview cache reduces generation calls

### Manual Testing
- [ ] Preview matches exported PDF
- [ ] Preview scrolls to show full form
- [ ] Split view resizes correctly
- [ ] Error states show helpful messages
- [ ] Test history loads recent submissions
- [ ] Copy button fills correct fields

---

## Performance Considerations

### PDF Generation
- **Concern**: Generating preview on every field change would be slow
- **Solution**: Only regenerate on manual refresh button press
- **Alternative**: Debounce auto-regeneration with 2-second delay

### Preview Caching
- **Cache size**: 5 previews max (~500KB-2MB each = 10MB max)
- **Memory impact**: Minimal on modern devices
- **Eviction**: FIFO with TTL ensures stale data removed

### Split View Layout
- **Reflow**: Use Flexible widgets to avoid layout thrashing
- **Rebuild**: Only rebuild preview when data changes (use cache key)

---

## Known Limitations

1. **PDF Preview Library**: Syncfusion free tier has branding watermark. Consider alternatives:
   - `pdf_render` (open source, no branding)
   - `flutter_pdfview` (native rendering)
   - `pdfx` (faster rendering)

2. **Preview Latency**: First preview generation takes 1-2 seconds
   - Mitigated by: Loading indicator, cache for subsequent views

3. **Mobile Screen Space**: Tabs reduce visible content area
   - Mitigated by: Default to fields tab, preview on-demand

4. **Checkbox/Radio in PDF**: Not all PDF templates use standard field types
   - Fallback: Render as text if field type doesn't match

---

## Rollback Plan

If Phase 7 introduces issues:

1. **Revert tab layout**: Change TabBarView back to SingleChildScrollView
2. **Remove preview tab**: Keep fields-only view
3. **Disable split view**: Force mobile layout on all screen sizes
4. **Remove test history**: Hide FormTestHistoryCard
5. **Revert non-text fields**: Keep text-only field rendering

All changes are in presentation layer - no database migrations or breaking data changes.

---

## Success Metrics

- [ ] Preview shows correctly for 0582B and 1174R forms
- [ ] Preview generation latency < 2 seconds
- [ ] Cache hit rate > 60% in typical usage
- [ ] Split view activates on tablet/desktop
- [ ] Test history loads in < 500ms
- [ ] Copy previous values reduces fill time by 50%
- [ ] Checkbox/radio fields work in MDOT 1174R
- [ ] All existing tests pass
- [ ] No performance regressions

---

## Agent Assignment

**Primary**: `flutter-specialist-agent`
- Tab layout and responsive design
- Widget composition and state management
- PDF preview integration
- Performance optimization

**Secondary**: `qa-testing-agent`
- Test coverage for new widgets
- Integration tests for preview workflow
- Manual testing checklist

---

## References

- **Current Implementation**: `lib/features/toolbox/presentation/screens/form_fill_screen.dart`
- **PDF Service**: `lib/features/toolbox/data/services/form_pdf_service.dart`
- **Field Model**: `lib/features/toolbox/data/models/form_field_entry.dart`
- **Theme Standards**: `.claude/rules/coding-standards.md`
- **Testing Patterns**: `.claude/rules/defect-logging.md`

---

## Next Phase Preview

**Phase 8: PDF Field Discovery + Mapping UI**
- Import PDF templates directly
- Auto-discover field names from AcroForm
- Visual mapping UI for field definitions
- Confidence scoring for auto-mapping

Depends on Phase 7 for:
- Preview infrastructure
- Non-text field support
- Field registry patterns
