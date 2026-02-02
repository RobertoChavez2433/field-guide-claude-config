# Flutter TDD Patterns

Specific Red-Green-Refactor patterns for Flutter development.

## Unit Test TDD

### Model Serialization

```dart
// RED: Test serialization before implementing model
group('Project model', () {
  test('should serialize to JSON', () {
    final project = Project(
      id: '123',
      name: 'Highway 101',
      projectNumber: 'HWY-101-2026',
    );

    final json = project.toJson();

    expect(json['id'], '123');
    expect(json['name'], 'Highway 101');
    expect(json['projectNumber'], 'HWY-101-2026');
  });

  test('should deserialize from JSON', () {
    final json = {
      'id': '123',
      'name': 'Highway 101',
      'projectNumber': 'HWY-101-2026',
    };

    final project = Project.fromJson(json);

    expect(project.id, '123');
    expect(project.name, 'Highway 101');
  });
});

// GREEN: Implement model to pass tests
// REFACTOR: Add factory constructor, improve null handling
```

### Repository CRUD

```dart
// RED: Test repository before implementing
group('ProjectRepository', () {
  late ProjectRepository repository;
  late MockDatabase mockDb;

  setUp(() {
    mockDb = MockDatabase();
    repository = ProjectRepository(mockDb);
  });

  test('should save project to database', () async {
    final project = TestData.project();

    await repository.save(project);

    verify(() => mockDb.insert('projects', project.toJson())).called(1);
  });

  test('should retrieve project by id', () async {
    when(() => mockDb.query('projects', 'id = ?', ['123']))
        .thenAnswer((_) async => [TestData.projectJson()]);

    final project = await repository.getById('123');

    expect(project?.id, '123');
  });
});
```

### Service Logic

```dart
// RED: Test business logic before implementing
group('SyncService', () {
  test('should queue changes when offline', () async {
    final service = SyncService(
      networkChecker: AlwaysOffline(),
      syncQueue: mockQueue,
    );

    await service.syncEntry(entry);

    verify(() => mockQueue.add(any)).called(1);
  });

  test('should sync immediately when online', () async {
    final service = SyncService(
      networkChecker: AlwaysOnline(),
      remoteDataSource: mockRemote,
    );

    await service.syncEntry(entry);

    verify(() => mockRemote.upsert(entry)).called(1);
  });
});
```

## Widget Test TDD

### Simple Widget

```dart
// RED: Test widget behavior before building it
testWidgets('StatusBadge displays correct text and color', (tester) async {
  await tester.pumpWidget(
    MaterialApp(
      home: StatusBadge(status: EntryStatus.draft),
    ),
  );

  expect(find.text('Draft'), findsOneWidget);

  final container = tester.widget<Container>(find.byType(Container));
  final decoration = container.decoration as BoxDecoration;
  expect(decoration.color, Colors.grey);
});

// GREEN: Build minimal StatusBadge to pass
// REFACTOR: Extract colors to theme, add more status types
```

### Interactive Widget

```dart
// RED: Test interaction before implementing
testWidgets('SaveButton shows loading state while saving', (tester) async {
  final mockProvider = MockEntryProvider();
  when(() => mockProvider.isSaving).thenReturn(true);

  await tester.pumpWidget(
    ChangeNotifierProvider<EntryProvider>.value(
      value: mockProvider,
      child: MaterialApp(home: SaveButton()),
    ),
  );

  expect(find.byType(CircularProgressIndicator), findsOneWidget);
  expect(find.text('Save'), findsNothing);
});

testWidgets('SaveButton calls save when tapped', (tester) async {
  final mockProvider = MockEntryProvider();
  when(() => mockProvider.isSaving).thenReturn(false);

  await tester.pumpWidget(
    ChangeNotifierProvider<EntryProvider>.value(
      value: mockProvider,
      child: MaterialApp(home: SaveButton()),
    ),
  );

  await tester.tap(find.byType(SaveButton));

  verify(() => mockProvider.save()).called(1);
});
```

### Form Validation

```dart
// RED: Test validation before building form
testWidgets('ProjectForm validates required fields', (tester) async {
  await tester.pumpWidget(
    MaterialApp(home: Scaffold(body: ProjectForm())),
  );

  // Submit without filling fields
  await tester.tap(find.byKey(TestingKeys.submitButton));
  await tester.pump();

  expect(find.text('Project name is required'), findsOneWidget);
  expect(find.text('Project number is required'), findsOneWidget);
});

testWidgets('ProjectForm submits when valid', (tester) async {
  final mockProvider = MockProjectProvider();

  await tester.pumpWidget(
    ChangeNotifierProvider<ProjectProvider>.value(
      value: mockProvider,
      child: MaterialApp(home: Scaffold(body: ProjectForm())),
    ),
  );

  await tester.enterText(
    find.byKey(TestingKeys.projectNameField),
    'Highway 101',
  );
  await tester.enterText(
    find.byKey(TestingKeys.projectNumberField),
    'HWY-101',
  );
  await tester.tap(find.byKey(TestingKeys.submitButton));

  verify(() => mockProvider.createProject(any)).called(1);
});
```

## TestingKeys TDD Pattern

Always define TestingKeys during RED phase:

```dart
// RED: Define key and use in test FIRST
// In test file:
await tester.tap(find.byKey(TestingKeys.newProjectButton));

// This forces you to add to TestingKeys during GREEN:
// lib/shared/testing_keys.dart
class TestingKeys {
  static const newProjectButton = Key('new_project_button');
}

// And wire in widget:
ElevatedButton(
  key: TestingKeys.newProjectButton,
  onPressed: _createProject,
  child: Text('New Project'),
)
```

## Provider TDD

```dart
// RED: Test state changes before implementing provider
group('EntryProvider', () {
  test('should load entries on init', () async {
    final mockRepository = MockEntryRepository();
    when(() => mockRepository.getAll())
        .thenAnswer((_) async => [TestData.entry()]);

    final provider = EntryProvider(mockRepository);
    await provider.loadEntries();

    expect(provider.entries.length, 1);
    expect(provider.isLoading, false);
  });

  test('should notify listeners when entries change', () async {
    final provider = EntryProvider(MockEntryRepository());
    var notified = false;
    provider.addListener(() => notified = true);

    await provider.loadEntries();

    expect(notified, true);
  });
});
```

## Test Data Factory

Create test helpers during GREEN phase:

```dart
// test/helpers/test_data.dart
class TestData {
  static Project project({
    String? id,
    String? name,
  }) {
    return Project(
      id: id ?? 'test-project-id',
      name: name ?? 'Test Project',
      projectNumber: 'TEST-001',
      createdAt: DateTime(2026, 1, 1),
    );
  }

  static DailyEntry entry({
    String? id,
    String? projectId,
  }) {
    return DailyEntry(
      id: id ?? 'test-entry-id',
      projectId: projectId ?? 'test-project-id',
      date: DateTime(2026, 1, 15),
    );
  }

  static Map<String, dynamic> projectJson() {
    return {
      'id': 'test-project-id',
      'name': 'Test Project',
      'projectNumber': 'TEST-001',
    };
  }
}
```
