"""Streaming, idempotent loader for one canonical brvehins1 partition.

The script keeps raw CSV immutable, validates the frozen source contract, and
uses SourceFile + SourceRowNumber as technical lineage.  It intentionally does
not create customer or policy identifiers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

try:
    import pyodbc
except ImportError as exc:  # pragma: no cover - depends on local runtime setup
    raise SystemExit(
        "Thiếu pyodbc. Hãy chạy: python -m pip install -r requirements.txt"
    ) from exc


CANONICAL_PARTITIONS = frozenset(
    {
        "brvehins1a.csv",
        "brvehins1b.csv",
        "brvehins1c.csv",
        "brvehins1d.csv",
        "brvehins1e.csv",
    }
)

SOURCE_COLUMNS = (
    "Gender",
    "DrivAge",
    "VehYear",
    "VehModel",
    "VehGroup",
    "Area",
    "State",
    "StateAb",
    "ExposTotal",
    "ExposFireRob",
    "PremTotal",
    "PremFireRob",
    "SumInsAvg",
    "ClaimNbRob",
    "ClaimNbPartColl",
    "ClaimNbTotColl",
    "ClaimNbFire",
    "ClaimNbOther",
    "ClaimAmountRob",
    "ClaimAmountPartColl",
    "ClaimAmountTotColl",
    "ClaimAmountFire",
    "ClaimAmountOther",
)

TEXT_LIMITS = {
    "Gender": 20,
    "DrivAge": 20,
    "VehModel": 255,
    "VehGroup": 255,
    "Area": 100,
    "State": 100,
    "StateAb": 2,
}

DECIMAL_COLUMNS = (
    "ExposTotal",
    "ExposFireRob",
    "PremTotal",
    "PremFireRob",
    "SumInsAvg",
    "ClaimAmountRob",
    "ClaimAmountPartColl",
    "ClaimAmountTotColl",
    "ClaimAmountFire",
    "ClaimAmountOther",
)

DECIMAL_SPECS = {
    "ExposTotal": (21, 17),
    "ExposFireRob": (19, 6),
    "PremTotal": (34, 27),
    "PremFireRob": (19, 6),
    "SumInsAvg": (19, 6),
    "ClaimAmountRob": (19, 6),
    "ClaimAmountPartColl": (19, 6),
    "ClaimAmountTotColl": (19, 6),
    "ClaimAmountFire": (19, 6),
    "ClaimAmountOther": (19, 6),
}

INTEGER_COLUMNS = (
    "ClaimNbRob",
    "ClaimNbPartColl",
    "ClaimNbTotColl",
    "ClaimNbFire",
    "ClaimNbOther",
)

INSERT_SQL = """
INSERT INTO stg.BrVehIns1 (
    BatchId, SourceFile, SourceRowNumber, SourceRecordHash,
    Gender, DrivAge, VehYear, VehModel, VehGroup, Area, State, StateAb,
    ExposTotal, ExposFireRob, PremTotal, PremFireRob, SumInsAvg,
    ClaimNbRob, ClaimNbPartColl, ClaimNbTotColl, ClaimNbFire, ClaimNbOther,
    ClaimAmountRob, ClaimAmountPartColl, ClaimAmountTotColl,
    ClaimAmountFire, ClaimAmountOther
)
VALUES (
    ?, ?, ?, ?,
    ?, ?, ?, ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?,
    ?, ?, ?, ?, ?
)
"""


class SourceContractError(ValueError):
    """A raw CSV row violates a hard rule in the frozen source contract."""


if INSERT_SQL.count("?") != len(SOURCE_COLUMNS) + 4:
    raise RuntimeError("INSERT_SQL phải có đúng bốn metadata và 23 source parameters.")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Nạp streaming một partition canonical brvehins1 vào SQL Server staging."
    )
    parser.add_argument("--source-file", required=True, choices=sorted(CANONICAL_PARTITIONS))
    parser.add_argument(
        "--raw-directory",
        type=Path,
        default=Path("data/raw/brvehins1"),
        help="Thư mục chỉ-đọc chứa năm CSV canonical.",
    )
    parser.add_argument("--server", default="localhost,1433")
    parser.add_argument("--database", default="DWH_Insurance")
    parser.add_argument("--odbc-driver", default="ODBC Driver 18 for SQL Server")
    parser.add_argument("--password-env", default="SQLSERVER_SA_PASSWORD")
    parser.add_argument("--batch-size", type=int, default=5_000)
    return parser.parse_args()


def text_or_none(value: str | None, field: str, row_number: int) -> str | None:
    if value is None:
        raise SourceContractError(f"Dòng {row_number}: thiếu cột {field}.")
    if value == "":
        return None
    limit = TEXT_LIMITS.get(field)
    if limit is not None and len(value) > limit:
        raise SourceContractError(
            f"Dòng {row_number}: {field} dài {len(value)} ký tự, vượt giới hạn {limit}."
        )
    return value


def decimal_value(value: str | None, field: str, row_number: int) -> Decimal:
    if value in (None, ""):
        raise SourceContractError(f"Dòng {row_number}: {field} là measure bắt buộc nhưng bị NULL/blank.")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise SourceContractError(f"Dòng {row_number}: {field} không parse được thành decimal.") from exc
    if not parsed.is_finite() or parsed < 0:
        raise SourceContractError(f"Dòng {row_number}: {field} phải hữu hạn và không âm.")
    precision, scale = DECIMAL_SPECS[field]
    fractional_digits = max(0, -parsed.as_tuple().exponent)
    integral_digits = 0 if parsed.is_zero() else max(0, parsed.adjusted() + 1)
    if fractional_digits > scale or integral_digits > precision - scale:
        raise SourceContractError(
            f"Dòng {row_number}: {field} không vừa DECIMAL({precision},{scale}) của contract."
        )
    return parsed


def integer_value(value: str | None, field: str, row_number: int, nullable: bool = False) -> int | None:
    if value in (None, ""):
        if nullable:
            return None
        raise SourceContractError(f"Dòng {row_number}: {field} là measure bắt buộc nhưng bị NULL/blank.")
    try:
        parsed = int(value)
    except ValueError as exc:
        raise SourceContractError(f"Dòng {row_number}: {field} không parse được thành integer.") from exc
    if parsed < 0:
        raise SourceContractError(f"Dòng {row_number}: {field} không được âm.")
    if not -(2**31) <= parsed < 2**31:
        raise SourceContractError(f"Dòng {row_number}: {field} vượt miền INT SQL Server.")
    return parsed


def canonical_hash(values: tuple[Any, ...]) -> str:
    """SHA-256 audit fingerprint for logical source values, not a business key."""
    payload: list[list[Any]] = []
    for name, value in zip(SOURCE_COLUMNS, values, strict=True):
        if isinstance(value, Decimal):
            normalized: Any = format(value, "f")
        else:
            normalized = value
        payload.append([name, normalized])
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest().upper()


def parse_source_row(row: dict[str | None, str | list[str] | None], row_number: int) -> tuple[Any, ...]:
    if row.get(None) is not None:
        raise SourceContractError(f"Dòng {row_number}: có nhiều field hơn schema canonical 23 cột.")

    values: dict[str, Any] = {}
    for field in ("Gender", "DrivAge", "VehModel", "VehGroup", "Area", "State", "StateAb"):
        raw_value = row.get(field)
        if isinstance(raw_value, list):
            raise SourceContractError(f"Dòng {row_number}: cấu trúc CSV của {field} không hợp lệ.")
        values[field] = text_or_none(raw_value, field, row_number)

    raw_veh_year = row.get("VehYear")
    if isinstance(raw_veh_year, list):
        raise SourceContractError(f"Dòng {row_number}: cấu trúc CSV của VehYear không hợp lệ.")
    values["VehYear"] = integer_value(raw_veh_year, "VehYear", row_number, nullable=True)

    for field in DECIMAL_COLUMNS:
        raw_value = row.get(field)
        if isinstance(raw_value, list):
            raise SourceContractError(f"Dòng {row_number}: cấu trúc CSV của {field} không hợp lệ.")
        values[field] = decimal_value(raw_value, field, row_number)

    for field in INTEGER_COLUMNS:
        raw_value = row.get(field)
        if isinstance(raw_value, list):
            raise SourceContractError(f"Dòng {row_number}: cấu trúc CSV của {field} không hợp lệ.")
        values[field] = integer_value(raw_value, field, row_number)

    if (values["State"] is None) != (values["StateAb"] is None):
        raise SourceContractError(
            f"Dòng {row_number}: State và StateAb phải cùng NULL hoặc cùng có giá trị."
        )

    return tuple(values[field] for field in SOURCE_COLUMNS)


def set_required_session_options(cursor: pyodbc.Cursor) -> None:
    cursor.execute(
        """
        SET NOCOUNT ON;
        SET ANSI_NULLS ON;
        SET QUOTED_IDENTIFIER ON;
        SET ANSI_PADDING ON;
        SET ANSI_WARNINGS ON;
        SET ARITHABORT ON;
        SET CONCAT_NULL_YIELDS_NULL ON;
        SET NUMERIC_ROUNDABORT OFF;
        """
    )


def acquire_session_lock(cursor: pyodbc.Cursor, source_file: str) -> None:
    lock_resource = f"stg.load_brvehins1:{source_file}"
    row = cursor.execute(
        """
        DECLARE @lock_result INT;
        EXEC @lock_result = sys.sp_getapplock
            @Resource = ?,
            @LockMode = N'Exclusive',
            @LockOwner = N'Session',
            @LockTimeout = 60000;
        SELECT @lock_result AS LockResult;
        """,
        lock_resource,
    ).fetchone()
    if row is None or row[0] < 0:
        raise RuntimeError(f"Không lấy được ingestion lock cho {source_file}.")


def release_session_lock(cursor: pyodbc.Cursor, source_file: str) -> None:
    cursor.execute(
        "EXEC sys.sp_releaseapplock @Resource = ?, @LockOwner = N'Session';",
        f"stg.load_brvehins1:{source_file}",
    )


def odbc_braced_value(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


def chunks(items: list[tuple[Any, ...]], size: int) -> Iterable[list[tuple[Any, ...]]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def load_partition(args: argparse.Namespace) -> tuple[str, str, int, int, int]:
    if args.batch_size <= 0:
        raise ValueError("--batch-size phải lớn hơn 0.")

    source_file = args.source_file
    source_path = (args.raw_directory / source_file).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy partition canonical: {source_path}")

    password = os.environ.get(args.password_env)
    if not password:
        raise RuntimeError(f"Thiếu biến môi trường credential: {args.password_env}")

    connection_string = (
        f"DRIVER={{{args.odbc_driver}}};"
        f"SERVER={odbc_braced_value(args.server)};"
        f"DATABASE={odbc_braced_value(args.database)};"
        "UID=sa;"
        f"PWD={odbc_braced_value(password)};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )

    started = time.perf_counter()
    batch_id: str | None = None
    rejected_rows = 0
    lock_acquired = False
    connection = pyodbc.connect(connection_string, autocommit=False)
    cursor = connection.cursor()

    try:
        set_required_session_options(cursor)
        acquire_session_lock(cursor, source_file)
        lock_acquired = True

        manifest_row = cursor.execute(
            """
            SELECT ExpectedSourceRows
            FROM meta.SourceFileManifest
            WHERE SourceFile = ? AND IsCanonical = 1;
            """,
            source_file,
        ).fetchone()
        if manifest_row is None:
            raise RuntimeError(f"{source_file} không có trong canonical SourceFileManifest.")
        expected_rows = int(manifest_row[0])

        existing = cursor.execute(
            """
            SELECT TOP (1) BatchId, StagingRows, RejectedRows, ElapsedMilliseconds
            FROM meta.IngestionBatch
            WHERE SourceFile = ? AND Status = N'SUCCESS'
            ORDER BY CompletedAtUtc DESC;
            """,
            source_file,
        ).fetchone()
        if existing is not None:
            batch_id = str(existing[0])
            cursor.execute(
                """
                INSERT INTO meta.PipelineAudit (BatchId, StageName, Status, RowsAffected, Detail)
                VALUES (?, N'STAGING_LOAD', N'SKIPPED', 0,
                        N'Partition already has a SUCCESS batch; client loader added no staging rows.');
                """,
                batch_id,
            )
            connection.commit()
            return batch_id, "SKIPPED", expected_rows, 0, 0

        batch_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO meta.IngestionBatch (BatchId, SourceFile, ExpectedSourceRows, Status)
            VALUES (?, ?, ?, N'RUNNING');
            """,
            batch_id,
            source_file,
            expected_rows,
        )
        cursor.execute(
            """
            INSERT INTO meta.PipelineAudit (BatchId, StageName, Status, RowsAffected, Detail)
            VALUES (?, N'STAGING_LOAD', N'STARTED', 0,
                    N'Client-side streaming CSV load started.');
            """,
            batch_id,
        )
        connection.commit()

        cursor.fast_executemany = True
        source_rows = 0
        pending: list[tuple[Any, ...]] = []
        with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != SOURCE_COLUMNS:
                raise SourceContractError(
                    f"Header của {source_file} không khớp schema canonical 23 cột."
                )
            for source_rows, row in enumerate(reader, start=1):
                try:
                    source_values = parse_source_row(row, source_rows)
                except SourceContractError:
                    rejected_rows += 1
                    raise
                source_hash = canonical_hash(source_values)
                pending.append(
                    (batch_id, source_file, source_rows, source_hash, *source_values)
                )
                if len(pending) >= args.batch_size:
                    cursor.executemany(INSERT_SQL, pending)
                    pending.clear()
            if pending:
                cursor.executemany(INSERT_SQL, pending)

        if source_rows != expected_rows:
            raise SourceContractError(
                f"{source_file}: source rows={source_rows}, manifest expected={expected_rows}."
            )

        staging_rows = int(
            cursor.execute(
                "SELECT COUNT_BIG(*) FROM stg.BrVehIns1 WHERE BatchId = ?;", batch_id
            ).fetchone()[0]
        )
        if staging_rows != source_rows:
            raise RuntimeError(
                f"Đối soát thất bại: source={source_rows}, staging={staging_rows}."
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        cursor.execute(
            """
            UPDATE meta.IngestionBatch
            SET StagingRows = ?, RejectedRows = 0, CompletedAtUtc = SYSUTCDATETIME(),
                ElapsedMilliseconds = ?, Status = N'SUCCESS', ErrorMessage = NULL
            WHERE BatchId = ? AND Status = N'RUNNING';
            """,
            staging_rows,
            elapsed_ms,
            batch_id,
        )
        completed_batch = cursor.execute(
            "SELECT Status FROM meta.IngestionBatch WHERE BatchId = ?;", batch_id
        ).fetchone()
        if completed_batch is None or completed_batch[0] != "SUCCESS":
            raise RuntimeError("Không thể chuyển ingestion batch sang SUCCESS.")
        cursor.execute(
            """
            INSERT INTO meta.PipelineAudit (BatchId, StageName, Status, RowsAffected, Detail)
            VALUES (?, N'STAGING_LOAD', N'SUCCESS', ?, ?);
            """,
            batch_id,
            staging_rows,
            f"Source rows={source_rows}; staging rows={staging_rows}; rejected rows=0.",
        )
        connection.commit()
        return batch_id, "SUCCESS", source_rows, staging_rows, elapsed_ms

    except Exception as exc:
        connection.rollback()
        if batch_id is not None:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            set_required_session_options(cursor)
            cursor.execute(
                """
                UPDATE meta.IngestionBatch
                SET StagingRows = NULL, RejectedRows = ?, CompletedAtUtc = SYSUTCDATETIME(),
                    ElapsedMilliseconds = ?, Status = N'FAILED', ErrorMessage = ?
                WHERE BatchId = ? AND Status = N'RUNNING';
                """,
                rejected_rows,
                elapsed_ms,
                str(exc)[:2048],
                batch_id,
            )
            cursor.execute(
                """
                INSERT INTO meta.PipelineAudit (BatchId, StageName, Status, RowsAffected, Detail)
                VALUES (?, N'STAGING_LOAD', N'FAILED', ?, ?);
                """,
                batch_id,
                rejected_rows,
                str(exc)[:2048],
            )
            connection.commit()
        raise
    finally:
        if lock_acquired:
            try:
                set_required_session_options(cursor)
                release_session_lock(cursor, source_file)
                connection.commit()
            except pyodbc.Error:
                connection.rollback()
        cursor.close()
        connection.close()


def main() -> int:
    args = parse_arguments()
    try:
        batch_id, outcome, source_rows, staging_rows, elapsed_ms = load_partition(args)
    except (OSError, RuntimeError, SourceContractError, pyodbc.Error, ValueError) as exc:
        print(f"[FAILED] {exc}", file=sys.stderr)
        return 1

    if outcome == "SKIPPED":
        print(
            f"[SKIPPED] {args.source_file}; batch={batch_id}; "
            f"đã có SUCCESS batch, không thêm staging row."
        )
        return 0

    print(
        f"[SUCCESS] {args.source_file}; batch={batch_id}; "
        f"source_rows={source_rows}; staging_rows={staging_rows}; elapsed_ms={elapsed_ms}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
