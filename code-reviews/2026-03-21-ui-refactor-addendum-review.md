# Code Review + Security Review — UI Refactor Addendum (2026-03-21)

## Code Review Verdict: REJECT → FIXED

### Findings and Resolutions

| # | Severity | Finding | Resolution |
|---|----------|---------|------------|
| 1 | CRITICAL | Step 7.B.2 number collision with original plan | **FIXED**: Renumbered to Step 7.B.3 |
| 2 | CRITICAL | `AppChip.purple()` mapping unresolved ("consider" language) | **FIXED**: Firm decision — accept `AppChip.purple()` with `AppTheme.sectionPhotos` accent; documented that semantic mismatch is accepted |
| 3 | HIGH | ProjectDeleteSheet needs AppBottomSheet.show() clarification | **FIXED**: Added "Sheet Structure" note requiring `AppBottomSheet.show()` wrapping |
| 4 | HIGH | Step 10.A.3 needs acceptance condition | **FIXED**: Added explicit acceptance condition checklist |
| 5 | MEDIUM | `AppChip.cyan()` for engineer role is imprecise | Accepted — documented explicitly in mapping table |
| 6 | MEDIUM | ProjectImportBanner key coverage thin (1 key) | Accepted — dismiss is the primary interactive element; retry is not a distinct button |
| 7 | MEDIUM | `EdgeInsets.symmetric(vertical: 2)` was a no-op | **FIXED**: Changed to "Keep as-is — below token floor" |
| 8 | MINOR | Scope table placeholder not filled | **FIXED**: Changed to "80+" |
| 9 | MINOR | `Icon(size: 64)` unresolved | **FIXED**: Changed to "Keep as-is" with rationale |
| 10 | MINOR | `PdfKeys` missing doc comment + naming convention | **FIXED**: Renamed to `PdfTestingKeys` with doc comment |

## Security Review Verdict: APPROVE

### Findings

| # | Severity | Finding | Notes |
|---|----------|---------|-------|
| 1 | LOW | Warning text color for ProjectDeleteSheet should prefer `fg.statusWarning` over `cs.onSurface` | **FIXED**: Plan now mandates `fg.statusWarning` with note "must remain visually urgent" |

All 7 security questions passed:
- Testing keys: no sensitive data embedded
- ProjectDeleteSheet: permission gates preserved (cosmetic-only changes)
- RemovalDialog: offline guard preserved (cosmetic-only changes)
- ExtractionBanner: state management preserved (only foreground colors changed)
- RLS: no implications (presentation-only)
- Color changes: no security-critical elements hidden
- Destructive actions: all confirmation flows intact
