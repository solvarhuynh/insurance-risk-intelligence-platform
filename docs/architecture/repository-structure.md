# Folder nào thuộc track nào?

```text
insurance-dwh-project/
├── data/raw/
│   ├── susep.gov.br/          # Track A: active canonical market source
│   └── brvehins1/             # Track B: active canonical motor-risk source
├── migrations/, sql/          # SQL Server platform; Track A + Track B runtime
├── scripts/                   # Validator, loaders/profilers/reconciler cho hai track
├── ml/                        # Track B only: risk-association training/scoring
├── dags/, airflow/            # Airflow runtime orchestration across independent tracks
├── powerbi/                   # Separate market/risk semantic-model manual handoff
├── docs/architecture/         # Scope, source strategy, contracts and designs
├── docs/specs/roadmap.md      # Current multi-track roadmap
├── reports/                   # Runtime evidence and historical checkpoints
└── log/progress-log.md        # Append-only history plus latest next step
```

## Migrations chứa implementation nào?

V1–V10, `stg.BrVehIns1`, các risk dimensions, fact, DQ và prediction table là implementation **Track B**. V11–V14 thêm `stg.SusepInsuranceMarket`, independent batch/reject metadata, SUSEP dimensions, one-observation fact, direct reconciliation, DQ và performance indexes cho **Track A**. `DWH_Insurance` là shared platform container, không phải lý do để join hai track.

## File nào là current và file nào là historical scaffold?

- Current Track A entry points: `scripts/load_susep_to_staging.py`, `scripts/reconcile_susep_source_to_fact.py`, V11–V14, `sql/09_load_susep_market_dwh.sql`, `sql/10_run_susep_quality_gate.sql`.
- Current Track B entry points: `scripts/load_brvehins1_to_staging.py`, V2–V10, `sql/04_load_canonical_dimensions.sql`, `sql/05_load_fact_risk_observation.sql`, `sql/07_run_quality_gate.sql`, và `ml/`.
- Current platform documents: `README.md`, `REPO_LEARNING_GUIDE.md`, `FINAL_PROJECT_GUIDE.md`, `docs/architecture/project-scope.md`, `source-strategy.md`, `overall-architecture.md`, run guide, roadmap và final report.
- Historical/stale scaffold: old customer/policy/premium/claims SQL examples. Không xóa hoặc thực thi chúng như một side effect; Track A đã có design/implementation evidence dựa trên CSV thật, không dựa scaffold cũ.

Raw data là immutable và ignored by Git. Artifacts/checkpoints là evidence: không rewrite runtime numbers cũ chỉ để lịch sử trông đồng nhất.
