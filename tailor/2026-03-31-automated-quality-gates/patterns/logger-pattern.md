# Pattern: Categorized Logger

## How We Do It
All logging goes through the static `Logger` class which provides 11 category methods (`sync`, `pdf`, `db`, `auth`, `ocr`, `nav`, `ui`, `photo`, `lifecycle`, `bg`, `error`). Each category method writes to a category-specific log file and optionally sends via HTTP. The `error` method additionally accepts an `Object? error` and `StackTrace? stack`. Silent catch blocks (catch without logging) are a lint violation.

## Exemplars

### Logger.sync (lib/core/logging/logger.dart:135)
```dart
static void sync(String msg, {Map<String, dynamic>? data}) =>
    _log('SYNC', 'sync', msg, 'sync.log', data: data);
```

### Logger.error (lib/core/logging/logger.dart:176)
```dart
static void error(String msg, {
  Object? error,
  StackTrace? stack,
  String category = 'app',
  Map<String, dynamic>? data,
})
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| `Logger.sync` | logger.dart:135 | `static void sync(String msg, {Map<String, dynamic>? data})` | Sync operations |
| `Logger.pdf` | logger.dart:139 | `static void pdf(String msg, {Map<String, dynamic>? data})` | PDF processing |
| `Logger.db` | logger.dart:143 | `static void db(String msg, {Map<String, dynamic>? data})` | Database operations |
| `Logger.auth` | logger.dart:147 | `static void auth(String msg, {Map<String, dynamic>? data})` | Auth flows |
| `Logger.ocr` | logger.dart:151 | `static void ocr(String msg, {Map<String, dynamic>? data})` | OCR processing |
| `Logger.nav` | logger.dart:155 | `static void nav(String msg, {Map<String, dynamic>? data})` | Navigation |
| `Logger.ui` | logger.dart:159 | `static void ui(String msg, {Map<String, dynamic>? data})` | UI events |
| `Logger.photo` | logger.dart:163 | `static void photo(String msg, {Map<String, dynamic>? data})` | Photo operations |
| `Logger.lifecycle` | logger.dart:167 | `static void lifecycle(String msg, {Map<String, dynamic>? data})` | App lifecycle |
| `Logger.bg` | logger.dart:171 | `static void bg(String msg, {Map<String, dynamic>? data})` | Background tasks |
| `Logger.error` | logger.dart:176 | `static void error(String msg, {Object? error, StackTrace? stack, ...})` | Error reporting |

## Imports
```dart
import 'package:construction_inspector/core/logging/logger.dart';
```

## Lint Rules Targeting This Pattern
- A9: `no_silent_catch` — catch blocks must contain Logger call
