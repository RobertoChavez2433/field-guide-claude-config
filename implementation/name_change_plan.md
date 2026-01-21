# App Name Change Plan: Construction Inspector → Field Guide

**Last Updated**: 2026-01-21
**Status**: READY FOR REVIEW
**Scope**: Change display names and user-facing text from "Construction Inspector" to "Field Guide"

---

## Executive Summary

This plan documents all locations where the app name "Construction Inspector" appears and provides a step-by-step approach to changing it to "Field Guide". The plan is divided into two strategies:

1. **Recommended Approach**: Change only display names (non-breaking)
2. **Full Rebrand Approach**: Change package name and bundle IDs (breaking change)

**Recommendation**: Use the **Recommended Approach** to avoid breaking changes to existing installations, deep links, and platform-specific configurations.

---

## Package Name Decision

### Current Package Structure
- **Dart Package**: `construction_inspector`
- **Android Package**: `com.fvconstruction.construction_inspector`
- **iOS Bundle ID**: `com.fvconstruction.constructionInspector`
- **Deep Link Scheme**: `com.fvconstruction.construction_inspector`

### Strategy 1: Display Name Only (RECOMMENDED)
**What Changes**: User-visible app names, titles, documentation
**What Stays**: Package names, bundle IDs, deep link schemes, file paths
**Impact**: Non-breaking, existing installations unaffected
**Effort**: Low (30 files, ~2 hours)

### Strategy 2: Full Rebrand
**What Changes**: Everything including package names and bundle IDs
**What Stays**: Nothing
**Impact**: Breaking change, requires new app installation
**Effort**: High (187+ files, ~8-12 hours)
**Risks**:
- Breaks existing installations
- Requires database migration path
- Deep link URLs change
- Platform-specific reconfigurations
- Extensive testing required

**RECOMMENDATION**: Use **Strategy 1** unless there is a business requirement for complete rebranding.

---

## Strategy 1: Display Name Changes (RECOMMENDED)

### Phase 1: Platform Configuration Files

#### 1.1 Android Configuration

**File**: `android/app/src/main/AndroidManifest.xml`
- **Line 20**: Change `android:label="construction_inspector"` to `android:label="Field Guide"`
- **Impact**: Changes app name shown in Android launcher and app drawer

**File**: `android/app/build.gradle.kts`
- **Lines 9, 24**: Keep `com.fvconstruction.construction_inspector` (no change)
- **Rationale**: Changing applicationId breaks existing installations

#### 1.2 iOS Configuration

**File**: `ios/Runner/Info.plist`
- **Line 8**: Change `<string>Construction Inspector</string>` to `<string>Field Guide</string>` (CFBundleDisplayName)
- **Line 16**: Keep `<string>construction_inspector</string>` (CFBundleName - internal identifier)
- **Impact**: Changes app name shown in iOS home screen

**File**: `ios/Runner.xcodeproj/project.pbxproj`
- **Lines 371, 550, 572**: Keep `com.fvconstruction.constructionInspector` (no change)
- **Rationale**: Changing bundle ID breaks existing installations

#### 1.3 Windows Configuration

**File**: `windows/runner/main.cpp`
- **Line 30**: Change `L"construction_inspector"` to `L"Field Guide"`
- **Impact**: Changes Windows window title

**File**: `windows/runner/Runner.rc`
- **Line 92**: Keep `"com.fvconstruction"` (no change)
- **Line 93**: Change `"FileDescription", "construction_inspector"` to `"FileDescription", "Field Guide"`
- **Line 95**: Keep `"InternalName", "construction_inspector"` (no change)
- **Line 98**: Change `"ProductName", "construction_inspector"` to `"ProductName", "Field Guide"`
- **Impact**: Changes Windows executable properties

**File**: `windows/CMakeLists.txt`
- **Line 3**: Keep `project(construction_inspector LANGUAGES CXX)` (no change)
- **Line 7**: Keep `set(BINARY_NAME "construction_inspector")` (no change)
- **Rationale**: Internal build identifiers, not user-facing

#### 1.4 Web Configuration

**File**: `web/index.html`
- **Line 26**: Change `<meta name="apple-mobile-web-app-title" content="construction_inspector">` to `content="Field Guide"`
- **Line 32**: Change `<title>construction_inspector</title>` to `<title>Field Guide</title>`
- **Impact**: Changes web page title and PWA name

