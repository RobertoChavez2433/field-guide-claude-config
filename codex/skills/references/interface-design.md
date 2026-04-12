# Interface Design Reference

Use this for presentation-layer Flutter design and design-system-sensitive UI work.

## Core Rule

State design choices before building widgets.

## Reference Order

1. `.claude/rules/frontend/flutter-ui.md`
2. `.claude/rules/frontend/ui-prototyping.md`
3. `.claude/skills/implement/references/flutter-ui-guide.md`
4. `lib/core/theme/app_theme.dart`

## Guardrails

- Prefer `AppTheme.*` and theme tokens over hardcoded values.
- Reuse spacing and typography tokens.
- Pressure-test for field conditions: glare, gloves, rushed workflows.
- If a new reusable pattern appears, update the repo-owned theme or
  design-system surface instead of pointing at removed upstream docs.

## Upstream Note

There is no current dedicated upstream Claude `interface-design` skill in this
repo. Use the frontend rules plus the live `implement` reference guides.
