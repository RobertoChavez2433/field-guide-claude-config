# Coding Standards

@.claude/rules/coding-standards.md

## Additional Best Practices (2026)

### Feature-First Organization
- Group by feature, not layer
- Most features use data/presentation structure
- Only sync feature uses full Clean Architecture with data/domain/presentation
- Shared code in core/ or shared/

### Provider State Management
- Use `ChangeNotifierProvider` for state management
- Keep `Consumer` widgets deep in tree
- Check `mounted` before context operations after async calls
- Load data in `initState` with `addPostFrameCallback`

### Offline-First Pattern
- Local SQLite is source of truth
- Queue operations for background sync
- Use last-write-wins for conflicts
- Track sync_status on all syncable entities

### Error Handling
- Domain-level Failure types
- Exception mapping at repository boundary
- Log errors with context
- User-friendly error messages

### Testing Strategy
- 60% unit tests (business logic)
- 20% widget tests (UI components)
- 20% integration tests (user flows)
