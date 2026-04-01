# Pattern: Router Redirect Gate

## How We Do It
AppRouter uses a single `redirect` callback in GoRouter that implements a sequential gate chain. Each gate checks a condition and returns a redirect path or `null` to continue. The gate order is security-critical: password recovery → auth check → force update → force reauth → consent → onboarding → profile completion → pending approval → admin guard → project guard. Currently, `ConsentProvider` is optional (nullable) and `AppConfigProvider` is read via `context.read` with try-catch — the spec makes all providers required.

## Exemplar

### AppRouter Constructor (`lib/core/router/app_router.dart:90-96`)
```dart
AppRouter({
  required AuthProvider authProvider,
  ConsentProvider? consentProvider,   // CURRENT: optional — spec says required
})  : _authProvider = authProvider,
     _consentProvider = consentProvider;
```

### Redirect Gate Chain (`lib/core/router/app_router.dart:155-340`)
```dart
redirect: (context, state) {
  // Gate 0: Config bypass (test mode, Supabase not configured)
  if (!SupabaseConfig.isConfigured || TestModeConfig.useMockAuth) { ... }

  // Gate 1: Password recovery deep link
  if (_authProvider.isPasswordRecovery) {
    if (location == '/update-password') return null;
    return '/update-password';
  }

  // Gate 2: Auth check (unauthenticated → login)
  if (!isAuthenticated && !isAuthRoute) return '/login';
  if (isAuthenticated && isAuthRoute) { ... return '/'; }

  // Gate 3: Force update (via context.read<AppConfigProvider>)
  // Gate 4: Force reauth (via context.read<AppConfigProvider>)
  if (isAuthenticated) {
    try {
      final appConfig = context.read<AppConfigProvider>();  // CURRENT: try-catch
      if (appConfig.requiresUpdate) { ... }
      if (appConfig.requiresReauth) { ... }
    } catch (e) {
      Logger.nav('AppConfigProvider not available in router: $e');
    }

    // Gate 5: Consent gate (via injected _consentProvider field)
    if (_consentProvider != null) {
      if (!_consentProvider.hasConsented) {
        if (location == '/consent') return null;
        return '/consent';
      }
    }
  }

  // Gate 6: Onboarding (profile-setup, company-setup, pending-approval)
  // Gate 7: Profile completion (null profile → profile-setup)
  // Gate 8: Pending approval / rejected / deactivated
  // Gate 9: Admin-only route guard
  // Gate 10: Project-required route guard
  ...
  return null;
},
```

### refreshListenable (`lib/core/router/app_router.dart:154-156`)
```dart
refreshListenable: _consentProvider != null
    ? Listenable.merge([_authProvider, _consentProvider])
    : _authProvider,
```

## Reusable Methods

| Method | File:Line | Signature | When to Use |
|--------|-----------|-----------|-------------|
| AppRouter constructor | app_router.dart:90 | `AppRouter({required AuthProvider, ConsentProvider?})` | Router creation |
| AppRouter.setInitialLocation | app_router.dart:98 | `void setInitialLocation(String location)` | Route restoration |
| AppRouter.isRestorableRoute | app_router.dart:105 | `static bool isRestorableRoute(String location)` | Route persistence check |
| AppRouter.router (getter) | app_router.dart:108 | `GoRouter get router` | Lazy router access |

## Imports
```dart
import 'package:go_router/go_router.dart';
import 'package:construction_inspector/core/router/app_router.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';
import 'package:construction_inspector/features/auth/presentation/providers/app_config_provider.dart';
import 'package:construction_inspector/features/settings/presentation/providers/consent_provider.dart';
import 'package:construction_inspector/core/config/supabase_config.dart';
import 'package:construction_inspector/core/config/test_mode_config.dart';
import 'package:construction_inspector/core/logging/logger.dart';
```
