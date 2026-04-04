# Code Review -- Cycle 1

**Verdict**: REJECT — 3 critical, 4 high, 3 medium

## Critical
C1: TesseractConfigV2 path wrong — actual: `ocr/tesseract_config_v2.dart`, not `stages/`
C2: Missing copyWith files: grid_lines.dart (11 sentinels), interpreted_value.dart (5 sentinels)
C3: `curly_braces_in_flow_control_structures` not enabled — phantom rule, remove

## High
H1: `super.dbService` pattern doesn't exist — only `super.supabaseClient` (17 violations)
H2: database_service.dart already uses `!` before `as` — SafeRow count may be inflated
H3: SafeAction/safeCall phases missing (FIXED by plan-fixer in later edit)
H4: Test catch exclusion divergence undocumented (FIXED by plan-fixer)

## Medium
M1: Missing guidance for `avoid_catching_errors` fix pattern (`.catchError` → try/await/on Exception)
M2: SafeRow needs `requireBool` (SQLite stores bool as int)
M3: Phase summary arithmetic overlap unexplained
