# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Pre-tool-use hook for Hookify."""

import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rule_engine import RuleEngine


def main():
    """Process pre-tool-use event."""
    try:
        try:
            event_data = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            print(json.dumps({"continue": True}))
            return

        tool_name = event_data.get("tool_name", "")
        tool_input = event_data.get("tool_input", {})

        # Initialize rule engine
        engine = RuleEngine()

        # Get content to check based on tool type
        content_to_check = ""

        if tool_name == "Bash":
            content_to_check = tool_input.get("command", "")
        elif tool_name == "Write":
            content_to_check = tool_input.get("content", "")
        elif tool_name == "Edit":
            content_to_check = tool_input.get("new_string", "")

        # Check rules
        result = engine.check_rules(
            event_type="pretooluse",
            tool_name=tool_name.lower(),
            content=content_to_check
        )

        # Output result
        print(json.dumps(result))
    except Exception:
        # Never crash - always return valid JSON so agent handoff succeeds
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
