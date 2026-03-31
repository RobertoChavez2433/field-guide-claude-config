# Pre-Release Hardening Implementation Plan

> **For Claude:** Use the implement skill (`/implement`) to execute this plan.

**Goal:** Add pre-release hardening infrastructure (consent, crash reporting, analytics, signing, about screen overhaul)
**Spec:** `.claude/specs/2026-03-29-pre-release-hardening-spec.md`
**Analysis:** `.claude/dependency_graphs/2026-03-29-pre-release-hardening/`

---

## Phase 1: Dependencies & Configuration
### Sub-phase 1.1: Add packages to pubspec.yaml
**Files:**
- Modify: `pubspec.yaml` (deps at line 30, dev_deps at line 107)
**Agent:** general-purpose

#### Step 1.1.1: Add sentry_flutter for crash reporting
In `pubspec.yaml`, after the `# Utilities` section (line 98-105), add a new comment group before `dev_dependencies`:

```yaml
  # Crash Reporting & Analytics
  sentry_flutter: ^8.13.0
```

**WHY:** Sentry provides crash reporting, performance monitoring, and breadcrumb trails. sentry_flutter is the official Flutter SDK that hooks into Flutter's error handling.

#### Step 1.1.2: Run pub get to validate dependency resolution
```
pwsh -Command "flutter pub get"
```

**NOTE:** If version conflicts arise, check `sentry_flutter` constraints against existing `firebase_core` and `http` versions. Sentry 8.x is compatible with Flutter 3.10+.

### Sub-phase 1.2: Update .env configuration
**Files:**
- Modify: `.env.example`
**Agent:** general-purpose

#### Step 1.2.1: Add Sentry DSN placeholder to .env.example
Append after line 11 (the SUPABASE_ANON_KEY line):

```
# Sentry crash reporting DSN
# Example: https://examplePublicKey@o0.ingest.sentry.io/0
SENTRY_DSN=your-sentry-dsn-here
```

**WHY:** Sentry DSN is the project-specific endpoint for crash reports. Injected via `--dart-define-from-file=.env` (same mechanism as Supabase credentials). Keeping it in .env prevents hardcoding secrets.

**NOTE:** The actual `.env` file is gitignored. Users copy `.env.example` and fill in real values.

### Sub-phase 1.3: Android release signing configuration
**Files:**
- Modify: `android/app/build.gradle.kts` (lines 55-64)
- Create: `android/key.properties.example`
**Agent:** general-purpose

#### Step 1.3.1: Add key.properties loading to build.gradle.kts
In `android/app/build.gradle.kts`, add the key.properties loading block **before** the `android {` block (before line 9). Insert between line 7 (`}` closing plugins) and line 9 (`android {`):

```kotlin
// WHY: Load release signing config from key.properties (gitignored).
// Falls back to debug signing if key.properties is absent (dev machines).
val keystorePropertiesFile = rootProject.file("key.properties")
val keystoreProperties = java.util.Properties()
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(keystorePropertiesFile.inputStream())
}
```

**NOTE:** Kotlin DSL format — NOT Groovy. The `rootProject.file()` resolves relative to `android/` directory.

#### Step 1.3.2: Add signingConfigs block inside android {}
In `android/app/build.gradle.kts`, add a `signingConfigs` block **before** the `buildTypes` block (before line 55). Insert after the `testOptions` closing brace (after line 53):

```kotlin
    signingConfigs {
        create("release") {
            // WHY: Only configure release signing if key.properties exists.
            // This prevents build failures on dev machines without a keystore.
            if (keystorePropertiesFile.exists()) {
                keyAlias = keystoreProperties["keyAlias"] as String
                keyPassword = keystoreProperties["keyPassword"] as String
                storeFile = file(keystoreProperties["storeFile"] as String)
                storePassword = keystoreProperties["storePassword"] as String
            }
        }
    }
```

#### Step 1.3.3: Update release buildType to use release signing config
Replace lines 55-64 in `android/app/build.gradle.kts`:

**Old (lines 55-64):**
```kotlin
    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
```

**New:**
```kotlin
    buildTypes {
        release {
            // WHY: Use release signing when key.properties exists, debug otherwise.
            // This allows release builds on CI while keeping dev builds working.
            signingConfig = if (keystorePropertiesFile.exists()) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
```

#### Step 1.3.4: Create key.properties.example template
Create `android/key.properties.example`:

```properties
# Android release signing configuration
# Copy this file to key.properties (which is gitignored) and fill in values.
#
# To generate a keystore:
#   keytool -genkey -v -keystore field-guide-release.keystore \
#     -alias field-guide -keyalg RSA -keysize 2048 -validity 10000
#
storePassword=your-keystore-password
keyPassword=your-key-password
keyAlias=field-guide
storeFile=../field-guide-release.keystore
```

**NOTE:** `.gitignore` already excludes `*.keystore`, `*.jks`, and `key.properties`. The `storeFile` path is relative to `android/app/`.

### Sub-phase 1.4: iOS project directory generation
**Files:**
- Create: `ios/` directory (generated by Flutter)
**Agent:** general-purpose

#### Step 1.4.1: Generate iOS project scaffold
```
pwsh -Command "flutter create --platforms=ios ."
```

**WHY:** The app currently has no `ios/` directory. This generates the minimal Xcode project structure needed for iOS builds. No signing config is needed at this stage — that will be configured when an Apple Developer account is available.

**NOTE:** This command is safe to run in an existing project — it only adds the `ios/` directory without modifying existing files. If it warns about existing files, that's expected and can be ignored.

#### Step 1.4.2: Verify the generated structure
```
pwsh -Command "Test-Path ios/Runner.xcodeproj"
```

**NOTE:** Should return `True`. The generated project will use the `com.fieldguideapp.inspector` bundle ID from the existing Android config.

### Sub-phase 1.5: Verification
**Agent:** general-purpose

#### Step 1.5.1: Verify dependency resolution and analyze
```
pwsh -Command "flutter pub get"
pwsh -Command "flutter analyze --no-fatal-infos"
```

**WHY:** Ensures all new dependencies resolve without conflicts and existing code still passes analysis.

---

## Phase 2: Database Schema
### Sub-phase 2.1: Create consent_tables.dart schema file
**Files:**
- Create: `lib/core/database/schema/consent_tables.dart`
**Agent:** backend-data-layer-agent

#### Step 2.1.1: Create the ConsentTables schema class
Create `lib/core/database/schema/consent_tables.dart`:

```dart
// WHY: Stores user consent records for privacy policy and terms of service.
// FROM SPEC: Append-only table — users can accept new versions but never
// delete or modify existing consent records. This is a legal/audit requirement.
class ConsentTables {
  static const String tableName = 'user_consent_records';

  static const String createUserConsentRecordsTable = '''
    CREATE TABLE IF NOT EXISTS user_consent_records (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      policy_type TEXT NOT NULL,
      policy_version TEXT NOT NULL,
      accepted_at TEXT NOT NULL,
      app_version TEXT NOT NULL
    )
  ''';

  // NOTE: Index on user_id for quick lookup of a user's consent history.
  // Index on policy_type + policy_version for checking if a specific version was accepted.
  static const List<String> indexes = [
    'CREATE INDEX IF NOT EXISTS idx_user_consent_records_user ON user_consent_records(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_user_consent_records_policy ON user_consent_records(policy_type, policy_version)',
  ];
}
```

**WHY:** `policy_type` is constrained to `'privacy_policy'` or `'terms_of_service'` at the model/datasource layer (not SQL CHECK — SQLite CHECK constraints are harder to migrate). `user_id` references auth.users on the Supabase side but is a plain TEXT locally since the FK target doesn't exist in local SQLite.

### Sub-phase 2.2: Create support_tables.dart schema file
**Files:**
- Create: `lib/core/database/schema/support_tables.dart`
**Agent:** backend-data-layer-agent

#### Step 2.2.1: Create the SupportTables schema class
Create `lib/core/database/schema/support_tables.dart`:

```dart
// WHY: Stores support tickets submitted from within the app.
// FROM SPEC: Users can create and view their own tickets. Status is managed
// server-side (admin updates). Client only does INSERT + SELECT.
class SupportTables {
  static const String tableName = 'support_tickets';

  static const String createSupportTicketsTable = '''
    CREATE TABLE IF NOT EXISTS support_tickets (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      subject TEXT,
      message TEXT NOT NULL,
      app_version TEXT NOT NULL,
      platform TEXT NOT NULL,
      log_file_path TEXT,
      created_at TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'open'
    )
  ''';

  // NOTE: Index on user_id for listing a user's tickets.
  // Index on status for filtering open/closed tickets.
  static const List<String> indexes = [
    'CREATE INDEX IF NOT EXISTS idx_support_tickets_user ON support_tickets(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status)',
  ];
}
```

### Sub-phase 2.3: Update schema barrel export
**Files:**
- Modify: `lib/core/database/schema/schema.dart` (line 19, end of file)
**Agent:** backend-data-layer-agent

#### Step 2.3.1: Add consent and support table exports
Append after line 19 (`export 'form_export_tables.dart';`):

```dart
export 'consent_tables.dart';
export 'support_tables.dart';
```

### Sub-phase 2.4: Update DatabaseService — version bump and _onCreate
**Files:**
- Modify: `lib/core/database/database_service.dart` (line 53 for version, lines 104-183 for _onCreate)
**Agent:** backend-data-layer-agent

#### Step 2.4.1: Bump database version from 43 to 44
At line 53, change:

```dart
      version: 43,
```

to:

```dart
      version: 44,
```

#### Step 2.4.2: Add consent and support table creation to _onCreate
In `_onCreate`, after the document/export tables block (after line 152, `await db.execute(FormExportTables.createFormExportsTable);`), add:

```dart
    // Consent + support tables (v44)
    await db.execute(ConsentTables.createUserConsentRecordsTable);
    await db.execute(SupportTables.createSupportTicketsTable);
```

#### Step 2.4.3: Add consent and support indexes to _createIndexes
In `_createIndexes`, after the existing index loops (find the last `for (final index in ...Tables.indexes)` block and add after it):

```dart
    // Consent indexes
    for (final index in ConsentTables.indexes) {
      await db.execute(index);
    }

    // Support indexes
    for (final index in SupportTables.indexes) {
      await db.execute(index);
    }
```

**NOTE:** Need to verify the exact location of the last index loop in `_createIndexes`. It should be near the end of the method, after `FormExportTables.indexes`.

### Sub-phase 2.5: Update DatabaseService — _onUpgrade for v44
**Files:**
- Modify: `lib/core/database/database_service.dart` (after line 1861, end of _onUpgrade)
**Agent:** backend-data-layer-agent

#### Step 2.5.1: Add v44 migration block
After line 1861 (the closing `}` of the v43 migration block, before the closing `}` of `_onUpgrade` at line 1862), add:

```dart
    // WHY: v44 adds consent records and support tickets for pre-release hardening.
    // These are new tables — no data migration needed, just CREATE + indexes.
    if (oldVersion < 44) {
      await db.execute(ConsentTables.createUserConsentRecordsTable);
      await db.execute(SupportTables.createSupportTicketsTable);

      for (final index in ConsentTables.indexes) {
        await db.execute(index);
      }
      for (final index in SupportTables.indexes) {
        await db.execute(index);
      }

      Logger.db('v44 migration: added user_consent_records, support_tickets tables');
    }
```

### Sub-phase 2.6: Supabase migration SQL
**Files:**
- Create: `supabase/migrations/20260329000000_consent_and_support_tables.sql`
**Agent:** backend-supabase-agent

#### Step 2.6.1: Create the Supabase migration file
Create `supabase/migrations/20260329000000_consent_and_support_tables.sql`:

```sql
-- WHY: Pre-release hardening — consent records + support tickets.
-- FROM SPEC: Both tables are append-only from the client perspective.
-- RLS: Users can only INSERT and SELECT their own records.

-- =============================================================
-- 1. user_consent_records
-- =============================================================
CREATE TABLE IF NOT EXISTS public.user_consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    policy_type TEXT NOT NULL CHECK (policy_type IN ('privacy_policy', 'terms_of_service')),
    policy_version TEXT NOT NULL,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    app_version TEXT NOT NULL
);

-- NOTE: Index on user_id for RLS filter pushdown.
CREATE INDEX IF NOT EXISTS idx_user_consent_records_user
    ON public.user_consent_records(user_id);
CREATE INDEX IF NOT EXISTS idx_user_consent_records_policy
    ON public.user_consent_records(policy_type, policy_version);

-- RLS: Users can only insert and read their own consent records.
-- No UPDATE or DELETE — consent is immutable once recorded.
ALTER TABLE public.user_consent_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can insert own consent"
    ON public.user_consent_records FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read own consent"
    ON public.user_consent_records FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- =============================================================
-- 2. support_tickets
-- =============================================================
CREATE TABLE IF NOT EXISTS public.support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    subject TEXT,
    message TEXT NOT NULL,
    app_version TEXT NOT NULL,
    platform TEXT NOT NULL,
    log_file_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'resolved'))
);

CREATE INDEX IF NOT EXISTS idx_support_tickets_user
    ON public.support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status
    ON public.support_tickets(status);

-- RLS: Users can insert and read their own tickets.
-- No UPDATE or DELETE from client — status managed by admin/backend.
ALTER TABLE public.support_tickets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can insert own tickets"
    ON public.support_tickets FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read own tickets"
    ON public.support_tickets FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- =============================================================
-- 3. support-logs storage bucket
-- =============================================================
-- WHY: Users attach log files to support tickets. Bucket is private —
-- only the uploader and service_role can read.
INSERT INTO storage.buckets (id, name, public)
VALUES ('support-logs', 'support-logs', false)
ON CONFLICT (id) DO NOTHING;

-- RLS: Authenticated users can upload to their own folder.
CREATE POLICY "Users can upload own support logs"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id = 'support-logs'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );

-- RLS: Users can only read their own uploaded logs.
CREATE POLICY "Users can read own support logs"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (
        bucket_id = 'support-logs'
        AND (storage.foldername(name))[1] = auth.uid()::text
    );
```

**NOTE:** Supabase uses UUID and TIMESTAMPTZ types (Postgres), unlike local SQLite which uses TEXT for everything. The CHECK constraints on `policy_type` and `status` provide server-side validation. The storage bucket uses folder-based RLS where each user's files are in a `{user_id}/` prefix.

### Sub-phase 2.7: Verification
**Agent:** qa-testing-agent

#### Step 2.7.1: Run static analysis
```
pwsh -Command "flutter analyze --no-fatal-infos"
```

#### Step 2.7.2: Run existing database tests to verify no regressions
```
pwsh -Command "flutter test test/core/database/ --no-pub"
```

**NOTE:** If no database-specific tests exist yet, verify with a broader test run:
```
pwsh -Command "flutter test --no-pub"
```

---

## Phase 3: Consent Data Layer
### Sub-phase 3.1: ConsentRecord model
**Files:**
- Create: `lib/features/settings/data/models/consent_record.dart`
- Modify: `lib/features/settings/data/models/models.dart` (barrel export, if it exists)
**Agent:** backend-data-layer-agent

#### Step 3.1.1: Create ConsentRecord model
Create `lib/features/settings/data/models/consent_record.dart`:

