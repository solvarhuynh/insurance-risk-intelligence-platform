#!/usr/bin/env python3
"""Score the reproducible bounded held-out test set into SQL Server safely."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from time import perf_counter

import joblib
import pyodbc

from modeling import (
    MODEL_FEATURES,
    REPO_ROOT,
    assign_splits,
    connection_string,
    extract_bounded_population,
)


MODEL_VERSION = "claim_risk_model_v001"
POPULATION = "bounded_held_out_test"
THRESHOLD = 0.5

TEMP_TABLE_SQL = """
CREATE TABLE #PredictionLoad (
    SourceFile nvarchar(128) NOT NULL,
    SourceRowNumber int NOT NULL,
    SourceRecordHash char(64) NOT NULL,
    ScoringPopulation nvarchar(64) NOT NULL,
    ModelVersion nvarchar(160) NOT NULL,
    ScoreProbabilityText nvarchar(32) NOT NULL,
    ThresholdValueText nvarchar(10) NOT NULL,
    PredictedHasClaim bit NOT NULL,
    ScoringRunId uniqueidentifier NOT NULL
);
"""

TEMP_INSERT_SQL = """
INSERT INTO #PredictionLoad
    (SourceFile, SourceRowNumber, SourceRecordHash, ScoringPopulation, ModelVersion,
     ScoreProbabilityText, ThresholdValueText, PredictedHasClaim, ScoringRunId)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

MERGE_SQL = """
MERGE dwh.RiskObservationPrediction AS target
USING (
    SELECT SourceFile, SourceRowNumber, SourceRecordHash, ScoringPopulation, ModelVersion,
           CONVERT(decimal(12,10), ScoreProbabilityText) AS ScoreProbability,
           CONVERT(decimal(5,4), ThresholdValueText) AS ThresholdValue,
           PredictedHasClaim, ScoringRunId
    FROM #PredictionLoad
) AS source
ON target.SourceFile = source.SourceFile
 AND target.SourceRowNumber = source.SourceRowNumber
 AND target.ScoringPopulation = source.ScoringPopulation
 AND target.ModelVersion = source.ModelVersion
WHEN MATCHED THEN UPDATE SET
    SourceRecordHash = source.SourceRecordHash,
    ScoreProbability = source.ScoreProbability,
    ThresholdValue = source.ThresholdValue,
    PredictedHasClaim = source.PredictedHasClaim,
    ScoringRunId = source.ScoringRunId,
    ScoredAtUtc = SYSUTCDATETIME()
WHEN NOT MATCHED THEN INSERT
    (SourceFile, SourceRowNumber, SourceRecordHash, ScoringPopulation, ModelVersion,
     ScoreProbability, ThresholdValue, PredictedHasClaim, ScoringRunId)
VALUES
    (source.SourceFile, source.SourceRowNumber, source.SourceRecordHash, source.ScoringPopulation, source.ModelVersion,
     source.ScoreProbability, source.ThresholdValue, source.PredictedHasClaim, source.ScoringRunId);
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Score bounded held-out brvehins1 observations.")
    parser.add_argument("--run-id", type=uuid.UUID, default=uuid.uuid4())
    args = parser.parse_args()
    artifact_path = REPO_ROOT / "ml/artifacts" / f"{MODEL_VERSION}.joblib"
    metadata_path = REPO_ROOT / "ml/artifacts" / f"{MODEL_VERSION}.metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata["model_version"] != MODEL_VERSION:
        raise RuntimeError("Artifact metadata không khớp model version của scorer.")
    model = joblib.load(artifact_path)
    population = assign_splits(extract_bounded_population())
    test = population.loc[population["Split"] == "test"].copy()
    score_started = perf_counter()
    probabilities = model.predict_proba(test[MODEL_FEATURES])[:, 1]
    scoring_seconds = perf_counter() - score_started
    if len(probabilities) != len(test):
        raise RuntimeError("Số probability không bằng scoring population.")
    records = [
        (
            str(row.SourceFile),
            int(row.SourceRowNumber),
            str(row.SourceRecordHash),
            POPULATION,
            MODEL_VERSION,
            f"{float(probability):.10f}",
            "0.5000",
            bool(probability >= THRESHOLD),
            str(args.run_id),
        )
        for row, probability in zip(test.itertuples(index=False), probabilities, strict=True)
    ]
    with pyodbc.connect(connection_string()) as connection:
        cursor = connection.cursor()
        cursor.execute(TEMP_TABLE_SQL)
        cursor.fast_executemany = True
        cursor.executemany(TEMP_INSERT_SQL, records)
        cursor.execute(MERGE_SQL)
        connection.commit()
        stored_rows = int(
            cursor.execute(
                "SELECT COUNT_BIG(*) FROM dwh.RiskObservationPrediction WHERE ScoringPopulation=? AND ModelVersion=?",
                POPULATION,
                MODEL_VERSION,
            ).fetchval()
        )
        duplicate_rows = int(
            cursor.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT SourceFile, SourceRowNumber, COUNT(*) AS c
                    FROM dwh.RiskObservationPrediction
                    WHERE ScoringPopulation=? AND ModelVersion=?
                    GROUP BY SourceFile, SourceRowNumber HAVING COUNT(*) > 1
                ) AS duplicate_identity;
                """,
                POPULATION,
                MODEL_VERSION,
            ).fetchval()
        )
    result = {
        "run_id": str(args.run_id),
        "population": POPULATION,
        "model_version": MODEL_VERSION,
        "expected_rows": int(len(test)),
        "predicted_rows": int(len(probabilities)),
        "stored_rows": stored_rows,
        "difference_expected_to_stored": int(len(test) - stored_rows),
        "duplicate_source_identity_rows": duplicate_rows,
        "threshold": THRESHOLD,
        "scoring_seconds": round(scoring_seconds, 6),
        "scored_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if result["difference_expected_to_stored"] != 0 or duplicate_rows != 0:
        raise RuntimeError(f"Prediction reconciliation thất bại: {result}")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
