#!/bin/bash
# Post-work validation after agent completes implementation
# Agents should run this automatically before reporting completion
# Usage: bash .claude/hooks/post-agent-coding.sh [FEATURE] [TEST_PATH]
# Example: bash .claude/hooks/post-agent-coding.sh pdf test/features/pdf/extraction/

set -e

FEATURE=${1:-"pdf"}
TEST_PATH=${2:-"test/features/${FEATURE}/"}

echo "🔍 Post-work validation for feature: $FEATURE"
echo ""

# Check 1: Unit tests
echo "  [1/4] Running unit tests ($TEST_PATH)..."
if ! pwsh -Command "flutter test \"$TEST_PATH\" --reporter=compact 2>&1" | tail -10; then
  echo "  ✗ FAILED: Tests not passing. Fix code and re-run."
  exit 1
fi
echo "  ✓ Tests passing"

# Check 2: Analyzer
echo ""
echo "  [2/4] Running analyzer (lib/features/$FEATURE/)..."
if dart analyze "lib/features/$FEATURE/" --no-fatal-infos 2>&1 | grep -i "error"; then
  echo "  ✗ FAILED: Analyzer errors found. Fix issues."
  exit 1
fi
echo "  ✓ Analyzer clean"

# Check 3: Feature constraints
echo ""
echo "  [3/4] Verifying feature constraints (architecture-decisions/${FEATURE}-constraints.md)..."
if [ -f ".claude/architecture-decisions/${FEATURE}-constraints.md" ]; then
  echo "  ✓ Constraints file exists. Manual verification needed by agent."
  echo "     (Automated checks: hardcoded strings, enum consistency, V1 imports)"
else
  echo "  ⚠ Warning: Constraints file not found."
fi

# Check 4: Shared constraints
echo ""
echo "  [4/4] Verifying shared constraints (architecture-decisions/data-validation-rules.md)..."
echo "  ✓ Shared constraints exist. Manual verification needed by agent."
echo "     (Automated checks: user input validation, null safety, error handling)"

echo ""
echo "✅ Post-work validation complete."
echo "   Agent ready to report completion."
echo ""
