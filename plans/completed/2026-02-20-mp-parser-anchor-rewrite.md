# Plan: M&P Parser Rewrite — Metadata-Driven Anchor Algorithm

## Context

**Problem**: The M&P parser regex `^\s*Item\s+(\d+)\.?\s+(.+?)(?::\s*|\.\s+)(.*)$` finds only 4 of 131 items in the Springfield M&P PDF. Root cause: the `^` line-start anchor fails because Syncfusion's `PdfTextExtractor` doesn't preserve line breaks at item boundaries — items appear inline mid-text.

**Solution**: Replace the broken regex with a **metadata-driven two-point anchor** algorithm. This approach is validated by:
- **Sensible.so** — commercial PDF extraction API built on anchor-based extraction as core pattern
- **Unstructured.io** — 20k+ star open-source library using section-based chunking
- **Community consensus** — anchor-based segmentation is a recognized best practice for numbered-document parsing (Dart SDK #4067 workaround using `RegExp.allMatches()`)
- **Syncfusion Issue #775** — confirms line-break unreliability is a known library issue

**Key insight (from brainstorming)**: Users already have bid items loaded before M&P import. The known item numbers serve as a metadata whitelist, creating a two-point anchor that eliminates false positives without needing header stripping, preamble removal, or postamble handling.

## Algorithm

```
Input: assembledText + existingBidItems (known item numbers)

1. FIND CANDIDATES:  RegExp(r'Item\s+(\d+)\.', caseSensitive: true).allMatches(text)
2. METADATA FILTER:  Keep only matches where captured number ∈ knownItemNumbers
3. DEDUPLICATE:      First occurrence per item number wins (sort by position)
4. SEGMENT:          body[i] = text.substring(anchor[i].end, anchor[i+1]?.start ?? text.length)
5. SAFETY NET:       If segment.trim().length < 30 → merge into previous item's body
6. TITLE/BODY SPLIT: Split segment at first ':'
7. PAGE ATTRIBUTION: Map anchor position to pageRanges for source page
```

When `knownItemNumbers` is null, all candidate anchors are accepted (general-purpose fallback for testing).

## Changes

### 1. Rewrite `_parseEntries()` — Core algorithm
**File**: `lib/features/pdf/services/mp/mp_extraction_service.dart:219-287`

Replace entire method. Returns a Dart 3 record `(List<MpEntry>, Map<String, int>)` — entries + anchor stats:

```dart
(List<MpEntry>, Map<String, int>) _parseEntries(
  String text, {
  Set<String>? knownItemNumbers,
  required List<_PageRange> pageRanges,
  required Map<int, MpExtractionStrategy> pageStrategies,
  required List<PageProfile> pageProfiles,
})
```

**Anchor stats map** (new — feeds into scorecard):
- `candidates_found`: Total `Item\s+(\d+)\.` regex matches before any filtering
- `after_filter`: Matches remaining after known-number metadata filter
- `duplicates_removed`: Anchors removed by dedup (same item number at multiple positions)
- `safety_net_merges`: Short segments (< 30 chars) merged back into previous item

Implementation steps:
- `RegExp(r'Item\s+(\d+)\.')` — no `^`, no `multiLine`, case-sensitive
- `allMatches(text)` → count as `candidates_found`
- If `knownItemNumbers != null`, filter to only known numbers → count as `after_filter`
- If `knownItemNumbers == null`, `after_filter = candidates_found`
- Deduplicate via `Map<String, RegExpMatch>` (first occurrence per normalized number wins) → count removed as `duplicates_removed`
- Sort remaining anchors by `.start` position
- Segment between consecutive anchors
- Safety net: segments with `trim().length < 30` → merge body into previous entry, increment `safety_net_merges`
- Title/body: split at first `:` in segment text
- Page attribution: reuse existing `pageRanges` logic

### 2. Update `extract()` call site
**File**: `lib/features/pdf/services/mp/mp_extraction_service.dart:110-115`

Build known item numbers set and unpack the record return:

```dart
final knownItemNumbers = existingBidItems
    .map((b) => _normalizeNumber(b.itemNumber))
    .where((n) => n.isNotEmpty)
    .toSet();

final (entries, anchorStats) = _parseEntries(
  assembledText.toString(),
  knownItemNumbers: knownItemNumbers,
  pageRanges: pageRanges,
  pageStrategies: pageStrategies,
  pageProfiles: pageProfiles,
);
```

Add `anchorStats` to the returned `MpExtractionResult.qualityMetrics` map so it's available downstream:

```dart
'anchorStats': anchorStats,
```

### 3. Update `parseEntriesForTesting()`
**File**: `lib/features/pdf/services/mp/mp_extraction_service.dart:387-404`

Add optional `knownItemNumbers` parameter. Return record to expose anchor stats:

```dart
@visibleForTesting
(List<MpEntry>, Map<String, int>) parseEntriesForTesting(
  String text, {
  Set<String>? knownItemNumbers,
  int pageIndex = 0,
  MpExtractionStrategy strategy = MpExtractionStrategy.native,
})
```

Semantics:
- `knownItemNumbers == null` → accept ALL regex matches (no metadata filter)
- `knownItemNumbers` is a `Set<String>` → filter to only those numbers

### 4. Update unit tests — parser
**File**: `test/features/pdf/services/mp/mp_item_parser_test.dart`

Existing tests call `parseEntriesForTesting(text)` — they now need to unpack the record:
```dart
// Before:
final entries = service.parseEntriesForTesting(text);
// After:
final (entries, _) = service.parseEntriesForTesting(text);
```

This is a mechanical change across all 6 existing tests. No logic changes.

Add 3 NEW tests for the metadata-driven anchor behavior:
- `filters out items not in known set` — text has Items 1-5, `knownItemNumbers: {'1', '3', '5'}` → 3 entries, `anchorStats['after_filter'] == 3`
- `safety net merges short cross-reference segments` — text has "see Item 3." inline in Item 2's body, `knownItemNumbers: {'2', '3'}` → 1 entry (Item 3 segment is < 30 chars, merged into Item 2's body), `anchorStats['safety_net_merges'] == 1`
- `accepts all items when knownItemNumbers is null` — backward compatibility, 5 items → all 5 found

