---
paths:
  - "lib/features/pdf/**/*.dart"
  - "assets/templates/**/*.pdf"
---

# PDF Generation And Extraction

- Keep the extraction path OCR-only. Do not reintroduce native or hybrid text extraction.
- Preserve the `flusseract`-driven platform assumptions behind the PDF stack.
- Do not bring binarization back into the clean-PDF preprocessing path.
- Keep template ownership and field mapping logic in the existing PDF services instead of scattering it across screens.
- After changing extraction-stage behavior, run the relevant pipeline report and extraction tests.
- For extraction heuristic or algorithmic rule changes, also load
  `.claude/rules/pdf/pdf-extraction-testing.md`.
- Reuse the production quality thresholds and retry strategy instead of inventing local overrides.
- Keep math/backfill heuristics conservative and tied to the existing production rules.
