# Pattern: Consent/Support Factory

## How We Do It
`createConsentAndSupportProviders()` is a standalone factory function that creates `ConsentProvider` and `SupportProvider` with their full datasource/repository wiring. It returns a `ConsentSupportResult` record. This was extracted as an H1 fix to eliminate duplication between `main.dart` and `main_driver.dart`. The spec plans to absorb this into `AppBootstrap.configure()`.

## Exemplar

### ConsentSupportResult (`lib/features/settings/di/consent_support_factory.dart:16-24`)
```dart
class ConsentSupportResult {
  final ConsentProvider consentProvider;
  final SupportProvider supportProvider;

  const ConsentSupportResult({
    required this.consentProvider,
    required this.supportProvider,
  });
}
```

### createConsentAndSupportProviders (`lib/features/settings/di/consent_support_factory.dart:29-55`)
```dart
ConsentSupportResult createConsentAndSupportProviders({
  required DatabaseService dbService,
  required PreferencesService preferencesService,
  required AuthProvider authProvider,
  SupabaseClient? supabaseClient,
}) {
  final consentLocalDatasource = ConsentLocalDatasource(dbService);
  final consentRepository = ConsentRepository(consentLocalDatasource);
  final consentProvider = ConsentProvider(
    preferencesService: preferencesService,
    consentRepository: consentRepository,
    authProvider: authProvider,
  );

  final supportLocalDatasource = SupportLocalDatasource(dbService);
  final supportRepository = SupportRepository(supportLocalDatasource);
  final logUploadDatasource = LogUploadRemoteDatasource(supabaseClient);
  final supportProvider = SupportProvider(
    supportRepository: supportRepository,
    logUploadDatasource: logUploadDatasource,
  );

  return ConsentSupportResult(
    consentProvider: consentProvider,
    supportProvider: supportProvider,
  );
}
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| createConsentAndSupportProviders | consent_support_factory.dart:29 | `ConsentSupportResult createConsentAndSupportProviders({...})` | Creating consent + support providers |

## Imports
```dart
import 'package:construction_inspector/features/settings/di/consent_support_factory.dart';
import 'package:construction_inspector/core/database/database_service.dart';
import 'package:construction_inspector/shared/services/preferences_service.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
```
