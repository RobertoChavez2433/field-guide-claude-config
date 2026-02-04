# Tesseract OCR Migration Plan (Offline, Android+iOS+Windows)

## Context
We will replace ML Kit OCR with Tesseract for all platforms, with offline-only operation and PDF-focused OCR. We will keep the existing post-processing and table extraction pipeline, and rewire OCR outputs to the existing OcrElement abstraction.

## Goals
- Use a single OCR engine across Android, iOS, and Windows.
- Preserve or improve extraction accuracy for PDF-based inputs.
- Keep OCR offline and self-contained.
- Maintain existing post-processing and parsing logic.

## Non-goals
- No cloud OCR.
- No new language packs beyond English.
- No A/B testing framework.

## Constraints and Notes
- Current OCR pipeline is ML Kit based and used primarily in pdf_import_service.dart, 	able_extractor.dart, and cell_extractor.dart.
- OcrElement is the existing internal abstraction but several ML Kit types still leak into the pipeline.
- Tesseract quality is sensitive to input quality; plan includes enforcing 300 DPI rendering and preprocessing.

---

## Phase 1 (PR 1): OCR Abstraction and Injection
Objective: decouple the pipeline from ML Kit so Tesseract can be dropped in cleanly.

Changes
- Add OcrEngine interface and OcrEngineFactory to lib/features/pdf/services/ocr/.
- Refactor pdf_import_service.dart to accept OcrEngine and remove direct ML Kit types.
- Refactor 	able_extractor.dart and cell_extractor.dart to accept OcrEngine instead of MlKitOcrService.
- Keep ML Kit implementation as MlKitOcrEngine for temporary parity while wiring changes.

Acceptance
- Build passes with ML Kit still enabled.
- PDF import and table extraction still function with current output behavior.

---

## Phase 2 (PR 2): Add Tesseract Engine and Assets
Objective: introduce Tesseract dependency and assets without switching default behavior yet.

Changes
- Add lusseract dependency.
- Add Tesseract trained data to assets (start with 	essdata_best/eng.traineddata for accuracy).
- Add initialization: call TessData.init() at app startup or within OCR engine initialization.
- Add config for Tesseract data path and sandbox storage.

Acceptance
- App builds on Android, iOS, Windows with Tesseract linked.
- TessData.init() succeeds and traineddata is available.

---

## Phase 3 (PR 3): Implement Tesseract OCR Adapter
Objective: implement Tesseract OCR output mapped to OcrElement for the pipeline.

Changes
- Add TesseractOcrEngine implementing OcrEngine.
- For each page image, create PixImage from bytes and run OCR via Tesseract.
- Use hocrText and getBoundingBoxes(PageIteratorLevel.word/line) to construct OcrElement with text + bounding boxes.
- Map OCR output to existing OcrElement and reuse existing post-processing in ocr_preprocessor.dart.
- Add error handling and cleanup (dispose) to prevent leaks.

Acceptance
- OCR runs end-to-end in the pipeline with Tesseract enabled via a config flag.
- Output is structurally compatible with existing post-processing and table extraction.

---

## Phase 4 (PR 4): Input Quality and PDF Rendering Improvements
Objective: ensure OCR quality matches or exceeds current output.

Changes
- Increase PDF render DPI to 300+ (or add dynamic DPI scaling) in pdf_page_renderer.dart.
- Ensure preprocessing includes grayscale/binarization and optional deskew in image_preprocessor.dart.
- Add PageSegMode tuning for PDF forms (likely uto or single_block depending on page type).
- Add optional character whitelist/blacklist for numeric-heavy tables.

Acceptance
- PDF import completes within acceptable runtime for typical project sizes.
- OCR output for a representative set of PDFs matches or improves current extraction quality.

---

## Phase 5 (PR 5): Remove ML Kit and Make Tesseract Default
Objective: fully replace ML Kit and stabilize Tesseract as the single engine.

Changes
- Remove google_mlkit_text_recognition dependency.
- Remove Android ML Kit ABI config and any ML Kit specific glue.
- Make TesseractOcrEngine the default engine in the factory.
- Update any documentation and developer notes.

Acceptance
- App builds and runs on all platforms using only Tesseract.
- PDF OCR completes without MissingPluginException or platform-specific crashes.

---

## Phase 6 (PR 6): Performance and Stability Hardening
Objective: reduce latency and resource usage for large PDF imports.

Changes
- Reuse a cached Tesseract instance per isolate to avoid repeated initialization.
- Gate concurrency to prevent memory spikes on large PDFs.
- Add timing and memory logs around OCR steps.

Acceptance
- Large PDF imports are stable and do not crash on Windows.
- Memory usage remains within expected bounds during OCR.

---

## Success Criteria
- Tesseract used across Android, iOS, Windows.
- Offline OCR only, no cloud dependency.
- No loss in extracted table accuracy on real project PDFs.
- Stable behavior on Windows without OCR plugin errors.
