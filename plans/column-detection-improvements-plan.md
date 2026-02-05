# Springfield PDF Column Detection Improvements - Implementation Plan

**Created**: 2026-02-04
**Status**: PROPOSED
**Complexity**: MEDIUM-HIGH
**Agent**: qa-testing-agent / pdf-agent

## Executive Summary

Springfield PDFs use multi-line/fragmented headers that the current `HeaderColumnDetector` fails to process correctly. The detector receives only single-row elements, finds only 1-2 keywords instead of 6, and falls back to standard ratios at **16.7% confidence**. This plan addresses the root causes through targeted fixes.

### Problem Statement

- **Symptom**: Column detection uses "fallback" method at 16.7% confidence
- **Impact**: 87 items extracted but 46 rows failing (133 total rows)
- **Root Cause**: Multi-line headers split across Y positions 120-165px are not combined before keyword detection

---

## Session Context (2026-02-04)

### Fixes Already Applied This Session

1. **Image Preprocessing** (`image_preprocessor.dart`):
   - Changed threshold constant `c`: 10 → 5 (less aggressive)
   - Changed blockSize: 15 → 11 (better for small text)
   - Moved Gaussian blur BEFORE adaptive threshold
   - **Impact**: OCR confidence improved 68.9% → 74.8%

2. **LS/LSUM Post-Processing** (`post_process_consistency.dart`):
   - Added LSUM, LUMPSUM, L.S. support (not just LS)
   - Use existing unitPrice when bidAmount is null
   - Always set quantity=1 for lump sum items
   - **Impact**: Springfield items properly processed

3. **DebugLogger** (`debug_logger.dart`):
   - Added `_makeJsonSafe()` for enum serialization
   - Added `_writeToSinkSync()` to avoid concurrent writes
   - Fixed ColumnDetectionMethod crash

---

## Root Cause Analysis

### 1. Multi-line Header Fragmentation

**File**: `lib/features/pdf/services/table_extraction/table_locator.dart`
**Lines**: 14, 208-242

Springfield PDF header structure:
```
Y: 120-140  | "ITEM"  | "DESCRIPTION OF WORK" | "QUANTITY" | "UNIT" | "UNIT PRICE" | "AMOUNT"
Y: 145-165  | "NO."   |                       |            |        |              |
```

The `_groupElementsByRow()` method uses `kRowYThreshold = 15.0` pixels. "ITEM" at Y:130 and "NO." at Y:155 are 25px apart - they become separate rows.

### 2. Header Detection Passes Single Row to ColumnDetector

**File**: `lib/features/pdf/services/table_extraction/table_extractor.dart`
**Lines**: 332-349

```dart
List<OcrElement> _extractHeaderRowElements(...) {
  // ...
  final headerY = tableRegion.headerRowYPositions.first;  // <-- Only FIRST Y position!
  // ...
}
```

**Problem**: Only elements near the FIRST header Y are included. Elements at Y:155 ("NO.") are excluded.

### 3. HeaderColumnDetector Minimum Threshold

**File**: `lib/features/pdf/services/table_extraction/header_column_detector.dart`
**Lines**: 7, 96

```dart
static const int kMinHeaderKeywords = 3;

if (headerMatches.length >= kMinHeaderKeywords) {
  return _buildColumnsFromHeaders(...);
}
// Falls back to standard ratios with 16.7% confidence
```

With only 2 keywords found (ITEM, QUANTITY), it falls back.

### 4. Confidence Calculation

**Lines**: 196-212

```dart
// Fallback confidence: 2/6 * 0.5 = 0.167 = 16.7%
final confidence = keywordsFound / kColumnNames.length * 0.5;
```

---

## Proposed Fixes

### Fix 1: Combine Multi-Row Header Elements (HIGHEST IMPACT)

**File**: `table_extractor.dart`

**Current** (lines 332-349):
```dart
final headerY = tableRegion.headerRowYPositions.first;
```

**Proposed**:
```dart
List<OcrElement> _extractHeaderRowElements(...) {
  final headerRowElements = <OcrElement>[];
  if (tableRegion.headerRowYPositions.isEmpty) return headerRowElements;

  final headerPageElements = ocrByPage[tableRegion.startPage] ?? [];

  // Include elements near ANY header Y position (multi-row support)
  for (final element in headerPageElements) {
    for (final headerY in tableRegion.headerRowYPositions) {
      if ((element.yCenter - headerY).abs() <= kHeaderYTolerance) {
        headerRowElements.add(element);
        break; // Don't add same element multiple times
      }
    }
  }
  return headerRowElements;
}
```

### Fix 2: Increase Header Y Tolerance

**File**: `table_extractor.dart`

**Current** (line 57):
```dart
static const double kHeaderYTolerance = 15.0;
```

**Proposed**:
```dart
static const double kHeaderYTolerance = 25.0;
```

### Fix 3: Add "DESCRIPTION OF WORK" to Keywords

**File**: `header_column_detector.dart`

**Current** (lines 43-47):
```dart
static const _descKeywords = [
  'DESCRIPTION',
  'DESC',
  'ITEM DESCRIPTION',
];
```

**Proposed**:
```dart
static const _descKeywords = [
  'DESCRIPTION',
  'DESC',
  'ITEM DESCRIPTION',
  'DESCRIPTION OF WORK',  // Springfield PDF format
];
```

