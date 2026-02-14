# Plan: Enhanced CMap Corruption Detection in DocumentAnalyzer (Stage 0)

## Context

The Springfield PDF has a broken ToUnicode CMap that produces wrong-but-valid ASCII characters (`I`->`l`, `$`->`s`, `SECTION`->`sEcTroN`). The current `_calculateCorruptionScore()` only detects replacement chars, control chars, non-ASCII ratios, and quote-based currency patterns — all checks that produce zero or minimal signal for CMap corruption. Springfield scores 10/100 against a threshold of 15, so all 6 pages route to native extraction (OCR is skipped entirely). Page 6 in particular has extremely corrupted/reversed text that must go through OCR.

**Goal**: Add two new corruption checks that detect CMap-level corruption, pushing Springfield's scores above 15 and routing all affected pages to OCR.

## Files to Modify

| File | Change |
|------|--------|
| `lib/features/pdf/services/extraction/stages/document_analyzer.dart` | Add 2 new checks to `_calculateCorruptionScore()` |
| `test/features/pdf/extraction/stages/stage_0_document_analyzer_test.dart` | Add ~7 new test cases |
| `test/features/pdf/extraction/fixtures/springfield_document_profile.json` | Update scores/strategies after running diagnostics |

## Implementation

### Step 1: Add Mixed-Case Pattern Detection to `_calculateCorruptionScore()`

Insert after the existing `hasQuotesInCurrency` check (line ~160), before `return score.clamp(0, 100)`:

- Split text into words of length >= 3
- For each word, count `lowercase→UPPERCASE` transitions using regex `[a-z][A-Z]`
- 2+ transitions in one word = definite corruption (e.g., `sEcTroN` has 2)
- 1 transition + word starts lowercase + word length <= 6 = likely corruption (e.g., `lTEM`)
- If ratio of corrupted words to total words > 5%, add 15-30 points (scaled)

**Why this works**: CMap corruption shifts character codes, producing impossible casing like `sEcTroN`, `lTEM`, `bID`. Construction documents use ALL CAPS or Title Case — never random mixed-case.

**False positive protection**:
- CamelCase words (>6 chars like `backgroundColor`) excluded by length filter
- Single abbreviated terms (`pH`, `mV`) won't reach 5% ratio threshold
- Proper nouns (`McDonald`) have length > 6, excluded

### Step 2: Add Currency Symbol Validation to `_calculateCorruptionScore()`

Insert immediately after the mixed-case check:

- Count digit-containing tokens (regex: `\b\d[\d,]*\.?\d*\b`)
- Count `$` signs
- If `digitTokens >= 3 && dollarSigns == 0`: **+15 points** (document has amounts but no dollar signs)
- Count `s` immediately before digit patterns (regex: `(?<![a-zA-Z])s\d[\d,]*\.?\d*`): if >= 2 matches, **+10 points** (the `$→s` corruption fingerprint)
- Count `t` or `r` before currency-like patterns (regex: `(?<![a-zA-Z])[tr]\d[\d,]*\.\d{2}\b`): if >= 1 match, **+5 points** (the `$1→t` and `1→r` corruption)

**Why this works**: Construction bid docs ALWAYS have `$` signs before amounts. Total absence of `$` with multiple numeric values is a strong corruption signal. The `s`-before-digits pattern is the specific CMap fingerprint.

### Step 3: Run Existing Tests (verify no regressions)

```
pwsh -Command "flutter test test/features/pdf/extraction/stages/stage_0_document_analyzer_test.dart"
```

Existing tests should still pass because:
- Clean text has no mixed-case corruption and proper `$` signs
- Existing corrupted text test uses `$1'234'56z` which HAS a `$`, so the missing-dollar check doesn't fire
- Threshold boundary tests use replacement/control chars, unaffected by new checks

### Step 4: Add New Test Cases

Add a new group `'DocumentAnalyzer - CMap Corruption Detection'` with these tests:

1. **Mixed-case corruption** (`sEcTroN`, `lTEM`) → score > 15, strategy = 'ocr'
2. **Dollar sign substitution** (`s25,000.00`) → score > 15, strategy = 'ocr'
3. **Missing dollar signs** (numbers but no `$`) → score >= 15
4. **Clean text with dollar signs** → no false positive, score < 15, strategy = 'native'
5. **CamelCase words** (>6 chars) → no false positive, score < 15
6. **Springfield-like combined corruption** (both patterns) → score > 25, strategy = 'ocr'
7. **Page 6 extreme corruption** (many mixed-case words) → score > 30, strategy = 'ocr'

### Step 5: Run Diagnostic to Get Actual Springfield Scores

```
pwsh -Command "flutter test test/features/pdf/extraction/golden/stage_trace_diagnostic_test.dart"
```

This produces the actual corruption scores for each Springfield page with the new checks.

### Step 6: Update Springfield Document Profile Fixture

Update `test/features/pdf/extraction/fixtures/springfield_document_profile.json` with actual scores from the diagnostic. Expected changes:
- All corrupted pages: `corruption_score` increases above 15
- `recommended_strategy` changes from `"native"` to `"ocr"` on affected pages
- `overall_strategy` changes from `"native_only"` to `"ocr_only"` or `"hybrid"`

### Step 7: Run Full Golden Test Suite

```
pwsh -Command "flutter test test/features/pdf/extraction/golden/"
```

Note: Downstream fixtures (processed_items, etc.) may need updating in a follow-up since routing to OCR changes the entire pipeline output. This PR focuses on the detection/routing decision.

## Expected Springfield Scoring (Post-Change)

| Page | Current Score | New Score (est.) | Strategy |
|------|:---:|:---:|--------|
| 0 (cover) | 0 | 0-10 | native or hybrid |
| 1 (bid items) | 10 | 25-40 | **ocr** |
| 2 (cover/non-table) | 0 | 0-10 | native or hybrid |
| 3 (bid items) | 10 | 25-40 | **ocr** |
| 4 (bid items) | 10 | 25-40 | **ocr** |
| 5 (bid items / page 6) | 10 | 35-50+ | **ocr** |

## Verification

1. All existing Stage 0 tests pass (no regressions)
2. New CMap corruption tests pass
3. Springfield diagnostic shows corrupted pages scoring > 15
4. Springfield document profile reflects OCR routing for corrupted pages
5. `flutter analyze` passes with no new warnings

## Research Summary

- ftfy, chardet, mojibake repair, encoding parameters (utf-8/latin-1/CP1252) CANNOT fix CMap corruption — it's a PDF-internal glyph-to-Unicode mapping issue, not a byte-encoding issue
- OCR is the general-purpose solution that bypasses the broken text layer entirely
- The existing PostProcessUtils heuristics are good for minor artifacts but don't scale to new PDFs with different corruption patterns
- The pipeline already has OCR capability (Flusseract/Tesseract) — the fix is better detection to trigger it
