---
name: no-coauthored-by
enabled: true
event: bash
pattern: Co-Authored-By
action: block
---

**Co-Authored-By detected in commit!**

Per project rules in CLAUDE.md, do not include Co-Authored-By in commits.
The user is the sole author.