**File**: `web/manifest.json`
- **Line 2**: Change `"name": "construction_inspector"` to `"name": "Field Guide"`
- **Line 3**: Change `"short_name": "construction_inspector"` to `"short_name": "Field Guide"`
- **Line 8**: Change `"description": "A new Flutter project."` to `"description": "Construction field inspection and daily reporting app."`
- **Impact**: Changes PWA manifest for web installations

#### 1.5 Flutter Configuration

**File**: `pubspec.yaml`
- **Line 1**: Keep `name: construction_inspector` (no change)
- **Line 2**: Change `description: "Construction Inspector Daily Report App - Track field activities, quantities, and generate professional PDF reports."` to `description: "Field Guide - Track field activities, quantities, and generate professional PDF reports."`
- **Rationale**: Package name must stay for imports to work

### Phase 2: Dart Code Changes

#### 2.1 Main Application

**File**: `lib/main.dart`
- **Line 110**: Keep `ConstructionInspectorApp` class name (no change)
- **Line 153**: Keep deep link scheme `com.fvconstruction.construction_inspector` (no change)
- **Line 184**: Keep `ConstructionInspectorApp` class name (no change)
- **Line 264**: Change `title: 'Construction Inspector'` to `title: 'Field Guide'`
- **Impact**: Changes app title shown in Flutter

#### 2.2 Feature Screens

**File**: `lib/features/auth/presentation/screens/login_screen.dart`
- **Line 71**: Change `'Construction Inspector'` to `'Field Guide'`
- **Impact**: Changes app name on login screen

**File**: `lib/features/settings/presentation/screens/settings_screen.dart`
- **Line 413**: Change `applicationName: 'Construction Inspector'` to `applicationName: 'Field Guide'`
- **Impact**: Changes app name in About dialog

#### 2.3 Code Comments

**File**: `lib/core/theme/app_theme.dart`
- **Line 4**: Change `/// Modern, field-optimized theme system for Construction Inspector App` to `/// Modern, field-optimized theme system for Field Guide App`

**File**: `lib/core/transitions/page_transitions.dart`
- **Line 4**: Change `/// Custom page transitions for the Construction Inspector App` to `/// Custom page transitions for the Field Guide App`

### Phase 3: Testing Configuration

**File**: `patrol.yaml`
- **Line 1**: Change `app_name: Construction Inspector` to `app_name: Field Guide`
- **Lines 3, 5**: Keep package/bundle IDs (no change)
- **Impact**: Updates test configuration display name

### Phase 4: Documentation

#### 4.1 Project Documentation

**File**: `README.md`
- **Line 1**: Change `# Construction Inspector App` to `# Field Guide App`
- **Line 3**: Change "Cross-platform mobile/desktop app for construction inspectors" to remain (describes purpose, not brand)
- **Line 89**: Change `Proprietary - FV Construction` (keep as-is or update if needed)

#### 4.2 Claude Configuration

**File**: `.claude/CLAUDE.md`
- **Line 1**: Change `# Construction Inspector App` to `# Field Guide App`
- **Note**: Keep feature descriptions as they explain functionality

**File**: `.claude/agents/planning-agent.md`
- **Line 9**: Change `Construction Inspector App` to `Field Guide App`

**File**: `.claude/agents/backend/data-layer-agent.md`
- **Line 18**: Change `Construction Inspector App` to `Field Guide App`

**File**: `.claude/agents/backend/supabase-agent.md`
- **Line 27**: Change `Construction Inspector App` to `Field Guide App`

**File**: `.claude/agents/auth/auth-agent.md`
- **Lines 10, 26**: Change `Construction Inspector App` to `Field Guide App`

**File**: `.claude/agents/pdf-agent.md`
- **Line 10**: Change `Construction Inspector App` to `Field Guide App`

**File**: `.claude/agents/frontend/flutter-specialist-agent.md`
- **Lines 3, 13**: Change `Construction Inspector App` to `Field Guide App`

**File**: `.claude/docs/architectural_patterns.md`
- **Line 5**: Change `Construction Inspector app` to `Field Guide app`

**File**: `.claude/docs/manual-testing-checklist.md`
- **Line 2**: Change `## Construction Inspector App` to `## Field Guide App`

**File**: `.claude/implementation/implementation_plan.md`
- **Line 8**: Already says "Field Guide (Construction Inspector App)" - change to just "Field Guide"