```dart
import 'package:uuid/uuid.dart';

// WHY: Consent records track user acceptance of privacy policy and ToS.
// FROM SPEC: Append-only — once created, never updated or deleted.
// This model is used both for local SQLite and Supabase sync.

/// Valid policy types for consent records.
enum ConsentPolicyType {
  privacyPolicy,
  termsOfService;

  /// Convert to database string format.
  String toDbString() {
    switch (this) {
      case ConsentPolicyType.privacyPolicy:
        return 'privacy_policy';
      case ConsentPolicyType.termsOfService:
        return 'terms_of_service';
    }
  }

  /// Parse from database string format.
  static ConsentPolicyType fromDbString(String value) {
    switch (value) {
      case 'privacy_policy':
        return ConsentPolicyType.privacyPolicy;
      case 'terms_of_service':
        return ConsentPolicyType.termsOfService;
      default:
        throw ArgumentError('Unknown policy type: $value');
    }
  }
}

class ConsentRecord {
  final String id;
  final String userId;
  final ConsentPolicyType policyType;
  final String policyVersion;
  final DateTime acceptedAt;
  final String appVersion;

  /// Table name constant for datasource usage.
  static const String tableName = 'user_consent_records';

  ConsentRecord({
    String? id,
    required this.userId,
    required this.policyType,
    required this.policyVersion,
    DateTime? acceptedAt,
    required this.appVersion,
  })  : id = id ?? const Uuid().v4(),
        acceptedAt = acceptedAt ?? DateTime.now().toUtc();

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'user_id': userId,
      'policy_type': policyType.toDbString(),
      'policy_version': policyVersion,
      'accepted_at': acceptedAt.toUtc().toIso8601String(),
      'app_version': appVersion,
    };
  }

  factory ConsentRecord.fromMap(Map<String, dynamic> map) {
    return ConsentRecord(
      id: map['id'] as String,
      userId: map['user_id'] as String,
      policyType: ConsentPolicyType.fromDbString(map['policy_type'] as String),
      policyVersion: map['policy_version'] as String,
      acceptedAt: DateTime.parse(map['accepted_at'] as String),
      appVersion: map['app_version'] as String,
    );
  }

  // NOTE: No copyWith() — consent records are immutable once created.
  // FROM SPEC: Append-only table, no UPDATE allowed.
}
```

**WHY:** The enum uses explicit `toDbString()`/`fromDbString()` instead of `.name`/`.byName()` because the DB values use snake_case (`privacy_policy`) while the Dart enum uses camelCase (`privacyPolicy`).

#### Step 3.1.2: Create or update barrel export
Check if `lib/features/settings/data/models/models.dart` exists. If so, add:

```dart
export 'consent_record.dart';
```

If it does not exist, create `lib/features/settings/data/models/models.dart`:

```dart
export 'consent_record.dart';
```

### Sub-phase 3.2: ConsentLocalDatasource
**Files:**
- Create: `lib/features/settings/data/datasources/consent_local_datasource.dart`
**Agent:** backend-data-layer-agent

#### Step 3.2.1: Create ConsentLocalDatasource
Create `lib/features/settings/data/datasources/consent_local_datasource.dart`:

```dart
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import '../models/consent_record.dart';

// WHY: Datasource for consent records. Does NOT extend GenericLocalDatasource
// because consent records are append-only (no update, no delete, no soft-delete filter).
// FROM SPEC: Only INSERT and SELECT operations allowed.

class ConsentLocalDatasource {
  final DatabaseService _dbService;

  ConsentLocalDatasource(this._dbService);

  /// Insert a new consent record.
  /// NOTE: No upsert — each acceptance creates a new row (append-only).
  Future<void> insert(ConsentRecord record) async {
    final db = await _dbService.database;
    await db.insert(ConsentRecord.tableName, record.toMap());
    Logger.db('INSERT ${ConsentRecord.tableName} id=${record.id} '
        'type=${record.policyType.toDbString()} v=${record.policyVersion}');
  }

  /// Get all consent records for a user, ordered by acceptance time (newest first).
  Future<List<ConsentRecord>> getByUserId(String userId) async {
    final db = await _dbService.database;
    final results = await db.query(
      ConsentRecord.tableName,
      where: 'user_id = ?',
      whereArgs: [userId],
      orderBy: 'accepted_at DESC',
    );
    return results.map((row) => ConsentRecord.fromMap(row)).toList();
  }

  /// Check if a user has accepted a specific policy version.
  /// Returns true if at least one record exists for this policy type + version.
  Future<bool> hasAccepted({
    required String userId,
    required ConsentPolicyType policyType,
    required String policyVersion,
  }) async {
    final db = await _dbService.database;
    final results = await db.query(
      ConsentRecord.tableName,
      where: 'user_id = ? AND policy_type = ? AND policy_version = ?',
      whereArgs: [userId, policyType.toDbString(), policyVersion],
      limit: 1,
    );
    return results.isNotEmpty;
  }

  /// Get the latest consent record for a specific policy type.
  /// Returns null if the user has never accepted this policy.
  Future<ConsentRecord?> getLatest({
    required String userId,
    required ConsentPolicyType policyType,
  }) async {
    final db = await _dbService.database;
    final results = await db.query(
      ConsentRecord.tableName,
      where: 'user_id = ? AND policy_type = ?',
      whereArgs: [userId, policyType.toDbString()],
      orderBy: 'accepted_at DESC',
      limit: 1,
    );
    if (results.isEmpty) return null;
    return ConsentRecord.fromMap(results.first);
  }
}
```

### Sub-phase 3.3: ConsentRepository
**Files:**
- Create: `lib/features/settings/data/repositories/consent_repository.dart`
**Agent:** backend-data-layer-agent

#### Step 3.3.1: Create ConsentRepository
Create `lib/features/settings/data/repositories/consent_repository.dart`:

```dart
import '../datasources/consent_local_datasource.dart';
import '../models/consent_record.dart';

// WHY: Thin wrapper around ConsentLocalDatasource.
// Does NOT implement BaseRepository because consent records are
// append-only with a non-standard API (no getAll, no delete, no save).

class ConsentRepository {
  final ConsentLocalDatasource _localDatasource;

  ConsentRepository(this._localDatasource);

  /// Record user acceptance of a policy version.
  Future<void> recordConsent(ConsentRecord record) {
    return _localDatasource.insert(record);
  }

  /// Get all consent records for a user.
  Future<List<ConsentRecord>> getConsentHistory(String userId) {
    return _localDatasource.getByUserId(userId);
  }

  /// Check if a user has accepted a specific policy version.
  Future<bool> hasAcceptedPolicy({
    required String userId,
    required ConsentPolicyType policyType,
    required String policyVersion,
  }) {
    return _localDatasource.hasAccepted(
      userId: userId,
      policyType: policyType,
      policyVersion: policyVersion,
    );
  }

  /// Get the latest consent record for a policy type.
  Future<ConsentRecord?> getLatestConsent({
    required String userId,
    required ConsentPolicyType policyType,
  }) {
    return _localDatasource.getLatest(
      userId: userId,
      policyType: policyType,
    );
  }
}
```

### Sub-phase 3.4: Consent model unit tests
**Files:**
- Create: `test/features/settings/data/models/consent_record_test.dart`
**Agent:** qa-testing-agent

#### Step 3.4.1: Create ConsentRecord model tests
Create `test/features/settings/data/models/consent_record_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/settings/data/models/consent_record.dart';

void main() {
  group('ConsentRecord', () {
    test('creates with auto-generated ID and UTC timestamp', () {
      final record = ConsentRecord(
        userId: 'user-1',
        policyType: ConsentPolicyType.privacyPolicy,
        policyVersion: '1.0.0',
        appVersion: '0.1.2+3',
      );
      expect(record.id, isNotEmpty);
      expect(record.userId, 'user-1');
      expect(record.policyType, ConsentPolicyType.privacyPolicy);
      expect(record.acceptedAt.isUtc, isTrue);
    });

    test('toMap produces correct keys and values', () {
      final record = ConsentRecord(
        id: 'test-id',
        userId: 'user-1',
        policyType: ConsentPolicyType.termsOfService,
        policyVersion: '2.0.0',
        appVersion: '0.1.2+3',
      );
      final map = record.toMap();
      expect(map['id'], 'test-id');
      expect(map['user_id'], 'user-1');
      expect(map['policy_type'], 'terms_of_service');
      expect(map['policy_version'], '2.0.0');
      expect(map['app_version'], '0.1.2+3');
      expect(map.containsKey('accepted_at'), isTrue);
    });

    test('fromMap round-trips correctly', () {
      final original = ConsentRecord(
        id: 'test-id',
        userId: 'user-1',
        policyType: ConsentPolicyType.privacyPolicy,
        policyVersion: '1.0.0',
        appVersion: '0.1.2+3',
      );
      final restored = ConsentRecord.fromMap(original.toMap());
      expect(restored.id, original.id);
      expect(restored.userId, original.userId);
      expect(restored.policyType, original.policyType);
      expect(restored.policyVersion, original.policyVersion);
      expect(restored.appVersion, original.appVersion);
      // NOTE: Millisecond precision may differ after ISO8601 round-trip
      expect(
        restored.acceptedAt.difference(original.acceptedAt).inSeconds,
        0,
      );
    });

    test('fromMap handles privacy_policy type string', () {
      final map = {
        'id': 'test-id',
        'user_id': 'user-1',
        'policy_type': 'privacy_policy',
        'policy_version': '1.0.0',
        'accepted_at': '2026-03-29T12:00:00.000Z',
        'app_version': '0.1.2+3',
      };
      final record = ConsentRecord.fromMap(map);
      expect(record.policyType, ConsentPolicyType.privacyPolicy);
    });

    test('fromMap handles terms_of_service type string', () {
      final map = {
        'id': 'test-id',
        'user_id': 'user-1',
        'policy_type': 'terms_of_service',
        'policy_version': '1.0.0',
        'accepted_at': '2026-03-29T12:00:00.000Z',
        'app_version': '0.1.2+3',
      };
      final record = ConsentRecord.fromMap(map);
      expect(record.policyType, ConsentPolicyType.termsOfService);
    });

    test('fromDbString throws on unknown policy type', () {
      expect(
        () => ConsentPolicyType.fromDbString('unknown'),
        throwsArgumentError,
      );
    });
  });

  group('ConsentPolicyType', () {
    test('toDbString returns correct snake_case strings', () {
      expect(
        ConsentPolicyType.privacyPolicy.toDbString(),
        'privacy_policy',
      );
      expect(
        ConsentPolicyType.termsOfService.toDbString(),
        'terms_of_service',
      );
    });
  });
}
```

### Sub-phase 3.5: Verification
**Agent:** qa-testing-agent

#### Step 3.5.1: Run consent model tests
```
pwsh -Command "flutter test test/features/settings/data/models/consent_record_test.dart --no-pub"
```

#### Step 3.5.2: Run static analysis
```
pwsh -Command "flutter analyze --no-fatal-infos"
```

---

## Phase 4: Support Data Layer
### Sub-phase 4.1: SupportTicket model
**Files:**
- Create: `lib/features/settings/data/models/support_ticket.dart`
- Modify: `lib/features/settings/data/models/models.dart` (barrel export)
**Agent:** backend-data-layer-agent

#### Step 4.1.1: Create SupportTicket model
Create `lib/features/settings/data/models/support_ticket.dart`:

```dart
import 'package:uuid/uuid.dart';

// WHY: Support tickets let users report issues from within the app.
// FROM SPEC: Client can INSERT and SELECT. Status is read-only from client
// (updated by admin via Supabase dashboard or backend function).

/// Status values for support tickets.
/// FROM SPEC: open, acknowledged, resolved (3 states only).
enum SupportTicketStatus {
  open,
  acknowledged,
  resolved;

  /// Convert to database string format.
  String toDbString() {
    switch (this) {
      case SupportTicketStatus.open:
        return 'open';
      case SupportTicketStatus.acknowledged:
        return 'acknowledged';
      case SupportTicketStatus.resolved:
        return 'resolved';
    }
  }

  /// Parse from database string format.
  static SupportTicketStatus fromDbString(String value) {
    switch (value) {
      case 'open':
        return SupportTicketStatus.open;
      case 'acknowledged':
        return SupportTicketStatus.acknowledged;
      case 'resolved':
        return SupportTicketStatus.resolved;
      default:
        throw ArgumentError('Unknown ticket status: $value');
    }
  }
}

class SupportTicket {
  final String id;
  final String userId;
  final String? subject;
  final String message;
  final String appVersion;
  final String platform;
  final String? logFilePath;
  final DateTime createdAt;
  final SupportTicketStatus status;

  /// Table name constant for datasource usage.
  static const String tableName = 'support_tickets';

  SupportTicket({
    String? id,
    required this.userId,
    this.subject,
    required this.message,
    required this.appVersion,
    required this.platform,
    this.logFilePath,
    DateTime? createdAt,
    this.status = SupportTicketStatus.open,
  })  : id = id ?? const Uuid().v4(),
        createdAt = createdAt ?? DateTime.now().toUtc();

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'user_id': userId,
      'subject': subject,
      'message': message,
      'app_version': appVersion,
      'platform': platform,
      'log_file_path': logFilePath,
      'created_at': createdAt.toUtc().toIso8601String(),
      'status': status.toDbString(),
    };
  }

  factory SupportTicket.fromMap(Map<String, dynamic> map) {
    return SupportTicket(
      id: map['id'] as String,
      userId: map['user_id'] as String,
      subject: map['subject'] as String?,
      message: map['message'] as String,
      appVersion: map['app_version'] as String,
      platform: map['platform'] as String,
      logFilePath: map['log_file_path'] as String?,
      createdAt: DateTime.parse(map['created_at'] as String),
      status: SupportTicketStatus.fromDbString(map['status'] as String),
    );
  }

  // NOTE: No copyWith() — tickets are created by the client and status is
  // managed server-side. If we need to display updated status from sync,
  // we create a new SupportTicket from the synced map data.
}
```

#### Step 4.1.2: Update barrel export
Add to `lib/features/settings/data/models/models.dart`:

```dart
export 'support_ticket.dart';
```

### Sub-phase 4.2: SupportLocalDatasource
**Files:**
- Create: `lib/features/settings/data/datasources/support_local_datasource.dart`
**Agent:** backend-data-layer-agent

#### Step 4.2.1: Create SupportLocalDatasource
Create `lib/features/settings/data/datasources/support_local_datasource.dart`:

```dart
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import '../models/support_ticket.dart';

// WHY: Datasource for support tickets. Does NOT extend GenericLocalDatasource
// because support tickets have no soft-delete, no update from client side,
// and use a non-standard query pattern (user-scoped, status-filtered).

class SupportLocalDatasource {
  final DatabaseService _dbService;

  SupportLocalDatasource(this._dbService);

  /// Insert a new support ticket.
  Future<void> insert(SupportTicket ticket) async {
    final db = await _dbService.database;
    await db.insert(SupportTicket.tableName, ticket.toMap());
    Logger.db('INSERT ${SupportTicket.tableName} id=${ticket.id} '
        'subject=${ticket.subject ?? "(none)"}');
  }

  /// Get all tickets for a user, ordered by creation time (newest first).
  Future<List<SupportTicket>> getByUserId(String userId) async {
    final db = await _dbService.database;
    final results = await db.query(
      SupportTicket.tableName,
      where: 'user_id = ?',
      whereArgs: [userId],
      orderBy: 'created_at DESC',
    );
    return results.map((row) => SupportTicket.fromMap(row)).toList();
  }

  /// Get a single ticket by ID.
  Future<SupportTicket?> getById(String id) async {
    final db = await _dbService.database;
    final results = await db.query(
      SupportTicket.tableName,
      where: 'id = ?',
      whereArgs: [id],
      limit: 1,
    );
    if (results.isEmpty) return null;
    return SupportTicket.fromMap(results.first);
  }

  /// Get tickets filtered by status for a user.
  Future<List<SupportTicket>> getByStatus({
    required String userId,
    required SupportTicketStatus status,
  }) async {
    final db = await _dbService.database;
    final results = await db.query(
      SupportTicket.tableName,
      where: 'user_id = ? AND status = ?',
      whereArgs: [userId, status.toDbString()],
      orderBy: 'created_at DESC',
    );
    return results.map((row) => SupportTicket.fromMap(row)).toList();
  }

  /// Update ticket status (used when syncing server-side status changes).
  /// NOTE: This is only called by the sync layer, not by user actions.
  Future<void> updateStatus(String id, SupportTicketStatus status) async {
    final db = await _dbService.database;
    await db.update(
      SupportTicket.tableName,
      {'status': status.toDbString()},
      where: 'id = ?',
      whereArgs: [id],
    );
    Logger.db('UPDATE ${SupportTicket.tableName} id=$id status=${status.toDbString()}');
  }
}
```

### Sub-phase 4.3: SupportRepository
**Files:**
- Create: `lib/features/settings/data/repositories/support_repository.dart`
**Agent:** backend-data-layer-agent

