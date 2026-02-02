# /analyze Command

Comprehensive session analysis for the Construction Inspector App.

## Usage

```
/analyze                    # Analyze current session
/analyze --last N           # Analyze last N sessions
/analyze --session <id>     # Analyze specific session
/analyze --all              # Full project analysis (all recent sessions)
```

## Alias

`/hookify` without subcommands also triggers analysis mode.

## What It Detects

### 1. Hookify Rule Candidates
Patterns that should become behavioral hooks to prevent unwanted actions.

**Signals detected:**
- User corrections: "Don't", "Stop", "Never"
- Frustrated reactions: "Why did you do that?"
- Repeated mistakes (same error 2+ times)
- Security concerns (credentials, secrets, .env access)

**Output:** Ready-to-use `.claude/hookify.*.local.md` rule files

### 2. Defect Patterns
Bugs and issues matching the `_defects.md` format.

**Categories:**
- `[ASYNC]` - Context safety, dispose issues
- `[E2E]` - Patrol testing patterns
- `[FLUTTER]` - Widget, Provider patterns
- `[DATA]` - Repository, collection access
- `[CONFIG]` - Supabase, credentials, environment

**Signals detected:**
- Stack traces in tool output
- Error/Exception messages
- Test and build failures
- Null/undefined errors

**Output:** Formatted entries for `.claude/autoload/_defects.md`

### 3. Workflow Issues
Development inefficiencies that waste time.

**Signals detected:**
- Same file read 3+ times (missing context)
- Repeated Glob/Grep with same pattern
- Task agent not used for complex searches
- Multiple failed tool attempts

**Output:** Suggestions for agent/skill improvements

### 4. Knowledge Gaps
Missing documentation or context.

**Signals detected:**
- Questions Claude asked the user
- WebSearch/WebFetch for project info
- User corrections of Claude's assumptions
- Uncertainty markers ("I'm not sure", "I don't know")

**Output:** Suggestions for documentation updates

### 5. Code Quality
Technical debt and quality concerns.

**Signals detected:**
- TODO/FIXME comments in written code
- "workaround", "hack", "temporary" mentions
- Similar code in multiple files (duplication)
- Magic numbers

**Output:** Refactoring suggestions

## Output Format

Generates a markdown report with:
- Executive summary (2-3 sentences)
- Findings organized by category
- Suggested file contents (copy-paste ready)
- Prioritized action items
- Checklist of files to update

## Report Mode

This command is **report-only**. It does not modify any files automatically.

You manually:
1. Review the findings
2. Copy relevant suggestions to appropriate files
3. Create hookify rules as needed
4. Update `_defects.md` with new patterns

## Integration with Existing Files

| Finding Type | Update Location |
|-------------|-----------------|
| Hookify rule | Create `.claude/hookify.*.local.md` |
| Defect | Add to `.claude/autoload/_defects.md` |
| Knowledge gap | Update relevant `.md` file |
| Workflow issue | Update agent or skill file |
| Code quality | Create refactoring task |

## Transcript Analysis

For past sessions, the analyzer reads Claude Code transcript files:
```
~/.claude/projects/<project-hash>/<session-id>.jsonl
```

Use `--last N` to analyze recent sessions without knowing specific IDs.

## Examples

### Analyze current session
```
/analyze
```
Produces report based on current conversation.

### Analyze last 3 sessions
```
/analyze --last 3
```
Aggregates patterns across recent sessions.

### Full project retrospective
```
/analyze --all
```
Comprehensive analysis of all available transcripts.

## Related

- `/hookify:list` - List existing hookify rules
- `/hookify:configure` - Create/edit a rule
- `/end-session` - Save session state (run /analyze first!)
