"""Streaming, idempotent Track-A loader for the immutable SUSEP market CSV.

The loader retains numeric source text for forensic fidelity and stores a
controlled DECIMAL(38,18) analytic representation for SQL aggregation.  It
does not infer customer, policy, vehicle, exposure, or relationships to Track B.
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
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Any

try:
    import pyodbc
except ImportError as exc:  # pragma: no cover - local dependency guard
    raise SystemExit("Thiếu pyodbc. Hãy chạy .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt") from exc


SOURCE_FILE_NAME = "insurance_dataset.csv"
SOURCE_COLUMNS = (
    "company_code",
    "company_name",
    "year_month",
    "product",
    "state",
    "premiums",
    "claims",
    "claim_premium_ratio",
)
TEXT_LIMITS = {"company_name": 116, "product": 42, "state": 2}
ANALYTIC_QUANTUM = Decimal("0.000000000000000001")

INSERT_SQL = """
INSERT INTO stg.SusepInsuranceMarket(
    BatchId,SourceFile,SourceFileSha256,SourceRowNumber,SourceRecordHash,
    CompanyCode,CompanyName,YearMonth,Product,State,
    PremiumsRaw,Premiums,ClaimsRaw,Claims,ClaimPremiumRatioRaw,ClaimPremiumRatio
)
VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""
REJECT_SQL = """
INSERT INTO stg.SusepInsuranceMarketReject(
    BatchId,SourceFile,SourceFileSha256,SourceRowNumber,SourceRecordHash,RawPayload,RejectReason
)
VALUES(?,?,?,?,?,?,?)
"""


