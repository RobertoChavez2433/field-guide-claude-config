### [DATA] 2026-04-06: Aggressive OCR crop DPI reduction can silently drop item numbers
**Pattern**: Lowering the default OCR crop target below the protected Android Springfield baseline improved runtime but caused the item-number path to lose fidelity, producing a `130/131` run with a bogus row even though the rest of the pipeline stayed structurally healthy.
**Prevention**: Treat the `131/131` Android Springfield run at the safer OCR target as the protected baseline, compare stage-trace artifacts before and after every OCR tuning change, and do not accept a faster OCR config unless it preserves item-number fidelity, exact checksum, and `autoAccept`.
**Ref**: @lib/features/pdf/services/extraction/shared/crop_upscaler.dart

### [ASYNC] 2026-04-06: Process-global stdout/stderr capture breaks concurrent OCR workers
**Pattern**: Wrapping native OCR calls with process-global stdout/stderr redirection (`dup2()` capture) caused page-worker OCR to hang when multiple isolates ran Tesseract concurrently inside one process.
**Prevention**: Do not use process-global stream capture around concurrent FFI OCR calls. Keep native logging capture disabled on Android/Windows for this wrapper, and treat any future concurrent OCR work as requiring isolate-safe native behavior end-to-end.
**Ref**: @packages/flusseract/src/logfns.h
