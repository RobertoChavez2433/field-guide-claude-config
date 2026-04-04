# Private Sync Hint Channel Spec

Date: 2026-04-04
Author: Codex
Status: Proposed follow-up to the sync strategy foundation

## Purpose

Eliminate metadata leakage from predictable tenant-wide Supabase Broadcast channels while preserving the existing sync product direction:

- SQLite remains the local source of working state
- `change_log` remains the incremental push source of truth
- offline work must continue without network dependency
- remote hints remain advisory invalidation signals only
- foreground freshness can still react quickly without broad full sync

## Decision Summary

The app will stop subscribing to predictable tenant channels such as `sync_hints:{company_id}`.

Foreground invalidation will instead use server-issued opaque per-device channels:

- one active sync-hint channel per authenticated app installation
- channel names are random opaque tokens, not derived from `company_id`, `user_id`, or role
- the client can only obtain its channel through an auth-protected registration RPC
- server-side fan-out resolves eligible devices by company and broadcasts to each device channel

This keeps the existing Supabase Broadcast transport, but removes predictable tenant addressing.

## Problem Being Solved

The current tenant-channel approach leaks operational metadata to any unauthorized listener who can guess a channel name and reach the Broadcast transport.

Metadata at risk includes:

- company activity timing
- project activity timing
- changed table category (`daily_entries`, `photos`, `documents`, `form_responses`, etc.)
- coarse work-pattern inference

The risk is metadata leakage, not authoritative data leakage. Record contents must still come through normal sync reads protected by auth and RLS.

## Non-Goals

- replacing SQLite-first sync
- making Broadcast a source of truth
- introducing OAuth2 as a prerequisite for this change
- removing FCM background invalidation
- removing manual full sync or fallback full recovery

## Architecture

### 1. Channel Scope

Use **opaque per-device channels**, not per-company channels.

Why per-device instead of per-company:

- avoids predictable tenant addressing
- supports multiple devices for the same user
- supports clean stale-device expiration
- minimizes cross-device metadata visibility beyond intended recipients

### 2. Registration Model

Each authenticated app installation maintains a local `device_install_id`.

On auth-ready startup, the client calls a registration RPC:

- input: `device_install_id`, optional platform/app-version metadata
- auth source: current Supabase session
- output: `channel_name`, `subscription_id`, `expires_at`, `refresh_after`

The server validates the session, resolves the caller's `user_id` and `company_id`, and issues or refreshes an opaque channel assignment.

### 3. Channel Naming

Channel names must be opaque and non-derivable.

Required properties:

- at least 128 bits of randomness
- not derived from tenant identifiers
- not stable across arbitrary reinstall/re-registration unless explicitly refreshed by server state

Recommended shape:

- `sync_hint:{opaque_token}`

Where `{opaque_token}` is server-generated random data.

### 4. Subscription Storage

Add a server-side table for active sync-hint subscriptions.

Recommended fields:

- `id`
- `user_id`
- `company_id`
- `device_install_id`
- `channel_name`
- `platform`
- `app_version`
- `last_seen_at`
- `expires_at`
- `created_at`
- `updated_at`
- optional `revoked_at`

### 5. Client Foreground Flow

1. app starts
2. auth/company context becomes ready
3. client registers or refreshes its private sync-hint channel
4. client subscribes only to the returned opaque channel
5. incoming hints mark dirty scopes locally
6. quick sync runs if appropriate

If the app signs out, changes company context, or loses auth:

- unsubscribe from the current channel
- clear local subscription binding
- optionally call best-effort unregister/deactivate RPC

### 6. Server Fan-Out Flow

1. table trigger detects relevant remote mutation
2. trigger builds an invalidation payload
3. trigger or helper function resolves eligible active subscriptions for the affected company
4. server broadcasts the payload to each active device channel
5. server also invokes FCM push for background or closed-app recovery

### 7. Background Behavior

Foreground Broadcast remains optional and advisory.

Background and closed-app catch-up still rely on:

- FCM data messages
- startup/resume quick sync
- manual full sync when the user wants certainty

## Security Requirements

### Hard Requirements

- MUST NOT use predictable tenant-wide Broadcast channel names
- MUST issue channel names only from an authenticated server-side RPC
- MUST store subscription mappings server-side, not infer them from channel naming conventions
- MUST scope fan-out by server-resolved `company_id`
- MUST treat Broadcast hints as invalidation metadata only
- MUST continue to rely on normal auth + RLS for actual data reads
- MUST expire or revoke stale device subscriptions

### Soft Guidelines

- prefer per-device channels over per-user shared channels
- refresh channel registration on startup and periodically while foregrounded
- prune stale subscriptions automatically
- keep hint payloads minimal

## Hint Payload Shape

Payload stays advisory and minimal:

- `company_id`
- `project_id` when applicable
- `table_name`
- `changed_at`
- optional coarse `scope_type`

The privacy improvement comes from addressing and fan-out, not from inflating payload contents.

## Required Data/Backend Changes

### New database objects

- `sync_hint_subscriptions` table
- auth-protected `register_sync_hint_channel(...)` RPC
- optional `deactivate_sync_hint_channel(...)` RPC
- optional periodic cleanup job for expired subscriptions

### Updated sync hint fan-out

- remove direct dependency on `sync_hints:{company_id}`
- replace tenant broadcast with per-device fan-out lookup
- keep FCM invocation path intact

### Required auth posture

This design works with the current Supabase auth model.

It does **not** require OAuth2 to land. A future OAuth2 / OIDC migration for AASHTOWare integration can still coexist with the same private-channel model.

## Client Changes Required

- persist a local `device_install_id`
- register/refresh the private channel after auth/company readiness
- subscribe via `RealtimeHintHandler` only to the returned opaque channel
- rebind or clear the subscription on auth/company changes
- keep FCM background hint handling unchanged except for documentation alignment

## Documentation Changes Required

The following docs must describe private sync-hint channels instead of predictable tenant channels:

- `.claude/specs/2026-04-03-sync-strategy-codex-spec.md`
- `.claude/prds/sync-prd.md`
- `.claude/docs/features/feature-sync-overview.md`
- `.claude/docs/features/feature-sync-architecture.md`
- `.claude/architecture-decisions/sync-constraints.md`

## Acceptance Intent

The architecture should satisfy:

1. Foreground invalidation no longer depends on predictable tenant channel names.
2. Unauthorized listeners cannot infer target channels from `company_id`.
3. SQLite-first and offline-first behavior remain unchanged.
4. Broadcast remains advisory only; real data still flows through normal sync pull.
5. FCM continues to cover background and closed-app invalidation.

## Migration Notes

Recommended migration sequence:

1. add subscription table + RPCs
2. update client bootstrap to register and subscribe to opaque channel
3. update server-side fan-out to target subscription rows
4. remove legacy tenant-channel subscriptions and documentation

## Required Implementation Changes

- add `device_install_id` persistence on the client
- add subscription registration and refresh flow in sync initialization
- add server-side subscription table and cleanup
- refactor sync-hint SQL fan-out to query active device subscriptions
- update tests for registration, rebinding, stale cleanup, and trigger fan-out
