# Defects: Photos

Active patterns for photos. Max 5 defects - oldest auto-archives.
Archive: .claude/logs/defects-archive.md

## Active Patterns

### [ASYNC] 2026-03-20: TextEditingController used after disposed in photo detail dialog — BUG-9 (Session 608)
**Pattern**: Photo detail dialog controllers are disposed when dialog closes, but async callbacks still reference them. Also triggers `_dependents.isEmpty` assertion failure.
**Prevention**: Check `mounted` before accessing controllers in async callbacks. Cancel pending async work in `dispose()`.
**Ref**: @lib/features/photos/presentation/widgets/photo_detail_dialog.dart

### [E2E] 2026-03-20: inject-photo-direct creates records without file_path — BUG-14 (Session 608)
**Pattern**: `inject-photo-direct` endpoint creates photo records with null `file_path`. Supabase `photos` table has NOT NULL on `file_path`, so injected photos never sync.
**Prevention**: Set a placeholder file_path when creating injected records, or make `file_path` nullable in Supabase.
**Ref**: @lib/test_harness/driver_server.dart

<!-- Add defects above this line -->
