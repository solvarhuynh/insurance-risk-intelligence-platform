"""Resource-bounded, reproducible helpers for brvehins1 ML experiments.

The ML contract is unchanged: HasClaim association on aggregate observations,
with group-isolated splits by SourceRecordHash.  This module deliberately
extracts a deterministic bounded population from the canonical DWH instead of
materialising the complete 1.9M-row feature frame on the host.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd
import pyodbc
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


REPO_ROOT = Path(__file__).resolve().parent.parent
RANDOM_SEED = 20260923
MODEL_FEATURES = [
    "Gender", "DrivAge", "VehYear", "VehModel", "VehGroup", "Area", "StateAb"
]
IDENTITY_COLUMNS = ["SourceFile", "SourceRowNumber", "SourceRecordHash"]
DATA_CONTRACT_REFERENCE = "docs/ml/ml-data-contract.md"

# 100k is intentionally below both the prior all-DWH materialisation and the
# 300k bounded attempt, which reached about 0.92 GB working set before the
# host stopped the process. Its quotas preserve live prevalence to four places.
BOUNDED_POPULATION = {
    "positive_hash_groups": 18_474,
    "negative_hash_groups": 81_526,
    "purpose": "resource-bounded reproducible model comparison and held-out batch inference demonstration",
}
PROGRESSIVE_TRAIN_CAPS = (4_000, 24_000, 60_000)

BOUNDED_EXTRACTION_SQL = """
WITH HashGroups AS (
    SELECT SourceRecordHash, CONVERT(int, HasClaim) AS HasClaim
    FROM dwh.FactRiskObservation
    GROUP BY SourceRecordHash, CONVERT(int, HasClaim)
), RankedHashGroups AS (
    SELECT
        SourceRecordHash,
        HasClaim,
        ROW_NUMBER() OVER (PARTITION BY HasClaim ORDER BY SourceRecordHash) AS HashRank
    FROM HashGroups
)
SELECT
    f.SourceFile,
    f.SourceRowNumber,
    f.SourceRecordHash,
    d.Gender,
    d.DrivAge,
    CONVERT(nvarchar(20), v.VehYear) AS VehYear,
    v.VehModel,
    v.VehGroup,
    g.Area,
    g.State,
    g.StateAb,
    CONVERT(int, f.HasClaim) AS HasClaim
FROM dwh.FactRiskObservation AS f
INNER JOIN RankedHashGroups AS selected_group
    ON selected_group.SourceRecordHash = f.SourceRecordHash
INNER JOIN dwh.DimDriverProfile AS d ON d.DriverProfileKey = f.DriverProfileKey
INNER JOIN dwh.DimVehicle AS v ON v.VehicleKey = f.VehicleKey
INNER JOIN dwh.DimGeography AS g ON g.GeographyKey = f.GeographyKey
WHERE (selected_group.HasClaim = 1 AND selected_group.HashRank <= ?)
   OR (selected_group.HasClaim = 0 AND selected_group.HashRank <= ?)
