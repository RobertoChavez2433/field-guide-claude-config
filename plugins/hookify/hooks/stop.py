# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""Stop event hook for Hookify."""

import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.rule_engine import RuleEngine


def main():
    """Process stop event."""
    try:
        # Read event data from stdin
        try:
            event_data = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            print(json.dumps({"continue": True}))
            return

        stop_reason = event_data.get("stop_reason", "")
        final_response = event_data.get("final_response", "")

        # Initialize rule engine
        engine = RuleEngine()

        # Check rules
        result = engine.check_rules(
            event_type="stop",
            tool_name="stop",
            content=final_response
        )

        # Output result
        print(json.dumps(result))
    except Exception:
        # Never crash - always return valid JSON so agent handoff succeeds
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
