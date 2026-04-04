# Smarter Sync Strategy Spec

Date: 2026-04-03
Author: Codex
Status: Proposed foundation

## Purpose

Define the intended sync direction moving forward so implementation work has a stable foundation:

- startup/foreground sync should be fast
- the app should not run a broad full project-wide sync by default on app open
- remote freshness should be driven by targeted invalidation, not blind sweeping
- users should always have a visible manual full-sync action

## Verified Current State

### What already works
- Local push is incremental through SQLite `change_log`
- Pull is cursor-based per table, not a full redownload
- FCM exists and can trigger sync
- Manual sync dashboard exists
- Sync mutex / change tracking / adapter ordering are fundamentally sound

### Current gaps
1. Startup sync is inconsistent and route-dependent.
2. Foreground sync does too much blocking work.
3. Pull strategy is broad per-table sweeping, not targeted remote invalidation.
4. Manual sync is too buried in the UI.
5. Observability is not granular enough to reason about sync phase cost quickly.

## Core Decisions

### 1. Sync Modes

The app will support three sync modes:

- `Quick sync`
  - startup / foreground / background catch-up
  - low-latency path
  - push local changes first
  - avoid broad project-wide `pushAndPull()` by default

- `Full sync`
  - user-invoked explicit refresh
  - broader push + pull sweep
  - fallback recovery path

- `Maintenance sync`
  - deferred or background work
  - integrity checks
  - orphan cleanup
  - company member pulls
  - `last_synced_at` update

### 2. Manual Sync Must Be Global

A manual sync action must be available in the main app chrome so the user does not need to navigate to Settings to force a refresh.

### 3. Local Change Log Remains The Push Source Of Truth

The existing `change_log` pattern remains the authoritative local push mechanism.

No per-record `sync_status` rollback. No duplicate sync queue.

### 4. Remote Freshness Must Become Hint-Driven

The client currently lacks a proper remote delta feed.

Target model:

- Supabase-originated foreground invalidation hints
- FCM background invalidation hints
- dirty-scope tracking locally
- quick sync pulls only affected scopes whenever possible

### 5. Full Sync Is Fallback, Not Default

Broad full sync remains necessary, but only for:

- explicit user request
- recovery / stale cursor cases
- periodic maintenance safety nets

It should not be the default startup behavior.

## Remote Invalidation Architecture

### Foreground Path: Supabase Broadcast / Realtime Hints

Use Supabase-originated change hints while the app is open.

Expected hint payload shape:

- `company_id`
- `project_id` when applicable
- `table_name`
- `changed_at`
- optional coarse `scope_type`

The client should treat these as invalidation hints, not trusted data replacements.

### Background / Closed-App Path: FCM Data Messages

Use FCM data messages to wake the device or mark scopes dirty when the app is backgrounded or closed.

Expected FCM behavior:

- send a small invalidation payload
- schedule quick sync or mark dirty scope
- do not default to full sync

### Why Both Are Needed

- Supabase Broadcast is best for live foreground responsiveness
- FCM is best for background wake-up and closed-app catch-up

They solve different delivery problems and should complement each other.

## Target Behavior

### Startup

- app launches
- auth/company context becomes ready
- one-shot `Quick sync` runs
- startup sync does not broad-sweep all synced scopes by default

### Foreground Remote Change While App Is Open

- Supabase hint arrives
- client marks scope dirty
- quick targeted sync runs

### Remote Change While App Is Backgrounded

- server emits FCM data message
- app wakes / schedules work
- quick targeted sync runs later

### User Wants Certainty

- user taps top-bar sync action
- app runs `Full sync`

## Scope Model

The sync system should become dirty-scope-aware.

Candidate scope dimensions:

- company-wide
- project-wide
- table-within-project
- rare global builtins

Preferred pull granularity:

- project + table when possible
- broader only when required by current adapter constraints

## Non-Goals

- Replacing SQLite trigger-based change capture
- Replacing adapter-based sync architecture
- Real-time collaborative editing semantics
- Eliminating full sync entirely

## Acceptance Intent

The future sync system should satisfy:

1. App open feels fresh without paying for a full sync cycle.
2. A user can always force a full sync from the main app sync button.
3. Foreground remote changes can be reacted to quickly.
4. Background remote changes can wake or notify the device efficiently.
5. Multi-project users do not pay a broad full project-wide sync cost on every app open.

## Primary Docs To Keep Aligned

- `.claude/prds/sync-prd.md`
- `.claude/docs/features/feature-sync-overview.md`
- `.claude/docs/features/feature-sync-architecture.md`
- `.claude/architecture-decisions/sync-constraints.md`
- `.codex/plans/2026-04-03-startup-sync-performance-plan.md`
