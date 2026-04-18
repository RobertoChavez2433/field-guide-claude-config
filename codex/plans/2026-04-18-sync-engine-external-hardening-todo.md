# Sync Engine External Hardening Todo

Date: 2026-04-18
Status: active review addendum
Sources:

- Local sync engine review under `lib/features/sync/`
- Current sync-soak plans and `.codex/research/2026-04-17-sync-soak-gap-research.md`
- External survey: PowerSync, ElectricSQL, WatermelonDB, RxDB, CouchDB/PouchDB,
  Syncable, MongoDB Device Sync deprecation, and pesterhazy's local-first sync
  engine survey gist
- Scale-hardening references: PowerSync Production Readiness, Monitoring and
  Alerting, Deployment Architecture, Troubleshooting, Compacting Buckets,
  Consistency/Protocol docs, public `jepsen-powersync`, Jepsen, FoundationDB
  simulation testing, TigerBeetle VOPR/fuzzing, and Antithesis fault injection

## Decision

Do not replace the Field Guide sync engine before the current release gates.

PowerSync is the closest external system to the current architecture because it
combines local SQLite, Flutter/Dart SDK support, Supabase integration,
partial-replication rules, upload queue semantics, and attachment patterns. It
is worth a bounded spike after the current S21/S10/staging release gates, but it
is not worth attempting a migration now.

Reasons:

- Field Guide sync is domain-specific: project assignment scope, Supabase RLS,
  role leakage prevention, soft-delete graph behavior, file-backed photos,
  signatures, form responses, repair jobs, conflict presentation, and device-lab
  evidence are product behavior, not generic replication plumbing.
- A PowerSync migration would require replacing large parts of the local data
  access and sync contract, then rebuilding the test matrix around new failure
  modes.
- The current risks are hardening/evidence risks, not clear proof that the
  custom architecture is invalid.
- PowerSync, WatermelonDB, RxDB, Electric, and CouchDB/PouchDB are still useful
  as design checklists for checkpoints, idempotency, integrity probes,
  attachment queues, and consistency contracts.

## Scale-Hardening Findings

PowerSync is the strongest external reference found for production sync
hardening. It documents operational readiness, diagnostics, monitoring,
deployment sizing, compaction, bucket/checkpoint integrity, and has public
Jepsen-style correctness testing.

Findings to carry forward:

- PowerSync recommends a client diagnostics view with connection state,
  upload/download state, first-sync completion, last sync timestamp, and upload
  queue length. Field Guide should treat the sync dashboard and device-soak
  artifacts as the equivalent support surface.
- PowerSync uses scoped buckets, checkpoints, write checkpoints, and per-bucket
  checksums to avoid advancing clients through partial or corrupted state.
  Field Guide should borrow the idea at project/table scope.
- PowerSync ops docs call out usage alerts, issue alerts, health endpoints,
  replication lag, replication slot monitoring, operation history compaction,
  operations-to-rows ratio, and bucket count as scale risks. Field Guide should
  translate those to Supabase/Postgres, SQLite `change_log`, file cleanup
  queue, and device actor metrics.
- The public `jepsen-powersync` work is a useful blueprint for our device soak:
  random multi-operation transactions, multiple local and remote actors,
  environmental failures, queue-drain checks, quiescence periods, and final
  strong-convergence assertions.
- PowerSync's Jepsen work also shows that mature sync systems still find rare
  liveness bugs under disconnect/reconnect, network partitions, and process
  kill/restart. The right target is not "no hard bugs exist"; it is a harness
  that reliably surfaces, classifies, reproduces, and gates them.
- WatermelonDB contributes a compact backend-contract checklist: consistent
  pull view, transactional push, monotonic server-side change tracking, tracked
  deletes, and permission grant/revocation treated as sync changes.
- RxDB contributes the RESYNC pattern: if realtime is incomplete or suspect,
  emit a coarse "unknown changed" signal and force checkpoint iteration.
- FoundationDB, TigerBeetle, Jepsen, and Antithesis are not app sync engines,
  but they define the mature hardening method: deterministic or seedable
  workloads, systematic fault injection, model/checker assertions, liveness
  recovery windows, and reproducible failure artifacts.

## Release-Critical Hardening

These items should feed the current sync-soak and staging gates.

- [ ] Replace offset-based pull pagination with stable keyset/checkpoint
  pagination.
  - Current risk: `SupabaseSync.fetchPage` orders by `updated_at` and uses
    offset/range pagination. Concurrent writes or many equal timestamps can skip
    or duplicate rows.
  - Target: checkpoint on `(updated_at, id)` or equivalent deterministic
    cursor; preserve the pull safety margin without depending on mutable
    offsets.
  - Tests: equal `updated_at` rows across page boundaries, concurrent remote
    insert during pull, long-offline pull, restart after partial page.

