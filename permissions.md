# Project Permissions

## File System Operations

**Approved**: All directory creation and file operations within the project structure.

- Creating feature directories (lib/features/*)
- Creating model, repository, datasource, and presentation files
- Moving/copying files during refactoring
- Running mkdir, ls, dir commands without confirmation

## Git Operations

**Approved**: Standard git operations (status, diff, log, add, commit)

**Requires Confirmation**: Force push, hard reset, amending commits

## Build & Test

**Approved**: flutter analyze, flutter test, flutter run, flutter build

## External Services

**Approved**: Read-only operations (viewing Supabase schema, checking sync status)

**Requires Confirmation**: Schema migrations, RLS policy changes, destructive operations
