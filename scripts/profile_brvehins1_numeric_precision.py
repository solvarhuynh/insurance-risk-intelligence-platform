"""Measure lexical numeric precision in immutable canonical brvehins1 CSV files."""

from __future__ import annotations

import argparse
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


PARTITIONS = (
    "brvehins1a.csv",
    "brvehins1b.csv",
    "brvehins1c.csv",
    "brvehins1d.csv",
    "brvehins1e.csv",
)

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


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Đo độ chính xác thập phân thực tế của brvehins1 bằng streaming CSV."
    )
    parser.add_argument("--source-directory", type=Path, default=Path("data/raw/brvehins1"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/data/brvehins1-numeric-precision.json"),
    )
    return parser.parse_args()


def integer_digits(value: Decimal) -> int:
    if value.is_zero():
        return 1
    return max(1, value.adjusted() + 1)


def main() -> int:
    args = parse_arguments()
    profiles = {
        column: {
            "rows": 0,
            "parse_errors": 0,
            "max_fractional_digits": 0,
            "max_integer_digits": 0,
            "sample_at_max_fractional_digits": None,
            "sample_at_max_integer_digits": None,
        }
        for column in DECIMAL_COLUMNS
    }
    total_rows = 0

    for partition in PARTITIONS:
        source_path = args.source_directory / partition
        with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row_number, row in enumerate(reader, start=1):
                total_rows += 1
                for column in DECIMAL_COLUMNS:
                    raw_value = row[column]
                    profile = profiles[column]
                    profile["rows"] += 1
                    try:
                        value = Decimal(raw_value)
                    except InvalidOperation:
                        profile["parse_errors"] += 1
                        continue
                    fractional_digits = max(0, -value.as_tuple().exponent)
                    whole_digits = integer_digits(value)
                    if fractional_digits > profile["max_fractional_digits"]:
                        profile["max_fractional_digits"] = fractional_digits
                        profile["sample_at_max_fractional_digits"] = {
                            "partition": partition,
                            "source_row_number": row_number,
                            "raw_value": raw_value,
                        }
                    if whole_digits > profile["max_integer_digits"]:
                        profile["max_integer_digits"] = whole_digits
                        profile["sample_at_max_integer_digits"] = {
                            "partition": partition,
                            "source_row_number": row_number,
                            "raw_value": raw_value,
                        }

    for profile in profiles.values():
        precision = profile["max_integer_digits"] + profile["max_fractional_digits"]
        profile["recommended_sql_logical_type"] = (
            f"DECIMAL({precision},{profile['max_fractional_digits']})"
        )

    result = {
        "source_directory": str(args.source_directory).replace("\\", "/"),
        "partitions": list(PARTITIONS),
        "total_rows": total_rows,
        "method": "csv.DictReader streaming + Decimal lexical precision; raw files are read only",
        "decimal_precision_profile": profiles,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Đã profile {total_rows} dòng vào {args.output}")
    for column, profile in profiles.items():
        print(f"{column}: {profile['recommended_sql_logical_type']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
