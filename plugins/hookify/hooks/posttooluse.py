# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Post-tool-use hook for Hookify."""

import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rule_engine import RuleEngine


def main():
    """Process post-tool-use event."""
    try:
        try:
            event_data = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            print(json.dumps({"continue": True}))
            return

        tool_name = event_data.get("tool_name", "")
        tool_output = event_data.get("tool_output", "")

        # Initialize rule engine
        engine = RuleEngine()

        # Check rules against output
        result = engine.check_rules(
            event_type="posttooluse",
            tool_name=tool_name.lower(),
            content=str(tool_output)
        )

        # Output result
        print(json.dumps(result))
    except Exception:
        # Never crash - always return valid JSON so agent handoff succeeds
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
