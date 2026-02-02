# Claim-Evidence Examples

Good vs bad patterns for completion claims.

## Good Claims (With Evidence)

### Tests Pass

**Good**:
```markdown
Tests pass:

$ pwsh -Command "flutter test"
00:18 +247: All tests passed!
```

### Analyzer Clean

**Good**:
```markdown
Analyzer is clean:

$ pwsh -Command "flutter analyze"
Analyzing construction_inspector...
No issues found!
```

### Build Succeeds

**Good**:
```markdown
Build succeeds:

$ pwsh -Command "flutter build apk --release"
Running Gradle task 'assembleRelease'...
✓ Built build/app/outputs/flutter-apk/app-release.apk (28.5 MB)
```

### Bug Fixed

**Good**:
```markdown
Bug fixed. Verified by:

1. Reproducing original issue:
   - Navigate to Entry screen
   - Tap Save without project selected
   - Previously: App crashed with NullPointerException
   - Now: Shows "Project required" validation error

2. Running new test:
   $ pwsh -Command "flutter test test/presentation/screens/entry_screen_test.dart"
   +5: All tests passed!
```

### Feature Complete

**Good**:
```markdown
Feature complete. Verified:

1. Manual testing:
   - Created new entry with all fields
   - Saved successfully
   - Entry appears in list
   - PDF generates correctly

2. Automated tests:
   $ pwsh -Command "flutter test"
   +252: All tests passed! (was 247, added 5 new tests)

3. Analyzer:
   $ pwsh -Command "flutter analyze"
   No issues found!
```

## Bad Claims (Without Evidence)

### Tests Pass - BAD

```markdown
❌ "Tests pass."
   (No command shown, no output)

❌ "Tests should pass."
   (Modal language, no verification)

❌ "I ran the tests earlier and they passed."
   (Not fresh, things may have changed)

❌ "Tests pass: +247"
   (Shows number but not full verification)
```

### Bug Fixed - BAD

```markdown
❌ "Fixed the bug."
   (No reproduction verification)

❌ "The bug should be fixed now."
   (Modal language)

❌ "I think that fixes it."
   (No verification at all)

❌ "Fixed. The code looks correct now."
   (Code appearance ≠ behavior)
```

### Build Succeeds - BAD

```markdown
❌ "Build succeeds."
   (No output shown)

❌ "It should build."
   (No actual build run)

❌ "Build works, I ran it yesterday."
   (Not fresh)
```

## Transformation Examples

### From Bad to Good

**Bad**:
> "I fixed the async issue. Tests should pass."

**Good**:
> "Fixed the async issue by adding mounted check after await.
>
> Verification:
> ```
> $ pwsh -Command "flutter test test/presentation/screens/entry_screen_test.dart"
> +12: All tests passed!
>
> $ pwsh -Command "flutter analyze"
> No issues found!
> ```
> "

---

**Bad**:
> "Added the new ProjectCard widget. It works."

**Good**:
> "Added ProjectCard widget.
>
> Verified with:
> - Widget test: `flutter test test/presentation/widgets/project_card_test.dart` → +5 passed
> - Manual test: Widget renders correctly in project list
> - Analyzer: No issues
> "

---

**Bad**:
> "The E2E test passes now."

**Good**:
> "E2E test passes:
> ```
> $ pwsh -Command "patrol test -t integration_test/patrol/e2e_tests/navigation_flow_test.dart"
> ✓ navigation flow test (12.3s)
> 1 test passed.
> ```
> "

## Evidence Quality Checklist

Before making a claim, verify:

- [ ] **Ran command**: Actually executed, not remembered
- [ ] **Fresh run**: Just now, not from earlier
- [ ] **Full output**: Shows actual result, not summarized
- [ ] **Matches claim**: Output supports what you're claiming
- [ ] **No warnings hidden**: Checked for issues beyond pass/fail

## Red Flag Language

These phrases indicate missing verification:

| Phrase | Problem |
|--------|---------|
| "should work" | No verification |
| "I think" | Uncertainty, no evidence |
| "looks good" | Visual inspection ≠ execution |
| "I believe" | Belief ≠ verification |
| "probably" | Probability ≠ certainty |
| "I assume" | Assumption ≠ verification |
| "it works" (without output) | Claim without evidence |

## When Evidence is Insufficient

Sometimes verification reveals problems:

**Example**:
```
$ pwsh -Command "flutter test"
00:15 +245 -2: Some tests failed.
```

**Correct response**:
> "Ran tests but 2 failures remain:
> - test/data/repositories/entry_repository_test.dart: 'should cascade delete'
> - test/presentation/providers/entry_provider_test.dart: 'should update list'
>
> Need to investigate these before claiming complete."

Do NOT:
- Ignore failures
- Cherry-pick passing tests
- Claim "mostly works"