- [ ] Add per-scope reconciliation probes after sync.
  - Borrow from PowerSync's checksum/write-checkpoint model.
  - Target: project/table row counts plus stable hashes for high-value tables
    after full sync and selected device-soak phases.
  - Include at minimum: `projects`, `project_assignments`, `daily_entries`,
    `entry_quantities`, `photos`, `form_responses`, `signature_files`,
    `signature_audit_log`, `documents`, and `pay_applications`.
  - Add mismatch behavior: emit a structured event, capture local/remote
    samples, and choose either scoped repair, cursor reset, or full project
    rehydrate.

- [ ] Add PowerSync-style write checkpoint semantics.
  - Do not mark a user-facing sync as fully fresh just because the local queue
    is empty.
  - Target: after `change_log` drains, verify that the server-side effect is
    visible in the next pull/reconciliation checkpoint.
  - Device-soak artifact must record queue drain, remote proof, pull proof, and
    final local proof as separate fields.

- [ ] Prove realtime hints are only hints.
  - Target: missed, delayed, duplicated, and out-of-order realtime hints must
    still converge through fallback polling or full sync.
  - Tests: disconnect realtime, mutate remotely, reconnect, verify dirty scopes
    or fallback sync recover.
  - Device gate: prove no stale unauthorized project data flashes during role
    revocation plus missed-hint recovery.

- [ ] Add idempotent replay tests for every push and pull phase.
  - Push: duplicate local change after server upsert succeeds but before
    `change_log` is marked processed.
  - Pull: duplicate page replay and duplicate row apply.
  - Delete: duplicate soft-delete push and already-absent remote row.
  - File: duplicate upload, storage 409, row upsert replay, bookmark replay.

- [ ] Add WatermelonDB-style sync contract gates.
  - Pull must provide a consistent view. If a cross-table consistent snapshot is
    not available, the cursor/checkpoint must be marked before querying so the
    next pull catches concurrent changes.
  - Push must be transactional at the semantic boundary: either the remote
    mutation is acknowledged and replay-safe or the local row remains queued.
  - Deletes and permission revocations must be represented as sync changes, not
    inferred by absence.
  - Server-side timestamps/cursors must not trust client clocks.

- [ ] Make file sync partial failures durable and queryable.
  - Current three-phase workflow is good, but failures should be first-class
    persisted states for retry, cleanup, and soak evidence.
  - Add durable state around: upload started, upload succeeded, row upsert
    succeeded, local bookmark succeeded, stale object cleanup queued.
  - Tests: crash after upload before row upsert, after row upsert before
    bookmark, after bookmark before `change_log` mark, and cleanup retry after
    storage delete failure.

- [ ] Add crash/restart tests around sync control boundaries.
  - Cases: while `sync_control.pulling = '1'`, while `sync_lock` is held, after
    cursor update, after manual conflict re-push insertion, during auth refresh,
    during background retry scheduling.
  - Acceptance: app restart clears or repairs unsafe state without losing
    already acknowledged local changes.

- [ ] Split conflict strategy by domain criticality.
  - Keep LWW where product-approved.
  - Add or document stronger behavior for append-only/audit records,
    signatures, signed form responses, quantities, and narrative fields.
  - Tests: same record edited on S21 and S10 plus remote actor; prove expected
    winner, conflict log contents, and user-visible review behavior.

- [ ] Fix misleading file-sync phase logging.
  - `file_sync_three_phase_workflow.dart` logs "Phase 3 bookmark failed" during
    phase 2 row upsert failure.
  - Low effort, high triage value during soak failures.

## Device-Soak Expansion

These items should remain in the device-sync soak, not the backend/RLS soak.

- [ ] Keep backend/RLS soak and device-sync soak explicitly separate.
  - Backend/RLS proves direct Supabase policy and remote concurrency.
  - Device-sync proves SQLite triggers, `change_log`, `sync_lock`, auth
    rebinding, UI-triggered sync, storage bytes, realtime hints, and visible UI
    convergence.

- [ ] Add multi-device same-record convergence scenarios.
  - S21 and S10 edit the same daily entry, quantity, photo metadata, and form
    response while remote actor also mutates project-scoped data.
  - Verify final local and remote state, conflict log, UI presentation, and
    queue drain.

- [ ] Add a Jepsen-style workload/checker layer to the device soak.
  - Generate a seedable sequence of multi-step operations instead of only fixed
    scripted happy paths.
  - Include local-device actors, direct remote Supabase actors, and read-only
    checker actors.
  - Track every operation in a history log with actor, user, project, table,
    record id, start/end time, result, and expected invariant impact.
  - Add final checkers for no lost acknowledged writes, no blocked rows, local
    and remote convergence, role visibility, storage object presence/absence,
    and conflict-log expectations.