#### Step 4.3.1: Create SupportRepository
Create `lib/features/settings/data/repositories/support_repository.dart`:

```dart
import '../datasources/support_local_datasource.dart';
import '../models/support_ticket.dart';

// WHY: Thin wrapper around SupportLocalDatasource.
// Does NOT implement BaseRepository — non-standard API (user-scoped, append-only).

class SupportRepository {
  final SupportLocalDatasource _localDatasource;

  SupportRepository(this._localDatasource);

  /// Submit a new support ticket.
  Future<void> submitTicket(SupportTicket ticket) {
    return _localDatasource.insert(ticket);
  }

  /// Get all tickets for the current user.
  Future<List<SupportTicket>> getTickets(String userId) {
    return _localDatasource.getByUserId(userId);
  }

  /// Get a specific ticket by ID.
  Future<SupportTicket?> getTicketById(String id) {
    return _localDatasource.getById(id);
  }

  /// Get tickets with a specific status.
  Future<List<SupportTicket>> getTicketsByStatus({
    required String userId,
    required SupportTicketStatus status,
  }) {
    return _localDatasource.getByStatus(
      userId: userId,
      status: status,
    );
  }

  /// Update ticket status from sync.
  Future<void> updateTicketStatus(String id, SupportTicketStatus status) {
    return _localDatasource.updateStatus(id, status);
  }
}
```

### Sub-phase 4.4: Support model unit tests
**Files:**
- Create: `test/features/settings/data/models/support_ticket_test.dart`
**Agent:** qa-testing-agent

#### Step 4.4.1: Create SupportTicket model tests
Create `test/features/settings/data/models/support_ticket_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:construction_inspector/features/settings/data/models/support_ticket.dart';

void main() {
  group('SupportTicket', () {
    test('creates with auto-generated ID, UTC timestamp, and open status', () {
      final ticket = SupportTicket(
        userId: 'user-1',
        subject: 'App crash',
        message: 'The app crashed when I tapped sync',
        appVersion: '0.1.2+3',
        platform: 'android',
      );
      expect(ticket.id, isNotEmpty);
      expect(ticket.userId, 'user-1');
      expect(ticket.status, SupportTicketStatus.open);
      expect(ticket.createdAt.isUtc, isTrue);
    });

    test('toMap produces correct keys and values', () {
      final ticket = SupportTicket(
        id: 'test-id',
        userId: 'user-1',
        subject: 'Bug report',
        message: 'Something is broken',
        appVersion: '0.1.2+3',
        platform: 'windows',
        logFilePath: '/path/to/log.txt',
      );
      final map = ticket.toMap();
      expect(map['id'], 'test-id');
      expect(map['user_id'], 'user-1');
      expect(map['subject'], 'Bug report');
      expect(map['message'], 'Something is broken');
      expect(map['app_version'], '0.1.2+3');
      expect(map['platform'], 'windows');
      expect(map['log_file_path'], '/path/to/log.txt');
      expect(map['status'], 'open');
      expect(map.containsKey('created_at'), isTrue);
    });

    test('toMap handles null subject and logFilePath', () {
      final ticket = SupportTicket(
        id: 'test-id',
        userId: 'user-1',
        message: 'No subject ticket',
        appVersion: '0.1.2+3',
        platform: 'android',
      );
      final map = ticket.toMap();
      expect(map['subject'], isNull);
      expect(map['log_file_path'], isNull);
    });

    test('fromMap round-trips correctly', () {
      final original = SupportTicket(
        id: 'test-id',
        userId: 'user-1',
        subject: 'Test subject',
        message: 'Test message body',
        appVersion: '0.1.2+3',
        platform: 'android',
        logFilePath: '/logs/debug.log',
        status: SupportTicketStatus.acknowledged,
      );
      final restored = SupportTicket.fromMap(original.toMap());
      expect(restored.id, original.id);
      expect(restored.userId, original.userId);
      expect(restored.subject, original.subject);
      expect(restored.message, original.message);
      expect(restored.appVersion, original.appVersion);
      expect(restored.platform, original.platform);
      expect(restored.logFilePath, original.logFilePath);
      expect(restored.status, original.status);
      expect(
        restored.createdAt.difference(original.createdAt).inSeconds,
        0,
      );
    });

    test('fromMap handles all status values', () {
      final baseMap = {
        'id': 'test-id',
        'user_id': 'user-1',
        'message': 'test',
        'app_version': '0.1.2+3',
        'platform': 'android',
        'created_at': '2026-03-29T12:00:00.000Z',
      };

      for (final entry in {
        'open': SupportTicketStatus.open,
        'acknowledged': SupportTicketStatus.acknowledged,
        'resolved': SupportTicketStatus.resolved,
      }.entries) {
        final map = {...baseMap, 'status': entry.key};
        final ticket = SupportTicket.fromMap(map);
        expect(ticket.status, entry.value,
            reason: 'Failed for status: ${entry.key}');
      }
    });

    test('fromDbString throws on unknown status', () {
      expect(
        () => SupportTicketStatus.fromDbString('unknown'),
        throwsArgumentError,
      );
    });
  });

  group('SupportTicketStatus', () {
    test('toDbString returns correct snake_case strings', () {
      expect(SupportTicketStatus.open.toDbString(), 'open');
      expect(SupportTicketStatus.acknowledged.toDbString(), 'acknowledged');
      expect(SupportTicketStatus.resolved.toDbString(), 'resolved');
    });
  });
}
```

### Sub-phase 4.5: Verification
**Agent:** qa-testing-agent

#### Step 4.5.1: Run all new model tests
```
pwsh -Command "flutter test test/features/settings/data/models/ --no-pub"
```

#### Step 4.5.2: Run full static analysis
```
pwsh -Command "flutter analyze --no-fatal-infos"
```

#### Step 4.5.3: Run full test suite to check for regressions
```
pwsh -Command "flutter test --no-pub"
```

---


## Phase 5: Sentry Integration

> **NOTE:** sentry_flutter dependency and SENTRY_DSN .env.example entry are already added in Part 1 Phase 1. Do NOT duplicate them here.

### Sub-phase 5.2: Wrap main() with SentryFlutter.init
**Files:**
- Modify: `lib/main.dart` (lines 109-124)
**Agent:** general-purpose

#### Step 5.2.1: Add sentry_flutter import
Add at the top of `lib/main.dart`, with the other imports:

```dart
import 'package:sentry_flutter/sentry_flutter.dart';
```

#### Step 5.2.2: Replace runZonedGuarded with SentryFlutter.init
Replace the current `main()` function at lines 109-124:

**Old (lines 109-124):**
```dart
Future<void> main() async {
  runZonedGuarded(
    () async {
      WidgetsFlutterBinding.ensureInitialized();
      await _runApp();
    },
    (error, stack) {
      Logger.error(
        'Uncaught zone error: $error',
        error: error,
        stack: stack,
      );
    },
    zoneSpecification: Logger.zoneSpec(),
  );
}
```

**New:**
```dart
// WHY: SentryFlutter.init replaces runZonedGuarded — it sets up its own error
// zone internally and captures uncaught errors. The appRunner callback is called
// within Sentry's zone, so all errors propagate to Sentry automatically.
// NOTE: The SENTRY_DSN is injected via --dart-define-from-file=.env at build time.
// When DSN is empty (local dev), Sentry is a no-op.
Future<void> main() async {
  await SentryFlutter.init(
    (options) {
      options.dsn = const String.fromEnvironment('SENTRY_DSN');
      options.tracesSampleRate = 0.2;
      // WHY: beforeSend scrubs PII before any data leaves the device.
      // Uses the same _scrubString and _scrubSensitive methods as Logger
      // to ensure consistent PII handling across all transports.
      options.beforeSend = _beforeSendSentry;
      // WHY: Disable screenshot capture — construction site photos may contain
      // sensitive project data (addresses, personnel, etc.)
      options.attachScreenshot = false;
    },
    appRunner: () async {
      WidgetsFlutterBinding.ensureInitialized();
      // WHY: Logger.zoneSpec() hooks debugPrint for file logging.
      // SentryFlutter.init already wraps in a zone, so we nest a child zone
      // with our print hooks rather than replacing Sentry's zone.
      await runZonedGuarded(
        () => _runApp(),
        (error, stack) {
          Logger.error(
            'Uncaught zone error: $error',
            error: error,
            stack: stack,
          );
        },
        zoneSpecification: Logger.zoneSpec(),
      );
    },
  );
}
```

> **NOTE:** We keep `runZonedGuarded` inside `appRunner` to preserve Logger's zone-based print capturing. Sentry's outer zone catches unhandled errors; Logger's inner zone captures `debugPrint` output. Both zones work cooperatively.

#### Step 5.2.2b: Create shared Sentry consent flag file
**File:** Create `lib/core/config/sentry_consent.dart`
**Agent:** general-purpose

```dart
/// WHY: Sentry consent flag must be accessible from both main.dart
/// (where _beforeSendSentry reads it) and consent_provider.dart
/// (where acceptConsent() sets it). Extracting to a shared file
/// avoids circular imports.
bool sentryConsentGranted = false;

/// Called by ConsentProvider after consent is accepted.
void enableSentryReporting() {
  sentryConsentGranted = true;
}
```

#### Step 5.2.3: Add _beforeSendSentry function to main.dart
Add this above `main()` in `lib/main.dart` (after the imports, before line 109).
Also add `import 'package:construction_inspector/core/config/sentry_consent.dart';` to main.dart imports.

```dart
/// PII scrubbing for Sentry events before they leave the device.
/// WHY: Security is non-negotiable — no user emails, JWTs, or sensitive
/// data should reach Sentry servers. Uses Logger's existing scrub methods
/// for consistency.
/// Also gates on consent — returns null (drops event) if consent not granted.
SentryEvent? _beforeSendSentry(SentryEvent event, Hint hint) {
  // WHY: Spec says "neither initializes without acceptance". We keep Sentry
  // wrapping main() for infrastructure, but drop all events until consent.
  if (!sentryConsentGranted) return null;

  // Scrub the exception message
  var exceptions = event.exceptions;
  if (exceptions != null) {
    exceptions = exceptions.map((e) {
      final scrubbed = e.value != null ? Logger.scrubString(e.value!) : null;
      return e.copyWith(value: scrubbed);
    }).toList();
  }

  // Scrub breadcrumb messages
  var breadcrumbs = event.breadcrumbs;
  if (breadcrumbs != null) {
    breadcrumbs = breadcrumbs.map((b) {
      final scrubbedMsg = b.message != null ? Logger.scrubString(b.message!) : null;
      return b.copyWith(message: scrubbedMsg);
    }).toList();
  }

  return event.copyWith(
    exceptions: exceptions,
    breadcrumbs: breadcrumbs,
  );
}
```

---

### Sub-phase 5.3: Rename `scrubStringForTest` to `scrubString` (production use case now exists)
**Files:**
- Modify: `lib/core/logging/logger.dart` (line ~701)
**Agent:** backend-data-layer-agent

#### Step 5.3.1: Rename existing scrubStringForTest to scrubString
The existing `scrubStringForTest` method is a public wrapper around `_scrubString`. Now that Sentry's `_beforeSendSentry` in `main.dart` needs it at runtime, rename it to `scrubString` and update any test references that call `scrubStringForTest` to use `scrubString` instead.

Rename in `lib/core/logging/logger.dart`:
```dart
/// Public accessor for PII scrubbing — used by Sentry beforeSend callback
/// and tests.
/// WHY: Sentry PII scrubbing must use the same rules as Logger to prevent
/// inconsistent handling (e.g., emails scrubbed in logs but leaked to Sentry).
static String scrubString(String s) => _scrubString(s);
```

**NOTE:** Search for all usages of `scrubStringForTest` in `test/` and update them to `scrubString`.

---

### Sub-phase 5.4: Add Sentry transport to Logger.error()
**Files:**
- Modify: `lib/core/logging/logger.dart` (line ~228, end of error() method)
**Agent:** backend-data-layer-agent

#### Step 5.4.1: Add Sentry capture call in Logger.error()
Insert before the closing `}` of the `error()` method (after line 227 `_sendHttp(payload);` block, before line 228 `}`):

```dart
    // Sentry transport — send errors to Sentry for crash reporting.
    // WHY: Third transport alongside file and HTTP. Only sends when Sentry
    // is initialized (DSN is non-empty). PII is already scrubbed above.
    // NOTE: We use captureException when we have an actual error object,
    // captureMessage for string-only errors. This gives Sentry proper
    // grouping and stack trace display.
    if (error != null) {
      Sentry.captureException(
        error,
        stackTrace: stack,
        withScope: (scope) {
          scope.setTag('category', category);
          if (scrubbedData != null) {
            scope.setContexts('extra', scrubbedData);
          }
        },
      );
    } else {
      Sentry.captureMessage(
        scrubbedMsg,
        level: SentryLevel.error,
        withScope: (scope) {
          scope.setTag('category', category);
        },
      );
    }
```

#### Step 5.4.2: Add Sentry import to logger.dart
Add at the top of `lib/core/logging/logger.dart`:

```dart
import 'package:sentry_flutter/sentry_flutter.dart';
```

---

### Sub-phase 5.5: Add SENTRY_DSN to .env (actual value only)
**Files:**
- Modify: `.env`
**Agent:** general-purpose

> **NOTE:** SENTRY_DSN was already added to `.env.example` in Part 1 Phase 1.2. Do NOT duplicate it here.

#### Step 5.5.1: Add SENTRY_DSN to .env
Add the actual DSN value (ask the user for the DSN, or leave empty for now):

```
SENTRY_DSN=
```

> **NOTE:** The DSN is read via `const String.fromEnvironment('SENTRY_DSN')` which is injected by the build script's `--dart-define-from-file=.env`. When empty, Sentry runs in no-op mode.

---

### Sub-phase 5.6: Verification
**Agent:** qa-testing-agent

#### Step 5.6.1: Static analysis
```
pwsh -Command "flutter analyze"
```

#### Step 5.6.2: Run existing tests
```
pwsh -Command "flutter test"
```

> **WHY:** Sentry integration is mostly runtime. Static analysis confirms no import or type errors. Existing tests confirm nothing is broken. Sentry in no-op mode (empty DSN) should not affect any behavior.

---

## Phase 6: Aptabase Integration
### Sub-phase 6.1: Add aptabase_flutter Dependency
**Files:**
- Modify: `pubspec.yaml`
**Agent:** general-purpose

#### Step 6.1.1: Add aptabase_flutter to pubspec.yaml
Add to the dependencies section:

```yaml
# WHY: Privacy-first analytics. Does not collect PII by design.
# App key is injected via --dart-define-from-file=.env.
aptabase_flutter: ^0.1.0
```

#### Step 6.1.2: Run pub get
```
pwsh -Command "flutter pub get"
```

---

### Sub-phase 6.2: Initialize Aptabase in _runApp()
**Files:**
- Modify: `lib/main.dart` (inside `_runApp()`, after PreferencesService.initialize())
**Agent:** general-purpose

#### Step 6.2.1: Add aptabase import
Add at the top of `lib/main.dart`:

```dart
import 'package:aptabase_flutter/aptabase_flutter.dart';
```

#### Step 6.2.2: Add Aptabase init after PreferencesService
Insert after `await preferencesService.initialize();` (line 134) and before `await _initDebugLogging(preferencesService);` (line 136):

```dart
  // WHY: Aptabase analytics init — only when user has accepted consent
  // and the app key is configured. Aptabase is privacy-first (no PII),
  // but we still respect user consent preferences.
  // NOTE: Must be after PreferencesService because consent state is stored there.
  final consentAccepted = preferencesService.getBool('consent_accepted') ?? false;
  final aptabaseKey = const String.fromEnvironment('APTABASE_APP_KEY');
  if (consentAccepted && aptabaseKey.isNotEmpty) {
    await Aptabase.init(aptabaseKey);
    Logger.lifecycle('Aptabase analytics initialized');
  } else {
    Logger.lifecycle('Aptabase analytics skipped (consent=${consentAccepted}, keyConfigured=${aptabaseKey.isNotEmpty})');
  }
```

