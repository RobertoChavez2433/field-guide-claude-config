---
paths:
  - "lib/features/**/presentation/**/*.dart"
  - "lib/core/theme/**/*.dart"
  - "lib/core/router/**/*.dart"
  - "lib/core/design_system/**/*.dart"
---

# Flutter UI

- Use `Theme.of(context).colorScheme` or `FieldGuideColors.of(context)` for colors. Do not hardcode `Colors.*` in presentation code.
- Use the design-system owners instead of raw Material widgets where the repo already provides one.
- Use provider-based access patterns (`read`, `watch`, `Consumer`) in UI code. Do not introduce Riverpod.
- Check `mounted` after async gaps before using `context`.
- Prefer `AppNavigator` / `context.appGo` / `context.appPush` over raw `Navigator`. Route definitions live in `lib/core/router/autoroute/` and `lib/core/navigation/`.
- Keep presentation files thin and aligned with the existing controller/provider split.
- Preserve responsive behavior across phone, tablet, and desktop widths.
