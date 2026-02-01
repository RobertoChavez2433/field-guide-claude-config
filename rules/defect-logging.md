# Defect Logging Instructions

When you discover bugs, anti-patterns, or issues during testing or review, **log them to `.claude/memory/defects.md`**.

## When to Log
- Test failures caused by known anti-patterns
- Async context issues (missing `mounted` check)
- Dispose errors (async in dispose)
- Recurring anti-patterns found during review
- Architecture violations
- Security vulnerabilities
- Performance issues that caused problems

## Defect Format (Required)
```markdown
### [CATEGORY] YYYY-MM-DD: Brief Title
**Pattern**: What to avoid (1 line)
**Prevention**: How to avoid (1-2 lines)
**Ref**: @path/to/file.dart (optional)
```

## Categories (Required)
| Category | Use For |
|----------|---------|
| [ASYNC] | Context safety, dispose, mounted checks |
| [E2E] | Patrol testing patterns |
| [FLUTTER] | Widget, Provider, state patterns |
| [DATA] | Repository, collection, model patterns |
| [CONFIG] | Supabase, credentials, environment |

## Auto-Archive Rules
- Maximum 15 active defects in `defects.md`
- Defect 16+ triggers rotation of oldest to `defects-archive.md`
- Use `/end-session` to handle rotation automatically

## How to Log
1. Add new defects **at the top** of Active Patterns section
2. Include category and date: `### [CAT] 2026-02-01: Title`
3. If >15 defects, move oldest to archive before adding new

## Archives
- Active: @.claude/memory/defects.md
- Archive: @.claude/memory/defects-archive.md
