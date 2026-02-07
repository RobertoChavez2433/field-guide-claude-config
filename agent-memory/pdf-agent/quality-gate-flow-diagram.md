# Per-Page Quality Gate - Flow Diagram

## Current Architecture (All-or-Nothing)

```
┌─────────────────────────────────────────────────────────────┐
│ importBidSchedule()                                         │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────┐
         │ extractRawText(document)  │  ← Concatenate ALL pages
         └───────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────┐
         │  needsOcr(rawText, count) │  ← Document-level decision
         └───────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
      FALSE │                         │ TRUE
            ▼                         ▼
    ┌───────────────┐         ┌──────────────┐
    │ Native Text   │         │ Full OCR     │
    │ ALL PAGES     │         │ ALL PAGES    │
    └───────────────┘         └──────────────┘
            │                         │
            │                         │
            └────────────┬────────────┘
                         ▼
              ┌────────────────────┐
              │  TableExtractor    │
              └────────────────────┘
```

**PROBLEM**: Page 6 has encoding corruption, but document-level check passes.
Result: Garbled data on page 6 (`$z'882'629'ze` instead of `$7,882,926.73`)

---

## Proposed Architecture (Per-Page Routing)

```
┌─────────────────────────────────────────────────────────────┐
│ importBidSchedule()                                         │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────┐
         │ extractRawText(document)  │  ← Still check document-level
         └───────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────┐
         │  needsOcr(rawText, count) │  ← If TRUE, skip to full OCR
         └───────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
      FALSE │                         │ TRUE
            ▼                         ▼
    ┌───────────────────────────┐  ┌──────────────┐
    │ NativeTextExtractor       │  │ Full OCR     │
    │ Extract ALL pages         │  │ ALL PAGES    │
    │ → List<List<OcrElement>>  │  └──────────────┘
    └───────────────────────────┘         │
                │                          │
                ▼                          │
    ┌────────────────────────────┐        │
    │ NEW: Per-Page Quality Gate │        │
    │                            │        │
    │ For each page:             │        │
    │ 1. _assessPageQuality()    │        │
    │ 2. Calculate composite     │        │
    │    score (0.0 - 1.0)       │        │
    │ 3. If score > 0.35 →       │        │
    │    Mark for OCR            │        │
    └────────────────────────────┘        │
                │                          │
                ▼                          │
    ┌────────────────────────────┐        │
    │ Any pages flagged?         │        │
    └────────────────────────────┘        │
                │                          │
       ┌────────┴────────┐                │
       │ YES             │ NO             │
       ▼                 ▼                │
┌──────────────┐  ┌──────────────┐       │
│ Mixed Mode   │  │ Native Only  │       │
│              │  │              │       │
│ Pages 1-5,   │  │ All pages    │       │
│ 7-12:        │  │ use native   │       │
│ Native text  │  │ text         │       │
│              │  │              │       │
│ Page 6:      │  │              │       │
│ OCR fallback │  │              │       │
└──────────────┘  └──────────────┘       │
       │                 │                │
       └────────┬────────┘                │
                │                         │
                └────────┬────────────────┘
                         ▼
              ┌────────────────────┐
              │  TableExtractor    │
              │                    │
              │ Input:             │
              │ - List<List<       │
              │   OcrElement>>     │
              │   (mixed sources)  │
              └────────────────────┘
```

---

## Quality Assessment Detail

```
┌──────────────────────────────────────────────────────────┐
│ _assessPageQuality(pageElements, pageIndex)             │
└──────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌───────────────┐ ┌──────────────┐ ┌─────────────┐
│ Heuristic 1:  │ │ Heuristic 2: │ │ Heuristic 3:│
│ Digit-Letter  │ │ Punctuation  │ │ Digit Swap  │
│ Substitution  │ │ Substitution │ │ (9 ↔ 6)     │
│               │ │              │ │             │
│ Example:      │ │ Example:     │ │ Example:    │
│ "$z'882"      │ │ "4'5" vs     │ │ "629" vs    │
│ has 'z' in    │ │ "4.5" or     │ │ "926"       │
│ dollar amt    │ │ "4,5"        │ │             │
│               │ │              │ │             │
│ Score: 0.6    │ │ Score: 0.7   │ │ Score: 0.5  │
└───────────────┘ └──────────────┘ └─────────────┘
        │                │                │
        │                │                ▼
        │                │        ┌──────────────┐
        │                │        │ Heuristic 4: │
        │                │        │ Header       │
        │                │        │ Garbling     │
        │                │        │              │
        │                │        │ "PRIC3" vs   │
        │                │        │ "PRICE"      │
        │                │        │              │
        │                │        │ Score: 0.3   │
        │                │        └──────────────┘
        │                │                │
        └────────────────┴────────────────┘
                         │
                         ▼
           ┌─────────────────────────────┐
           │ Composite Score Calculation │
           │                             │
           │ = (0.6 × 0.35) +  ← Digit   │
           │   (0.7 × 0.30) +  ← Punct   │
           │   (0.3 × 0.25) +  ← Header  │
           │   (0.5 × 0.10)    ← Swap    │
           │                             │
           │ = 0.21 + 0.21 + 0.075 + 0.05│
           │ = 0.545                     │
           └─────────────────────────────┘
                         │
                         ▼
              ┌────────────────────┐
              │ Is score > 0.35?   │
              └────────────────────┘
                         │
                    YES  │
                         ▼
              ┌────────────────────┐
              │ Flag page for OCR  │
              └────────────────────┘
```

