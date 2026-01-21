# Seed Data Service Timestamp Patch Instructions

## Objective
Update `lib/core/database/seed_data_service.dart` to use varied timestamps for test data, preventing sorting issues in tests.

## Changes Required

### 1. Add Helper Function (After line 5)
Add this method to the `SeedDataService` class:

```dart
  /// Generate a varied timestamp for test data to ensure proper sorting.
  ///
  /// Offsets the current time by the specified number of minutes.
  /// This prevents all seeded records from having identical timestamps,
  /// which would make tests that rely on timestamp-based sorting fail.
  static String _variedTime(int minutesOffset) {
    return DateTime.now()
        .subtract(Duration(minutes: minutesOffset))
        .toIso8601String();
  }
```

### 2. Update Daily Entries Timestamps (Around line 456-457)
In the `daily_entries` insert section:

**From:**
```dart
        'created_at': now,
        'updated_at': now,
```

**To:**
```dart
        'created_at': _variedTime(i * 10),
        'updated_at': _variedTime(i * 10),
```

### 3. Update Entry Personnel Timestamps (Around line 473-482)
#### 3a. Add counter initialization (after line 462)
After `final contractorNames = _parseContractors(entry['contractors'] ?? '');`, add:
```dart
      int personnelIndexCounter = 0;
```

#### 3b. Replace "final now" declaration (line 473)
**From:**
```dart
          final now = DateTime.now().toIso8601String();
```

**To:**
```dart
          final personnelIndex = personnelIndexCounter++;
```

#### 3c. Update timestamps in entry_personnel insert (lines 481-482)
**From:**
```dart
            'created_at': now,
            'updated_at': now,
```

**To:**
```dart
            'created_at': _variedTime(i * 10 + personnelIndex),
            'updated_at': _variedTime(i * 10 + personnelIndex),
```

### 4. Update Entry Quantities Timestamps (Around line 503, 522-523)
#### 4a. Remove "final now" declaration (line 503)
**Delete this line:**
```dart
    final now = DateTime.now().toIso8601String();
```

#### 4b. Update all entry_quantities inserts (multiple occurrences starting ~line 522)
**From:**
```dart
            'created_at': now,
            'updated_at': now,
```

**To:**
```dart
            'created_at': _variedTime(entryIndex * 5 + qtyIndex),
            'updated_at': _variedTime(entryIndex * 5 + qtyIndex),
```

This change applies to ALL entry_quantities inserts throughout the `_seedEntryQuantities` function (approximately 20+ occurrences).

## Timestamp Offset Strategy
- **Daily Entries**: 10-minute offset per entry (i * 10)
- **Entry Personnel**: Entry offset + personnel index (i * 10 + personnelIndex)
- **Entry Quantities**: Entry offset + quantity index (entryIndex * 5 + qtyIndex)

This ensures unique timestamps while maintaining chronological ordering.

## Verification
After changes, run:
```bash
flutter analyze lib/core/database/seed_data_service.dart
flutter test
```

## Backup
Original file backed up to:
`lib/core/database/seed_data_service.dart.backup`
