"""Direct streaming reconciliation for one SUSEP source version through Track A."""

from __future__ import annotations

import argparse
import csv
import os
import sys
import uuid
from decimal import Decimal, localcontext
from pathlib import Path

import pyodbc

from load_susep_to_staging import (
    SOURCE_COLUMNS,
    odbc_braced_value,
    parse_source_row,
    source_file_sha256,
    validate_header,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Đối soát trực tiếp raw SUSEP → staging → fact.")
    parser.add_argument("--source-path", type=Path, default=Path("data/raw/susep.gov.br/insurance_dataset.csv"))
    parser.add_argument("--server", default="localhost,1433")
    parser.add_argument("--database", default="DWH_Insurance")
    parser.add_argument("--odbc-driver", default="ODBC Driver 18 for SQL Server")
    parser.add_argument("--password-env", default="SQLSERVER_SA_PASSWORD")
    return parser.parse_args()


def direct_source_totals(path: Path) -> tuple[int, Decimal, Decimal]:
    validate_header(path)
    rows = 0
    premiums = Decimal(0)
    claims = Decimal(0)
    with localcontext() as context:
        context.prec = 60
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != SOURCE_COLUMNS:
                raise ValueError("Header SUSEP thay đổi trong khi reconciliation.")
            for rows, row in enumerate(reader, start=1):
                values = parse_source_row(row, rows)
                premiums += values[6]
                claims += values[8]
    return rows, premiums, claims


def main() -> int:
    args = parse_arguments()
    path = args.source_path.resolve()
    if not path.is_file():
        print(f"[FAILED] Không tìm thấy source: {path}", file=sys.stderr)
        return 1
    password = os.environ.get(args.password_env)
    if not password:
        print(f"[FAILED] Thiếu credential environment variable: {args.password_env}", file=sys.stderr)
        return 1
    try:
        source_rows, source_premiums, source_claims = direct_source_totals(path)
        file_hash = source_file_sha256(path)
        connection = pyodbc.connect(
            f"DRIVER={{{args.odbc_driver}}};SERVER={odbc_braced_value(args.server)};DATABASE={odbc_braced_value(args.database)};"
            f"UID=sa;PWD={odbc_braced_value(password)};Encrypt=yes;TrustServerCertificate=yes;",
            autocommit=False,
        )
        cursor = connection.cursor()
        batch = cursor.execute(
            """
            SELECT TOP(1) BatchId,ExpectedSourceRows,AcceptedRows,RejectedRows
            FROM meta.SusepIngestionBatch
            WHERE SourceFile=? AND SourceFileSha256=? AND Status=N'SUCCESS'
            ORDER BY CompletedAtUtc DESC;
            """,
            path.name,
            file_hash,
        ).fetchone()
        if batch is None:
            raise RuntimeError("Không có SUCCESS ingestion batch cùng raw fingerprint để đối soát.")
        batch_id = batch[0]
        stage = cursor.execute(
            "SELECT COUNT_BIG(*),COALESCE(SUM(Premiums),0),COALESCE(SUM(Claims),0) FROM stg.SusepInsuranceMarket WHERE BatchId=?;",
            batch_id,
        ).fetchone()
        fact = cursor.execute(
            "SELECT COUNT_BIG(*),COALESCE(SUM(Premiums),0),COALESCE(SUM(Claims),0) FROM dwh.FactSusepInsuranceMarket WHERE BatchId=?;",
            batch_id,
        ).fetchone()
        status = "SUCCESS" if (
            source_rows == int(batch[1]) == int(batch[2]) + int(batch[3])
            and int(stage[0]) == int(batch[2])
            and int(fact[0]) == int(batch[2])
            and source_premiums == stage[1] == fact[1]
            and source_claims == stage[2] == fact[2]
        ) else "FAILED"
        detail = (
            f"raw_rows={source_rows}; accepted={batch[2]}; rejected={batch[3]}; "
            f"stage_rows={stage[0]}; fact_rows={fact[0]}; source_sha256={file_hash}."
        )
        cursor.execute(
            """
            INSERT INTO meta.SusepReconciliationRun(
                BatchId,SourceRows,AcceptedRows,RejectedRows,StagingRows,FactRows,
                SourcePremiumsAnalyticTotal,StagingPremiumsTotal,FactPremiumsTotal,
                SourceClaimsAnalyticTotal,StagingClaimsTotal,FactClaimsTotal,Status,Detail
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?);
            """,
            batch_id,source_rows,int(batch[2]),int(batch[3]),int(stage[0]),int(fact[0]),
            source_premiums,stage[1],fact[1],source_claims,stage[2],fact[2],status,detail,
        )
        cursor.execute(
            """
            UPDATE meta.SusepIngestionBatch
            SET SourcePremiumsAnalyticTotal=?, SourceClaimsAnalyticTotal=?
            WHERE BatchId=?;
            """,
            source_premiums,
            source_claims,
            batch_id,
        )
        cursor.execute(
            "INSERT INTO meta.SusepPipelineAudit(BatchId,StageName,Status,RowsAffected,Detail) VALUES(?,N'RECONCILIATION_RAW_TO_FACT',?,?,?);",
            batch_id,"SUCCESS" if status == "SUCCESS" else "FAILED",int(fact[0]),detail,
        )
        connection.commit()
        cursor.close()
        connection.close()
    except (OSError, ValueError, RuntimeError, pyodbc.Error) as error:
        print(f"[FAILED] {error}", file=sys.stderr)
        return 1
    print(f"[{status}] {detail}")
    return 0 if status == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