**File**: `.claude/implementation/AASHTOWARE_Implementation_Plan.md`
- **Lines 12, 75**: Change `Construction Inspector App` to `Field Guide App`

---

## File Summary Table

### Critical Platform Files (Must Change)
| File | Line(s) | Current Value | New Value | Impact |
|------|---------|---------------|-----------|--------|
| `android/app/src/main/AndroidManifest.xml` | 20 | `android:label="construction_inspector"` | `android:label="Field Guide"` | Android launcher name |
| `ios/Runner/Info.plist` | 8 | `<string>Construction Inspector</string>` | `<string>Field Guide</string>` | iOS home screen name |
| `windows/runner/main.cpp` | 30 | `L"construction_inspector"` | `L"Field Guide"` | Windows title bar |
| `windows/runner/Runner.rc` | 93, 98 | `"construction_inspector"` | `"Field Guide"` | Windows exe properties |
| `web/index.html` | 26, 32 | `construction_inspector` | `Field Guide` | Web page title |
| `web/manifest.json` | 2, 3, 8 | `construction_inspector` | `Field Guide` | PWA manifest |
| `lib/main.dart` | 264 | `'Construction Inspector'` | `'Field Guide'` | App title |
| `lib/features/auth/presentation/screens/login_screen.dart` | 71 | `'Construction Inspector'` | `'Field Guide'` | Login screen |
| `lib/features/settings/presentation/screens/settings_screen.dart` | 413 | `'Construction Inspector'` | `'Field Guide'` | About dialog |

### Documentation Files (Should Change)
| File | Lines | Changes |
|------|-------|---------|
| `README.md` | 1 | Title |
| `pubspec.yaml` | 2 | Description only |
| `patrol.yaml` | 1 | Display name |
| `.claude/CLAUDE.md` | 1 | Title |
| `.claude/agents/*.md` | Various | References in agent descriptions |
| `.claude/docs/*.md` | Various | References in documentation |
| `.claude/implementation/*.md` | Various | References in implementation plans |

### Files That Should NOT Change
| File | Rationale |
|------|-----------|
| `pubspec.yaml` (name field) | Dart package name - breaking change |
| `android/app/build.gradle.kts` (applicationId) | Android package - breaks installs |
| `ios/Runner.xcodeproj/project.pbxproj` (PRODUCT_BUNDLE_IDENTIFIER) | iOS bundle ID - breaks installs |
| All Dart import statements | Depend on package name |
| Deep link URLs in code | Would break auth callbacks |
| `android/app/src/main/kotlin/com/fvconstruction/construction_inspector/MainActivity.kt` | Package structure |
| Directory structure under `android/app/src/main/` | Package structure |

---

## Execution Order

### Step 1: Platform Configuration (Critical Path)
1. Android: `AndroidManifest.xml`
2. iOS: `Info.plist`
3. Windows: `main.cpp`, `Runner.rc`
4. Web: `index.html`, `manifest.json`

### Step 2: Flutter Application Code
1. `lib/main.dart`
2. `lib/features/auth/presentation/screens/login_screen.dart`
3. `lib/features/settings/presentation/screens/settings_screen.dart`
4. `lib/core/theme/app_theme.dart` (comment only)
5. `lib/core/transitions/page_transitions.dart` (comment only)

### Step 3: Configuration Files
1. `pubspec.yaml` (description only)
2. `patrol.yaml`

### Step 4: Documentation
1. `README.md`
2. `.claude/CLAUDE.md`
3. All agent documentation files
4. Implementation plan files

### Step 5: Build and Verify
1. Run `flutter clean`
2. Run `flutter pub get`
3. Build for each platform
4. Verify app name displays correctly

---

## Testing Checklist

### Build Verification
- [ ] `flutter analyze` - No new errors
- [ ] `flutter test` - All tests pass
- [ ] `flutter build apk` - Android build succeeds
- [ ] `flutter build ios` - iOS build succeeds (requires macOS)
- [ ] `flutter build windows` - Windows build succeeds

