<p align="center">
  <img src="dashboard/assets/banner.svg" alt="Insurance Data Platform: a personal data engineering and risk analytics project" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/SQL_Server-2022-CC2927?style=flat-square" alt="SQL Server 2022">
  <img src="https://img.shields.io/badge/Apache_Airflow-2.8-017CEE?style=flat-square&amp;logo=apacheairflow&amp;logoColor=white" alt="Apache Airflow 2.8">
  <img src="https://img.shields.io/badge/Plotly-Dash-147D78?style=flat-square&amp;logo=plotly&amp;logoColor=white" alt="Plotly Dash">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&amp;logo=docker&amp;logoColor=white" alt="Docker Compose">
</p>

<p align="center"><strong>From insurance CSVs to a quality-checked SQL warehouse, risk analysis, and an interactive dashboard.</strong></p>

<p align="center">
  <a href="#dashboard-stories">Explore the charts</a> ·
  <a href="#quick-start">Run the dashboard</a> ·
  <a href="#technology-map">View the technology map</a>
</p>

## What this project does

Insurance Data Platform is a personal data engineering and analytics project. Python ingests source CSVs in batches, SQL Server stores staging and dimensional warehouse tables, quality gates check the loads, and Airflow can orchestrate the jobs. Plotly Dash serves an exported, timestamped aggregate snapshot, so changing a filter does not scan millions of SQL rows.

The two sources answer different questions:

- **Track A — SUSEP insurance market:** 8,338,214 rows at company × month × product × state grain, from January 2003 through July 2023. It supports premium, claims, product mix, and SQL performance analysis.
- **Track B — brvehins1 motor risk:** 1,965,355 aggregate risk observations across five CSV files. It supports exposure and observed claim analysis, plus a bounded `HasClaim` model evaluation.

The sources have different grains and no demonstrated shared customer, policy, or claim identity. Their warehouse tracks remain independent; there is no row-level join. Prudential is a future idea with no raw data or implemented pipeline.

## Technology map

<p align="center">
  <img src="dashboard/assets/architecture.svg" alt="Technology logos for Python, SQL Server, Plotly Dash, Apache Airflow, scikit-learn, and Docker Compose" width="100%">
</p>

Python and pandas load and aggregate data; SQL Server stores and checks it; Plotly Dash presents the exported JSON snapshot. Airflow coordinates local jobs, scikit-learn supports the separately run model workflow, and Docker Compose starts the local services. The diagram shows the tools used in this repository, not a join between its two data sources.

## Dashboard stories

These are **individual views from the English-language Dash app**, captured from the SQL export dated **11 November 2026**. They show the unfiltered default view. Choose a state or year range in the app to ask a narrower question; the screenshot findings below describe only the displayed population. The dashboard is a snapshot, not a live SQL view. For a page-by-page narrative in Vietnamese, read [the dashboard story guide](dashboard/STORY.md).

### Market overview · Track A

#### How have premiums and claims changed?

<p align="center"><img src="dashboard/assets/market-trend.png" alt="Monthly SUSEP premiums and claims from 2003 to July 2023" width="100%"></p>

**Reading:** Premium volume rises over much of the series while claims remain below premiums. Across the full selected period, premiums total **3.05 trillion** and claims **735.52 billion** in *source units*, giving a **24.1% claims-to-premiums ratio**. The latest comparable period, January–July 2023 versus January–July 2022, has **8.9% higher premiums** and a **4.9 percentage-point lower ratio**. The chart can switch between monthly and annual aggregation; 2023 contains only January–July, so its annual point is a partial year. This ratio is a descriptive aggregate, not a profit margin.

#### Which companies account for the most premium volume?

<p align="center"><img src="dashboard/assets/market-companies.png" alt="Top ten SUSEP companies ranked by premium volume" width="80%"></p>

**Reading:** BRADESCO VIDA and BRASILPREV lead this selection at approximately **455.2 billion** and **443.0 billion** source units. Their shares of total premium volume are about **14.9%** and **14.5%**. Ranking is based on the selected years and state; hover in the app for full source names. A large volume does not establish a better claims result.

#### Which product lines dominate the mix?

<p align="center"><img src="dashboard/assets/market-products.png" alt="Top eight SUSEP product lines ranked by premium volume" width="80%"></p>

**Reading:** “VGBL & related plans” is the largest displayed line at about **1.10 trillion** source units, or **36.0%** of all selected premiums. “Motor own damage” follows at about **382.3 billion**. These are source product categories; the app keeps source codes and full names in hover details. Concentration is a volume observation, not a forecast.

### Motor risk and model · Track B

#### Where do held-out model scores fall?

<p align="center"><img src="dashboard/assets/risk-distribution.png" alt="Held-out HasClaim model score distribution in 0.05-wide bands" width="80%"></p>

**Reading:** **13,526 of 20,000 held-out observations (67.6%)** have a model score below 0.20. The chart describes the score distribution of a bounded, historical evaluation sample. It does not display scores for every warehouse row, and the scores are not validated probabilities of future claims.