class SourceContractError(ValueError):
    """The current CSV violates a hard source-data-contract rule."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nạp streaming CSV SUSEP vào stg.SusepInsuranceMarket.")
    parser.add_argument("--source-path", type=Path, default=Path("data/raw/susep.gov.br/insurance_dataset.csv"))
    parser.add_argument("--server", default="localhost,1433")
    parser.add_argument("--database", default="DWH_Insurance")
    parser.add_argument("--odbc-driver", default="ODBC Driver 18 for SQL Server")
    parser.add_argument("--password-env", default="SQLSERVER_SA_PASSWORD")
    parser.add_argument("--batch-size", type=int, default=20_000)
    return parser.parse_args()


def odbc_braced_value(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


def source_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_header(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        header = tuple(next(csv.reader(handle)))
    if header != SOURCE_COLUMNS:
        raise SourceContractError(
            "Header SUSEP không khớp contract: " + ",".join(header)
        )


def record_hash(row: dict[str | None, str | list[str] | None]) -> str:
    """Hash textual source values with a NUL separator, including field order."""
    values: list[str] = []
    for column in SOURCE_COLUMNS:
        value = row.get(column)
        if isinstance(value, list):
            values.append("<CSV_EXTRA_FIELD>" + "\x1f".join(value))
        elif value is None:
            values.append("<MISSING>")
        else:
            values.append(value)
    return hashlib.sha256("\0".join(values).encode("utf-8")).hexdigest().upper()


def raw_payload(row: dict[str | None, str | list[str] | None]) -> str:
    """Serialize only rejected source data for diagnostic lineage."""
    return json.dumps(row, ensure_ascii=False, separators=(",", ":"), default=str)


def required_text(row: dict[str | None, str | list[str] | None], field: str, row_number: int) -> str:
    value = row.get(field)
    if isinstance(value, list) or value is None or value == "":
        raise SourceContractError(f"Dòng {row_number}: {field} bắt buộc và phải là text đơn.")
    limit = TEXT_LIMITS[field]
    if len(value) > limit:
        raise SourceContractError(f"Dòng {row_number}: {field} dài {len(value)}, vượt NVARCHAR({limit}).")
    return value


def company_code(row: dict[str | None, str | list[str] | None], row_number: int) -> int:
    value = row.get("company_code")
    if isinstance(value, list) or value is None or value == "":
        raise SourceContractError(f"Dòng {row_number}: company_code bắt buộc.")
    try:
        parsed = int(value)
    except ValueError as exc:
        raise SourceContractError(f"Dòng {row_number}: company_code không phải INT.") from exc
    if str(parsed) != value:
        raise SourceContractError(f"Dòng {row_number}: company_code phải là integer lexical chuẩn.")
    if not -(2**31) <= parsed < 2**31:
        raise SourceContractError(f"Dòng {row_number}: company_code vượt miền INT SQL Server.")
    return parsed


def month_value(row: dict[str | None, str | list[str] | None], row_number: int) -> date:
    value = row.get("year_month")
    if isinstance(value, list) or value is None or value == "":
        raise SourceContractError(f"Dòng {row_number}: year_month bắt buộc.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SourceContractError(f"Dòng {row_number}: year_month không phải ISO date hợp lệ.") from exc
    if parsed.isoformat() != value or parsed.day != 1:
        raise SourceContractError(f"Dòng {row_number}: year_month phải là ISO ngày đầu tháng.")
    return parsed


def numeric_value(
    row: dict[str | None, str | list[str] | None], field: str, row_number: int, *, nullable_na: bool = False
) -> tuple[str | None, Decimal | None]:
    value = row.get(field)
    if isinstance(value, list) or value is None or value == "":
        raise SourceContractError(f"Dòng {row_number}: {field} phải là decimal text hoặc NA theo contract.")
    if nullable_na and value == "NA":
        return None, None
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise SourceContractError(f"Dòng {row_number}: {field} không parse được thành decimal.") from exc
    if not parsed.is_finite():
        raise SourceContractError(f"Dòng {row_number}: {field} phải là finite decimal.")
    with localcontext() as context:
        context.prec = 60
        rounded = parsed.quantize(ANALYTIC_QUANTUM, rounding=ROUND_HALF_EVEN)
    if rounded.adjusted() > 19:
        raise SourceContractError(f"Dòng {row_number}: {field} vượt phần nguyên DECIMAL(38,18).")
    return value, rounded


def parse_source_row(row: dict[str | None, str | list[str] | None], row_number: int) -> tuple[Any, ...]:
    if row.get(None) is not None:
        raise SourceContractError(f"Dòng {row_number}: số cột CSV lớn hơn contract 8 cột.")
    company = company_code(row, row_number)
    name = required_text(row, "company_name", row_number)
    period = month_value(row, row_number)
    product = required_text(row, "product", row_number)
    state = required_text(row, "state", row_number)
    premiums_raw, premiums = numeric_value(row, "premiums", row_number)
    claims_raw, claims = numeric_value(row, "claims", row_number)
    ratio_raw, ratio = numeric_value(row, "claim_premium_ratio", row_number, nullable_na=True)
    return company, name, period, product, state, premiums_raw, premiums, claims_raw, claims, ratio_raw, ratio


def set_required_session_options(cursor: pyodbc.Cursor) -> None:
    cursor.execute(
        """
        SET NOCOUNT ON; SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
        SET ANSI_PADDING ON; SET ANSI_WARNINGS ON; SET ARITHABORT ON;
        SET CONCAT_NULL_YIELDS_NULL ON; SET NUMERIC_ROUNDABORT OFF;
        """
    )


def acquire_session_lock(cursor: pyodbc.Cursor, source_file: str) -> None:
    row = cursor.execute(
        """
        DECLARE @result INT;
        EXEC @result=sys.sp_getapplock @Resource=?, @LockMode=N'Exclusive',
            @LockOwner=N'Session', @LockTimeout=60000;
        SELECT @result;
        """,
        f"stg.load_susep:{source_file}",
    ).fetchone()
    if row is None or row[0] < 0:
        raise RuntimeError(f"Không lấy được ingestion lock cho {source_file}.")


def release_session_lock(cursor: pyodbc.Cursor, source_file: str) -> None:
    cursor.execute("EXEC sys.sp_releaseapplock @Resource=?, @LockOwner=N'Session';", f"stg.load_susep:{source_file}")


def flush(
    connection: pyodbc.Connection,
    cursor: pyodbc.Cursor,
    accepted: list[tuple[Any, ...]],
    rejected: list[tuple[Any, ...]],
) -> None:
    if accepted:
        cursor.executemany(INSERT_SQL, accepted)
        accepted.clear()
    if rejected:
        cursor.executemany(REJECT_SQL, rejected)
        rejected.clear()
    connection.commit()


def load_susep(args: argparse.Namespace) -> tuple[str, str, int, int, int, int]:
    if args.batch_size <= 0:
        raise ValueError("--batch-size phải lớn hơn 0.")
    path = args.source_path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy raw SUSEP: {path}")
    if path.name != SOURCE_FILE_NAME:
        raise SourceContractError(f"Contract chỉ nhận filename {SOURCE_FILE_NAME}, không phải {path.name}.")
    validate_header(path)
    source_bytes = path.stat().st_size
    file_hash = source_file_sha256(path)
    password = os.environ.get(args.password_env)
    if not password:
        raise RuntimeError(f"Thiếu credential environment variable: {args.password_env}")
    connection_string = (
        f"DRIVER={{{args.odbc_driver}}};SERVER={odbc_braced_value(args.server)};"
        f"DATABASE={odbc_braced_value(args.database)};UID=sa;PWD={odbc_braced_value(password)};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )

    started = time.perf_counter()
    batch_id: str | None = None
    lock_acquired = False
    connection = pyodbc.connect(connection_string, autocommit=False)
    cursor = connection.cursor()
    try:
        set_required_session_options(cursor)
        acquire_session_lock(cursor, path.name)
        lock_acquired = True
        manifest = cursor.execute(
            "SELECT ExpectedSourceRows,ExpectedSourceBytes FROM meta.SusepSourceFileManifest WHERE SourceFile=? AND IsCanonical=1;",
            path.name,
        ).fetchone()
        if manifest is None:
            raise RuntimeError("Thiếu canonical SUSEP manifest; hãy apply V11 trước.")
        expected_rows, expected_bytes = int(manifest[0]), int(manifest[1])
        if source_bytes != expected_bytes:
            raise SourceContractError(f"SUSEP bytes={source_bytes}, manifest expected={expected_bytes}.")

        existing = cursor.execute(
            """
            SELECT TOP(1) b.BatchId,b.AcceptedRows,b.RejectedRows,
                   (SELECT COUNT_BIG(*) FROM stg.SusepInsuranceMarket s WHERE s.BatchId=b.BatchId),
                   (SELECT COUNT_BIG(*) FROM stg.SusepInsuranceMarketReject r WHERE r.BatchId=b.BatchId)
            FROM meta.SusepIngestionBatch b
            WHERE b.SourceFile=? AND b.SourceFileSha256=? AND b.Status=N'SUCCESS'
            ORDER BY b.CompletedAtUtc DESC;
            """,
            path.name,
            file_hash,
        ).fetchone()
        if existing is not None:
            if int(existing[1]) != int(existing[3]) or int(existing[2]) != int(existing[4]) or int(existing[1]) + int(existing[2]) != expected_rows:
                raise RuntimeError("SUCCESS batch SUSEP tồn tại nhưng reconciliation staging/reject không còn đúng.")
            cursor.execute(
                "INSERT INTO meta.SusepPipelineAudit(BatchId,StageName,Status,RowsAffected,Detail) VALUES(?,N'STAGING_LOAD',N'SKIPPED',0,N'Cùng source fingerprint đã SUCCESS; không thêm row.');",
                existing[0],
            )
            connection.commit()
            return str(existing[0]), "SKIPPED", expected_rows, int(existing[1]), int(existing[2]), 0

        # A failed/restarted batch never becomes a source of duplicate technical identities.
        cursor.execute(
            """
            DELETE r FROM stg.SusepInsuranceMarketReject r
            JOIN meta.SusepIngestionBatch b ON b.BatchId=r.BatchId
            WHERE b.SourceFile=? AND b.SourceFileSha256=? AND b.Status IN(N'FAILED',N'RUNNING');
            DELETE s FROM stg.SusepInsuranceMarket s
            JOIN meta.SusepIngestionBatch b ON b.BatchId=s.BatchId
            WHERE b.SourceFile=? AND b.SourceFileSha256=? AND b.Status IN(N'FAILED',N'RUNNING');
            """,
            path.name,
            file_hash,
            path.name,
            file_hash,
        )
        connection.commit()

        batch_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO meta.SusepIngestionBatch(BatchId,SourceFile,SourceFileSha256,SourceBytes,ExpectedSourceRows,Status)
            VALUES(?,?,?,?,?,N'RUNNING');
            INSERT INTO meta.SusepPipelineAudit(BatchId,StageName,Status,RowsAffected,Detail)
            VALUES(?,N'STAGING_LOAD',N'STARTED',0,N'CSV streaming load started; raw remains read-only.');
            """,
            batch_id,
            path.name,
            file_hash,
            source_bytes,
            expected_rows,
            batch_id,
        )
        connection.commit()
        cursor.fast_executemany = True
        accepted_pending: list[tuple[Any, ...]] = []
        rejected_pending: list[tuple[Any, ...]] = []
        accepted_rows = 0
        rejected_rows = 0
        source_rows = 0
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != SOURCE_COLUMNS:
                raise SourceContractError("Header thay đổi trong khi đang nạp.")
            for source_rows, row in enumerate(reader, start=1):
                fingerprint = record_hash(row)
                try:
                    values = parse_source_row(row, source_rows)
                except SourceContractError as error:
                    rejected_rows += 1
                    rejected_pending.append((batch_id, path.name, file_hash, source_rows, fingerprint, raw_payload(row), str(error)[:2048]))
                else:
                    accepted_rows += 1
                    accepted_pending.append((batch_id, path.name, file_hash, source_rows, fingerprint, *values))
                if len(accepted_pending) + len(rejected_pending) >= args.batch_size:
                    flush(connection, cursor, accepted_pending, rejected_pending)
        flush(connection, cursor, accepted_pending, rejected_pending)

        if source_rows != expected_rows:
            raise SourceContractError(f"SUSEP rows={source_rows}, manifest expected={expected_rows}.")
        if source_rows != accepted_rows + rejected_rows:
            raise RuntimeError("Source reconciliation trong bộ nhớ thất bại.")
        actual = cursor.execute(
            """
            SELECT
                (SELECT COUNT_BIG(*) FROM stg.SusepInsuranceMarket WHERE BatchId=?),
                (SELECT COUNT_BIG(*) FROM stg.SusepInsuranceMarketReject WHERE BatchId=?);
            """,
            batch_id,
            batch_id,
        ).fetchone()
        if int(actual[0]) != accepted_rows or int(actual[1]) != rejected_rows:
            raise RuntimeError(f"Staging reconciliation thất bại: accepted={actual[0]}, rejected={actual[1]}.")
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        cursor.execute(
            """
            UPDATE meta.SusepIngestionBatch
            SET AcceptedRows=?,RejectedRows=?,CompletedAtUtc=SYSUTCDATETIME(),ElapsedMilliseconds=?,Status=N'SUCCESS',ErrorMessage=NULL
            WHERE BatchId=? AND Status=N'RUNNING';
            INSERT INTO meta.SusepPipelineAudit(BatchId,StageName,Status,RowsAffected,Detail)
            VALUES(?,N'STAGING_LOAD',N'SUCCESS',?,?);
            """,
            accepted_rows,
            rejected_rows,
            elapsed_ms,
            batch_id,
            batch_id,
            accepted_rows,
            f"source={source_rows}; accepted={accepted_rows}; rejected={rejected_rows}; source_sha256={file_hash}.",
        )
        connection.commit()
        return batch_id, "SUCCESS", source_rows, accepted_rows, rejected_rows, elapsed_ms
    except Exception as error:
        connection.rollback()
        if batch_id is not None:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            set_required_session_options(cursor)
            cursor.execute(
                """
                UPDATE meta.SusepIngestionBatch
                SET CompletedAtUtc=SYSUTCDATETIME(),ElapsedMilliseconds=?,Status=N'FAILED',ErrorMessage=?
                WHERE BatchId=? AND Status=N'RUNNING';
                INSERT INTO meta.SusepPipelineAudit(BatchId,StageName,Status,RowsAffected,Detail)
                VALUES(?,N'STAGING_LOAD',N'FAILED',NULL,?);
                """,
                elapsed_ms,
                str(error)[:2048],
                batch_id,
                batch_id,
                str(error)[:2048],
            )
            connection.commit()
        raise
    finally:
        if lock_acquired:
            try:
                set_required_session_options(cursor)
                release_session_lock(cursor, path.name)
                connection.commit()
            except pyodbc.Error:
                connection.rollback()
        cursor.close()
        connection.close()


def main() -> int:
    args = parse_arguments()
    try:
        batch_id, outcome, source_rows, accepted, rejected, elapsed_ms = load_susep(args)
    except (OSError, RuntimeError, SourceContractError, ValueError, pyodbc.Error) as error:
        print(f"[FAILED] {error}", file=sys.stderr)
        return 1
    print(
        f"[{outcome}] batch={batch_id}; source_rows={source_rows}; accepted={accepted}; "
        f"rejected={rejected}; elapsed_ms={elapsed_ms}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
