"""Small, explicit entry points for warehouse operations. Run from any directory."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from config import ROOT, connect


def migration_paths(directory: Path | None = None) -> list[Path]:
    return sorted((directory or ROOT / "database/migrations").glob("V*__*.sql"),
                  key=lambda path: int(path.name.split("__")[0][1:]))


def sql_batches(text: str) -> list[str]:
    # Repository migrations use GO alone on a line; GO is a client separator.
    return [part.strip() for part in re.split(r"(?im)^\s*GO\s*(?:--[^\n]*)?$", text) if part.strip()]


def execute(connection, statement: str, *parameters) -> None:
    cursor = connection.cursor()
    cursor.execute(statement, *parameters)
    while cursor.nextset():
        pass  # Terminal THROW can arrive after a result set.


def migrate() -> None:
    with connect("master", autocommit=True) as connection:
        for path in migration_paths():
            version = path.name.split("__")[0]
            exists = connection.execute("SELECT DB_ID(N'DWH_Insurance')").fetchval()
            if exists:
                has_history = connection.execute("SELECT OBJECT_ID(N'DWH_Insurance.meta.SchemaVersion',N'U')").fetchval()
                if has_history and connection.execute(
                    "SELECT COUNT(*) FROM DWH_Insurance.meta.SchemaVersion WHERE MigrationVersion=?", version
                ).fetchval():
                    print(f"SKIPPED {path.name}")
                    continue
            for batch in sql_batches(path.read_text(encoding="utf-8-sig")):
                execute(connection, batch)
            print(f"APPLIED {path.name}")


def run_script(name: str, *arguments: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "pipeline" / name), *arguments], cwd=ROOT, check=True)


def load(track: str) -> None:
    import os
    server = os.getenv("SQLSERVER_HOST", "localhost,1433")
    if track == "market":
        run_script("load_market.py", "--server", server)
        procedures = ("dwh.sp_LoadSusepDimensions", "dwh.sp_LoadFactSusepInsuranceMarket")
    else:
        for suffix in "abcde":
            run_script("load_risk.py", "--source-file", f"brvehins1{suffix}.csv", "--server", server)
        procedures = ("dwh.sp_LoadCanonicalDimensions", "dwh.sp_LoadFactRiskObservation")
    with connect() as connection:
        for procedure in procedures:
            execute(connection, f"EXEC {procedure};")
        connection.commit()
    print(f"LOADED {track}; run quality next.")


def quality() -> None:
    with connect(autocommit=True) as connection:
        for procedure in ("dq.sp_RunSusepQualityGate", "dq.sp_RunQualityGate"):
            execute(connection, f"EXEC {procedure} @RunLabel=N'manage_quality';")
            print(f"PASS {procedure}")


def status() -> None:
    with connect() as connection:
        for name in ("stg.SusepInsuranceMarket", "dwh.FactSusepInsuranceMarket", "stg.BrVehIns1", "dwh.FactRiskObservation", "dwh.RiskObservationPrediction"):
            count = connection.execute(f"SELECT COUNT_BIG(*) FROM {name}").fetchval()
            print(f"{name}: {count:,}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["migrate", "load-market", "load-risk", "quality", "status", "export", "score"])
    action = parser.parse_args().action
    if action == "migrate":
        migrate()
    elif action.startswith("load-"):
        load(action.split("-")[1])
    elif action == "quality":
        quality()
    elif action == "status":
        status()
    else:
        run_script("export_dash.py" if action == "export" else "score_risk.py")


if __name__ == "__main__":
    main()
