"""Run and verify the isolated P1-INC-02 SQL Server CDC demonstration."""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyodbc


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONSUMER = "p1-inc-02-demo-consumer"
EXPECTED_OPERATION_COUNTS = {2: 2, 3: 1, 4: 1}


def parse_arguments() -> argparse.Namespace:
    """Parse connection and evidence-output configuration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", default="localhost,1433")
    parser.add_argument("--database", default="DWH_Insurance")
    parser.add_argument("--odbc-driver", default="ODBC Driver 18 for SQL Server")
    parser.add_argument("--password-env", default="SQLSERVER_SA_PASSWORD")
    parser.add_argument("--consumer", default=DEFAULT_CONSUMER)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--output", type=Path, default=Path("reports/data/p1-inc-02-cdc-demo.json"))
    return parser.parse_args()


def connection_string(args: argparse.Namespace) -> str:
    """Build a local SQL Server connection string without printing its secret."""
    password = os.environ.get(args.password_env)
    if not password:
        raise RuntimeError(f"Missing required environment variable: {args.password_env}")
    driver = args.odbc_driver.replace("}", "}}")
    return (
        f"DRIVER={{{driver}}};SERVER={args.server};DATABASE={args.database};"
        f"UID=sa;PWD={password};Encrypt=yes;TrustServerCertificate=yes;"
    )


def wait_for_capture(cursor: pyodbc.Cursor, demo_run_id: str, timeout_seconds: int) -> dict[int, int]:
    """Wait until SQL Server Agent exposes all expected controlled CDC events."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        rows = cursor.execute(
            """
            SELECT __$operation, COUNT_BIG(*)
            FROM cdc.meta_CdcDemoOperationalRecord_CT
            WHERE DemoRunId = CONVERT(uniqueidentifier, ?)
            GROUP BY __$operation;
            """,
            demo_run_id,
        ).fetchall()
        counts = {int(operation): int(count) for operation, count in rows}
        if all(counts.get(operation, 0) == expected for operation, expected in EXPECTED_OPERATION_COUNTS.items()):
            return counts
        time.sleep(1)
    raise TimeoutError("CDC capture did not expose the expected controlled events.")


def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    """Create isolated changes, consume them twice and return runtime evidence."""
    demo_run_id = str(uuid.uuid4())
    with pyodbc.connect(connection_string(args), autocommit=False) as connection:
        cursor = connection.cursor()
        if cursor.execute("SELECT is_cdc_enabled FROM sys.databases WHERE name = DB_NAME();").fetchval() != 1:
            raise RuntimeError("CDC is not enabled for DWH_Insurance. Apply V9 first.")
        cursor.execute(
            """
            INSERT INTO meta.CdcDemoOperationalRecord (DemoRunId, OperationalStatus, DemoNote)
            OUTPUT INSERTED.OperationalRecordId
            VALUES (CONVERT(uniqueidentifier, ?), N'INITIAL', N'P1-INC-02 controlled initial row');
            """,
            demo_run_id,
        )
        updated_record_id = int(cursor.fetchval())
        cursor.execute(
            """
            UPDATE meta.CdcDemoOperationalRecord
            SET OperationalStatus = N'UPDATED', DemoNote = N'P1-INC-02 controlled update',
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE OperationalRecordId = ?;
            """,
            updated_record_id,
        )
        cursor.execute(
            """
            INSERT INTO meta.CdcDemoOperationalRecord (DemoRunId, OperationalStatus, DemoNote)
            OUTPUT INSERTED.OperationalRecordId
            VALUES (CONVERT(uniqueidentifier, ?), N'INSERTED', N'P1-INC-02 controlled insert');
            """,
            demo_run_id,
        )
        inserted_record_id = int(cursor.fetchval())
        connection.commit()

        operation_counts = wait_for_capture(cursor, demo_run_id, args.timeout_seconds)
        capture_rows = cursor.execute(
            """
            SELECT __$operation, sys.fn_varbintohexstr(__$start_lsn),
                   sys.fn_varbintohexstr(__$seqval), OperationalRecordId,
                   OperationalStatus, DemoNote
            FROM cdc.meta_CdcDemoOperationalRecord_CT
            WHERE DemoRunId = CONVERT(uniqueidentifier, ?)
            ORDER BY __$start_lsn, __$seqval, __$operation;
            """,
            demo_run_id,
        ).fetchall()
        first_consume = cursor.execute(
            "EXEC meta.sp_ConsumeCdcDemoChanges @ConsumerName = ?, @DemoRunId = ?;",
            args.consumer,
            demo_run_id,
        ).fetchone()
        second_consume = cursor.execute(
            "EXEC meta.sp_ConsumeCdcDemoChanges @ConsumerName = ?, @DemoRunId = ?;",
            args.consumer,
            demo_run_id,
        ).fetchone()
        consumed_rows = cursor.execute(
            "SELECT COUNT_BIG(*) FROM meta.CdcDemoConsumedChange WHERE ConsumerName = ? AND DemoRunId = CONVERT(uniqueidentifier, ?);",
            args.consumer,
            demo_run_id,
        ).fetchval()
        watermark = cursor.execute(
            "SELECT sys.fn_varbintohexstr(LastStartLsn) FROM meta.CdcConsumerWatermark WHERE ConsumerName = ?;",
            args.consumer,
        ).fetchval()
        connection.commit()

    return {
        "stage": "P1-INC-02",
        "framing": "Synthetic CDC engineering demonstration; not brvehins1 source history.",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "demo_run_id": demo_run_id,
        "updated_operational_record_id": updated_record_id,
        "inserted_operational_record_id": inserted_record_id,
        "operation_counts": {str(key): value for key, value in operation_counts.items()},
        "captured_change_count": len(capture_rows),
        "captured_changes": [
            {
                "operation_code": int(row[0]), "start_lsn": row[1], "sequence_value": row[2],
                "operational_record_id": int(row[3]), "operational_status": row[4], "demo_note": row[5],
            }
            for row in capture_rows
        ],
        "consumer": args.consumer,
        "first_consume_new_rows": int(first_consume[0]),
        "second_consume_new_rows": int(second_consume[0]),
        "consumed_rows_for_demo": int(consumed_rows),
        "watermark_last_start_lsn": watermark,
    }


def main() -> int:
    """Run the demonstration and persist compact machine-readable evidence."""
    args = parse_arguments()
    if args.timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be positive")
    result = run_demo(args)
    output_path = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"CDC_DEMO_PASS demo_run_id={result['demo_run_id']}")
    print(f"CDC_CAPTURED_CHANGES={result['captured_change_count']}")
    print(f"CDC_FIRST_CONSUME_NEW_ROWS={result['first_consume_new_rows']}")
    print(f"CDC_SECOND_CONSUME_NEW_ROWS={result['second_consume_new_rows']}")
    print(f"CDC_EVIDENCE={output_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
