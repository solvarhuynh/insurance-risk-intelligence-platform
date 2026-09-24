#!/usr/bin/env python3
"""Static validator for the multi-track Insurance Data Platform.

The validator reads only raw-file metadata and CSV headers. It does not profile
rows, start containers, connect to SQL Server, or certify runtime success.
"""

from __future__ import annotations

import csv
import json
import py_compile
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BRVEHINS1_PARTITIONS = (
    "brvehins1a.csv",
    "brvehins1b.csv",
    "brvehins1c.csv",
    "brvehins1d.csv",
    "brvehins1e.csv",
)
BRVEHINS1_HEADER = (
    "Gender", "DrivAge", "VehYear", "VehModel", "VehGroup", "Area",
    "State", "StateAb", "ExposTotal", "ExposFireRob", "PremTotal",
    "PremFireRob", "SumInsAvg", "ClaimNbRob", "ClaimNbPartColl",
    "ClaimNbTotColl", "ClaimNbFire", "ClaimNbOther", "ClaimAmountRob",
    "ClaimAmountPartColl", "ClaimAmountTotColl", "ClaimAmountFire",
    "ClaimAmountOther",
)
SUSEP_HEADER = (
    "company_code",
    "company_name",
    "year_month",
    "product",
    "state",
    "premiums",
    "claims",
    "claim_premium_ratio",
)
REQUIRED_FILES = (
    "README.md",
    "REPO_LEARNING_GUIDE.md",
    "FINAL_PROJECT_GUIDE.md",
    ".gitignore",
    "requirements.txt",
    "requirements-dev.txt",
    "docker-compose.yml",
    "log/progress-log.md",
    "docs/architecture/architecture-explained.md",
    "docs/architecture/project-scope.md",
    "docs/architecture/source-strategy.md",
    "docs/architecture/overall-architecture.md",
    "docs/architecture/data-dictionary.md",
    "docs/architecture/repository-structure.md",
    "docs/architecture/source-data-contract.md",
    "docs/guides/how-to-run.md",
    "docs/specs/implementation-guide.md",
    "docs/specs/roadmap.md",
    "docs/ml/ml-data-contract.md",
    "docs/susep/source-data-contract.md",
    "docs/susep/data-dictionary.md",
    "docs/susep/dwh-design.md",
    "docs/susep/data-quality.md",
    "docs/susep/how-to-run-track-a.md",
    "docs/bi/semantic-model.md",
    "reports/performance-report.md",
    "reports/final-project-report.md",
    "reports/checkpoints/P1-ORCH-01.md",
    "reports/checkpoints/P1-ORCH-02.md",
    "reports/checkpoints/P1-E2E-01.md",
    "reports/checkpoints/P1-E2E-02.md",
    "migrations/V1__create_dwh_schema.sql",
    "migrations/V11__create_susep_staging.sql",
    "migrations/V12__create_susep_market_dwh.sql",
    "migrations/V13__create_susep_quality_gate.sql",
    "migrations/V14__add_susep_performance_indexes.sql",
    "scripts/load_susep_to_staging.py",
    "scripts/reconcile_susep_source_to_fact.py",
    "notebooks/01-eda.ipynb",
    "scripts/validate_repo.py",
    "data/raw/.gitkeep",
    "data/raw/susep.gov.br/insurance_dataset.csv",
    "powerbi/.gitkeep",
    "powerbi/README.md",
    "ml/artifacts/claim_risk_model_v001.joblib",
    "ml/artifacts/claim_risk_model_v001.metadata.json",
)
CURRENT_DOCS = (
    "README.md",
    "REPO_LEARNING_GUIDE.md",
    "docs/architecture/architecture-explained.md",
    "docs/architecture/project-scope.md",
    "docs/architecture/source-strategy.md",
    "docs/architecture/overall-architecture.md",
    "docs/architecture/data-dictionary.md",
    "docs/architecture/repository-structure.md",
    "docs/architecture/source-data-contract.md",
    "docs/guides/glossary.md",
    "docs/guides/how-to-run.md",
    "docs/specs/implementation-guide.md",
    "docs/specs/roadmap.md",
    "docs/ml/ml-data-contract.md",
    "docs/susep/source-data-contract.md",
    "docs/susep/data-dictionary.md",
    "docs/susep/dwh-design.md",
    "docs/susep/data-quality.md",
    "docs/bi/semantic-model.md",
    "powerbi/README.md",
    "FINAL_PROJECT_GUIDE.md",
)
FORBIDDEN_CURRENT_DOC_TERMS = (
    "nguồn duy nhất của pipeline là brvehins1",
    "brvehins1 = canonical dataset",
    "susep là legacy",
    "legacy / non-canonical",
    "motor insurance data warehouse",
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
        print()
        print(f"VALIDATION SUMMARY: {passed} PASSED | {failed} FAILED | {skipped} SKIPPED")
        return failed == 0


def check_required_files(reporter: ValidationReporter) -> None:
    """Confirm current source-of-truth files are present."""
    for relative_path in REQUIRED_FILES:
        path = REPO_ROOT / relative_path
        status = "PASS" if path.is_file() else "FAIL"
        detail = "Tệp tồn tại" if status == "PASS" else "Không tìm thấy tệp"
        reporter.add("Required file", relative_path, status, detail)


def check_dependency_manifests(reporter: ValidationReporter) -> None:
    """Keep host, development and Airflow dependency boundaries explicit."""
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
    expected_host = {
        "numpy==2.4.6",
        "pandas==3.0.3",
        "pyodbc==5.3.0",
        "scikit-learn==1.7.2",
        "joblib==1.5.2",
    }
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
        return
    reporter.add(
        "Python dependencies",
        "requirements manifests",
        "PASS",
        "Host/dev tách rõ; ML Track B khai báo dependency; Airflow không ở host",
    )


def check_gitignore(reporter: ValidationReporter) -> None:
    """Confirm raw files remain ignored while the placeholder is retained."""
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    expected_rules = ("data/raw/*", "!data/raw/.gitkeep")
    missing = [rule for rule in expected_rules if rule not in gitignore]
    if missing:
        reporter.add("Git ignore", ".gitignore", "FAIL", f"Thiếu rule: {', '.join(missing)}")
        return
    reporter.add("Git ignore", ".gitignore", "PASS", "Raw được ignore, .gitkeep được giữ lại")


def read_header(path: Path) -> tuple[str, ...]:
    """Read only a UTF-8 CSV header."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(next(csv.reader(handle)))


def check_susep_raw_dataset(reporter: ValidationReporter) -> None:
    """Validate Track A source presence and its header without reading data rows."""
    path = REPO_ROOT / "data" / "raw" / "susep.gov.br" / "insurance_dataset.csv"
    if not path.is_file():
        reporter.add("Track A raw dataset", str(path.relative_to(REPO_ROOT)), "FAIL", "Không tìm thấy SUSEP CSV")
        return
    if path.stat().st_size == 0:
        reporter.add("Track A raw dataset", path.name, "FAIL", "File rỗng")
        return
    try:
        header = read_header(path)
    except (OSError, StopIteration, csv.Error) as error:
        reporter.add("Track A raw dataset", path.name, "FAIL", f"Không đọc được header: {error}")
        return
    if header != SUSEP_HEADER:
        reporter.add(
            "Track A raw dataset",
            path.name,
            "FAIL",
            f"Header không khớp contract discovery: {', '.join(header)}",
        )
        return
    reporter.add(
        "Track A raw dataset",
        path.name,
        "PASS",
        "Non-empty; header SUSEP 8 cột đọc được. Static check không thay thế P1-SUSEP runtime evidence.",
    )


def check_brvehins1_raw_dataset(reporter: ValidationReporter) -> None:
    """Validate Track B partitions and their schema without reading data rows."""
    raw_dir = REPO_ROOT / "data" / "raw" / "brvehins1"
    if not raw_dir.is_dir():
        reporter.add("Track B raw dataset", "data/raw/brvehins1", "FAIL", "Không có thư mục nguồn")
        return

    actual = tuple(sorted(path.name for path in raw_dir.glob("*.csv")))
    if actual != BRVEHINS1_PARTITIONS:
        reporter.add("Track B raw dataset", "Canonical partitions", "FAIL", f"Tìm thấy: {', '.join(actual)}")
        return
    reporter.add("Track B raw dataset", "Canonical partitions", "PASS", "Có đúng năm partition bắt buộc")

    headers: dict[str, tuple[str, ...]] = {}
    for name in BRVEHINS1_PARTITIONS:
        path = raw_dir / name
        if path.stat().st_size == 0:
            reporter.add("Track B raw dataset", name, "FAIL", "File rỗng")
            continue
        try:
            header = read_header(path)
        except (OSError, StopIteration, csv.Error) as error:
            reporter.add("Track B raw dataset", name, "FAIL", f"Không đọc được header: {error}")
            continue
        if not header:
            reporter.add("Track B raw dataset", name, "FAIL", "Header rỗng")
            continue
        headers[name] = header
        reporter.add("Track B raw dataset", name, "PASS", f"Header đọc được; {len(header)} cột")

    if len(headers) != len(BRVEHINS1_PARTITIONS):
        return
    header_values = tuple(headers.values())
    if len(set(header_values)) != 1:
        reporter.add("Track B raw dataset", "Schema equality", "FAIL", "Schema giữa các partition khác nhau")
    elif header_values[0] != BRVEHINS1_HEADER:
        reporter.add("Track B raw dataset", "Canonical header", "FAIL", "Header không khớp Track B contract")
    else:
        reporter.add("Track B raw dataset", "Schema equality", "PASS", "Năm schema bằng nhau và có 23 cột chuẩn")


def check_current_docs(reporter: ValidationReporter) -> None:
    """Reject active one-source wording while preserving historical reports."""
    content = chr(10).join(
        (REPO_ROOT / path).read_text(encoding="utf-8").lower() for path in CURRENT_DOCS
    )
    required_terms = (
        "insurance data platform",
        "track a",
        "track b",
        "susep",
        "brvehins1",
        "active_canonical",
    )
    missing = [term for term in required_terms if term not in content]
    forbidden = [term for term in FORBIDDEN_CURRENT_DOC_TERMS if term in content]
    if missing:
        reporter.add("Current docs", "Multi-track source strategy", "FAIL", f"Thiếu: {', '.join(missing)}")
    elif forbidden:
        reporter.add("Current docs", "Multi-track source strategy", "FAIL", f"Còn wording drift: {', '.join(forbidden)}")
    else:
        reporter.add(
            "Current docs",
            "Multi-track source strategy",
            "PASS",
            "SUSEP Track A và brvehins1 Track B được phân biệt; không có wording one-source",
        )


def check_docker_compose(reporter: ValidationReporter) -> None:
    """Parse Docker Compose without starting a runtime service."""
    compose_path = REPO_ROOT / "docker-compose.yml"
    try:
        import yaml

        compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        services = compose.get("services", {}) if isinstance(compose, dict) else {}
        missing = {"sqlserver", "airflow"} - set(services)
        if missing:
            reporter.add("Docker compose", "docker-compose.yml", "FAIL", f"Thiếu service: {', '.join(sorted(missing))}")
        else:
            reporter.add("Docker compose", "docker-compose.yml", "PASS", "YAML hợp lệ, có SQL Server và Airflow profile")
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
    """Apply minimal structure checks without treating them as SQL execution."""
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
    """State clearly what this static entry point cannot certify."""
    for item in (
        "Docker container running",
        "SQL Server connectivity",
        "Track A SUSEP profiling, ingestion, DWH and DQ",
        "Track B staging and DWH reconciliation",
        "Track B Data Quality execution",
        "Track B ML training or scoring",
        "Airflow execution",
        "Performance benchmark",
        "Power BI refresh",
    ):
        reporter.add("Runtime scope", item, "SKIPPED", "Ngoài phạm vi static validator")


def main() -> int:
    """Run static checks and return a process exit code."""
    reporter = ValidationReporter()
    check_required_files(reporter)
    check_dependency_manifests(reporter)
    check_gitignore(reporter)
    check_susep_raw_dataset(reporter)
    check_brvehins1_raw_dataset(reporter)
    check_current_docs(reporter)
    check_docker_compose(reporter)
    check_python_syntax(reporter)
    check_notebooks(reporter)
    check_sql_structure(reporter)
    report_runtime_scope(reporter)
    return 0 if reporter.success() else 1


if __name__ == "__main__":
    raise SystemExit(main())
