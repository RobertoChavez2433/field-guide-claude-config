---
feature: auth
type: architecture
scope: User Authentication & Session Management
updated: 2026-02-13
---

# Auth Feature Architecture

## Data Model

### Core Entities

| Entity | Fields | Type | Notes |
|--------|--------|------|-------|
| **User** | id, email, emailConfirmed, createdAt, userMetadata | Supabase | Built-in user record |
| **AuthState** | session, user, error | Value Object | Current authentication state |
| **AuthSession** | accessToken, refreshToken, expiresIn, expiresAt | Supabase | Token management |

### Key Models

**User** (from Supabase):
- `id`: Unique user UUID
- `email`: User email address (unique)
- `emailConfirmed`: Boolean indicating email verification status
- `createdAt`: Account creation timestamp
- `userMetadata`: JSON object for custom user data (full_name, etc.)

**AuthSession**:
- `accessToken`: JWT for authenticated API requests
- `refreshToken`: Used to obtain new access token when expired
- `expiresIn`: Seconds until access token expires (typically 3600)
- `expiresAt`: Absolute expiration timestamp

**AuthState**:
- `session`: Current AuthSession (null if unauthenticated)
- `user`: Current User (null if unauthenticated)
- `error`: Error message from last failed operation

## Relationships

### Supabase Auth → App User (1-1)
```
Supabase Auth (remote)
    │
    ├─→ User record (id, email, emailConfirmed, metadata)
    │
    └─→ Session (access_token, refresh_token, expires_at)
        │
        ↓
    In-App User (AuthProvider)
        ├─→ currentUser: User?
        ├─→ isAuthenticated: bool
        └─→ authState: Stream<AuthState>
```

### Authentication Flow
```
Sign-In Form
    ↓
AuthService.signIn(email, password)
    ├─→ Supabase.auth.signInWithPassword()
    ├─→ Returns AuthResponse (session, user, error)
    │
    └─→ If success:
        ├─→ AuthProvider._user = user
        ├─→ AuthProvider._isLoading = false
        └─→ notifyListeners() → UI rebuilds

    └─→ If error:
        ├─→ AuthProvider._error = error message
        ├─→ AuthProvider._isLoading = false
        └─→ UI displays error to user
```

### Email Verification Flow
```
User clicks verification link in email
    │
    ├─→ Deep link: com.fvconstruction.construction_inspector://login-callback
    │   └─→ Query params include: access_token, refresh_token, expires_in
    │
    ├─→ App launched (or brought to foreground)
    │   └─→ DeepLinkHandler._handleDeepLink(uri)
    │
    ├─→ Supabase.auth.recoverSession(fragment)
    │   └─→ Extracts tokens from URL fragment
    │
    └─→ AuthProvider notified of session change
        └─→ user.emailConfirmed = true
```

## Repository Pattern

### AuthService

**Location**: `lib/features/auth/services/auth_service.dart`

```dart
class AuthService {
  final SupabaseClient? _client;

  // Properties
  bool get isConfigured
  User? get currentUser
  Stream<AuthState> get authStateChanges

  // Methods
  Future<AuthResponse> signUp({
    required String email,
    required String password,
    String? fullName,
  })

  Future<AuthResponse> signIn({
    required String email,
    required String password,
  })

  Future<void> signOut()

  Future<void> resetPassword(String email)
}
```

**Key Behavior**:
- `isConfigured`: Returns true only if SupabaseClient is initialized
- `signUp()`: Sends verification email (user must click link to confirm)
- `signIn()`: Returns session on success or throws AuthException on failure
- `resetPassword()`: Sends reset email with deep link callback
- All methods throw `StateError` if Supabase not configured

### Error Handling

**AuthException** (from Supabase):
- `message: String` - Supabase error message
- Common errors:
  - "Invalid login credentials" → "Invalid email or password" (user-friendly)
  - "Email not confirmed" → "Please verify your email first"
  - "User already registered" → "Email already in use"

**Parsing Pattern**:
```dart
try {
  await _authService.signIn(email, password);
} on AuthException catch (e) {
  final userMessage = _parseAuthError(e.message);
  _error = userMessage;
  notifyListeners();
}

String _parseAuthError(String message) {
  if (message.contains('Invalid login'))
    return 'Invalid email or password';
  if (message.contains('Email not confirmed'))
    return 'Please verify your email';
  return 'Authentication failed';
}
```

## State Management

### Provider Type: ChangeNotifier

**AuthProvider** (`lib/features/auth/presentation/providers/auth_provider.dart`):

```dart
class AuthProvider extends ChangeNotifier {
  final AuthService _authService;

  // State
  User? _user;
  bool _isLoading = false;
  String? _error;

  // Getters
  User? get user => _user;
  bool get isAuthenticated => _user != null;
  bool get isLoading => _isLoading;
  String? get error => _error;

  // Methods
  Future<void> signUp(String email, String password, String fullName)
  Future<void> signIn(String email, String password)
  Future<void> signOut()
  Future<void> resetPassword(String email)
  Future<void> clearError()
}
```

### Initialization Lifecycle

```
App Start
    ↓
AuthProvider instantiated
    ├─→ Listens to authService.authStateChanges stream
    │   └─→ onAuthStateChange event for each status change
    │
    └─→ AuthService initializes Supabase session
        ├─→ If token exists on device: Refresh and restore
        ├─→ If token expired: Request new token
        └─→ If no token: User is unauthenticated

App Initialization
    ↓
Check isAuthenticated
    ├─→ true: Navigate to Dashboard
    └─→ false: Navigate to LoginScreen
```

