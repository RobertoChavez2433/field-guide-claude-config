# Analyzer Findings Implementation Plan

**Created**: 2026-02-01 (Session 255)
**Status**: READY FOR IMPLEMENTATION
**Ref**: `.claude/plans/conversation-analyzer-findings.md`

---

## Overview

This plan addresses findings from the comprehensive 100-session analysis. Scope:
- 4 Hookify security rules + auto-disable mechanism
- Python UTF-8 encoding fixes
- Test file splitting (2 large files)
- Documentation improvements (3 new docs)

---

## Phase 1: Hookify Security Rules

**Files to Create**: 4 new rule files

### 1.1 `.claude/hookify.env-file-warning.local.md`

```markdown
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
```

### 1.2 `.claude/hookify.credential-pattern-warning.local.md`

```markdown
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
```

### 1.3 `.claude/hookify.hardcoded-secret-warning.local.md`

```markdown
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
```

### 1.4 `.claude/hookify.sensitive-files-warning.local.md`

```markdown
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
```

**Verification**:
```bash
# Test .env detection
echo "test" > test.env && cat test.env  # Should trigger warning
rm test.env

# Verify rules loaded
python .claude/plugins/hookify/core/config_loader.py
```

---

## Phase 2: Auto-Disable Mechanism

**Goal**: After 5 triggers of the same rule, auto-disable it for the session to prevent warning fatigue.

### 2.1 Modify `.claude/plugins/hookify/core/rule_engine.py`

Add at top of file (after imports):
```python
# Auto-disable threshold
AUTO_DISABLE_THRESHOLD = 5

# Session state (persists until Claude Code restarts)
_session_trigger_counts = {}  # {rule_name: count}
_disabled_rules = set()  # Rules auto-disabled this session
```

Modify `evaluate_rules()` method to add before returning result:
```python
def evaluate_rules(self, event_type: str, tool_name: str, content: str) -> dict:
    # ... existing matching logic ...

    for rule in matching_rules:
        # Skip if auto-disabled
        if rule.name in _disabled_rules:
            continue

        # Check if matches
        if self._matches_rule(rule, content):
            # Increment counter
            _session_trigger_counts[rule.name] = _session_trigger_counts.get(rule.name, 0) + 1

            # Check for auto-disable
            if _session_trigger_counts[rule.name] >= AUTO_DISABLE_THRESHOLD:
                _disabled_rules.add(rule.name)
                print(f"[hookify] Rule '{rule.name}' auto-disabled after {AUTO_DISABLE_THRESHOLD} triggers",
                      file=sys.stderr)
                # Still return this result, but future triggers won't fire

            return {
                "continue": rule.action != "block",
                "message": rule.message,
                # ... rest of result
            }
```

### 2.2 Add reset function (optional, for testing):
```python
def reset_session_state():
    """Reset auto-disable state. Call at session start if needed."""
    global _session_trigger_counts, _disabled_rules
    _session_trigger_counts = {}
    _disabled_rules = set()
```

**Verification**:
```bash
# Trigger same pattern 6 times
# 5th should warn, 6th should be silent
# Check stderr for "[hookify] Rule X auto-disabled" message
```

---

## Phase 3: Python UTF-8 Fixes

**Files to Modify**: 10 Python files in `.claude/plugins/hookify/`

### 3.1 Add Encoding Declaration

Add to line 1 (or line 2 after shebang) of ALL Python files:
```python
# -*- coding: utf-8 -*-
```

**Files**:
- `core/pattern_extractors.py`
- `core/transcript_parser.py`
- `core/config_loader.py`
- `core/rule_engine.py`
- `core/__init__.py`
- `hooks/pretooluse.py`
- `hooks/posttooluse.py`
- `hooks/stop.py`
- `hooks/userpromptsubmit.py`
- `hooks/__init__.py`
- `matchers/__init__.py`
- `utils/__init__.py`

### 3.2 Add Windows Console UTF-8 Wrapper

Add to `pattern_extractors.py` and `transcript_parser.py` (in CLI section):

```python
# In the if __name__ == "__main__": section, at the start:
import io

# Windows console fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```

