# Brainstorming Question Patterns

Use these patterns to keep brainstorming scoped, incremental, and easy to
answer. Prefer one question per message.

## General Scope

```text
Which scope fits best for this pass?

A) Minimum viable slice
   Best for: proving the workflow quickly

B) Complete feature pass
   Best for: shipping the full intended behavior

C) Infrastructure first
   Best for: laying groundwork before visible UI changes
```

## Success Criteria

```text
What matters most to get right first?

A) User experience
   Best for: workflow clarity, speed, reduced friction

B) Technical correctness
   Best for: data integrity, edge-case handling, consistency

C) Delivery speed
   Best for: unblocking a follow-up phase quickly
```

## Constraints

```text
Which hard constraint should drive the design?

A) Preserve current architecture
   Best for: low blast radius, pattern consistency

B) Minimize migration risk
   Best for: fragile data or shared production flows

C) Optimize for future extensibility
   Best for: expected follow-on features
```

## Delivery Shape

```text
How should this be delivered?

A) Single focused change
   Best for: one workflow, one owner, one clear outcome

B) Staged rollout
   Best for: risky changes that should land in phases

C) Spec only for now
   Best for: design and approval before planning or coding
```

## Data Persistence

```text
Where should [feature] data be stored?

A) Local Only
   Best for: device-specific settings, temporary data

B) Sync to Cloud
   Best for: data needed across devices or shared with team

C) Cloud First
   Best for: reference data, rarely changed content
```

## Offline Behavior

```text
How should [feature] behave offline?

A) Full Functionality
   Trade-off: more sync complexity

B) Read-Only Offline
   Trade-off: simpler logic, less field flexibility

C) Graceful Degradation
   Trade-off: must define the offline core clearly
```

## State Management

```text
How should [feature] manage state?

A) Provider (ChangeNotifier)
   Best for: consistency with current project patterns

B) Local StatefulWidget
   Best for: self-contained UI state

C) Repository Pattern
   Best for: business logic, caching, testability
```

## Navigation Flow

```text
How should users reach [feature]?

A) Bottom Nav Tab
   Best for: frequent access

B) Dashboard Card
   Best for: home-screen workflows

C) Nested in Existing Feature
   Best for: tightly related flows

D) Settings/Menu
   Best for: infrequent configuration tasks
```

## Form Design

```text
How should [data entry] be organized?

A) Single Screen
   Best for: short, fast entry

B) Wizard Steps
   Best for: guided multi-step workflows

C) Tabbed Sections
   Best for: many fields with clear groupings

D) Expandable Sections
   Best for: overview plus optional details
```

## Photo Handling

```text
How should photos be handled for [feature]?

A) Capture Only
   Best for: simple documentation

B) Capture + Annotate
   Best for: marking issues or highlighting areas

C) Gallery Selection
   Best for: importing existing photos

D) OCR Extract
   Best for: extracting structured data from images
```

## Sync Priority

```text
When syncing [data], what matters most?

A) Immediate
   Best for: critical or time-sensitive updates

B) Background
   Best for: heavy data with low urgency

C) Manual
   Best for: explicit user control

D) On Demand
   Best for: lazily loaded reference data
```

## Field Conditions

```text
What field condition should this optimize for first?

A) Bright Sunlight
   Consider: high contrast, stronger borders, larger type

B) Gloved Operation
   Consider: larger touch targets and spacing

C) One-Handed Use
   Consider: bottom-aligned primary actions

D) Quick Entry
   Consider: fewer taps, better defaults, autofill or voice
```
