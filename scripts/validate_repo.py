#!/usr/bin/env python3
"""
scripts/validate_repo.py
Project: Insurance DWH, Performance Tuning & Machine Learning
Muc dich: Entry-point kiem tra tinh (Static Baseline Validation) cho repository.
Pham vi kiem tra:
  1. Su ton tai cua cac tep bat buoc (Canonical Required Files)
  2. Parse tinh tep cau hinh Docker Compose (PyYAML hoac docker compose config)
  3. Bien dich cu phap Python (AST py_compile) tren dags/, ml/, scripts/
  4. Parse tinh Notebooks JSON tren notebooks/
  5. Kiem tra cau truc SQL (kich thuoc khong rong, can bang block comment /* */)
  6. Kiem tra trung lap ten file canonical co ban
  7. Báo cáo minh bach danh muc kiem tra Runtime duoc SKIPPED (PENDING_RUNTIME)

Luu y quan trong:
  Script nay chi thuc hien STATIC VALIDATION.
  Khong ket noi database, khong chay container va khong xac nhan RUNTIME_PASS.
"""

import csv
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path

# Thư mục gốc repository
REPO_ROOT = Path(__file__).resolve().parent.parent

# Danh sách file canonical bắt buộc phải tồn tại
REQUIRED_CANONICAL_FILES = [
    "README.md",
    "docker-compose.yml",
    ".gitignore",
    "log/progress-log.md",
    "docs/specs/implementation-guide.md",
    "docs/architecture/repository-structure.md",
    "docs/guides/how-to-run.md",
    "migrations/V1__create_dwh_schema.sql",
    "dags/insurance_dwh_pipeline.py",
    "ml/train_risk_model.py",
    "ml/predict_risk_batch.py",
    "notebooks/01-eda.ipynb",
    "data/raw/.gitkeep",
    "data/raw/brvehins1/brvehins1a.csv",
    "data/raw/brvehins1/brvehins1b.csv",
    "data/raw/brvehins1/brvehins1c.csv",
    "data/raw/brvehins1/brvehins1d.csv",
    "data/raw/brvehins1/brvehins1e.csv",
    "data/raw/susep.gov.br/insurance_dataset.csv",
    "powerbi/.gitkeep",
    "scripts/validate_repo.py",
    "sql/01_load_staging.sql",
    "sql/02_enable_cdc.sql",
    "sql/03_sp_dim_customer_scd2.sql",
    "sql/04_sp_dim_others.sql",
    "sql/05_sp_fact_premium.sql",
    "sql/06_sp_fact_claims.sql",
    "sql/07_data_quality_checks.sql",
    "sql/08_sp_load_risk_predictions.sql",
    ".cursor/rules/01-quy-trinh-thuc-hien.mdc",
    ".cursor/rules/02-quan-ly-file-va-log.mdc",
    ".cursor/rules/03-kiem-tra-git-va-review.mdc",
    ".cursor/rules/04-python.mdc",
    ".cursor/rules/05-setup-handoff.mdc",
]


class ValidationReporter:
    def __init__(self):
        self.results = []

    def add(self, category: str, item: str, status: str, detail: str = ""):
        self.results.append({
            "category": category,
            "item": item,
            "status": status,
            "detail": detail
        })
        prefix = f"[{status}]"
        print(f"{prefix:<10} {category:<20} {item:<40} {detail}")

    def summary(self):
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIPPED")
        print("\n" + "=" * 78)
        print(f"VALIDATION SUMMARY: {passed} PASSED | {failed} FAILED | {skipped} SKIPPED")
        print("=" * 78)
        return failed == 0


def check_canonical_files(reporter: ValidationReporter):
    print("\n--- 1. Kiem tra cac tep canonical bat buoc ---")
    for rel_path in REQUIRED_CANONICAL_FILES:
        target = REPO_ROOT / rel_path
        if target.exists() and target.is_file():
            reporter.add("Canonical Files", rel_path, "PASS", "Tep ton tai")
        else:
            reporter.add("Canonical Files", rel_path, "FAIL", "Khong tim thay tep")


