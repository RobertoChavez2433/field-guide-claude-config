# /hookify:help Command

Show Hookify help information.

## Usage

```
/hookify:help
```

## Output

```
Hookify Plugin
==============

Create behavioral hooks that trigger on Claude Code events.

COMMANDS
--------
  /hookify           Main command (shows this help)
  /hookify:list      List all configured rules
  /hookify:configure Create or edit a rule
  /hookify:help      Show this help

RULE FILES
----------
Rules are markdown files in .claude/ matching:
  hookify.<name>.local.md

Example rule file:

  ---
  name: my-rule
  enabled: true
  event: bash
  pattern: dangerous.*command
  action: warn
  ---

  **Warning message shown to user**

  Additional details here.

FRONTMATTER FIELDS
------------------
  name     Rule identifier (required)
  enabled  true/false (default: true)
  event    Event type (required)
  pattern  Regex pattern (required)
  action   warn or block (default: warn)

EVENTS
------
  bash              Bash commands
  write             File writes
  edit              File edits
  stop              Stop events
  userpromptsubmit  User prompts

ACTIONS
-------
  warn   Show message, continue operation
  block  Show message, prevent operation

QUICK START
-----------
1. Create a rule:
   /hookify:configure

2. Or manually create .claude/hookify.my-rule.local.md

3. List rules:
   /hookify:list

DOCUMENTATION
-------------
See: .claude/plugins/hookify/skills/writing-rules/SKILL.md
```
