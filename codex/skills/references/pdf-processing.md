# PDF Processing Reference

Use this when operating as `pdf-agent`.

## Core Rule

Verify field positions visually before filling or remapping them
programmatically.

## Primary Uses

- debug template field positions
- inspect PDFs that fail the Dart parser cascade
- pre-analyze bid schedules before import
- troubleshoot low-confidence extraction

## Reference Order

1. `.claude/skills/pdf-processing/SKILL.md`
2. `.claude/skills/pdf-processing/references/forms-workflow.md`
3. `.claude/skills/pdf-processing/references/extraction-enhancement.md`
4. `.claude/skills/pdf-processing/references/idr-template-mapping.md`
5. `.claude/skills/pdf-processing/references/cli-commands.md`

## Script Surface

Use the existing Python scripts in `.claude/skills/pdf-processing/scripts/`
when the task needs deterministic PDF analysis or field inspection.

## Project Files

- `assets/templates/idr_template.pdf`
- `lib/features/pdf/services/pdf_service.dart`
- `lib/features/pdf/services/pdf_import_service.dart`
- `lib/features/pdf/services/extraction/pipeline/extraction_pipeline.dart`
