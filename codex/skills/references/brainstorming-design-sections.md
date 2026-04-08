# Brainstorming Design Sections

Break the design into validated sections. Scale each section to the complexity
of the request. Small features may only need the first 3-4 sections.

## Section Order

1. Overview
2. Data Model
3. User Flow
4. UI Components
5. State Management
6. Offline Behavior
7. Edge Cases
8. Testing Strategy
9. Performance Considerations
10. Security Implications
11. Migration/Cleanup

## Overview

```markdown
## Overview

### Purpose
[What problem this solves]

### Scope
[What is included and excluded]

### Success Criteria
- [ ] [Measurable outcome 1]
- [ ] [Measurable outcome 2]
```

## Data Model

```markdown
## Data Model

### Entities
| Entity | Change | Notes |
|--------|--------|-------|
| [Name] | New/Update/None | [Why] |

### Relationships
- [Relationship and ownership rules]

### Storage / Sync
- [SQLite / Supabase / cache expectations]
- [Conflict resolution strategy]
```

## User Flow

```markdown
## User Flow

### Entry Points
1. [Primary entry]
2. [Secondary entry]

### Flow
[Screen A] -> [Screen B] -> [Result]

### Key Interactions
| Action | Result | Notes |
|--------|--------|-------|
| [Action] | [Outcome] | [Notes] |
```

## UI Components

```markdown
## UI Components

### New or Changed Widgets
| Widget | Location | Purpose |
|--------|----------|---------|
| [Name] | [Path] | [Why] |

### Reuse
- Existing pattern: [Widget/pattern]
- New reusable piece: [Widget/pattern]

### Testing Keys
- `TestingKeys.[name]` - [Purpose]
```

## State Management

```markdown
## State Management

### Owner
- [Provider / repository / screen state]

### Responsibilities
- [Responsibility 1]
- [Responsibility 2]

### Error Handling
- [How errors surface]
- [Retry behavior]
```

## Offline Behavior

```markdown
## Offline Behavior

| Action | Offline? | Notes |
|--------|----------|-------|
| View | Yes/No | [How] |
| Create | Yes/No | [How] |
| Edit | Yes/No | [How] |

### Sync Strategy
- Trigger: [Background / manual / on-demand]
- Direction: [Upload / download / bidirectional]
- Conflict rule: [Rule]
```

## Edge Cases

```markdown
## Edge Cases

| Scenario | Handling | UI Feedback |
|----------|----------|-------------|
| No network | [Behavior] | [Message] |
| Invalid input | [Behavior] | [Message] |
| Missing data | [Behavior] | [Message] |
```

## Testing Strategy

```markdown
## Testing Strategy

### Unit
- [What to test]

### Widget
- [What to test]

### Integration
- [Critical path]
```

## Performance Considerations

```markdown
## Performance Considerations

- [Potential bottleneck]
- [Mitigation]
- [Acceptable performance target]
```

## Security Implications

```markdown
## Security Implications

- [Auth requirement]
- [Data exposure concern]
- [Validation boundary]
- [RLS or tenant isolation impact]
```

## Migration/Cleanup

```markdown
## Migration/Cleanup

- [Schema or storage change]
- [Dead code cleanup]
- [Backward compatibility note]
```

## Validation Prompt

After each section, ask:

```text
Does this match your expectations for [section name]? Any changes before we continue?
```