#### Do higher score bands contain more observed claims?

<p align="center"><img src="dashboard/assets/risk-observed.png" alt="Observed HasClaim share compared with mean model score across held-out score bands" width="80%"></p>

**Reading:** In the held-out sample, the combined bands below 0.20 have **8.8%** observed `HasClaim`, while bands from 0.50 upward have **69.9%** across **1,091** observations. The chart compares the observed share with the mean score within each band; small high-score bands can be noisy. This is cross-sectional association, not a future underwriting probability or evidence of causality. The historical full-sample ROC-AUC is **0.808815** and average precision is **0.513523**; those metrics do not change with the dashboard's state filter.

### Data quality and performance

#### Which data rows feed the dashboard?

<p align="center"><img src="dashboard/assets/data-explorer.png" alt="Paginated SUSEP month and state aggregate rows in the Dash data explorer" width="100%"></p>

**Reading:** The Data tab now exposes the dated SQL snapshot's **6,669** market month/state aggregates or **644** motor risk segments. Switch source, filter by state, and page through 15 rows at a time. The market view shows premiums, claims, their ratio, and observation counts. The motor view shows exposure, claim counts, and observed `HasClaim` share by state, source gender label, and age group. These rows are aggregates; they are not the private raw records or individual customers and policies.

#### What did the SQL indexes improve, and what did they cost?

<p align="center"><img src="dashboard/assets/sql-benchmark.png" alt="Before and after SQL logical reads for two SUSEP workloads, with a log-scale axis" width="100%"></p>

**Reading:** In a **24 September 2026** warm-cache benchmark, two covering indexes reduced logical reads by **98.94%** for the company/month workload and **98.82%** for the state/product/month workload. They also added approximately **924.51 MB** of index storage and write overhead. Logical reads measure SQL page accesses; this is historical evidence for those two queries, not a new benchmark or an end-to-end dashboard speed test. The Data tab's KPI also shows staging/fact row-count reconciliation from the current snapshot.

The app also includes age-group and profile-label views, per-track filters and resets, CSV exports of **filtered aggregates**, and Plotly PNG chart downloads. Market KPI comparison badges use matching calendar months in the prior year and can show favorable or unfavorable movement. The risk tab separates full-warehouse observations from the 20,000-row held-out model sample.

## Quick start

**To view the bundled dashboard snapshot, you only need Python 3.12.** From the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m dashboard.app
```

Open **http://127.0.0.1:8050**. If the virtual environment already exists, skip its creation. This path reads `data/dashboard.json` and needs no SQL Server login, raw CSV, `.env`, or private model binary. Stop the app with `Ctrl+C`. To refresh the displayed data after a new SQL load, run `export` in the full pipeline below and reload the page. No public dashboard URL is configured yet.

## Run the full pipeline

This path requires **Docker Desktop**, **Python 3.12**, **Microsoft ODBC Driver 18 for SQL Server on the host**, and the source CSVs described below. Run commands from the repository root. Use the same virtual environment and installed `requirements.txt` from Quick start.

### 1. Configure and start SQL Server

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Edit .env and set SQLSERVER_SA_PASSWORD to a strong local password.
docker compose up -d sqlserver
docker compose logs --tail 30 sqlserver
.venv\Scripts\python.exe pipeline/manage.py migrate
```

Wait until SQL Server is ready before migration. `.env.example` lists optional settings; `.env` can contain only `SQLSERVER_SA_PASSWORD` because host (`localhost,1433`), database (`DWH_Insurance`), and user (`sa`) have defaults in `pipeline/config.py`. Keep `.env` private. An existing SQL volume retains its original `sa` password; editing `.env` alone does not change it. Migrations **V1–V14** run in numeric order and skip versions already recorded in SQL Server.

### 2. Supply and validate the source files

```text
data/raw/susep.gov.br/insurance_dataset.csv
data/raw/brvehins1/brvehins1a.csv
data/raw/brvehins1/brvehins1b.csv
data/raw/brvehins1/brvehins1c.csv
data/raw/brvehins1/brvehins1d.csv
data/raw/brvehins1/brvehins1e.csv
```

Raw files are local-only and must be left unchanged. Then run:

```powershell
.venv\Scripts\python.exe pipeline/validate.py --raw
.venv\Scripts\python.exe pipeline/manage.py load-market
.venv\Scripts\python.exe pipeline/manage.py load-risk
.venv\Scripts\python.exe pipeline/manage.py quality
.venv\Scripts\python.exe pipeline/manage.py status
.venv\Scripts\python.exe pipeline/reconcile_market.py
.venv\Scripts\python.exe pipeline/manage.py export
```

The first load can take time for more than ten million rows. Completed input batches are fingerprinted so repeated loads can skip them. Both SQL quality gates must pass before treating the warehouse as ready; row counts from `status` alone are insufficient. `export` writes a new timestamped aggregate snapshot for Dash. Run it after the quality checks when data changes.

### 3. Optional model scoring and Airflow