### 5. Update unit tests — extraction service
**File**: `test/features/pdf/services/mp/mp_extraction_service_test.dart`

No changes needed — `extract()` API is unchanged. Tests pass bid items already and only check `MpExtractionResult` fields which remain stable.

### 6. Update fixture generator — capture anchor stats
**File**: `integration_test/generate_mp_fixtures_test.dart`

**Line 167**: Update `parseEntriesForTesting` call to unpack record and pass known item numbers:

```dart
// Before:
final entries = service.parseEntriesForTesting(assembledText.toString());
// After:
final knownItemNumbers = bidItems.map((b) => b.itemNumber).toSet();
final (entries, anchorStats) = service.parseEntriesForTesting(
  assembledText.toString(),
  knownItemNumbers: knownItemNumbers,
);
```

**Write anchor stats to `mp_parsed_entries.json`** — add to existing fixture (not a new file):

```dart
// In the 'summary' block of mp_parsed_entries.json, add:
'anchor_stats': anchorStats,
```

This keeps all parser-stage data in one fixture file. The scorecard reads it from `parsedEntriesJson['summary']['anchor_stats']`.

### 7. Update scorecard — new Anchor stage + strict assertions
**File**: `test/features/pdf/services/mp/mp_stage_trace_diagnostic_test.dart`

**Add anchor stats to the metrics section** (after line ~176, Parser section):

```dart
// Anchor (new stage — read from parsed entries summary)
final anchorStats = (parsedSummary['anchor_stats'] as Map<String, dynamic>?) ?? {};
final candidatesFound = (anchorStats['candidates_found'] as num?)?.toInt() ?? 0;
final afterFilter = (anchorStats['after_filter'] as num?)?.toInt() ?? 0;
final duplicatesRemoved = (anchorStats['duplicates_removed'] as num?)?.toInt() ?? 0;
final safetyNetMerges = (anchorStats['safety_net_merges'] as num?)?.toInt() ?? 0;
```

**Add 4 new scorecard rows** (insert between QualityGate and Parser rows):

