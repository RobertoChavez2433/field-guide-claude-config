# Quality Checklist

## Architecture
- [ ] Follows feature-first organization
- [ ] Clear separation: data/domain/presentation
- [ ] No circular dependencies
- [ ] Appropriate use of dependency injection

## Code Patterns
- [ ] Follows project coding standards
- [ ] Uses established patterns (Provider, repositories)
- [ ] Proper error handling at boundaries
- [ ] Async safety (mounted checks, dispose)

## Performance
- [ ] No unnecessary rebuilds
- [ ] Efficient data structures
- [ ] Lazy loading where appropriate
- [ ] No memory leaks (disposed controllers)

## Maintainability
- [ ] Self-documenting code
- [ ] Appropriate naming conventions
- [ ] Single responsibility principle
- [ ] No magic numbers/strings

## Security
- [ ] No hardcoded credentials
- [ ] Input validation at boundaries
- [ ] Secure data storage
- [ ] OWASP considerations

## Database (Supabase)
- [ ] All tables have appropriate indexes
- [ ] Foreign keys have ON DELETE CASCADE where appropriate
- [ ] Timestamps use TIMESTAMPTZ (not TIMESTAMP)
- [ ] TEXT IDs used consistently (not UUID)
- [ ] RLS policies cover all access patterns
- [ ] Query performance verified with EXPLAIN ANALYZE

## PDF
- [ ] All fields map to correct visual positions
- [ ] No `[PDF] Field not found` errors in console
- [ ] Data appears in expected format
- [ ] Page breaks don't split content awkwardly
- [ ] Empty sections show appropriate placeholder
