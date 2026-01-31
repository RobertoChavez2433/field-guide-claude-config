# Column Layout Parser Enhancements

**Last Updated**: 2026-01-31
**Version**: Phase 1a & 1b Complete

## Quick Reference

### What Changed

#### Before (Problems)
- Fixed 18.0pt gap threshold collapsed wide columns
- Header search limited to first 50 lines (missed cover sheets)
- No validation of parsed output quality
- Parsed boilerplate text as bid items

#### After (Solutions)
- ✅ Adaptive gap threshold (3% of page width, 18-50pt)
- ✅ Multi-pass clustering with fallbacks [18, 25, 35, 50]
- ✅ Multi-page header search (first 3 pages)
- ✅ Quality gate (≥70% valid items required)
- ✅ Pre-header content filtering

---

## Debug Console Tags

When running PDF parsing, watch for these tags:

### Clustering
```
[ColumnParser] Calculated adaptive gap threshold: 30.0 (page width: 1000.0)
[ColumnParser] Adaptive threshold succeeded: 4 clusters with threshold 30.0
[ColumnParser] Fallback threshold 25.0 succeeded: 3 clusters
[ColumnParser] Insufficient clusters detected: 2 (minimum: 3)
```

### Header Detection
```
[ColumnParser] Header found on page 2, line 45
[ColumnParser] Starting row parsing from line 46 (after header)
[ColumnParser] No header found - returning empty to trigger fallback
```

### Quality Gate
```
[ColumnParser] Quality gate: 18/20 items valid (90.0%)
[ColumnParser] Quality gate PASSED
[ColumnParser] Quality gate FAILED - returning empty to trigger fallback
```

---

## Configuration Constants

Located in `column_layout_parser.dart`:

```dart
/// Fallback thresholds for multi-pass clustering
static const List<double> _clusteringThresholds = [18.0, 25.0, 35.0, 50.0];

/// Minimum number of clusters required for successful detection
static const int _minClustersRequired = 3;

/// Maximum pages to search for header
const maxSearchPages = 3; // in _findHeaderLine()

/// Quality gate threshold
const qualityThreshold = 0.70; // 70% in _parseItemsWithLayout()
```

---

## Troubleshooting

### Issue: Parser Falls Back Despite Valid Layout

**Symptoms**:
```
[ColumnParser] Insufficient clusters detected: 2 (minimum: 3)
[ColumnParser] Could not detect column layout
```

**Diagnosis**:
1. Check page width: Is adaptive threshold too small?
2. Check column spacing: Are columns <18pt apart?
3. Check data: Are there actually ≥3 distinct columns?

**Solutions**:
- Verify PDF has item, description, unit, qty, price columns
- Check if columns are very narrow (may need manual threshold tuning)
- Consider if PDF needs ClumpedTextParser instead

---

### Issue: Header Not Found on Page 2

**Symptoms**:
```
[ColumnParser] Header search stopped after 3 pages
[ColumnParser] No header found - returning empty to trigger fallback
```

**Diagnosis**:
1. Header is on page >3
2. Header keywords don't match expected patterns
3. Header line has <3 keywords

**Solutions**:
- Increase `maxSearchPages` if header is farther in
- Check header keywords in `_isHeaderLine()`
- Verify header has: item + description + (qty OR price)

---

### Issue: Quality Gate Fails on Valid PDF

**Symptoms**:
```
[ColumnParser] Quality gate: 8/20 items valid (40.0%)
[ColumnParser] Quality gate FAILED
```

**Diagnosis**:
1. Items missing unit or quantity
2. Column boundaries incorrectly detected
3. Lump sum items counted as invalid

**Solutions**:
- Check column bounds in debug PDF
- Verify LS items have quantity=1 or unitPrice
- Lower quality threshold if necessary (current: 70%)

---

## Testing

### Run Specific Tests
```bash
flutter test test/features/pdf/parsers/column_layout_parser_test.dart
```

### Run All PDF Parser Tests
```bash
flutter test test/features/pdf/parsers/
```

### Create Test Fixture
See `test/fixtures/pdf/header_on_page_2.txt` for example format:
- Page 1: Cover sheet boilerplate
- Page 2: Header line + bid items

---

## Performance Notes

### Adaptive Threshold
- **Cost**: O(n) where n = number of words on page
- **When**: Once per document during header detection
- **Impact**: Negligible (<1ms)

### Multi-Pass Clustering
- **Worst Case**: 4 passes (adaptive + 3 fallbacks)
- **Best Case**: 1 pass (adaptive succeeds)
- **Impact**: Minimal (<10ms for typical PDF)

### Multi-Page Header Search
- **Best Case**: Header on page 1, line 1
- **Worst Case**: Header on page 3, last line
- **Impact**: <50ms for 3-page search

### Quality Gate
- **Cost**: O(n) where n = number of parsed items
- **When**: After all items parsed
- **Impact**: Negligible (<1ms)

---

## Future Enhancements

### Phase 2 Candidates
- Statistical column detection (frequency analysis)
- Heuristic column inference (no header)
- Multi-font boundary detection
- Vertical line detection for columns

### Phase 3 Candidates
- Per-column confidence scoring
- Adaptive quality thresholds by parser
- Machine learning threshold optimization
- Telemetry for adaptive threshold distribution

---

## Code Locations

### Main Logic
```
lib/features/pdf/services/parsers/column_layout_parser.dart
├── _calculateGapThreshold()      # Adaptive threshold calculation
├── _clusterWithMultiplePasses()  # Multi-pass clustering
├── _clusterWordsWithThreshold()  # Single-pass clustering
├── _findHeaderLine()             # Multi-page header search
├── _isHeaderLine()               # Header validation
└── _parseItemsWithLayout()       # Quality gate validation
```

### Tests
```
test/features/pdf/parsers/column_layout_parser_test.dart
├── Phase 1a Tests (5)
├── Phase 1b Tests (4)
├── Integration Tests (2)
├── Multi-Page Header Tests (1)
└── Quality Gate Tests (2)
```

### Fixtures
```
test/fixtures/pdf/
└── header_on_page_2.txt  # Multi-page header example
```

---

## Related Documentation

- **Implementation Summary**: `.claude/implementation/phase-1ab-implementation-summary.md`
- **Original Plan**: `.claude/plans/pdf-parsing-fixes-v2.md`
- **PDF Agent Guide**: `.claude/agents/pdf-agent.md`
