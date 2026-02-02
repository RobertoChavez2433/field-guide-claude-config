"""
Hookify pattern matchers.

This module provides pattern matching utilities for hook rules.
"""

import re
from functools import lru_cache
from typing import Optional


@lru_cache(maxsize=128)
def compile_pattern(pattern: str) -> Optional[re.Pattern]:
    """
    Compile a regex pattern with caching.

    Args:
        pattern: Regex pattern string

    Returns:
        Compiled regex or None if invalid
    """
    try:
        return re.compile(pattern, re.MULTILINE | re.IGNORECASE)
    except re.error:
        return None


def matches(pattern: str, content: str) -> bool:
    """
    Check if content matches a pattern.

    Args:
        pattern: Regex pattern to match
        content: Content to check

    Returns:
        True if pattern matches
    """
    compiled = compile_pattern(pattern)
    if compiled:
        return bool(compiled.search(content))

    # Fallback to literal match if regex is invalid
    return pattern.lower() in content.lower()


def contains(needle: str, haystack: str) -> bool:
    """
    Case-insensitive substring check.

    Args:
        needle: String to find
        haystack: String to search in

    Returns:
        True if needle is in haystack
    """
    return needle.lower() in haystack.lower()


def equals(expected: str, actual: str) -> bool:
    """
    Case-insensitive equality check.

    Args:
        expected: Expected value
        actual: Actual value

    Returns:
        True if values are equal (case-insensitive)
    """
    return expected.lower() == actual.lower()
