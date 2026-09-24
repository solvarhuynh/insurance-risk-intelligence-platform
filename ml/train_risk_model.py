#!/usr/bin/env python3
"""Train a bounded, reproducible HasClaim association model from the DWH."""

from __future__ import annotations

import platform
import tracemalloc
from time import perf_counter

import joblib
import numpy as np
import pandas as pd
import pyodbc
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.naive_bayes import ComplementNB

from modeling import (
    DATA_CONTRACT_REFERENCE,
    MODEL_FEATURES,
    PROGRESSIVE_TRAIN_CAPS,
    RANDOM_SEED,
    REPO_ROOT,
    assign_splits,
    deterministic_stratified_cap,
    evaluate,
    extract_bounded_population,
    git_state,
    make_pipeline,
    split_summary,
    transformed_shape,
    utc_now,
    write_json,
)


MODEL_VERSION = "claim_risk_model_v001"
THRESHOLD = 0.5


def sgd_logistic() -> SGDClassifier:
    """Single-process stochastic logistic-loss baseline for sparse categorical data."""
    return SGDClassifier(
        loss="log_loss",
        alpha=0.0001,
        max_iter=40,
        tol=1e-3,
        random_state=RANDOM_SEED,
        early_stopping=False,
        average=True,
    )


def train_and_measure(name: str, estimator, train: pd.DataFrame, validation: pd.DataFrame) -> tuple:
    pipeline = make_pipeline(estimator)
    started = perf_counter()
    pipeline.fit(train[MODEL_FEATURES], train["HasClaim"])
    training_seconds = perf_counter() - started
    metrics = evaluate(pipeline, validation, "validation")
    metrics.update(
        {
            "model": name,
            "training_rows": int(len(train)),
            "training_positive_rate": float(train["HasClaim"].mean()),
            "training_seconds": round(training_seconds, 6),
            "transformed_training_shape": transformed_shape(pipeline, train),
        }
    )
    return pipeline, metrics


