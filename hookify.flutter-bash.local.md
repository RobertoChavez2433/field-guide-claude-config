---
name: flutter-bash-warning
enabled: true
event: bash
pattern: ^flutter\s+(build|clean|run|test|pub)
action: warn
---

**Flutter command in Git Bash detected**

Git Bash may silently fail on Flutter commands.
Consider using: `pwsh -Command "flutter ..."`

See CLAUDE.md Build Commands section.
