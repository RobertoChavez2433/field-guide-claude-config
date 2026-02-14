# PDF Extraction V2 Constraints

**Feature**: PDF Extraction & Generation (V2 Pipeline)
**Scope**: Applies to all code in `lib/features/pdf/services/extraction/` (V2 only)

---

## Hard Rules (Violations = Reject)

### No V1 Imports
- ✗ No imports from `deprecated/` folder in active extraction code
- ✗ No imports of `DocumentAnalyzer`, `NativeExtractor`, `StructurePreserver`
- ✗ No reuse of V1 stage logic (copy-pasting patterns from deprecated/ is forbidden)
- ✓ All V2 code must be novel implementations, not V1 refactored

**Why**: V1 hybrid routing was unreliable. V2 is OCR-only, fundamentally different.

### OCR-Only Routing (No Hybrid)
- ✗ No hybrid native/OCR strategies
- ✗ No fallback to native text extraction when OCR fails
- ✗ No ToUnicode CMap repair attempts (route to OCR instead)
- ✓ Binary decision: Always OCR (document_quality_profiler.dart outputs `strategy: 'ocr'`)

**Why**: CMap corruption detection showed native extraction is unreliable on damaged PDFs.

### No Legacy Compatibility Flags
- ✗ No `forceFullOcr` or similar toggles to switch between V1/V2 behavior
- ✗ No version checks in code
- ✗ No conditional imports based on PDF type
- ✓ Single unified OCR-first pipeline for all PDFs

**Why**: Feature flags create maintenance burden and testing complexity.

### Re-extraction Loop Differentiation
- ✓ Each re-extraction attempt must have distinct DPI and/or PSM configuration
- ✓ Attempt 0: DPI 300, PSM 6 (single block)
- ✓ Attempt 1: DPI 400, PSM 3 (auto-segmentation)
- ✓ Attempt 2: DPI 400, PSM 6 (enhanced preprocessing)
- ✗ No duplicate configurations across attempts

**Why**: Loop must actually try different strategies, not retry identical settings.

---

## Soft Guidelines (Violations = Discuss)

### Performance Targets
- Target: Single-page PDF OCR < 15 seconds
- Target: Multi-page (10+) avg < 3 sec/page
- If exceeded: Document rationale + measure baseline before optimizing

### Test Coverage
- Target: >= 90% for extraction stages
- If lower: Discuss test gaps before shipping

### Benchmark Baseline
- All variants (DPI/PSM configs) benchmarked against Springfield PDF ground truth
- Results tracked in golden fixture framework

---

## Reference
- **PRD**: `prds/pdf-extraction-v2-prd-2.0.md`
- **Architecture**: `docs/features/feature-pdf-architecture.md`
- **Shared Rules**: `architecture-decisions/data-validation-rules.md`
