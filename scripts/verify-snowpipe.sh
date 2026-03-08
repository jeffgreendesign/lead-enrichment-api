#!/usr/bin/env bash
# Quick Snowpipe health check using Snowflake CLI (snow sql).
#
# Prerequisites:
#   pip install snowflake-cli
#   snow connection add          # one-time setup
#
# Usage:
#   ./scripts/verify-snowpipe.sh [--connection name]

set -euo pipefail

# Find snow CLI: check PATH, then common venv locations
SNOW_CMD="${SNOW_CMD:-$(command -v snow 2>/dev/null || echo "")}"
if [[ -z "$SNOW_CMD" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  REPO_ROOT="$(dirname "$SCRIPT_DIR")"
  for candidate in "$REPO_ROOT/.venv/bin/snow" "${VIRTUAL_ENV:-/nonexistent}/bin/snow"; do
    if [[ -x "$candidate" ]]; then
      SNOW_CMD="$candidate"
      break
    fi
  done
fi
if [[ -z "$SNOW_CMD" ]]; then
  echo "Error: 'snow' CLI not found. Install with: pip install snowflake-cli"
  exit 1
fi

CONNECTION="default"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --connection) CONNECTION="$2"; shift 2 ;;
    *) echo "Usage: $0 [--connection name]"; exit 1 ;;
  esac
done

SQL_OPTS=("--connection" "$CONNECTION")
FAILURES=0

run_check() {
  local label="$1"
  local query="$2"
  echo ""
  echo "--- $label ---"
  if "$SNOW_CMD" sql -q "$query" "${SQL_OPTS[@]}"; then
    echo "  -> OK"
  else
    echo "  -> FAIL"
    FAILURES=$((FAILURES + 1))
  fi
}

echo "Snowpipe Verification (connection: $CONNECTION)"
echo "================================================"

run_check "1/5 Connection" \
  "SELECT CURRENT_VERSION() AS snowflake_version;"

run_check "2/5 Pipe status" \
  "SELECT SYSTEM\$PIPE_STATUS('martech.lead_enrichment_pipe') AS pipe_status;"

run_check "3/5 Row count" \
  "SELECT COUNT(*) AS row_count FROM martech.raw_webhook_events;"

run_check "4/5 Latest row" \
  "SELECT lead_id, loan_type, urgency_score, ingested_at
   FROM martech.raw_webhook_events
   ORDER BY ingested_at DESC
   LIMIT 1;"

run_check "5/5 Copy history (24h)" \
  "SELECT FILE_NAME, STATUS, FIRST_ERROR_MESSAGE, LAST_LOAD_TIME
   FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
     TABLE_NAME => 'RAW_WEBHOOK_EVENTS',
     START_TIME => DATEADD(HOUR, -24, CURRENT_TIMESTAMP())
   ))
   ORDER BY LAST_LOAD_TIME DESC
   LIMIT 10;"

echo ""
if [[ $FAILURES -gt 0 ]]; then
  echo "Result: $FAILURES check(s) failed"
  exit 1
else
  echo "Result: All checks passed"
  exit 0
fi
