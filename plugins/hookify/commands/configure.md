# /hookify:configure Command

Create or edit a Hookify rule.

## Usage

```
/hookify:configure [rule-name]
```

## Interactive Flow

### 1. Rule Name
If not provided, prompt for a name:
```
What should this rule be called? (e.g., "no-secrets", "require-tests")
```

### 2. Event Type
```
What event should trigger this rule?
1. bash - When a bash command runs
2. write - When a file is written
3. edit - When a file is edited
4. stop - When Claude stops responding
5. userpromptsubmit - When user submits a prompt
```

### 3. Pattern
```
What pattern should match? (regex supported)
Examples:
  - "password" (literal match)
  - "rm\s+-rf" (rm with -rf flag)
  - "\.env$" (files ending in .env)
```

### 4. Action
```
What should happen when the pattern matches?
1. warn - Show a warning but continue
2. block - Prevent the operation
```

### 5. Message
```
What message should be shown?
(This will be the body of the markdown file)
```

## Output

Creates file: `.claude/hookify.<rule-name>.local.md`

```markdown
---
name: <rule-name>
enabled: true
event: <event>
pattern: <pattern>
action: <action>
---

<message>
```

## Editing Existing Rules

If the rule file already exists, show current values and ask what to change.

## Example Session

```
> /hookify:configure

Rule name: sensitive-files
Event type: write
Pattern: \.(env|pem|key)$
Action: block

Message (markdown supported):
**Attempting to write sensitive file!**

This file type may contain secrets. Are you sure?

Created: .claude/hookify.sensitive-files.local.md
```
