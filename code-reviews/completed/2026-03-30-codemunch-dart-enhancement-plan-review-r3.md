# CodeMunch Dart Enhancement — Plan Review (Round 3)

**Date:** 2026-03-30
**Plan:** `.claude/plans/2026-03-30-codemunch-dart-enhancement.md`

## Reviewers & Verdicts

| Reviewer | R3 Verdict | Summary |
|----------|-----------|---------|
| Code Review | REJECT → Fixed | 2 CRIT, 2 HIGH, 3 MED, 2 LOW found and fixed |
| Security | APPROVE | No blocking issues. 2 non-blocking hardening notes. |
| Completeness | INCOMPLETE → Fixed | 4 blocker issues found and fixed |

## Round 3 Findings & Resolutions

| # | Finding | Severity | Fix Applied |
|---|---------|----------|-------------|
| 1 | `get_parser()` is an import, not a local function | CRITICAL | Rewrote to use `_NIELSENKO_DART_PARSER` module-level + modify `_parse_with_spec()` |
| 2 | `initialized_variable_definition` in both places | CRITICAL | Removed from `symbol_node_types`, kept in `constant_patterns` only |
| 3 | Symbol dataclass accessed as dict | HIGH | Changed all `s["kind"]` → `s.kind` etc. |
| 4 | bytes passed to parse_file(str) | HIGH | Changed `open('rb')` → `open('r')`, `read_bytes()` → `read_text()` |
| 5 | UPPER_CASE guard blocks camelCase Dart constants | HIGH | Added Step 5.1.4 to bypass guard for Dart |
| 6 | Phase 14 tool API signatures unverified | MEDIUM | Added Step 1.1.5 post-sync API verification |
| 7 | Invalid Python in Step 2.1.3 | LOW | Fixed `len()` on int → `getattr()` |

## Security (Non-Blocking Notes)
- Add line-length guard before conditional import regex (theoretical ReDoS)
- Add comment noting posixpath.normpath is defense-in-depth, source_files allowlist is primary

## Cumulative Review Stats (Rounds 1-3)

| Round | Findings | Fixed | Remaining |
|-------|----------|-------|-----------|
| R1 | 15 | 13 (via fix agent) | 2 cosmetic |
| R2 | 1 minor | 1 (git pin step) | 0 |
| R3 | 9 | 7 (via fix agent) | 2 non-blocking security notes |

## Status

Plan has been through 3 review/fix sweeps with 25 total findings addressed. Ready for implementation.
