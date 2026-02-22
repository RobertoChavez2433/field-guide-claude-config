# UI Prototyping Workflow

Rapid visual design iteration using MCP-powered browser control + live HTML mockups.

## Overview

Instead of writing Flutter production code to see if a design looks right, we use standalone HTML/CSS mockups served in a browser. Two MCP servers enable this:

| Server | Package | Purpose |
|--------|---------|---------|
| **html-sync** | `mcp-html-sync-server` | Create/update HTML pages with real-time hot reload via WebSocket |
| **playwright** | `@playwright/mcp` | Navigate to pages, take screenshots, inject CSS/JS, device emulation |

## When to Use This

- Designing a new screen or feature UI
- Iterating on layout, colors, typography, spacing
- Comparing multiple design options side-by-side
- Getting user approval before writing Flutter code
- Any time the user says "let's prototype" or "show me a mockup"

## When NOT to Use This

- Bug fixes to existing screens (just fix the Flutter code)
- Logic-only changes (no visual component)
- Simple text/color tweaks where the change is obvious

## The Iteration Loop

```
1. Claude calls html-sync create_page → returns URL + page ID
2. User opens URL in browser (auto-refreshes on changes)
3. Claude calls playwright browser_navigate → goes to same URL
4. Claude calls playwright browser_take_screenshot → sees the page
5. User gives feedback ("move X", "change color", "try tabs instead of cards")
6. Claude calls html-sync update_page → browser auto-refreshes
7. Claude takes another screenshot → confirms the change
8. Repeat 5-7 until approved
9. Claude writes production Flutter code matching the approved design
```

## Beer CSS (Material Design 3 Framework)

All mockups use [Beer CSS](https://www.beercss.com/) — a lightweight Material Design 3 CSS framework that closely mirrors Flutter's Material widgets.

### CDN Links (include in every mockup)

```html
<link href="https://cdn.jsdelivr.net/npm/beercss@4/dist/cdn/beer.min.css" rel="stylesheet">
<script type="module" src="https://cdn.jsdelivr.net/npm/beercss@4/dist/cdn/beer.min.js"></script>
<script type="module" src="https://cdn.jsdelivr.net/npm/material-dynamic-colors@1/dist/cdn/material-dynamic-colors.min.js"></script>
```

### HTML Boilerplate

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Screen Name] Mockup</title>
  <link href="https://cdn.jsdelivr.net/npm/beercss@4/dist/cdn/beer.min.css" rel="stylesheet">
  <script type="module" src="https://cdn.jsdelivr.net/npm/beercss@4/dist/cdn/beer.min.js"></script>
  <script type="module" src="https://cdn.jsdelivr.net/npm/material-dynamic-colors@1/dist/cdn/material-dynamic-colors.min.js"></script>
  <style>
    /* Mobile-first: constrain to phone width for Flutter fidelity */
    body { max-width: 412px; margin: 0 auto; min-height: 100vh; }
  </style>
</head>
<body>
  <!-- Mockup content here -->
</body>
</html>
```

### Flutter → Beer CSS Component Mapping

| Flutter Widget | Beer CSS | HTML Pattern |
|---------------|----------|-------------|
| `Scaffold` | page | `<body class="page">` |
| `AppBar` | header, top-app-bar | `<header><nav>...</nav></header>` |
| `NavigationBar` | navigation | `<nav class="bottom">...</nav>` |
| `Card` | card | `<article class="card">...</article>` |
| `ElevatedButton` | button | `<button>Label</button>` |
| `TextButton` | button, text | `<button class="text">Label</button>` |
| `FloatingActionButton` | button, circle, large | `<button class="circle large">+</button>` |
| `TextField` | field | `<div class="field"><input><label>Hint</label></div>` |
| `Chip` | chip | `<span class="chip">Label</span>` |
| `ListTile` | list, row | `<a class="row"><div>...</div></a>` |
| `TabBar` | tabs | `<div class="tabs">...</div>` |
| `Dialog` | dialog, active | `<dialog class="active">...</dialog>` |
| `BottomSheet` | modal, bottom | `<dialog class="modal bottom">` |
| `Switch` | switch | `<label class="switch">` |
| `Checkbox` | checkbox | `<label class="checkbox">` |
| `Divider` | divider | `<hr class="divider">` |
| `ExpansionTile` | expansion | `<details class="expansion">` |
| `LinearProgressIndicator` | progress | `<progress class="progress">` |
| `SnackBar` | snackbar, active | `<div class="snackbar active">` |
| `DataTable` | table | `<table class="table">` |
| `Slider` | slider | `<input type="range" class="slider">` |
| `DropdownButton` | select | `<div class="field"><select>...</select></div>` |

### Theming

Beer CSS supports Material 3 dynamic colors. Set theme in the body:

```html
<!-- Light theme (default) -->
<body class="light">