ORDER BY f.SourceRecordHash, f.SourceFile, f.SourceRowNumber;
"""


def connection_string() -> str:
    password = os.environ.get("SQLSERVER_SA_PASSWORD")
    if not password:
        raise RuntimeError("Thiếu biến môi trường SQLSERVER_SA_PASSWORD cho ML extraction.")
    server = os.environ.get("SQLSERVER_HOST", "localhost,1433")
    return (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};"
        "DATABASE=DWH_Insurance;UID=sa;PWD=" + password + ";"
        "Encrypt=no;TrustServerCertificate=yes;Connection Timeout=30;"
    )


def extract_bounded_population() -> pd.DataFrame:
    """Read a deterministic, group-complete bounded population from the DWH."""
    with pyodbc.connect(connection_string()) as connection:
        cursor = connection.cursor()
        cursor.execute(
            BOUNDED_EXTRACTION_SQL,
            BOUNDED_POPULATION["positive_hash_groups"],
            BOUNDED_POPULATION["negative_hash_groups"],
        )
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
    frame = pd.DataFrame.from_records(rows, columns=columns)
    if frame.empty:
        raise RuntimeError("Bounded DWH extraction trả về 0 dòng.")
    if frame[IDENTITY_COLUMNS].isna().any().any():
        raise RuntimeError("Bounded extraction có technical identity NULL.")
    if not set(frame["HasClaim"].unique()).issubset({0, 1}):
        raise RuntimeError("HasClaim không phải binary target.")
    # sklearn's SimpleImputer expects Python None/np.nan, not pandas.NA in an
    # object comparison. Keep values categorical while normalising missingness.
    for column in MODEL_FEATURES + ["State"]:
        frame[column] = frame[column].astype("object").where(frame[column].notna(), None)
    return frame


def assign_splits(frame: pd.DataFrame) -> pd.DataFrame:
    """Assign deterministic group-isolated 60/20/20 labels without Python sets."""
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    labels = np.full(len(frame), "train", dtype="U10")
    y = frame["HasClaim"].to_numpy(dtype=np.int8)
    groups = frame["SourceRecordHash"].to_numpy()
    folds = list(splitter.split(np.zeros(len(frame), dtype=np.int8), y, groups))
    labels[folds[0][1]] = "test"
    labels[folds[1][1]] = "validation"
    output = frame.copy()
    output["Split"] = pd.Series(labels, index=output.index, dtype="string")
    if (output.groupby("SourceRecordHash", observed=True)["Split"].nunique() > 1).any():
        raise RuntimeError("SourceRecordHash đã vượt qua ranh giới split.")
    return output


def deterministic_stratified_cap(frame: pd.DataFrame, cap: int) -> pd.DataFrame:
    """Take a deterministic, prevalence-preserving, group-complete subset."""
    if cap >= len(frame):
        return frame.copy()
    fraction = cap / len(frame)
    groups = frame[["SourceRecordHash", "HasClaim"]].drop_duplicates()
    selected_hashes = (
        groups.groupby("HasClaim", group_keys=False, observed=True)
        .sample(frac=fraction, random_state=RANDOM_SEED)
    )
    return frame.loc[frame["SourceRecordHash"].isin(selected_hashes["SourceRecordHash"])].copy()


def make_pipeline(estimator: Any) -> Pipeline:
    """Build sparse train-only preprocessing plus an estimator."""
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", dtype=np.float32)),
        ]
    )
    return Pipeline(
        steps=[
            (
                "preprocess",
                ColumnTransformer(
                    [("categorical", categorical, MODEL_FEATURES)],
                    sparse_threshold=1.0,
                ),
            ),
            ("estimator", estimator),
        ]
    )


def transformed_shape(pipeline: Pipeline, frame: pd.DataFrame) -> dict[str, int | float]:
    matrix = pipeline.named_steps["preprocess"].transform(frame[MODEL_FEATURES])
    nonzero = int(matrix.nnz) if hasattr(matrix, "nnz") else int(np.count_nonzero(matrix))
    total = int(matrix.shape[0] * matrix.shape[1])
    return {
        "rows": int(matrix.shape[0]),
        "columns": int(matrix.shape[1]),
        "nonzero_values": nonzero,
        "density": float(nonzero / total) if total else 0.0,
        "sparse": bool(hasattr(matrix, "tocsr")),
    }


def evaluate(pipeline: Pipeline, frame: pd.DataFrame, split_name: str) -> dict[str, Any]:
    start = perf_counter()
    probabilities = pipeline.predict_proba(frame[MODEL_FEATURES])[:, 1]
    inference_seconds = perf_counter() - start
    labels = (probabilities >= 0.5).astype(int)
    target = frame["HasClaim"].to_numpy(dtype=np.int8)
    return {
        "split": split_name,
        "rows": int(len(frame)),
        "positive_rows": int(target.sum()),
        "positive_rate": float(target.mean()),
        "roc_auc": float(roc_auc_score(target, probabilities)),
        "average_precision": float(average_precision_score(target, probabilities)),
        "accuracy_at_0_5": float(accuracy_score(target, labels)),
        "precision_at_0_5": float(precision_score(target, labels, zero_division=0)),
        "recall_at_0_5": float(recall_score(target, labels, zero_division=0)),
        "f1_at_0_5": float(f1_score(target, labels, zero_division=0)),
        "confusion_matrix_at_0_5": confusion_matrix(target, labels, labels=[0, 1]).tolist(),
        "inference_seconds": round(inference_seconds, 6),
        "inference_rows_per_second": round(len(frame) / inference_seconds, 2),
        "probability_min": float(probabilities.min()),
        "probability_max": float(probabilities.max()),
    }


def split_summary(frame: pd.DataFrame) -> dict[str, Any]:
    splits: dict[str, Any] = {}
    for name in ("train", "validation", "test"):
        part = frame.loc[frame["Split"] == name]
        splits[name] = {
            "rows": int(len(part)),
            "positive_rows": int(part["HasClaim"].sum()),
            "negative_rows": int((part["HasClaim"] == 0).sum()),
            "positive_rate": float(part["HasClaim"].mean()),
            "distinct_source_hashes": int(part["SourceRecordHash"].nunique()),
        }
    return {
        "population_strategy": BOUNDED_POPULATION,
        "total_rows": int(len(frame)),
        "total_source_hashes": int(frame["SourceRecordHash"].nunique()),
        "duplicate_hash_excess": int(len(frame) - frame["SourceRecordHash"].nunique()),
        "split_strategy": "StratifiedGroupKFold(5); fold 0 test, fold 1 validation, folds 2-4 train",
        "random_seed": RANDOM_SEED,
        "source_identity_crosses_split": False,
        "splits": splits,
    }


def write_json(relative_path: str, content: dict[str, Any]) -> Path:
    path = REPO_ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_state() -> dict[str, str]:
    def run(args: list[str]) -> str:
        result = subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else "unavailable"

    return {"commit": run(["git", "rev-parse", "HEAD"]), "working_tree": run(["git", "status", "--short"])}
