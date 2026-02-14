---
feature: settings
type: architecture
scope: User Preferences & Theme Management
updated: 2026-02-13
---

# Settings Feature Architecture

## Data Model

### Core Entities

Settings has **minimal persistent models**. Most data is UI state or references from other features.

| Entity | Fields | Type | Notes |
|--------|--------|------|-------|
| **ThemeMode** | light, dark, system | Enum | App theme preference |
| **InspectorProfile** | name, email, phone, organization | Value Object | User profile (from auth + local cache) |

### Key Models

**ThemeMode**:
- `light` - Always light theme
- `dark` - Always dark theme
- `system` - Follow device system theme (default)

**InspectorProfile** (cached from auth):
- `name`: Inspector display name
- `email`: From auth provider
- `phone`: Optional contact phone
- `organization`: Optional organization/company name

## Relationships

```
SettingsScreen (read-only aggregation)
    ├─→ ThemeProvider (theme preference)
    ├─→ AuthProvider (current user, sign-out)
    ├─→ SyncProvider (pending data count, sync history)
    ├─→ ContractorProvider (personnel types for project)
    └─→ Shared Preferences (theme persistence, user metadata)
```

## State Management

### Provider Type: ChangeNotifier

**ThemeProvider** (`lib/features/settings/presentation/providers/theme_provider.dart`):

```dart
class ThemeProvider extends ChangeNotifier {
  // State
  ThemeMode _themeMode = ThemeMode.system;

  // Getters
  ThemeMode get themeMode => _themeMode;
  ThemeData get lightTheme => AppTheme.lightTheme;
  ThemeData get darkTheme => AppTheme.darkTheme;

  // Methods
  Future<void> setThemeMode(ThemeMode mode)
  Future<void> loadSavedTheme()
  bool get isDarkMode => _themeMode == ThemeMode.dark ||
      (_themeMode == ThemeMode.system && _isSystemDark);
}
```

### Initialization Lifecycle

```
App Start
    ↓
main() initializes providers
    ├─→ ThemeProvider.loadSavedTheme()
    │   ├─→ Reads Shared Preferences for saved theme
    │   ├─→ If not found: defaults to system theme
    │   ├─→ _themeMode = savedMode
    │   └─→ notifyListeners() → MaterialApp rebuilds with theme
    │
    └─→ SettingsProvider (lazy-loaded when navigating to settings)
        └─→ Loads user profile, sync status on demand
```

### Theme Change Flow

```
Settings Screen Loaded
    ↓
User toggles theme
    ├─→ ThemeProvider.setThemeMode(newMode) called
    │   ├─→ _themeMode = newMode
    │   ├─→ Saves to Shared Preferences
    │   └─→ notifyListeners() → MaterialApp rebuilds with new theme
    │
    └─→ App immediately reflects theme change
        └─→ All screens rebuild with new colors
```

### Settings UI Pattern

**SettingsScreen** (StatefulWidget, no dedicated provider):

```dart
class SettingsScreen extends StatefulWidget {
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  // Depends on other features' providers
  late AuthProvider _authProvider;
  late SyncProvider _syncProvider;
  late ThemeProvider _themeProvider;

  @override
  void initState() {
    super.initState();
    _authProvider = context.read<AuthProvider>();
    _syncProvider = context.read<SyncProvider>();
    _themeProvider = context.read<ThemeProvider>();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        // Profile section (from auth)
        Consumer<AuthProvider>(
          builder: (context, auth, _) {
            return InspectorProfileSection(
              name: auth.user?.email ?? 'Unknown',
              email: auth.user?.email,
            );
          },
        ),

        // Theme section (from theme provider)
        Consumer<ThemeProvider>(
          builder: (context, theme, _) {
            return ThemeSection(
              selectedTheme: theme.themeMode,
              onThemeChanged: _themeProvider.setThemeMode,
            );
          },
        ),

        // Sync status section (from sync provider)
        Consumer<SyncProvider>(
          builder: (context, sync, _) {
            return SyncSection(
              pendingCount: sync.pendingItemCount,
              lastSyncTime: sync.lastSyncTime,
            );
          },
        ),

        // Actions
        SignOutButton(),
        ClearCacheButton(),
      ],
    );
  }
}
```

