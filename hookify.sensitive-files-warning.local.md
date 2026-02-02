---
name: sensitive-files-warning
enabled: true
event: write
pattern: \.(keystore|jks|pem|key|p12|pfx|cer|crt)$
action: warn
---

**Sensitive File Write Detected**

Writing to a file with sensitive extension:
- `.keystore/.jks` - Android signing keys
- `.pem/.key` - Private keys
- `.p12/.pfx` - PKCS12 certificates

Please verify:
- [ ] File is in .gitignore
- [ ] Not committing actual secrets
- [ ] Using secure storage location
