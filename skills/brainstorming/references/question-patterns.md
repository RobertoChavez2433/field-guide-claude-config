# Question Patterns

Multiple choice templates for common Flutter/construction domain decisions.

## Data Persistence

```
Where should [feature] data be stored?

A) **Local Only** - SQLite only, no cloud sync
   Best for: Device-specific settings, temporary data

B) **Sync to Cloud** - SQLite + Supabase sync
   Best for: Data needed across devices, shared with team

C) **Cloud First** - Fetch from Supabase, cache locally
   Best for: Reference data, rarely changes
```

## Offline Behavior

```
How should [feature] behave offline?

A) **Full Functionality** - Works completely offline, syncs later
   Trade-off: More complex sync logic

B) **Read-Only Offline** - Can view but not modify
   Trade-off: Simpler but limits field use

C) **Graceful Degradation** - Core works offline, extras need network
   Trade-off: Must define what's "core"
```

## State Management

```
How should [feature] manage state?

A) **Provider (ChangeNotifier)** - Current project pattern
   Best for: Consistency with existing code

B) **Local StatefulWidget** - Self-contained component
   Best for: UI-only state, no sharing needed

C) **Repository Pattern** - Provider delegates to repository
   Best for: Business logic + caching
```

## Navigation Flow

```
How should users navigate to [feature]?

A) **Bottom Nav Tab** - Always visible, one tap
   Best for: Frequently used features

B) **Dashboard Card** - From home screen
   Best for: Daily workflow actions

C) **Nested in Feature** - Within existing flow
   Best for: Related to parent feature

D) **Settings/Menu** - Accessed via settings
   Best for: Configuration, rarely used
```

## Form Design

```
How should [data entry] be organized?

A) **Single Screen** - All fields on one page
   Best for: < 5 fields, quick entry

B) **Wizard Steps** - Multi-step with progress
   Best for: Complex forms, guided input

C) **Tabbed Sections** - Tabs for field groups
   Best for: Many fields, logical groupings

D) **Expandable Sections** - Collapsible cards
   Best for: Optional sections, overview + details
```

## Photo Handling

```
How should photos be handled for [feature]?

A) **Capture Only** - Take photo, attach to entry
   Best for: Documentation, simple attachment

B) **Capture + Annotate** - Add markers, text overlay
   Best for: Marking defects, highlighting areas

C) **Gallery Selection** - Choose existing photos
   Best for: Historical reference, batch import

D) **OCR Extract** - Photo to data extraction
   Best for: Importing from paper forms
```

## Sync Priority

```
When syncing [data], what's the priority?

A) **Immediate** - Sync as soon as online
   Best for: Critical data, time-sensitive

B) **Background** - Sync during idle time
   Best for: Large data, not urgent

C) **Manual** - User triggers sync
   Best for: Control over data usage

D) **On Demand** - Sync when accessed
   Best for: Reference data, lazy loading
```

## Field Conditions

```
What field conditions should [feature] optimize for?

A) **Bright Sunlight** - High contrast, large text
   Consider: Dark backgrounds, thick borders

B) **Gloved Operation** - Large touch targets
   Consider: 48dp minimum, spacing between buttons

C) **One-Handed Use** - Bottom-aligned actions
   Consider: FABs, swipe gestures

D) **Quick Entry** - Minimal taps
   Consider: Smart defaults, auto-fill, voice
```
