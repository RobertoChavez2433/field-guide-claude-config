# Design Section Templates

Break designs into 200-300 word validated sections.

## Section Order

1. **Overview** - What and why
2. **Data Model** - Entities and relationships
3. **User Flow** - Screen-by-screen journey
4. **UI Components** - Widgets and layout
5. **State Management** - Provider/repository design
6. **Offline Behavior** - Sync and conflict resolution
7. **Edge Cases** - Error states and boundaries

---

## 1. Overview Section

```markdown
## Overview

### Purpose
[1-2 sentences: What problem does this solve?]

### Scope
[What's included vs. excluded in this implementation]

### Success Criteria
- [ ] [Measurable outcome 1]
- [ ] [Measurable outcome 2]
- [ ] [Measurable outcome 3]
```

---

## 2. Data Model Section

```markdown
## Data Model

### New Entity: [EntityName]

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | String | Yes | UUID primary key |
| [field] | [Type] | [Yes/No] | [Purpose] |

### Relationships
- **Parent**: [Entity] - [relationship description]
- **Children**: [Entity] - [relationship description]

### Database Changes
```sql
-- New table or columns
```

### Sync Considerations
- [How does this sync to Supabase?]
- [Conflict resolution strategy]
```

---

## 3. User Flow Section

```markdown
## User Flow

### Entry Points
1. [How user gets here]
2. [Alternative paths]

### Screen Flow
```
[Screen A] --> [Screen B] --> [Screen C]
     |              |
     v              v
  [Branch]      [Branch]
```

### Key Interactions
| Action | Result | Notes |
|--------|--------|-------|
| Tap X | Opens Y | [Context] |
```

---

## 4. UI Components Section

```markdown
## UI Components

### New Widgets
| Widget | Location | Purpose |
|--------|----------|---------|
| [Name] | `lib/features/X/presentation/widgets/` | [Purpose] |

### Layout Sketch
```
+------------------+
| [Header]         |
+------------------+
| [Content Area]   |
|                  |
+------------------+
| [Actions]        |
+------------------+
```

### Reusable Patterns
- Uses existing: [StatusBadge, StatCard, etc.]
- New reusable: [Widget that could be shared]

### TestingKeys Required
- `TestingKeys.[keyName]` - [Purpose]
```

---

## 5. State Management Section

```markdown
## State Management

### Provider: [ProviderName]

**Responsibilities**:
- [What state it manages]
- [What operations it exposes]

**Key Methods**:
```dart
// Pseudo-signature
Future<void> loadData(String id);
Future<void> saveData(Entity entity);
```

### Data Flow
```
Screen -> Provider -> Repository -> Datasource -> SQLite/Supabase
```

### Error Handling
- [How errors surface to UI]
- [Retry behavior]
```

---

## 6. Offline Behavior Section

```markdown
## Offline Behavior

### Offline Capabilities
| Action | Offline? | Notes |
|--------|----------|-------|
| View data | Yes | From local SQLite |
| Create new | Yes | Queued for sync |
| Edit | Yes | Queued for sync |
| Delete | Yes | Soft delete, sync later |

### Sync Strategy
- **Direction**: [Bidirectional / Upload only / Download only]
- **Trigger**: [Background / Manual / On-demand]
- **Conflict**: [Last-write-wins / Merge / Prompt user]

### Queue Behavior
- Pending changes stored in: `sync_queue` table
- Retry: [Policy for failed syncs]
```

---

## 7. Edge Cases Section

```markdown
## Edge Cases

### Error States
| Scenario | Handling | UI Feedback |
|----------|----------|-------------|
| No network | [Behavior] | [What user sees] |
| Invalid input | [Validation] | [Error message] |
| Not found | [Behavior] | [Empty state] |

### Boundaries
- Maximum: [Size limits, count limits]
- Minimum: [Required fields, defaults]

### Permission Edge Cases
- [What if user lacks permission?]
- [What if permission revoked mid-flow?]
```

---

## Validation Prompt

After each section, ask:

> "Does this match your expectations for [section name]? Any changes before we continue?"

Only proceed after explicit confirmation.