### Manual Testing
- [ ] **Android**: App shows "Field Guide" in launcher and app drawer
- [ ] **iOS**: App shows "Field Guide" on home screen
- [ ] **Windows**: Window title bar shows "Field Guide"
- [ ] **Login Screen**: Shows "Field Guide" title
- [ ] **Settings → About**: Shows "Field Guide" in About dialog
- [ ] **Web**: Browser tab shows "Field Guide"
- [ ] **Deep Links**: Auth callbacks still work (email verification, password reset)
- [ ] **Existing Data**: Local database still accessible
- [ ] **Sync**: Cloud sync still works (if Supabase configured)

### Regression Testing
- [ ] Authentication flow works
- [ ] Can create/edit projects
- [ ] Can create/edit daily entries
- [ ] PDF export works
- [ ] Photo capture works
- [ ] Offline mode works
- [ ] Sync to Supabase works (if configured)

---

## Risks and Mitigation

### Risk 1: Import Statements Break
**Likelihood**: None (if following Strategy 1)
**Impact**: High (app won't compile)
**Mitigation**: Keep Dart package name unchanged

### Risk 2: Deep Links Stop Working
**Likelihood**: None (if following Strategy 1)
**Impact**: High (auth broken)
**Mitigation**: Keep deep link scheme unchanged in `lib/main.dart` and `AndroidManifest.xml`

### Risk 3: Existing Installations Break
**Likelihood**: None (if following Strategy 1)
**Impact**: High (users lose data)
**Mitigation**: Keep applicationId and bundle ID unchanged

### Risk 4: Missed References
**Likelihood**: Low
**Impact**: Low (cosmetic only)
**Mitigation**: Search codebase after changes for remaining references

### Risk 5: Platform Build Failures
**Likelihood**: Low
**Impact**: Medium (delays release)
**Mitigation**: Test builds on all platforms before committing

---

## Rollback Plan

If issues are discovered after deployment:

1. **Git Revert**: All changes are in version control
   ```bash
   git revert <commit-hash>
   ```

2. **Manual Rollback**: Use this plan in reverse
   - Change all "Field Guide" back to "Construction Inspector"
   - Rebuild and redeploy

3. **No Data Loss**: Since package names are unchanged, user data is preserved

---

## Alternative: Strategy 2 (Full Rebrand - NOT RECOMMENDED)

If complete rebranding is required, additional changes:

### Additional Files to Change (187+ files)
1. Rename all imports from `package:construction_inspector/` to `package:field_guide/`
2. Change `pubspec.yaml` package name
3. Change Android applicationId in `build.gradle.kts`
4. Change iOS bundle ID in Xcode project
5. Change deep link scheme in code and manifests
6. Move Android package directory structure
7. Update all 181+ files that import from the package

### Additional Risks
- Database migration required
- Users must uninstall/reinstall app
- Play Store/App Store treats as new app
- Extensive testing required (estimated 20+ hours)
- Deep link migration for existing users

**Estimated Effort**: 2-3 days of development + testing
**NOT RECOMMENDED** unless business requires complete rebrand

---

## Agent Assignment

**Agent**: `flutter-specialist-agent`

**Task Breakdown**:
1. Platform configuration changes (Phase 1) - 30 minutes
2. Dart code changes (Phase 2) - 30 minutes
3. Configuration files (Phase 3) - 15 minutes
4. Documentation updates (Phase 4) - 45 minutes
5. Build verification (Phase 5) - 30 minutes
6. Manual testing (Phase 5) - 1 hour

**Total Estimated Time**: 3 hours

---

## Verification Commands

After implementation, run these commands to verify:

```bash
# Clean build
flutter clean
flutter pub get

# Analysis
flutter analyze

# Tests
flutter test

# Search for remaining references (should find none in code)
grep -r "Construction Inspector" lib/ --exclude-dir=.dart_tool

# Build verification
flutter build apk --debug
flutter build windows --debug
```

---

## Notes

- This plan follows Strategy 1 (Display Names Only) for minimal risk
- All user-facing names change to "Field Guide"
- All internal identifiers remain "construction_inspector"
- No breaking changes to existing installations
- Deep links continue to work
- Supabase sync continues to work
- Local database accessible without migration

## Questions for User

Before proceeding, please confirm:

1. **Scope**: Is changing just the display name sufficient, or is a full rebrand required?
2. **Existing Users**: Do we need to preserve compatibility with existing installations?
3. **Timeline**: When should this change be deployed?
4. **Testing**: Can you test on physical iOS device (requires macOS for build)?
5. **Branding**: Should the description also change in `pubspec.yaml` and `web/manifest.json`?