def check_docker_compose(reporter: ValidationReporter):
    print("\n--- 2. Kiem tra Docker Compose Configuration ---")
    print("\n--- 3. Kiem tra Docker Compose Configuration ---")
    compose_path = REPO_ROOT / "docker-compose.yml"
    if not compose_path.exists():
        reporter.add("Docker Compose", "docker-compose.yml", "FAIL", "Khong tim thay tep")
        return

    # Kiem tra qua thu vien PyYAML neu co
    try:
        import yaml
        with open(compose_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict) and "services" in data:
            services = list(data["services"].keys())
            if "sqlserver" in services and "airflow" in services:
                reporter.add("Docker Compose", "docker-compose.yml", "PASS", f"Services xac nhan: {', '.join(services)}")
            else:
                reporter.add("Docker Compose", "docker-compose.yml", "FAIL", f"Thieu service bat buoc (can sqlserver, airflow; co: {services})")
        else:
            reporter.add("Docker Compose", "docker-compose.yml", "FAIL", "Cac dinh nghia services khong hop le")
        return
    except ImportError:
        pass
    except Exception as e:
        reporter.add("Docker Compose", "docker-compose.yml", "FAIL", f"Loi parse YAML: {e}")
        return

    # Fallback goi docker compose config
    try:
        res = subprocess.run(["docker", "compose", "config", "-q"], cwd=str(REPO_ROOT), capture_output=True, text=True)
        if res.returncode == 0:
            reporter.add("Docker Compose", "docker-compose.yml", "PASS", "Parse thanh cong qua docker compose config CLI")
        else:
            reporter.add("Docker Compose", "docker-compose.yml", "FAIL", res.stderr.strip())
    except FileNotFoundError:
        reporter.add("Docker Compose", "docker-compose.yml", "SKIPPED", "PyYAML chua cai va docker CLI khong kha dung")


def check_python_files(reporter: ValidationReporter):
    print("\n--- 3. Bien dich cu phap Python (py_compile) ---")
    print("\n--- 4. Bien dich cu phap Python (py_compile) ---")
    py_dirs = ["dags", "ml", "scripts"]
    for d in py_dirs:
        dir_path = REPO_ROOT / d
        if not dir_path.exists():
            continue
        for py_file in dir_path.rglob("*.py"):
            rel_name = py_file.relative_to(REPO_ROOT).as_posix()
            try:
                py_compile.compile(str(py_file), doraise=True)
                reporter.add("Python Syntax", rel_name, "PASS", "Cu phap hop le")
            except py_compile.PyCompileError as e:
                reporter.add("Python Syntax", rel_name, "FAIL", f"Loi cu phap: {e}")