---

### Sub-phase 6.3: Add trackEvent calls at key user flow points
**Files:**
- Modify: `lib/features/entries/presentation/screens/home_screen.dart`
- Modify: `lib/features/sync/application/sync_orchestrator.dart`
- Modify: `lib/features/pdf/presentation/screens/` (main PDF screen)
- Modify: `lib/features/auth/presentation/providers/auth_provider.dart`
**Agent:** backend-data-layer-agent

#### Step 6.3.1: Create analytics helper
Create `lib/core/analytics/analytics.dart`:

```dart
import 'package:aptabase_flutter/aptabase_flutter.dart';
import 'package:construction_inspector/core/logging/logger.dart';

/// Thin wrapper around Aptabase for event tracking.
///
/// WHY: Centralizes analytics calls so we can:
/// 1. Add/remove analytics providers without touching feature code
/// 2. Gate all tracking behind a single consent check
/// 3. Catch and log any analytics errors without crashing the app
///
/// NOTE: All event names use snake_case for consistency.
/// No PII is ever passed as a property — only counts, durations, and enum values.
class Analytics {
  Analytics._();

  /// Track a named event with optional properties.
  /// Silently no-ops if Aptabase is not initialized (no consent or no key).
  static void track(String eventName, [Map<String, dynamic>? props]) {
    try {
      Aptabase.instance.trackEvent(eventName, props);
    } catch (e) {
      // WHY: Analytics must never crash the app. Log and move on.
      Logger.lifecycle('Analytics track error: $e');
    }
  }

  // =========================================================================
  // Pre-defined events — use these instead of raw strings for type safety
  // =========================================================================

  /// User signed in successfully
  static void trackSignIn() => track('user_sign_in');

  /// User signed out
  static void trackSignOut() => track('user_sign_out');

  /// User created a new account
  static void trackSignUp() => track('user_sign_up');

  /// User created a new daily entry
  static void trackEntryCreated() => track('entry_created');

  /// User triggered a manual sync
  static void trackManualSync() => track('sync_manual_triggered');

  /// Sync completed successfully
  static void trackSyncCompleted({int? pushCount, int? pullCount}) =>
      track('sync_completed', {
        if (pushCount != null) 'push_count': pushCount,
        if (pullCount != null) 'pull_count': pullCount,
      });

  /// User imported a PDF
  static void trackPdfImported() => track('pdf_imported');

  /// User generated a report
  static void trackReportGenerated() => track('report_generated');

  /// User opened a form
  static void trackFormOpened({required String formType}) =>
      track('form_opened', {'form_type': formType});

  /// User submitted a form
  static void trackFormSubmitted({required String formType}) =>
      track('form_submitted', {'form_type': formType});

  /// App launched (called once per cold start)
  static void trackAppLaunch() => track('app_launch');
}
```

#### Step 6.3.2: Add trackAppLaunch to _runApp()
Insert at the end of `_runApp()` in `lib/main.dart`, just before the `runApp(ConstructionInspectorApp(...))` call:

```dart
  // WHY: Track cold app launch for usage analytics. No PII.
  Analytics.trackAppLaunch();
```

Add import:
```dart
import 'package:construction_inspector/core/analytics/analytics.dart';
```

#### Step 6.3.3: Add trackSignIn to AuthProvider
In `lib/features/auth/presentation/providers/auth_provider.dart`, after a successful sign-in (where `isAuthenticated` is set to true), add:

```dart
// WHY: Track sign-in for session analytics. No PII — just the event name.
Analytics.trackSignIn();
```

Add import:
```dart
import 'package:construction_inspector/core/analytics/analytics.dart';
```

> **NOTE:** Exact insertion point depends on the sign-in method. Look for where `_isAuthenticated = true` or `notifyListeners()` is called after successful auth. Insert the `Analytics.trackSignIn()` call immediately after.

#### Step 6.3.4: Add trackSignOut to AuthProvider
In the sign-out method of `AuthProvider`, add before the state reset:

```dart
Analytics.trackSignOut();
```

#### Step 6.3.5: Add trackManualSync to sync trigger
In `lib/features/sync/application/sync_orchestrator.dart`, at the start of the manual sync method (the one called by the UI sync button), add:

```dart
Analytics.trackManualSync();
```

Add import:
```dart
import 'package:construction_inspector/core/analytics/analytics.dart';
```

---

### Sub-phase 6.4: Add APTABASE_APP_KEY to .env template
**Files:**
- Modify: `.env.example`
- Modify: `.env`
**Agent:** general-purpose

#### Step 6.4.1: Add APTABASE_APP_KEY to .env.example
```
# Aptabase privacy-first analytics key (leave empty to disable)
APTABASE_APP_KEY=
```

#### Step 6.4.2: Add APTABASE_APP_KEY to .env
```
APTABASE_APP_KEY=
```

---

### Sub-phase 6.5: Verification
**Agent:** qa-testing-agent

#### Step 6.5.1: Static analysis
```
pwsh -Command "flutter analyze"
```

#### Step 6.5.2: Run existing tests
```
pwsh -Command "flutter test"
```

---

## Phase 7: Consent UI & Provider
### Sub-phase 7.1: ConsentProvider
**Files:**
- Create: `lib/features/settings/presentation/providers/consent_provider.dart`
**Agent:** backend-data-layer-agent

#### Step 7.1.1: Create ConsentProvider
```dart
import 'package:flutter/foundation.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/shared/services/preferences_service.dart';
import 'package:construction_inspector/features/settings/data/repositories/consent_repository.dart';
import 'package:construction_inspector/features/settings/data/models/consent_record.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/core/config/sentry_consent.dart';

/// Manages user consent state for analytics and crash reporting.
///
/// WHY: GDPR/privacy compliance requires explicit user consent before
/// collecting any telemetry data. This provider tracks:
/// 1. Whether the user has accepted the current policy version
/// 2. Which policy version was accepted (for re-consent on policy updates)
///
/// NOTE: Consent state is stored in SharedPreferences for quick sync checks
/// AND in ConsentRepository (SQLite) for audit trail / legal compliance.
class ConsentProvider extends ChangeNotifier {
  final PreferencesService _prefs;
  final ConsentRepository _consentRepository;
  final AuthProvider _authProvider;

  /// Current policy version. Bump this when ToS/Privacy Policy changes
  /// to force re-consent.
  /// WHY: Hardcoded initially. Can be fetched from app_config table later
  /// when remote policy versioning is needed.
  static const String currentPolicyVersion = '1.0.0';

  // Preference keys
  static const String _keyConsentAccepted = 'consent_accepted';
  static const String _keyConsentPolicyVersion = 'consent_policy_version';
  static const String _keyConsentTimestamp = 'consent_timestamp';

  bool _hasConsented = false;
  String? _consentedPolicyVersion;

  ConsentProvider({
    required PreferencesService preferencesService,
    required ConsentRepository consentRepository,
    required AuthProvider authProvider,
  })  : _prefs = preferencesService,
        _consentRepository = consentRepository,
        _authProvider = authProvider;

  // ---------------------------------------------------------------------------
  // Getters
  // ---------------------------------------------------------------------------

  /// Whether the user has accepted the CURRENT policy version.
  /// WHY: Returns false if they accepted an older version — forces re-consent
  /// when the policy is updated (bump currentPolicyVersion).
  bool get hasConsented =>
      _hasConsented && _consentedPolicyVersion == currentPolicyVersion;

  /// Whether the user has ever consented (any version).
  bool get hasEverConsented => _hasConsented;

  /// The policy version the user consented to (null if never consented).
  String? get consentedPolicyVersion => _consentedPolicyVersion;

  /// Whether the user needs to re-consent due to a policy update.
  bool get needsReconsent =>
      _hasConsented && _consentedPolicyVersion != currentPolicyVersion;

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  /// Load consent state from SharedPreferences. Call once at startup.
  void loadConsentState() {
    _hasConsented = _prefs.getBool(_keyConsentAccepted) ?? false;
    _consentedPolicyVersion = _prefs.getString(_keyConsentPolicyVersion);

    Logger.lifecycle(
      'Consent state loaded: accepted=$_hasConsented, '
      'version=$_consentedPolicyVersion, '
      'current=$currentPolicyVersion, '
      'valid=$hasConsented',
    );
  }

  /// Record user acceptance of the current policy version.
  /// WHY: Stores the exact version and timestamp for audit trail.
  /// Writes to BOTH SharedPreferences (quick checks) AND ConsentRepository
  /// (SQLite audit records). Two ConsentRecord rows are inserted: one for
  /// privacy_policy and one for terms_of_service.
  Future<void> acceptConsent({String? appVersion}) async {
    await _prefs.setBool(_keyConsentAccepted, true);
    await _prefs.setString(_keyConsentPolicyVersion, currentPolicyVersion);
    await _prefs.setString(
      _keyConsentTimestamp,
      DateTime.now().toUtc().toIso8601String(),
    );

    // WHY: Insert audit records into SQLite via ConsentRepository.
    // Two rows: one for privacy_policy, one for terms_of_service.
    // This is the legal audit trail — prefs alone are not sufficient.
    final userId = _authProvider.userId;
    if (userId == null) {
      Logger.error('Cannot record consent: no authenticated user');
      return;
    }
    final resolvedAppVersion = appVersion ?? 'unknown';

    await _consentRepository.recordConsent(ConsentRecord(
      userId: userId,
      policyType: ConsentPolicyType.privacyPolicy,
      policyVersion: currentPolicyVersion,
      appVersion: resolvedAppVersion,
    ));
    await _consentRepository.recordConsent(ConsentRecord(
      userId: userId,
      policyType: ConsentPolicyType.termsOfService,
      policyVersion: currentPolicyVersion,
      appVersion: resolvedAppVersion,
    ));

    // Enable Sentry reporting now that consent is granted
    enableSentryReporting();

    _hasConsented = true;
    _consentedPolicyVersion = currentPolicyVersion;

    Logger.lifecycle('User accepted consent for policy v$currentPolicyVersion');
    notifyListeners();
  }

  /// Revoke consent (e.g., from settings screen).
  /// WHY: Users must be able to withdraw consent at any time (GDPR right).
  Future<void> revokeConsent() async {
    await _prefs.setBool(_keyConsentAccepted, false);
    // NOTE: Keep the policy version and timestamp for audit — only flip the bool.

    _hasConsented = false;

    Logger.lifecycle('User revoked consent');
    notifyListeners();
  }

  /// Clear all consent state on sign-out.
  /// WHY: Consent is per-user. When a different user signs in on the same
  /// device, they must give their own consent.
  Future<void> clearOnSignOut() async {
    await _prefs.setBool(_keyConsentAccepted, false);
    // NOTE: We could also remove the keys entirely, but setting to false
    // is safer — avoids null-check edge cases on next load.
    _hasConsented = false;
    _consentedPolicyVersion = null;
    notifyListeners();
  }
}
```

---

### Sub-phase 7.2: ConsentScreen
**Files:**
- Create: `lib/features/settings/presentation/screens/consent_screen.dart`
- Create: `lib/shared/testing_keys/consent_keys.dart`
**Agent:** frontend-flutter-specialist-agent

#### Step 7.2.1: Create testing keys for consent screen
Create `lib/shared/testing_keys/consent_keys.dart`:

```dart
import 'package:flutter/material.dart';

/// Testing keys for the consent / Terms of Service screen.
///
/// WHY: E2E tests need stable keys to interact with the consent flow.
class ConsentTestingKeys {
  ConsentTestingKeys._();

  /// The scrollable body containing the ToS/Privacy Policy text
  static const consentScrollView = Key('consent_scroll_view');

  /// The "I Accept" button (enabled only after scrolling to bottom)
  static const consentAcceptButton = Key('consent_accept_button');

  /// The full consent screen scaffold
  static const consentScreen = Key('consent_screen');

  /// Checkbox on the registration screen for ToS agreement
  static const registerTosCheckbox = Key('register_tos_checkbox');
}
```

#### Step 7.2.2: Create ConsentScreen
Create `lib/features/settings/presentation/screens/consent_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:construction_inspector/core/theme/app_theme.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/settings/presentation/providers/consent_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/shared/testing_keys/consent_keys.dart';

/// Full-screen blocking consent screen.
///
/// WHY: Users must explicitly accept Terms of Service and Privacy Policy
/// before using the app. This screen:
/// 1. Blocks navigation until accepted (enforced by router redirect)
/// 2. Requires scrolling to the bottom before the Accept button enables
/// 3. Records acceptance with policy version for audit trail
///
/// NOTE: This screen is shown:
/// - On first launch (new users)
/// - After policy version bump (existing users, re-consent)
class ConsentScreen extends StatefulWidget {
  const ConsentScreen({super.key});

  @override
  State<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends State<ConsentScreen> {
  final _scrollController = ScrollController();
  bool _hasScrolledToBottom = false;
  bool _isAccepting = false;
  String? _tosText;
  String? _privacyText;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    _loadPolicyTexts();
  }

  /// WHY: Load policy text from bundled markdown assets (single source of truth).
  /// Same assets used by LegalDocumentScreen in Phase 11.
  Future<void> _loadPolicyTexts() async {
    try {
      final tos = await rootBundle.loadString('assets/legal/terms_of_service.md');
      final privacy = await rootBundle.loadString('assets/legal/privacy_policy.md');
      if (!mounted) return;
      setState(() {
        _tosText = tos;
        _privacyText = privacy;
      });
    } catch (e) {
      Logger.error('Failed to load policy text from assets', error: e);
    }
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_hasScrolledToBottom) return;
    // WHY: Check if user has scrolled to within 50px of the bottom.
    // Small threshold accounts for different screen sizes / font scaling.
    final maxScroll = _scrollController.position.maxScrollExtent;
    final currentScroll = _scrollController.position.pixels;
    if (currentScroll >= maxScroll - 50) {
      setState(() => _hasScrolledToBottom = true);
    }
  }

  Future<void> _handleAccept() async {
    setState(() => _isAccepting = true);

    try {
      final appVersion = context.read<AppConfigProvider>().appVersion;
      await context.read<ConsentProvider>().acceptConsent(appVersion: appVersion);
      if (!mounted) return;
      // WHY: After consent, go to root — the router redirect will handle
      // routing to the correct screen (onboarding, dashboard, etc.)
      context.go('/');
    } catch (e) {
      Logger.error('Failed to save consent', error: e);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Failed to save. Please try again.')),
      );
    } finally {
      if (mounted) setState(() => _isAccepting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final consentProvider = context.watch<ConsentProvider>();

    return Scaffold(
      key: ConsentTestingKeys.consentScreen,
      appBar: AppBar(
        title: Text(
          consentProvider.needsReconsent
              ? 'Updated Terms of Service'
              : 'Terms of Service',
        ),
        automaticallyImplyLeading: false, // WHY: No back button — blocking screen
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppTheme.space4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header text
              Text(
                consentProvider.needsReconsent
                    ? 'Our Terms of Service and Privacy Policy have been updated. '
                      'Please review and accept to continue.'
                    : 'Please review our Terms of Service and Privacy Policy '
                      'to continue.',
                style: theme.textTheme.bodyLarge,
              ),
              const SizedBox(height: AppTheme.space4),

              // Scrollable policy summary + links to full documents
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    border: Border.all(color: theme.dividerColor),
                    borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
                  ),
                  child: SingleChildScrollView(
                    key: ConsentTestingKeys.consentScrollView,
                    controller: _scrollController,
                    padding: const EdgeInsets.all(AppTheme.space4),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Summary text
                        Text(
                          'By accepting, you agree to our Terms of Service and Privacy Policy. '
                          'Key points:',
                          style: theme.textTheme.bodyLarge,
                        ),
                        const SizedBox(height: AppTheme.space3),
                        Text(
                          '• Your inspection data remains your property\n'
                          '• Data is stored locally and synced to cloud when connected\n'
                          '• With your consent, anonymous crash reports and usage analytics help improve the app\n'
                          '• You can revoke consent at any time in Settings\n'
                          '• No personally identifiable information is sent to analytics',
                          style: theme.textTheme.bodyMedium,
                        ),
                        const SizedBox(height: AppTheme.space4),

                        // Full Terms of Service text (loaded from bundled asset)
                        Text(
                          'Terms of Service',
                          style: theme.textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: AppTheme.space3),
                        Text(
                          _tosText ?? 'Loading...',
                          style: theme.textTheme.bodyMedium,
                        ),
                        // Tappable link to full document viewer
                        GestureDetector(
                          onTap: () => context.pushNamed(
                            'legal-document',
                            queryParameters: {'type': 'tos'},
                          ),
                          child: Text(
                            'View full Terms of Service',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: theme.colorScheme.primary,
                              decoration: TextDecoration.underline,
                            ),
                          ),
                        ),
                        const SizedBox(height: AppTheme.space6),

                        // Full Privacy Policy text (loaded from bundled asset)
                        Text(
                          'Privacy Policy',
                          style: theme.textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: AppTheme.space3),
                        Text(
                          _privacyText ?? 'Loading...',
                          style: theme.textTheme.bodyMedium,
                        ),
                        // Tappable link to full document viewer
                        GestureDetector(
                          onTap: () => context.pushNamed(
                            'legal-document',
                            queryParameters: {'type': 'privacy'},
                          ),
                          child: Text(
                            'View full Privacy Policy',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: theme.colorScheme.primary,
                              decoration: TextDecoration.underline,
                            ),
                          ),
                        ),
                        const SizedBox(height: AppTheme.space4),
                        Text(
                          'Policy version: ${ConsentProvider.currentPolicyVersion}',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.textTheme.bodySmall?.color?.withAlpha(153),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: AppTheme.space3),

              // Scroll hint (hidden once scrolled to bottom)
              if (!_hasScrolledToBottom)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppTheme.space2),
                  child: Text(
                    'Scroll to the bottom to enable the Accept button',
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontStyle: FontStyle.italic,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),

              // Accept button
              ElevatedButton(
                key: ConsentTestingKeys.consentAcceptButton,
                // WHY: Disabled until user scrolls to bottom — ensures they
                // have at least seen the full text.
                onPressed: _hasScrolledToBottom && !_isAccepting
                    ? _handleAccept
                    : null,
                child: _isAccepting
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('I Accept'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// NOTE: Policy text is no longer hardcoded here.
// It is loaded from bundled markdown assets (assets/legal/terms_of_service.md
// and assets/legal/privacy_policy.md) via rootBundle.loadString() in initState.
// This maintains a single source of truth — the same assets are rendered
// by LegalDocumentScreen (Phase 11).
```

