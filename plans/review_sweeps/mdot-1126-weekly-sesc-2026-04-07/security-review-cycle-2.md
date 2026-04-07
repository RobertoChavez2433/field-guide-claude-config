# Security Review — Cycle 2

**Plan**: `.claude/plans/2026-04-06-mdot-1126-weekly-sesc.md`
**Reviewer**: security-agent (opus)
**Date**: 2026-04-07

## VERDICT: APPROVE

All 15 cycle-1 findings resolved or acknowledged-deferred. No new security regressions introduced.

## Verification Matrix

| ID | Status | Evidence |
|---|---|---|
| SEC-1126-01 RLS rewrite | PASS | Per-operation SELECT/INSERT/UPDATE/DELETE policies, scope via `project_id IN (SELECT id FROM public.projects WHERE company_id = get_my_company_id())`, `NOT is_viewer()` on writes. Zero `is_user_in_company`/`company_users` references. |
| SEC-1126-02 Storage path/policies | PASS | Path `signatures/$companyId/$projectId/$id.png` with literal `signatures/` prefix. Policies extract `[2]` from `storage.foldername`. All four ops covered. |
| SEC-1126-03 Audit immutability + PNG hash | PASS | `signature_png_sha256` column added. Postgres + SQLite BEFORE UPDATE immutability triggers on both tables. FK is `ON DELETE RESTRICT`. |
| SEC-1126-04 No client-supplied company_id | PASS | `SignatureContext` has no `companyId` field. Use case derives from session. Server trigger sets `NEW.company_id := get_my_company_id()`. |
| SEC-1126-05 Auth assertion | PASS | `_session.currentUser` null check throws StateError. Server trigger sets `NEW.user_id := auth.uid()`. Unit test row in matrix. |
| SEC-1126-06 Universal edit-after-sign | PASS | Hook moved into `FormResponseRepositoryImpl.update()`. Compares normalized payload excluding `signature_audit_id` to avoid churn. Catches background sync + conflict resolution paths. |
| SEC-1126-07 PNG storage | DEFERRED (documented) | Acknowledged trade-off. Mitigated by SEC-1126-02/03/11 + re-audit gate next sprint. Acceptable for cycle 2. |
| SEC-1126-08 GPS consent | PASS | Default OFF, requires setting AND permission. consent_records row with `policy_type='signature_location_capture'`. NULL GPS documented valid. |
| SEC-1126-09 device_id | PASS | Per-install `Uuid().v4()` in `flutter_secure_storage`, never hardware-derived. |
| SEC-1126-10 File immutability | PASS | Covered by SEC-1126-03 trigger set. |
| SEC-1126-11 Bucket limits | PASS | `file_size_limit = 524288` (512 KB), `allowed_mime_types = ARRAY['image/png']`. |
| SEC-1126-12 Realtime PII | PASS | `signature_audit_log` NOT added to `supabase_realtime`. Only `signature_files` included for sync hints. |
| SEC-1126-13 Crypto rationale | PASS | Inline WHY comment added. |
| SEC-1126-14 ExportBlockedException | PASS | Defined in new Sub-phase 8.0. |
| SEC-1126-15 Helper name in plan body | PASS | All plan SQL uses verified helpers. |

## New Findings (Cycle 2)
None.

## Spot Checks
- Plan-wide grep `is_user_in_company|company_users`: zero hits
- Postgres + SQLite immutability column lists consistent
- Immutability triggers exclude `local_path/remote_path/updated_at/deleted_at` so legitimate sync writes remain possible
- Server `signature_files_set_owner` also forces `created_by_user_id := auth.uid()` — closes spoofing corner
- Repo-layer invalidation strips `signature_audit_id` before equality check — avoids no-op churn
- Platform CHECK tightened to `('android','ios','windows')` in both sides
- `SignatureContextProvider._resolvePlatform` throws for unsupported targets — defense in depth

## OWASP Mobile Top 10 — Delta

| # | Risk | Cycle 1 | Cycle 2 |
|---|---|---|---|
| M1 Credentials | FAIL | PASS |
| M3 Auth/Authz | FAIL | PASS |
| M4 Input validation | PARTIAL | PASS |
| M6 Privacy | FAIL | PASS |
| M8 Misconfig | FAIL | PASS |
| M9 Storage | PARTIAL | PARTIAL (SEC-1126-07 deferred) |

## Remediation Priority
1. Block merge: none
2. Next sprint re-audit: SEC-1126-07 — BLOB or platform secure storage
3. Backlog: server-side device_id length ≤ 64 validation
