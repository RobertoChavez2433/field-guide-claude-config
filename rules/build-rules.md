---
paths:
  - "android/**/*"
  - "ios/**/*"
  - "windows/**/*"
  - "packages/flusseract/**/*"
  - "codemagic.yaml"
  - "tools/build.ps1"
---

# Build Rules

- Do not spend CI minutes on blind reruns. Before each retry, record the build id, failing step, first real error, hypothesis, files changed, and local checks run.
- iOS unsigned builds use Codemagic `ios-unsigned` and `flutter build ios --simulator --debug`; signed TestFlight builds are a separate gate after Apple signing is configured.
- For iOS native failures, inspect the full Codemagic step log plus `packages/flusseract` podspecs, script phases, executable bits, CMake policy compatibility, and generated header/library paths before another build.
- Android builds go through `tools/build.ps1 -Platform android`; Windows builds go through `tools/build.ps1 -Platform windows`.
- Do not pass `.env.secret` wholesale to Flutter. Use the repo env wrapper/allowlist and run `scripts/verify_secrets_lockdown.ps1` before CI changes.
- Keep platform version pins aligned with repo config unless the failing dependency proves a version bump is required.
