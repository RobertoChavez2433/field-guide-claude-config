# Adversarial Review: Test Skill Redesign

**Spec**: `.claude/specs/2026-03-19-test-skill-redesign-spec.md`
**Date**: 2026-03-19
**Reviewers**: code-review-agent (sonnet), security-agent (sonnet)

## MUST-FIX (8 items — all resolved in spec update)

### Root Cause 1: Widget interaction mechanism unspecified
- **CODE #1**: HTTP driver tap/find mechanism not specified → **RESOLVED**: IntegrationTestWidgetsFlutterBinding with custom main_driver.dart entrypoint
- **CODE #2**: Isolate threading — HTTP handler vs main UI thread → **RESOLVED**: Dispatch to main isolate via scheduleTask/StreamController, await result
- **CODE #5**: /driver/screenshot requires main thread access → **RESOLVED**: IntegrationTestWidgetsFlutterBinding provides takeScreenshot()
- **CODE #3**: App readiness race condition → **RESOLVED**: Added GET /driver/ready endpoint, returns ready after first frame renders

### Root Cause 2: No authentication on driver server
- **SEC MF-1**: No auth token on driver endpoints → **RESOLVED**: Per-session random token via Random.secure(), Authorization: Bearer header required
- **SEC MF-2**: Driver port unspecified, conflicts with debug server → **RESOLVED**: Port 4948, separate from debug server 3947
- **SEC MF-3**: screenshot/tree expose PII without guard → **RESOLVED**: Token required + Origin blocking
- **SEC MF-6**: inject-photo/inject-file bypass security checks → **RESOLVED**: Path validation (sandboxed temp dir, extension allowlist, 10MB cap, no ..)

### Root Cause 3: PII leakage from test infrastructure
- **SEC MF-4**: verify-sync.ps1 output persists PII → **RESOLVED**: Agents always use -CountOnly, never full row data
- **CODE #8**: Cleanup failure mode undefined → **RESOLVED**: Cleanup failure aborts next run + alerts user. Pre-run SQLite cleanup of E2E records

### Root Cause 4: Build guard gaps
- **SEC MF-5**: build.ps1 doesn't catch direct --dart-define usage → **RESOLVED**: -DebugServer flag required, documented as only sanctioned method
- **SEC SC-6**: MOCK_AUTH + DEBUG_SERVER combination dangerous → **RESOLVED**: build.ps1 blocks this combination

## SHOULD-CONSIDER (6 items — all resolved)

| # | Item | Decision |
|---|------|----------|
| CODE #9 | Use IntegrationTestWidgetsFlutterBinding | **ACCEPTED** — custom main_driver.dart |
| CODE #13 | Group flows to reduce agent startup overhead | **ACCEPTED** — 3 tier-based agents instead of 14 |
| CODE #15 | inject-photo mechanism needs specification | **ACCEPTED** — TestPhotoService override |
| SEC SC-1 | Android network_security_config.xml | **SKIPPED** — Android 12+ default sufficient |
| SEC SC-3 | company_id scope on cleanup | **SKIPPED** — E2E prefix sufficient |
| SEC SC-4 | Script-based pruning | **ACCEPTED** — tools/prune-test-results.ps1 |

## NICE-TO-HAVE (7 items — 3 accepted, 4 skipped)

| # | Item | Decision |
|---|------|----------|
| CODE #16 | /driver/tree depth limiting | **ACCEPTED** — default depth=5, configurable |
| CODE #17 | Use since= for log queries | **ACCEPTED** — prevents cross-flow bleed |
| SEC NH-5 | Broaden .gitignore to *.secret | **ACCEPTED** |
| CODE #10 | /driver/wait frame pump semantics | **RESOLVED** in MUST-FIX (pumpAndSettle) |
| CODE #11 | /driver/scroll-to-key vs /driver/scroll | **ACCEPTED** — added scroll-to-key endpoint |
| SEC NH-3 | PII warning in run-summary.md | **SKIPPED** |
| SEC NH-4 | Don't log launch commands | **SKIPPED** |

## Additional Items Not In Original Spec

- **CODE #4**: iOS not supported (dart:io HttpServer + entitlements) → **DOCUMENTED** as out of scope
- **CODE #12**: Pre-run SQLite cleanup of E2E data → **ADDED** to cleanup section
- **CODE #14**: Registry merge mapping table → **DEFERRED** to writing-plans phase
