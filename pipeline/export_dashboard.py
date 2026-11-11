"""Export real, aggregated warehouse data for the Dash application.

No customer/source-row identifiers leave SQL Server. The exported JSON is an
auditable snapshot: its timestamp and source are displayed by the dashboard.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from config import ROOT, connect


def query(connection, sql: str, *parameters) -> dict:
    cursor = connection.cursor()
    connection.timeout = 180
    cursor.execute(sql, *parameters)
    columns = [column[0] for column in cursor.description]
    rows = []
    for record in cursor:
        rows.append([
            value.isoformat() if isinstance(value, (date, datetime))
            else float(value) if isinstance(value, Decimal)
            else value for value in record
        ])
    return {"columns": columns, "rows": rows}


def export_snapshot(destination: Path) -> dict:
    with connect() as connection:
        # SNAPSHOT is not enabled on every local SQL Server. SERIALIZABLE keeps
        # all exported aggregates consistent with one another during this read.
        connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;")
        counts = query(connection, """
            SELECT (SELECT COUNT_BIG(*) FROM stg.SusepInsuranceMarket) AS market_staging,
                   (SELECT COUNT_BIG(*) FROM dwh.FactSusepInsuranceMarket) AS market_fact,
                   (SELECT COUNT_BIG(*) FROM stg.BrVehIns1) AS risk_staging,
                   (SELECT COUNT_BIG(*) FROM dwh.FactRiskObservation) AS risk_fact;
        """)
        monthly = query(connection, """
            SELECT CONVERT(varchar(10),m.YearMonth,23) AS month, s.State AS state,
                   SUM(CONVERT(float,f.Premiums)) AS premium,
                   SUM(CONVERT(float,f.Claims)) AS claims, COUNT_BIG(*) AS observations
            FROM dwh.FactSusepInsuranceMarket f
            JOIN dwh.DimSusepMonth m ON m.SusepMonthKey=f.SusepMonthKey
            JOIN dwh.DimSusepState s ON s.SusepStateKey=f.SusepStateKey
            GROUP BY m.YearMonth,s.State ORDER BY m.YearMonth,s.State;
        """)
        companies = query(connection, """
            SELECT m.CalendarYear AS year,s.State AS state,f.SusepCompanyKey AS company,
                   SUM(CONVERT(float,f.Premiums)) AS premium,
                   SUM(CONVERT(float,f.Claims)) AS claims
            FROM dwh.FactSusepInsuranceMarket f
            JOIN dwh.DimSusepMonth m ON m.SusepMonthKey=f.SusepMonthKey
            JOIN dwh.DimSusepState s ON s.SusepStateKey=f.SusepStateKey
            GROUP BY m.CalendarYear,s.State,f.SusepCompanyKey;
        """)
        products = query(connection, """
            SELECT m.CalendarYear AS year,s.State AS state,f.SusepProductKey AS product,
                   SUM(CONVERT(float,f.Premiums)) AS premium,
                   SUM(CONVERT(float,f.Claims)) AS claims
            FROM dwh.FactSusepInsuranceMarket f
            JOIN dwh.DimSusepMonth m ON m.SusepMonthKey=f.SusepMonthKey
            JOIN dwh.DimSusepState s ON s.SusepStateKey=f.SusepStateKey
            GROUP BY m.CalendarYear,s.State,f.SusepProductKey;
        """)
        risk = query(connection, """
            SELECT COALESCE(g.StateAb,N'Không rõ') AS state,
                   COALESCE(d.Gender,N'Không rõ') AS gender,
                   COALESCE(d.DrivAge,N'Không rõ') AS age,
                   COUNT_BIG(*) AS observations,
                   SUM(CONVERT(float,f.ExposTotal)) AS exposure,
                   SUM(CONVERT(float,f.PremTotal)) AS premium,
                   SUM(CONVERT(bigint,f.TotalClaimCount)) AS claim_count,
                   SUM(CONVERT(float,f.TotalClaimAmount)) AS claims,
                   SUM(CONVERT(bigint,f.HasClaim)) AS has_claim
            FROM dwh.FactRiskObservation f
            JOIN dwh.DimDriverProfile d ON d.DriverProfileKey=f.DriverProfileKey
            JOIN dwh.DimGeography g ON g.GeographyKey=f.GeographyKey
            GROUP BY g.StateAb,d.Gender,d.DrivAge;
        """)
        scores = query(connection, """
            SELECT COALESCE(g.StateAb,N'Không rõ') AS state,
                   CONVERT(int,FLOOR(CONVERT(float,p.ScoreProbability)*20)) AS band,
                   COUNT_BIG(*) AS observations,
                   SUM(CONVERT(float,p.ScoreProbability)) AS score_sum,
                   SUM(CONVERT(bigint,f.HasClaim)) AS positives
            FROM dwh.RiskObservationPrediction p
            JOIN dwh.FactRiskObservation f
              ON f.SourceFile=p.SourceFile AND f.SourceRowNumber=p.SourceRowNumber
            JOIN dwh.DimGeography g ON g.GeographyKey=f.GeographyKey
            WHERE p.ModelVersion=N'claim_risk_model_v001'
              AND p.ScoringPopulation=N'bounded_held_out_test'
            GROUP BY g.StateAb,CONVERT(int,FLOOR(CONVERT(float,p.ScoreProbability)*20));
        """)
        lookup = {
            "company_names": {str(r[0]): r[1] for r in connection.execute("SELECT SusepCompanyKey,CompanyName FROM dwh.DimSusepCompany")},
            "product_names": {str(r[0]): r[1] for r in connection.execute("SELECT SusepProductKey,Product FROM dwh.DimSusepProduct")},
        }
        connection.commit()
    evidence = json.loads((ROOT / "data/evidence.json").read_text(encoding="utf-8"))
    content = {
        "schema_version": 1,
        "exported_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SQL Server · DWH_Insurance",
        "source_period": "2003-01 đến 2023-07; dữ liệu motor không có event time",
        "counts": dict(zip(counts["columns"], counts["rows"][0], strict=True)),
        "market": {"monthly": monthly, "companies": companies, "products": products, **lookup},
        "risk": {"segments": risk, "scores": scores},
        "model_metrics": evidence["model"]["held_out_test_metrics"],
        "performance": evidence["performance"],
    }
    if sum(r[4] for r in monthly["rows"]) != content["counts"]["market_fact"]:
        raise RuntimeError("Dashboard export không đối soát được market row count.")
    if sum(r[3] for r in risk["rows"]) != content["counts"]["risk_fact"]:
        raise RuntimeError("Dashboard export không đối soát được risk row count.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".pending")
    temporary.write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    os.replace(temporary, destination)
    print(json.dumps({"path": str(destination), "counts": content["counts"], "exported_at_utc": content["exported_at_utc"]}))
    return content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/dashboard.json")
    export_snapshot(parser.parse_args().output)
