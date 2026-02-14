---
feature: settings
type: overview
scope: User Preferences & Theme Management
updated: 2026-02-13
---

# Settings Feature Overview

## Purpose

The Settings feature manages user preferences and app configuration. It enables inspectors to customize app appearance (theme), manage their profile information, view sync status, and trigger account actions (sign-out, cache clear). Settings are persisted locally and synchronized with cloud backend when applicable.

## Key Responsibilities

- **Theme Management**: Toggle between light and dark themes, persist preference
- **Inspector Profile**: View and edit inspector name and contact information
- **Sync Status Display**: Show pending data ready for sync, sync history
- **Cache Management**: Clear cached data including photos and offline content
- **Account Management**: Sign out, view authentication status
- **Personnel Types Management**: Create and manage custom personnel categories per project
- **App Information**: Display version, environment, diagnostics information

## Key Files

| File Path | Purpose |
|-----------|---------|
| `lib/features/settings/presentation/providers/theme_provider.dart` | Theme state management |
| `lib/features/settings/presentation/screens/settings_screen.dart` | Main settings UI |
| `lib/features/settings/presentation/screens/personnel_types_screen.dart` | Personnel type management |
| `lib/features/settings/presentation/widgets/theme_section.dart` | Theme toggle widget |
| `lib/features/settings/presentation/widgets/sync_section.dart` | Sync status display |
| `lib/features/settings/presentation/widgets/inspector_profile_section.dart` | Profile management |

## Data Sources

- **Shared Preferences**: Persists theme preference and user metadata
- **SQLite**: Personnel types and project-specific settings
- **Auth**: Current user profile from `auth` feature
- **Sync Status**: Pending items count from sync feature

## Integration Points

**Depends on:**
- `auth` - Current user profile and sign-out
- `sync` - Pending data count and sync status
- `contractors` - Personnel type data for project
- `core/theme` - Theme constants and styling

**Required by:**
- All features - Theme provider affects app-wide styling
- `dashboard` - Settings access from main menu

## Offline Behavior

Settings are **fully offline-capable**. All preferences stored locally in Shared Preferences or SQLite. Theme changes apply immediately offline. Sign-out requires network (via `auth` feature). Cache operations and sync status are local. Inspectors can manage settings entirely offline; account actions requiring network handled separately.

## Edge Cases & Limitations

- **Theme Persistence**: Theme preference persists across app kills; default is system theme
- **Profile Editing**: Profile fields cached locally; sync to cloud backend is eventual
- **Personnel Types**: Project-scoped; not shared across projects
- **Cache Clearing**: Clears local photos and offline data; recovery requires re-sync
- **Sync Status**: Display only; actual sync triggered separately from `sync` feature
- **Sign-Out**: Requires network; offline sign-out not supported

## Detailed Specifications

See `architecture-decisions/settings-constraints.md` for:
- Hard rules on theme persistence and default behavior
- Cache clearing policies and data recovery semantics
- Profile field validation and sync behavior

See `rules/frontend/flutter-ui.md` for:
- Theme constants and color palette
- Settings screen layout and component standards

