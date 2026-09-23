#!/usr/bin/env python3
"""Static validator for the canonical brvehins1 repository foundation.

The validator deliberately reads only CSV headers. It does not profile rows,
start containers, connect to SQL Server, or claim runtime success.
"""

from __future__ import annotations

import csv
import json
import os
import py_compile
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PARTITIONS = (
    "brvehins1a.csv",
    "brvehins1b.csv",
    "brvehins1c.csv",
    "brvehins1d.csv",
    "brvehins1e.csv",
)
CANONICAL_HEADER = (
    "Gender", "DrivAge", "VehYear", "VehModel", "VehGroup", "Area",
    "State", "StateAb", "ExposTotal", "ExposFireRob", "PremTotal",
    "PremFireRob", "SumInsAvg", "ClaimNbRob", "ClaimNbPartColl",
    "ClaimNbTotColl", "ClaimNbFire", "ClaimNbOther", "ClaimAmountRob",
    "ClaimAmountPartColl", "ClaimAmountTotColl", "ClaimAmountFire",
    "ClaimAmountOther",
)
REQUIRED_FILES = (
    "README.md",
    ".gitignore",
    "requirements.txt",
    "requirements-dev.txt",
    "docker-compose.yml",
    "log/progress-log.md",
    "docs/architecture/architecture-explained.md",
    "docs/architecture/data-dictionary.md",
    "docs/architecture/repository-structure.md",
    "docs/guides/how-to-run.md",
    "docs/specs/implementation-guide.md",
    "migrations/V1__create_dwh_schema.sql",
    "notebooks/01-eda.ipynb",
    "scripts/validate_repo.py",
    "data/raw/.gitkeep",
    "data/raw/susep.gov.br/insurance_dataset.csv",
    "powerbi/.gitkeep",
)
CURRENT_DOCS = (
    "README.md",
    "docs/architecture/architecture-explained.md",
    "docs/architecture/data-dictionary.md",
    "docs/architecture/repository-structure.md",
    "docs/guides/glossary.md",
    "docs/guides/how-to-run.md",
    "docs/reports/insights.md",
    "docs/specs/implementation-guide.md",
)
FORBIDDEN_CURRENT_DOC_TERMS = (
    "porto seguro",
    "safe driver",
    "prudent",
    "train.csv",
    "test.csv",
    "ps_ind_",
    "ps_reg_",
    "ps_car_",
    "ps_calc_",
)


class ValidationReporter:
    """Collect and print individual static validation results."""

    def __init__(self) -> None:
        self.results: list[dict[str, str]] = []

    def add(self, category: str, item: str, status: str, detail: str) -> None:
        self.results.append(
            {"category": category, "item": item, "status": status, "detail": detail}
        )
        print(f"[{status}] {category}: {item} — {detail}")

    def success(self) -> bool:
        passed = sum(result["status"] == "PASS" for result in self.results)
        failed = sum(result["status"] == "FAIL" for result in self.results)
        skipped = sum(result["status"] == "SKIPPED" for result in self.results)
        print(f"\nVALIDATION SUMMARY: {passed} PASSED | {failed} FAILED | {skipped} SKIPPED")
        return failed == 0


def check_required_files(reporter: ValidationReporter) -> None:
    """Confirm canonical project files are present."""
    for relative_path in REQUIRED_FILES:
        path = REPO_ROOT / relative_path
        status = "PASS" if path.is_file() else "FAIL"
        detail = "Tệp tồn tại" if status == "PASS" else "Không tìm thấy tệp"
        reporter.add("Required file", relative_path, status, detail)


