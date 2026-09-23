#!/usr/bin/env python3
"""Stream and profile the canonical brvehins1 source without modifying raw CSVs.

The script reads one pandas chunk at a time. It retains numeric vectors only
for exact quantiles and uses a temporary SQLite set of complete logical rows
to count exact duplicates across all partitions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "brvehins1"
OUTPUT_DIR = REPO_ROOT / "reports" / "data"
PARTITIONS = (
    "brvehins1a.csv",
    "brvehins1b.csv",
    "brvehins1c.csv",
    "brvehins1d.csv",
    "brvehins1e.csv",
)
NUMERIC_COLUMNS = (
    "VehYear",
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
CATEGORICAL_COLUMNS = (
    "Gender",
    "DrivAge",
    "VehModel",
    "VehGroup",
    "Area",
    "State",
    "StateAb",
)
CLAIM_COUNT_COLUMNS = (
    "ClaimNbRob",
    "ClaimNbPartColl",
    "ClaimNbTotColl",
    "ClaimNbFire",
    "ClaimNbOther",
)
CLAIM_AMOUNT_COLUMNS = (
    "ClaimAmountRob",
    "ClaimAmountPartColl",
    "ClaimAmountTotColl",
    "ClaimAmountFire",
    "ClaimAmountOther",
)
QUANTILES = (0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)


def to_json_value(value: Any) -> Any:
    """Convert numpy and pandas scalar values to stable JSON-compatible values."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, np.generic):
        return value.item()
    if pd.isna(value):
        return None
    return value


@dataclass
class NumericAccumulator:
    """Accumulate numeric evidence and retain only values needed for quantiles."""

    total_seen: int = 0
    valid_count: int = 0
    missing_or_nonfinite_count: int = 0
    conversion_error_count: int = 0
    negative_count: int = 0
    zero_count: int = 0
    values: list[np.ndarray] = field(default_factory=list)

    def add_series(self, series: pd.Series) -> None:
        """Add a source series while distinguishing parse errors from missing values."""
        self.total_seen += len(series)
        original_present = series.notna()
        numeric = pd.to_numeric(series, errors="coerce")
        values = numeric.to_numpy(dtype=np.float64, na_value=np.nan)
        finite_mask = np.isfinite(values)
        self.conversion_error_count += int((original_present & numeric.isna()).sum())
        self._add_values(values, finite_mask)

    def add_values(self, values: pd.Series | np.ndarray) -> None:
        """Add a derived numeric vector that is already numeric."""
        array = np.asarray(values, dtype=np.float64)
        self.total_seen += len(array)
        self._add_values(array, np.isfinite(array))

    def _add_values(self, values: np.ndarray, finite_mask: np.ndarray) -> None:
        valid = values[finite_mask]
        self.valid_count += int(valid.size)
        self.missing_or_nonfinite_count += int(values.size - valid.size)
        if valid.size:
            self.negative_count += int((valid < 0).sum())
            self.zero_count += int((valid == 0).sum())
            self.values.append(valid)

    def as_dict(self) -> dict[str, Any]:
        """Return min, max and exact quantiles from retained numeric values."""
        if not self.values:
            return {
                "rows_seen": self.total_seen,
                "valid_count": self.valid_count,
                "missing_or_nonfinite_count": self.missing_or_nonfinite_count,
                "conversion_error_count": self.conversion_error_count,
                "negative_count": self.negative_count,
                "zero_count": self.zero_count,
                "min": None,
                "max": None,
                "mean": None,
                "quantiles": {},
            }
        all_values = np.concatenate(self.values)
        return {
            "rows_seen": self.total_seen,
            "valid_count": self.valid_count,
            "missing_or_nonfinite_count": self.missing_or_nonfinite_count,
            "conversion_error_count": self.conversion_error_count,
            "negative_count": self.negative_count,
            "zero_count": self.zero_count,
            "min": float(np.min(all_values)),
            "max": float(np.max(all_values)),
            "mean": float(np.mean(all_values)),
            "quantiles": {
                f"p{int(level * 100):02d}": float(value)
                for level, value in zip(QUANTILES, np.quantile(all_values, QUANTILES))
            },
        }


