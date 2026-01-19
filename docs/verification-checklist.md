# Feature-First Reorganization - Verification Checklist

**Date**: 2026-01-19
**Branch**: feature/feature-first-reorganization
**Status**: COMPLETE - Ready for Verification

---

## Pre-Commit Verification

### 1. Static Analysis
```bash
cd "C:\Users\rseba\Projects\Field Guide App"
flutter analyze
```

**Expected Result**:
- No new errors
- Only 4 info-level warnings (pre-existing in report_screen.dart)
- No import errors
- No missing dependencies

**If Issues Found**:
- Review error messages
- Fix import paths if needed
- Re-run analyzer

---

### 2. Test Suite
```bash
flutter test
```

**Expected Result**:
- All 278 tests pass
- No new test failures
- No timeout issues

**If Failures Found**:
- Review test output
- Check for import errors in test files
- Fix and re-run

---

### 3. Git Diff Review
```bash
git status
git diff --stat
```

**Expected Changes**:
- ~13 files modified
- ~13 files deleted
- ~7 new feature directories

**Review Points**:
- Verify no unintended file deletions
- Check that all imports use package paths
- Ensure barrel exports are correct
- Confirm no debug code left in

---

### 4. Build Verification
```bash
# Windows
flutter build windows --debug

# Android (if configured)
flutter build apk --debug

# Check for build errors
```

**Expected Result**:
- Clean build with no errors
- All imports resolved correctly
- No missing assets

---

### 5. Import Path Audit
```bash
# Search for old-style imports (should find none in features/)
grep -r "import '\.\./\.\./\.\./data/models" lib/features/
grep -r "import '\.\./\.\./\.\./presentation" lib/features/

# Search for relative imports crossing features (should find none)
grep -r "import '\.\./\.\.\/" lib/features/ | grep -v "import '\.\./\.\./models"
```

**Expected Result**:
- No old-style imports in features/
- No cross-feature relative imports
- All imports use package:construction_inspector/

---

### 6. Barrel Export Verification

Check that all feature barrels exist and export correctly:

```bash
# List all feature main barrels
ls lib/features/*/[a-z]*.dart

# Expected files:
# lib/features/auth/auth.dart
# lib/features/contractors/contractors.dart
# lib/features/dashboard/dashboard.dart
# lib/features/entries/entries.dart
# lib/features/locations/locations.dart
# lib/features/pdf/pdf.dart
# lib/features/photos/photos.dart
# lib/features/projects/projects.dart
# lib/features/quantities/quantities.dart
# lib/features/settings/settings.dart
# lib/features/sync/sync.dart
# lib/features/weather/weather.dart
```

**Verification**:
- All 12 feature barrels exist
- Each barrel exports its sublayers (data.dart, presentation.dart, etc.)

---

### 7. Widget Organization Check

Verify widgets moved to correct locations:

```bash
# Photo widgets should be in photos feature
ls lib/features/photos/presentation/widgets/

# Expected files:
# photo_source_dialog.dart
# photo_thumbnail.dart
# photo_name_dialog.dart
# widgets.dart (barrel)

# PDF widget should be in pdf feature
ls lib/features/pdf/presentation/widgets/

# Expected files:
# import_type_dialog.dart
# widgets.dart (barrel)
```

---

### 8. Empty Directory Check

Verify empty directories were deleted:

```bash
# These should NOT exist:
ls lib/presentation/screens/dashboard 2>nul  # Should fail
ls lib/presentation/screens/settings 2>nul   # Should fail
ls lib/presentation/widgets 2>nul             # Should fail (or only have non-feature widgets)
```

**Expected**: All feature-specific directories moved to features/

---

## Post-Commit Verification

### 9. Branch Status
```bash
git status
```

**Expected Result**:
- Working directory clean
- No uncommitted changes
- On branch: feature/feature-first-reorganization

---

### 10. Commit History
```bash
git log --oneline -5
```

**Expected**:
- Latest commit describes reorganization
- Previous commits show phase completions
- No merge conflicts

---

## Manual Testing Checklist

### 11. App Launch
- [ ] App launches without errors
- [ ] No missing dependencies warnings
- [ ] Splash screen displays correctly
- [ ] Theme loads properly

