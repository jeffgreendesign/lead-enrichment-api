#!/bin/bash
# ============================================================================
# Security Check — Pre-commit Security Scanner (Python)
# ============================================================================
# Scans Python source files for common security issues.
# Non-blocking by default (exits 0 with warnings).
# Use --strict to fail on any finding.
#
# What it catches:
# - Hardcoded secrets: API keys, tokens, passwords in source
# - eval()/exec() usage: code injection risk
# - SQL string interpolation: SQL injection risk in f-strings
# - .env file committed to git
#
# Usage:
#   ./scripts/security-check.sh              # Warn only (exit 0)
#   ./scripts/security-check.sh --strict     # Fail on findings (exit 1)
# ============================================================================
set -euo pipefail

STRICT=false
if [ "${1:-}" = "--strict" ]; then
  STRICT=true
fi

WARNINGS=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

warn() {
  echo -e "${YELLOW}WARNING:${NC} $1"
  echo "  File: $2"
  echo "  Line: $3"
  echo ""
  WARNINGS=$((WARNINGS + 1))
}

# Get Python files to check (staged files, or all source files if not in a git context)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  FILES=$(git diff --cached --name-only --diff-filter=ACM -- '*.py' 2>/dev/null || true)
  if [ -z "$FILES" ]; then
    FILES=$(find "$PROJECT_DIR/src" "$PROJECT_DIR/tests" -type f -name "*.py" 2>/dev/null || true)
  fi
else
  FILES=$(find "$PROJECT_DIR/src" "$PROJECT_DIR/tests" -type f -name "*.py" 2>/dev/null || true)
fi

if [ -z "$FILES" ]; then
  echo -e "${GREEN}No files to check.${NC}"
  exit 0
fi

echo "Security scan: checking $(echo "$FILES" | wc -l | tr -d ' ') files..."
echo ""

for file in $FILES; do
  [ -f "$file" ] || continue
  LINE_NUM=0

  while IFS= read -r line; do
    LINE_NUM=$((LINE_NUM + 1))

    # Skip test files for some checks
    IS_TEST=false
    case "$file" in
      *test_* | *_test.py | *tests/*) IS_TEST=true ;;
    esac

    # --- Hardcoded Secrets ---
    if echo "$line" | grep -qiE "(api_key|apikey|secret|password|token|private_key)\s*[:=]\s*['\"][A-Za-z0-9+/=_-]{8,}" 2>/dev/null; then
      case "$file" in
        *.example | *.template | *conftest*) ;;
        *) warn "Possible hardcoded secret" "$file" "$LINE_NUM" ;;
      esac
    fi

    # --- eval()/exec() Usage ---
    if echo "$line" | grep -qE "\b(eval|exec)\s*\(" 2>/dev/null; then
      TRIMMED=$(echo "$line" | sed 's/^[[:space:]]*//')
      case "$TRIMMED" in
        "#"*) ;; # skip comments
        *) warn "eval()/exec() usage — code injection risk" "$file" "$LINE_NUM" ;;
      esac
    fi

    # --- SQL String Interpolation ---
    if echo "$line" | grep -qE "(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER).*f['\"]" 2>/dev/null; then
      warn "SQL string interpolation — use parameterized queries" "$file" "$LINE_NUM"
    fi

  done < "$file"
done

# --- Check for .env committed ---
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    echo -e "${YELLOW}WARNING:${NC} .env file is tracked by git — add it to .gitignore"
    echo ""
    WARNINGS=$((WARNINGS + 1))
  fi
fi

# Summary
echo "---"
if [ "$WARNINGS" -eq 0 ]; then
  echo -e "${GREEN}No security issues found.${NC}"
  exit 0
fi

echo -e "${YELLOW}Found $WARNINGS warning(s).${NC}"

if [ "$STRICT" = true ]; then
  echo -e "${RED}Strict mode: failing due to warnings.${NC}"
  exit 1
fi

echo "Run with --strict to treat warnings as errors."
exit 0
