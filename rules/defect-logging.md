# Defect Logging Instructions

When you discover bugs, anti-patterns, or issues during testing or review, **log them to `.claude/memory/defects.md`**.

## When to Log
- Test failures caused by known anti-patterns
- Async context issues (missing `mounted` check)
- Dispose errors (async in dispose)
- Sort/ordering issues in tests
- Recurring anti-patterns found during review
- Architecture violations
- Security vulnerabilities
- Performance issues that caused problems
- Any pattern worth documenting for prevention

## Defect Format
```markdown
### YYYY-MM-DD: [Brief Title]
**Issue**: What went wrong
**Root Cause**: Why it happened
**Prevention**: How to avoid in future
**Ref**: @path/to/file.dart:line
```

## How to Log
Use the Edit tool to add new defects **above** the `<!-- Add new defects above this line -->` marker in `.claude/memory/defects.md`.
