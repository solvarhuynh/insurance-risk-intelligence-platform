#!/usr/bin/env python3
"""Stream-profile the SUSEP Track-A CSV without modifying raw data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "data" / "raw" / "susep.gov.br" / "insurance_dataset.csv"
OUTPUT_DIR = REPO_ROOT / "reports" / "data"
SOURCE_COLUMNS = (
    "company_code", "company_name", "year_month", "product",
    "state", "premiums", "claims", "claim_premium_ratio",
)
TEXT_COLUMNS = ("company_name", "product", "state")
NUMERIC_COLUMNS = ("premiums", "claims")
CANDIDATE_GRAIN_COLUMNS = ("company_code", "year_month", "product", "state")
RATIO_NULL_SENTINELS = {"", "NA", "N/A", "NULL"}


@dataclass
class DecimalProfile:
    """Collect Decimal evidence while retaining only aggregate state."""

    present_count: int = 0
    null_count: int = 0
    invalid_count: int = 0
    negative_count: int = 0
    zero_count: int = 0
    minimum: Decimal | None = None
    maximum: Decimal | None = None
    integer_digits: int = 0
    scale_digits: int = 0
    total: Decimal = Decimal("0")

    def add(self, raw_value: str | None) -> None:
        value = (raw_value or "").strip()
        if not value:
            self.null_count += 1
            return
        try:
            number = Decimal(value)
        except InvalidOperation:
            self.invalid_count += 1
            return
        if not number.is_finite():
            self.invalid_count += 1
            return
        self.present_count += 1
        self.total += number
        self.minimum = number if self.minimum is None or number < self.minimum else self.minimum
        self.maximum = number if self.maximum is None or number > self.maximum else self.maximum
        self.negative_count += int(number < 0)
        self.zero_count += int(number == 0)
        parts = number.as_tuple()
        self.scale_digits = max(self.scale_digits, max(-parts.exponent, 0))
        self.integer_digits = max(
            self.integer_digits, max(len(parts.digits) + parts.exponent, 0)
        )

    def as_dict(self) -> dict[str, Any]:
        precision = min(max(self.integer_digits + self.scale_digits, 1), 38)
        return {
            "present_count": self.present_count,
            "null_count": self.null_count,
            "invalid_count": self.invalid_count,
            "negative_count": self.negative_count,
            "zero_count": self.zero_count,
            "min": decimal_text(self.minimum),
            "max": decimal_text(self.maximum),
            "sum": decimal_text(self.total),
            "max_integer_digits": self.integer_digits,
            "max_scale_digits": self.scale_digits,
            "suggested_sql_type": f"DECIMAL({precision},{self.scale_digits})",
        }


@dataclass
class TextProfile:
    """Collect bounded categorical evidence without retaining every row."""

    null_count: int = 0
    values: Counter[str] = field(default_factory=Counter)
    max_length: int = 0

    def add(self, raw_value: str | None) -> None:
        value = (raw_value or "").strip()
        if not value:
            self.null_count += 1
            return
        self.values[value] += 1
        self.max_length = max(self.max_length, len(value))

    def as_dict(self) -> dict[str, Any]:
        return {
            "null_count": self.null_count,
            "cardinality_excluding_null": len(self.values),
            "max_length": self.max_length,
            "top_values": [
                {"value": value, "count": count}
                for value, count in self.values.most_common(10)
            ],
        }


def decimal_text(value: Decimal | None) -> str | None:
    """Return a plain JSON-safe decimal string."""
    return None if value is None else format(value, "f")


def stable_hash(values: Iterable[str | None]) -> str:
    """Create a lossless audit fingerprint using JSON field boundaries."""
    payload = json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_int(raw_value: str | None) -> int | None:
    """Parse a source integer-like code."""
    value = (raw_value or "").strip()
    return int(value) if value else None


def parse_date(raw_value: str | None) -> date | None:
    """Parse ISO source date text."""
    value = (raw_value or "").strip()
    return date.fromisoformat(value) if value else None


def create_store(path: Path) -> sqlite3.Connection:
    """Create a temporary disk-backed store for duplicate/grain checks."""
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute(
        "CREATE TABLE seen (source_hash TEXT PRIMARY KEY, candidate_hash TEXT NOT NULL, occurrences INTEGER NOT NULL) WITHOUT ROWID"
    )
    connection.execute("CREATE INDEX ix_seen_candidate ON seen(candidate_hash)")
    return connection


def profile(source_path: Path, batch_size: int) -> dict[str, Any]:
    """Read all SUSEP rows in a bounded-memory streaming pass."""
    if not source_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy source: {source_path}")
    if batch_size <= 0:
        raise ValueError("batch_size phải lớn hơn 0.")

    started = time.perf_counter()
    rows = 0
    text = {column: TextProfile() for column in TEXT_COLUMNS}
    numbers = {column: DecimalProfile() for column in NUMERIC_COLUMNS}
    ratio = DecimalProfile()
    ratio_sentinels: Counter[str] = Counter()
    company_code_nulls = 0
    company_code_invalid: Counter[str] = Counter()
    company_codes: Counter[int] = Counter()
    company_names: dict[int, set[str]] = defaultdict(set)
    date_nulls = 0
    date_invalid: Counter[str] = Counter()
    month_min: date | None = None
    month_max: date | None = None
    pending: list[tuple[str, str]] = []

    with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        if header != SOURCE_COLUMNS:
            raise ValueError(f"Header không khớp. Expected={SOURCE_COLUMNS}; actual={header}")

        with tempfile.TemporaryDirectory(prefix="susep-profile-") as temporary_directory:
            connection = create_store(Path(temporary_directory) / "profile.sqlite")
            try:
                for row in reader:
                    rows += 1

                    try:
                        company_code = parse_int(row["company_code"])
                    except ValueError:
                        company_code = None
                        company_code_invalid[(row["company_code"] or "").strip()] += 1
                    if company_code is None:
                        company_code_nulls += int(not (row["company_code"] or "").strip())
                    else:
                        company_codes[company_code] += 1
                        company_name = (row["company_name"] or "").strip()
                        if company_name:
                            company_names[company_code].add(company_name)

                    try:
                        source_month = parse_date(row["year_month"])
                    except ValueError:
                        source_month = None
                        date_invalid[(row["year_month"] or "").strip()] += 1
                    if source_month is None:
                        date_nulls += int(not (row["year_month"] or "").strip())
                    else:
                        month_min = source_month if month_min is None or source_month < month_min else month_min
                        month_max = source_month if month_max is None or source_month > month_max else month_max

                    for column, field in text.items():
                        field.add(row[column])
                    for column, field in numbers.items():
                        field.add(row[column])

                    ratio_value = (row["claim_premium_ratio"] or "").strip()
                    if ratio_value.upper() in RATIO_NULL_SENTINELS:
                        ratio.null_count += 1
                        ratio_sentinels[ratio_value or "<empty>"] += 1
                    else:
                        ratio.add(ratio_value)

                    pending.append(
                        (
                            stable_hash(row[column] for column in SOURCE_COLUMNS),
                            stable_hash(row[column] for column in CANDIDATE_GRAIN_COLUMNS),
                        )
                    )
                    if len(pending) >= batch_size:
                        connection.executemany(
                            "INSERT INTO seen(source_hash,candidate_hash,occurrences) VALUES(?,?,1) ON CONFLICT(source_hash) DO UPDATE SET occurrences=occurrences+1",
                            pending,
                        )
                        pending.clear()

                if pending:
                    connection.executemany(
                        "INSERT INTO seen(source_hash,candidate_hash,occurrences) VALUES(?,?,1) ON CONFLICT(source_hash) DO UPDATE SET occurrences=occurrences+1",
                        pending,
                    )
                connection.commit()

                distinct_rows = int(connection.execute("SELECT COUNT(*) FROM seen").fetchone()[0])
                duplicate_rows = int(
                    connection.execute(
                        "SELECT COALESCE(SUM(occurrences-1),0) FROM seen"
                    ).fetchone()[0]
                )
                duplicate_groups = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM seen WHERE occurrences > 1"
                    ).fetchone()[0]
                )
                candidate_groups, candidate_excess = connection.execute(
                    "SELECT COUNT(*),COALESCE(SUM(row_count-1),0) FROM (SELECT candidate_hash,SUM(occurrences) AS row_count FROM seen GROUP BY candidate_hash HAVING SUM(occurrences)>1) AS grouped"
                ).fetchone()
            finally:
                connection.close()

    field_profiles: dict[str, dict[str, Any]] = {
        "company_code": {
            "source_dtype_observed": "integer-like text",
            "null_count": company_code_nulls,
            "invalid_count": sum(company_code_invalid.values()),
            "invalid_values": dict(company_code_invalid),
            "cardinality_excluding_null": len(company_codes),
            "suggested_sql_type": "INT",
        },
        "company_name": {
            "source_dtype_observed": "text",
            **text["company_name"].as_dict(),
            "suggested_sql_type": f"NVARCHAR({max(text['company_name'].max_length, 1)})",
        },
        "year_month": {
            "source_dtype_observed": "ISO date text",
            "null_count": date_nulls,
            "invalid_count": sum(date_invalid.values()),
            "invalid_values": dict(date_invalid),
            "min": month_min.isoformat() if month_min else None,
            "max": month_max.isoformat() if month_max else None,
            "suggested_sql_type": "DATE",
        },
        "product": {
            "source_dtype_observed": "text",
            **text["product"].as_dict(),
            "suggested_sql_type": f"NVARCHAR({max(text['product'].max_length, 1)})",
        },
        "state": {
            "source_dtype_observed": "text",
            **text["state"].as_dict(),
            "suggested_sql_type": f"NVARCHAR({max(text['state'].max_length, 1)})",
        },
        "premiums": {
            "source_dtype_observed": "decimal text",
            **numbers["premiums"].as_dict(),
        },
        "claims": {
            "source_dtype_observed": "decimal text",
            **numbers["claims"].as_dict(),
        },
        "claim_premium_ratio": {
            "source_dtype_observed": "decimal text or null sentinel",
            **ratio.as_dict(),
            "null_sentinels": dict(ratio_sentinels),
        },
    }
    name_conflicts = {
        str(code): sorted(values)
        for code, values in company_names.items()
        if len(values) > 1
    }
    candidate_unique = int(candidate_excess) == 0
    return {
        "run_metadata": {
            "source_path": source_path.relative_to(REPO_ROOT).as_posix(),
            "source_bytes": source_path.stat().st_size,
            "profiled_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "method": "csv.DictReader streaming; Decimal lexical profile; temporary SQLite duplicate/grain indexes",
            "batch_size": batch_size,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        },
        "schema": {"column_count": len(SOURCE_COLUMNS), "header": list(SOURCE_COLUMNS)},
        "row_count": rows,
        "field_profiles": field_profiles,
        "company_name_consistency": {
            "company_codes_with_multiple_names": name_conflicts,
            "conflict_count": len(name_conflicts),
        },
        "duplicate_profile": {
            "exact_duplicate_rows": duplicate_rows,
            "exact_duplicate_groups": duplicate_groups,
            "distinct_exact_rows": distinct_rows,
            "candidate_key": list(CANDIDATE_GRAIN_COLUMNS),
            "candidate_key_duplicate_groups": int(candidate_groups),
            "candidate_key_duplicate_rows": int(candidate_excess),
        },
        "grain_assessment": {
            "candidate_grain": "Một market observation theo company_code, year_month, product và state.",
            "candidate_key_is_unique": candidate_unique,
            "conclusion": (
                "Mỗi source row là một unique market observation theo company/month/product/state."
                if candidate_unique
                else "Candidate key không unique; contract phải preserve SourceRowNumber và không gọi candidate key là business key duy nhất."
            ),
            "not_supported": "Schema không có CustomerId, PolicyId, VIN, exposure hoặc claim-event identifier.",
        },
        "business_roles": {
            "company_fields": ["company_code", "company_name"],
            "time_field": "year_month",
            "product_field": "product",
            "geography_field": "state",
            "premium_measure": "premiums",
            "claim_measure": "claims",
            "ratio_measure": "claim_premium_ratio",
            "exposure_measure": None,
        },
    }


def write_artifacts(profile_data: dict[str, Any], output_dir: Path) -> None:
    """Write machine-readable and owner-readable EDA evidence."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "susep-profile.json").write_text(
        json.dumps(profile_data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fields = profile_data["field_profiles"]
    duplicate = profile_data["duplicate_profile"]
    lines = [
        "# P1-SUSEP-01 — EDA streaming của nguồn SUSEP",
        "",
        "Raw CSV chỉ được đọc tuần tự; không bị sửa. Duplicate và candidate-grain uniqueness dùng SQLite tạm ngoài repository.",
        "",
        "## Schema và quy mô",
        "",
        f"- Rows: **{profile_data['row_count']:,}**",
        f"- Columns: **{profile_data['schema']['column_count']}**",
        f"- Source bytes: **{profile_data['run_metadata']['source_bytes']:,}**",
        f"- Elapsed seconds: **{profile_data['run_metadata']['elapsed_seconds']:.3f}**",
        "",
        "## Field evidence",
        "",
        "| Field | Source type | Null | Invalid | Cardinality or range | SQL target |",
        "|---|---|---:|---:|---|---|",
    ]
    for column in SOURCE_COLUMNS:
        field = fields[column]
        descriptor = (
            f"cardinality {field['cardinality_excluding_null']:,}"
            if "cardinality_excluding_null" in field
            else f"{field.get('min')} to {field.get('max')}"
        )
        lines.append(
            f"| {column} | {field['source_dtype_observed']} | {field.get('null_count', 0):,} | "
            f"{field.get('invalid_count', 0):,} | {descriptor} | {field['suggested_sql_type']} |"
        )
    lines.extend(
        [
            "",
            "## Duplicate và grain",
            "",
            f"- Exact duplicate rows: **{duplicate['exact_duplicate_rows']:,}**.",
            f"- Candidate key: {', '.join(duplicate['candidate_key'])}.",
            f"- Candidate-key duplicate groups / excess rows: **{duplicate['candidate_key_duplicate_groups']:,} / {duplicate['candidate_key_duplicate_rows']:,}**.",
            f"- Kết luận: {profile_data['grain_assessment']['conclusion']}",
            "",
            "## Ranh giới semantic",
            "",
            "SUSEP schema có company, month, product, state, premium, claims và ratio nguồn cung cấp. Nó không có customer, policy, VIN, exposure hay claim-event identifier.",
        ]
    )
    (output_dir / "susep-eda-summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    with (output_dir / "susep-column-profile.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "field", "source_dtype_observed", "suggested_sql_type", "null_count",
                "invalid_count", "cardinality_excluding_null", "min", "max",
                "negative_count", "zero_count",
            ),
        )
        writer.writeheader()
        for column, field in fields.items():
            writer.writerow(
                {
                    "field": column,
                    "source_dtype_observed": field["source_dtype_observed"],
                    "suggested_sql_type": field["suggested_sql_type"],
                    "null_count": field.get("null_count", 0),
                    "invalid_count": field.get("invalid_count", 0),
                    "cardinality_excluding_null": field.get("cardinality_excluding_null"),
                    "min": field.get("min"),
                    "max": field.get("max"),
                    "negative_count": field.get("negative_count"),
                    "zero_count": field.get("zero_count"),
                }
            )


def parse_arguments() -> argparse.Namespace:
    """Parse explicit streaming profile options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--batch-size", type=int, default=25_000)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    """Run profiling and write reports/data evidence."""
    args = parse_arguments()
    try:
        result = profile(args.source.resolve(), args.batch_size)
        write_artifacts(result, args.output_dir)
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"[FAILED] {error}")
        return 1
    print(
        f"[SUCCESS] rows={result['row_count']}; "
        f"candidate_key_unique={result['grain_assessment']['candidate_key_is_unique']}; "
        f"elapsed_seconds={result['run_metadata']['elapsed_seconds']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

