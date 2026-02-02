# Construction Domain Design

Pre-populated domain knowledge for construction inspector app interface design.

## Domain Context

**Users**: Construction inspectors documenting daily field activities

**Environment**: Outdoor, variable lighting, dust, weather exposure

**Device Usage**: Held in one hand, operated with thumb or gloved finger

**Mental State**: Task-focused, often rushed, need to minimize errors

## Environmental Constraints

### Outdoor Visibility

| Condition | Design Response |
|-----------|-----------------|
| Bright sunlight | High contrast ratios (7:1 minimum) |
| Deep shadows | Avoid pure white backgrounds (use off-white) |
| Variable lighting | Test in both extremes |
| Screen glare | Matte-friendly color choices |

### Physical Constraints

| Constraint | Design Response |
|------------|-----------------|
| Gloved hands | 48dp minimum touch targets, prefer 56dp |
| Dirty screens | Large tap areas, avoid edge gestures |
| One-handed use | Primary actions reachable with thumb |
| Device movement | Avoid precision requirements |

## Color Recommendations

### Primary Palette

| Color | Hex | Usage |
|-------|-----|-------|
| Blueprint Blue | #0D47A1 | Primary actions, navigation |
| Safety Orange | #FF6D00 | Warnings, important notices |
| Concrete Gray | #757575 | Secondary text, borders |
| High-Vis Yellow | #FFEA00 | Alerts, caution states |

### Semantic Colors

| State | Color | Usage |
|-------|-------|-------|
| Success | #4CAF50 | Saved, completed, synced |
| Warning | #FF9800 | Pending, needs attention |
| Error | #F44336 | Failed, missing required |
| Info | #2196F3 | Informational, tips |

### Background Colors

| Surface | Light Mode | Dark Mode |
|---------|------------|-----------|
| Primary surface | #F5F5F5 (off-white) | #121212 |
| Card surface | #FFFFFF | #1E1E1E |
| Elevated surface | #FFFFFF | #2C2C2C |

## Typography Recommendations

### Field-Readable Text

| Element | Size | Weight | Notes |
|---------|------|--------|-------|
| Screen title | 24sp | 600 | One glance identification |
| Section header | 18sp | 600 | Scannable hierarchy |
| Body text | 16sp | 400 | Readable at arm's length |
| Labels | 14sp | 500 | Clear form labeling |
| Captions | 12sp | 400 | Secondary information only |

### Font Choice

- System fonts for reliability
- Avoid thin weights (< 400)
- Avoid decorative fonts

## Touch Target Guidelines

### Minimum Sizes

| Element | Size | Reason |
|---------|------|--------|
| Buttons | 48 x 48 dp | Gloved finger |
| FAB | 56 x 56 dp | Primary action |
| List items | 56 dp height | Easy row selection |
| Checkboxes | 48 x 48 dp | Reliable toggle |
| Form fields | 56 dp height | Comfortable text entry |

### Spacing Between Targets

| Context | Spacing | Reason |
|---------|---------|--------|
| Related actions | 8 dp | Grouped, distinguishable |
| Distinct actions | 16 dp | Clear separation |
| Opposite actions | 24+ dp | Prevent misclicks |

## Form Design

### Best Practices

```
✓ One field per row (easier scanning)
✓ Labels above fields (not inside)
✓ Large submit button at bottom
✓ Immediate validation feedback
✓ Auto-save where possible
✓ Clear error messages
```

### Field Layout

```
┌──────────────────────────────┐
│ Project *                    │  ← Label outside, required indicator
│ ┌──────────────────────────┐ │
│ │ Highway 101 Expansion    │ │  ← 56dp height field
│ └──────────────────────────┘ │
│                              │
│ Location *                   │
│ ┌──────────────────────────┐ │
│ │ Mile Marker 45          ▼│ │  ← Dropdown with visible indicator
│ └──────────────────────────┘ │
│                              │
│                              │
│ ┌──────────────────────────┐ │
│ │        SAVE ENTRY        │ │  ← Full-width, 56dp primary button
│ └──────────────────────────┘ │
└──────────────────────────────┘
```

## Data Entry Optimization

### Minimize Typing

| Instead Of | Use |
|------------|-----|
| Free text | Dropdowns, selection |
| Address entry | GPS auto-fill |
| Date typing | Date picker |
| Time typing | Time picker |
| Number typing | Stepper, quick +/- |

### Smart Defaults

| Field | Default Strategy |
|-------|------------------|
| Date | Today's date |
| Time | Current time |
| Location | Last used location |
| Project | Last accessed project |
| Weather | Auto-fetch from API |

## Navigation Patterns

### Recommended

| Pattern | When to Use |
|---------|-------------|
| Bottom navigation | Main app sections (3-5 items) |
| Tabs | Sub-sections within a screen |
| FAB | Primary creation action |
| Back arrow | Return to previous screen |
| Swipe gestures | AVOID - unreliable with gloves |

### Avoid

| Pattern | Why |
|---------|-----|
| Edge swipes | Hard with gloves/cases |
| Small icons without labels | Unclear meaning |
| Hidden menus | Discoverability issues |
| Double-tap | Unreliable timing |
| Long press | Not obvious, slow |

## Status Communication

### Visual Indicators

| Status | Visual Treatment |
|--------|------------------|
| Saved locally | Checkmark, "Saved" label |
| Pending sync | Cloud with arrow icon |
| Synced | Cloud with checkmark |
| Sync error | Red warning, retry button |
| Offline | Offline icon in header |

### Feedback Timing

| Action | Feedback |
|--------|----------|
| Button tap | Immediate ripple |
| Save action | Progress indicator |
| Sync status | Persistent in header |
| Errors | Toast + action button |

## Construction-Specific Terminology

Use domain-appropriate language:

| Generic | Construction Domain |
|---------|---------------------|
| Item | Bid Item |
| Amount | Quantity |
| Worker count | Personnel / Crew |
| Categories | Work Types |
| Notes | Activities |
| Pictures | Photo Log |
| Report | IDR (Inspector Daily Report) |

## Accessibility Considerations

### Minimum Contrast

| Element | Ratio |
|---------|-------|
| Normal text | 4.5:1 |
| Large text (18sp+) | 3:1 |
| UI controls | 3:1 |
| Focus indicators | 3:1 |

### Screen Reader Support

- All images have descriptions
- Buttons have labels
- Form fields have associated labels
- Status changes announced
