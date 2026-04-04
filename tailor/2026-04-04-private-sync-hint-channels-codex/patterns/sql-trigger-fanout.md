# Pattern: SQL Trigger → Fan-Out

## How We Do It

Server-side sync hints use PostgreSQL AFTER triggers on all synced tables. Three trigger functions handle different table shapes (company-scoped, project-scoped, contractor-scoped). Each trigger: (1) resolves the affected company_id, (2) applies per-transaction advisory lock deduplication, (3) broadcasts via Supabase Realtime HTTP API, and (4) invokes the FCM edge function. Currently, all three broadcast to a single predictable channel `sync_hints:{company_id}`. The spec replaces this with per-device channel fan-out by querying `sync_hint_subscriptions`.

## Exemplars

### broadcast_sync_hint_company() (`supabase/migrations/20260404000000_sync_hint_broadcast_trigger.sql:40`)

```sql
CREATE OR REPLACE FUNCTION public.broadcast_sync_hint_company()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_row record;
  v_company_id uuid;
  v_payload jsonb;
  v_channel_name text;
  v_dedupe_key text;
  v_realtime_url text;
  v_service_role_key text;
BEGIN
  v_row := COALESCE(NEW, OLD);
  v_company_id := (v_row).company_id;
  v_realtime_url := current_setting('supabase.realtime_url', true);
  v_service_role_key := current_setting('supabase.service_role_key', true);

  IF v_company_id IS NULL OR v_service_role_key IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  -- Per-transaction advisory lock for deduplication
  v_dedupe_key := TG_TABLE_NAME || ':' || v_company_id::text;
  IF NOT pg_try_advisory_xact_lock(
    hashtext('sync_hint_company'),
    hashtext(v_dedupe_key)
  ) THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  v_payload := jsonb_build_object(
    'company_id', v_company_id::text,
    'project_id', NULL,
    'table_name', TG_TABLE_NAME,
    'scope_type', 'company_wide',
    'changed_at', now()::text
  );
  v_channel_name := 'sync_hints:' || v_company_id::text;  -- ← PREDICTABLE, TO REPLACE

  -- Broadcast via Realtime HTTP API
  IF v_realtime_url IS NOT NULL THEN
    PERFORM extensions.http_post(
      url := v_realtime_url || '/api/broadcast',
      headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'apikey', v_service_role_key
      ),
      body := jsonb_build_object(
        'channel', v_channel_name,
        'event', 'sync_hint',
        'payload', v_payload
      )
    );
  END IF;

  -- Also invoke FCM edge function
  PERFORM public.invoke_daily_sync_push(v_payload);

  RETURN COALESCE(NEW, OLD);
EXCEPTION
  WHEN OTHERS THEN
    RAISE WARNING 'broadcast_sync_hint_company failed: %', SQLERRM;
    RETURN COALESCE(NEW, OLD);
END;
$$;
```

### invoke_daily_sync_push() (`20260404000000_sync_hint_broadcast_trigger.sql:3`)

Helper that calls the edge function. Uses `supabase.functions_url` (with `supabase.url` fallback) and `supabase.service_role_key`.

## Reusable Methods

| Function | File:Line | Signature | When to Use |
|----------|-----------|-----------|-------------|
| `broadcast_sync_hint_company()` | `broadcast_trigger.sql:40` | `RETURNS trigger` | Tables with direct `company_id` column |
| `broadcast_sync_hint_project()` | `broadcast_trigger.sql:106` | `RETURNS trigger` | Tables with `project_id` (joins to projects for company_id) |
| `broadcast_sync_hint_contractor()` | `broadcast_trigger.sql:181` | `RETURNS trigger` | Tables with `contractor_id` (joins contractors→projects→company) |
| `invoke_daily_sync_push()` | `broadcast_trigger.sql:3` | `(p_payload jsonb) RETURNS void` | Call edge function for FCM push |

## Key Implementation Notes

- All 3 functions use `SECURITY DEFINER` (runs as owner, not caller)
- Advisory locks (`pg_try_advisory_xact_lock`) deduplicate within a transaction
- `COALESCE(NEW, OLD)` handles INSERT/UPDATE/DELETE uniformly
- Exception handler returns row to prevent trigger failure from blocking DML
- The `http` extension must be enabled (`CREATE EXTENSION IF NOT EXISTS http WITH SCHEMA extensions`)
