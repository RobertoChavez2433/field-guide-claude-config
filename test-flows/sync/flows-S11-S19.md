# Sync Flows S11-S21: Advanced — Documents, Realtime, FCM, Dirty-Scope, Channels, Support, Consent

> No compaction pause in this group — these are the final flows.
> Every flow in this file must satisfy the framework proof standard:
> UI action, SQLite row, `change_log`, Supabase, receiver SQLite, receiver UI,
> and log review.

---

## S11: Documents Sync Verification

**Tables:** documents
**Bucket:** entry-documents
**Depends:** S02 (needs existing entry)

**Protocol:**

1. Admin (4948): inject document via `inject-document-direct`:
   ```bash
   # Encode a small test PDF to base64
   BASE64_DOC=$(python3 -c "import base64; print(base64.b64encode(b'%PDF-1.4 test document content').decode())")
   curl -s -X POST http://127.0.0.1:4948/driver/inject-document-direct \
     -H "Content-Type: application/json" \
     -d "{\"base64Data\":\"${BASE64_DOC}\",\"filename\":\"vrf-test-doc-${RUN_TAG}.pdf\",\"entryId\":\"<entryId>\",\"projectId\":\"<projectId>\"}"
   # Capture documentId from response
   ```

2. Admin sync via UI:
   ```bash
   curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4948/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
   sleep 3
   ```

3. **Supabase REST verify:**
   ```bash
   curl -s "${SUPABASE_URL}/rest/v1/documents?entry_id=eq.<entryId>&deleted_at=is.null&select=id,filename,remote_path" \
     -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
     -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}"
   # Expect 1 row with remote_path non-null
   ```

4. **Storage verify:**
   ```bash
   curl -s -X POST "${SUPABASE_URL}/storage/v1/object/list/entry-documents" \
     -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
     -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
     -H "Content-Type: application/json" \
     -d "{\"prefix\":\"<companyId>/<projectId>/\",\"limit\":100}"
   # Expect at least 1 file matching the injected document
   ```

5. Inspector (4949) sync x2 via UI:
   ```bash
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_nav_button"}'
   sleep 1
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
   sleep 3
   curl -s -X POST http://127.0.0.1:4949/driver/tap -H "Content-Type: application/json" -d '{"key":"settings_sync_button"}'
   sleep 3
   ```

6. Inspector UI verify: navigate to entry → verify document attachment visible → screenshot.

7. Required verification:
   - sender SQLite: `documents/<documentId>` exists
   - sender queue: `change_log?table=documents` drains after sync
   - Supabase: exact row exists with non-null `remote_path`
   - storage: object exists in `entry-documents`
   - receiver SQLite: `documents/<documentId>` exists after pull
   - receiver UI: document attachment visible on the entry surface

8. Capture `ctx.documentIds` for use in S09 cascade verification.

**If document UI not yet wired:** Record as OBSERVATION (not FAIL), continue to S09.

---

## S12: Quick Resume Catch-Up

**Tables:** projects, daily_entries, contractors
**Depends:** S01-S02

**Purpose:** Verify the lifecycle path uses quick sync on resume so the inspector sees fresh remote changes without manually opening Settings and tapping sync.

**Protocol:**
1. Admin (4948): update a visible record on the shared assigned project, then sync via the canonical UI sequence.
2. Inspector (4949): leave the app on a project-related screen, background it briefly using the device OS, then resume it.
3. Inspector verify:
   - Do **not** tap any sync action.
   - Wait for the updated record to appear via normal UI navigation.
   - Capture a screenshot and scan sync logs for a `quick` mode run on resume.
4. Failure conditions:
   - Only a manual full sync reveals the change.
   - Logs show a broad default full sync rather than quick resume behavior.

---

## S13: Foreground Realtime Hint

**Tables:** daily_entries, contractors, entry_quantities
**Depends:** S02, S07

**Purpose:** Verify Supabase Broadcast hints mark dirty scope and trigger a foreground quick sync while the inspector app remains open.

**Protocol:**
1. Inspector (4949): keep the app in the foreground on the screen where the affected record is visible.
2. Admin (4948): mutate that same record and sync via UI.
3. Inspector verify:
   - Do **not** tap sync.
   - Wait for the UI to refresh on its own, or navigate away/back once without syncing.
   - Capture screenshot evidence.
4. Log review:
   - Expect realtime hint logs followed by quick sync logs.
   - Reject any run that only refreshes after manual sync.

---

## S14: Background FCM Hint Recovery

**Tables:** daily_entries, contractors
**Depends:** S02, S07

**Purpose:** Verify closed-app or backgrounded delivery can still recover the hinted remote changes when the inspector returns.

**Status:** MANUAL

**Manual protocol:**
1. Inspector operator backgrounds or closes the app from the OS.
2. Admin mutates assigned-project data and syncs so the server emits the FCM path.
3. Inspector reopens/resumes the app without using manual full sync.
4. Verify the updated data appears and capture screenshots plus sync logs.

**Why manual:** the current HTTP driver does not provide reliable OS-level notification/background control.

---

## S15: Global Full Sync Action + Role Visibility

**Tables:** sync UI chrome
**Depends:** S01

**Purpose:** Verify the new manual full-sync affordance is visible in main app chrome and usable by both supported field roles.

**Protocol:**
1. Admin (4948):
   - Navigate to Dashboard and Calendar.
   - Verify the app-bar sync icon is visible.
   - Tap it to open the sync dashboard.
   - Run the `sync_now_full_button` flow and confirm the dashboard remains healthy after completion.
2. Inspector (4949):
   - Repeat the same verification.
