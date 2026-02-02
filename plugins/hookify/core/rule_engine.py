# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Rule evaluation engine for hookify."""

import sys
from functools import lru_cache
from typing import Any, Dict, List, Optional

from .config_loader import Condition, Rule, load_all_rules

# Import matchers
sys.path.insert(0, str(__file__).rsplit("core", 1)[0])
try:
    from matchers import matches, contains, equals
except ImportError:
    # Fallback implementations
    import re

    @lru_cache(maxsize=128)
    def _compile_pattern(pattern: str):
        try:
            return re.compile(pattern, re.MULTILINE | re.IGNORECASE)
        except re.error:
            return None

    def matches(pattern: str, content: str) -> bool:
        compiled = _compile_pattern(pattern)
        if compiled:
            return bool(compiled.search(content))
        return pattern.lower() in content.lower()

    def contains(needle: str, haystack: str) -> bool:
        return needle.lower() in haystack.lower()

    def equals(expected: str, actual: str) -> bool:
        return expected.lower() == actual.lower()


# Auto-disable threshold
AUTO_DISABLE_THRESHOLD = 5

# Session state (persists until Claude Code restarts)
_session_trigger_counts = {}  # {rule_name: count}
_disabled_rules = set()  # Rules auto-disabled this session


def reset_session_state():
    """Reset auto-disable state. Call at session start if needed."""
    global _session_trigger_counts, _disabled_rules
    _session_trigger_counts = {}
    _disabled_rules = set()


class RuleEngine:
    """Engine for evaluating hookify rules."""

    def __init__(self, base_dir: str = ".claude"):
        """
        Initialize the rule engine.

        Args:
            base_dir: Base directory for rule files
        """
        self.base_dir = base_dir
        self.rules = load_all_rules(base_dir)

    def reload_rules(self):
        """Reload rules from disk."""
        self.rules = load_all_rules(self.base_dir)

    def get_rules_for_event(self, event_type: str, tool_name: Optional[str] = None) -> List[Rule]:
        """
        Get rules that apply to a specific event type.

        Args:
            event_type: Type of event (pretooluse, posttooluse, stop, userpromptsubmit)
            tool_name: Optional tool name to filter by

        Returns:
            List of matching rules
        """
        matching = []

        for rule in self.rules:
            rule_event = rule.event

            # Check if event matches
            if rule_event == event_type:
                matching.append(rule)
            elif tool_name and rule_event == tool_name:
                matching.append(rule)

        return matching

    def _extract_field(self, field: str, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """
        Extract a field value from tool input.

        Args:
            field: Field name to extract
            tool_name: Name of the tool
            tool_input: Tool input dictionary

        Returns:
            Extracted field value as string
        """
        # Handle special fields
        if field == "command" and tool_name.lower() == "bash":
            return tool_input.get("command", "")
        elif field == "content" and tool_name.lower() == "write":
            return tool_input.get("content", "")
        elif field == "new_string" and tool_name.lower() == "edit":
            return tool_input.get("new_string", "")
        elif field == "file_path":
            return tool_input.get("file_path", "")

        # Generic field access
        return str(tool_input.get(field, ""))

    def _check_condition(self, condition: Condition, content: str) -> bool:
        """
        Check if a condition matches content.

        Args:
            condition: Condition to check
            content: Content to match against

        Returns:
            True if condition matches
        """
        operator = condition.operator.lower()
        pattern = condition.pattern

        if operator == "matches":
            return matches(pattern, content)
        elif operator == "contains":
            return contains(pattern, content)
        elif operator == "equals":
            return equals(pattern, content)
        else:
            # Default to regex match
            return matches(pattern, content)

    def _rule_matches(self, rule: Rule, tool_name: str, tool_input: Dict[str, Any]) -> bool:
        """
        Check if a rule matches the given input.

        Args:
            rule: Rule to check
            tool_name: Name of the tool
            tool_input: Tool input dictionary

        Returns:
            True if all conditions match
        """
        for condition in rule.conditions:
            content = self._extract_field(condition.field, tool_name, tool_input)
            if not self._check_condition(condition, content):
                return False
        return True

    def evaluate_rules(
        self,
        event_type: str,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate all applicable rules against input.

        Args:
            event_type: Type of event
            tool_name: Name of the tool
            tool_input: Tool input dictionary

        Returns:
            Result dictionary with 'continue', 'message', 'action', 'rule'
        """
        global _session_trigger_counts, _disabled_rules

        rules = self.get_rules_for_event(event_type, tool_name)

        # Check blocking rules first
        for rule in rules:
            # Skip auto-disabled rules
            if rule.name in _disabled_rules:
                continue

            if rule.action == "block" and self._rule_matches(rule, tool_name, tool_input):
                # Track trigger count
                _session_trigger_counts[rule.name] = _session_trigger_counts.get(rule.name, 0) + 1

                # Check if we should auto-disable
                if _session_trigger_counts[rule.name] >= AUTO_DISABLE_THRESHOLD:
                    _disabled_rules.add(rule.name)
                    print(f"[hookify] Rule '{rule.name}' auto-disabled after {AUTO_DISABLE_THRESHOLD} triggers", file=sys.stderr)

                return {
                    "continue": False,
                    "message": rule.message or f"Blocked by rule: {rule.name}",
                    "rule": rule.name,
                    "action": "block"
                }

        # Then check warning rules
        for rule in rules:
            # Skip auto-disabled rules
            if rule.name in _disabled_rules:
                continue

            if rule.action == "warn" and self._rule_matches(rule, tool_name, tool_input):
                # Track trigger count
                _session_trigger_counts[rule.name] = _session_trigger_counts.get(rule.name, 0) + 1

                # Check if we should auto-disable
                if _session_trigger_counts[rule.name] >= AUTO_DISABLE_THRESHOLD:
                    _disabled_rules.add(rule.name)
                    print(f"[hookify] Rule '{rule.name}' auto-disabled after {AUTO_DISABLE_THRESHOLD} triggers", file=sys.stderr)

                return {
                    "continue": True,
                    "message": rule.message or f"Warning from rule: {rule.name}",
                    "rule": rule.name,
                    "action": "warn"
                }

        # No rules matched
        return {"continue": True}

    def check_rules(
        self,
        event_type: str,
        tool_name: str,
        content: str
    ) -> Dict[str, Any]:
        """
        Simplified rule check using content string.

        Args:
            event_type: Type of event
            tool_name: Name of the tool
            content: Content to check

        Returns:
            Result dictionary
        """
        # Convert content to tool_input format
        tool_input = {"command": content, "content": content}
        return self.evaluate_rules(event_type, tool_name, tool_input)

    def list_rules(self) -> List[Dict[str, Any]]:
        """
        Get a summary of all loaded rules.

        Returns:
            List of rule summaries
        """
        return [
            {
                "name": rule.name,
                "event": rule.event,
                "pattern": rule.conditions[0].pattern if rule.conditions else "",
                "action": rule.action,
                "enabled": rule.enabled,
                "file": rule.file,
            }
            for rule in self.rules
        ]
