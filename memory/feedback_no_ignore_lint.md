---
name: No ignore comments for lint suppression
description: Never use // ignore: comments to suppress lint violations — always fix the root cause
type: feedback
---

Never use `// ignore:` comments to suppress lint violations. Always fix the root cause of the violation.

**Why:** User explicitly rejected using ignore comments to silence lint errors. "We don't use ignore to just ignore errors." Suppression masks problems and creates maintenance debt.

**How to apply:** When a lint rule fires, find a real code fix (type promotion, proper exception types, annotations, etc.). The only acceptable `// ignore:` usage is for pre-existing ignores that need `document_ignores` reason text added.
