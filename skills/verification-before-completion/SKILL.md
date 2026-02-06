---
name: verification-before-completion
description: Evidence-based verification gate
---

# Verification Before Completion Skill

**Purpose**: Evidence-based claims that prevent false confidence.

## Iron Law

> **NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE**

Never say "it works" without showing it works. Never say "tests pass" without running them.

## The 5-Step Gate

Before claiming ANY completion, follow this process:

```
┌─────────────────────────────────────────────────────────┐
│                  VERIFICATION GATE                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   1. IDENTIFY  →  What verification is needed?          │
│         ↓                                               │
│   2. RUN       →  Execute the verification command      │
│         ↓                                               │
│   3. READ      →  Examine the FULL output               │
│         ↓                                               │
│   4. VERIFY    →  Does output match claim?              │
│         ↓                                               │
│   5. CLAIM     →  State result WITH evidence            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Step 1: IDENTIFY

What verification command matches your claim?

| Claim Type | Verification Command |
|------------|---------------------|
| Tests pass | `flutter test` |
| Build succeeds | `flutter build apk --release` |
| Analyzer clean | `flutter analyze` |
| E2E passes | `patrol test -t [path]` |
| Bug fixed | Run reproduction steps |
| Feature works | Run feature flow manually |

### Step 2: RUN

Execute the verification command **fresh**.

```bash
# CRITICAL: Use PowerShell for Flutter on Windows
pwsh -Command "flutter test"
pwsh -Command "flutter analyze"
pwsh -Command "flutter build apk --release"
```

Do NOT rely on:
- Previous runs ("it passed last time")
- Partial runs ("I ran part of it")
- Memory ("I think it passed")

### Step 3: READ

Examine the FULL output, not just exit code.

Look for:
- Test counts: "All X tests passed"
- Error messages: Even if exit code is 0
- Warnings: May indicate problems
- Partial results: Some tests may be skipped

### Step 4: VERIFY

Compare output to your intended claim:

| Intended Claim | Required Evidence |
|----------------|-------------------|
| "Tests pass" | "All X tests passed" in output |
| "Build succeeds" | Exit code 0 + APK path shown |
| "Analyzer clean" | "No issues found" |
| "Bug fixed" | Expected behavior observed |

### Step 5: CLAIM

State your result WITH the evidence:

**Good claims**:
- "Tests pass: `flutter test` shows 247 tests passed, 0 failed"
- "Build succeeds: APK generated at build/app/outputs/flutter-apk/"
- "Analyzer clean: `flutter analyze` reports no issues found"

**Bad claims**:
- "Tests should pass" (no evidence)
- "I think it works" (no verification)
- "It built successfully" (no output shown)

## Reference Documents

@.claude/skills/verification-before-completion/references/flutter-verification-commands.md
@.claude/skills/verification-before-completion/references/claim-evidence-examples.md

## Failure Patterns

| Pattern | Problem | What to Do |
|---------|---------|------------|
| "Tests pass" without running | False confidence | Run tests NOW |
| "Should work" | Modal language = no verification | Run verification |
| "Build succeeds" without output | May have succeeded with warnings | Check full output |
| "Fixed the bug" without repro | Bug may still exist | Reproduce to verify |
| "Analyzer is clean" from memory | May have new issues | Run analyzer fresh |

## Red Flags Requiring STOP

If you catch yourself:
- Using "should", "probably", "might" → STOP, run verification
- Claiming success before running commands → STOP, run commands
- Feeling satisfied before seeing evidence → STOP, get evidence
- Skipping verification "to save time" → STOP, verification is fast

## Rationalization Prevention

| Rationalization | Reality | Response |
|-----------------|---------|----------|
| "I just ran tests" | Results may have changed | Run again |
| "It's the same code" | Build env may differ | Verify anyway |
| "I'm confident" | Confidence ≠ correctness | Verify anyway |
| "This is simple" | Simple things break too | Verify anyway |
| "I'll test later" | Later never comes | Test now |

## Evidence Template

When completing work, use this format:

```markdown
## Verification Results

### Tests
```bash
$ pwsh -Command "flutter test"
00:15 +247: All tests passed!
```

### Analyzer
```bash
$ pwsh -Command "flutter analyze"
Analyzing construction_inspector...
No issues found!
```

### Build (if applicable)
```bash
$ pwsh -Command "flutter build apk --release"
✓ Built build/app/outputs/flutter-apk/app-release.apk
```
```

## Verification Timing

**When to verify**:
- After completing a task
- Before claiming completion
- Before committing code
- Before creating PR
- After any code change

**How often**:
- Every time. No exceptions.
- Fresh run each time. No caching.