## Offline Behavior

**Mostly offline**: Theme changes and profile display happen offline. Sign-out and cache operations have network/local trade-offs.

### Read Path (Offline)
- Theme preference read from Shared Preferences
- User profile read from auth provider (cached in memory)
- Sync status read from sync provider
- All operations local

### Write Path (Offline)
- Theme changes written immediately to Shared Preferences
- Profile edits cached locally; sync to cloud deferred
- Cache clear is immediate (destructive)

### Theme Persistence
- Saved to Shared Preferences on every change
- Survives app kill/restart
- Default is system theme if not explicitly set

## Testing Strategy

### Unit Tests (Provider-level)
- **ThemeProvider**: Save/load theme, toggle modes, verify notifications
- **Theme persistence**: Write to Shared Preferences, read back
- **Default theme**: System theme applied if not saved

Location: `test/features/settings/presentation/providers/theme_provider_test.dart`

### Widget Tests (Screen-level)
- **SettingsScreen**: Verify sections displayed (profile, theme, sync, actions)
- **Theme toggle**: Change theme → verify MaterialApp rebuilds
- **Profile display**: Verify user email shown
- **Sign-out button**: Tap → calls AuthProvider.signOut()

Location: `test/features/settings/presentation/screens/settings_screen_test.dart`

### Integration Tests
- **Theme persistence**: Change theme → restart app → theme persists
- **Profile editing**: Edit name → save → verify persisted
- **Sync status**: Pending items shown, refresh updates count

Location: `test/features/settings/presentation/integration/`

### Test Coverage
- ≥ 90% for provider (theme persistence is critical)
- ≥ 80% for screens (UI layer)
- Mock auth, sync, and other feature providers

## Performance Considerations

### Target Response Times
- Load settings screen: < 300 ms (read from Shared Preferences)
- Change theme: < 100 ms (save + notify listeners)
- Clear cache: < 1 second (depends on cache size)

### Memory Constraints
- Theme preference: ~50 bytes
- User profile cache: ~500 bytes
- Settings state: minimal

### Optimization Opportunities
- Lazy-load sync status (not needed immediately)
- Batch profile updates (if fields editable)
- Background cache cleanup (if cache clearing added)

## File Locations

```
lib/features/settings/
├── presentation/
│   ├── screens/
│   │   ├── screens.dart
│   │   ├── settings_screen.dart
│   │   └── personnel_types_screen.dart
│   │
│   ├── widgets/
│   │   ├── widgets.dart
│   │   ├── theme_section.dart
│   │   ├── sync_section.dart
│   │   ├── inspector_profile_section.dart
│   │   ├── section_header.dart
│   │   ├── clear_cache_dialog.dart
│   │   ├── edit_inspector_dialog.dart
│   │   └── sign_out_dialog.dart
│   │
│   ├── providers/
│   │   ├── providers.dart
│   │   └── theme_provider.dart
│   │
│   └── presentation.dart
│
└── settings.dart                     # Feature entry point

lib/core/theme/
├── app_theme.dart                    # Theme constants and ThemeData
└── app_colors.dart                   # Color palette

lib/core/config/
└── shared_preferences_config.dart    # Shared Preferences setup
```

### Import Pattern

```dart
// Within settings feature
import 'package:construction_inspector/features/settings/presentation/providers/theme_provider.dart';

// Theme constants
import 'package:construction_inspector/core/theme/app_theme.dart';

// From other features (read-only)
import 'package:construction_inspector/features/auth/auth.dart';
import 'package:construction_inspector/features/sync/sync.dart';

// Barrel export
import 'package:construction_inspector/features/settings/settings.dart';
```

