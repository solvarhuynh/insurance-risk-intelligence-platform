"""Validate the maintained layout without requiring private raw files or SQL."""
from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from pathlib import Path

from config import ROOT


def validate(raw: bool = False) -> None:
    required = ["README.md", "GUIDE.md", "CHANGELOG.md", "AGENTS.md", ".env.example", "docker-compose.yml",
                "dashboard/app.py", "dashboard/assets/style.css", "pipeline/manage.py", "data/dashboard.json", "data/evidence.json"]
    for name in required:
        if not (ROOT / name).is_file():
            raise ValueError(f"Missing: {name}")
    for directory in ("dashboard", "pipeline", "tests"):
        for path in (ROOT / directory).rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    versions = sorted(int(p.name.split("__")[0][1:]) for p in (ROOT / "database/migrations").glob("V*__*.sql"))
    if versions != list(range(1, 15)):
        raise ValueError(f"Migration sequence: {versions}")
    for document in ("README.md", "GUIDE.md", "CHANGELOG.md", "AGENTS.md"):
        content = (ROOT / document).read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if "://" not in target and not target.startswith("#"):
                path = target.split("#")[0]
                if path and not (ROOT / path).exists():
                    raise ValueError(f"Broken local link in {document}: {target}")
    data = json.loads((ROOT / "data/dashboard.json").read_text(encoding="utf-8"))
    if data["schema_version"] != 1:
        raise ValueError("Snapshot version")
    for section, names in {"market": ["monthly", "companies", "products"], "risk": ["segments", "scores"]}.items():
        for name in names:
            spec = data[section][name]
            if not spec["rows"] or any(len(row) != len(spec["columns"]) for row in spec["rows"]):
                raise ValueError(f"Invalid snapshot table: {section}.{name}")
    if raw:
        from load_susep_to_staging import SOURCE_COLUMNS as MARKET_COLUMNS
        from load_brvehins1_to_staging import SOURCE_COLUMNS as RISK_COLUMNS
        files = [(ROOT / "data/raw/susep.gov.br/insurance_dataset.csv", MARKET_COLUMNS)]
        files += [(ROOT / f"data/raw/brvehins1/brvehins1{s}.csv", RISK_COLUMNS) for s in "abcde"]
        for path, expected in files:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                if tuple(next(csv.reader(handle))) != expected:
                    raise ValueError(f"Raw schema mismatch: {path.name}")
    print("PASS: layout, Python syntax, 14 migrations, documentation links and snapshot contract.")
    print("Raw headers checked." if raw else "Raw/SQL/Airflow/browser runtime not checked by this command.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", action="store_true", help="Also validate locally supplied raw headers")
    validate(parser.parse_args().raw)