def check_notebooks(reporter: ValidationReporter):
    print("\n--- 4. Parse Notebooks (JSON validity) ---")
    print("\n--- 5. Parse Notebooks (JSON validity) ---")
    nb_dir = REPO_ROOT / "notebooks"
    if not nb_dir.exists():
        reporter.add("Notebooks", "notebooks/", "SKIPPED", "Thu muc notebooks khong ton tai")
        return

    nb_files = list(nb_dir.glob("*.ipynb"))
    if not nb_files:
        reporter.add("Notebooks", "notebooks/", "SKIPPED", "Khong co tep .ipynb")
        return

    for nb_file in nb_files:
        rel_name = nb_file.relative_to(REPO_ROOT).as_posix()
        try:
            with open(nb_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "cells" in data and "metadata" in data:
                reporter.add("Notebooks", rel_name, "PASS", f"JSON hop le ({len(data['cells'])} cells)")
            else:
                reporter.add("Notebooks", rel_name, "FAIL", "Thieu key 'cells' hoac 'metadata'")
        except Exception as e:
            reporter.add("Notebooks", rel_name, "FAIL", f"Loi parse JSON: {e}")


def check_sql_files(reporter: ValidationReporter):
    print("\n--- 5. Kiem tra cau truc cac tep SQL ---")
    print("\n--- 6. Kiem tra cau truc cac tep SQL ---")
    sql_dirs = ["sql", "migrations"]
    for d in sql_dirs:
        dir_path = REPO_ROOT / d
        if not dir_path.exists():
            continue
        for sql_file in sorted(dir_path.glob("*.sql")):
            rel_name = sql_file.relative_to(REPO_ROOT).as_posix()
            size = sql_file.stat().st_size
            if size == 0:
                reporter.add("SQL Structure", rel_name, "FAIL", "Tep rong (0 bytes)")
                continue

            # Kiem tra can bang block comment /* */
            try:
                with open(sql_file, "r", encoding="utf-8") as f:
                    content = f.read()
                open_blocks = content.count("/*")
                close_blocks = content.count("*/")
                if open_blocks == close_blocks:
                    reporter.add("SQL Structure", rel_name, "PASS", f"Size: {size}B, Block comments can bang ({open_blocks}/{close_blocks})")
                else:
                    reporter.add("SQL Structure", rel_name, "FAIL", f"Mat can bang block comments (/* : {open_blocks}, */ : {close_blocks})")
            except Exception as e:
                reporter.add("SQL Structure", rel_name, "FAIL", f"Loi doc file: {e}")


def check_duplicate_canonical_files(reporter: ValidationReporter):
    print("\n--- 6. Kiem tra trung lap ten file canonical co ban ---")
    print("\n--- 7. Kiem tra trung lap ten file canonical co ban ---")
    # Kiem tra cac file script hoac rule co bi tao trung lap o thu muc khac khong
    basenames = {}
    ignore_dirs = {".git", ".venv", "__pycache__"}
    duplicates_found = False

    canonical_basenames = {Path(p).name for p in REQUIRED_CANONICAL_FILES}
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            if f in canonical_basenames:
                rel_f = Path(root, f).relative_to(REPO_ROOT).as_posix()
                basenames.setdefault(f, []).append(rel_f)

    for f, paths in basenames.items():
        if len(paths) > 1 and f != ".gitkeep":
            duplicates_found = True
            reporter.add("Duplicate Check", f, "FAIL", f"Trung lap tai: {', '.join(paths)}")

    if not duplicates_found:
        reporter.add("Duplicate Check", "Canonical Basenames", "PASS", "Khong co trung lap ten file bat thuong")


def check_raw_dataset_brvehins1(reporter: ValidationReporter):
    print("\n--- 2. Kiem tra tap du lieu tho canonical brvehins1 ---")
    br_dir = REPO_ROOT / "data" / "raw" / "brvehins1"
    if not br_dir.exists() or not br_dir.is_dir():
        reporter.add("Raw Dataset", "data/raw/brvehins1", "FAIL", "Thu muc khong ton tai")
        return

    partitions = ["brvehins1a.csv", "brvehins1b.csv", "brvehins1c.csv", "brvehins1d.csv", "brvehins1e.csv"]
    headers = {}
    for p in partitions:
        p_path = br_dir / p
        if not p_path.exists():
            reporter.add("Raw Dataset", f"brvehins1/{p}", "FAIL", "Tep khong ton tai")
            continue
        size = p_path.stat().st_size
        if size == 0:
            reporter.add("Raw Dataset", f"brvehins1/{p}", "FAIL", "Tep rong (0 bytes)")
            continue
        try:
            with open(p_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                header = next(reader)
                headers[p] = header
        except Exception as e:
            reporter.add("Raw Dataset", f"brvehins1/{p}", "FAIL", f"Loi doc header: {e}")

    if len(headers) == len(partitions):
        base_header = headers["brvehins1a.csv"]
        all_match = all(h == base_header for h in headers.values())
        if all_match:
            reporter.add("Raw Dataset", "brvehins1 partitions", "PASS", f"5 phan doan hop le, schema dong nhat ({len(base_header)} cot)")
        else:
            reporter.add("Raw Dataset", "brvehins1 partitions", "FAIL", "Schema giua cac phan doan khong khop nhau")


def report_skipped_runtime_validations(reporter: ValidationReporter):
    print("\n--- 7. Danh muc kiem tra Runtime duoc SKIPPED (PENDING_RUNTIME) ---")
    print("\n--- 8. Danh muc kiem tra Runtime duoc SKIPPED (PENDING_RUNTIME) ---")
    skipped_items = [
        ("SQL Server Connectivity", "Ket noi mang toi localhost:1433", "Chua khoi dong container sqlserver"),
        ("Flyway / DbUp Migration", "Thuc thi V1__create_dwh_schema.sql tao DWH_Insurance", "Can SQL Server runtime va cong cu migration"),
        ("Staging BULK INSERT", "Nap du lieu CSV tho vao Staging_InsuranceRaw", "Can du lieu CSV that va SQL Server runtime"),
        ("Staging BULK INSERT", "Nap 5 phan doan CSV brvehins1 vao Staging_InsuranceRaw", "Can SQL Server runtime va kiem tra BULK INSERT"),
        ("CDC Enable & Capture", "Kich hoat sys.sp_cdc_enable_db va bat LSN watermark", "Can SQL Server Agent runtime"),
        ("SCD2 Idempotency", "sp_Load_DimCustomer kiem tra versioning va idempotent rerun", "Can du lieu Staging va database runtime"),
        ("Fact Referential Integrity", "sp_Load_FactPremium, sp_Load_FactClaims FK integrity", "Can cac bang Dim duoc nap truoc"),
        ("Data Quality Execution", "sp_Run_DataQualityChecks va kiem tra ngat pipeline", "Can cac bang Fact/Dim trong DWH"),
        ("SCD2 / Dimension Load", "Nap Dimension theo data contract brvehins1", "Can du lieu Staging va database runtime"),
        ("Fact Referential Integrity", "sp_Load_Fact* FK integrity theo schema brvehins1", "Can cac bang Dim duoc nap truoc"),
        ("Data Quality Execution", "sp_Run_DataQualityChecks theo cac rule brvehins1", "Can cac bang Fact/Dim trong DWH"),
        ("Airflow DAG Run", "Thuc thi insurance_dwh_pipeline tren webserver/scheduler", "Can khoi dong Airflow container"),
        ("ML Model Training", "Huan luyen mo hinh tu du lieu Porto Seguro that", "Can du lieu train.csv va scikit-learn"),
        ("Performance Benchmark", "Do STATISTICS IO/TIME truoc va sau khi tao index", "Can du lieu Fact ~8-10 trieu dong tren DWH"),
        ("ML Model Training", "Huan luyen mo hinh tu du lieu brvehins1", "Can hoan thien data contract va scikit-learn"),
        ("Performance Benchmark", "Do STATISTICS IO/TIME truoc va sau khi tao index", "Can du lieu Fact ~2 trieu dong tren DWH"),
        ("Power BI Dashboard", "Kiem tra ket noi truc tiep Power BI toi DWH_Insurance", "Can DWH hoan thanh va Power BI Desktop"),
    ]
    for item, action, reason in skipped_items:
        reporter.add("Runtime Checklist", item, "SKIPPED", f"{action} -> {reason}")


def main():
    print("=" * 78)
    print("INSURANCE DWH - STATIC REPOSITORY VALIDATION")
    print(f"Repository Root: {REPO_ROOT}")
    print("=" * 78)

    reporter = ValidationReporter()
    check_canonical_files(reporter)
    check_raw_dataset_brvehins1(reporter)
    check_docker_compose(reporter)
    check_python_files(reporter)
    check_notebooks(reporter)
    check_sql_files(reporter)
    check_duplicate_canonical_files(reporter)
    report_skipped_runtime_validations(reporter)

    success = reporter.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
