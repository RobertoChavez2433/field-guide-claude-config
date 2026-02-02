# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Load and parse hookify rule files."""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Condition:
    """A single matching condition."""
    field: str
    operator: str  # matches, contains, equals
    pattern: str


@dataclass
class Rule:
    """A complete hookify rule."""
    name: str
    enabled: bool
    event: str
    conditions: List[Condition]
    action: str
    message: str
    file: str = ""


def find_rule_files(base_dir: str = ".claude") -> List[Path]:
    """
    Find all hookify rule files in the specified directory.

    Rule files match the pattern: hookify.*.local.md

    Args:
        base_dir: Base directory to search (default: .claude)

    Returns:
        List of paths to rule files
    """
    base_path = Path(base_dir)

    if not base_path.exists():
        return []

    return sorted(base_path.glob("hookify.*.local.md"))


def parse_frontmatter(content: str) -> tuple[Dict, str]:
    """
    Parse YAML-like frontmatter from markdown content.

    Args:
        content: Full markdown file content

    Returns:
        Tuple of (frontmatter dict, message body)
    """
    frontmatter = {}
    body = content

    # Check for frontmatter delimiters
    if not content.startswith("---"):
        return frontmatter, body

    # Find end of frontmatter
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return frontmatter, body

    fm_content = content[3:end_match.start() + 3]
    body = content[end_match.end() + 3:].strip()

    # Parse key: value pairs
    current_key = None
    current_list = None

    for line in fm_content.strip().split("\n"):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue

        # Check for list item
        if stripped.startswith("- ") and current_key:
            if current_list is None:
                current_list = []
                frontmatter[current_key] = current_list
            current_list.append(stripped[2:])
            continue

        # Regular key: value
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()

            current_key = key
            current_list = None

            # Handle boolean values
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value == "":
                # Might be followed by list items
                value = None

            if value is not None:
                frontmatter[key] = value

    return frontmatter, body


def parse_conditions(frontmatter: Dict) -> List[Condition]:
    """
    Parse conditions from frontmatter.

    Supports both simple pattern format and explicit conditions list.

    Args:
        frontmatter: Parsed frontmatter dictionary

    Returns:
        List of Condition objects
    """
    conditions = []

    # Check for explicit conditions list
    if "conditions" in frontmatter and isinstance(frontmatter["conditions"], list):
        for cond in frontmatter["conditions"]:
            if isinstance(cond, dict):
                conditions.append(Condition(
                    field=cond.get("field", "command"),
                    operator=cond.get("operator", "matches"),
                    pattern=cond.get("pattern", "")
                ))
            elif isinstance(cond, str):
                # Parse "field operator pattern" format
                parts = cond.split(None, 2)
                if len(parts) >= 3:
                    conditions.append(Condition(
                        field=parts[0],
                        operator=parts[1],
                        pattern=parts[2]
                    ))
        return conditions

    # Legacy: simple pattern format
    if "pattern" in frontmatter:
        conditions.append(Condition(
            field="command",  # Default field for bash events
            operator="matches",
            pattern=frontmatter["pattern"]
        ))

    return conditions


def load_rule(file_path: Path) -> Optional[Rule]:
    """
    Load a single rule file.

    Args:
        file_path: Path to rule file

    Returns:
        Rule object or None if invalid
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return None

    frontmatter, body = parse_frontmatter(content)

    # Validate required fields
    if not frontmatter.get("name"):
        print(f"Warning: Rule {file_path} missing 'name' in frontmatter", file=sys.stderr)
        return None

    if not frontmatter.get("event"):
        print(f"Warning: Rule {file_path} missing 'event' in frontmatter", file=sys.stderr)
        return None

    conditions = parse_conditions(frontmatter)
    if not conditions:
        print(f"Warning: Rule {file_path} has no pattern or conditions", file=sys.stderr)
        return None

    return Rule(
        name=frontmatter["name"],
        enabled=frontmatter.get("enabled", True),
        event=frontmatter["event"].lower(),
        conditions=conditions,
        action=frontmatter.get("action", "warn").lower(),
        message=body,
        file=str(file_path),
    )


def load_all_rules(base_dir: str = ".claude", event: Optional[str] = None) -> List[Rule]:
    """
    Load all enabled rules from the base directory.

    Args:
        base_dir: Base directory to search
        event: Optional event type to filter by

    Returns:
        List of Rule objects
    """
    rules = []

    for file_path in find_rule_files(base_dir):
        rule = load_rule(file_path)
        if rule and rule.enabled:
            if event is None or rule.event == event.lower():
                rules.append(rule)

    return rules


# Legacy compatibility: dict-based interface
def load_rules_as_dicts(base_dir: str = ".claude") -> List[Dict]:
    """
    Load rules and return as dictionaries for backward compatibility.

    Args:
        base_dir: Base directory to search

    Returns:
        List of rule dictionaries
    """
    rules = load_all_rules(base_dir)
    return [
        {
            "name": r.name,
            "enabled": r.enabled,
            "event": r.event,
            "pattern": r.conditions[0].pattern if r.conditions else "",
            "action": r.action,
            "message": r.message,
            "file": r.file,
        }
        for r in rules
    ]
