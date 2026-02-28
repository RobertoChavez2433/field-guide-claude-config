# Security Agent Memory

## Baseline Audit (2026-02-27)

First audit performed via manual exploration + web research. Established baseline findings.

### Critical Findings
1. Hardcoded Supabase credentials in `supabase_config.dart:14,22` (defaultValue fallbacks)
2. RLS policies in `supabase_schema_v4_rls.sql` grant full CRUD to `anon` on 13 tables

### High Findings
3. `.env.local` contains plaintext production credentials + E2E password
4. `flutter_secure_storage` in pubspec but zero usages in `lib/`
5. SQLite (`sqflite`) has no encryption — PII at rest in plaintext
6. `base_remote_datasource.dart` `getAll()` with null companyId returns all rows cross-tenant
7. Custom URI scheme deep link hijackable on Android < 12

### Patterns Discovered
- PII stored in SharedPreferences: inspector name, initials, phone, cert number (seen in `PreferencesService`, `pdf_data_builder.dart`)
- Deep link URI with access token logged via `debugPrint` at `main.dart:486`
- `PRAGMA foreign_keys = ON` never set in `database_service.dart`
- Release build uses debug signing key (`signingConfigs.getByName("debug")`)
- `isMinifyEnabled` not set in release build type
- `proguard-rules.pro` is empty

### Frequently Referenced Files
| File | Security Relevance |
|------|-------------------|
| `lib/core/config/supabase_config.dart` | Hardcoded credentials |
| `lib/core/database/database_service.dart` | Unencrypted SQLite, missing FK pragma |
| `lib/features/auth/presentation/providers/auth_provider.dart` | Session handling |
| `lib/shared/datasources/base_remote_datasource.dart` | Null companyId bypass |
| `lib/main.dart` | Deep link token logging |
| `android/app/src/main/AndroidManifest.xml` | Permissions, backup, deep links |
| `android/app/build.gradle.kts` | Release build config |
| `supabase/supabase_schema_v4_rls.sql` | Permissive anon RLS |
| `lib/services/photo_service.dart` | EXIF not stripped, filename sanitization |

### Stack-Specific CVEs Tracked
| CVE | Package | Status |
|-----|---------|--------|
| CVE-2025-48757 | Supabase RLS bypass (Lovable) | Pattern present in our v4 schema |
| CVE-2024-29887 | serverpod_client cert bypass | Not affected (don't use serverpod) |
