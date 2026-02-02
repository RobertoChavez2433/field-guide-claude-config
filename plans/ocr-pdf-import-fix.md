# Fix PDF Bid Schedule Import for Scanned/OCR PDFs

## Problem Summary

Scanned bid schedule PDFs fail to parse because:
1. **OCR character substitution**: `$` → `s`, `1` → `r`/`l`/`t`
2. **Column concatenation**: Entire rows extracted as single "word" (1 cluster, needs 3+)
3. **Strict pattern matching**: TokenClassifier rejects `$2.80s`, `$ r 8.70`

**Sample problematic text:**
```
"6Erosion Control, Silt FenceFT640$2.80s 1,792.007Maintenance GravelTON950$ r 8.70$17.765.00"
```

---

## Solution: OCR Preprocessor Layer

Add OCR error correction **before** existing normalization, maintaining backwards compatibility.

```
PDF → Raw Text → [NEW: OCR Preprocessor] → TextNormalizer → TokenClassifier → RowStateMachine → Items
```

---

## Implementation Plan

### Phase 1: Create OcrPreprocessor (NEW FILE)
**File**: `lib/features/pdf/services/parsers/ocr_preprocessor.dart`

- Detect OCR indicators (≥2 patterns required to activate)
- Fix `s` → `$` in currency contexts
- Fix trailing `s` after currency (`$2.80s` → `$2.80`)
- Fix spaced letters in currency (`$ r 8.70` → `$8.70`)
- Fix period-as-comma (`17.765.00` → `17,765.00`)
- Fix header errors (`ADDENDUM i IItemNo.` → `ADDENDUM 1 ItemNo.`)

### Phase 2: Integrate into TextNormalizer
**File**: `lib/features/pdf/services/parsers/text_normalizer.dart`

- Call `OcrPreprocessor.process()` as first step in `normalize()`
- Only applies when `hasOcrIndicators()` returns true (clean PDFs unchanged)

### Phase 3: Lenient TokenClassifier Patterns
**File**: `lib/features/pdf/services/parsers/token_classifier.dart`

- Add `_lenientCurrencyPattern` allowing trailing letters
- Update `parseCurrency()` to strip OCR artifacts before parsing
- Add `isPunctuation()` helper for comma handling

### Phase 4: Robust RowStateMachine
**File**: `lib/features/pdf/services/parsers/row_state_machine.dart`

- Skip isolated punctuation tokens in description
- Handle `TokenType.unknown` gracefully

### Phase 5: Test Coverage
**New file**: `test/features/pdf/parsers/ocr_preprocessor_test.dart`

Test cases:
- `s2.80` → `$2.80`
- `$2.80s` → `$2.80`
- `$ r 8.70` → `$8.70`
- `17.765.00` → `17,765.00`
- Clean text unchanged
- Real OCR sample extraction

### Phase 6: Barrel Export
**File**: `lib/features/pdf/services/parsers/parsers.dart`

- Add `export 'ocr_preprocessor.dart';`

---

## Files to Modify

| File | Action | Priority |
|------|--------|----------|
| `lib/features/pdf/services/parsers/ocr_preprocessor.dart` | CREATE | High |
| `lib/features/pdf/services/parsers/text_normalizer.dart` | MODIFY | High |
| `lib/features/pdf/services/parsers/token_classifier.dart` | MODIFY | High |
| `lib/features/pdf/services/parsers/row_state_machine.dart` | MODIFY | Medium |
| `lib/features/pdf/services/parsers/parsers.dart` | MODIFY | Low |
| `test/features/pdf/parsers/ocr_preprocessor_test.dart` | CREATE | High |

---

## Key OCR Correction Patterns

```dart
// Currency: s → $
r'\bs\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\b' → '$\1'

// Trailing s removal
r'(\$\d{1,3}(?:,\d{3})*(?:\.\d+)?)s\b' → '\1'

// Spaced letter fix
r'\$\s*[rltio]\s*(\d)' → '$\1'

// Period-as-comma
r'(\d{1,3})\.(\d{3})\.(\d{2})\b' → '\1,\2.\3'
```

---

## OcrPreprocessor Implementation

```dart
/// OCR error correction for scanned PDF text.
class OcrPreprocessor {
  /// Detect if text has OCR characteristics.
  static bool hasOcrIndicators(String text) {
    int indicatorCount = 0;

    // 's' adjacent to digits (likely $ -> s)
    if (RegExp(r's\s*\d|\d\s*s').hasMatch(text)) indicatorCount++;

    // Isolated single letters between digits
    if (RegExp(r'\d\s+[rlt]\s+\d').hasMatch(text)) indicatorCount++;

    // Multiple periods where commas expected
    if (RegExp(r'\d\.\d{3}\.\d').hasMatch(text)) indicatorCount++;

    return indicatorCount >= 2;
  }

  /// Apply OCR corrections to text.
  static String process(String text) {
    if (text.isEmpty || !hasOcrIndicators(text)) return text;

    var result = text;
    result = _fixCurrencyErrors(result);
    result = _fixDigitErrors(result);
    result = _fixHeaderErrors(result);
    return result;
  }

  static String _fixCurrencyErrors(String text) {
    var result = text;

    // Fix 's' → '$' at start of currency
    result = result.replaceAllMapped(
      RegExp(r'\bs\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\b'),
      (m) => '\$${m.group(1)}',
    );

    // Fix trailing 's' after currency
    result = result.replaceAllMapped(
      RegExp(r'(\$\d{1,3}(?:,\d{3})*(?:\.\d+)?)s\b'),
      (m) => m.group(1)!,
    );

    // Fix spaced currency with OCR letter
    result = result.replaceAllMapped(
      RegExp(r'\$\s*[rltio]\s*(\d)'),
      (m) => '\$${m.group(1)}',
    );

    return result;
  }

  static String _fixDigitErrors(String text) {
    var result = text;

    // Fix period-as-comma (17.765.00 -> 17,765.00)
    result = result.replaceAllMapped(
      RegExp(r'(\d{1,3})\.(\d{3})\.(\d{2})\b'),
      (m) => '${m.group(1)},${m.group(2)}.${m.group(3)}',
    );

    return result;
  }

  static String _fixHeaderErrors(String text) {
    var result = text;
    result = result.replaceAll(RegExp(r'\bIItem\b'), 'Item');
    return result;
  }
}
```

---

## Verification

1. **Unit tests**: `pwsh -Command "flutter test test/features/pdf/parsers/"`
2. **Integration**: Test with actual problematic scanned PDF
3. **Regression**: Verify clean PDFs still parse correctly
4. **Quality gate**: Ensure `ParserQualityThresholds` still passes

---

## Risk Mitigation

- OCR corrections only activate when ≥2 indicators detected
- Clean PDFs pass through unchanged
- Existing quality gates reject poor results
- Logs when OCR corrections applied