<!-- Dark theme -->
<body class="dark">

<!-- Custom primary color -->
<body class="light" data-ui="#1B5E20">
```

Use the app's primary color: `data-ui="#1B5E20"` (construction green — adjust to match AppTheme).

### Helper Classes (Layout)

```html
<!-- Spacing -->
<div class="padding">         <!-- p-16 -->
<div class="small-padding">   <!-- p-8 -->
<div class="large-padding">   <!-- p-24 -->
<div class="margin">          <!-- m-16 -->

<!-- Flex layout -->
<div class="row">              <!-- Row -->
<div class="column">           <!-- Column -->
<div class="center-align">     <!-- Center -->
<div class="space-between">    <!-- MainAxisAlignment.spaceBetween -->

<!-- Sizing -->
<div class="max">              <!-- Expanded / fill width -->
<div class="small">            <!-- small variant -->
<div class="medium">           <!-- medium variant -->
<div class="large">            <!-- large variant -->

<!-- Responsive grid -->
<div class="grid">
  <div class="s12 m6 l4">     <!-- full on small, half on medium, third on large -->
</div>
```

## MCP Tool Reference

### html-sync Tools

| Tool | Use For |
|------|---------|
| `create_page` | Create a new HTML mockup page. Returns URL + page ID. |
| `update_page` | Update an existing page by ID. All connected browsers auto-refresh. |
| `destroy_page` | Remove a page when done. |
| `add_scripts` | Inject JavaScript (CDN or inline). |
| `add_stylesheets` | Attach external CSS files. |

### playwright Tools

| Tool | Use For |
|------|---------|
| `browser_navigate` | Go to a URL (the html-sync page URL) |
| `browser_take_screenshot` | Capture what the page looks like (I can see this) |
| `browser_click` | Click elements to test interactions |
| `browser_evaluate` | Run JavaScript to test dynamic behavior |
| `browser_resize` | Simulate different screen sizes |
| `browser_snapshot` | Get accessibility tree (structured page content) |

### Device Emulation

Use `browser_resize` to simulate device sizes:

| Device | Width | Height |
|--------|-------|--------|
| Phone (Android) | 412 | 915 |
| Phone (iPhone 14) | 390 | 844 |
| Tablet | 768 | 1024 |
| Desktop | 1280 | 720 |

## Design Session Workflow

### Starting a Design Session

```
User: "Let's prototype the inspection form screen"
Claude:
  1. Creates HTML with Beer CSS using create_page
  2. Says "Open this URL: http://localhost:3000/abc123"
  3. Navigates playwright to same URL
  4. Takes screenshot to verify rendering
  5. Asks "What would you like to change?"
```

### Iterating

```
User: "Make the header taller, add a FAB for new photos"
Claude:
  1. Calls update_page with modified HTML
  2. User's browser auto-refreshes
  3. Takes screenshot to see the change
  4. Asks "How's this? Anything else?"
```

### Comparing Options

```
User: "Show me tabs vs cards for the section layout"
Claude:
  1. Creates TWO pages (tabs version + cards version)
  2. User opens both URLs side-by-side
  3. Screenshots both for reference
  4. "Which direction do you prefer?"
```

### Finalizing

```
User: "Looks good, build it"
Claude:
  1. Saves final HTML as reference in mockups/ (optional)
  2. Writes Flutter production code matching the approved design
  3. Destroys temporary pages
```

## Tips

- Always constrain mockups to `max-width: 412px` for phone fidelity
- Use the app's actual color palette from `lib/core/theme/`
- Include realistic data (not "Lorem ipsum") — use construction domain terms
- When comparing layouts, create separate pages so user can view side-by-side
- Take a screenshot after every update so you can see what the user sees
