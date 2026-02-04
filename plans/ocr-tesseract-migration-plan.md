# OCR Migration Plan: Tesseract via flusseract (Offline, Android + iOS + Windows)

## Summary
We will replace the current OCR implementation with a single offline Tesseract engine that works on Android, iOS, and Windows using the lusseract plugin. This plan is split into PR-sized phases to minimize risk and keep each change reviewable.

## Goals
- One OCR engine across Android, iOS, and Windows.
- Offline-only OCR (no cloud dependency).
- Preserve or improve extraction quality for PDF-based inputs.
- Keep existing post-processing and table extraction logic intact.

## Non-goals
- No cloud OCR.
- No new language packs beyond English.
- No A/B testing framework.

## Known Issues to Address (Current State)
- Current OCR uses lutter_tesseract_ocr, which does not list Windows support.
- TesseractInitializer.initialize() is not called anywhere.
- 	essdata_config.json is missing (required by flutter_tesseract_ocr, but will be removed with migration).
- Pooled OCR engines are disposed incorrectly in pdf_import_service.dart and 	able_extractor.dart.

---

## Phase 1 (PR 1): Cleanup and Correctness
Objective: fix current issues and prepare for engine swap with minimal functional change.

Changes
- Fix pooled OCR engine lifecycle:
  - Remove dispose() for pooled instances in pdf_import_service.dart and 	able_extractor.dart.
  - Add clear guidance for pooled vs non-pooled usage in OcrEngineFactory docs.
- Ensure OCR initialization is invoked at app startup:
  - Add startup hook to initialize OCR engine data (temporary for current engine, replace in Phase 2).
- Add or update logging around OCR init and engine selection.

Acceptance
- App runs without OCR engine disposal errors.
- Logs show OCR initialization attempted at startup.

---

## Phase 2 (PR 2): Replace flutter_tesseract_ocr with flusseract
Objective: switch to a Windows-capable Tesseract plugin and align assets and build steps.

Changes
- Remove lutter_tesseract_ocr dependency from pubspec.yaml.
- Add lusseract dependency.
- Update Tesseract data handling for flusseract:
  - Bundle ssets/tessdata/eng.traineddata.
  - Add 	essdata_config.json if required by flusseract (verify with plugin docs).
  - Update TesseractInitializer to copy traineddata to the writable directory expected by flusseract.
- Add/adjust platform build notes (Android, iOS, Windows) for flusseract.

Acceptance
- App builds on Android, iOS, Windows with flusseract linked.
- Tesseract initialization succeeds and traineddata is accessible.

---

## Phase 3 (PR 3): Implement flusseract OCR Engine Adapter
Objective: use flusseract end-to-end in the OCR pipeline.

Changes
- Create FlusseractOcrEngine implementing OcrEngine:
  - Support HOCR or bounding box extraction (if available in flusseract).
  - If HOCR is not supported, derive elements via word-level or line-level bbox APIs.
- Wire OcrEngineFactory default to flusseract.
- Update pdf_import_service.dart and 	able_extractor.dart to use the new engine.

Acceptance
- PDF OCR pipeline runs using flusseract.
- Table extraction produces OcrElements with bounding boxes.

---

## Phase 4 (PR 4): OCR Quality Safeguards
Objective: ensure PDF OCR quality stays high after the swap.

Changes
- Keep default PDF render DPI at 300 in pdf_page_renderer.dart.
- Use existing image_preprocessor.dart enhancements on all OCR images.
- Tune Tesseract settings for PDF tables:
  - PageSegMode defaults to uto or sparseText.
  - Character whitelist for numeric-heavy columns.
- Add deterministic unit tests for OCR engine configuration mapping.

Acceptance
- OCR output is consistent with existing parsing and post-processing.
- No regressions in representative PDF imports.

---

## Phase 5 (PR 5): Remove Legacy OCR Code and Dependencies
Objective: finalize migration by removing unused code.

Changes
- Delete ML Kit and flutter_tesseract_ocr code paths (if any remain).
- Remove unused OCR helpers or adapters.
- Update documentation and developer notes.

Acceptance
- App builds and runs with only flusseract for OCR.
- No platform-specific OCR exceptions or missing plugin errors.

---

## Phase 6 (PR 6): Performance and Stability Hardening
Objective: ensure large PDFs are stable and resource usage is controlled.

Changes
- Implement concurrency gating in the OCR pipeline (use OcrConcurrencyGate).
- Add performance timing via OcrPerformanceLogger.
- Cache and reuse OCR engine instances safely (no pooled disposal bugs).

Acceptance
- Large PDF imports complete without crashes on Windows.
- Memory and time logging available for OCR pipeline.

---

## Required File Touchpoints
- pubspec.yaml
- lib/features/pdf/services/ocr/ocr_engine.dart
- lib/features/pdf/services/ocr/ocr_engine_factory.dart
- lib/features/pdf/services/ocr/tesseract_initializer.dart
- lib/features/pdf/services/ocr/tesseract_config.dart
- lib/features/pdf/services/ocr/ (new flusseract engine)
- lib/features/pdf/services/pdf_import_service.dart
- lib/features/pdf/services/table_extraction/table_extractor.dart
- lib/features/pdf/services/table_extraction/cell_extractor.dart

## Risks
- flusseract build time and dependency compilation on Windows.
- HOCR/bounding-box availability differences vs previous engine.
- Performance on large PDFs if OCR is not throttled.

## Success Criteria
- Single offline OCR engine across Android, iOS, Windows.
- No MissingPluginException on Windows.
- PDF OCR extraction remains stable and accurate for project inputs.
