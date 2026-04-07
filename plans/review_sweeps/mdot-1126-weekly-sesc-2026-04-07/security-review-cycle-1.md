# Security Review — Cycle 1

> **STATUS:** Addressed in fixer cycle 1. SEC-1126-01..06, -08..-12 all
> applied. SEC-1126-07 (BLOB migration) deferred — see fixer summary in the
> plan file. SEC-1126-13 covered by inline WHY comment.



**Plan**: `.claude/plans/2026-04-06-mdot-1126-weekly-sesc.md`
**Reviewer**: security-agent (opus)
**Date**: 2026-04-07

## VERDICT: REJECT

## CRITICAL

### SEC-1126-01: RLS migration references nonexistent helper
- Plan uses `is_user_in_company(company_id)` and `company_users` — neither exists.
- Actual helper: `get_my_company_id()` returning `user_profiles.company_id` from JWT.
- Actual pattern (used by 50+ policies in `20260222100000_multi_tenant_foundation.sql`): `project_id IN (SELECT id FROM projects WHERE company_id = get_my_company_id())` + `NOT is_viewer()` on writes.
- **Fix:** Rewrite all policies. Split per operation (SELECT/INSERT/UPDATE/DELETE), derive scope from JWT not row column, add `NOT is_viewer()` on writes.

### SEC-1126-02: Storage bucket policies use wrong path index
- `_buildSignatureFilePath` returns `'<companyId>/<projectId>/<id>.png'`.
- All existing buckets prepend the bucket name as a literal prefix (`exports/<companyId>/<projectId>/...`) and extract `(storage.foldername(name))[2]`.
- Plan uses `[1]` which either locks inspectors out or silently weakens defense-in-depth.
- **Fix:** Change path to `'signatures/$companyId/$projectId/$id.png'`, policies use `(storage.foldername(name))[2] = get_my_company_id()::text`, add policies for SELECT/INSERT/UPDATE/DELETE.

### SEC-1126-03: Audit integrity — no immutability triggers, audit row missing PNG hash
- Audit row only stores `document_hash_sha256` (pre-sign PDF hash), NOT the PNG hash. PNG hash lives only on mutable `signature_files.sha256`.
- No `BEFORE UPDATE` trigger preventing changes to `sha256`, `document_hash_sha256`, `signed_at_utc`, GPS, etc. after first commit.
- **Fix:** Add `signature_png_sha256` column to `signature_audit_log`. Add Postgres + SQLite `BEFORE UPDATE` triggers blocking changes to any column except `deleted_at`, `updated_at`, `remote_path`. Change FK to `ON DELETE RESTRICT`.

## HIGH

### SEC-1126-04: Client-supplied `company_id` trusted
- `SignatureContext.companyId` is passed from caller and written directly. RLS policies check row value instead of deriving from `auth.uid()`.
- **Fix:** Remove `companyId` from `SignatureContext`; derive inside use case from session. Add Postgres `BEFORE INSERT` trigger that overrides `NEW.company_id := get_my_company_id()`.

### SEC-1126-05: No `auth.uid()` assertion in `SignFormResponseUseCase`
- `ctx.userId` taken on faith. No check against current auth session.
- **Fix:** Inject auth service; assert `ctx.userId == currentUser?.id` or derive from session. Add server `BEFORE INSERT` trigger `NEW.user_id := auth.uid()`. Add unit test.

### SEC-1126-06: Edit-after-sign invariant not watertight
- Invalidation hook wired to one provider method only. Any other repo-update path bypasses it.
- **Fix:** Move invalidation into `FormResponseRepositoryImpl.update()` or SQLite `AFTER UPDATE` trigger on `form_responses` where `form_type='mdot_1126'` and `response_data` changed.

## MEDIUM

### SEC-1126-07: Signature PNG on plain disk
- Written to app documents dir — extractable on rooted device.
- **Fix:** Prefer storing PNG bytes as BLOB on `signature_files` (removes file adapter entirely), OR use platform secure storage.

### SEC-1126-08: GPS capture has no consent gate
- **Fix:** Gate behind per-user setting (default OFF), add consent record in `consent_records`, document NULL GPS is legally valid.

### SEC-1126-09: `device_id` generation undefined
- **Fix:** Specify per-install random UUID in `flutter_secure_storage`, never hardware-derived. Server validates length ≤ 64.

### SEC-1126-10: `signature_files.sha256` not immutable post-sync
- Covered by SEC-1126-03 fix.

### SEC-1126-11: Storage bucket has no quota / MIME limit
- **Fix:** Set `file_size_limit = 524288` (512 KB) and `allowed_mime_types = ARRAY['image/png']` on bucket INSERT.

### SEC-1126-12: Realtime broadcasts PII
- `ALTER PUBLICATION supabase_realtime ADD TABLE signature_audit_log` streams `gps_lat`, `gps_lng`, `device_id`, `user_id` to all company members.
- **Fix:** Drop `signature_audit_log` from `supabase_realtime`. Pull on demand only. Keep `signature_files` in publication only if sync-hint-based; otherwise also drop.

## LOW

### SEC-1126-13: SHA-256 vs HMAC rationale undocumented
- Add `WHY:` comment explaining threat model (hash+RLS+auth.uid is the bind).

### SEC-1126-14: `ExportBlockedException` undefined
- (Also in code review.)

### SEC-1126-15: Plan body still ships unresolved helper name flag
- (Covered by SEC-1126-01 fix.)

## Remediation Priority
1. Block merge: SEC-1126-01, -02, -03, -04, -05, -06
2. This sprint: -07, -08, -10, -11, -12
3. Next sprint: -09, -14
