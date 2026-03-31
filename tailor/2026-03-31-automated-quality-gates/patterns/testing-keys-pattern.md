# Pattern: Testing Keys Facade

## How We Do It
All widget Keys in runtime code use the `TestingKeys` facade class. TestingKeys delegates to 15 feature-specific sub-key files. Runtime code MUST use `TestingKeys.*` — never `Key('...')` directly. Test code MUST also use `TestingKeys.*` — never hardcoded strings. This ensures key refactoring propagates everywhere.

## Exemplars

### TestingKeys (lib/shared/testing_keys/testing_keys.dart:64)
90 static methods, each returning `Key`. Some are simple (`static const Key settingsScreen = Key('settings_screen')`) and some are parameterized (`static Key entryCard(String entryId) => Key('entry_card_$entryId')`).

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `TestingKeys.entryCard` | testing_keys.dart:579 | `static Key entryCard(String entryId)` | Entry card widget |
| `TestingKeys.projectCard` | testing_keys.dart:169 | `static Key projectCard(String projectId)` | Project card widget |
| `TestingKeys.formCard` | testing_keys.dart:188 | `static Key formCard(String formId)` | Form card widget |
| `TestingKeys.todoCard` | testing_keys.dart:347 | `static Key todoCard(String todoId)` | Todo card widget |
| `TestingKeys.photoThumbnail` | testing_keys.dart:823 | `static Key photoThumbnail(String photoId)` | Photo thumbnail widget |

## Imports
```dart
import 'package:construction_inspector/shared/testing_keys/testing_keys.dart';
```

## Lint Rules Targeting This Pattern
- T1: `no_hardcoded_key_in_widgets` — use TestingKeys, not Key('...') in runtime
- T2: `no_hardcoded_key_in_tests` — use TestingKeys in test code
- T7: `no_direct_testing_keys_bypass` — only TestingKeys.* facade in runtime