- [ ] Add Jepsen/PowerSync-style quiescence gates.
  - After any fault window, stop new writes, heal connectivity, then wait for:
    local queue count = 0, blocked count = 0, sync/download state idle,
    realtime/fallback sync settled, and reconciliation hashes matched.
  - Only then perform final local/remote reads and mark the run accepted.

- [ ] Add deterministic seeds and replay bundles.
  - Every soak run should record a seed, actor list, operation schedule, fault
    schedule, fixture hash, app build/version, schema hash, device ids, and
    relevant Supabase project info.
  - A failing run should produce enough data to rerun the same operation/fault
    schedule against S21/S10 or a headless local app actor.

- [ ] Add offline burst and long-offline replay.
  - Queue many local changes while offline, then reconnect.
  - Include file-backed rows and role revocation during the offline window.
  - Acceptance: no blocked rows, no unauthorized data retained, no missing
    storage objects.

- [ ] Add same-device account switching stress.
  - Admin -> inspector -> office technician -> revoked inspector on the same
    device.
  - Acceptance: local scope cache, synced project list, realtime channels,
    storage access, and sync dashboard all match the active session.

- [ ] Add remaining file-backed form/signature/export families to device soak.
  - MDOT 1126 typed signature and expanded fields/rows are accepted on S21 as
    the current form/signature baseline; keep them in regression coverage.
  - MDOT 0582B form-response mutation is accepted on S21; keep it in
    regression coverage and still add export/storage proof.
  - MDOT 1174R.
  - Form exports and saved-form/gallery lifecycle.
  - Document/pay-app/export artifacts where product behavior requires sync.

- [ ] Add storage RLS and object-proof gates for every file-backed table.
  - Proof must include upload, remote row, authorized download, unauthorized
    denial, cleanup delete, and object absence.

- [ ] Add explicit fault families to the device soak.
  - Client disconnect/reconnect.
  - App process pause/resume or background/foreground.
  - App process kill/restart while preserving SQLite files.
  - Network partition: outbound-only, inbound-only where possible, and full
    disconnect.
  - Supabase 401/auth refresh, 403/RLS denial, 409 storage conflict, timeout,
    and rate-limit style transient failures.
  - Sync-control crash points: during `pulling=1`, lock held, cursor write,
    file upload, row upsert, local bookmark, and cleanup.

- [ ] Add liveness-specific acceptance criteria.
  - Safety checks prove no unauthorized data, no lost acknowledged writes, and
    no invalid final state.
  - Liveness checks prove the system recovers after faults: queues drain, sync
    state returns idle, retries stop escalating, and convergence happens within
    a defined timeout.

## Consistency Contract Docs

- [ ] Write `docs/sync-consistency-contract.md`.
  - State what the engine guarantees and what it does not.
  - Cover local acknowledged writes, remote acknowledged writes, eventual
    convergence, conflict policy, immutable/audit tables, file object semantics,
    storage cleanup, role revocation, realtime hint behavior, and recovery
    responsibilities.

- [ ] Document per-table conflict and sync semantics.
  - For every adapter: scope type, insert/update/delete behavior, soft-delete
    support, file behavior, conflict strategy, LWW allowed or not, natural-key
    remap behavior, and required soak coverage.

- [ ] Add a "new synced table checklist".
  - Adapter metadata.
  - SQLite trigger coverage.
  - Supabase table/RLS/storage policies.
  - Migration and rollback.
  - Fixture data.
  - Characterization tests.
  - Device-soak mutation or explicit exemption.
  - Reconciliation probe membership.

- [ ] Add `docs/sync-scale-hardening-playbook.md`.
  - Describe the hardening method: seedable workloads, actor model, fault
    families, quiescence gates, convergence checkers, diagnostics, and release
    thresholds.
  - Include a table mapping PowerSync/Jepsen/WatermelonDB/RxDB ideas to the
    Field Guide implementation.
  - Include an operator section for staging: what to inspect when a device has
    blocked rows, missed storage objects, stale role scope, or non-matching
    reconciliation hashes.

## External Patterns To Adopt Without Migrating

- [ ] PowerSync-style client diagnostics contract.
  - Expose and persist: connected, connecting, uploading, downloading,
    hasSynced, lastSyncedAt, queue count, blocked count, retry count, active
    user/company/project, app version, schema version, and sync run id.
  - Include the same fields in device-soak artifacts and Sentry/log events.

- [ ] PowerSync-style write checkpoints.
  - After upload queue/change-log drains, verify the server has processed all
    pushed writes before freshness UI treats sync as fully current.

- [ ] PowerSync-style scoped integrity checks.
  - For each project/table scope, compare compact local and remote checksums or
    hashes and trigger repair/full rehydrate on mismatch.

