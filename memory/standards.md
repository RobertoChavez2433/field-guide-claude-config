# Coding Standards

@.claude/rules/coding-standards.md

## Additional Best Practices (2026)

### Feature-First Organization
- Group by feature, not layer
- Each feature contains its own data/domain/presentation
- Shared code in core/ or shared/

### Provider State Management
- Use `FutureProvider` for async data fetching
- Use `ChangeNotifierProvider` for form state
- Keep `Consumer` widgets deep in tree
- Check `mounted` before context operations

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
- 70% unit tests (business logic)
- 20% widget tests (UI components)
- 10% integration tests (user flows)