---

### Sub-phase 7.3: Add ConsentProvider to main.dart initialization
**Files:**
- Modify: `lib/main.dart` (inside `_runApp()`, before `runApp()`)
- Modify: `lib/main.dart` (`ConstructionInspectorApp` constructor and MultiProvider)
**Agent:** general-purpose

#### Step 7.3.1: Create ConsentProvider in _runApp()
Insert after `final preferencesService = PreferencesService();` and `await preferencesService.initialize();` (line 133-134), and after the Aptabase init block added in Phase 6:

```dart
  // WHY: ConsentProvider must be created after repositories are built because
  // it needs ConsentRepository (for audit trail) and AuthProvider (for userId).
  // 1. Aptabase init (above) checks consent via PreferencesService directly
  // 2. The router needs ConsentProvider for the consent gate redirect
  // 3. The ConsentScreen needs it to display state and record acceptance
  final consentProvider = ConsentProvider(
    preferencesService: preferencesService,
    consentRepository: consentRepository,  // built earlier in _runApp with other repositories
    authProvider: authProvider,             // built earlier in _runApp
  );
  consentProvider.loadConsentState();

  // WHY: Set the Sentry consent gate flag so _beforeSendSentry allows events.
  // Until this point, all Sentry events are dropped (see sentryConsentGranted).
  // NOTE: Uses enableSentryReporting() from lib/core/config/sentry_consent.dart
  if (consentProvider.hasConsented) {
    enableSentryReporting();
  }
```

**NOTE:** `consentRepository` must be created earlier in `_runApp()` alongside the other repositories (after DatabaseService is initialized). Add:
```dart
  final consentLocalDatasource = ConsentLocalDatasource(dbService);
  final consentRepository = ConsentRepository(consentLocalDatasource);
```

#### Step 7.3.2: Add ConsentProvider to ConstructionInspectorApp constructor
In the `ConstructionInspectorApp` class (line 733+), add `consentProvider` as a constructor parameter:

```dart
final ConsentProvider consentProvider;
```

And in the constructor parameter list, add:

```dart
required this.consentProvider,
```

#### Step 7.3.3: Add ConsentProvider to MultiProvider
In the `ConstructionInspectorApp.build()` method, inside the `MultiProvider.providers` list, add:

```dart
ChangeNotifierProvider.value(value: consentProvider),
```

#### Step 7.3.4: Pass consentProvider in runApp() call
In the `runApp(ConstructionInspectorApp(...))` call inside `_runApp()`, add:

```dart
consentProvider: consentProvider,
```

#### Step 7.3.5: Add imports for ConsentProvider and dependencies in main.dart
```dart
import 'package:construction_inspector/features/settings/presentation/providers/consent_provider.dart';
import 'package:construction_inspector/features/settings/data/datasources/consent_local_datasource.dart';
import 'package:construction_inspector/features/settings/data/repositories/consent_repository.dart';
```

---

### Sub-phase 7.4: Add ToS checkbox to registration screen
**Files:**
- Modify: `lib/features/auth/presentation/screens/register_screen.dart` (line 186-189)
**Agent:** frontend-flutter-specialist-agent

#### Step 7.4.1: Add state variable for ToS checkbox
Add to the `_RegisterScreenState` class fields:

```dart
bool _tosAccepted = false;
```

#### Step 7.4.2: Insert ToS checkbox between spacer and Create Account button
Insert between `const SizedBox(height: AppTheme.space6),` (line 186) and `// Create Account Button` (line 188):

```dart
                // WHY: Users must agree to ToS before creating an account.
                // This does NOT replace the full ConsentScreen — it's a
                // quick acknowledgment during registration. The full consent
                // screen handles detailed policy review + scroll-to-accept.
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Checkbox(
                      key: ConsentTestingKeys.registerTosCheckbox,
                      value: _tosAccepted,
                      onChanged: (value) {
                        setState(() => _tosAccepted = value ?? false);
                      },
                    ),
                    Expanded(
                      child: GestureDetector(
                        onTap: () => setState(() => _tosAccepted = !_tosAccepted),
                        child: Padding(
                          padding: const EdgeInsets.only(top: 12),
                          child: Text.rich(
                            TextSpan(
                              text: 'I agree to the ',
                              children: [
                                TextSpan(
                                  text: 'Terms of Service',
                                  style: TextStyle(
                                    color: Theme.of(context).colorScheme.primary,
                                    decoration: TextDecoration.underline,
                                  ),
                                ),
                                const TextSpan(text: ' and '),
                                TextSpan(
                                  text: 'Privacy Policy',
                                  style: TextStyle(
                                    color: Theme.of(context).colorScheme.primary,
                                    decoration: TextDecoration.underline,
                                  ),
                                ),
                              ],
                            ),
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppTheme.space3),
```

#### Step 7.4.3: Write consent records after successful registration
In `_handleSignUp`, after the success block (where sign-up succeeds and the user is created), add:

```dart
      // WHY: Create consent records at registration time since the user
      // checked the ToS checkbox. This writes to both SharedPreferences
      // AND ConsentRepository (SQLite audit trail) via acceptConsent().
      final consentProvider = context.read<ConsentProvider>();
      final appVersion = context.read<AppConfigProvider>().appVersion;
      await consentProvider.acceptConsent(appVersion: appVersion);
```

Add import if not already present:
```dart
import 'package:construction_inspector/features/settings/presentation/providers/consent_provider.dart';
```

#### Step 7.4.4: Gate Create Account button on ToS acceptance
Modify the Create Account button's `onPressed` (line 193). Change:

```dart
onPressed: authProvider.isLoading ? null : _handleSignUp,
```

To:

```dart
// WHY: Button is disabled when ToS not accepted OR when loading.
onPressed: authProvider.isLoading || !_tosAccepted ? null : _handleSignUp,
```

#### Step 7.4.5: Add import for ConsentTestingKeys
Add to `register_screen.dart`:

```dart
import 'package:construction_inspector/shared/testing_keys/consent_keys.dart';
```

---

### Sub-phase 7.5: Export new files via barrel exports
**Files:**
- Modify: `lib/shared/testing_keys/testing_keys.dart` (if barrel exists)
- Modify: `lib/features/settings/presentation/providers/providers.dart` (if barrel exists)
- Modify: `lib/features/settings/presentation/screens/screens.dart` (if barrel exists)
**Agent:** general-purpose

#### Step 7.5.1: Add consent_keys export
Check if `lib/shared/testing_keys/testing_keys.dart` exists and add:

```dart
export 'consent_keys.dart';
```

If no barrel exists, add the direct import in files that need it.

#### Step 7.5.2: Add consent_provider export
Check if a providers barrel exists at `lib/features/settings/presentation/providers/providers.dart` and add:

```dart
export 'consent_provider.dart';
```

#### Step 7.5.3: Add consent_screen export
Check if `lib/features/settings/presentation/screens/screens.dart` exists and add:

```dart
export 'consent_screen.dart';
```

---

### Sub-phase 7.6: Verification
**Agent:** qa-testing-agent

#### Step 7.6.1: Static analysis
```
pwsh -Command "flutter analyze"
```

#### Step 7.6.2: Run existing tests
```
pwsh -Command "flutter test"
```

---

## Phase 8: Router Integration
### Sub-phase 8.1: Add consent route to GoRouter
**Files:**
- Modify: `lib/core/router/app_router.dart` (routes list, around line 303)
**Agent:** frontend-flutter-specialist-agent

#### Step 8.1.1: Add ConsentScreen import
Add at the top of `lib/core/router/app_router.dart`:

```dart
import 'package:construction_inspector/features/settings/presentation/screens/consent_screen.dart';
```

#### Step 8.1.2: Add '/consent' to _kNonRestorableRoutes
Modify the `_kNonRestorableRoutes` set (line 52-61) to include `/consent`:

**Old:**
```dart
const _kNonRestorableRoutes = {
  '/profile-setup',
  '/company-setup',
  '/pending-approval',
  '/account-status',
  '/edit-profile',
  '/admin-dashboard',
  '/update-password',
  '/update-required',
};
```

**New:**
```dart
// WHY: '/consent' added — app must never deep-link into the consent screen
// on next launch. The router redirect will send users there if needed.
const _kNonRestorableRoutes = {
  '/profile-setup',
  '/company-setup',
  '/pending-approval',
  '/account-status',
  '/edit-profile',
  '/admin-dashboard',
  '/update-password',
  '/update-required',
  '/consent',
};
```

#### Step 8.1.3: Add '/consent' to _kOnboardingRoutes
Modify the `_kOnboardingRoutes` set (line 41-48) to include `/consent`:

**Old:**
```dart
const _kOnboardingRoutes = {
  '/profile-setup',
  '/company-setup',
  '/pending-approval',
  '/account-status',
  '/update-password',
  '/update-required',
};
```

**New:**
```dart
// WHY: '/consent' is exempt from profile-check redirect — users must
// accept consent before any profile routing happens.
const _kOnboardingRoutes = {
  '/profile-setup',
  '/company-setup',
  '/pending-approval',
  '/account-status',
  '/update-password',
  '/update-required',
  '/consent',
};
```

#### Step 8.1.4: Add GoRoute for consent screen
Insert after the `/update-required` route definition in the routes list (around line 340-350, in the authentication routes section):

```dart
      GoRoute(
        path: '/consent',
        name: 'consent',
        builder: (context, state) => const ConsentScreen(),
      ),
```

---

### Sub-phase 8.2: Add consent check in router redirect
**Files:**
- Modify: `lib/core/router/app_router.dart` (redirect function, after version gate ~line 202)
**Agent:** frontend-flutter-specialist-agent

#### Step 8.2.1: Add ConsentProvider import
Add at the top of `lib/core/router/app_router.dart`:

```dart
import 'package:construction_inspector/features/settings/presentation/providers/consent_provider.dart';
```

#### Step 8.2.2: Insert consent gate after version gate
Insert after the version gate block (after line 202, before the onboarding route check at line 204). The consent check goes between the `try/catch` for AppConfigProvider and the `// If on an onboarding route` comment:

**Insert after line 202 (the closing `}` of the AppConfigProvider try/catch):**

```dart
      // Consent gate: block on /consent when user hasn't accepted current policy.
      // WHY: Placed AFTER version gate (force-update takes priority) and
      // AFTER auth (unauthenticated users don't need consent yet — they'll
      // see the registration checkbox and full consent screen after sign-up).
      // NOTE: Uses try/catch like AppConfigProvider above — provider may not
      // be available in test mode.
      try {
        final consent = context.read<ConsentProvider>();
        if (!consent.hasConsented) {
          if (location == '/consent') return null;
          return '/consent';
        }
      } catch (e) {
        Logger.nav('ConsentProvider not available in router: $e');
      }
```