3. Reject if either role lacks the chrome entrypoint or the dashboard full-sync action.

---

## S16: Dirty-Scope Project Isolation

**Tables:** projects, daily_entries, contractors
**Depends:** S01, S10

**Purpose:** Verify multi-project users do not pay a broad sweep for unrelated projects when a targeted hint arrives.

**Protocol:**
1. Ensure inspector has at least two assigned projects visible locally.
2. Admin mutates only project A and syncs.
3. Inspector remains foregrounded and lets the automatic catch-up run.
4. Verify:
   - Project A shows the update.
   - Project B remains unchanged.
   - Sync logs indicate quick/scoped behavior rather than a broad all-project sweep.
5. Record any broad sweep as a regression against sync-strategy intent.

---

## S17: Maintenance Sync Housekeeping

**Tables:** user_profiles, sync_metadata
**Depends:** S01

**Purpose:** Verify deferred maintenance work still performs the required housekeeping: pending local push, company-member refresh, and `last_synced_at` advancement.

**Status:** MANUAL

**Manual protocol:**
1. Prepare a device with a small pending local change plus a known remote profile/member change.
2. Let the maintenance/background path run, or trigger it through the supported platform mechanism.
3. Verify:
   - Pending local change is pushed.
   - Company member/profile data refreshes locally.
   - `last_synced_at` advances.
4. Capture screenshots and sync/auth logs for evidence.

---

## S18: Private Channel Registration

**Tables:** sync_hint_subscriptions
**Depends:** S01, S13

**Purpose:** Verify each authenticated app installation receives its own opaque private channel registration and that foreground hint delivery still works through those registrations.

**Protocol:**
1. Ensure both devices are authenticated and foreground-capable.
2. Query Supabase for the current user/device subscription rows:
   - expect at least one active row per active device
   - expect distinct `channel_name` values for admin and inspector devices
   - expect `channel_name` to use the opaque `sync_hint:` shape and not include `company_id`
   - expect `refresh_after` / `expires_at` semantics to be represented by populated timing fields on the row/RPC result
3. Trigger a normal foreground hint scenario:
   - inspector remains foregrounded
   - admin mutates assigned-project data and syncs
4. Verify:
   - inspector still auto-catches-up without manual sync
   - logs show the foreground hint path still functioning after private-channel registration
5. Record FAIL if:
   - both devices share the same active channel
   - channel naming is tenant-derived/predictable
   - foreground hint delivery only works after manual sync

---

## S19: Private Channel Teardown + Rebind

**Tables:** sync_hint_subscriptions
**Depends:** S18

**Purpose:** Verify sign-out/sign-in on the same install tears down or replaces the old private-channel registration, preserves one-active-row-per-install semantics, and continues delivering hints to the current session.

**Protocol:**
1. Pick one device and capture its current active `sync_hint_subscriptions` row from Supabase.
2. On that same device:
   - sign out
   - sign back in with the intended test account
3. Query Supabase again and verify:
   - the previous row is revoked or replaced
   - only one active row remains for that `device_install_id`
   - the active row is owned by the current authenticated user/company context
4. Re-run a lightweight foreground hint check:
   - keep the device foregrounded
   - mutate assigned-project data from the peer device and sync
   - verify the re-signed-in device still auto-catches-up without manual sync
5. Record FAIL if:
   - multiple active rows remain for the same install
   - the active row still belongs to the prior session context
   - hint delivery breaks after rebind

---

## S20: Support Ticket Sync

**Tables:** support_tickets
**Depends:** authenticated session only

**Purpose:** Verify user-scoped support tickets push to Supabase, persist
locally, clear from `change_log`, and can receive remote status updates.

**Protocol:**
1. Admin (4948): navigate to Help & Support and submit a ticket through the real
   support form UI.
2. Sender SQLite verify:
   - `support_tickets/<ticketId>` exists locally
   - `change_log?table=support_tickets` contains the new insert before sync
3. Admin sync via Settings UI.
4. Supabase verify:
   - exact `support_tickets/<ticketId>` row exists
   - status is the initial expected status
5. Sender queue verify:
   - `change_log?table=support_tickets` drains after sync
6. Optional remote update:
   - update ticket status remotely through Supabase/admin workflow
7. Receiver sync and verify:
   - if the second device uses the same user context, verify the row pulls down
     and local SQLite reflects the updated status
   - if the second device is a different user, verify it does **not** pull the
     ticket and document the user-scoping behavior explicitly

**Capture:** `ctx.supportTicketIds`

---

## S21: Consent Audit Sync

**Tables:** user_consent_records
**Depends:** authenticated session only

**Purpose:** Verify consent audit records are insert-only, sync to Supabase,
clear from `change_log`, and are never treated as pull/update rows.

**Protocol:**
1. On a device with a valid authenticated session, trigger a real consent
   action through the app UI:
   - preferred: revoke then re-accept if the UI path is available
   - fallback: drive the consent screen path in a controlled test session
2. Sender SQLite verify:
   - new `user_consent_records` rows exist locally
   - `change_log?table=user_consent_records` contains inserts before sync
3. Sync via Settings UI.
4. Supabase verify:
   - exact consent rows exist for the current user
   - rows reflect insert-only semantics
5. Sender queue verify:
   - `change_log?table=user_consent_records` drains after sync
6. Receiver verify:
   - do **not** require pull, because consent records are `skipPull`
   - instead verify logs show no erroneous pull/update behavior for this table
7. Record FAIL if:
   - updates or deletes are attempted for consent rows
   - sync leaves a stuck queue entry
   - Supabase rows are missing after a successful local accept/revoke action

**Capture:** `ctx.consentRecordIds`
