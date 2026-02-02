# /hookify:list Command

List all configured Hookify rules.

## Usage

```
/hookify:list
```

## Implementation

When this command is invoked, read all rule files and display:

1. **Find rule files:**
   ```bash
   ls -la .claude/hookify.*.local.md
   ```

2. **For each rule, show:**
   - Name
   - Event type
   - Pattern (truncated if long)
   - Action (block/warn)
   - Enabled status

## Output Format

```
Hookify Rules
=============

Rule: no-coauthored-by
  Event:   bash
  Pattern: Co-Authored-By
  Action:  block
  Status:  enabled
  File:    .claude/hookify.no-coauthored-by.local.md

Rule: flutter-bash-warning
  Event:   bash
  Pattern: ^flutter\s+(build|clean|run|test|pub)
  Action:  warn
  Status:  enabled
  File:    .claude/hookify.flutter-bash.local.md

---
Total: 2 rules (2 enabled, 0 disabled)
```

## No Rules Found

If no rules exist:
```
No Hookify rules found.

Create a rule with: /hookify:configure

Or manually create a file:
  .claude/hookify.<name>.local.md
```