- [ ] PowerSync-style operational alerts.
  - Alert on blocked queue rows, rising retry counts, stale sync locks,
    `pulling=1` not reset, stale last sync, repeated reconciliation mismatch,
    storage cleanup backlog, and per-device sync timeouts.
  - For staging/backend paths, also track Supabase/Postgres replication health,
    storage errors, RLS denials, and edge-function/log-drain failures.

- [ ] PowerSync-style operation history maintenance.
  - Define retention/compaction policy for `change_log`, `conflict_log`,
    debug logs, repair audit rows, and storage cleanup queue.
  - Track an operations-to-live-rows style ratio for local sync tables so
    high-churn data does not quietly degrade sync performance.

- [ ] PowerSync attachment-helper pattern.
  - Treat file upload/download as a persisted attachment queue with progress,
    retry, and cleanup states, not only inline row-sync work.

- [ ] WatermelonDB-style backend contract tests.
  - Consistent pull snapshot.
  - Transactional push.
  - Idempotent create/update/delete.
  - Conflict detection when server changed since last pull.
  - Migration-aware sync for new columns/tables.

- [ ] RxDB-style checkpoint and resync tests.
  - Checkpoint consists of deterministic ordering fields, not only timestamp.
  - Reconnect emits or schedules a resync so missed realtime events are harmless.
  - Push includes enough assumed-master/prior-state evidence to detect conflicts
    where timestamps are insufficient.

- [ ] Jepsen-style checker model.
  - Define invariants independently of UI flow implementation.
  - Check no lost acknowledged writes, monotonic reads where applicable,
    convergence after quiescence, role isolation, atomic visibility of related
    records, and storage row/object consistency.

- [ ] FoundationDB/TigerBeetle-style reproducibility.
  - Prefer seedable fault/workload generation.
  - Save failing seeds and minimize them into smaller regression tests when
    possible.
  - Separate safety mode (fault-heavy correctness) from liveness mode
    (faults stop, system must recover).

- [ ] Antithesis-style quiet periods.
  - Add an explicit "stop faults and heal" phase before final assertions.
  - This avoids accepting runs that only prove the system was under continuous
    failure, not that it can recover when conditions improve.

- [ ] CouchDB/PouchDB-style conflict preservation where useful.
  - Do not adopt revision trees globally.
  - Consider preserving both sides for selected narrative or quantity conflicts
    where silent LWW data loss would be unacceptable.

- [ ] Electric-style read-path scope thinking.
  - Treat project assignment and role scope as first-class replication shapes.
  - Use the concept to audit which tables should pull for a project, company,
    user, assignment, or entry.

## PowerSync Spike

Status: recommended after current release gates; not a current migration.

- [ ] Run a one-week technical spike in a throwaway branch.
  - Goal: answer migration feasibility, not productionize.
  - Data slice: one project with assignments, contractors, daily entries,
    quantities, one photo, one form response, and one signature file.
  - Backend: staging or disposable Supabase project only.
  - Success criteria: first sync, local write, remote write, role revocation,
    file object proof, and conflict case can be represented without losing
    Field Guide semantics.

- [ ] Evaluate three integration modes.
  - Full replacement: PowerSync owns local replicated SQLite data and upload
    queue.
  - Hybrid read path: PowerSync hydrates read models while current engine owns
    writes/files. Expected risk: two sync truths, likely not worth it.
  - Pattern adoption only: keep current engine and port concepts like
    checkpoints, checksums, attachment queues, and sync rules into Field Guide.

- [ ] PowerSync spike decision criteria.
  - Migration is only worth continuing if it reduces more code/risk than it
    adds across RLS, files, forms, signatures, role revocation, repairs, and
    test evidence.
  - Stop if Field Guide needs substantial custom code beside PowerSync for the
    same failure modes the current engine already handles.
  - Stop if the local schema/data access rewrite delays current release gates.
  - Continue only if PowerSync materially simplifies scoped pull, upload queue
    reliability, and attachment handling while preserving RLS and device-lab
    acceptance behavior.
  - Include a hardening-tooling evaluation: SyncStatus diagnostics, upload
    queue inspection, local DB inspection, sync-rule/bucket diagnostics,
    checksums/checkpoints, alerts, and whether its Jepsen-proven semantics
    cover Field Guide's project/role/file/signature cases.

- [ ] Expected likely outcome.
  - Do not migrate for the current release.
  - Most likely durable adoption path is "pattern adoption only".
  - Reassess full migration after staging/device gates and once a small
    PowerSync proof records concrete cost, missing semantics, and code removed.

## Explicit Non-Goals

- Do not introduce CRDTs globally.
- Do not treat realtime as authoritative replication.
- Do not replace device sync soak with backend/RLS soak.
- Do not add a second production sync truth without a dedicated migration plan.
- Do not use MongoDB Device Sync as a candidate; it is deprecated/end-of-life.
