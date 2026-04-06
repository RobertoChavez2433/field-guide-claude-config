### [DATA] 2026-04-06: Aggressive OCR crop DPI reduction can silently drop item numbers
**Pattern**: Lowering the default OCR crop target below the protected Android Springfield baseline improved runtime but caused the item-number path to lose fidelity, producing a `130/131` run with a bogus row even though the rest of the pipeline stayed structurally healthy.
**Prevention**: Treat the `131/131` Android Springfield run at the safer OCR target as the protected baseline, compare stage-trace artifacts before and after every OCR tuning change, and do not accept a faster OCR config unless it preserves item-number fidelity, exact checksum, and `autoAccept`.
**Ref**: @lib/features/pdf/services/extraction/shared/crop_upscaler.dart