> **IMPORTANT:** This block must be placed:
> - AFTER the version gate (line 186-202) — so force-update takes priority
> - BEFORE the onboarding route check (line 204) — so consent is checked before profile routing
> - Only runs when `isAuthenticated` is true (it's inside the `if (isAuthenticated)` block that starts at line 186)

---

### Sub-phase 8.3: Add refreshListenable for ConsentProvider
**Files:**
- Modify: `lib/core/router/app_router.dart` (GoRouter constructor, line 126-130)
**Agent:** frontend-flutter-specialist-agent

#### Step 8.3.1: Update AppRouter to accept ConsentProvider
Modify the `AppRouter` class to accept an optional `ConsentProvider`:

**Old (line 63-73):**
```dart
class AppRouter {
  final AuthProvider _authProvider;

  final _rootNavigatorKey = GlobalKey<NavigatorState>();
  final _shellNavigatorKey = GlobalKey<NavigatorState>();

  String _initialLocation = '/';
  GoRouter? _router;

  AppRouter({required AuthProvider authProvider})
      : _authProvider = authProvider;
```

**New:**
```dart
class AppRouter {
  final AuthProvider _authProvider;
  final ConsentProvider? _consentProvider;

  final _rootNavigatorKey = GlobalKey<NavigatorState>();
  final _shellNavigatorKey = GlobalKey<NavigatorState>();

  String _initialLocation = '/';
  GoRouter? _router;

  // WHY: ConsentProvider is optional for backward compatibility with tests
  // that don't set up consent. When null, the consent gate in redirect is
  // skipped (context.read will throw, caught by the try/catch).
  AppRouter({
    required AuthProvider authProvider,
    ConsentProvider? consentProvider,
  })  : _authProvider = authProvider,
       _consentProvider = consentProvider;
```

#### Step 8.3.2: Add ConsentProvider as refreshListenable
The GoRouter currently uses `refreshListenable: _authProvider` (line 130). To listen to both AuthProvider and ConsentProvider, we need a `Listenable.merge`:

**Old (line 130):**
```dart
    refreshListenable: _authProvider,
```

**New:**
```dart
    // WHY: Router must re-evaluate redirects when consent state changes
    // (e.g., user accepts consent on ConsentScreen). Listenable.merge
    // triggers redirect re-evaluation when either provider notifies.
    refreshListenable: _consentProvider != null
        ? Listenable.merge([_authProvider, _consentProvider])
        : _authProvider,
```

---

### Sub-phase 8.4: Pass ConsentProvider to AppRouter in main.dart
**Files:**
- Modify: `lib/main.dart` (where AppRouter is created)
**Agent:** general-purpose

#### Step 8.4.1: Find AppRouter instantiation and add consentProvider
Search `lib/main.dart` for `AppRouter(` and add the consentProvider parameter:

**Old:**
```dart
AppRouter(authProvider: authProvider)
```

**New:**
```dart
// WHY: ConsentProvider passed to AppRouter so the router can gate
// navigation behind consent acceptance.
AppRouter(authProvider: authProvider, consentProvider: consentProvider)
```

---

### Sub-phase 8.5: Verification
**Agent:** qa-testing-agent

#### Step 8.5.1: Static analysis
```
pwsh -Command "flutter analyze"
```

#### Step 8.5.2: Run existing tests
```
pwsh -Command "flutter test"
```

#### Step 8.5.3: Manual verification checklist
Verify the following flow manually:
1. Fresh install → sign up → ToS checkbox required → consent screen after auth → dashboard
2. Existing user without consent → login → consent screen → dashboard
3. Policy version bump → existing consented user → consent screen on next launch
4. Accept consent → navigates to dashboard (or onboarding if profile incomplete)
5. Sentry DSN empty → no errors, Sentry is no-op
6. APTABASE_APP_KEY empty → no errors, analytics skipped

---

## Phase 9: About Screen Overhaul
### Sub-phase 9.1: Add Testing Keys & Build Number Getter
**Files:**
- Modify: `lib/shared/testing_keys/settings_keys.dart`
- Modify: `lib/features/auth/presentation/providers/app_config_provider.dart`
**Agent:** frontend-flutter-specialist-agent

#### Step 9.1.1: Add new testing keys for About section tiles
**File:** `lib/shared/testing_keys/settings_keys.dart`

Add the following keys after `settingsLicensesTile` (line 99), inside the `// Settings - Help & About Tiles` section:

```dart
  // WHY: New About section tiles for pre-release hardening (ToS, Privacy, build number, help)
  static const aboutTosTile = Key('about_tos_tile');
  static const aboutPrivacyTile = Key('about_privacy_tile');
  static const aboutBuildNumber = Key('about_build_number');
```

NOTE: `settingsHelpSupportTile` (line 97) already exists — reuse it, do NOT duplicate.

#### Step 9.1.2: Add buildNumber getter to AppConfigProvider
**File:** `lib/features/auth/presentation/providers/app_config_provider.dart`

Add a new field and getter. After `String? _appVersion;` (line 24), add:

```dart
  // WHY: Build number displayed in About section for debugging/support reference
  String? _buildNumber;
```

After the `String? get appVersion => _appVersion;` getter (line 103), add:

```dart
  /// Current app build number string (e.g., "3" from version 0.1.2+3).
  String? get buildNumber => _buildNumber;
```

In `loadAppVersion()` (line 113-121), after `_appVersion = info.version;` (line 116), add:

```dart
      _buildNumber = info.buildNumber;
```

### Sub-phase 9.2: Replace About Section in Settings Screen
**Files:**
- Modify: `lib/features/settings/presentation/screens/settings_screen.dart`
**Agent:** frontend-flutter-specialist-agent

#### Step 9.2.1: Add url_launcher import
**File:** `lib/features/settings/presentation/screens/settings_screen.dart`

Add at the top imports section (verify it is not already imported):

```dart
import 'package:url_launcher/url_launcher.dart';
```

NOTE: `url_launcher` is already a dependency in pubspec.yaml (line 96). No pubspec change needed.

#### Step 9.2.2: Replace the entire About section (lines 312-346)
**File:** `lib/features/settings/presentation/screens/settings_screen.dart`

Replace the block from `// ---- 5. ABOUT ----` (line 312) through the closing `const SizedBox(height: 32),` (line 346) with:

```dart
          // ---- 5. ABOUT ----
          // WHY: Enhanced About section for pre-release — version+build, help, ToS, privacy, licenses
          SectionHeader(
            key: TestingKeys.settingsAboutSection,
            title: 'About',
          ),
          // Version tile with build number subtitle
          Consumer<AppConfigProvider>(
            builder: (context, configProvider, _) {
              final version = configProvider.appVersion ?? 'unknown';
              final build = configProvider.buildNumber ?? '?';
              return ListTile(
                key: TestingKeys.settingsVersionTile,
                leading: const Icon(Icons.info_outline),
                title: const Text('Version'),
                // NOTE: Show both version and build for support ticket reference
                subtitle: Text(
                  '$version (build $build)',
                  key: TestingKeys.aboutBuildNumber,
                ),
              );
            },
          ),
          // Help & Support — navigates to support ticket form
          ListTile(
            key: TestingKeys.settingsHelpSupportTile,
            leading: const Icon(Icons.help_outline),
            title: const Text('Help & Support'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // WHY: Route to support ticket screen added in Phase 10
              context.pushNamed('help-support');
            },
          ),
          // Terms of Service — navigates to legal document viewer
          ListTile(
            key: TestingKeys.aboutTosTile,
            leading: const Icon(Icons.gavel),
            title: const Text('Terms of Service'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              // WHY: Route to legal document screen added in Phase 11
              context.pushNamed(
                'legal-document',
                queryParameters: {'type': 'tos'},
              );
            },
          ),
          // Privacy Policy — navigates to legal document viewer
          ListTile(
            key: TestingKeys.aboutPrivacyTile,
            leading: const Icon(Icons.privacy_tip_outlined),
            title: const Text('Privacy Policy'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              context.pushNamed(
                'legal-document',
                queryParameters: {'type': 'privacy'},
              );
            },
          ),
          // Licenses — uses Flutter's built-in LicenseRegistry for accurate data
          Consumer<AppConfigProvider>(
            builder: (context, configProvider, _) {
              return ListTile(
                key: TestingKeys.settingsLicensesTile,
                leading: const Icon(Icons.description),
                title: const Text('Open Source Licenses'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  // WHY: Route to custom licenses screen added in Phase 11.
                  // Replaces showLicensePage() with a custom screen that
                  // renders grouped license entries from LicenseRegistry.
                  context.pushNamed('oss-licenses');
                },
              );
            },
          ),
          const SizedBox(height: 32),
```

### Sub-phase 9.3: Verify Phase 9
**Agent:** frontend-flutter-specialist-agent

#### Step 9.3.1: Run static analysis
```
pwsh -Command "flutter analyze lib/features/settings/presentation/screens/settings_screen.dart lib/features/auth/presentation/providers/app_config_provider.dart lib/shared/testing_keys/settings_keys.dart"
```

NOTE: Analysis will report unresolved routes (`help-support`, `legal-document`, `oss-licenses`) — these are wired in Phase 12. The code compiles but routes are dead until then.

---

## Phase 10: Support Ticket System
### Sub-phase 10.1: Create SupportProvider
**Files:**
- Create: `lib/features/settings/presentation/providers/support_provider.dart`
- Modify: `lib/features/settings/presentation/providers/providers.dart` (barrel export)
**Agent:** frontend-flutter-specialist-agent

#### Step 10.1.1: Create SupportProvider class
**File:** `lib/features/settings/presentation/providers/support_provider.dart` (NEW)

```dart
import 'dart:io';

import 'package:archive/archive.dart';
import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:uuid/uuid.dart';
import 'package:construction_inspector/core/config/supabase_config.dart';
import 'package:construction_inspector/core/logging/logger.dart';
import 'package:construction_inspector/features/settings/data/repositories/support_repository.dart';
import 'package:construction_inspector/features/settings/data/models/support_ticket.dart';

/// WHY: Handles support ticket submission with optional log bundle upload.
/// Tickets are inserted into LOCAL SQLite via SupportRepository (offline-first).
/// Log files are zipped and uploaded to Supabase Storage `support-logs` bucket.
/// Sync of the support_tickets table to Supabase is deferred (see FIX-12).
class SupportProvider extends ChangeNotifier {
  final SupportRepository _supportRepository;

  SupportProvider({required SupportRepository supportRepository})
      : _supportRepository = supportRepository;
  // Subject categories matching support workflow
  // WHY: Fixed categories allow support team to triage efficiently
  static const List<String> subjectCategories = [
    'Bug Report',
    'Feature Request',
    'General Feedback',
    'Other',
  ];

  String? _selectedSubject;
  String _message = '';
  bool _attachLogs = false;
  bool _isSubmitting = false;
  String? _error;
  bool _submitted = false;

  // Getters
  String? get selectedSubject => _selectedSubject;
  String get message => _message;
  bool get attachLogs => _attachLogs;
  bool get isSubmitting => _isSubmitting;
  String? get error => _error;
  bool get submitted => _submitted;

  /// Whether the form is valid for submission.
  bool get canSubmit =>
      _selectedSubject != null &&
      _message.trim().length >= 10 &&
      !_isSubmitting;

  // Setters
  void setSubject(String? subject) {
    _selectedSubject = subject;
    notifyListeners();
  }

  void setMessage(String message) {
    _message = message;
    notifyListeners();
  }

  void setAttachLogs(bool attach) {
    _attachLogs = attach;
    notifyListeners();
  }

  /// Reset form to initial state.
  void reset() {
    _selectedSubject = null;
    _message = '';
    _attachLogs = false;
    _isSubmitting = false;
    _error = null;
    _submitted = false;
    notifyListeners();
  }

  /// Submit the support ticket.
  ///
  /// 1. If attachLogs is true, zip log files and upload to Supabase Storage.
  /// 2. Insert a SupportTicket into LOCAL SQLite via SupportRepository (offline-first).
  /// 3. On failure, set error message but don't throw.
  Future<void> submit({
    required String userId,
    required String? appVersion,
  }) async {
    if (!canSubmit) return;

    _isSubmitting = true;
    _error = null;
    notifyListeners();

    try {
      final ticketId = const Uuid().v4();
      String? logPath;

      // Step 1: Bundle and upload logs if requested
      // NOTE: Log upload still goes directly to Supabase Storage (separate from ticket record)
      if (_attachLogs) {
        logPath = await _uploadLogBundle(userId: userId, ticketId: ticketId);
      }

      // Step 2: Insert ticket into LOCAL SQLite via SupportRepository (offline-first)
      // WHY: Tickets are stored locally first, then synced to Supabase later.
      // This follows the app's offline-first architecture.
      // NOTE: build_number removed (not in schema), platform added, log_file_path corrected.
      final ticket = SupportTicket(
        id: ticketId,
        userId: userId,
        subject: _selectedSubject,
        message: _message.trim(),
        appVersion: appVersion ?? 'unknown',
        platform: defaultTargetPlatform.name,
        logFilePath: logPath,
      );

      await _supportRepository.submitTicket(ticket);
      // TODO: Sync trigger for support_tickets — deferred (see FIX-12)

      _submitted = true;
      Logger.ui('[SupportProvider] Ticket $ticketId submitted successfully');
    } catch (e) {
      Logger.error('[SupportProvider] Ticket submission failed: $e');
      _error = 'Failed to submit ticket. Please try again later.';
    } finally {
      _isSubmitting = false;
      notifyListeners();
    }
  }

  /// Zip log files from the current session directory and upload to Supabase Storage.
  /// Returns the remote path on success, null on failure.
  Future<String?> _uploadLogBundle({
    required String userId,
    required String ticketId,
  }) async {
    try {
      final logDir = Logger.logDirectoryPath;
      if (logDir == null) {
        Logger.ui('[SupportProvider] No log directory available, skipping log upload');
        return null;
      }

      final dir = Directory(logDir);
      if (!await dir.exists()) return null;

      // WHY: Collect all .log files from the log directory (not subdirs)
      // to keep bundle size manageable
      final logFiles = await dir
          .list()
          .where((entity) => entity is File && entity.path.endsWith('.log'))
          .cast<File>()
          .toList();

      if (logFiles.isEmpty) return null;

      // Create zip archive
      final archive = Archive();
      for (final file in logFiles) {
        final bytes = await file.readAsBytes();
        final name = file.uri.pathSegments.last;
        archive.addFile(ArchiveFile(name, bytes.length, bytes));
      }

      final zipBytes = ZipEncoder().encode(archive);
      if (zipBytes == null) return null;

      // FROM SPEC: "Cap at last N session files or X MB total"
      const maxLogBundleSize = 5 * 1024 * 1024; // 5MB
      if (zipBytes.length > maxLogBundleSize) {
        Logger.ui('Log bundle too large (${zipBytes.length} bytes), skipping upload');
        return null;
      }

      // Upload to Supabase Storage
      final remotePath = '$userId/$ticketId/logs.zip';
      final storage = Supabase.instance.client.storage;
      await storage.from('support-logs').uploadBinary(
        remotePath,
        zipBytes,
        fileOptions: const FileOptions(contentType: 'application/zip'),
      );

      Logger.ui('[SupportProvider] Log bundle uploaded: $remotePath');
      return remotePath;
    } catch (e) {
      // WHY: Log upload failure should NOT block ticket submission
      Logger.error('[SupportProvider] Log bundle upload failed: $e');
      return null;
    }
  }
}
```

NOTE: This uses the `archive` package. It must be added to pubspec.yaml in Step 10.1.3.

#### Step 10.1.2: Add barrel export
**File:** `lib/features/settings/presentation/providers/providers.dart`

Add to the exports:

```dart
export 'support_provider.dart';
```

#### Step 10.1.3: Add `archive` dependency to pubspec.yaml
**File:** `pubspec.yaml`

Under the `# Utilities` section (after line 103, near `crypto`), add:

```yaml
  archive: ^4.0.2
```

Then run:
```
pwsh -Command "flutter pub get"
```

### Sub-phase 10.2: Create Testing Keys for Support Screen
**Files:**
- Create: `lib/shared/testing_keys/support_keys.dart`
- Modify: `lib/shared/testing_keys/testing_keys.dart` (barrel export + facade)
**Agent:** frontend-flutter-specialist-agent

#### Step 10.2.1: Create support_keys.dart
**File:** `lib/shared/testing_keys/support_keys.dart` (NEW)

```dart
import 'package:flutter/material.dart';

/// Support ticket screen testing keys.
class SupportTestingKeys {
  SupportTestingKeys._(); // Prevent instantiation

  // WHY: Keys for support ticket form elements, used in integration tests
  static const supportSubjectDropdown = Key('support_subject_dropdown');
  static const supportMessageField = Key('support_message_field');
  static const supportAttachLogs = Key('support_attach_logs');
  static const supportSubmitButton = Key('support_submit_button');
}
```

#### Step 10.2.2: Add barrel export and facade delegation in testing_keys.dart
**File:** `lib/shared/testing_keys/testing_keys.dart`

Add to the export list (after `export 'sync_keys.dart';`):

```dart
export 'support_keys.dart';
```

Add to the import list (after `import 'sync_keys.dart';`):

```dart
import 'support_keys.dart';
```

Add facade delegation inside the `TestingKeys` class body (follow the existing pattern of delegating to feature-specific keys classes). Find the appropriate alphabetical position in the facade and add:

```dart
  // ============================================
  // Support Ticket
  // ============================================
  static const supportSubjectDropdown = SupportTestingKeys.supportSubjectDropdown;
  static const supportMessageField = SupportTestingKeys.supportMessageField;
  static const supportAttachLogs = SupportTestingKeys.supportAttachLogs;
  static const supportSubmitButton = SupportTestingKeys.supportSubmitButton;
```

### Sub-phase 10.3: Create HelpSupportScreen
**Files:**
- Create: `lib/features/settings/presentation/screens/help_support_screen.dart`
- Modify: `lib/features/settings/presentation/screens/screens.dart` (barrel export)
**Agent:** frontend-flutter-specialist-agent

#### Step 10.3.1: Create HelpSupportScreen widget
**File:** `lib/features/settings/presentation/screens/help_support_screen.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/settings/presentation/providers/support_provider.dart';
import 'package:construction_inspector/shared/shared.dart';

/// WHY: Support ticket form screen. Users can report bugs, request features,
/// or send general feedback. Optional log attachment for debugging.
class HelpSupportScreen extends StatefulWidget {
  const HelpSupportScreen({super.key});

  @override
  State<HelpSupportScreen> createState() => _HelpSupportScreenState();
}

class _HelpSupportScreenState extends State<HelpSupportScreen> {
  final _messageController = TextEditingController();

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Help & Support'),
      ),
      body: Consumer<SupportProvider>(
        builder: (context, provider, _) {
          // WHY: Show success state after submission
          if (provider.submitted) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(
                      Icons.check_circle_outline,
                      size: 64,
                      color: Colors.green,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Ticket Submitted',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Thank you for your feedback. We\'ll review your ticket and get back to you.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: () {
                        provider.reset();
                        Navigator.of(context).pop();
                      },
                      child: const Text('Done'),
                    ),
                  ],
                ),
              ),
            );
          }

          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Subject dropdown
                DropdownButtonFormField<String>(
                  key: TestingKeys.supportSubjectDropdown,
                  decoration: const InputDecoration(
                    labelText: 'Subject',
                    border: OutlineInputBorder(),
                  ),
                  value: provider.selectedSubject,
                  items: SupportProvider.subjectCategories
                      .map(
                        (cat) => DropdownMenuItem(value: cat, child: Text(cat)),
                      )
                      .toList(),
                  onChanged: provider.isSubmitting ? null : provider.setSubject,
                  // WHY: Required field — shows validation hint
                  hint: const Text('Select a category'),
                ),
                const SizedBox(height: 16),

                // Message field
                TextFormField(
                  key: TestingKeys.supportMessageField,
                  controller: _messageController,
                  decoration: const InputDecoration(
                    labelText: 'Message',
                    border: OutlineInputBorder(),
                    hintText: 'Describe your issue or feedback (min 10 characters)',
                    alignLabelWithHint: true,
                  ),
                  maxLines: 6,
                  maxLength: 2000,
                  enabled: !provider.isSubmitting,
                  onChanged: provider.setMessage,
                ),
                const SizedBox(height: 8),

                // Attach logs toggle
                SwitchListTile(
                  key: TestingKeys.supportAttachLogs,
                  title: const Text('Attach diagnostic logs'),
                  subtitle: const Text(
                    'Includes recent app logs to help diagnose issues',
                  ),
                  value: provider.attachLogs,
                  onChanged: provider.isSubmitting
                      ? null
                      : (value) => provider.setAttachLogs(value),
                ),
                const SizedBox(height: 16),

                // Error message
                if (provider.error != null) ...[
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.errorContainer,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      provider.error!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.onErrorContainer,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // Submit button
                FilledButton.icon(
                  key: TestingKeys.supportSubmitButton,
                  onPressed: provider.canSubmit
                      ? () => _submit(context, provider)
                      : null,
                  icon: provider.isSubmitting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.send),
                  label: Text(
                    provider.isSubmitting ? 'Submitting...' : 'Submit Ticket',
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Future<void> _submit(BuildContext context, SupportProvider provider) async {
    final authProvider = context.read<AuthProvider>();
    final configProvider = context.read<AppConfigProvider>();
    final userId = authProvider.userProfile?.id ?? 'anonymous';

    await provider.submit(
      userId: userId,
      appVersion: configProvider.appVersion,
    );
  }
}
```

#### Step 10.3.2: Add barrel export
**File:** `lib/features/settings/presentation/screens/screens.dart`

Add:

```dart
export 'help_support_screen.dart';
```

### Sub-phase 10.4: Verify Phase 10
**Agent:** frontend-flutter-specialist-agent

#### Step 10.4.1: Run static analysis
```
pwsh -Command "flutter analyze lib/features/settings/presentation/"
```

NOTE: `archive` package may need import adjustment. The package exports `Archive`, `ArchiveFile`, and `ZipEncoder` from `package:archive/archive.dart`. Verify the import path compiles.

---

## Phase 11: Legal Documents
### Sub-phase 11.1: Create Legal Document Assets
**Files:**
- Create: `assets/legal/terms_of_service.md`
- Create: `assets/legal/privacy_policy.md`
- Modify: `pubspec.yaml` (register assets)
**Agent:** general-purpose

#### Step 11.1.1: Create Terms of Service markdown
**File:** `assets/legal/terms_of_service.md` (NEW)

```markdown
# Field Guide — Terms of Service

**Effective Date:** March 29, 2026
**Last Updated:** March 29, 2026

## 1. Acceptance of Terms

By downloading, installing, or using Field Guide ("the App"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree, do not use the App.

## 2. Description of Service

Field Guide is a construction inspection tracking application that enables inspectors to:
- Record daily inspection entries and field observations
- Track quantities, contractors, and project personnel
- Capture and organize construction site photographs
- Generate professional PDF inspection reports
- Fill out and manage standardized inspection forms (e.g., MDOT 0582B)
- Synchronize data across devices via cloud services

## 3. Account Registration

You must register an account to use the App. You agree to:
- Provide accurate, current, and complete registration information
- Maintain and promptly update your registration information
- Maintain the security of your password and accept responsibility for all activities under your account
- Immediately notify us of unauthorized use of your account

## 4. User Content

You retain ownership of all content you create in the App, including inspection entries, photos, reports, and form submissions ("User Content"). By using the App, you grant us a limited license to store, process, and transmit your User Content solely for the purpose of providing the service.

## 5. Acceptable Use

You agree not to:
- Use the App for any unlawful purpose
- Upload malicious content or attempt to compromise the system
- Share your account credentials with unauthorized users
- Circumvent any access controls or security measures
- Attempt to access data belonging to other users or organizations

## 6. Data Retention

Construction inspection records may be subject to regulatory retention requirements. The App retains your data for a minimum of 7 years to comply with typical construction industry record-keeping requirements. You may request data export at any time.

## 7. Service Availability

We strive to maintain high availability but do not guarantee uninterrupted service. The App is designed for offline-first operation; core features work without an internet connection. Cloud synchronization requires connectivity.

## 8. Intellectual Property

The App, including its design, code, and documentation, is protected by copyright and other intellectual property laws. You may not copy, modify, distribute, or reverse-engineer the App.

## 9. Limitation of Liability

TO THE MAXIMUM EXTENT PERMITTED BY LAW, THE APP IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND. WE SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING FROM YOUR USE OF THE APP.

The App generates reports and records based on user input. Accuracy of inspection records is the responsibility of the inspector. The App does not replace professional judgment.

## 10. Termination

We may suspend or terminate your access to the App at any time for violation of these Terms. Upon termination, your right to use the App ceases immediately. Your data will be retained per Section 6.

## 11. Changes to Terms

We may modify these Terms at any time. Continued use of the App after changes constitutes acceptance of the modified Terms. We will notify users of material changes via the App.

## 12. Contact

For questions about these Terms, contact us through the Help & Support section in the App.
```

#### Step 11.1.2: Create Privacy Policy markdown
**File:** `assets/legal/privacy_policy.md` (NEW)

```markdown
# Field Guide — Privacy Policy

**Effective Date:** March 29, 2026
**Last Updated:** March 29, 2026

## 1. Introduction

This Privacy Policy describes how Field Guide ("the App," "we," "our") collects, uses, and protects your information. We are committed to protecting the privacy of construction inspectors and their organizations.

## 2. Information We Collect

### 2.1 Account Information
- Name, email address, and professional initials
- Organization/company affiliation
- Role (Inspector, Engineer, Admin)

### 2.2 Inspection Data
- Daily inspection entries and field observations
- Contractor and personnel records
- Quantity tracking and bid item data
- Form submissions (e.g., MDOT 0582B soil density reports)

### 2.3 Photographs
- Construction site photographs captured through the App
- **Photo EXIF metadata**, including GPS coordinates, timestamps, and camera settings
- GPS/location data is embedded in photos for geo-tagging inspection evidence

### 2.4 Device Information
- Device model and operating system version (for crash reporting)
- App version and build number

### 2.5 Usage Analytics
- Anonymous usage patterns via **Aptabase** (privacy-focused analytics)
- **No personally identifiable information (PII)** is sent to analytics
- Analytics help us improve the App experience

## 3. How We Process Your Data

### 3.1 On-Device Processing
- **OCR (Optical Character Recognition)** is performed entirely on-device using Tesseract
- No document images or OCR text are sent to external servers
- PDF generation occurs locally on your device

### 3.2 Cloud Synchronization
- Data is synchronized to our cloud backend via **Supabase** (hosted on AWS)
- Synchronization enables multi-device access and team collaboration
- Data is encrypted in transit (TLS 1.2+) and at rest
- Row-Level Security (RLS) ensures users can only access data belonging to their organization

### 3.3 Local Storage
- A local database caches your data on-device for offline access
- Local data is stored in a local database within the app's private storage directory
- Uninstalling the App removes all local data

## 4. Crash Reporting

We use **Sentry** for anonymous crash reporting:
- Stack traces and error messages (no PII)
- Device model and OS version
- App version and build number
- Crash reports help us identify and fix bugs quickly

## 5. Data Sharing

- **We do not sell your data to third parties**
- Data is shared only with your organization's team members (as configured by your Admin)
- We may disclose data if required by law or legal process
- Service providers (Supabase, Sentry, Aptabase) process data on our behalf under strict data processing agreements

## 6. Data Retention

- Inspection records are retained for a minimum of **7 years** to comply with construction industry record-keeping requirements
- You may request data export at any time through your organization's Admin
- Account deletion requests will be processed within 30 days, subject to retention requirements
- Diagnostic logs are retained for 30 days and automatically purged

## 7. Data Security

- All cloud data is protected by Row-Level Security (RLS) policies
- Authentication is handled via Supabase Auth with secure token management
- Sensitive credentials are stored using platform-secure storage (Keychain/Keystore)
- Regular security reviews and dependency updates

## 8. Your Rights

Depending on your jurisdiction, you may have the right to:
- Access your personal data
- Correct inaccurate data
- Request deletion of your data (subject to retention requirements)
- Export your data in a portable format
- Object to certain processing activities

## 9. Children's Privacy

The App is not intended for use by individuals under 18 years of age. We do not knowingly collect personal information from children.

## 10. Changes to This Policy

We may update this Privacy Policy from time to time. We will notify you of material changes via the App. Continued use of the App after changes constitutes acceptance.

## 11. Contact

For privacy-related questions or to exercise your rights, contact us through the Help & Support section in the App.
```

#### Step 11.1.3: Register legal assets in pubspec.yaml
**File:** `pubspec.yaml`

After the line `    - assets/tessdata/` (line 154), add:

```yaml
    - assets/legal/
```

### Sub-phase 11.2: Add flutter_markdown Dependency
**Files:**
- Modify: `pubspec.yaml`
**Agent:** general-purpose

#### Step 11.2.1: Add flutter_markdown to pubspec.yaml
**File:** `pubspec.yaml`

Under the `# URL Launching` section (after `url_launcher: ^6.3.1`, line 96), add:

```yaml

  # Legal / Markdown rendering
  flutter_markdown: ^0.7.6
```

Then run:
```
pwsh -Command "flutter pub get"
```

### Sub-phase 11.3: Create LegalDocumentScreen
**Files:**
- Create: `lib/features/settings/presentation/screens/legal_document_screen.dart`
- Modify: `lib/features/settings/presentation/screens/screens.dart` (barrel export)
**Agent:** frontend-flutter-specialist-agent

#### Step 11.3.1: Create LegalDocumentScreen widget
**File:** `lib/features/settings/presentation/screens/legal_document_screen.dart` (NEW)

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:construction_inspector/core/logging/logger.dart';

/// WHY: Renders bundled markdown legal documents (ToS, Privacy Policy).
/// Supports "open in browser" for external viewing.
/// The `type` parameter selects which document to display:
/// - 'tos' -> assets/legal/terms_of_service.md
/// - 'privacy' -> assets/legal/privacy_policy.md
class LegalDocumentScreen extends StatefulWidget {
  final String type;

  const LegalDocumentScreen({super.key, required this.type});

  @override
  State<LegalDocumentScreen> createState() => _LegalDocumentScreenState();
}

class _LegalDocumentScreenState extends State<LegalDocumentScreen> {
  String? _markdownContent;
  String? _error;

  /// Map document type to asset path and display title.
  static const _documents = {
    'tos': (
      asset: 'assets/legal/terms_of_service.md',
      title: 'Terms of Service',
    ),
    'privacy': (
      asset: 'assets/legal/privacy_policy.md',
      title: 'Privacy Policy',
    ),
  };

  @override
  void initState() {
    super.initState();
    _loadDocument();
  }

  Future<void> _loadDocument() async {
    final doc = _documents[widget.type];
    if (doc == null) {
      setState(() => _error = 'Unknown document type: ${widget.type}');
      return;
    }

    try {
      final content = await rootBundle.loadString(doc.asset);
      if (!mounted) return;
      setState(() => _markdownContent = content);
    } catch (e) {
      Logger.error('[LegalDocumentScreen] Failed to load ${doc.asset}: $e');
      if (!mounted) return;
      setState(() => _error = 'Failed to load document.');
    }
  }

  String get _title {
    return _documents[widget.type]?.title ?? 'Legal Document';
  }

  /// WHY: Hosted URLs for legal documents — placeholder until GitHub Pages is set up.
  static const _hostedUrls = {
    'tos': 'https://fieldguideapp.com/terms',
    'privacy': 'https://fieldguideapp.com/privacy',
  };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_title),
        // WHY: Spec requires "Open in browser button in app bar to view hosted version"
        actions: [
          IconButton(
            icon: const Icon(Icons.open_in_browser),
            tooltip: 'Open in browser',
            onPressed: () async {
              final url = _hostedUrls[widget.type] ?? _hostedUrls['tos']!;
              try {
                await launchUrl(
                  Uri.parse(url),
                  mode: LaunchMode.externalApplication,
                );
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Unable to open browser. Check your internet connection.'),
                    ),
                  );
                }
              }
            },
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(_error!, style: const TextStyle(color: Colors.red)),
        ),
      );
    }

    if (_markdownContent == null) {
      return const Center(child: CircularProgressIndicator());
    }

    return Markdown(
      data: _markdownContent!,
      selectable: true,
      // WHY: Handle taps on links in the markdown content
      onTapLink: (text, href, title) {
        if (href != null) {
          launchUrl(
            Uri.parse(href),
            mode: LaunchMode.externalApplication,
          );
        }
      },
    );
  }
}
```

#### Step 11.3.2: Add barrel export
**File:** `lib/features/settings/presentation/screens/screens.dart`

Add:

```dart
export 'legal_document_screen.dart';
```

### Sub-phase 11.4: Create OssLicensesScreen
**Files:**
- Create: `lib/features/settings/presentation/screens/oss_licenses_screen.dart`
- Modify: `lib/features/settings/presentation/screens/screens.dart` (barrel export)
**Agent:** frontend-flutter-specialist-agent

#### Step 11.4.1: Create OssLicensesScreen widget
**File:** `lib/features/settings/presentation/screens/oss_licenses_screen.dart` (NEW)

```dart
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// WHY: Custom open-source licenses screen that reads from Flutter's built-in
/// LicenseRegistry. Replaces the default showLicensePage() with a more
/// polished and navigable experience. Groups licenses by package name.
///
/// NOTE: We intentionally use LicenseRegistry (built into Flutter) instead of
/// a third-party oss_licenses package. This ensures accuracy since
/// LicenseRegistry is populated directly from pubspec.lock at build time.
class OssLicensesScreen extends StatefulWidget {
  const OssLicensesScreen({super.key});

