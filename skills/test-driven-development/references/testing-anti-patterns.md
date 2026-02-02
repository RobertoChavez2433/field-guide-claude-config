# Testing Anti-Patterns

Common TDD violations and how to avoid them.

## Anti-Pattern: Write Code First

**What it looks like**:
```dart
// "I'll just get it working, then add tests"
class ProjectRepository {
  Future<Project?> getById(String id) async {
    final result = await db.query('projects', 'id = ?', [id]);
    return result.isEmpty ? null : Project.fromJson(result.first);
  }
}

// Tests added after (if at all)
test('getById works', () { ... });
```

**Why it's wrong**:
- Test is written to pass, not to verify behavior
- Edge cases are missed
- Implementation shapes test, not other way around

**Correct approach**:
```dart
// 1. Write test first (RED)
test('should return null when project not found', () async {
  when(() => mockDb.query(any, any, any)).thenAnswer((_) async => []);

  final result = await repository.getById('nonexistent');

  expect(result, isNull);
});

// 2. Make it pass (GREEN)
// 3. Refactor
```

## Anti-Pattern: Testing Implementation

**What it looks like**:
```dart
test('uses regex to validate email', () {
  final validator = EmailValidator();
  expect(validator.regex.pattern, contains('@'));
});
```

**Why it's wrong**:
- Tests internal details, not behavior
- Breaks when implementation changes
- Doesn't verify what matters to users

**Correct approach**:
```dart
test('should accept valid email addresses', () {
  expect(validator.isValid('user@example.com'), true);
  expect(validator.isValid('a.b@c.co'), true);
});

test('should reject invalid email addresses', () {
  expect(validator.isValid('not-an-email'), false);
  expect(validator.isValid('@missing-local'), false);
});
```

## Anti-Pattern: Giant Test Setup

**What it looks like**:
```dart
test('should save entry', () async {
  // 50 lines of setup
  final db = Database();
  await db.init();
  final projectRepo = ProjectRepository(db);
  final project = await projectRepo.create(Project(...));
  final locationRepo = LocationRepository(db);
  final location = await locationRepo.create(Location(...));
  final entryRepo = EntryRepository(db);
  // ... more setup

  // 2 lines of actual test
  await entryRepo.save(entry);
  expect(await entryRepo.getById(entry.id), isNotNull);
});
```

**Why it's wrong**:
- Hard to understand what's being tested
- Slow to run
- Brittle - breaks when unrelated things change

**Correct approach**:
```dart
// Use mocks to isolate
test('should save entry', () async {
  final mockDb = MockDatabase();
  final repo = EntryRepository(mockDb);
  final entry = TestData.entry();

  await repo.save(entry);

  verify(() => mockDb.insert('daily_entries', entry.toJson())).called(1);
});
```

## Anti-Pattern: Hardcoded Delays

**What it looks like**:
```dart
testWidgets('shows loading then data', (tester) async {
  await tester.pumpWidget(MyWidget());

  expect(find.byType(CircularProgressIndicator), findsOneWidget);

  await Future.delayed(Duration(seconds: 2)); // BAD

  expect(find.text('Data loaded'), findsOneWidget);
});
```

**Why it's wrong**:
- Slow (every test adds 2 seconds)
- Flaky (2 seconds might not be enough)
- Doesn't test actual behavior

**Correct approach**:
```dart
testWidgets('shows loading then data', (tester) async {
  await tester.pumpWidget(MyWidget());

  expect(find.byType(CircularProgressIndicator), findsOneWidget);

  await tester.pumpAndSettle(); // Wait for animations/futures

  expect(find.text('Data loaded'), findsOneWidget);
});
```

## Anti-Pattern: God Test

**What it looks like**:
```dart
test('entry workflow', () async {
  // Create project
  // Create location
  // Create entry
  // Add contractors
  // Add equipment
  // Add quantities
  // Add photos
  // Save entry
  // Verify sync queue
  // Verify PDF generation
  // 200 lines later...
});
```

**Why it's wrong**:
- When it fails, you don't know what broke
- Hard to maintain
- Tests multiple concerns

**Correct approach**:
```dart
group('Entry workflow', () {
  test('should create entry with project and location', () { ... });
  test('should add contractors to entry', () { ... });
  test('should add equipment to entry', () { ... });
  test('should queue for sync after save', () { ... });
  // Each test is focused and independent
});
```

## Anti-Pattern: Test Commenting

**What it looks like**:
```dart
test('should validate email', () {
  // Arrange
  final validator = EmailValidator();

  // Act
  final result = validator.isValid('test@example.com');

  // Assert
  expect(result, true);
});
```

**Why it's problematic**:
- Comments add noise
- If your test needs comments, it's too complex
- The code should be self-documenting

**Correct approach**:
```dart
test('should validate email', () {
  final validator = EmailValidator();

  final isValid = validator.isValid('test@example.com');

  expect(isValid, true);
});
```

## Anti-Pattern: Ignoring Failures

**What it looks like**:
```dart
test('might work', () {
  try {
    riskyOperation();
    expect(result, expectedValue);
  } catch (e) {
    // Sometimes fails, that's okay
  }
});
```

**Why it's wrong**:
- Test always passes
- Hides real failures
- False confidence

**Correct approach**:
```dart
test('should handle expected error gracefully', () {
  expect(() => riskyOperation(), throwsA(isA<ExpectedException>()));
});

test('should succeed under normal conditions', () {
  setupNormalConditions();
  expect(riskyOperation(), expectedValue);
});
```

## Anti-Pattern: No Assertions

**What it looks like**:
```dart
test('can create entry', () async {
  final provider = EntryProvider(mockRepo);
  await provider.createEntry(TestData.entry());
  // ... nothing here
});
```

**Why it's wrong**:
- Test always passes
- Verifies nothing
- False confidence

**Correct approach**:
```dart
test('should add entry to list after creation', () async {
  final provider = EntryProvider(mockRepo);

  await provider.createEntry(TestData.entry());

  expect(provider.entries.length, 1);
  verify(() => mockRepo.save(any)).called(1);
});
```

## Quick Reference: Red Flags

- Test added after code was written
- Test inspects private/internal state
- Test uses hardcoded delays
- Test is > 30 lines
- Test has try/catch that swallows failures
- Test has no assertions
- Test name describes implementation, not behavior
