---
name: env-file-warning
enabled: true
event: bash
pattern: (cat|head|tail|grep|less|more|vim|nano|code)\s+.*\.env
action: warn
---

**Environment File Access Detected**

You are accessing an .env file. These files contain:
- Supabase credentials
- API keys
- Service configurations

Please verify:
- [ ] No credentials copied to other files
- [ ] Not including content in git commits
- [ ] This access is intentional