  @override
  State<OssLicensesScreen> createState() => _OssLicensesScreenState();
}

class _OssLicensesScreenState extends State<OssLicensesScreen> {
  late Future<Map<String, List<LicenseEntry>>> _licensesFuture;

  @override
  void initState() {
    super.initState();
    _licensesFuture = _loadLicenses();
  }

  /// Collects all license entries from LicenseRegistry and groups by package.
  Future<Map<String, List<LicenseEntry>>> _loadLicenses() async {
    final Map<String, List<LicenseEntry>> grouped = {};

    await for (final entry in LicenseRegistry.licenses) {
      for (final package in entry.packages) {
        grouped.putIfAbsent(package, () => []).add(entry);
      }
    }

    // Sort package names alphabetically
    final sorted = Map.fromEntries(
      grouped.entries.toList()..sort((a, b) => a.key.compareTo(b.key)),
    );

    return sorted;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Open Source Licenses'),
      ),
      body: FutureBuilder<Map<String, List<LicenseEntry>>>(
        future: _licensesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError) {
            return Center(
              child: Text('Failed to load licenses: ${snapshot.error}'),
            );
          }

          final licenses = snapshot.data!;

          return ListView.builder(
            itemCount: licenses.length,
            itemBuilder: (context, index) {
              final package = licenses.keys.elementAt(index);
              final entries = licenses[package]!;

              return ExpansionTile(
                title: Text(package),
                subtitle: Text(
                  '${entries.length} license${entries.length > 1 ? 's' : ''}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                children: entries.map((entry) {
                  // WHY: LicenseEntry.paragraphs yields LicenseParagraph objects.
                  // Each has `text` and `indent` properties.
                  final paragraphText = entry.paragraphs
                      .map((p) => p.text)
                      .join('\n\n');

                  return Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    child: Text(
                      paragraphText,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  );
                }).toList(),
              );
            },
          );
        },
      ),
    );
  }
}
```

#### Step 11.4.2: Add barrel export
**File:** `lib/features/settings/presentation/screens/screens.dart`

Add:

```dart
export 'oss_licenses_screen.dart';
```

### Sub-phase 11.5: Verify Phase 11
**Agent:** frontend-flutter-specialist-agent

#### Step 11.5.1: Run pub get and static analysis
```
pwsh -Command "flutter pub get && flutter analyze lib/features/settings/presentation/screens/legal_document_screen.dart lib/features/settings/presentation/screens/oss_licenses_screen.dart"
```

---

## Phase 12: Integration Testing & Cleanup
### Sub-phase 12.1: Wire Routes in AppRouter
**Files:**
- Modify: `lib/core/router/app_router.dart`
**Agent:** general-purpose

#### Step 12.1.1: Add import for new screens
**File:** `lib/core/router/app_router.dart`

Verify that `lib/features/settings/presentation/screens/screens.dart` is already imported (it is, via line 20: `import '...settings/presentation/screens/screens.dart';`). No new import needed — the barrel export handles it.

#### Step 12.1.2: Add routes for help-support, legal-document, and oss-licenses
**File:** `lib/core/router/app_router.dart`

Find the route block for `/admin-dashboard` (around line 426-428). After that GoRoute block, add three new routes:

```dart
      // WHY: Help & Support ticket form — Phase 10
      GoRoute(
        path: '/help-support',
        name: 'help-support',
        builder: (context, state) => const HelpSupportScreen(),
      ),
      // WHY: Legal document viewer — Phase 11
      // Query param 'type' selects document: 'tos' or 'privacy'
      GoRoute(
        path: '/legal-document',
        name: 'legal-document',
        builder: (context, state) {
          final type = state.uri.queryParameters['type'] ?? 'tos';
          return LegalDocumentScreen(type: type);
        },
      ),
      // WHY: Open source licenses screen — Phase 11
      GoRoute(
        path: '/oss-licenses',
        name: 'oss-licenses',
        builder: (context, state) => const OssLicensesScreen(),
      ),
