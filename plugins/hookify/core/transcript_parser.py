#!/usr/bin/env python3
"""Parse Claude Code transcript files (.jsonl) for analysis."""

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """A tool invocation from the assistant."""
    name: str
    input: Dict[str, Any] = field(default_factory=dict)
    id: str = ""


@dataclass
class ToolResult:
    """Result from a tool execution."""
    tool_name: str
    output: str = ""
    error: Optional[str] = None
    tool_use_id: str = ""


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # 'user' | 'assistant'
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    timestamp: Optional[datetime] = None
    raw: Dict[str, Any] = field(default_factory=dict)


def get_project_hash(project_dir: Path) -> str:
    """
    Generate the project hash used by Claude Code for transcript storage.

    Claude Code uses the absolute path with special characters replaced by dashes.
    """
    abs_path = str(project_dir.resolve())
    # Windows: C:\Users\foo bar -> C--Users-foo-bar
    # Unix: /home/user/foo bar -> -home-user-foo-bar
    # Replace colons, slashes, and spaces with dashes
    result = abs_path.replace(":", "").replace("\\", "-").replace("/", "-").replace(" ", "-")
    # Claude Code uses double dash after drive letter on Windows
    if len(result) > 1 and result[0].isalpha() and result[1] == "-":
        result = result[0] + "-" + result[1:]
    return result


def find_transcripts(
    project_dir: Optional[Path] = None,
    limit: int = 10,
    claude_dir: Optional[Path] = None
) -> List[Path]:
    """
    Find recent transcript files for a project.

    Args:
        project_dir: Project directory (default: current directory)
        limit: Maximum number of transcripts to return
        claude_dir: Override Claude config directory (for testing)

    Returns:
        List of paths to transcript files, sorted by modification time (newest first)
    """
    if project_dir is None:
        project_dir = Path.cwd()

    if claude_dir is None:
        # Default Claude config location
        if sys.platform == "win32":
            claude_dir = Path(os.environ.get("USERPROFILE", "")) / ".claude" / "projects"
        else:
            claude_dir = Path.home() / ".claude" / "projects"

    # Find project folder
    project_hash = get_project_hash(project_dir)
    project_transcript_dir = claude_dir / project_hash

    if not project_transcript_dir.exists():
        return []

    # Find all .jsonl files
    transcripts = list(project_transcript_dir.glob("*.jsonl"))

    # Sort by modification time (newest first)
    transcripts.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return transcripts[:limit]


def _parse_content_block(block: Dict[str, Any]) -> tuple[str, Optional[ToolCall], Optional[ToolResult]]:
    """
    Parse a content block from a message.

    Returns:
        Tuple of (text, tool_call, tool_result)
    """
    block_type = block.get("type", "")

    if block_type == "text":
        return block.get("text", ""), None, None

    elif block_type == "tool_use":
        tool_call = ToolCall(
            name=block.get("name", ""),
            input=block.get("input", {}),
            id=block.get("id", "")
        )
        return "", tool_call, None

    elif block_type == "tool_result":
        # Tool results can have nested content
        content_parts = []
        if "content" in block:
            if isinstance(block["content"], str):
                content_parts.append(block["content"])
            elif isinstance(block["content"], list):
                for item in block["content"]:
                    if isinstance(item, dict) and item.get("type") == "text":
                        content_parts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        content_parts.append(item)

        tool_result = ToolResult(
            tool_name=block.get("tool_name", ""),
            output="\n".join(content_parts),
            error=block.get("error"),
            tool_use_id=block.get("tool_use_id", "")
        )
        return "", None, tool_result

    return "", None, None


def _parse_message(entry: Dict[str, Any]) -> Optional[Message]:
    """
    Parse a single JSONL entry into a Message.

    Args:
        entry: Parsed JSON entry from transcript

    Returns:
        Message object or None if not a conversation message
    """
    # Skip non-message entries
    if entry.get("type") not in ("user", "assistant"):
        return None

    role = entry.get("type", "")
    content_parts = []
    tool_calls = []
    tool_results = []

    # Handle message content (can be string or list of blocks)
    message_content = entry.get("message", {}).get("content", [])

    if isinstance(message_content, str):
        content_parts.append(message_content)
    elif isinstance(message_content, list):
        for block in message_content:
            if isinstance(block, str):
                content_parts.append(block)
            elif isinstance(block, dict):
                text, tool_call, tool_result = _parse_content_block(block)
                if text:
                    content_parts.append(text)
                if tool_call:
                    tool_calls.append(tool_call)
                if tool_result:
                    tool_results.append(tool_result)

    # Parse timestamp if available
    timestamp = None
    if "timestamp" in entry:
        try:
            timestamp = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            pass

    return Message(
        role=role,
        content="\n".join(content_parts),
        tool_calls=tool_calls,
        tool_results=tool_results,
        timestamp=timestamp,
        raw=entry
    )


def parse_transcript(file_path: Path) -> List[Message]:
    """
    Parse a .jsonl transcript file into structured messages.

    Args:
        file_path: Path to the transcript file

    Returns:
        List of Message objects
    """
    messages = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                    message = _parse_message(entry)
                    if message:
                        messages.append(message)
                except json.JSONDecodeError:
                    continue

    except Exception as e:
        print(f"Warning: Could not read transcript {file_path}: {e}", file=sys.stderr)

    return messages


