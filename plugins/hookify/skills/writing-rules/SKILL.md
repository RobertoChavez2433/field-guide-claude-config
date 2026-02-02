# Writing Hookify Rules Skill

**Purpose**: Create effective behavioral hooks for Claude Code that prevent unwanted actions and enforce project standards.

## Iron Law

> **START WITH WARNINGS, ONLY BLOCK WHEN NECESSARY**

Blocking actions disrupts workflow. Use `warn` first, only escalate to `block` for truly dangerous operations.

## Rule File Structure

```markdown
---
name: rule-identifier
enabled: true
event: bash|write|edit|stop|userpromptsubmit
pattern: regex-pattern
action: warn|block
---

**User-facing message title**

Detailed explanation and guidance.
```

## Event Types

| Event | Triggers On | Common Uses |
|-------|-------------|-------------|
| `bash` | Shell commands | Dangerous commands, wrong tools |
| `write` | File creation | Sensitive files, wrong locations |
| `edit` | File modifications | Protected files, bad patterns |
| `stop` | Claude stopping | Verification requirements |
| `userpromptsubmit` | User input | Workflow guidance |

## Pattern Writing

### Basic Patterns
```
pattern: dangerous-word       # Literal match
pattern: \.env$              # Files ending in .env
pattern: password|secret     # Either word
```

### Command Patterns
```
pattern: rm\s+(-rf|-fr)      # rm with recursive force
pattern: git push.*--force   # Force push
pattern: DROP\s+TABLE        # SQL drop
```

### Path Patterns
```
pattern: /etc/               # System directories
pattern: node_modules/       # Dependencies
pattern: \.git/              # Git internals
```

## Action Guidelines

### Use `warn` for:
- Potentially risky but valid operations
- Reminders about best practices
- Suggestions for better alternatives
- Operations that need user attention

### Use `block` for:
- Operations that violate project rules
- Actions that could cause data loss
- Security-sensitive operations
- Breaking established patterns

## Message Writing

### Good Messages
```markdown
**Flutter command in Git Bash detected**

Git Bash may silently fail on Flutter commands.
Consider using: `pwsh -Command "flutter ..."`
```

### Bad Messages
```markdown
Error detected stop now
```

### Include:
- Clear title explaining what triggered
- Why this is a concern
- What to do instead (if applicable)
- Reference to docs if complex

## Project-Specific Rules

### Construction Inspector App

**No Co-Authored-By**
```markdown
---
name: no-coauthored-by
event: bash
pattern: Co-Authored-By
action: block
---
```

**Flutter in Git Bash**
```markdown
---
name: flutter-bash-warning
event: bash
pattern: ^flutter\s+(build|clean|run|test|pub)
action: warn
---
```

## Testing Rules

1. Create the rule file
2. Manually trigger the pattern
3. Verify action (warn/block) works
4. Check message displays correctly
5. Confirm false positives are minimal

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Too broad pattern | Many false positives | Be more specific |
| Block everything | Disrupts workflow | Use warn first |
| No helpful message | User confused | Explain why and what to do |
| Untested regex | May not match | Test with actual content |

## Rule Organization

```
.claude/
├── hookify.no-coauthored-by.local.md    # Git commit rules
├── hookify.flutter-bash.local.md         # Tool warnings
├── hookify.dangerous-rm.local.md         # Safety rules
└── hookify.sensitive-files.local.md      # Security rules
```

## Debugging

If a rule isn't triggering:
1. Check `enabled: true` in frontmatter
2. Verify pattern with a regex tester
3. Confirm event type matches the action
4. Check for typos in the filename pattern

If getting false positives:
1. Make pattern more specific
2. Add anchors (^, $) if needed
3. Consider case sensitivity