def check_dependency_manifests(reporter: ValidationReporter) -> None:
    """Keep host, dev/notebook and Airflow dependency boundaries explicit."""
    host_path = REPO_ROOT / "requirements.txt"
    dev_path = REPO_ROOT / "requirements-dev.txt"
    host_lines = {
        line.strip()
        for line in host_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    dev_lines = {
        line.strip()
        for line in dev_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    expected_host = {"numpy==2.4.6", "pandas==3.0.3", "pyodbc==5.3.0"}
    expected_dev = {"-r requirements.txt", "PyYAML==6.0.3", "jupyterlab==4.6.4"}
    missing_host = expected_host - host_lines
    missing_dev = expected_dev - dev_lines
    airflow_declared = any("airflow" in line.lower() for line in host_lines | dev_lines)
    if missing_host or missing_dev or airflow_declared:
        details: list[str] = []
        if missing_host:
            details.append(f"thiếu host: {', '.join(sorted(missing_host))}")
        if missing_dev:
            details.append(f"thiếu dev: {', '.join(sorted(missing_dev))}")
        if airflow_declared:
            details.append("Airflow phải chỉ nằm trong Docker image")
        reporter.add("Python dependencies", "requirements manifests", "FAIL", "; ".join(details))
    else:
        reporter.add(
            "Python dependencies",
            "requirements manifests",
            "PASS",
            "Host/dev tách rõ; Airflow không bị cài vào host Python",
        )


def check_gitignore(reporter: ValidationReporter) -> None:
    """Confirm raw files remain ignored while the placeholder is retained."""
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    expected_rules = ("data/raw/*", "!data/raw/.gitkeep")
    missing = [rule for rule in expected_rules if rule not in gitignore]
    if missing:
        reporter.add("Git ignore", ".gitignore", "FAIL", f"Thiếu rule: {', '.join(missing)}")
    else:
        reporter.add("Git ignore", ".gitignore", "PASS", "Raw được ignore, .gitkeep được giữ lại")


def check_raw_dataset(reporter: ValidationReporter) -> None:
    """Validate exact partitions, non-empty files, readable headers and schema equality."""
    raw_dir = REPO_ROOT / "data" / "raw" / "brvehins1"
    if not raw_dir.is_dir():
        reporter.add("Raw dataset", "data/raw/brvehins1", "FAIL", "Không có thư mục nguồn chuẩn")
        return

    actual = tuple(sorted(path.name for path in raw_dir.glob("*.csv")))
    if actual != PARTITIONS:
        reporter.add("Raw dataset", "Canonical partitions", "FAIL", f"Tìm thấy: {', '.join(actual)}")
        return
    reporter.add("Raw dataset", "Canonical partitions", "PASS", "Có đúng năm partition bắt buộc")

    headers: dict[str, tuple[str, ...]] = {}
    for name in PARTITIONS:
        path = raw_dir / name
        if path.stat().st_size == 0:
            reporter.add("Raw dataset", name, "FAIL", "File rỗng")
            continue
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                header = tuple(next(csv.reader(handle)))
            if not header:
                reporter.add("Raw dataset", name, "FAIL", "Header rỗng")
                continue
            headers[name] = header
            reporter.add("Raw dataset", name, "PASS", f"Header đọc được; {len(header)} cột")
        except (OSError, StopIteration, csv.Error) as error:
            reporter.add("Raw dataset", name, "FAIL", f"Không đọc được header: {error}")

    if len(headers) != len(PARTITIONS):
        return
    header_values = tuple(headers.values())
    if len(set(header_values)) != 1:
        reporter.add("Raw dataset", "Schema equality", "FAIL", "Schema giữa các partition khác nhau")
    elif header_values[0] != CANONICAL_HEADER:
        reporter.add("Raw dataset", "Canonical header", "FAIL", "Header không khớp contract đã biết")
    else:
        reporter.add("Raw dataset", "Schema equality", "PASS", "Năm schema bằng nhau và có 23 cột chuẩn")


def check_current_docs(reporter: ValidationReporter) -> None:
    """Prevent active documentation from reverting to a superseded source design."""
    content = "\n".join((REPO_ROOT / path).read_text(encoding="utf-8").lower() for path in CURRENT_DOCS)
    missing_requirements = [term for term in ("brvehins1", "legacy / non-canonical") if term not in content]
    stale_terms = [term for term in FORBIDDEN_CURRENT_DOC_TERMS if term in content]
    unsupported_metric = re.search(r"roc\s*[- ]?auc\s*(?:>|>=)", content)
    if missing_requirements:
        reporter.add("Current docs", "Canonical source", "FAIL", f"Thiếu: {', '.join(missing_requirements)}")
    elif stale_terms:
        reporter.add("Current docs", "Canonical source", "FAIL", f"Còn thuật ngữ cũ: {', '.join(stale_terms)}")
    elif unsupported_metric:
        reporter.add("Current docs", "ML acceptance", "FAIL", "Còn ngưỡng ROC-AUC chưa có bằng chứng")
    else:
        reporter.add("Current docs", "Canonical source", "PASS", "Tài liệu hiện hành dùng brvehins1 và nêu rõ legacy non-canonical")


def check_docker_compose(reporter: ValidationReporter) -> None:
    """Parse Docker Compose without starting any runtime service."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    try:
        import yaml

        compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        services = compose.get("services", {}) if isinstance(compose, dict) else {}
        if "sqlserver" not in services:
            reporter.add("Docker compose", "docker-compose.yml", "FAIL", "Thiếu service sqlserver")
        else:
            reporter.add("Docker compose", "docker-compose.yml", "PASS", "YAML hợp lệ, có service sqlserver")
        return
    except ImportError:
        pass
    except Exception as error:
        reporter.add("Docker compose", "docker-compose.yml", "FAIL", f"YAML không hợp lệ: {error}")
        return

    try:
        result = subprocess.run(
            ["docker", "compose", "config", "-q"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        reporter.add("Docker compose", "docker-compose.yml", "SKIPPED", "Không có PyYAML hoặc Docker CLI")
        return
    if result.returncode == 0:
        reporter.add("Docker compose", "docker-compose.yml", "PASS", "docker compose config hợp lệ")
    else:
        reporter.add("Docker compose", "docker-compose.yml", "FAIL", result.stderr.strip() or "Compose không hợp lệ")


def check_python_syntax(reporter: ValidationReporter) -> None:
    """Compile maintained Python files without importing runtime dependencies."""
    for directory in ("scripts", "ml", "dags"):
        for path in sorted((REPO_ROOT / directory).rglob("*.py")):
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            try:
                py_compile.compile(str(path), doraise=True)
                reporter.add("Python syntax", relative_path, "PASS", "py_compile thành công")
            except py_compile.PyCompileError as error:
                reporter.add("Python syntax", relative_path, "FAIL", str(error))


def check_notebooks(reporter: ValidationReporter) -> None:
    """Ensure notebooks remain valid JSON artifacts."""
    for path in sorted((REPO_ROOT / "notebooks").glob("*.ipynb")):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"))
            valid = isinstance(notebook.get("cells"), list) and "metadata" in notebook
            reporter.add("Notebook", relative_path, "PASS" if valid else "FAIL", "JSON hợp lệ" if valid else "Thiếu cells hoặc metadata")
        except (OSError, json.JSONDecodeError) as error:
            reporter.add("Notebook", relative_path, "FAIL", f"JSON không hợp lệ: {error}")


def check_sql_structure(reporter: ValidationReporter) -> None:
    """Apply minimal structural checks without treating them as SQL execution."""
    for directory in ("migrations", "sql"):
        for path in sorted((REPO_ROOT / directory).glob("*.sql")):
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            content = path.read_text(encoding="utf-8")
            if not content.strip():
                reporter.add("SQL structure", relative_path, "FAIL", "File SQL rỗng")
            elif content.count("/*") != content.count("*/"):
                reporter.add("SQL structure", relative_path, "FAIL", "Block comment không cân bằng")
            else:
                reporter.add("SQL structure", relative_path, "PASS", "Không rỗng, block comment cân bằng")


def report_runtime_scope(reporter: ValidationReporter) -> None:
    """State clearly which validations this static entry point cannot certify."""
    for item in (
        "Docker container running",
        "SQL Server connectivity",
        "Database migration execution",
        "Staging ingestion and reconciliation",
        "DWH reconciliation",
        "Data Quality execution",
        "Airflow execution",
        "ML training or scoring",
    ):
        reporter.add("Runtime scope", item, "SKIPPED", "Ngoài phạm vi static validator")


def main() -> int:
    """Run all static checks and return a process exit code."""
    reporter = ValidationReporter()
    check_required_files(reporter)
    check_dependency_manifests(reporter)
    check_gitignore(reporter)
    check_raw_dataset(reporter)
    check_current_docs(reporter)
    check_docker_compose(reporter)
    check_python_syntax(reporter)
    check_notebooks(reporter)
    check_sql_structure(reporter)
    report_runtime_scope(reporter)
    return 0 if reporter.success() else 1


if __name__ == "__main__":
    raise SystemExit(main())
