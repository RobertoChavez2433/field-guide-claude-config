---
name: console-log-warning
enabled: false
event: write
pattern: console\.log\(|print\(
action: warn
---

**Debug statement detected**

Consider removing console.log/print statements before committing:
- Use proper logging if needed for production
- Debug statements can leak sensitive information
- They clutter console output
