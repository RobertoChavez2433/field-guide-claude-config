# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""User prompt submit hook for Hookify."""

import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rule_engine import RuleEngine


def main():
    """Process user prompt submit event."""
    # Read event data from stdin
    try:
        event_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # No input or invalid JSON
        print(json.dumps({"continue": True}))
        return

    user_prompt = event_data.get("user_prompt", "")

    # Initialize rule engine
    engine = RuleEngine()

    # Check rules
    result = engine.check_rules(
        event_type="userpromptsubmit",
        tool_name="userprompt",
        content=user_prompt
    )

    # Output result
    print(json.dumps(result))


if __name__ == "__main__":
    main()
