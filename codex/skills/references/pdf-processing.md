# PDF Processing Reference

Use this for PDF, OCR, template, and extraction work.

## Core Rule

Verify field positions visually before filling or remapping them
programmatically.

## Primary Uses

- debug template field positions
- inspect PDFs that fail the Dart parser cascade
- pre-analyze bid schedules before import
- troubleshoot low-confidence extraction

## Reference Order

1. `.claude/rules/pdf/pdf-generation.md`
2. `.claude/skills/implement/references/pdf-generation-guide.md`
3. `.claude/rules/testing/testing.md`
4. `lib/features/pdf/services/`
5. `lib/features/forms/data/services/`

## Script Surface

Use repo-owned scripts and the existing project PDF services when the task needs
deterministic PDF analysis, field inspection, or export verification.

## Project Files

- `assets/templates/idr_template.pdf`
- `lib/features/pdf/services/pdf_service.dart`
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`

## Upstream Note

There is no current dedicated upstream Claude `pdf-processing` skill in this
repo. Use the live PDF rule and `implement` reference guide instead.
