---
name: hardcoded-secret-warning
enabled: true
event: edit
pattern: (secret|password|token|private_key)\s*[:=]\s*['"][A-Za-z0-9+/=_-]{10,}['"]
action: warn
---

**Hardcoded Secret in Code Edit**

Editing code that may contain a hardcoded secret (long alphanumeric string).

For this project:
- Supabase keys go in `.env`
- Use `Platform.environment['KEY']` or `dotenv.env['KEY']`
- See `lib/core/config/supabase_config.dart` for patterns
