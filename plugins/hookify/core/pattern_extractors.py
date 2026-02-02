# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Pattern detection for conversation analysis."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Handle both package and standalone imports
try:
    from .transcript_parser import Message, ToolCall, ToolResult
except ImportError:
    from transcript_parser import Message, ToolCall, ToolResult


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


class Severity(Enum):
    """Pattern severity levels."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class DefectCategory(Enum):
    """Defect categories matching _defects.md."""
    ASYNC = "[ASYNC]"
    E2E = "[E2E]"
    FLUTTER = "[FLUTTER]"
    DATA = "[DATA]"
    CONFIG = "[CONFIG]"


@dataclass
class HookifyPattern:
    """A pattern that should become a hookify rule."""
    name: str
    severity: Severity
    event: str  # bash, write, edit, stop
    pattern: str
    action: str  # warn, block
    evidence: List[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class DefectPattern:
    """A bug pattern for _defects.md."""
    title: str
    category: DefectCategory
    severity: Severity
    pattern: str
    prevention: str
    evidence: List[str] = field(default_factory=list)
    ref: Optional[str] = None
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


@dataclass
class WorkflowPattern:
    """A workflow inefficiency pattern."""
    description: str
    frequency: int
    impact: str  # Description of time/effort wasted
    current_behavior: str
    suggestion: str
    affected_agents: List[str] = field(default_factory=list)


@dataclass
class KnowledgeGap:
    """Missing documentation or context."""
    topic: str
    category: str  # Architecture, API, Business Logic, Config
    missing_info: str
    suggested_location: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class CodeQualityIssue:
    """Code quality concern."""
    description: str
    issue_type: str  # TODO, Workaround, Duplication, MagicNumber, ErrorHandling
    files: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    suggestion: str = ""


# ============================================================================
# Hookify Pattern Extraction
# ============================================================================

# User correction patterns that suggest hooks
CORRECTION_PATTERNS = [
    (r"(?i)\bdon'?t\s+use\b", "Usage restriction"),
    (r"(?i)\bstop\s+doing\b", "Behavioral correction"),
    (r"(?i)\bnever\s+\w+", "Prohibition"),
    (r"(?i)\bwhy\s+did\s+you\b", "Frustrated question"),
    (r"(?i)\bthat'?s\s+wrong\b", "Explicit correction"),
    (r"(?i)\bplease\s+don'?t\b", "Polite prohibition"),
    (r"(?i)\bdo\s+not\b", "Direct prohibition"),
    (r"(?i)\bshouldn'?t\b", "Negative suggestion"),
    (r"(?i)\bi\s+said\s+(no|not|don'?t)\b", "Repeated instruction"),
]

# Security-sensitive patterns
SECURITY_PATTERNS = [
    (r"\.env", "Environment file access"),
    (r"credentials", "Credentials handling"),
    (r"password", "Password handling"),
    (r"secret", "Secret handling"),
    (r"api[_-]?key", "API key handling"),
    (r"token", "Token handling"),
]


def extract_hookify_patterns(messages: List[Message]) -> List[HookifyPattern]:
    """
    Detect patterns suitable for hookify rules.

    Signals:
    - User says "Don't", "Stop", "Never", "Why did you"
    - User reverts Claude's changes
    - Same mistake repeated 2+ times
    - Security-related corrections

    Args:
        messages: List of parsed messages

    Returns:
        List of HookifyPattern objects
    """
    patterns = []
    corrections = []

    # Collect user corrections
    for message in messages:
        if message.role != "user":
            continue

        for regex, label in CORRECTION_PATTERNS:
            if re.search(regex, message.content):
                corrections.append({
                    "content": message.content,
                    "label": label,
                    "pattern": regex
                })
                break

    # Analyze corrections for rule candidates
    if corrections:
        # Group similar corrections
        by_label = {}
        for c in corrections:
            label = c["label"]
            if label not in by_label:
                by_label[label] = []
            by_label[label].append(c["content"])

        # Create patterns for repeated corrections
        for label, contents in by_label.items():
            if len(contents) >= 2 or any("never" in c.lower() or "always" in c.lower() for c in contents):
                # Try to extract the specific command/action mentioned
                pattern = _extract_action_pattern(contents)
                if pattern:
                    patterns.append(HookifyPattern(
                        name=_generate_rule_name(label, contents[0]),
                        severity=Severity.MEDIUM if len(contents) >= 2 else Severity.LOW,
                        event="bash",  # Default, may need refinement
                        pattern=pattern,
                        action="warn",
                        evidence=contents[:3],
                        rationale=f"User expressed {label.lower()} {len(contents)} time(s)"
                    ))

    # Check for security-related patterns in tool calls
    security_issues = _find_security_concerns(messages)
    for issue in security_issues:
        patterns.append(HookifyPattern(
            name=f"security-{issue['type'].lower().replace(' ', '-')}",
            severity=Severity.HIGH,
            event=issue["event"],
            pattern=issue["pattern"],
            action="warn",
            evidence=[issue["evidence"]],
            rationale=f"Security concern: {issue['type']}"
        ))

    return patterns


def _extract_action_pattern(corrections: List[str]) -> Optional[str]:
    """Extract the action/command pattern from correction messages."""
    # Look for quoted commands or specific tool mentions
    for content in corrections:
        # Find quoted content
        quoted = re.findall(r'["\']([^"\']+)["\']', content)
        if quoted:
            return re.escape(quoted[0])

        # Find command-like words
        cmd_match = re.search(r'\b(rm|delete|remove|git|flutter|npm|pip)\s+\S+', content, re.I)
        if cmd_match:
            return re.escape(cmd_match.group(0))

    return None


def _generate_rule_name(label: str, content: str) -> str:
    """Generate a rule name from label and content."""
    # Extract key words
    words = re.findall(r'\b\w{4,}\b', content.lower())[:3]
    if words:
        return f"{label.lower().replace(' ', '-')}-{'-'.join(words)}"
    return label.lower().replace(' ', '-')


def _find_security_concerns(messages: List[Message]) -> List[Dict[str, Any]]:
    """Find security-related patterns in tool usage."""
    concerns = []

    for message in messages:
        for tool_call in message.tool_calls:
            tool_input_str = str(tool_call.input)

            for pattern, concern_type in SECURITY_PATTERNS:
                if re.search(pattern, tool_input_str, re.I):
                    concerns.append({
                        "type": concern_type,
                        "event": tool_call.name.lower(),
                        "pattern": pattern,
                        "evidence": f"{tool_call.name}: {tool_input_str[:200]}"
                    })
                    break

    return concerns


# ============================================================================
# Defect Pattern Extraction
# ============================================================================

# Error patterns mapped to defect categories
ERROR_CATEGORY_PATTERNS = {
    DefectCategory.ASYNC: [
        r"(?i)context.*after.*await",
        r"(?i)disposed.*controller",
        r"(?i)setState.*mounted",
        r"(?i)async.*dispose",
        r"(?i)Future.*null",
        r"(?i)unawaited",
    ],
    DefectCategory.E2E: [
        r"(?i)patrol",
        r"(?i)integration.?test",
        r"(?i)widget.*not.*found",
        r"(?i)finder.*empty",
        r"(?i)tap.*failed",
    ],
    DefectCategory.FLUTTER: [
        r"(?i)widget.*overflow",
        r"(?i)renderbox",
        r"(?i)setState",
        r"(?i)provider.*not.*found",
        r"(?i)context.*deactivated",
    ],
    DefectCategory.DATA: [
        r"(?i)firstWhere.*orElse",
        r"(?i)\.first\b.*empty",
        r"(?i)null.*access",
        r"(?i)repository",
        r"(?i)collection.*empty",
    ],
    DefectCategory.CONFIG: [
        r"(?i)supabase",
        r"(?i)environment",
        r"(?i)configuration",
        r"(?i)credential",
        r"(?i)\.env",
    ],
}


def extract_defect_patterns(messages: List[Message]) -> List[DefectPattern]:
    """
    Detect patterns for _defects.md.

    Signals:
    - Stack traces in tool results
    - "Error:", "Exception:", "Failed:" in output
    - Test failures
    - Build failures
    - Null/undefined errors

    Args:
        messages: List of parsed messages

    Returns:
        List of DefectPattern objects
    """
    defects = []
    seen_errors = set()

    for message in messages:
        for result in message.tool_results:
            output = result.output
            error = result.error

            # Combine output and error for analysis
            full_text = f"{output}\n{error or ''}"

            # Skip if too short to be meaningful
            if len(full_text.strip()) < 20:
                continue

            # Look for error indicators
            error_match = re.search(
                r'(?i)(error|exception|failed|traceback|stacktrace)',
                full_text
            )
            if not error_match:
                continue

            # Avoid duplicates
            error_key = full_text[:100]
            if error_key in seen_errors:
                continue
            seen_errors.add(error_key)

            # Categorize the error
            category = _categorize_error(full_text)

            # Extract title and pattern
            title = _extract_error_title(full_text)
            pattern_desc = _extract_pattern_description(full_text)
            prevention = _suggest_prevention(full_text, category)

            # Extract file reference if present
            ref = _extract_file_reference(full_text)

            defects.append(DefectPattern(
                title=title,
                category=category,
                severity=_assess_severity(full_text),
                pattern=pattern_desc,
                prevention=prevention,
                evidence=[full_text[:500]],
                ref=ref
            ))

    return defects


def _categorize_error(text: str) -> DefectCategory:
    """Categorize an error based on content."""
    for category, patterns in ERROR_CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return category

    # Default to FLUTTER for general errors
    return DefectCategory.FLUTTER


def _extract_error_title(text: str) -> str:
    """Extract a concise title from error text."""
    # Look for common error patterns
    patterns = [
        r"(?i)(Error|Exception):\s*(.{10,60})",
        r"(?i)^([\w.]+Error):",
        r"(?i)^([\w.]+Exception):",
        r"(?i)failed\s+to\s+(.{10,40})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            title = match.group(1) if match.lastindex == 1 else match.group(2)
            return title.strip()[:60]

    # Fallback: first meaningful line
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if lines:
        return lines[0][:60]

    return "Unknown Error"


def _extract_pattern_description(text: str) -> str:
    """Extract what pattern to avoid from error text."""
    # Look for the problematic code or action
    patterns = [
        r"(?i)cannot\s+(.{10,50})",
        r"(?i)unable\s+to\s+(.{10,50})",
        r"(?i)failed\s+(.{10,50})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    return "See error details"


def _suggest_prevention(text: str, category: DefectCategory) -> str:
    """Suggest prevention based on error and category."""
    # Category-specific suggestions
    suggestions = {
        DefectCategory.ASYNC: "Check mounted state after await; use proper dispose patterns",
        DefectCategory.E2E: "Use scrollTo() before tap(); verify widget visibility",
        DefectCategory.FLUTTER: "Check widget state before setState; verify Provider access",
        DefectCategory.DATA: "Use firstOrNull instead of first; validate collections before access",
        DefectCategory.CONFIG: "Check isConfigured before accessing services; validate environment",
    }

    return suggestions.get(category, "Review error context and add appropriate guards")


def _extract_file_reference(text: str) -> Optional[str]:
    """Extract file path reference from error text."""
    # Look for Dart file paths
    match = re.search(r'(lib/[\w/]+\.dart)', text)
    if match:
        return f"@{match.group(1)}"

    match = re.search(r'(test/[\w/]+\.dart)', text)
    if match:
        return f"@{match.group(1)}"

    return None


def _assess_severity(text: str) -> Severity:
    """Assess error severity."""
    text_lower = text.lower()

    if any(w in text_lower for w in ["crash", "fatal", "critical", "unhandled"]):
        return Severity.CRITICAL

    if any(w in text_lower for w in ["exception", "failed", "error"]):
        return Severity.HIGH

    if any(w in text_lower for w in ["warning", "deprecat"]):
        return Severity.MEDIUM

    return Severity.LOW


# ============================================================================
# Workflow Pattern Extraction
# ============================================================================

def extract_workflow_patterns(messages: List[Message]) -> List[WorkflowPattern]:
    """
    Detect workflow inefficiencies.

    Signals:
    - Same file read 3+ times (missing context)
    - Glob/Grep repeated for same pattern
    - Task agent not used for complex searches
    - Multiple failed attempts at same task

    Args:
        messages: List of parsed messages

    Returns:
        List of WorkflowPattern objects
    """
    patterns = []

    # Track file reads
    file_reads = {}
    # Track search patterns
    search_patterns = {}
    # Track failed tool calls
    failed_tools = {}

    for message in messages:
        for tool_call in message.tool_calls:
            tool_name = tool_call.name

            if tool_name == "Read":
                path = tool_call.input.get("file_path", "")
                file_reads[path] = file_reads.get(path, 0) + 1

            elif tool_name in ("Glob", "Grep"):
                pattern = tool_call.input.get("pattern", "")
                key = f"{tool_name}:{pattern}"
                search_patterns[key] = search_patterns.get(key, 0) + 1

        # Track errors
        for result in message.tool_results:
            if result.error or "error" in result.output.lower()[:200]:
                tool_name = result.tool_name
                failed_tools[tool_name] = failed_tools.get(tool_name, 0) + 1

    # Detect repeated file reads
    for path, count in file_reads.items():
        if count >= 3:
            patterns.append(WorkflowPattern(
                description=f"File read {count} times: {path}",
                frequency=count,
                impact="Repeated context loading",
                current_behavior=f"Reading {path} multiple times in session",
                suggestion="Consider keeping file content in context or using Task agent for exploration",
                affected_agents=["Explore"]
            ))

    # Detect repeated searches
    for key, count in search_patterns.items():
        if count >= 3:
            tool, pattern = key.split(":", 1)
            patterns.append(WorkflowPattern(
                description=f"Search repeated {count} times: {pattern}",
                frequency=count,
                impact="Redundant search operations",
                current_behavior=f"Using {tool} with same pattern repeatedly",
                suggestion="Use Task agent for complex searches that may need iteration",
                affected_agents=["Explore", "general-purpose"]
            ))

    # Detect high failure rates
    for tool, count in failed_tools.items():
        if count >= 3:
            patterns.append(WorkflowPattern(
                description=f"Tool failures: {tool}",
                frequency=count,
                impact="Failed operations requiring retry",
                current_behavior=f"{tool} failed {count} times",
                suggestion="Review tool usage patterns and consider alternative approaches",
                affected_agents=[]
            ))

    # Check for missing Task agent delegation
    total_searches = sum(1 for m in messages for tc in m.tool_calls if tc.name in ("Glob", "Grep"))
    task_calls = sum(1 for m in messages for tc in m.tool_calls if tc.name == "Task")

    if total_searches > 10 and task_calls == 0:
        patterns.append(WorkflowPattern(
            description="Many searches without Task delegation",
            frequency=total_searches,
            impact="Could have used Explore agent for complex codebase navigation",
            current_behavior=f"Performed {total_searches} searches directly",
            suggestion="Use Task tool with Explore agent for open-ended codebase exploration",
            affected_agents=["Explore"]
        ))

    return patterns


# ============================================================================
# Knowledge Gap Extraction
# ============================================================================

def extract_knowledge_gaps(messages: List[Message]) -> List[KnowledgeGap]:
    """
    Detect missing documentation/context.

    Signals:
    - Claude asked user a question
    - WebSearch/WebFetch used for project info
    - User corrected Claude's assumption
    - "I don't know" or uncertainty markers

    Args:
        messages: List of parsed messages

    Returns:
        List of KnowledgeGap objects
    """
    gaps = []

    # Track questions asked
    questions_asked = []
    # Track web searches
    web_searches = []
    # Track user corrections
    corrections = []

    for message in messages:
        if message.role == "assistant":
            # Find questions asked
            questions = re.findall(r'[^.!?]*\?', message.content)
            for q in questions:
                q = q.strip()
                if len(q) > 20:  # Filter out trivial questions
                    questions_asked.append(q)

            # Check for uncertainty markers
            uncertainty_patterns = [
                r"(?i)i'?m\s+not\s+sure",
                r"(?i)i\s+don'?t\s+know",
                r"(?i)i'?m\s+uncertain",
                r"(?i)i\s+couldn'?t\s+find",
            ]
            for pattern in uncertainty_patterns:
                if re.search(pattern, message.content):
                    gaps.append(KnowledgeGap(
                        topic=_extract_topic(message.content),
                        category="Unknown",
                        evidence=[message.content[:200]],
                        missing_info="Claude expressed uncertainty",
                        suggested_location=".claude/CLAUDE.md or relevant rules file"
                    ))
                    break

        # Track web searches
        for tool_call in message.tool_calls:
            if tool_call.name in ("WebSearch", "WebFetch"):
                query = tool_call.input.get("query", tool_call.input.get("url", ""))
                web_searches.append(query)

        # Track user corrections (from user messages)
        if message.role == "user":
            correction_patterns = [
                r"(?i)actually,?\s+",
                r"(?i)no,?\s+",
                r"(?i)that'?s\s+(not|wrong)",
                r"(?i)i\s+meant\s+",
            ]
            for pattern in correction_patterns:
                if re.search(pattern, message.content):
                    corrections.append(message.content)
                    break

    # Create gaps from questions
    if questions_asked:
        # Group similar questions
        for q in questions_asked[:5]:  # Limit to 5
            gaps.append(KnowledgeGap(
                topic=_extract_topic(q),
                category=_categorize_question(q),
                evidence=[q],
                missing_info=f"Question asked: {q[:100]}",
                suggested_location=_suggest_doc_location(q)
            ))

    # Create gaps from web searches for project info
    for search in web_searches:
        if any(kw in search.lower() for kw in ["how to", "example", "documentation"]):
            gaps.append(KnowledgeGap(
                topic=_extract_topic(search),
                category="External Documentation",
                evidence=[f"Web search: {search}"],
                missing_info="Required external lookup",
                suggested_location=".claude/rules/ or relevant agent file"
            ))

    # Create gaps from corrections
    for correction in corrections[:3]:  # Limit
        gaps.append(KnowledgeGap(
            topic=_extract_topic(correction),
            category="Assumption Error",
            evidence=[correction[:200]],
            missing_info="Claude's assumption was corrected by user",
            suggested_location=".claude/CLAUDE.md"
        ))

    return gaps


def _extract_topic(text: str) -> str:
    """Extract main topic from text."""
    # Remove question words and get key nouns
    cleaned = re.sub(r'(?i)^(what|how|why|where|when|which|is|are|do|does|can|should)\s+', '', text)
    words = cleaned.split()[:5]
    return " ".join(words)[:50]


def _categorize_question(question: str) -> str:
    """Categorize a question."""
    q_lower = question.lower()

    if any(w in q_lower for w in ["api", "endpoint", "request", "response"]):
        return "API"
    if any(w in q_lower for w in ["config", "setting", "environment"]):
        return "Config"
    if any(w in q_lower for w in ["architecture", "structure", "pattern"]):
        return "Architecture"
    if any(w in q_lower for w in ["business", "logic", "rule"]):
        return "Business Logic"

    return "General"


def _suggest_doc_location(question: str) -> str:
    """Suggest where documentation should be added."""
    q_lower = question.lower()

    if "flutter" in q_lower or "widget" in q_lower:
        return ".claude/rules/frontend/flutter-ui.md"
    if "supabase" in q_lower or "database" in q_lower:
        return ".claude/rules/backend/supabase-sql.md"
    if "test" in q_lower or "patrol" in q_lower:
        return ".claude/rules/testing/patrol-testing.md"
    if "sync" in q_lower:
        return ".claude/rules/sync/sync-patterns.md"

    return ".claude/CLAUDE.md"


# ============================================================================
# Code Quality Issue Extraction
# ============================================================================

def extract_code_quality_issues(messages: List[Message]) -> List[CodeQualityIssue]:
    """
    Detect code quality concerns.

    Signals:
    - TODO/FIXME in written code
    - "workaround", "hack", "temporary" in comments
    - Copy-paste detected (similar edits)
    - Magic numbers in code
    - Missing error handling patterns

    Args:
        messages: List of parsed messages

    Returns:
        List of CodeQualityIssue objects
    """
    issues = []

    # Track written code for patterns
    written_code = []
    edited_files = []

    for message in messages:
        for tool_call in message.tool_calls:
            if tool_call.name == "Write":
                content = tool_call.input.get("content", "")
                path = tool_call.input.get("file_path", "")
                written_code.append({"path": path, "content": content})

            elif tool_call.name == "Edit":
                new_string = tool_call.input.get("new_string", "")
                path = tool_call.input.get("file_path", "")
                edited_files.append({"path": path, "content": new_string})

    # Check for TODO/FIXME
    for item in written_code + edited_files:
        content = item["content"]
        path = item["path"]

        todo_matches = re.findall(r'(?i)(//\s*(TODO|FIXME|HACK|XXX)[^"\n]*)', content)
        for match in todo_matches:
            issues.append(CodeQualityIssue(
                description=f"TODO/FIXME comment added",
                issue_type="TODO",
                files=[path],
                evidence=[match[0]],
                suggestion="Address the TODO before considering work complete"
            ))

        # Check for workaround comments
        workaround_matches = re.findall(
            r'(?i)(//[^"\n]*(?:workaround|hack|temporary|temp fix)[^"\n]*)',
            content
        )
        for match in workaround_matches:
            issues.append(CodeQualityIssue(
                description="Workaround code added",
                issue_type="Workaround",
                files=[path],
                evidence=[match],
                suggestion="Document why workaround is needed; create ticket for proper fix"
            ))

        # Check for magic numbers (simple heuristic)
        magic_numbers = re.findall(r'(?<![a-zA-Z0-9_"])\b([2-9]\d{2,}|[1-9]\d{3,})\b(?![a-zA-Z0-9_"])', content)
        if len(magic_numbers) >= 3:
            issues.append(CodeQualityIssue(
                description="Multiple magic numbers detected",
                issue_type="MagicNumber",
                files=[path],
                evidence=[f"Numbers: {', '.join(magic_numbers[:5])}"],
                suggestion="Extract magic numbers to named constants"
            ))

    # Check for similar edits (potential duplication)
    if len(edited_files) >= 2:
        # Simple similarity check
        for i, edit1 in enumerate(edited_files):
            for edit2 in edited_files[i+1:]:
                if _is_similar(edit1["content"], edit2["content"]) and edit1["path"] != edit2["path"]:
                    issues.append(CodeQualityIssue(
                        description="Similar code in multiple files",
                        issue_type="Duplication",
                        files=[edit1["path"], edit2["path"]],
                        evidence=["Similar edit patterns detected"],
                        suggestion="Consider extracting common code to shared utility"
                    ))
                    break

    return issues


def _is_similar(text1: str, text2: str, threshold: float = 0.7) -> bool:
    """Check if two texts are similar."""
    if not text1 or not text2:
        return False

    # Simple word overlap check
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return False

    overlap = len(words1 & words2)
    total = min(len(words1), len(words2))

    return (overlap / total) >= threshold if total > 0 else False


# ============================================================================
# Combined Extraction
# ============================================================================

@dataclass
class AnalysisResult:
    """Combined analysis results."""
    hookify_patterns: List[HookifyPattern] = field(default_factory=list)
    defect_patterns: List[DefectPattern] = field(default_factory=list)
    workflow_patterns: List[WorkflowPattern] = field(default_factory=list)
    knowledge_gaps: List[KnowledgeGap] = field(default_factory=list)
    code_quality_issues: List[CodeQualityIssue] = field(default_factory=list)


def extract_all_patterns(messages: List[Message]) -> AnalysisResult:
    """
    Run all pattern extractors on messages.

    Args:
        messages: List of parsed messages

    Returns:
        AnalysisResult with all patterns found
    """
    return AnalysisResult(
        hookify_patterns=extract_hookify_patterns(messages),
        defect_patterns=extract_defect_patterns(messages),
        workflow_patterns=extract_workflow_patterns(messages),
        knowledge_gaps=extract_knowledge_gaps(messages),
        code_quality_issues=extract_code_quality_issues(messages),
    )


# CLI for testing
if __name__ == "__main__":
    import io
    import sys
    from pathlib import Path
    from .transcript_parser import parse_transcript

    # Windows console fix
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    if len(sys.argv) < 2:
        print("Usage: python pattern_extractors.py <transcript.jsonl>")
        sys.exit(1)

    transcript_path = Path(sys.argv[1])
    messages = parse_transcript(transcript_path)
    result = extract_all_patterns(messages)

    print(f"Analysis of {transcript_path.name}:")
    print(f"  Hookify patterns: {len(result.hookify_patterns)}")
    print(f"  Defect patterns: {len(result.defect_patterns)}")
    print(f"  Workflow patterns: {len(result.workflow_patterns)}")
    print(f"  Knowledge gaps: {len(result.knowledge_gaps)}")
    print(f"  Code quality issues: {len(result.code_quality_issues)}")

    for pattern in result.hookify_patterns:
        print(f"\n  Hook: {pattern.name} ({pattern.severity.value})")
        print(f"    Event: {pattern.event}, Pattern: {pattern.pattern}")
