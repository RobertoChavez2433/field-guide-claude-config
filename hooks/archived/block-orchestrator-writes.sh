#!/bin/bash
# PreToolUse hook: blocks Edit, Write, Bash for the orchestrator
# Uses grep instead of jq (jq not installed on this system)

INPUT=$(cat)
TOOL=$(echo "$INPUT" | grep -oP '"tool_name"\s*:\s*"\K[^"]+')

case "$TOOL" in
  Edit|Write|NotebookEdit|MultiEdit)
    cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Orchestrator must delegate via Task, not modify files directly."}}
EOF
    exit 0
    ;;
  Bash)
    COMMAND=$(echo "$INPUT" | grep -oP '"command"\s*:\s*"\K[^"]+')
    if echo "$COMMAND" | grep -qiE 'sed\s+-i|awk\s+-i|perl\s+-[ip]|>\s*\S|>>\s*\S|\btee\b|\brm\b|\bmv\b|\bcp\b' ; then
      cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Orchestrator cannot modify files via Bash."}}
EOF
      exit 0
    fi
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
