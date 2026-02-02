"""
Hookify utility functions.

This module provides common utilities for the hookify plugin.
"""

import os
from pathlib import Path
from typing import List


def get_claude_dir() -> Path:
    """
    Get the .claude directory path.

    Returns:
        Path to .claude directory
    """
    return Path(".claude")


def get_rule_files() -> List[Path]:
    """
    Find all hookify rule files.

    Returns:
        List of paths to rule files matching hookify.*.local.md
    """
    claude_dir = get_claude_dir()
    if not claude_dir.exists():
        return []

    return sorted(claude_dir.glob("hookify.*.local.md"))


def get_rule_name_from_path(path: Path) -> str:
    """
    Extract rule name from file path.

    Args:
        path: Path to rule file (e.g., hookify.my-rule.local.md)

    Returns:
        Rule name (e.g., my-rule)
    """
    name = path.stem  # hookify.my-rule.local
    if name.startswith("hookify.") and name.endswith(".local"):
        return name[8:-6]  # Remove prefix and suffix
    return name


def ensure_claude_dir() -> Path:
    """
    Ensure .claude directory exists.

    Returns:
        Path to .claude directory
    """
    claude_dir = get_claude_dir()
    claude_dir.mkdir(parents=True, exist_ok=True)
    return claude_dir


def rule_file_path(rule_name: str) -> Path:
    """
    Get the file path for a rule name.

    Args:
        rule_name: Name of the rule

    Returns:
        Path where rule file should be stored
    """
    return get_claude_dir() / f"hookify.{rule_name}.local.md"
