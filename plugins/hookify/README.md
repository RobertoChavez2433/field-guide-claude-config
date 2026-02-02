# Hookify Plugin

Create custom hooks to prevent unwanted behaviors through simple markdown configuration files.

## Features

- **Automatic Analysis**: Run `/hookify` to analyze conversation patterns and suggest rules
- **Markdown Configuration**: Define rules with YAML frontmatter, no complex JSON editing
- **Regex Patterns**: Match behaviors with regular expressions
- **Immediate Effect**: Rules apply without restart

## Quick Start

### Create a Rule Manually

Create a file `.claude/hookify.my-rule.local.md`:

```markdown
---
name: my-rule
enabled: true
event: bash
pattern: rm\s+-rf
action: warn
---

**Dangerous rm command detected!**

Please verify the path before proceeding.
```

### Let Claude Create Rules

```
/hookify warn me when I use rm -rf
```

Or analyze your session for problematic patterns:

```
/hookify
```

## Commands

| Command | Description |
|---------|-------------|
| `/hookify [instruction]` | Create rule from instruction or analyze session |
| `/hookify:list` | Show all configured rules |
| `/hookify:configure` | Interactive rule creation |
| `/hookify:help` | Show help information |

## Rule Format

```markdown
---
name: rule-identifier        # Required: unique name
enabled: true                # Optional: default true
event: bash                  # Required: bash, write, edit, stop, userpromptsubmit
pattern: regex-pattern       # Required: pattern to match
action: warn                 # Optional: warn (default) or block
---

Message shown to user when pattern matches.
Supports **markdown** formatting.
```

## Events

| Event | Triggers When | Pattern Matches Against |
|-------|---------------|------------------------|
| `bash` | Bash command runs | Command string |
| `write` | File is written | File content |
| `edit` | File is edited | New content |
| `stop` | Claude stops | Final response |
| `userpromptsubmit` | User sends message | User's message |

## Actions

| Action | Behavior |
|--------|----------|
| `warn` | Show message, allow operation to proceed |
| `block` | Show message, prevent operation |

## Project Rules

This project includes these default rules:

| Rule | Event | Action | Purpose |
|------|-------|--------|---------|
| `no-coauthored-by` | bash | block | Prevent Co-Authored-By in commits |
| `flutter-bash` | bash | warn | Warn about Flutter in Git Bash |
| `dangerous-rm` | bash | warn | Warn about recursive rm |

## File Locations

- Rules: `.claude/hookify.*.local.md`
- Plugin: `.claude/plugins/hookify/`
- Examples: `.claude/plugins/hookify/examples/`

## Requirements

- Python 3.7+
- No external dependencies

## Architecture

```
.claude/plugins/hookify/
├── .claude-plugin/         # Plugin registration
├── agents/                 # Conversation analyzer
├── commands/               # Slash commands
├── core/                   # Rule loading and engine
├── examples/               # Example rules
├── hooks/                  # Event handlers
├── matchers/               # Pattern matching
├── skills/                 # Rule writing skill
└── utils/                  # Utilities
```