### 12. Navigation
- [ ] Projects list loads
- [ ] Can navigate to project dashboard
- [ ] Can open calendar/home screen
- [ ] Can open settings screen
- [ ] All routes work correctly

### 13. Feature Functionality
- [ ] Can create/edit project
- [ ] Can add daily entry
- [ ] Can capture photo with GPS
- [ ] Can generate PDF report
- [ ] Can sync with Supabase (if configured)
- [ ] Theme switching works (light/dark/high contrast)

### 14. Data Persistence
- [ ] Data saves to local SQLite
- [ ] Data loads on app restart
- [ ] No data loss after reorganization

---

## Performance Checks

### 15. App Performance
- [ ] App starts quickly (no regression)
- [ ] Screens load smoothly
- [ ] No new memory leaks
- [ ] Build time acceptable

### 16. Test Performance
- [ ] Tests run in reasonable time
- [ ] No test timeouts
- [ ] Coverage unchanged (278 tests)

---

## Documentation Review

### 17. Documentation Updated
- [x] `.claude/plans/_state.md` - Current phase updated
- [x] `.claude/docs/latest-session.md` - Session summary complete
- [x] `.claude/docs/current-plan.md` - All phases marked complete
- [x] `.claude/rules/project-status.md` - Phase 12 added
- [x] `CLAUDE.md` - Project structure updated
- [x] `.claude/docs/feature-first-reorganization-summary.md` - Summary created
- [x] `.claude/docs/cleanup-instructions.md` - Cleanup guide created
- [x] `.claude/docs/verification-checklist.md` - This file

---

## Final Checklist Before Merge

### 18. Pre-Merge Requirements
- [ ] All verification steps passed
- [ ] Flutter analyze: 0 errors
- [ ] Flutter test: 278/278 passing
- [ ] Manual testing complete
- [ ] Documentation updated
- [ ] Review reports cleaned up (deleted or archived)
- [ ] Git diff reviewed and approved
- [ ] No debug code or TODO comments added
- [ ] All team members notified of architecture change

### 19. Merge Preparation
- [ ] Branch is up to date with main
- [ ] No merge conflicts
- [ ] Commit message is descriptive
- [ ] PR description includes summary
- [ ] Breaking changes documented (if any)

---

## Success Criteria

Reorganization is successful if:
1. **No Regressions**: All existing functionality works
2. **No Test Failures**: All 278 tests pass
3. **No Analyzer Errors**: Only pre-existing warnings
4. **Clean Build**: App builds and runs on all platforms
5. **Documentation Complete**: All docs reflect new structure
6. **No Circular Dependencies**: Feature isolation maintained
7. **Import Consistency**: All imports use package paths
8. **Widget Organization**: Feature widgets in feature directories

---

## Issue Resolution

If verification fails at any step:

1. **Analyzer Errors**:
   - Review error messages
   - Fix import paths
   - Check barrel exports
   - Re-run analyzer

2. **Test Failures**:
   - Review failed test output
   - Check test imports
   - Verify test data still valid
   - Fix and re-run tests

3. **Build Errors**:
   - Clean build: `flutter clean`
   - Rebuild: `flutter pub get && flutter build windows --debug`
   - Check for missing files

4. **Runtime Errors**:
   - Review error logs
   - Check feature initialization
   - Verify provider setup in main.dart
   - Debug and fix

---

## Rollback Plan

If critical issues found:

```bash
# Rollback to previous commit
git reset --hard HEAD~1

# Or checkout main branch
git checkout main

# Or create hotfix branch
git checkout -b hotfix/reorganization-issues
```

**Note**: Only rollback if critical issues prevent app functionality. Minor issues can be fixed with follow-up commits.

---

## Sign-Off

### Verification Completed By
- Name: ___________________
- Date: ___________________
- Status: [ ] PASS  [ ] FAIL

### Review Completed By
- Name: ___________________
- Date: ___________________
- Status: [ ] APPROVED  [ ] CHANGES REQUESTED

---

**Status**: Ready for verification
**Next Step**: Run verification steps 1-16
**Goal**: Merge to main branch after all checks pass