### Sign-In Flow

```
LoginScreen → User enters email, password
    ↓
User taps "Sign In"
    ├─→ authProvider._isLoading = true
    ├─→ notifyListeners() → UI shows loading spinner
    │
    ├─→ authService.signIn(email, password)
    │   └─→ POST /auth/v1/token (Supabase)
    │
    ├─→ If success:
    │   ├─→ authProvider._user = user
    │   ├─→ authProvider._error = null
    │   ├─→ authProvider._isLoading = false
    │   ├─→ notifyListeners()
    │   └─→ Router navigates to Dashboard
    │
    └─→ If error:
        ├─→ authProvider._error = parsed message
        ├─→ authProvider._isLoading = false
        ├─→ notifyListeners()
        └─→ UI displays error snackbar
```

### Session Persistence

```
App Killed
    │
    └─→ Access token lost from memory
        But refresh token persists in secure storage

App Relaunched
    │
    ├─→ SupabaseClient initializes
    ├─→ Reads refresh token from secure storage
    ├─→ Calls auth.refreshSession()
    │   └─→ POST /auth/v1/token with refresh_token
    │
    ├─→ If success:
    │   ├─→ New access token obtained
    │   └─→ Session restored
    │
    └─→ If refresh fails:
        └─→ User prompted to re-authenticate
```

## Offline Behavior

### During Authentication (Requires Network)
- All auth operations require connectivity
- Offline sign-in not supported (no biometric or cached password)
- Error handling: Display "No internet connection" message

### After Authentication (Offline-Safe)
- **Session in Memory**: Access token cached in AuthProvider
- **Token Refresh Deferred**: If token expires offline, refresh attempted on reconnect
- **Session Info Accessible**: currentUser, isAuthenticated accessible offline

### On Reconnect
- Automatic token refresh if close to expiration
- Silent refresh (no user interruption)
- If refresh fails: User signed out and prompted to re-authenticate

## Testing Strategy

### Unit Tests (Service-level)
- **AuthService**: Mock SupabaseClient, verify method calls + error handling
- **Password reset**: Verify email sent correctly with redirect URL
- **Session recovery**: Mock token storage, verify refresh logic

Location: `test/features/auth/services/`

### Widget Tests (Provider-level)
- **AuthProvider**: Mock AuthService, trigger sign-in/out, verify state updates
- **Error display**: Verify error messages shown correctly
- **Loading state**: Verify spinner displays during async operations

Location: `test/features/auth/presentation/`

### Integration Tests (Deep Linking)
- **Email verification link**: Simulate deep link callback, verify session restored
- **Password reset link**: Simulate reset flow, verify user able to set new password

Location: `test/features/auth/integration/`

### Test Coverage
- ≥ 85% for AuthService (high-criticality security code)
- 100% for error parsing logic (must handle all Supabase errors)
- 80% for UI layer (widget tests only needed for critical flows)

## Performance Considerations

### Target Response Times
- Sign-in: < 3 seconds (network-dependent)
- Token refresh: < 1 second (cached token available)
- Sign-out: < 500 ms (local operation only)

### Memory Constraints
- Session in memory: ~1-2 KB (token strings + user metadata)
- Secure storage: ~4-5 KB (tokens)

### Optimization Opportunities
- Pre-emptive token refresh (refresh 1 minute before expiration)
- Session caching in SQLite (optional, for offline recovery)
- Lazy load user metadata (if heavy custom data added to userMetadata)

## File Locations

```
lib/features/auth/
├── services/
│   ├── services.dart               # Barrel export
│   └── auth_service.dart           # Supabase authentication service
│
├── presentation/
│   ├── providers/
│   │   ├── providers.dart          # Barrel export
│   │   └── auth_provider.dart      # ChangeNotifier for UI state
│   │
│   └── screens/
│       ├── screens.dart            # Barrel export
│       ├── login_screen.dart       # Sign-in UI
│       ├── register_screen.dart    # Sign-up UI
│       └── forgot_password_screen.dart  # Password reset UI
│
└── auth.dart                       # Feature entry point (barrel export)

lib/core/config/
└── supabase_config.dart           # SupabaseClient initialization

lib/core/router/
└── app_router.dart                # Deep link handling for auth callbacks
```

### Import Pattern

```dart
// Within auth feature
import 'package:construction_inspector/features/auth/services/auth_service.dart';
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

// From other features
import 'package:construction_inspector/features/auth/presentation/providers/auth_provider.dart';

// Barrel export
import 'package:construction_inspector/features/auth/auth.dart';
```

### Deep Linking Configuration

**Android** (`android/app/src/main/AndroidManifest.xml`):
```xml
<intent-filter>
  <action android:name="android.intent.action.VIEW"/>
  <category android:name="android.intent.category.DEFAULT"/>
  <category android:name="android.intent.category.BROWSABLE"/>
  <data
    android:scheme="com.fvconstruction.construction_inspector"
    android:host="login-callback"/>
</intent-filter>
```

**iOS** (`ios/Runner/Info.plist`):
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>com.fvconstruction.construction_inspector</string>
    </array>
  </dict>
</array>
```

**Callback Handler** (in app_router.dart):
```dart
void _handleDeepLink(Uri uri) async {
  if (uri.scheme == 'com.fvconstruction.construction_inspector' &&
      uri.host == 'login-callback') {
    final fragment = uri.fragment;
    if (fragment.contains('access_token')) {
      await Supabase.instance.client.auth.recoverSession(fragment);
    }
  }
}
```
