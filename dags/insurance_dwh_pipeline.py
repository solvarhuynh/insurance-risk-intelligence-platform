"""Airflow orchestration for independent Track A and Track B platform flows."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pyodbc
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator


PROJECT = Path("/opt/airflow/project")
RAW_SUSEP = Path("/opt/airflow/raw_data/susep.gov.br/insurance_dataset.csv")
SUSEP_LOADER = PROJECT / "scripts" / "load_susep_to_staging.py"
SUSEP_RECONCILER = PROJECT / "scripts" / "reconcile_susep_source_to_fact.py"
RISK_SCORER = PROJECT / "ml" / "predict_risk_batch.py"
RISK_POPULATION = "bounded_held_out_test"


def connect() -> pyodbc.Connection:
    password = os.environ["SQLSERVER_SA_PASSWORD"]
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};SERVER=sqlserver,1433;"
        "DATABASE=DWH_Insurance;UID=sa;PWD=" + password + ";Encrypt=no;TrustServerCertificate=yes;"
    )


def run_python(path: Path, *arguments: str) -> None:
    result = subprocess.run(
        [sys.executable, str(path), *arguments], cwd=str(PROJECT), check=False, text=True, capture_output=True
    )
    if result.returncode:
        raise RuntimeError(
            f"Python task failed ({path.name}, exit={result.returncode}): "
            f"stdout={result.stdout[-2000:]}; stderr={result.stderr[-2000:]}"
        )
    print(result.stdout)


def track_a_ingest(**_) -> None:
    """Idempotent source-version load; current canonical file becomes SKIPPED on rerun."""
    run_python(SUSEP_LOADER, "--source-path", str(RAW_SUSEP), "--server", "sqlserver,1433")


def track_a_load_dwh(**_) -> None:
    with connect() as connection:
        cursor = connection.cursor()
        cursor.execute("EXEC dwh.sp_LoadSusepDimensions;")
        cursor.execute("EXEC dwh.sp_LoadFactSusepInsuranceMarket;")
        connection.commit()


def track_a_reconcile(**_) -> None:
    """Direct full-file reconciliation is intentionally a real, not synthetic, control."""
    run_python(SUSEP_RECONCILER, "--source-path", str(RAW_SUSEP), "--server", "sqlserver,1433")


def track_a_quality_gate(**context) -> None:
    inject = bool((context["dag_run"].conf or {}).get("controlled_track_a_dq_failure", False))
    with connect() as connection:
        # SQL Server can return the procedure's result set before it exposes a
        # terminal THROW to pyodbc.  Consume every result set so an executable
        # DQ failure becomes an Airflow task failure instead of a false success.
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute("EXEC dq.sp_RunSusepQualityGate @RunLabel=?, @InjectControlledFailure=?;", "airflow", int(inject))
        while cursor.nextset():
            pass


def track_b_foundation_precheck(**_) -> None:
    with connect() as connection:
        row = connection.execute("SELECT (SELECT COUNT_BIG(*) FROM stg.BrVehIns1), (SELECT COUNT_BIG(*) FROM dwh.FactRiskObservation)").fetchone()
    if row[0] != row[1] or row[0] == 0:
        raise RuntimeError(f"Track B foundation reconciliation failed: staging={row[0]}, fact={row[1]}")
    print(f"Track B foundation PASS: staging={row[0]}, fact={row[1]}")


def track_b_incremental_audit(**_) -> None:
    with connect() as connection:
        rows = connection.execute("SELECT COUNT(*) FROM meta.IngestionBatch WHERE Status=N'SUCCESS'").fetchone()[0]
    if rows < 5:
        raise RuntimeError(f"Expected five successful canonical Track-B batches, found {rows}")
    print(f"Track B incremental audit PASS: successful batches={rows}")


def track_b_quality_gate(**context) -> None:
    inject = bool((context["dag_run"].conf or {}).get("controlled_track_b_dq_failure", False))
    with connect() as connection:
        # See Track A: drain procedure result sets so SQL THROW propagates to
        # Airflow and blocks the dependent scoring task.
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute("EXEC dq.sp_RunQualityGate @RunLabel=?, @InjectControlledFailure=?;", "airflow", int(inject))
        while cursor.nextset():
            pass


def track_b_batch_score(**context) -> None:
    run_python(RISK_SCORER, "--run-id", str(context["run_id"]))


def track_b_validate_predictions(**_) -> None:
    with connect() as connection:
        row = connection.execute(
            "SELECT COUNT_BIG(*),COUNT(DISTINCT SourceFile+N':'+CONVERT(nvarchar(20),SourceRowNumber)) FROM dwh.RiskObservationPrediction WHERE ScoringPopulation=?;",
            RISK_POPULATION,
        ).fetchone()
    if row[0] != row[1] or row[0] == 0:
        raise RuntimeError(f"Track B prediction reconciliation failed: rows={row[0]}, distinct_identity={row[1]}")
    print(f"Track B prediction reconciliation PASS: rows={row[0]}")


with DAG(
    dag_id="insurance_data_platform",
    description="Independent SUSEP market and brvehins1 risk/ML flows; no cross-track data join",
    start_date=datetime(2026, 1, 1), schedule=None, catchup=False,
    default_args={"owner": "data_engineering_team", "retries": 1, "retry_delay": timedelta(minutes=1)},
    tags=["insurance-platform", "track-a-susep", "track-b-brvehins1", "dq", "ml"],
) as dag:
    start = EmptyOperator(task_id="platform_start")
    end_a = EmptyOperator(task_id="track_a_market_consumer_ready")
    end_b = EmptyOperator(task_id="track_b_risk_consumer_ready")

    a_ingest = PythonOperator(task_id="track_a_ingest_susep", python_callable=track_a_ingest)
    a_dwh = PythonOperator(task_id="track_a_load_market_dwh", python_callable=track_a_load_dwh)
    a_reconcile = PythonOperator(task_id="track_a_reconcile_raw_to_fact", python_callable=track_a_reconcile)
    a_dq = PythonOperator(task_id="track_a_data_quality_gate", python_callable=track_a_quality_gate)

    b_precheck = PythonOperator(task_id="track_b_foundation_precheck", python_callable=track_b_foundation_precheck)
    b_incremental = PythonOperator(task_id="track_b_incremental_audit", python_callable=track_b_incremental_audit)
    b_dq = PythonOperator(task_id="track_b_data_quality_gate", python_callable=track_b_quality_gate)
    b_score = PythonOperator(task_id="track_b_batch_score_held_out", python_callable=track_b_batch_score)
    b_validate = PythonOperator(task_id="track_b_validate_prediction_reconciliation", python_callable=track_b_validate_predictions)

    start >> a_ingest >> a_dwh >> a_reconcile >> a_dq >> end_a
    start >> b_precheck >> b_incremental >> b_dq >> b_score >> b_validate >> end_b
