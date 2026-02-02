---
name: require-tests
enabled: false
event: stop
pattern: (created|added|implemented|wrote).*\.(dart|py|js|ts)
action: warn
---

**Code changes detected - consider testing**

Before marking this task complete:
- [ ] Run existing tests
- [ ] Add tests for new functionality
- [ ] Verify no regressions

Use: `pwsh -Command "flutter test"`
