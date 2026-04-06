# Pattern: Data Model

## How We Do It
Models are plain Dart classes with `final` fields, a constructor with `String? id` auto-defaulting to UUID, timestamp fields auto-defaulting to `DateTime.now()`, a sentinel-based `copyWith`, `toMap()` for SQLite, and `factory fromMap()` for deserialization. Models live in `lib/features/<feature>/data/models/`. No Flutter imports. Soft-delete support via `deletedAt`/`deletedBy` nullable fields.

## Exemplars

### EntryExport (`lib/features/entries/data/models/entry_export.dart`)
```dart
class EntryExport {
  final String id;
  final String? entryId;
  final String projectId;
  final String? filePath;
  final String? remotePath;
  final String filename;
  final int? fileSizeBytes;
  final String exportedAt;
  final String createdAt;
  final String updatedAt;
  final String? createdByUserId;
  final String? deletedAt;
  final String? deletedBy;

  EntryExport({
    String? id,
    this.entryId,
    required this.projectId,
    // ...
  })  : id = id ?? const Uuid().v4(),
        exportedAt = exportedAt ?? DateTime.now().toUtc().toIso8601String(),
        createdAt = createdAt ?? DateTime.now().toUtc().toIso8601String(),
        updatedAt = updatedAt ?? DateTime.now().toUtc().toIso8601String();

  static const _sentinel = Object();

  EntryExport copyWith({ Object? id = _sentinel, ... }) { ... }
  Map<String, dynamic> toMap() => { 'id': id, 'entry_id': entryId, ... };
  factory EntryExport.fromMap(Map<String, dynamic> map) => EntryExport(...);
}
```

### BidItem (`lib/features/quantities/data/models/bid_item.dart`)
Uses `DateTime` instead of `String` for timestamps — both patterns exist. BidItem uses `DateTime.parse()` in fromMap. New models should use `String` (ISO 8601) for consistency with newer models like EntryExport/FormExport.

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `Uuid().v4()` | `package:uuid` | `String v4()` | Auto-generate primary key |
| `DateTime.now().toUtc().toIso8601String()` | dart:core | — | Default timestamp value |
| `_sentinel` pattern | any model | `static const _sentinel = Object()` | Distinguish "not provided" from null in copyWith |

## Imports
```dart
import 'package:uuid/uuid.dart';
```