def canonical_row(row: Iterable[Any]) -> str:
    """Encode a complete logical row losslessly for exact SQLite equality checks."""
    values = [to_json_value(value) for value in row]
    return json.dumps(values, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def insert_rows_and_count_duplicates(
    connection: sqlite3.Connection,
    chunk: pd.DataFrame,
) -> int:
    """Insert logical rows into a temporary exact set and return duplicate count."""
    rows = ((canonical_row(row),) for row in chunk.itertuples(index=False, name=None))
    changes_before = connection.total_changes
    connection.executemany("INSERT OR IGNORE INTO seen_rows (row_value) VALUES (?)", rows)
    inserted = connection.total_changes - changes_before
    return len(chunk) - inserted


def initialise_duplicate_store(path: Path) -> sqlite3.Connection:
    """Create a disk-backed temporary exact set without using project storage."""
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute(
        "CREATE TABLE seen_rows (row_value TEXT PRIMARY KEY COLLATE BINARY) WITHOUT ROWID"
    )
    return connection


def profile_dataset(chunk_size: int) -> dict[str, Any]:
    """Profile all partitions using streaming pandas chunks and a temporary duplicate set."""
    started = time.perf_counter()
    files = [RAW_DIR / partition for partition in PARTITIONS]
    missing_files = [path.name for path in files if not path.is_file()]
    if missing_files:
        raise FileNotFoundError(f"Thiếu partition: {', '.join(missing_files)}")

    physical_dtypes: dict[str, set[str]] = defaultdict(set)
    missing_counts: Counter[str] = Counter()
    numeric = {column: NumericAccumulator() for column in NUMERIC_COLUMNS}
    categorical_values: dict[str, Counter[str]] = {
        column: Counter() for column in CATEGORICAL_COLUMNS
    }
    derived = {
        "TotalClaimCount": NumericAccumulator(),
        "TotalClaimAmount": NumericAccumulator(),
        "ClaimFrequency": NumericAccumulator(),
        "LossRatio": NumericAccumulator(),
    }
    has_claim = Counter()
    per_partition: list[dict[str, Any]] = []
    state_to_abbreviations: dict[str, set[str]] = defaultdict(set)
    abbreviation_to_states: dict[str, set[str]] = defaultdict(set)
    consistency = Counter()
    header: list[str] | None = None
    total_rows = 0

    with tempfile.TemporaryDirectory(prefix="brvehins1-duplicates-") as temp_dir:
        connection = initialise_duplicate_store(Path(temp_dir) / "exact_rows.sqlite")
        try:
            for path in files:
                file_rows = 0
                file_duplicates = 0
                file_header = list(pd.read_csv(path, nrows=0).columns)
                if header is None:
                    header = file_header
                elif file_header != header:
                    raise ValueError(f"Schema không khớp: {path.name}")

                for chunk in pd.read_csv(path, chunksize=chunk_size, low_memory=False):
                    file_rows += len(chunk)
                    total_rows += len(chunk)
                    file_duplicates += insert_rows_and_count_duplicates(connection, chunk)

                    for column in header:
                        physical_dtypes[column].add(str(chunk[column].dtype))
                        missing_counts[column] += int(chunk[column].isna().sum())

                    for column in NUMERIC_COLUMNS:
                        numeric[column].add_series(chunk[column])

                    for column in CATEGORICAL_COLUMNS:
                        values = chunk[column].dropna().astype(str)
                        categorical_values[column].update(values.tolist())

                    state = chunk["State"].dropna().astype(str)
                    state_abbreviation = chunk["StateAb"].dropna().astype(str)
                    valid_pairs = chunk[["State", "StateAb"]].dropna()
                    for state_name, abbreviation in valid_pairs.itertuples(index=False, name=None):
                        state_to_abbreviations[str(state_name)].add(str(abbreviation))
                        abbreviation_to_states[str(abbreviation)].add(str(state_name))
                    consistency["rows_with_state"] += len(state)
                    consistency["rows_with_state_ab"] += len(state_abbreviation)
                    consistency["rows_with_state_pair"] += len(valid_pairs)

                    count_values = pd.DataFrame(
                        {column: pd.to_numeric(chunk[column], errors="coerce") for column in CLAIM_COUNT_COLUMNS}
                    )
                    amount_values = pd.DataFrame(
                        {column: pd.to_numeric(chunk[column], errors="coerce") for column in CLAIM_AMOUNT_COLUMNS}
                    )
                    total_claim_count = count_values.sum(axis=1, min_count=len(CLAIM_COUNT_COLUMNS))
                    total_claim_amount = amount_values.sum(axis=1, min_count=len(CLAIM_AMOUNT_COLUMNS))
                    derived["TotalClaimCount"].add_values(total_claim_count.to_numpy(dtype=np.float64, na_value=np.nan))
                    derived["TotalClaimAmount"].add_values(total_claim_amount.to_numpy(dtype=np.float64, na_value=np.nan))

                    has_claim_values = total_claim_count.notna()
                    has_claim["missing"] += int((~has_claim_values).sum())
                    has_claim["yes"] += int((total_claim_count[has_claim_values] > 0).sum())
                    has_claim["no"] += int((total_claim_count[has_claim_values] == 0).sum())

                    exposure = pd.to_numeric(chunk["ExposTotal"], errors="coerce")
                    premium = pd.to_numeric(chunk["PremTotal"], errors="coerce")
                    valid_frequency = (exposure > 0) & total_claim_count.notna()
                    valid_loss_ratio = (premium > 0) & total_claim_amount.notna()
                    frequency = np.full(len(chunk), np.nan, dtype=np.float64)
                    loss_ratio = np.full(len(chunk), np.nan, dtype=np.float64)
                    frequency[valid_frequency.to_numpy()] = (
                        total_claim_count[valid_frequency] / exposure[valid_frequency]
                    ).to_numpy(dtype=np.float64)
                    loss_ratio[valid_loss_ratio.to_numpy()] = (
                        total_claim_amount[valid_loss_ratio] / premium[valid_loss_ratio]
                    ).to_numpy(dtype=np.float64)
                    derived["ClaimFrequency"].add_values(frequency)
                    derived["LossRatio"].add_values(loss_ratio)

                    consistency["zero_or_negative_exposure"] += int((exposure <= 0).fillna(False).sum())
                    consistency["zero_or_negative_premium"] += int((premium <= 0).fillna(False).sum())
                    consistency["amount_positive_count_zero"] += int(
                        ((total_claim_amount > 0) & (total_claim_count == 0)).sum()
                    )
                    consistency["count_positive_amount_zero"] += int(
                        ((total_claim_count > 0) & (total_claim_amount == 0)).sum()
                    )
                    fire_rob_exposure = pd.to_numeric(chunk["ExposFireRob"], errors="coerce")
                    fire_rob_premium = pd.to_numeric(chunk["PremFireRob"], errors="coerce")
                    consistency["fire_rob_exposure_exceeds_total"] += int(
                        ((fire_rob_exposure > exposure) & exposure.notna() & fire_rob_exposure.notna()).sum()
                    )
                    consistency["fire_rob_premium_exceeds_total"] += int(
                        ((fire_rob_premium > premium) & premium.notna() & fire_rob_premium.notna()).sum()
                    )

                per_partition.append(
                    {
                        "file": path.name,
                        "bytes": path.stat().st_size,
                        "rows": file_rows,
                        "exact_duplicates_encountered": file_duplicates,
                    }
                )
            connection.commit()
            distinct_rows = int(connection.execute("SELECT COUNT(*) FROM seen_rows").fetchone()[0])
        finally:
            connection.close()

    if header is None:
        raise ValueError("Không đọc được header")

    state_conflicts = {
        state: sorted(values) for state, values in state_to_abbreviations.items() if len(values) > 1
    }
    abbreviation_conflicts = {
        abbreviation: sorted(values)
        for abbreviation, values in abbreviation_to_states.items()
        if len(values) > 1
    }
    categorical_profile = {
        column: {
            "cardinality_excluding_null": len(counter),
            "top_values": [{"value": value, "count": count} for value, count in counter.most_common(10)],
        }
        for column, counter in categorical_values.items()
    }
    numeric_profile = {column: accumulator.as_dict() for column, accumulator in numeric.items()}
    derived_profile = {column: accumulator.as_dict() for column, accumulator in derived.items()}
    elapsed_seconds = round(time.perf_counter() - started, 3)

    return {
        "run_metadata": {
            "source_directory": str(RAW_DIR.relative_to(REPO_ROOT)).replace("\\", "/"),
            "chunk_size": chunk_size,
            "elapsed_seconds": elapsed_seconds,
            "method": (
                "pandas streaming chunks; exact duplicate equality through a temporary SQLite "
                "primary-key set of all logical source fields; exact quantiles from retained numeric vectors"
            ),
        },
        "schema": {
            "column_count": len(header),
            "columns": header,
            "physical_dtypes_by_column": {column: sorted(dtypes) for column, dtypes in physical_dtypes.items()},
            "partition_schema_compatible": True,
        },
        "partitions": per_partition,
        "total_rows": total_rows,
        "missing_counts": dict(missing_counts),
        "missing_percentages": {
            column: (missing_counts[column] / total_rows * 100 if total_rows else 0.0)
            for column in header
        },
        "numeric_profile": numeric_profile,
        "categorical_profile": categorical_profile,
        "exact_duplicate_profile": {
            "combined_exact_duplicate_rows": total_rows - distinct_rows,
            "combined_distinct_logical_rows": distinct_rows,
            "duplicate_policy_assessment": (
                "Không tự deduplicate. SourceFile + SourceRowNumber sẽ là nhận diện kỹ thuật "
                "để giữ nguyên mọi bản ghi nguồn, kể cả khi có dòng logic trùng."
            ),
        },
        "derived_metric_profile": {
            **derived_profile,
            "HasClaim": dict(has_claim),
            "formulas": {
                "TotalClaimCount": "Tổng năm cột ClaimNb*.",
                "TotalClaimAmount": "Tổng năm cột ClaimAmount*.",
                "HasClaim": "TotalClaimCount > 0 khi toàn bộ ClaimNb* có giá trị.",
                "ClaimFrequency": "TotalClaimCount / ExposTotal khi ExposTotal > 0.",
                "LossRatio": "TotalClaimAmount / PremTotal khi PremTotal > 0.",
            },
        },
        "state_abbreviation_consistency": {
            "rows_with_state_pair": consistency["rows_with_state_pair"],
            "state_to_abbreviation_conflicts": state_conflicts,
            "abbreviation_to_state_conflicts": abbreviation_conflicts,
        },
        "cross_field_observations": dict(consistency),
        "grain_assessment": {
            "assessment": (
                "Mỗi dòng là một quan sát tổng hợp về exposure, premium và claim cho một tổ hợp "
                "thuộc tính người lái, xe và địa lý; nguồn không cung cấp mã business identifier rõ ràng."
            ),
            "natural_policy_identifier": "Không quan sát thấy trong 23 cột nguồn.",
            "natural_customer_identifier": "Không quan sát thấy trong 23 cột nguồn.",
            "technical_identity": "SourceFile + SourceRowNumber; SourceRecordHash chỉ là fingerprint nội dung.",
        },
    }


def format_number(value: Any) -> str:
    """Format a value for the human-readable markdown summary."""
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:,.6f}"
    return f"{value:,}" if isinstance(value, int) else str(value)


