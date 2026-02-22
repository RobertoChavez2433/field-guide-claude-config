---
paths:
  - "mockups/**"
  - ".claude/docs/guides/ui-prototyping-workflow.md"
description: "Auto-loads when working with UI mockups or prototyping workflow"
---

# UI Prototyping Rules

## When to Prototype

Before writing Flutter UI code for new screens or major redesigns, offer to create an HTML mockup first:
- "Want me to prototype this in the browser before we write Flutter code?"
- This saves time by iterating visually before committing to production code.

## MCP Servers Required

| Server | Purpose |
|--------|---------|
| `html-sync` | Create/update HTML pages with live hot reload |
| `playwright` | Navigate, screenshot, interact with browser |

If either is unavailable, fall back to describing the layout or use inline HTML files opened manually.

## Workflow Quick Reference

1. `html-sync:create_page` → get URL + page ID
2. Tell user to open the URL
3. `playwright:browser_navigate` → go to same URL
4. `playwright:browser_take_screenshot` → see the result
5. User gives feedback → `html-sync:update_page` → auto-refresh
6. Repeat until approved → write Flutter code

## Mockup Standards

- Always use Beer CSS (Material Design 3): `beercss@4`
- Constrain to `max-width: 412px` for phone fidelity
- Use the app's color palette (check `lib/core/theme/`)
- Use realistic construction domain data, not placeholder text
- Include bottom nav if the screen has it in production

## Full Reference

See `.claude/docs/guides/ui-prototyping-workflow.md` for:
- Beer CSS CDN links and boilerplate
- Flutter → Beer CSS component mapping table
- Device emulation sizes
- Design session workflow patterns
