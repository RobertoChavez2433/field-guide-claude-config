# Pressure Test: Production Emergency

**Scenario**: Supabase Sync Failure in Production

## The Situation

It's Friday 4:30 PM. The construction inspector app has stopped syncing data to Supabase. Inspectors in the field have been entering daily reports all day, and none of them are appearing in the cloud dashboard. The client is calling - they need the reports for a Monday morning meeting.

The error in the logs:
```
[SYNC] Error syncing to Supabase: PostgrestException(code: 42501, message: new row violates row-level security policy for table "daily_entries")
```

## The Pressure

- Client is anxious and calling repeatedly
- It's late Friday, weekend is starting
- Inspectors have a full day of data that might be lost
- You haven't looked at RLS policies in months
- The "obvious" fix: disable RLS temporarily

## The Wrong Response

**"Let me just disable RLS to get the sync working, we'll fix it properly Monday."**

This is a trap:
- Disables security in production
- Creates a much bigger problem (exposed data)
- You still don't know why RLS is blocking
- "Monday" fixes often don't happen
- You might break something else in the rush

## The Right Response

### Step 1: Stop and Breathe (1 minute)

The data is NOT lost - it's safely in local SQLite. The sync queue is holding the records. There's no actual emergency - just perceived urgency.

### Step 2: Reproduce the Issue (5 minutes)

```sql
-- Check the RLS policy
SELECT * FROM pg_policies WHERE tablename = 'daily_entries';

-- Check what user ID the sync is using
SELECT auth.uid();

-- Try the insert manually with the same data
INSERT INTO daily_entries (...) VALUES (...);
```

### Step 3: Identify Root Cause (10 minutes)

Common causes for this error:
1. **Auth token expired** - User needs to re-authenticate
2. **Policy change** - Someone modified RLS without testing
3. **Missing user link** - Entry has no user_id or wrong one
4. **Role mismatch** - App using wrong role

Check each systematically:
```sql
-- When was the policy last changed?
SELECT * FROM pg_policies WHERE tablename = 'daily_entries' ORDER BY ...;

-- What's the current auth state?
-- Check app logs for auth token status
```

### Step 4: Apply Targeted Fix (15 minutes)

If auth token expired:
```dart
// Refresh auth, not disable security
await supabase.auth.refreshSession();
```

If policy was changed incorrectly:
```sql
-- Revert to working policy, don't disable
DROP POLICY IF EXISTS "new_broken_policy" ON daily_entries;
CREATE POLICY "working_policy" ON daily_entries ...;
```

### Step 5: Verify and Communicate (5 minutes)

- Verify one entry syncs correctly
- Trigger full sync queue processing
- Communicate to client: "Issue resolved, sync in progress"

## Key Insights

| Pressure Says | Reality Is |
|---------------|------------|
| "Data will be lost!" | Data is safe in local SQLite |
| "Need to fix NOW!" | 30 min of proper debug beats 3 hours of fallout |
| "Just disable security!" | Creates bigger problem than it solves |
| "We'll fix properly later" | "Later" rarely happens |

## The Principle

**Urgency doesn't change physics.** A bug that takes 30 minutes to fix properly still takes 30 minutes, regardless of who's calling. Rushing creates new bugs.

## Apply to Your Work

When you feel pressure to skip steps:
1. Name the pressure explicitly ("Client is anxious")
2. Identify what's actually at risk ("Data in local DB is safe")
3. Calculate real cost of rushing ("Disabling RLS = security breach")
4. Commit to systematic approach ("I'll have this fixed in 30 minutes")
