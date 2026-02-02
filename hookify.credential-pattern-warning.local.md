---
name: credential-pattern-warning
enabled: true
event: write
pattern: (password|passwd|secret|api_key|apikey|auth_token)\s*[:=]\s*['"][^'"]+['"]
action: warn
---

**Credential Pattern Detected**

This file appears to contain hardcoded credentials.

Required actions:
- Use environment variables instead
- Reference `.env` files (ensure in .gitignore)
- For Supabase: use `dotenv.env['SUPABASE_KEY']`
