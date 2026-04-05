# Headless CLI Commands

Exact CLI commands for each agent type. All paths MUST be absolute.

**Base path**: `C:/Users/rseba/Projects/Field_Guide_App`

**Output model**: All agents use `--bare` for clean headless execution and `--json-schema` for
structured output. No files are written by agents — everything flows through stdout.

**Live visibility**: Foreground agents pipe through `tee` to show tool calls on terminal via
`stream-filter.py`, then `extract-result.py` extracts only the `structured_output` JSON.

**Background agents**: Use `--output-format json` (not stream-json) since there's no terminal
to stream to. Parse `structured_output` from the JSON result directly.

---

## Implementer (foreground, live visibility)

```bash
CLAUDECODE= claude --bare \
  -p "You are implementing Phase N. Read the plan at <PLAN_PATH> (lines X-Y for your phase). Read the spec at <SPEC_PATH>. Implement exactly as specified. Run lint verification before completing." \
  --model sonnet \
  --tools "Read,Edit,Write,Glob,Grep,Bash" \
  --allowedTools "Read,Edit,Write,Glob,Grep,Bash(pwsh*)" \
  --permission-mode acceptEdits \
  --max-turns 80 \
  --output-format stream-json \
  --verbose \
  --json-schema '<IMPLEMENTER_SCHEMA>' \
  --append-system-prompt-file "C:/Users/rseba/Projects/Field_Guide_App/.claude/skills/implement/reference/worker-rules.md" \
  --no-session-persistence \
  2>&1 | tee >(python3 .claude/tools/stream-filter.py > /dev/tty) \
  | python3 .claude/tools/extract-result.py
```

Replace `N` with the phase number, `<PLAN_PATH>` and `<SPEC_PATH>` with absolute paths,
and `X-Y` with the line range for the phase in the plan file.

The `-p` prompt is constructed inline by the orchestrator — no prompt files.

---

## Reviewer (background, parallel x3)

```bash
CLAUDECODE= claude --bare \
  -p "Review Phase N implementation. Plan: <PLAN_PATH> (lines X-Y). Spec: <SPEC_PATH>. Files to review: <FILE_LIST>. You are the <TYPE> reviewer." \
  --model opus \
  --tools "Read,Glob,Grep" \
  --allowedTools "Read,Glob,Grep" \
  --permission-mode dontAsk \
  --max-turns 40 \
  --output-format json \
  --json-schema '<FINDINGS_SCHEMA>' \
  --append-system-prompt-file "C:/Users/rseba/Projects/Field_Guide_App/.claude/skills/implement/reference/reviewer-rules.md" \
  --append-system-prompt-file "C:/Users/rseba/Projects/Field_Guide_App/.claude/agents/<TYPE>-agent.md" \
  --no-session-persistence
```

Replace `<TYPE>` with one of:
- `completeness-review` (uses `completeness-review-agent.md`)
- `code-review` (uses `code-review-agent.md`)
- `security` (uses `security-agent.md`)

Reviewers use `--output-format json` (not stream-json) since they run in background.
Result is compact findings JSON parsed from `structured_output`.

---

## Fixer (foreground, live visibility)

```bash
CLAUDECODE= claude --bare \
  -p "Fix these findings. Plan: <PLAN_PATH>. Spec: <SPEC_PATH>. Only fix CRITICAL, HIGH, and MEDIUM findings. Skip LOW. Findings: <CONSOLIDATED_FINDINGS_JSON>" \
  --model sonnet \
  --tools "Read,Edit,Write,Glob,Grep,Bash" \
  --allowedTools "Read,Edit,Write,Glob,Grep,Bash(pwsh*)" \
  --permission-mode acceptEdits \
  --max-turns 80 \
  --output-format stream-json \
  --verbose \
  --json-schema '<FIXER_SCHEMA>' \
  --append-system-prompt-file "C:/Users/rseba/Projects/Field_Guide_App/.claude/skills/implement/reference/worker-rules.md" \
  --append-system-prompt-file "C:/Users/rseba/Projects/Field_Guide_App/.claude/agents/code-fixer-agent.md" \
  --no-session-persistence \
  2>&1 | tee >(python3 .claude/tools/stream-filter.py > /dev/tty) \
  | python3 .claude/tools/extract-result.py
```

---

## JSON Schemas

### Implementer Schema

```json
{
  "type": "object",
  "properties": {
    "phase": { "type": "integer" },
    "status": { "enum": ["done", "failed", "blocked"] },
    "files_created": { "type": "array", "items": { "type": "string" } },
    "files_modified": { "type": "array", "items": { "type": "string" } },
    "substeps": { "type": "object" },
    "decisions": { "type": "array", "items": { "type": "string" } },
    "lint_clean": { "type": "boolean" },
    "notes": { "type": "string" }
  },
  "required": ["phase", "status", "files_created", "files_modified", "substeps", "decisions", "lint_clean"]
}
```

### Findings Schema (all 3 reviewer types)

See `findings-schema.json` for the canonical schema.

### Fixer Schema

```json
{
  "type": "object",
  "properties": {
    "findings_received": { "type": "integer" },
    "findings_fixed": { "type": "integer" },
    "findings_skipped": { "type": "integer" },
    "skipped_reasons": { "type": "array", "items": { "type": "string" } },
    "files_modified": { "type": "array", "items": { "type": "string" } },
    "lint_clean": { "type": "boolean" }
  },
  "required": ["findings_received", "findings_fixed", "findings_skipped", "files_modified", "lint_clean"]
}
```

---

## Common Flags

| Flag | Purpose |
|------|---------|
| `CLAUDECODE=` | Bypass nested-session protection (replaces `unset CLAUDECODE`) |
| `--bare` | Headless mode — no interactive UI, clean context |
| `--model` | `sonnet` for implementers/fixers, `opus` for reviewers |
| `--tools` | Declares available tools per agent type |
| `--allowedTools` | Auto-approved tools (no permission prompts) |
| `--permission-mode` | `acceptEdits` for writers, `dontAsk` for read-only |
| `--max-turns` | Prevents runaway agents (80 implementers/fixers, 40 reviewers) |
| `--output-format` | `stream-json` (foreground) or `json` (background) |
| `--verbose` | Include tool calls in stream (foreground only) |
| `--json-schema` | Structured output schema — agent returns typed JSON |
| `--append-system-prompt-file` | Injects static rules (worker/reviewer) + agent definition |
| `--no-session-persistence` | Ephemeral — don't pollute session history |
| `tee >(...) \| extract-result.py` | Live visibility + clean structured output extraction |
