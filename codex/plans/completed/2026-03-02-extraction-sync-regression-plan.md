# Codex Plan: Extraction + Sync Regression Containment

**Last Updated**: 2026-03-02
**Status**: READY
**Scope**: Android extraction regression (129 items / $357B budget) + Supabase sync pull failure (`daily_entries.test_results`) + partial-push data-flow risk
**Related upstream plan**: `.claude/plans/2026-03-02-sync-resilience-fix.md`

## Evidence Summary

### Extraction (live Android session `session_2026-03-02_18-12-29`)
- `pdf_import.log` shows Stage 4A dropped to `data=130`, Stage 4E dropped to `130 parsed items`, then post-process removed one duplicate and finished at `129`.
- The run still auto-accepted with score `0.978`, so the current quality gate did not stop the regression.
- The device SQLite DB confirms the imported project exists locally with 129 `bid_items` and `totalBudget = 357,089,588,241.38`.
- The primary bad row is `item_number = "4 S"` with description merged across items 4+5, `bid_quantity = 1641`, and `unit_price = 217,600,087.45`.
- The DB also shows `95` was misread as `05`, and `51` is missing from the final persisted dataset.

### Sync (same Android session)
- `sync.log` shows all retries fail in pull phase on `daily_entries` with `DatabaseException(no such column: test_results ...)`.
- The device DB is at `PRAGMA user_version = 24` and `daily_entries` no longer contains `test_results`.
- `SyncService._convertForLocal()` claims to strip unknown columns, but it does not actually remove any keys before `db.insert()` / `db.update()`.
- Because `SyncService._pushBaseData()` uses in-memory `_lastSyncTime == null` as the “first-ever sync” test, every cold start behaves like a first sync and can push local data before the later pull crash.

## Parallel Investigation Findings (Agent-Style Synthesis)

### Extraction Track A: Device log + DB forensics
- The regression is not a UI-only formatting bug; the malformed values are persisted in SQLite.
- The $357B budget comes from one corrupted merged row, not a broad summation bug.
- The merged row pattern matches adjacent-row concatenation: item 4 + item 5 data collapsed into one record.

### Extraction Track B: Code-path review
- The regression likely sits upstream of post-processing, in row/cell extraction or OCR crop handling, not in dashboard math.
- The geometry-aware `CropUpscaler` raises target DPI above 600 for narrow columns, which is the most likely recent change affecting Android OCR behavior.
- `PostProcessUtils` can legally collapse multi-period numeric strings into a valid decimal, which turns concatenated OCR text into a huge but syntactically valid price instead of rejecting it.
- Current auto-accept logic can miss this class of failure because checksum uses parsed `bidAmount`, while the dashboard budget later uses `bidQuantity * unitPrice` after `bidAmount` has been discarded.

### Sync Track A: Device log + schema forensics
- The current sync blocker is no longer DNS; it is a local/remote schema mismatch on `daily_entries.test_results`.
- The pull crash happens after earlier tables have already been processed, so an error banner does not imply “nothing synced.”

### Sync Track B: Data-flow review
- `_convertForLocal()` is the direct defect: it passes remote columns through unchanged despite the comment claiming otherwise.
- `_pushBaseData()` is structurally unsafe because “first sync” is process-local, not durable.
- This combination means a corrupted project can be pushed to Supabase before the pull phase crashes, then the app still reports sync failure.

## Fix Plan

### Phase 1: Contain the Extraction Regression
**Agent**: `pdf-agent`
**Files**:
- `lib/features/pdf/services/extraction/stages/text_recognizer_v2.dart`
- `lib/features/pdf/services/extraction/shared/crop_upscaler.dart`
- `lib/features/pdf/services/extraction/stages/post_processor_v2.dart`
- `lib/features/pdf/services/extraction/shared/post_process_utils.dart`