def main() -> None:
    tracemalloc.start()
    overall_start = perf_counter()
    extraction_start = perf_counter()
    population = assign_splits(extract_bounded_population())
    extraction_seconds = perf_counter() - extraction_start
    summary = split_summary(population)
    train = population.loc[population["Split"] == "train"].copy()
    validation = population.loc[population["Split"] == "validation"].copy()
    test = population.loc[population["Split"] == "test"].copy()

    progressive: list[dict] = []
    for cap in PROGRESSIVE_TRAIN_CAPS:
        bounded_train = deterministic_stratified_cap(train, cap)
        _, metrics = train_and_measure("sgd_logistic_baseline", sgd_logistic(), bounded_train, validation)
        metrics["progressive_cap_requested"] = cap
        progressive.append(metrics)
    write_json(
        "reports/data/p1-ml-resource-scaling.json",
        {
            "timestamp_utc": utc_now(),
            "extraction_and_split_seconds": round(extraction_seconds, 6),
            "progressive_baseline": progressive,
            "resource_note": "tracemalloc measures Python allocations, not total native/OS memory.",
        },
    )

    final_train_for_selection = deterministic_stratified_cap(train, PROGRESSIVE_TRAIN_CAPS[-1])
    dummy, dummy_metrics = train_and_measure(
        "majority_dummy", DummyClassifier(strategy="most_frequent", random_state=RANDOM_SEED), final_train_for_selection, validation
    )
    baseline, baseline_metrics = train_and_measure(
        "sgd_logistic_baseline", sgd_logistic(), final_train_for_selection, validation
    )
    alternative, alternative_metrics = train_and_measure(
        "complement_nb", ComplementNB(alpha=1.0), final_train_for_selection, validation
    )
    write_json(
        "reports/data/p1-ml-baseline-metrics.json",
        {"majority_dummy": dummy_metrics, "sgd_logistic_baseline": baseline_metrics},
    )
    comparison = {
        "majority_dummy": dummy_metrics,
        "sgd_logistic_baseline": baseline_metrics,
        "complement_nb": alternative_metrics,
        "resource_rejected": [
            {
                "model": "LogisticRegression(solver=saga)",
                "reason": "Prior all-DWH execution materialised a ~1.97M-row categorical frame and exceeded the acceptable local resource/runtime budget before training completed.",
            }
        ],
    }
    selected_name, selected_metrics = max(
        [("sgd_logistic_baseline", baseline_metrics), ("complement_nb", alternative_metrics)],
        key=lambda item: (item[1]["average_precision"], item[1]["roc_auc"], item[0] == "sgd_logistic_baseline"),
    )
    comparison["selection"] = {
        "selected_model": selected_name,
        "criteria": "validation Average Precision, then validation ROC-AUC, then linear logistic-loss interpretability",
    }
    write_json("reports/data/p1-ml-model-comparison.json", comparison)

    # Final fit uses a deterministic group-complete cap from train+validation.
    train_validation = pd.concat([train, validation], ignore_index=True)
    final_train = deterministic_stratified_cap(train_validation, PROGRESSIVE_TRAIN_CAPS[-1])
    final_estimator = sgd_logistic() if selected_name == "sgd_logistic_baseline" else ComplementNB(alpha=1.0)
    final_pipeline = make_pipeline(final_estimator)
    final_started = perf_counter()
    final_pipeline.fit(final_train[MODEL_FEATURES], final_train["HasClaim"])
    final_training_seconds = perf_counter() - final_started
    test_metrics = evaluate(final_pipeline, test, "held_out_test")

    artifact_path = REPO_ROOT / "ml/artifacts" / f"{MODEL_VERSION}.joblib"
    metadata_path = REPO_ROOT / "ml/artifacts" / f"{MODEL_VERSION}.metadata.json"
    joblib.dump(final_pipeline, artifact_path)
    reloaded = joblib.load(artifact_path)
    reload_sample = test.sort_values(["SourceRecordHash", "SourceFile", "SourceRowNumber"]).head(100)
    original = final_pipeline.predict_proba(reload_sample[MODEL_FEATURES])[:, 1]
    reloaded_probabilities = reloaded.predict_proba(reload_sample[MODEL_FEATURES])[:, 1]
    if not np.array_equal(original, reloaded_probabilities):
        raise RuntimeError("Artifact reload cho probability khác artifact trong bộ nhớ.")

    _, python_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    metadata = {
        "model_version": MODEL_VERSION,
        "model_class": type(final_estimator).__name__,
        "selection_name": selected_name,
        "target_definition": "HasClaim = 1 iff TotalClaimCount > 0",
        "business_framing": "Cross-sectional HasClaim association for aggregate risk observations; not future customer or policy claim prediction.",
        "feature_list": MODEL_FEATURES,
        "excluded_leakage_fields": ["ClaimNb*", "ClaimAmount*", "TotalClaimCount", "TotalClaimAmount", "HasClaim", "ClaimFrequency", "LossRatio"],
        "decision_threshold": THRESHOLD,
        "random_seed": RANDOM_SEED,
        "data_contract": DATA_CONTRACT_REFERENCE,
        "population_and_splits": summary,
        "selection_training_rows": int(len(final_train_for_selection)),
        "final_training_rows": int(len(final_train)),
        "validation_rows": int(len(validation)),
        "test_rows": int(len(test)),
        "validation_metrics": selected_metrics,
        "held_out_test_metrics": test_metrics,
        "final_training_seconds": round(final_training_seconds, 6),
        "total_script_seconds": round(perf_counter() - overall_start, 6),
        "python_tracemalloc_peak_bytes": int(python_peak_bytes),
        "resource_strategy": "Deterministic 100k-hash-group bounded population after a 300k attempt reached about 0.92 GB working set; sparse one-hot float32; single-process SGD/ComplementNB; progressive caps 4k, 24k, 60k; no CV/grid search/dense matrix.",
        "known_limitations": "Deterministic 100,004-row local resource-bounded population, not all 1,965,355 observations. Cross-sectional association only; no future predictive validity or production threshold claim.",
        "dependencies": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scikit_learn": sklearn.__version__, "joblib": joblib.__version__, "pyodbc": pyodbc.version},
        "training_timestamp_utc": utc_now(),
        "git": git_state(),
        "artifact_reload_test": {"rows_scored": int(len(reload_sample)), "probabilities_identical": True, "probability_min": float(reloaded_probabilities.min()), "probability_max": float(reloaded_probabilities.max())},
    }
    metadata_path.write_text(__import__("json").dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_json("reports/data/p1-ml-bounded-dataset-summary.json", summary)
    write_json("reports/data/p1-ml-final-model.json", metadata)
    print(
        f"Selected={selected_name}; artifact={artifact_path.name}; "
        f"test_AP={test_metrics['average_precision']:.6f}; test_ROC_AUC={test_metrics['roc_auc']:.6f}; "
        f"test_rows={len(test)}"
    )


if __name__ == "__main__":
    main()
