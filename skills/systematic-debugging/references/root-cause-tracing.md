# Root Cause Tracing

Five-step backward tracing from symptom to source.

## The Five Whys (Adapted)

Start from the symptom and work backward:

### Step 1: What is the symptom?
Document the exact observable problem.

```
SYMPTOM: Widget not displaying updated data after save
```

### Step 2: What directly causes this symptom?
The immediate technical cause.

```
DIRECT CAUSE: Provider's notifyListeners() not triggering rebuild
```

### Step 3: Why does that happen?
The condition that allows the direct cause.

```
CONDITION: notifyListeners() called, but widget not listening to this provider
```

### Step 4: What allows that condition?
The design/code that permits the condition.

```
ALLOWS: Widget using context.read() instead of context.watch()
```

### Step 5: What is the root cause?
The underlying mistake that should be fixed.

```
ROOT CAUSE: Misunderstanding of read() vs watch() in Provider pattern
```

## Tracing Template

```markdown
## Bug: [Brief Title]

### Symptom
[What the user sees / what fails]

### Direct Cause
[Immediate technical reason]

### Condition
[What allows the direct cause to occur]

### Allows
[Design/code decision that permits condition]

### Root Cause
[Fundamental issue to address]

### Fix
[Targeted fix for root cause]

### Prevention
[Pattern to avoid in future]
```

## Flutter-Specific Tracing Paths

### Widget Not Updating
```
Symptom: Widget shows stale data
  -> Provider notifyListeners not called?
    -> State mutation without notification?
      -> Direct object modification instead of copy?
        -> ROOT: Dart object identity vs value equality
```

### Navigation Not Working
```
Symptom: Navigation does nothing
  -> Router not receiving event?
    -> Context not in widget tree?
      -> Using wrong context after async?
        -> ROOT: Context captured before await, used after
```

### Async Error
```
Symptom: setState() called after dispose
  -> Async callback completing after widget gone?
    -> No mounted check before setState?
      -> Missing lifecycle awareness?
        -> ROOT: Async without mounted guard
```

### Test Flakiness
```
Symptom: Test passes/fails randomly
  -> Timing-dependent assertion?
    -> No wait for condition?
      -> Assumed synchronous what's async?
        -> ROOT: Missing waitFor/pump in test
```

### Supabase Sync Failure
```
Symptom: Data not syncing
  -> Sync queue processing?
    -> Network available?
      -> RLS policy blocking?
        -> ROOT: Missing or incorrect RLS policy
```

## Evidence Collection

For each step, collect:

| Evidence Type | How to Get It |
|---------------|---------------|
| Error message | Full console output |
| Stack trace | Exception details |
| State snapshot | Provider state at failure |
| Network trace | Supabase logs, HTTP inspector |
| Timeline | Git log, when last worked |
| Environment | Device, OS, Flutter version |

## Red Flags in Tracing

| Red Flag | Meaning |
|----------|---------|
| "It just started happening" | Check recent commits |
| "Works sometimes" | Race condition or timing issue |
| "Works on my machine" | Environment difference |
| "Works in debug, fails in release" | Release mode optimization issue |
| "Worked before upgrade" | Dependency breaking change |