def write_markdown(profile: dict[str, Any], target: Path) -> None:
    """Write a concise review-friendly evidence summary."""
    lines = [
        "# EDA và Source Profile — brvehins1",
        "",
        "Kết quả được tạo bằng streaming chunk; raw không bị sửa đổi.",
        "",
        "## Partition và schema",
        "",
        "| File | Bytes | Số dòng | Dòng trùng logic gặp trong lúc quét |",
        "|---|---:|---:|---:|",
    ]
    for partition in profile["partitions"]:
        lines.append(
            f"| `{partition['file']}` | {partition['bytes']:,} | {partition['rows']:,} | "
            f"{partition['exact_duplicates_encountered']:,} |"
        )
    lines.extend(
        [
            "",
            f"Tổng số dòng: **{profile['total_rows']:,}**. Số cột: **{profile['schema']['column_count']}**. "
            f"Schema tương thích: **{profile['schema']['partition_schema_compatible']}**.",
            "",
            "## Missing và duplicate",
            "",
            "| Cột | Missing | Missing % |",
            "|---|---:|---:|",
        ]
    )
    for column in profile["schema"]["columns"]:
        lines.append(
            f"| `{column}` | {profile['missing_counts'][column]:,} | "
            f"{profile['missing_percentages'][column]:.6f}% |"
        )
    duplicate = profile["exact_duplicate_profile"]
    lines.extend(
        [
            "",
            f"Exact duplicate rows toàn nguồn: **{duplicate['combined_exact_duplicate_rows']:,}**; "
            f"distinct logical rows: **{duplicate['combined_distinct_logical_rows']:,}**.",
            "",
            "## Numeric ranges và quantiles",
            "",
            "| Cột | Min | P50 | P95 | P99 | Max | Âm | Bằng 0 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for column, stats in {**profile["numeric_profile"], **profile["derived_metric_profile"]}.items():
        if not isinstance(stats, dict) or "quantiles" not in stats:
            continue
        quantiles = stats["quantiles"]
        lines.append(
            f"| `{column}` | {format_number(stats['min'])} | {format_number(quantiles.get('p50'))} | "
            f"{format_number(quantiles.get('p95'))} | {format_number(quantiles.get('p99'))} | "
            f"{format_number(stats['max'])} | {stats['negative_count']:,} | {stats['zero_count']:,} |"
        )
    lines.extend(
        [
            "",
            "## Derived metric distribution",
            "",
            f"HasClaim: có claim `{profile['derived_metric_profile']['HasClaim']['yes']:,}`, "
            f"không claim `{profile['derived_metric_profile']['HasClaim']['no']:,}`, "
            f"thiếu `{profile['derived_metric_profile']['HasClaim']['missing']:,}`.",
            "",
            "## Kiểm tra chéo",
            "",
        ]
    )
    for name, count in profile["cross_field_observations"].items():
        lines.append(f"- `{name}`: {count:,}")
    state_profile = profile["state_abbreviation_consistency"]
    lines.extend(
        [
            "",
            "## Đánh giá grain",
            "",
            profile["grain_assessment"]["assessment"],
            "",
            f"- Natural PolicyID: {profile['grain_assessment']['natural_policy_identifier']}",
            f"- Natural CustomerID: {profile['grain_assessment']['natural_customer_identifier']}",
            f"- Technical identity: {profile['grain_assessment']['technical_identity']}",
            "",
            f"Mâu thuẫn State -> StateAb: {len(state_profile['state_to_abbreviation_conflicts'])}. "
            f"Mâu thuẫn StateAb -> State: {len(state_profile['abbreviation_to_state_conflicts'])}.",
            "",
            f"Thời gian chạy profile: {profile['run_metadata']['elapsed_seconds']} giây.",
        ]
    )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_column_csv(profile: dict[str, Any], target: Path) -> None:
    """Write flat, machine-readable source and derived column statistics."""
    rows: list[dict[str, Any]] = []
    for kind, stats_by_column in (
        ("SOURCE", profile["numeric_profile"]),
        ("DERIVED", profile["derived_metric_profile"]),
    ):
        for column, stats in stats_by_column.items():
            if not isinstance(stats, dict) or "quantiles" not in stats:
                continue
            rows.append(
                {
                    "kind": kind,
                    "column": column,
                    "rows_seen": stats["rows_seen"],
                    "valid_count": stats["valid_count"],
                    "missing_or_nonfinite_count": stats["missing_or_nonfinite_count"],
                    "conversion_error_count": stats["conversion_error_count"],
                    "negative_count": stats["negative_count"],
                    "zero_count": stats["zero_count"],
                    "min": stats["min"],
                    "mean": stats["mean"],
                    "p01": stats["quantiles"].get("p01"),
                    "p05": stats["quantiles"].get("p05"),
                    "p25": stats["quantiles"].get("p25"),
                    "p50": stats["quantiles"].get("p50"),
                    "p75": stats["quantiles"].get("p75"),
                    "p95": stats["quantiles"].get("p95"),
                    "p99": stats["quantiles"].get("p99"),
                    "max": stats["max"],
                }
            )
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["kind", "column"])
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    """Parse command-line configuration for reproducible profiling."""
    parser = argparse.ArgumentParser(description="Profile canonical brvehins1 CSV partitions.")
    parser.add_argument("--chunk-size", type=int, default=100_000, help="Rows per pandas chunk.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Directory for profile artifacts.")
    return parser.parse_args()


def main() -> int:
    """Run the profile and persist JSON, CSV and markdown evidence."""
    args = parse_args()
    if args.chunk_size <= 0:
        raise ValueError("--chunk-size phải lớn hơn 0")
    profile = profile_dataset(args.chunk_size)
    output_dir = args.output_dir if args.output_dir.is_absolute() else REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "brvehins1-profile.json"
    markdown_path = output_dir / "brvehins1-eda-summary.md"
    csv_path = output_dir / "brvehins1-column-profile.csv"
    json_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(profile, markdown_path)
    write_column_csv(profile, csv_path)
    print(f"PROFILE_COMPLETE total_rows={profile['total_rows']}")
    print(f"PROFILE_JSON={json_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"PROFILE_MARKDOWN={markdown_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"PROFILE_CSV={csv_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
