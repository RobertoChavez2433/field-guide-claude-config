# Adversarial Review: PDF Grid And OCR Hardening

Date: 2026-03-13
Reviewer: Codex
Spec: `2026-03-13-pdf-grid-ocr-hardening-codex-spec.md`

## MUST-FIX Findings

1. The spec must preserve a strict boundary between `OCR recovery` and `row inference`.
If row-anchor safeguards are allowed to create new-item semantics too early, the pipeline can hide OCR failures by inventing rows from partial structure. Implementation should require row safeguards to be conservative and traceable, with diagnostics indicating when a row was promoted despite a weak item anchor.

2. The spec must define retry acceptance per column before implementation starts.
Without explicit acceptance rules, adding retries will increase runtime and produce unstable winner selection. Column `0` in particular needs a precise acceptance rule for item-number-shaped output instead of a generic “non-blank” success check.

3. Grid cleanup diagnostics must operate at crop level, not only page level.
The current failure mode survived page-level “0 excess mask pixels” metrics. If implementation only adds more page metrics, it will miss the same class of failure again.

## SHOULD-CONSIDER Findings

1. Keep policy definitions data-driven.
If policies are scattered in conditionals, continuity will regress and future columns can be missed again. A central per-column policy map is safer.

2. Add retry win-rate telemetry per policy.
This is the easiest way to find runtime waste later without re-debugging from scratch.

3. Preserve saved debug crops as an intentional workflow.
The temporary integration harness already proved valuable. Keeping it documented and stable will make future OCR regressions much faster to isolate.

## Security And Safety Notes

- No meaningful security exposure is introduced by the spec itself.
- Diagnostic image storage should remain local/test-only and should not be enabled in production extraction paths without explicit guardrails.

## Review Outcome

Approved with the MUST-FIX constraints above folded into implementation planning.