```powershell
.venv\Scripts\python.exe pipeline/manage.py score
.venv\Scripts\python.exe pipeline/manage.py export
docker compose --profile orchestration up -d --build airflow
```

`score` needs the already trained local artifact at `data/models/claim_risk_model_v001.joblib` and a loaded Track B warehouse. That binary is **not included in a public clone**. Training is a separate, deliberate operation through `pipeline/train_risk.py`; running the dashboard never trains a model. Export again after scoring if you want the dashboard snapshot to reflect new prediction aggregates.

Airflow runs at **http://127.0.0.1:8080** using the `insurance_data_platform` DAG. The DAG has `schedule=None`: trigger it manually. Track A loads, reconciles, and quality-checks market data. Track B assumes its foundation and model already exist, then checks quality, scores, and verifies predictions. The DAG does **not** perform first-time Track B loading, model training, or dashboard export. Airflow uses a local standalone/SQLite setup here; its CLI test evidence is not a production scheduler run.

To run Dash in Docker instead of the Python command:

```powershell
docker compose --profile analytics up -d --build dashboard
```

Compose requires `SQLSERVER_SA_PASSWORD` in `.env` for configuration interpolation even when you start only the dashboard profile. Dash binds to **127.0.0.1:8050**, Airflow to **127.0.0.1:8080**, and SQL Server to **127.0.0.1:1433**. Only one dashboard process should use port 8050.

## Data contract and interpretation

- **SUSEP:** the CSV header must be `company_code,company_name,year_month,product,state,premiums,claims,claim_premium_ratio`. Each row is a company/month/product/state aggregate. Raw text remains available for audit; analyzed numeric values use a documented decimal rounding policy. Source `claim_premium_ratio` may be `NA`; the dashboard computes its displayed ratio as `SUM(claims) / SUM(premiums)` when total premiums are positive. The monetary unit has not been fully verified, so charts say **source units**, not BRL.
- **brvehins1:** 23 source fields describe driver, vehicle, geography, exposure, premium, and five claim groups. Each row is an **aggregate risk observation**, not necessarily one customer, policy, or claim event. `HasClaim` is true when the sum of the five `ClaimNb*` fields is positive. Claims/exposure is a claim-count frequency when exposure is positive. Identical source values retain separate lineage.
- **Model:** features are `Gender`, `DrivAge`, `VehYear`, `VehModel`, `VehGroup`, `Area`, and `StateAb`. The bounded sample has **100,004** rows, including a **20,000**-row held-out test set. Splitting by `SourceRecordHash` limits leakage from repeated records. There is no event timestamp in Track B, so the current model measures cross-sectional `HasClaim` association rather than prospective claim risk.

## Repository layout and storage

```text
dashboard/   Dash app, styling, technology diagram, chart images, and STORY.md
pipeline/    Ingestion, validation, quality operations, ML, export, Airflow DAG, CLI
database/    Versioned SQL migrations V1–V14 and benchmark SQL
infra/       Dockerfiles and service-specific dependencies
data/        Public aggregate snapshot and evidence; private raw/model/output locally
tests/       Unit and browser checks
```

`docker-compose.yml` stays at the root as the system entry point. `database/` holds **SQL code** that creates and upgrades the database; `data/` holds **files** used or produced by the project. SQL Server's actual database files live in the Docker named volume `sqlserver_data` at `/var/opt/mssql`, not in either repository folder. `airflow_state` holds local Airflow metadata and `airflow_logs` holds task logs. Raw and model folders are mounted read-only into containers that need them.

`docker compose stop` stops services. `docker compose down` keeps named volumes by default. Keep the same Compose project name to reuse the existing SQL volume, and avoid `docker compose down -v` when the database must be preserved. Git is not a backup of SQL data.

## Verification and known limits

The latest recorded warehouse checks on **11 November 2026** reconciled staging and fact row counts for both tracks (**8,338,214** and **1,965,355**) and passed two SQL quality gates. An Airflow `dags test` run completed **12/12 tasks**; it was a CLI test run. The model metrics and SQL benchmark above are **historical September 2026** results, not measurements repeated by this README update. The dashboard snapshot carries `exported_at_utc` so users can see its age.

Run static validation and unit tests locally:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe pipeline/validate.py
.venv\Scripts\python.exe -m unittest discover -s tests -p test_*.py
docker compose --profile analytics --profile orchestration config -q
```

With the app running and Microsoft Edge installed, `.venv\Scripts\python.exe tests/browser_check.py` checks the three pages, filters, resets, downloads, responsive widths, and health endpoint. `data/evidence.json` records older machine-readable evidence. A fresh isolated SQL rebuild/restore has not been validated, the dashboard has no authentication or RBAC, and local Airflow is not configured as a production deployment.

## License

Code is covered by [LICENSE](LICENSE). `.env`, raw CSVs, trained model binaries, generated runtime output, and virtual environments stay outside Git. Check the source providers' terms before redistributing source data; the bundled dashboard file contains aggregates for demonstration.
