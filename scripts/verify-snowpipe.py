#!/usr/bin/env python3
"""Verify Snowpipe pipeline health by running diagnostic queries against Snowflake.

Prerequisites:
    pip install -e ".[ops]"

Authentication (pick one):
    1. Snowflake CLI config (recommended):
       snow connection add        # one-time setup, saved to ~/.snowflake/config.toml
       python scripts/verify-snowpipe.py --connection default

    2. Environment variables:
       SNOWFLAKE_ACCOUNT    e.g. xy12345.us-east-1
       SNOWFLAKE_USER       Snowflake username
       SNOWFLAKE_PASSWORD   Snowflake password
       SNOWFLAKE_WAREHOUSE  Compute warehouse
       SNOWFLAKE_DATABASE   Database name

Usage:
    python scripts/verify-snowpipe.py [--connection name]
    python scripts/verify-snowpipe.py                       # uses env vars
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import snowflake.connector  # type: ignore[import-untyped]
from snowflake.connector.cursor import SnowflakeCursor  # type: ignore[import-untyped]

SCHEMA = "martech"
TABLE = "martech.raw_webhook_events"
PIPE = "martech.lead_enrichment_pipe"

REQUIRED_ENV_VARS = [
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
]


@dataclass
class CheckResult:
    name: str
    status: Literal["OK", "WARN", "FAIL"]
    message: str
    detail: str | None = None


def check_connection(cursor: SnowflakeCursor) -> CheckResult:
    """Verify basic connectivity by querying the Snowflake version."""
    try:
        cursor.execute("SELECT CURRENT_VERSION()")
        row = cursor.fetchone()
        version = row[0] if row else "unknown"
        return CheckResult("Connection", "OK", f"Snowflake {version}")
    except Exception as e:
        return CheckResult("Connection", "FAIL", str(e))


def check_pipe_status(cursor: SnowflakeCursor) -> CheckResult:
    """Check the execution state of the Snowpipe."""
    try:
        cursor.execute(f"SELECT SYSTEM$PIPE_STATUS('{PIPE}')")
        row = cursor.fetchone()
        if not row:
            return CheckResult("Pipe status", "FAIL", "No result returned")

        status = json.loads(row[0])
        state = status.get("executionState", "UNKNOWN")
        pending = status.get("pendingFileCount", 0)

        if state == "RUNNING":
            return CheckResult("Pipe status", "OK", f"{state}, {pending} pending")
        return CheckResult("Pipe status", "WARN", f"{state}, {pending} pending")
    except Exception as e:
        return CheckResult("Pipe status", "FAIL", str(e))


def check_row_count(cursor: SnowflakeCursor) -> CheckResult:
    """Count rows in the target table."""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE}")
        row = cursor.fetchone()
        count = row[0] if row else 0

        if count == 0:
            return CheckResult("Row count", "WARN", "0 rows (table is empty)")
        return CheckResult("Row count", "OK", f"{count:,} rows")
    except Exception as e:
        return CheckResult("Row count", "FAIL", str(e))


def check_latest_row(cursor: SnowflakeCursor) -> CheckResult:
    """Fetch the most recently ingested row."""
    try:
        cursor.execute(
            f"SELECT lead_id, loan_type, urgency_score, ingested_at "
            f"FROM {TABLE} ORDER BY ingested_at DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if not row:
            return CheckResult("Latest row", "WARN", "No rows found")

        lead_id, loan_type, urgency, ingested_at = row
        age = ""
        if ingested_at:
            delta = datetime.now(UTC) - ingested_at.replace(tzinfo=UTC)
            minutes = int(delta.total_seconds() / 60)
            if minutes < 60:
                age = f", ingested {minutes}m ago"
            else:
                hours = minutes // 60
                age = f", ingested {hours}h ago"

        return CheckResult(
            "Latest row",
            "OK",
            f"lead_id={lead_id}, loan_type={loan_type}, urgency={urgency}{age}",
        )
    except Exception as e:
        return CheckResult("Latest row", "FAIL", str(e))


def check_copy_history(cursor: SnowflakeCursor) -> CheckResult:
    """Check for recent copy errors in the last 24 hours."""
    try:
        cursor.execute(
            "SELECT FILE_NAME, STATUS, FIRST_ERROR_MESSAGE, LAST_LOAD_TIME "
            "FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY("
            "  TABLE_NAME => 'RAW_WEBHOOK_EVENTS',"
            "  START_TIME => DATEADD(HOUR, -24, CURRENT_TIMESTAMP())"
            ")) ORDER BY LAST_LOAD_TIME DESC LIMIT 20"
        )
        rows = cursor.fetchall()

        if not rows:
            return CheckResult("Copy history (24h)", "OK", "No copy activity in last 24h")

        total = len(rows)
        errors = [r for r in rows if r[2]]  # FIRST_ERROR_MESSAGE is not null
        loaded = total - len(errors)

        if errors:
            first_error = errors[0][2]
            return CheckResult(
                "Copy history (24h)",
                "WARN",
                f"{loaded} loaded, {len(errors)} with errors",
                detail=f'Error: "{first_error}"',
            )
        return CheckResult("Copy history (24h)", "OK", f"{loaded} loaded, 0 errors")
    except Exception as e:
        return CheckResult("Copy history (24h)", "FAIL", str(e))


def print_result(index: int, total: int, result: CheckResult) -> None:
    """Print a single check result with aligned formatting."""
    label = f"[{index}/{total}] {result.name}"
    dots = "." * (30 - len(label))
    print(f"{label} {dots} {result.status} ({result.message})")
    if result.detail:
        print(f"      {result.detail}")


def build_connection(connection_name: str | None) -> snowflake.connector.SnowflakeConnection:  # type: ignore[name-defined]
    """Connect using CLI config (--connection) or environment variables."""
    if connection_name:
        return snowflake.connector.connect(connection_name=connection_name, schema=SCHEMA)

    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        print("Tip: use --connection <name> to authenticate via Snowflake CLI config instead")
        sys.exit(1)

    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=SCHEMA,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Snowpipe pipeline health")
    parser.add_argument(
        "--connection",
        default=None,
        help="Snowflake CLI connection name (from ~/.snowflake/config.toml)",
    )
    args = parser.parse_args()

    print("Snowpipe Verification")
    print("=====================")
    print()

    conn = build_connection(args.connection)

    checks = [
        check_connection,
        check_pipe_status,
        check_row_count,
        check_latest_row,
        check_copy_history,
    ]

    results: list[CheckResult] = []
    try:
        cursor = conn.cursor()
        for i, check in enumerate(checks, 1):
            result = check(cursor)
            results.append(result)
            print_result(i, len(checks), result)
    finally:
        conn.close()

    ok = sum(1 for r in results if r.status == "OK")
    warn = sum(1 for r in results if r.status == "WARN")
    fail = sum(1 for r in results if r.status == "FAIL")

    print()
    print(f"Result: {ok} passed, {warn} warning, {fail} failed")

    return 1 if fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
