---
name: feedback_architecture_rules_approach
description: Code reviews should distill into enforceable architecture rules, not one-off fix lists
type: feedback
---

Code review findings should be treated as evidence of missing architectural rules, not individual bugs.

**Why:** The user wants deep patterns and strong architecture enforcement. One-off hacks and individual bug fixes don't prevent recurrence — codified rules do.

**How to apply:** When reviewing code or processing audit findings, distill recurring patterns into architecture rules (in `.claude/rules/`). Rules should be prescriptive and enforceable, not descriptive. When writing plans or specs, reference and enforce existing rules rather than re-discovering the same patterns.
