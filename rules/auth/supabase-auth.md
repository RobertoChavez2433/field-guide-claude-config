---
paths:
  - "lib/features/auth/**/*.dart"
  - "lib/core/config/supabase_config.dart"
---

# Auth Service Guidelines

## Common Commands
```bash
npx supabase status               # Check Supabase status
npx supabase db reset             # Reset database (dev only!)
npx supabase functions list       # List edge functions
```

## Code Style

### AuthService Pattern
```dart
class AuthService {
  final SupabaseClient _client;

  Stream<AuthState> authStateChanges() {
    return _client.auth.onAuthStateChange.map((data) => data.session);
  }

  Future<AuthResponse> signIn(String email, String password) async {
    return await _client.auth.signInWithPassword(
      email: email,
      password: password,
    );
  }

  Future<AuthResponse> signUp(String email, String password) async {
    return await _client.auth.signUp(
      email: email,
      password: password,
    );
  }

  Future<void> signOut() async {
    await _client.auth.signOut();
  }

  Future<void> resetPassword(String email) async {
    await _client.auth.resetPasswordForEmail(email);
  }

  User? get currentUser => _client.auth.currentUser;
}
```

### AuthProvider Pattern
```dart
class AuthProvider extends ChangeNotifier {
  final AuthService _authService;
  User? _user;
  bool _isLoading = false;
  String? _error;

  AuthProvider(this._authService) {
    _authService.authStateChanges().listen((session) {
      _user = session?.user;
      notifyListeners();
    });
  }

  bool get isAuthenticated => _user != null;
  User? get user => _user;
}
```

## State Management

### Auth State Flow
```
App Start -> Check Session ->
  -> Has Session -> Load User -> Home
  -> No Session -> Login Screen
```

### Protected Routes
```dart
redirect: (context, state) {
  final isAuthenticated = ref.read(authProvider).isAuthenticated;
  if (!isAuthenticated && !publicRoutes.contains(state.location)) {
    return '/login';
  }
  return null;
}
```

## Deep Linking

### Callback URL
```
com.fieldguideapp.inspector://login-callback
```

> **Important**: Deep link token exchange is handled by `supabase_flutter` when
> `AuthFlowType.pkce` is configured. Do not add custom deep link handlers.
> The library intercepts the deep link, exchanges the PKCE code for tokens,
> and fires the appropriate `AuthChangeEvent` (e.g., `passwordRecovery`).

### PASSWORD_RECOVERY Event Pattern
```dart
// In AuthProvider — listen for recovery event BEFORE updating _currentUser
_authSubscription = _authService.authStateChanges.listen((state) {
  if (state.event == AuthChangeEvent.passwordRecovery) {
    _isPasswordRecovery = true;
    _currentUser = state.session?.user;
    notifyListeners();
    return; // Skip profile load — user must update password first
  }
  // ... normal auth state handling
});
```

## Security

### Token Storage
- Use `flutter_secure_storage` for tokens
- Never log tokens or credentials
- Clear on sign out

### Password Requirements
- Minimum 8 characters
- Handled by Supabase (configurable)

### Rate Limiting
- Configure in Supabase dashboard
- Handle 429 errors gracefully

## Error Handling
```dart
try {
  await _authService.signIn(email, password);
} on AuthException catch (e) {
  _error = _parseAuthError(e.message);
  notifyListeners();
}

String _parseAuthError(String message) {
  if (message.contains('Invalid login')) return 'Invalid email or password';
  if (message.contains('Email not confirmed')) return 'Please verify your email';
  return 'Authentication failed';
}
```

## Logging
```dart
debugPrint('AUTH: User signed in: ${user?.email}');
// NEVER log passwords or tokens
```

## Debugging
```dart
// Check current session
debugPrint('Session: ${Supabase.instance.client.auth.currentSession}');
// Check user
debugPrint('User: ${Supabase.instance.client.auth.currentUser?.email}');
```

## Pull Request Template
```markdown
## Auth Changes
- [ ] Auth flow affected: Login/Register/Reset/Logout
- [ ] Deep linking tested
- [ ] Token handling secure
- [ ] Error messages user-friendly

## Security Checklist
- [ ] No credentials in logs
- [ ] No hardcoded secrets
- [ ] Rate limiting considered
- [ ] Session handling correct
```