### 3.3 Add ASCII Fallback Helper

Add to `pattern_extractors.py`:
```python
def _ascii_safe(text: str) -> str:
    """Replace Unicode characters with ASCII equivalents."""
    replacements = {
        '\u2192': '->',   # arrow
        '\u2190': '<-',   # left arrow
        '\u2713': '[OK]', # checkmark
        '\u2717': '[X]',  # x mark
        '\u2026': '...',  # ellipsis
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    return text
```

**Verification**:
```bash
pwsh -Command "python .claude/plugins/hookify/core/pattern_extractors.py --help"
# Should not throw UnicodeEncodeError
```

---

## Phase 4: Test File Splitting

### 4.1 Split `row_state_machine_test.dart`

**Source**: `test/features/pdf/parsers/row_state_machine_test.dart` (1,042 lines)

**Create**: `test/features/pdf/parsers/parsed_row_data_test.dart`
- Lines 1-6: imports
- Lines 7-178: `group('ParsedRowData', ...)` with all nested tests
- ~180 lines total, 29 tests

**Keep**: `test/features/pdf/parsers/row_state_machine_test.dart`
- Lines 1-6: imports (update to remove ParsedRowData if not needed)
- Lines 180-1042: `group('RowStateMachine', ...)` with all nested tests
- ~860 lines total, 55 tests

### 4.2 Split `project_setup_screen_test.dart`

**Source**: `test/features/projects/presentation/screens/project_setup_screen_test.dart` (619 lines)

**Create**: `test/features/projects/presentation/screens/project_setup_screen_logic_test.dart`
- Lines 1-18: imports
- Lines 19-530: `group('ProjectSetupScreen Logic', ...)`
- ~515 lines total, 49 tests

**Create**: `test/features/projects/presentation/screens/project_setup_screen_ui_state_test.dart`
- Lines 1-18: imports (same as original)
- Lines 532-619: `group('ProjectSetupScreen UI State', ...)`
- ~90 lines total, 14 tests

**Delete original**: `project_setup_screen_test.dart` (replaced by two new files)

**Verification**:
```bash
pwsh -Command "flutter test test/features/pdf/parsers/"
pwsh -Command "flutter test test/features/projects/presentation/screens/"
# All tests should pass, same count as before
```

---

## Phase 5: Documentation Improvements

### 5.1 Create `.claude/logs/archive-index.md`

```markdown
# Archive Navigation Index

**Last Updated**: 2026-02-01

## State Archive
| Session Range | Date Range | File | Line Numbers |
|---------------|------------|------|--------------|
| 193-241 | Jan 2026 | state-archive.md | Lines 8-95 |
| 242-254 | Feb 2026 | autoload/_state.md | Active (current) |

## Defects Archive
| Category | Status | File | Count |
|----------|--------|------|-------|
| [ASYNC] | Archived | defects-archive.md | 3 |
| [E2E] | Archived | defects-archive.md | 4 |
| [ASYNC] | Active | autoload/_defects.md | 3 |
| [E2E] | Active | autoload/_defects.md | 6 |

## Quick Lookup
- **Find Session 230**: `grep "Session 230" .claude/logs/state-archive.md`
- **Find all [E2E] defects**: `grep "\[E2E\]" .claude/autoload/_defects.md .claude/logs/defects-archive.md`
```

### 5.2 Create `.claude/commands/session-checklist.md`

