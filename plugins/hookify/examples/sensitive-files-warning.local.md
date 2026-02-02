---
name: sensitive-files
enabled: false
event: write
pattern: \.(env|pem|key|p12|keystore)$
action: block
---

**Attempting to write sensitive file!**

This file type may contain secrets or credentials.

If this is intentional:
1. Ensure the file is in .gitignore
2. Consider using environment variables instead
3. Never commit actual secrets

Set `enabled: false` in this rule if you need to proceed.