```

### Sub-phase 12.2: Wire SupportProvider in main.dart
**Files:**
- Modify: `lib/main.dart`
**Agent:** general-purpose

#### Step 12.2.1: Add SupportProvider to ConstructionInspectorApp
**File:** `lib/main.dart`

This is a two-part change:

**Part A:** In the `_runApp()` function, create the repository and provider. The repository should be created alongside other repositories (after DatabaseService init). The provider should be created before the `runApp(` call:

```dart
  // Create alongside other repositories after DatabaseService init:
  final supportLocalDatasource = SupportLocalDatasource(dbService);
  final supportRepository = SupportRepository(supportLocalDatasource);

  // Create before runApp():
  final supportProvider = SupportProvider(supportRepository: supportRepository);
```

Add the imports at the top of the file:

```dart
import 'package:construction_inspector/features/settings/presentation/providers/support_provider.dart';
import 'package:construction_inspector/features/settings/data/datasources/support_local_datasource.dart';
import 'package:construction_inspector/features/settings/data/repositories/support_repository.dart';
```

**Part B:** Pass it into `ConstructionInspectorApp`. Add to the constructor call (after `documentService: documentService,` on line 593):

```dart
      supportProvider: supportProvider,
```

**Part C:** Add the field and constructor parameter to `ConstructionInspectorApp` class.

After `final DocumentService documentService;` (around line 769), add:

```dart
  final SupportProvider supportProvider;
```

After `required this.documentService,` in the constructor (around line 807), add:

```dart
    required this.supportProvider,
```

**Part D:** Add to the MultiProvider providers list. Find an appropriate spot in the providers list (after `ChangeNotifierProvider.value(value: appConfigProvider),` around line 816), add:

```dart
        ChangeNotifierProvider.value(value: supportProvider),
```

### Sub-phase 12.3: Create Integration Test Stubs
**Files:**
- Create: `test/features/settings/about_section_test.dart`
**Agent:** qa-testing-agent

#### Step 12.3.1: Create unit test for SupportProvider
**File:** `test/features/settings/about_section_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:construction_inspector/features/settings/data/repositories/support_repository.dart';
import 'package:construction_inspector/features/settings/presentation/providers/support_provider.dart';

@GenerateMocks([SupportRepository])
import 'about_section_test.mocks.dart';

/// WHY: Unit tests for SupportProvider validation logic.
/// Integration tests for full form submission require Supabase mocking
/// and are deferred to the E2E test suite.
void main() {
  group('SupportProvider', () {
    late MockSupportRepository mockSupportRepo;
    late SupportProvider provider;

    setUp(() {
      mockSupportRepo = MockSupportRepository();
      provider = SupportProvider(supportRepository: mockSupportRepo);
    });

    test('initial state is valid', () {
      expect(provider.selectedSubject, isNull);
      expect(provider.message, isEmpty);
      expect(provider.attachLogs, isFalse);
      expect(provider.isSubmitting, isFalse);
      expect(provider.error, isNull);
      expect(provider.submitted, isFalse);
      expect(provider.canSubmit, isFalse);
    });

    test('canSubmit requires subject and message >= 10 chars', () {
      // No subject, no message
      expect(provider.canSubmit, isFalse);

      // Subject only
      provider.setSubject('Bug Report');
      expect(provider.canSubmit, isFalse);

      // Subject + short message
      provider.setMessage('short');
      expect(provider.canSubmit, isFalse);

      // Subject + valid message
      provider.setMessage('This is a valid bug report message');
      expect(provider.canSubmit, isTrue);
    });

    test('reset clears all state', () {
      provider.setSubject('Bug Report');
      provider.setMessage('Some message text');
      provider.setAttachLogs(true);

      provider.reset();

      expect(provider.selectedSubject, isNull);
      expect(provider.message, isEmpty);
      expect(provider.attachLogs, isFalse);
      expect(provider.submitted, isFalse);
    });

    test('subjectCategories has expected values', () {
      expect(SupportProvider.subjectCategories, [
        'Bug Report',
        'Feature Request',
        'General Feedback',
        'Other',
      ]);
    });
  });
}
```

### Sub-phase 12.4: ConsentProvider Unit Tests
**Files:**
- Create: `test/features/settings/presentation/providers/consent_provider_test.dart`
**Agent:** qa-testing-agent

#### Step 12.4.1: Create ConsentProvider unit tests
**File:** `test/features/settings/presentation/providers/consent_provider_test.dart` (NEW)

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:construction_inspector/features/settings/presentation/providers/consent_provider.dart';
import 'package:construction_inspector/features/settings/data/repositories/consent_repository.dart';
import 'package:construction_inspector/features/settings/data/models/consent_record.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/shared/services/preferences_service.dart';

@GenerateMocks([ConsentRepository, AuthProvider, PreferencesService])
import 'consent_provider_test.mocks.dart';

void main() {
  late ConsentProvider provider;
  late MockConsentRepository mockConsentRepo;
  late MockAuthProvider mockAuthProvider;
  late MockPreferencesService mockPrefs;

  setUp(() {
    mockConsentRepo = MockConsentRepository();
    mockAuthProvider = MockAuthProvider();
    mockPrefs = MockPreferencesService();

    provider = ConsentProvider(
      preferencesService: mockPrefs,
      consentRepository: mockConsentRepo,
      authProvider: mockAuthProvider,
    );
  });

  group('loadConsentState', () {
    test('reads prefs and returns correct state when consent exists', () {
      when(mockPrefs.getBool('consent_accepted')).thenReturn(true);
      when(mockPrefs.getString('consent_policy_version'))
          .thenReturn(ConsentProvider.currentPolicyVersion);

      provider.loadConsentState();

      expect(provider.hasConsented, isTrue);
      expect(provider.hasEverConsented, isTrue);
      expect(provider.needsReconsent, isFalse);
    });

    test('reads prefs and returns false when no consent', () {
      when(mockPrefs.getBool('consent_accepted')).thenReturn(null);
      when(mockPrefs.getString('consent_policy_version')).thenReturn(null);

      provider.loadConsentState();

      expect(provider.hasConsented, isFalse);
      expect(provider.hasEverConsented, isFalse);
    });
  });

  group('acceptConsent', () {
    test('writes prefs AND inserts 2 ConsentRecords via repository', () async {
      when(mockPrefs.setBool(any, any)).thenAnswer((_) async {});
      when(mockPrefs.setString(any, any)).thenAnswer((_) async {});
      when(mockAuthProvider.userId).thenReturn('test-user-id');
      when(mockConsentRepo.recordConsent(any)).thenAnswer((_) async {});

      await provider.acceptConsent(appVersion: '0.1.0');

      // Verify prefs were written
      verify(mockPrefs.setBool('consent_accepted', true)).called(1);
      verify(mockPrefs.setString(
        'consent_policy_version',
        ConsentProvider.currentPolicyVersion,
      )).called(1);

      // Verify 2 ConsentRecord rows inserted (privacy_policy + terms_of_service)
      final captured = verify(mockConsentRepo.recordConsent(captureAny))
          .captured;
      expect(captured.length, 2);
      expect(
        (captured[0] as ConsentRecord).policyType,
        ConsentPolicyType.privacyPolicy,
      );
      expect(
        (captured[1] as ConsentRecord).policyType,
        ConsentPolicyType.termsOfService,
      );
    });
  });

  group('hasConsented', () {
    test('returns true after acceptance', () async {
      when(mockPrefs.setBool(any, any)).thenAnswer((_) async {});
      when(mockPrefs.setString(any, any)).thenAnswer((_) async {});
      when(mockAuthProvider.userId).thenReturn('test-user-id');
      when(mockConsentRepo.recordConsent(any)).thenAnswer((_) async {});

      await provider.acceptConsent(appVersion: '0.1.0');

      expect(provider.hasConsented, isTrue);
    });
  });

  group('needsReconsent', () {
    test('returns true when version mismatch', () {
      when(mockPrefs.getBool('consent_accepted')).thenReturn(true);
      when(mockPrefs.getString('consent_policy_version'))
          .thenReturn('0.9.0'); // old version

      provider.loadConsentState();

      expect(provider.needsReconsent, isTrue);
      expect(provider.hasConsented, isFalse); // current version not accepted
      expect(provider.hasEverConsented, isTrue);
    });
  });
}
```

NOTE: Run `pwsh -Command "flutter pub run build_runner build --delete-conflicting-outputs"` to generate the `.mocks.dart` file before running these tests.

### Sub-phase 12.5: Remove Dead Code (moved from old 12.4)
**Files:**
- Verify: `lib/features/settings/presentation/screens/settings_screen.dart`
**Agent:** general-purpose

#### Step 12.5.1: Verify showLicensePage is no longer used
The `showLicensePage()` call was in the old About section (lines 337-341) and was fully replaced in Phase 9 Step 9.2.2. Verify that no other references to `showLicensePage` exist in the codebase:

```
pwsh -Command "flutter analyze"
```

Search for any remaining `showLicensePage` references. If the import `import 'package:flutter/material.dart'` includes it implicitly (it does — it's part of material), that's fine. Just verify no call sites remain.

### Sub-phase 12.6: Final Verification
**Agent:** general-purpose

#### Step 12.6.1: Run full test suite
```
pwsh -Command "flutter test"
```

#### Step 12.6.2: Run full static analysis
```
pwsh -Command "flutter analyze"
```

#### Step 12.6.3: Verify assets are bundled
```
pwsh -Command "flutter pub get"
```

Confirm no errors about missing assets in `assets/legal/`.

### Sub-phase 12.8: Add Sync Deferral TODOs
**Agent:** general-purpose

#### Step 12.8.1: Add TODO comments for sync deferral
Add TODO comments in the following files to explicitly mark where sync integration would go:

**File:** `lib/features/settings/data/repositories/consent_repository.dart`
After the class declaration, add a comment:
```dart
// TODO: Sync integration for user_consent_records is deferred.
// This table is INSERT-only and upload-only (no pull/conflict resolution needed).
// When ready, add a SyncAdapter that pushes new consent records to Supabase
// on each sync cycle. See SyncOrchestrator for the pattern.
```

**File:** `lib/features/settings/data/repositories/support_repository.dart`
After the class declaration, add a comment:
```dart
// TODO: Sync integration for support_tickets is deferred.
// This table is INSERT-only from the client and upload-only (no bidirectional sync).
// Status updates come from the server side (admin dashboard).
// When ready, add a SyncAdapter that:
// 1. Pushes new local tickets to Supabase
// 2. Pulls status updates for existing tickets
```

**File:** `lib/features/settings/presentation/providers/support_provider.dart`
The `// TODO: Sync trigger for support_tickets` comment was already added in FIX-2.

> **NOTE:** Both `user_consent_records` and `support_tickets` are insert-only from the client perspective. This makes sync significantly simpler than bidirectional tables (no conflict resolution needed). Sync implementation is deferred to a follow-up plan.

---

## Summary of All New/Modified Files

### New Files (9)
| File | Phase | Agent |
|------|-------|-------|
| `lib/features/settings/presentation/providers/support_provider.dart` | 10 | frontend-flutter-specialist-agent |
| `lib/features/settings/presentation/screens/help_support_screen.dart` | 10 | frontend-flutter-specialist-agent |
| `lib/features/settings/presentation/screens/legal_document_screen.dart` | 11 | frontend-flutter-specialist-agent |
| `lib/features/settings/presentation/screens/oss_licenses_screen.dart` | 11 | frontend-flutter-specialist-agent |
| `lib/shared/testing_keys/support_keys.dart` | 10 | frontend-flutter-specialist-agent |
| `assets/legal/terms_of_service.md` | 11 | general-purpose |
| `assets/legal/privacy_policy.md` | 11 | general-purpose |
| `test/features/settings/about_section_test.dart` | 12 | qa-testing-agent |
| `test/features/settings/presentation/providers/consent_provider_test.dart` | 12 | qa-testing-agent |

### Modified Files (8)
| File | Phase | Change |
|------|-------|--------|
| `lib/shared/testing_keys/settings_keys.dart` | 9 | Add aboutTosTile, aboutPrivacyTile, aboutBuildNumber keys |
| `lib/shared/testing_keys/testing_keys.dart` | 10 | Add support_keys barrel export + facade |
| `lib/features/auth/presentation/providers/app_config_provider.dart` | 9 | Add buildNumber getter |
| `lib/features/settings/presentation/screens/settings_screen.dart` | 9 | Replace About section |
| `lib/features/settings/presentation/providers/providers.dart` | 10 | Add support_provider barrel export |
| `lib/features/settings/presentation/screens/screens.dart` | 10-11 | Add 3 barrel exports |
| `lib/core/router/app_router.dart` | 12 | Add 3 routes |
| `lib/main.dart` | 12 | Wire SupportProvider |
| `pubspec.yaml` | 10-11 | Add archive, flutter_markdown deps + legal assets |

### Dependencies Added
| Package | Version | Purpose |
|---------|---------|---------|
| `archive` | ^4.0.2 | Zip log files for support ticket attachment |
| `flutter_markdown` | ^0.7.6 | Render legal document markdown |

### Supabase Requirements (migration in Part 1 Phase 2.6)
- `support_tickets` table: id, user_id, subject, message, app_version, platform, log_file_path, created_at, status
- `user_consent_records` table: id, user_id, policy_type, policy_version, accepted_at, app_version
- `support-logs` Storage bucket with RLS policy (user can only upload to their own path)
- Sync for both tables is deferred — insert-only / upload-only (see Sub-phase 12.8)