```markdown
# Session Workflow Checklist

Single reference for starting and ending sessions.

---

## Starting a Session

### 1. Load Context
Read these files (in order):
1. `.claude/autoload/_state.md` - Current state
2. `.claude/autoload/_defects.md` - Active patterns
3. `.claude/autoload/_tech-stack.md` - Tech reference

### 2. Check Git Status
```bash
git status && git log --oneline -3
```

### 3. Review Defects
Before starting work, scan defects for patterns matching your task:
- PDF work? Watch for async context issues
- E2E tests? Remember scrollTo() before tap()
- Forms? Check auto-fill patterns

### 4. Confirm Focus
Ask user: "What would you like to focus on this session?"

---

## Ending a Session

### 1. Quality Checks
```bash
pwsh -Command "flutter analyze"
git status
git diff --stat
```

### 2. Update State
Add to `_state.md`:
```markdown
### Session N (YYYY-MM-DD)
**Work**: [1-2 sentence summary]
**Commits**: `abc1234` or "Pending"
**Ref**: @path/to/relevant/file
```

### 3. Log New Defects
If patterns discovered, add to `_defects.md`:
```markdown
### [CATEGORY] YYYY-MM-DD: Title
**Pattern**: What to avoid
**Prevention**: How to prevent
**Ref**: @path/to/file.dart
```

### 4. Check Rotation
- `_state.md` has >10 sessions? Move oldest to `state-archive.md`
- `_defects.md` has >15 entries? Move oldest to `defects-archive.md`
- Update `archive-index.md` with new locations

### 5. Commit
```bash
git add -A && git commit -m "session N: summary"
```
```

### 5.3 Create `.claude/logs/README.md`

```markdown
# Logs Directory

## Active State (Hot Memory)
Located in `../autoload/`:
- `_state.md` - Current 10 sessions (loaded every session)
- `_defects.md` - Current 15 defects (loaded every session)
- `_tech-stack.md` - Tech reference (loaded every session)

## Archives (Cold Storage)
- `state-archive.md` - Sessions 193+, auto-rotated when >10 active
- `defects-archive.md` - Older defects, auto-rotated when >15 active
- `archive-index.md` - Navigation helper for quick lookup

## Rotation Rules
1. When `_state.md` exceeds 10 sessions:
   - Move oldest entry to `state-archive.md`
   - Update `archive-index.md` with new line numbers

2. When `_defects.md` exceeds 15 entries:
   - Move oldest entries to `defects-archive.md`
   - Update `archive-index.md` with new counts

## Deprecated Files
- `session-log.md` - Historical artifact, duplicates `_state.md`. Do not update.
```

---

## Implementation Order

| Order | Phase | Files | Parallel? |
|-------|-------|-------|-----------|
| 1 | Phase 1 (Security Rules) | 4 new | Yes (with 3, 4, 5) |
| 2 | Phase 3 (UTF-8 Fixes) | 12 modified | Yes (with 1, 4, 5) |
| 3 | Phase 4 (Test Splitting) | 4 new, 2 replaced | Yes (with 1, 3, 5) |
| 4 | Phase 5 (Docs) | 3 new | Yes (with 1, 3, 4) |
| 5 | Phase 2 (Auto-Disable) | 1-2 modified | No (after Phase 1) |

**Recommended**: Run Phases 1, 3, 4, 5 in parallel, then Phase 2.

---

## Rollback Instructions

### Phase 1
```bash
rm .claude/hookify.env-file-warning.local.md
rm .claude/hookify.credential-pattern-warning.local.md
rm .claude/hookify.hardcoded-secret-warning.local.md
rm .claude/hookify.sensitive-files-warning.local.md
```

### Phase 2
```bash
git checkout .claude/plugins/hookify/core/rule_engine.py
```

### Phase 3
```bash
git checkout .claude/plugins/hookify/
```

### Phase 4
```bash
git checkout test/features/pdf/parsers/row_state_machine_test.dart
git checkout test/features/projects/presentation/screens/project_setup_screen_test.dart
rm test/features/pdf/parsers/parsed_row_data_test.dart
rm test/features/projects/presentation/screens/project_setup_screen_logic_test.dart
rm test/features/projects/presentation/screens/project_setup_screen_ui_state_test.dart
```

### Phase 5
```bash
rm .claude/logs/archive-index.md
rm .claude/logs/README.md
rm .claude/commands/session-checklist.md
```

---

## Summary

| Phase | New Files | Modified Files | Effort |
|-------|-----------|----------------|--------|
| 1. Security Rules | 4 | 0 | Low |
| 2. Auto-Disable | 0 | 1-2 | Medium |
| 3. UTF-8 Fixes | 0 | 12 | Low |
| 4. Test Splitting | 4 | 2 (replaced) | Low |
| 5. Docs | 3 | 0 | Low |
| **Total** | **11** | **15** | **Low-Medium** |

---

*Ready for implementation approval.*
