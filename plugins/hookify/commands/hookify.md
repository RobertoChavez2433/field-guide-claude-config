# /hookify Command

Main command for the Hookify plugin.

## Usage

```
/hookify                    # Analyze session (same as /analyze)
/hookify [subcommand]       # Run specific subcommand
```

## Without Subcommand: Session Analysis

Running `/hookify` without a subcommand triggers the **conversation analyzer** which:

1. Analyzes the current session for patterns
2. Identifies hookify rule candidates
3. Detects defects, workflow issues, knowledge gaps, code quality concerns
4. Produces a comprehensive report

This is equivalent to `/analyze`. See `/analyze` for full documentation.

## Subcommands

| Command | Description |
|---------|-------------|
| `/hookify:list` | List all configured rules |
| `/hookify:configure` | Create or edit a rule |
| `/hookify:help` | Show help information |

## Related Commands

| Command | Description |
|---------|-------------|
| `/analyze` | Full session analysis (same as `/hookify`) |
| `/analyze --last N` | Analyze last N sessions |
| `/analyze --all` | Comprehensive project analysis |

## Quick Start

1. **Analyze current session:**
   ```
   /hookify
   ```
   or
   ```
   /analyze
   ```

2. **List existing rules:**
   ```
   /hookify:list
   ```

3. **Create a new rule:**
   ```
   /hookify:configure
   ```

4. **View help:**
   ```
   /hookify:help
   ```

## Rule Files

Rules are stored as markdown files in `.claude/` with the naming pattern:
```
hookify.<rule-name>.local.md
```

## Example Rule

```markdown
---
name: dangerous-rm
enabled: true
event: bash
pattern: rm\s+(-rf|-fr|--recursive)
action: warn
---

**Potentially dangerous rm command detected**

Please verify the path is correct before proceeding.
```

## Actions

| Action | Behavior |
|--------|----------|
| `block` | Prevents the operation and shows message |
| `warn` | Shows warning message but allows operation |

## Events

| Event | Triggers When |
|-------|---------------|
| `bash` | Bash command is executed |
| `write` | File is written |
| `edit` | File is edited |
| `stop` | Claude stops responding |
| `userpromptsubmit` | User submits a prompt |