def extract_tool_usage(messages: List[Message]) -> Dict[str, int]:
    """
    Count tool usage across messages.

    Args:
        messages: List of parsed messages

    Returns:
        Dictionary mapping tool names to usage counts
    """
    usage = {}

    for message in messages:
        for tool_call in message.tool_calls:
            name = tool_call.name
            usage[name] = usage.get(name, 0) + 1

    return usage


def extract_user_corrections(messages: List[Message]) -> List[str]:
    """
    Find user messages that indicate corrections or frustration.

    Looks for patterns like:
    - "Don't", "Stop", "Never"
    - "Why did you", "That's wrong"
    - "No, I meant"
    - Explicit corrections

    Args:
        messages: List of parsed messages

    Returns:
        List of user messages containing corrections
    """
    correction_patterns = [
        "don't", "dont", "do not",
        "stop", "never", "shouldn't", "shouldnt",
        "why did you", "that's wrong", "thats wrong",
        "no,", "no i", "no I",
        "wrong", "incorrect", "mistake",
        "i meant", "I meant",
        "please don't", "please dont",
        "actually,", "actually i",
    ]

    corrections = []

    for message in messages:
        if message.role != "user":
            continue

        content_lower = message.content.lower()
        for pattern in correction_patterns:
            if pattern in content_lower:
                corrections.append(message.content)
                break

    return corrections


def extract_errors(messages: List[Message]) -> List[Dict[str, Any]]:
    """
    Find error messages from tool results.

    Args:
        messages: List of parsed messages

    Returns:
        List of dictionaries with error details
    """
    error_patterns = [
        "error:", "exception:", "failed:",
        "traceback", "stack trace",
        "cannot", "could not", "unable to",
        "null", "undefined", "nil",
        "permission denied", "access denied",
        "not found", "no such file",
        "syntax error", "parse error",
        "build failed", "test failed",
    ]

    errors = []

    for message in messages:
        for result in message.tool_results:
            if result.error:
                errors.append({
                    "tool": result.tool_name,
                    "error": result.error,
                    "output": result.output[:500] if result.output else "",
                    "type": "explicit_error"
                })
                continue

            # Check output for error patterns
            output_lower = result.output.lower()
            for pattern in error_patterns:
                if pattern in output_lower:
                    errors.append({
                        "tool": result.tool_name,
                        "error": None,
                        "output": result.output[:500],
                        "type": "pattern_match",
                        "pattern": pattern
                    })
                    break

    return errors


def extract_assistant_questions(messages: List[Message]) -> List[str]:
    """
    Find questions the assistant asked the user.

    Args:
        messages: List of parsed messages

    Returns:
        List of questions asked
    """
    questions = []

    for message in messages:
        if message.role != "assistant":
            continue

        # Look for question marks in assistant content
        content = message.content
        sentences = content.replace("?", "?\n").split("\n")

        for sentence in sentences:
            sentence = sentence.strip()
            if sentence.endswith("?") and len(sentence) > 10:
                questions.append(sentence)

    return questions


def get_session_summary(messages: List[Message]) -> Dict[str, Any]:
    """
    Generate a summary of a transcript session.

    Args:
        messages: List of parsed messages

    Returns:
        Summary dictionary with statistics and highlights
    """
    tool_usage = extract_tool_usage(messages)
    corrections = extract_user_corrections(messages)
    errors = extract_errors(messages)
    questions = extract_assistant_questions(messages)

    # Calculate message counts
    user_messages = [m for m in messages if m.role == "user"]
    assistant_messages = [m for m in messages if m.role == "assistant"]

    # Get timestamps if available
    first_timestamp = None
    last_timestamp = None
    for m in messages:
        if m.timestamp:
            if first_timestamp is None:
                first_timestamp = m.timestamp
            last_timestamp = m.timestamp

    duration = None
    if first_timestamp and last_timestamp:
        duration = (last_timestamp - first_timestamp).total_seconds()

    return {
        "message_count": len(messages),
        "user_messages": len(user_messages),
        "assistant_messages": len(assistant_messages),
        "tool_usage": tool_usage,
        "total_tool_calls": sum(tool_usage.values()),
        "corrections": corrections,
        "correction_count": len(corrections),
        "errors": errors,
        "error_count": len(errors),
        "questions_asked": questions,
        "question_count": len(questions),
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "duration_seconds": duration,
    }


# CLI for testing
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python transcript_parser.py <transcript.jsonl>")
        print("       python transcript_parser.py --find [project_dir]")
        sys.exit(1)

    if sys.argv[1] == "--find":
        project_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
        transcripts = find_transcripts(project_dir)
        print(f"Found {len(transcripts)} transcripts for {project_dir}:")
        for t in transcripts:
            print(f"  {t}")
        sys.exit(0)

    transcript_path = Path(sys.argv[1])
    if not transcript_path.exists():
        print(f"Error: File not found: {transcript_path}")
        sys.exit(1)

    messages = parse_transcript(transcript_path)
    summary = get_session_summary(messages)

    print(f"Transcript: {transcript_path.name}")
    print(f"Messages: {summary['message_count']} ({summary['user_messages']} user, {summary['assistant_messages']} assistant)")
    print(f"Tool calls: {summary['total_tool_calls']}")
    print(f"Corrections: {summary['correction_count']}")
    print(f"Errors: {summary['error_count']}")
    print(f"Questions: {summary['question_count']}")

    if summary['duration_seconds']:
        minutes = summary['duration_seconds'] / 60
        print(f"Duration: {minutes:.1f} minutes")

    print("\nTool usage:")
    for tool, count in sorted(summary['tool_usage'].items(), key=lambda x: -x[1]):
        print(f"  {tool}: {count}")
