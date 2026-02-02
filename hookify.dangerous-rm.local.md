---
name: dangerous-rm-warning
enabled: true
event: bash
pattern: rm\s+(-rf|-fr|--recursive)
action: warn
---

**Potentially dangerous rm command detected**

Please verify:
- Path is correct
- No important files will be deleted
- You have backups if needed