---

## Mixed Mode Element Merging

```
Page 1:  [Native: Item, 123, $1000] ────┐
Page 2:  [Native: Item, 456, $2000] ────┤
Page 3:  [Native: Item, 789, $3000] ────┤
Page 4:  [Native: Item, 012, $4000] ────┤
Page 5:  [Native: Item, 345, $5000] ────┤
Page 6:  [OCR:    Item, 678, $6000]  ←──┼─── OCR'd (quality: 0.545)
Page 7:  [Native: Item, 901, $7000] ────┤
Page 8:  [Native: Item, 234, $8000] ────┤
Page 9:  [Native: Item, 567, $9000] ────┤
Page 10: [Native: Item, 890, $1000] ────┤
Page 11: [Native: Item, 123, $2000] ────┤
Page 12: [Native: Item, 456, $3000] ────┘
                                         │
                                         ▼
                         ┌───────────────────────────┐
                         │ TableExtractor.extract()  │
                         │                           │
                         │ Input:                    │
                         │ ocrElementsPerPage =      │
                         │ [                         │
                         │   [Item, 123, $1000],  ←──┼─ Page 1 (native)
                         │   [Item, 456, $2000],     │
                         │   ...                     │
                         │   [Item, 678, $6000],  ←──┼─ Page 6 (OCR)
                         │   ...                     │
                         │   [Item, 456, $3000]   ←──┼─ Page 12 (native)
                         │ ]                         │
                         └───────────────────────────┘
```

**Key Insight**: TableExtractor doesn't care about source. It just needs:
- `List<List<OcrElement>>` (per page)
- `List<Uint8List>` page images (for line detection)

Mixed mode provides both, with page 6's elements from OCR instead of native text.

---

## Quality Score Thresholds

```
 0.0 ├───────────────────────┤ 0.20 ├────────┤ 0.35 ├─────────────┤ 1.0
     │                       │      │        │      │             │
     │   CLEAN               │  BORDERLINE  │   CORRUPTED         │
     │   (Native Text)       │  (Log warn,  │   (Trigger OCR)     │
     │                       │   use native)│                     │
     │                       │              │                     │
     ▼                       ▼              ▼                     ▼
  Perfect                 Slight        Encoding              Total
  extraction              noise         corruption            garbage


Examples by Score:
┌────────────────────────────────────────────────────────────────┐
│ 0.05 - Normal bid schedule page (native text)                 │
│ 0.15 - Page with unusual item numbers (e.g., "7z-001")        │
│ 0.25 - Page with OCR-like artifacts (borderline)              │
│ 0.50 - Springfield page 6 (digit/punct substitution)          │
│ 0.80 - Page with severe encoding corruption                   │
└────────────────────────────────────────────────────────────────┘
```

---

## Performance Impact

### Current (Native Text Only)
```
extractRawText():                50ms
NativeTextExtractor:            150ms
TableExtractor:                 100ms
                        ─────────────
TOTAL:                          300ms
```

### Proposed (Mixed Mode - 1/12 pages OCR'd)
```
extractRawText():                50ms
NativeTextExtractor:            150ms
_assessPageQuality() × 12:       10ms  ← NEW
_buildMixedElementsPerPage():
  - 11 pages native:              0ms  (already extracted)
  - 1 page OCR:                2000ms  ← OCR single page
TableExtractor:                 100ms
                        ─────────────
TOTAL:                         2310ms  (+2000ms for correctness)
```

### Worst Case (All Pages OCR'd)
```
Same as full OCR path:        24000ms  (no regression)
```

**Trade-off**: Accept 2s slowdown for 1 corrupted page vs garbage data.

---

## Decision Tree

```
                    Start Import
                         │
                         ▼
              ┌──────────────────┐
              │ Document-level   │
              │ needsOcr()?      │
              └──────────────────┘
                         │
           ┌─────────────┴─────────────┐
           │ TRUE                      │ FALSE
           ▼                           ▼
    ┌─────────────┐          ┌──────────────────┐
    │ Full OCR    │          │ Extract native   │
    │ Pipeline    │          │ text ALL pages   │
    └─────────────┘          └──────────────────┘
           │                          │
           │                          ▼
           │              ┌────────────────────────┐
           │              │ Assess quality per     │
           │              │ page (NEW)             │
           │              └────────────────────────┘
           │                          │
           │              ┌────────────┴────────────┐
           │              │                         │
           │              ▼                         ▼
           │      ┌──────────────┐        ┌─────────────┐
           │      │ All pages    │        │ Some pages  │
           │      │ quality OK   │        │ quality BAD │
           │      └──────────────┘        └─────────────┘
           │              │                         │
           │              ▼                         ▼
           │      ┌──────────────┐        ┌─────────────┐
           │      │ Use native   │        │ Mixed Mode: │
           │      │ text only    │        │ Native +    │
           │      └──────────────┘        │ OCR         │
           │              │                └─────────────┘
           │              │                         │
           └──────────────┴─────────────────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ TableExtractor│
                  └───────────────┘
                          │
                          ▼
                  ┌───────────────┐
                  │ Parsed Items  │
                  └───────────────┘
```
