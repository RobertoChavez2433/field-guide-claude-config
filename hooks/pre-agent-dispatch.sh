#!/bin/bash
# Pre-flight validation before spawning agents
# Run this BEFORE any Task tool calls to spawn sub-agents
# Usage: bash .claude/hooks/pre-agent-dispatch.sh

set -e

echo "🔍 Pre-flight agent validation..."
echo ""

# Check 1: Write permissions
echo "  [1/3] Checking write permissions (dart pub get)..."
if ! pwsh -Command "dart pub get 2>&1 | Select-String -Pattern 'error|Error' | Measure-Object | Select-Object -ExpandProperty Count" | grep -q "^0"; then
  echo "  ✗ FAILED: Write permissions issue. Check disk space and permissions."
  exit 1
fi
echo "  ✓ Write permissions OK"

# Check 2: Test runner
echo "  [2/3] Checking test runner (flutter test --version)..."
if ! pwsh -Command "flutter test --version 2>&1" | grep -q "Flutter\|flutter"; then
  echo "  ✗ FAILED: Flutter test runner not available. Run 'flutter pub get' first."
  exit 1
fi
echo "  ✓ Test runner OK"

# Check 3: Analyzer
echo "  [3/3] Checking analyzer (dart analyze --version)..."
if ! dart analyze --version 2>&1 | grep -q "dart\|Dart"; then
  echo "  ✗ FAILED: Dart analyzer not available."
  exit 1
fi
echo "  ✓ Analyzer OK"

echo ""
echo "✅ All pre-flight checks passed."
echo "   Safe to spawn agents. Context files will be lazy-loaded via frontmatter."
echo ""
