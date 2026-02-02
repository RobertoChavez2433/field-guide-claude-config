# Full Session Analysis Instructions

**Created**: 2026-02-01 (Session 254)
**Status**: Ready for execution
**Ref**: @.claude/plugins/hookify/

## Objective

Run a FULL and COMPREHENSIVE analysis of all available transcripts focusing on:

1. **Hookify Rule Candidates** - Behavioral patterns to prevent
2. **Defect Patterns** - Bugs matching `_defects.md` format
3. **Workflow Inefficiencies** - Repeated searches, missed delegations

## Execution Steps

### Step 1: Find All Transcripts

```bash
cd "C:/Users/rseba/Projects/Field Guide App"
python .claude/plugins/hookify/core/transcript_parser.py --find .
```

### Step 2: Analyze Each Transcript

For each transcript found, run:

```bash
python .claude/plugins/hookify/core/transcript_parser.py <path.jsonl>
```

### Step 3: Full Pattern Extraction

```python
import sys
sys.path.insert(0, '.claude/plugins/hookify/core')
from transcript_parser import parse_transcript, find_transcripts, get_session_summary
from pattern_extractors import extract_all_patterns
from pathlib import Path

# Analyze last 20 sessions
transcripts = find_transcripts(Path('.'), limit=20)

all_hookify = []
all_defects = []
all_workflow = []

for t in transcripts:
    messages = parse_transcript(t)
    result = extract_all_patterns(messages)
    all_hookify.extend(result.hookify_patterns)
    all_defects.extend(result.defect_patterns)
    all_workflow.extend(result.workflow_patterns)

print(f"Total hookify patterns: {len(all_hookify)}")
print(f"Total defect patterns: {len(all_defects)}")
print(f"Total workflow patterns: {len(all_workflow)}")
```

### Step 4: Generate Report

Use the template at `.claude/plugins/hookify/templates/analysis-report.md`

#### Required Report Sections

**1. Hookify Rules Report**
- List ALL patterns with severity High or Medium
- Group by event type (bash, write, edit)
- Provide ready-to-use rule files
- Note patterns that appeared 3+ times

**2. Defect Patterns Report**
- Categorize by: [ASYNC], [E2E], [FLUTTER], [DATA], [CONFIG]
- Cross-reference with existing `_defects.md` to avoid duplicates
- Format each as Pattern/Prevention/Ref
- Prioritize by severity

**3. Workflow Patterns Report**
- Identify most-repeated file reads (indicate missing context)
- Find repeated search patterns
- Note where Task agent should have been used
- Calculate total time/effort wasted

### Step 5: Output Locations

Save comprehensive reports to:
- `.claude/logs/analysis-report-YYYY-MM-DD.md` - Full report
- `.claude/hookify.*.local.md` - New rules (manual creation)
- `.claude/autoload/_defects.md` - New defects (manual addition)

## Analysis Focus Areas

### Hookify Patterns to Look For
- User saying "don't", "stop", "never"
- Security concerns (.env, credentials, secrets)
- Git-related (Co-Authored-By, force push)
- Flutter-specific (Git Bash for flutter commands)

### Defect Categories (existing)
- `[ASYNC]` - Context after await, dispose issues
- `[E2E]` - Patrol testing, widget visibility
- `[FLUTTER]` - Provider, setState, deprecated APIs
- `[DATA]` - Collection access, firstWhere without orElse
- `[CONFIG]` - Supabase config, environment

### Workflow Red Flags
- Same file read 3+ times = missing context
- Glob/Grep same pattern 3+ times = should use Task agent
- Multiple failed attempts = needs better error handling

## Expected Deliverables

1. **Hookify Rules**: 5-10 new `.local.md` rule files ready for use
2. **Defect Updates**: 3-5 new patterns for `_defects.md`
3. **Workflow Recommendations**: Agent/skill improvements
4. **Summary Statistics**: Message counts, tool usage, error rates

## Notes

- This analysis should cover at least 10-20 sessions
- Focus on HIGH and MEDIUM severity patterns
- Deduplicate similar findings
- Provide copy-paste ready outputs