### Fix 4: Handle OCR Artifacts in Keywords

**File**: `header_column_detector.dart`

**Current** (lines 222-226):
```dart
bool _containsAny(String text, List<String> keywords) {
  for (final keyword in keywords) {
    if (text.contains(keyword)) return true;
  }
  return false;
}
```

**Proposed**:
```dart
bool _containsAny(String text, List<String> keywords) {
  // Normalize text: remove leading punctuation (OCR artifacts like 'QUANTITY)
  final normalizedText = text
      .replaceAll(RegExp(r"^['\"`.,;:]+"), '')
      .replaceAll(RegExp(r"['\"`.,;:]+$"), '')
      .trim();

  for (final keyword in keywords) {
    if (normalizedText.contains(keyword) || text.contains(keyword)) {
      return true;
    }
  }
  return false;
}
```

### Fix 5: Lower kMinHeaderKeywords (IF NEEDED)

**File**: `header_column_detector.dart`

Only implement if Fixes 1-4 insufficient:
```dart
static const int kMinHeaderKeywords = 2; // Was 3
```

---

## Implementation Sequence

| Phase | Fix | Complexity | Impact |
|-------|-----|------------|--------|
| 1 | Fix 1: Multi-row header elements | LOW | HIGH |
| 1 | Fix 2: Y tolerance 15→25 | LOW | MEDIUM |
| 2 | Fix 3: Add DESCRIPTION OF WORK | LOW | LOW |
| 2 | Fix 4: OCR artifact normalization | LOW | LOW |
| 3 | Fix 5: Lower threshold (if needed) | LOW | MEDIUM |

---

## Acceptance Criteria

| Criteria | Target |
|----------|--------|
| Column detection confidence | >= 83% (5/6 keywords) |
| Column detection method | `header` (NOT `fallback`) |
| Springfield items extracted | >= 120 (from 87) |
| Row failure rate | < 20% (from 34.5%) |

---

## Verification Steps

### 1. Unit Test: Multi-Row Header Extraction

```dart
test('_extractHeaderRowElements combines multi-row headers', () {
  final ocrByPage = {
    0: [
      OcrElement(text: 'ITEM', boundingBox: Rect.fromLTWH(50, 120, 40, 20)),
      OcrElement(text: 'NO.', boundingBox: Rect.fromLTWH(50, 145, 40, 20)),
      OcrElement(text: 'DESCRIPTION OF WORK', boundingBox: Rect.fromLTWH(120, 120, 260, 45)),
      // ...
    ],
  };
  final tableRegion = TableRegion(
    headerRowYPositions: [130.0, 155.0], // Two header rows
  );

  final headerElements = extractor._extractHeaderRowElements(ocrByPage, tableRegion);

  expect(headerElements.length, greaterThanOrEqualTo(6));
  expect(headerElements.any((e) => e.text == 'ITEM'), isTrue);
  expect(headerElements.any((e) => e.text == 'NO.'), isTrue);
});
```

### 2. Integration Test: Springfield Pipeline

```dart
test('Springfield PDF uses header method', () async {
  final result = await extractor.extract(...);

  expect(result.diagnostics.columnMethod, isNot(ColumnDetectionMethod.fallback));
  expect(result.diagnostics.columnConfidence, greaterThan(0.8));
  expect(result.items.length, greaterThanOrEqualTo(100));
});
```

### 3. Manual Verification

```bash
pwsh -Command "flutter run --dart-define=PDF_PARSER_DIAGNOSTICS=true"
```

Check logs for:
- `[TableExtractor] Columns detected: 6 columns, method: header, confidence: 100.0%`

---

## Defect Patterns for _defects.md

### [PDF] 2026-02-04: Multi-line Headers Need Combining
**Pattern**: Passing only single-row elements to HeaderColumnDetector for multi-line headers
**Prevention**: Iterate ALL `headerRowYPositions` in `_extractHeaderRowElements()`
**Ref**: @lib/features/pdf/services/table_extraction/table_extractor.dart:332-349

### [OCR] 2026-02-04: OCR Artifacts in Header Keywords
**Pattern**: Leading apostrophe preventing keyword match (e.g., "'QUANTITY")
**Prevention**: Normalize text by stripping punctuation before keyword matching
**Ref**: @lib/features/pdf/services/table_extraction/header_column_detector.dart:222-226

### [OCR] 2026-02-04: Aggressive Preprocessing Destroys Text
**Pattern**: Adaptive threshold c=10, blockSize=15 too aggressive for weak text
**Prevention**: Use c=5, blockSize=11; Gaussian blur BEFORE threshold, not after
**Ref**: @lib/features/pdf/services/ocr/image_preprocessor.dart:643,184

---

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `table_extractor.dart` | Multi-row header extraction | 332-349 |
| `header_column_detector.dart` | Keyword matching, threshold | 7, 43-47, 222-226 |
| `table_locator.dart` | Row grouping, multi-row detection | 14, 149-179 |
| `springfield_integration_test.dart` | Integration tests | - |
| `fixtures/springfield_*.json` | Test data | - |

---

## Related Plans

- `comprehensive-logging-plan.md` - DebugLogger implementation (COMPLETE)
- `windows-ocr-accuracy-fix.md` - OCR preprocessing (Phases 1-3 COMPLETE)