| Stage | Metric | Expected | Logic |
|-------|--------|----------|-------|
| `Anchor` | `candidates_found` | `>=131` | Total regex hits should be >= item count (may include noise) |
| `Anchor` | `after_filter` | `131` | After metadata filter, should match expected item count exactly |
| `Anchor` | `duplicates_removed` | `0` | Each item number should appear exactly once |
| `Anchor` | `safety_net_merges` | `0` | No short segments expected in clean Springfield PDF |

**Updated scorecard layout** (18 metrics total, was 14):

```
#   Stage         Metric               Expected   Actual   %     Status
1   QualityGate   pages_analyzed       13         ...
2   QualityGate   native_pages         13         ...
3   QualityGate   ocr_pages            0          ...
4   QualityGate   avg_corruption       <15        ...
5   QualityGate   max_corruption       <15        ...
6   QualityGate   avg_single_char      <0.30      ...
7   Anchor        candidates_found     >=131      ...        NEW
8   Anchor        after_filter         131        ...        NEW
9   Anchor        duplicates_removed   0          ...        NEW
10  Anchor        safety_net_merges    0          ...        NEW
11  Parser        entries_parsed       131        ...
12  Parser        unique_items         131        ...
13  Parser        avg_body_len         >50        ...
14  Matcher       matched              131        ...
15  Matcher       unmatched            0          ...
16  Matcher       avg_confidence       >0.95      ...
17  Overall       overall_conf         >0.95      ...
18  Overall       elapsed_ms           <5000      ...
```

**Update assertions** at bottom (lines 439-453):

```dart
// Strict: parser must find all items
expect(entriesParsed, equals(131), reason: 'Parser should find all 131 items');
expect(matched, equals(131), reason: 'All 131 items should match bid items');
expect(bugCount, equals(0), reason: 'No BUG-level failures allowed');
```

## Files Summary

| File | Action | Scope |
|------|--------|-------|
| `lib/features/pdf/services/mp/mp_extraction_service.dart` | Modify | Rewrite `_parseEntries` (record return + anchor algorithm), update `extract()` call site, update `parseEntriesForTesting` |
| `test/features/pdf/services/mp/mp_item_parser_test.dart` | Modify | Unpack records in 6 existing tests + add 3 new metadata-filter tests |
| `test/features/pdf/services/mp/mp_stage_trace_diagnostic_test.dart` | Modify | Add 4 Anchor metrics, update assertions to strict 131/131 |
| `integration_test/generate_mp_fixtures_test.dart` | Modify | Pass known item numbers, unpack record, write `anchor_stats` to fixture |

## What Does NOT Change

- Quality gate logic (`_shouldUseOcr`, page profiling) — unchanged
- OCR fallback pipeline (`_ocrPage`) — unchanged
- Text assembly with `pageRanges` — unchanged
- `_buildMatches()` — matching entries to bid items — unchanged
- `_entryConfidence()` — confidence scoring — unchanged
- `MpExtractionResult` class structure — unchanged (stats go in existing `qualityMetrics` map)
- `mp_models.dart` — unchanged
- `mp_test_helpers.dart` — unchanged
- `mp_extraction_service_test.dart` — unchanged (uses `extract()` which is API-stable)
- `mp_quality_gate_test.dart` — unchanged
- `mp_item_matcher_test.dart` — unchanged

## Verification

1. **Run existing M&P tests** (expect all green — no API break):
   ```
   pwsh -Command "flutter test test/features/pdf/services/mp/"
   ```

2. **Regenerate fixtures** with the real Springfield M&P PDF:
   ```
   pwsh -Command "flutter test integration_test/generate_mp_fixtures_test.dart -d windows --dart-define='SPRINGFIELD_MP_PDF=C:\Users\rseba\OneDrive\Desktop\864130 Springfield DWSRF Water System Improvements CTC [319-331) M&P.pdf'"
   ```

3. **Run scorecard** — expect 18 metrics, all OK, 131/131 parsed and matched:
   ```
   pwsh -Command "flutter test test/features/pdf/services/mp/mp_stage_trace_diagnostic_test.dart"
   ```

4. **Run static analysis** — expect clean:
   ```
   pwsh -Command "flutter analyze lib/features/pdf/services/mp/"
   ```

5. **Present scorecard to user** in markdown table format per CLAUDE.md reporting preferences.