**Steps**:
1. Add targeted diagnostics for Android reproduction around rows/items 4/5, 51, and 95 so we can confirm whether the failure is row-boundary collapse, cell crop bleed, or OCR token concatenation.
2. Tighten the geometry-aware upscaler with a bounded safety rule for narrow numeric/item-number columns so Android does not over-amplify cross-row contamination.
3. Add a structural reject/repair guard for clearly concatenated numeric strings before they become valid huge decimals (for example, multiple decimal groups collapsing into one large price).
4. Promote non-canonical item numbers (`4 S`, `05` in an otherwise 1-131 schedule, missing-sequence gaps) from soft warnings into blocking review conditions.

### Phase 2: Add an Import Safety Net
**Agent**: `backend-data-layer-agent`
**Files**:
- `lib/features/pdf/presentation/screens/pdf_import_preview_screen.dart`
- `lib/features/pdf/data/models/parsed_bid_item.dart`
- `lib/features/dashboard/presentation/screens/project_dashboard_screen.dart`

**Steps**:
1. Preserve enough import-time signal to detect impossible rows before persistence (the current `BidItem` model drops `bidAmount`, which hides the checksum context after import).
2. Block or force manual review when a row’s computed extended value is a catastrophic outlier relative to the document and the item number/sequence is already suspicious.
3. Prevent bad imports from silently creating poisoned project budgets even if OCR regresses again.

### Phase 3: Fix the Sync Pull Crash Robustly
**Agent**: `backend-data-layer-agent`
**Files**:
- `lib/services/sync_service.dart`

**Steps**:
1. Make `_convertForLocal()` actually strip unknown columns by comparing remote keys to the local SQLite schema (`PRAGMA table_info`) before insert/update.
2. Cache allowed-column sets per table so schema filtering does not add per-record overhead.
3. Log dropped remote fields once per table/session so schema drift is visible in logs.
4. Add a regression test that simulates a remote `daily_entries` payload containing `test_results` and verifies the pull succeeds locally.

### Phase 4: Stop Re-Pushing “First Sync” on Every Cold Start
**Agent**: `backend-supabase-agent`
**Files**:
- `lib/services/sync_service.dart`
- `lib/features/sync/application/sync_orchestrator.dart`
- `lib/features/auth/data/models/user_profile.dart` (read for existing durable timestamp source)

**Steps**:
1. Replace the process-local `_lastSyncTime == null` heuristic with a durable “has completed initial full sync” signal.
2. Source that signal from persisted local state and/or the existing `user_profiles.last_synced_at` flow instead of volatile in-memory state.
3. Ensure base-data full push runs only once per account/company context, not once per process.
4. Add explicit logging so the app states whether it is doing an initial full push or an incremental sync.

### Phase 5: Clean Up Bad Data Before Re-Validation
**Agent**: `backend-supabase-agent` + `backend-data-layer-agent`
**Files**:
- No code first; execute a controlled cleanup after the fixes are in place.

**Steps**:
1. Remove the corrupted project `1a05e4c4-ebd0-45b0-923b-0b21b8e2d1b7` locally before re-import testing.
2. Assume the same project may already exist remotely because push precedes the failing pull; verify and delete the remote copy as part of cleanup.
3. Re-run the Android import and confirm `131` items, no malformed item numbers, and budget returns to the expected ~`$7.88M` range.

## Verification
1. Pull the live Android DB again and verify the next import has exactly `131` bid items.
2. Confirm item numbers `4`, `5`, `51`, and `95` all exist with canonical values; no `4 S` / `05` survivors.
3. Confirm project budget is near the known Springfield baseline, not compacted to a `B`-suffix outlier.
4. Confirm `sync.log` no longer reports `no such column: test_results` and the cycle completes without retries.
5. Confirm a cold restart does not trigger another unconditional base-data full push.

## Adversarial Review Findings Integrated
- Do not fix sync with a one-off `test_results` special case only; the guard must be generic for future schema drift.
- Do not rely only on UI budget validation; the extraction pipeline needs an upstream structural defense so poisoned rows never auto-import.
- Recovery must include local and remote cleanup because the current push-then-pull flow likely already propagated the bad project.
- Any extraction safety net that depends on checksum context must run before `ParsedBidItem -> BidItem` conversion, because `BidItem` does not retain `bidAmount`.
- The current implementation violates the intended “first-ever sync” behavior; the durable sync-state fix is required, not optional.
