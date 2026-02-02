# Test-Driven Development Skill

**Purpose**: Red-Green-Refactor methodology for all test types.

## Iron Law

> **NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST**

Writing tests after code leads to tests that confirm code works as written, not as intended. Write the test first, watch it fail, then make it pass.

## The Red-Green-Refactor Cycle

```
    ┌──────────────┐
    │     RED      │ Write failing test
    └──────┬───────┘
           ↓
    ┌──────────────┐
    │    GREEN     │ Write minimal code to pass
    └──────┬───────┘
           ↓
    ┌──────────────┐
    │   REFACTOR   │ Clean up while tests pass
    └──────┬───────┘
           ↓
        (repeat)
```

## Phase Details

### RED Phase: Write Failing Test

**Goal**: Create a test that fails for the RIGHT reason.

1. **Write the test first** - Before any production code
2. **Test should fail** - Not compile or throw expected error
3. **Verify failure reason** - Must fail because feature missing, not typo

**Verification Checklist**:
- [ ] Test written before production code
- [ ] Test fails when run
- [ ] Failure message indicates missing feature, not error

**Example (Unit Test)**:
```dart
test('Project.fromJson creates valid project', () {
  final json = {'id': '123', 'name': 'Test Project'};

  final project = Project.fromJson(json);  // Doesn't exist yet!

  expect(project.id, '123');
  expect(project.name, 'Test Project');
});
```

### GREEN Phase: Make It Pass

**Goal**: Write the SIMPLEST code that makes the test pass.

1. **Minimal implementation** - Just enough to pass
2. **No extra features** - YAGNI (You Aren't Gonna Need It)
3. **Hardcode if needed** - Can refactor later

**Rules**:
- Only write code required by a failing test
- Don't add "obvious" features not tested
- Don't optimize prematurely

**Example**:
```dart
class Project {
  final String id;
  final String name;

  Project({required this.id, required this.name});

  factory Project.fromJson(Map<String, dynamic> json) {
    return Project(
      id: json['id'] as String,
      name: json['name'] as String,
    );
  }
}
```

### REFACTOR Phase: Clean Up

**Goal**: Improve code quality while tests stay green.

1. **Run tests continuously** - Refactoring must not break tests
2. **Extract patterns** - Remove duplication
3. **Improve naming** - Clear, intention-revealing names
4. **Simplify** - Remove unnecessary complexity

**Rules**:
- Tests must pass after every small change
- One refactoring at a time
- If tests break, revert and try smaller step

## Flutter-Specific TDD Patterns

@.claude/skills/test-driven-development/references/flutter-tdd-patterns.md

## Testing Anti-Patterns

@.claude/skills/test-driven-development/references/testing-anti-patterns.md

## Patrol E2E TDD

@.claude/skills/test-driven-development/references/patrol-tdd.md

## TDD by Test Type

### Unit Test TDD (Models, Services)

```
1. Write test for serialization → Run (RED)
2. Implement fromJson/toJson → Run (GREEN)
3. Clean up, add factory constructors → Run (REFACTOR)
```

### Widget Test TDD (UI Components)

```
1. Write test for widget behavior → Run (RED)
2. Implement widget to pass → Run (GREEN)
3. Extract reusable widgets → Run (REFACTOR)
```

### E2E Test TDD (User Flows)

```
1. Write test for user journey → Run (RED)
2. Implement screens/navigation → Run (GREEN)
3. Optimize, add error handling → Run (REFACTOR)
```

## TestingKeys First

When doing TDD for UI:

1. **In RED phase**: Define TestingKey in test
   ```dart
   await $(TestingKeys.saveButton).tap();  // Key doesn't exist yet
   ```

2. **In GREEN phase**: Add key to TestingKeys class and wire to widget
   ```dart
   // lib/shared/testing_keys.dart
   static const saveButton = Key('save_button');

   // In widget
   ElevatedButton(key: TestingKeys.saveButton, ...)
   ```

## Rationalization Prevention

| If You Think... | Stop And... |
|-----------------|-------------|
| "I'll write tests after" | Tests after confirm bugs, not correctness |
| "This is too simple to test" | Simple bugs cause complex problems |
| "I'll just add this one feature" | Features without tests are technical debt |
| "Testing slows me down" | Debugging untested code is slower |
| "I know it works" | Prove it with a test |

## Quick Commands

```bash
# Run all tests
flutter test

# Run specific test file
flutter test test/data/models/project_test.dart

# Run with coverage
flutter test --coverage

# Watch mode (rerun on change)
flutter test --watch

# Patrol tests
patrol test -t integration_test/patrol/e2e_tests/entry_flow_test.dart
```

## Definition of Done

A feature is done when:
- [ ] All tests written first (RED)
- [ ] All tests pass (GREEN)
- [ ] Code is clean (REFACTOR)
- [ ] No skipped tests
- [ ] Coverage maintained or improved
