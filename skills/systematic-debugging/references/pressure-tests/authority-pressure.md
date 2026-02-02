# Pressure Test: Authority Pressure

**Scenario**: Senior Developer Says "Just Add a Retry"

## The Situation

You're debugging a sync issue where Supabase uploads occasionally fail with a timeout. You've identified that the issue happens when uploading large photo batches - the connection times out after 30 seconds.

You're in a code review, and a senior developer looks at your investigation and says:

> "You're overthinking this. Just wrap it in a retry with exponential backoff. That's the standard pattern for network issues. We don't have time for a deep dive."

They're not wrong that retry is a common pattern. But something feels off.

## The Pressure

- Senior developer has more experience
- They're confident and you're uncertain
- "Standard pattern" sounds authoritative
- Disagreeing feels risky
- You're already behind schedule

## The Wrong Response

**"You're right, I'll add the retry pattern."**

This might be wrong because:
- 30 second timeout on photo upload isn't normal
- Retry will just fail 3 times instead of 1
- The root cause is still unknown
- Photos might be too large (compression issue)
- Network config might be wrong
- Adding retry adds complexity without fixing anything

## The Right Response

### Step 1: Separate Authority from Correctness

Seniority doesn't make someone right about technical facts. Respect their experience while maintaining your analysis.

### Step 2: Share Your Evidence

Don't just disagree - show what you found:

> "I looked at the failing uploads and they're all photos over 5MB. The 30 second timeout is our client timeout, not a network issue. If we retry, we'll just hit the same timeout 3 times. I think we need to either increase the timeout for large files or compress before upload."

### Step 3: Propose an Experiment

> "Can we try one thing first? Let me add logging to confirm file sizes on failures. If it's always large files, we know it's not network flakiness and retry won't help. Takes 5 minutes."

### Step 4: Accept Being Wrong Gracefully

If the evidence shows the senior was right:

> "You were right - the logging shows it's random failures across all file sizes. Retry pattern it is."

No ego, just follow the evidence.

### Step 5: Stand Firm with Evidence

If your evidence holds:

> "The logs show 100% of failures are files over 5MB. Retry won't fix this - we need to address the file size. I'd recommend adding compression before upload."

## The Dialogue Pattern

| Authority Says | You Respond With |
|----------------|------------------|
| "Just do X, it's standard" | "Let me verify X addresses the root cause" |
| "You're overthinking" | "Here's the evidence I found: [specific data]" |
| "We don't have time" | "5 minutes to verify will save retry debugging later" |
| "Trust me, I've seen this" | "Your experience is valuable - can you help me understand why X fits here?" |

## Key Insights

| Pressure Says | Reality Is |
|---------------|------------|
| "Senior knows best" | Authority ≠ correctness on specific bugs |
| "Standard pattern" | Standard doesn't mean appropriate here |
| "No time for deep dive" | Wrong fix takes more time than right fix |
| "Don't argue with experience" | Evidence-based disagreement is professional |

## The Principle

**Evidence trumps authority.** Seniority doesn't change technical facts. Present evidence respectfully, propose experiments, and follow what the data shows - whether it confirms your hypothesis or theirs.

## How to Disagree Professionally

1. **Lead with evidence**: "The logs show..."
2. **Acknowledge their point**: "Retry is standard for network issues, but..."
3. **Propose experiment**: "Can we try X to verify?"
4. **Stay outcome-focused**: "I want to fix this right the first time"
5. **Accept being wrong**: "The evidence shows you were right, let's do X"

## Red Flags in Authority Advice

| Red Flag | What It Suggests |
|----------|------------------|
| "Just do X" without looking at evidence | Premature solution |
| "Trust me" without explanation | May not apply to this case |
| "We always do X" | Habit, not analysis |
| Dismissing your findings | Not engaging with evidence |
| "Don't overthink" | May be undertinking the problem |
