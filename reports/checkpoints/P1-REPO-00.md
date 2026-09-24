# P1-REPO-00 — Repository Understanding Report

Date: 2026-09-23

Result: `PASS`

Scope: read-only repository onboarding. This report is the only project file
created or changed for Stage 0. Raw data, source code, SQL, configuration,
containers, database state and progress history were not changed.

## 1. Project purpose

The project is a Motor Insurance Data Warehouse for Brazilian vehicle
insurance observations. The current canonical objective is a verifiable
foundation for exposure, premium, insured value and claim analysis:

```text
immutable brvehins1 CSV
  -> typed SQL Server staging with batch and row lineage
  -> descriptor dimensions and one-row-per-source-observation fact
  -> executable data-quality gate
```

The foundation is documented as runtime-proven in the latest checkpoints.
Incremental/CDC, ML, Airflow, performance tuning and Power BI remain later
milestones. A source row is an aggregate risk observation, not a proven
customer, policy or claim event.

## 2. Repository map

| Area | Responsibility | Current understanding |
|---|---|---|
| `data/raw/` | Immutable source files | Canonical `brvehins1` plus preserved legacy SUSEP file; ignored by Git. |
| `scripts/` | Static validation, profiling and staging loader | `validate_repo.py`, streaming EDA/profiling and canonical ODBC loader. |
| `notebooks/` | EDA presentation layer | `01-eda.ipynb` reads saved evidence; it is not the runtime ingest path. |
| `migrations/` | Versioned SQL Server schema changes | V1–V8 implement foundation bootstrap, staging, dimensions, fact and DQ. |
| `sql/` | Runtime entry points and historical SQL scaffolds | Four canonical entry points are current; several numbered files remain legacy scaffolds. |
| `docs/architecture/` | Architecture, dictionary, contract, staging and DWH design | Mostly current, with a few stale status statements. |
| `docs/guides/` | Run guide and glossary | Current foundation operating guidance. |
| `docs/specs/` | Implementation guide and roadmap | Implementation guide is current; roadmap contains a stale progress snapshot and is ignored locally. |
| `reports/` | Checkpoints and machine-readable evidence | Latest evidence covers foundation through DQ. |
| `log/` | Append-only project history | Contains historical scaffold entries and later foundation entries. |
| `ml/` | Future model training and scoring | Old Porto/customer scaffold only. |
| `dags/` | Future Airflow orchestration | Old customer/policy stub DAG only. |
| `powerbi/` | Future BI artifact | Placeholder only; no `.pbix`. |
| `.cursor/rules/` | Project workflow and handoff rules | Five tracked rule files; generally applicable with noted vocabulary/path drift. |
| `docker-compose.yml` | Local SQL Server and optional Airflow services | SQL Server foundation is reported runtime-proven; Airflow is deferred. |

`REPO_LEARNING_GUIDE.md` is a current explanatory guide and explicitly says
that the latest foundation evidence outranks stale README status text.

## 3. Current canonical data

The filesystem was checked for names, sizes and headers without loading the
full dataset in Stage 0.

| Source file | Size | Header/result | Classification |
|---|---:|---|---|
| `data/raw/brvehins1/brvehins1a.csv` | 60,499,054 bytes | 23-column canonical header | CURRENT_CANONICAL |
| `data/raw/brvehins1/brvehins1b.csv` | 60,497,433 bytes | Same header | CURRENT_CANONICAL |
| `data/raw/brvehins1/brvehins1c.csv` | 60,481,086 bytes | Same header | CURRENT_CANONICAL |
| `data/raw/brvehins1/brvehins1d.csv` | 60,491,192 bytes | Same header | CURRENT_CANONICAL |
| `data/raw/brvehins1/brvehins1e.csv` | 60,501,172 bytes | Same header | CURRENT_CANONICAL |
| `data/raw/susep.gov.br/insurance_dataset.csv` | 751,126,569 bytes | `company_code,...,claim_premium_ratio` | LEGACY / NON-CANONICAL |

The canonical header is:

`Gender, DrivAge, VehYear, VehModel, VehGroup, Area, State, StateAb, ExposTotal, ExposFireRob, PremTotal, PremFireRob, SumInsAvg, ClaimNbRob, ClaimNbPartColl, ClaimNbTotColl, ClaimNbFire, ClaimNbOther, ClaimAmountRob, ClaimAmountPartColl, ClaimAmountTotColl, ClaimAmountFire, ClaimAmountOther`.

Existing P1-DATA-01 evidence reports 393,071 data rows per partition and
1,965,355 total rows, 14 exact logical duplicates, and no numeric negatives.
Those row counts are inherited evidence; this Stage 0 pass did not rescan all
rows. Raw files are not to be modified, staged from the legacy source, or
committed.

## 4. Architecture as currently documented

The current contract and foundation reports define:

1. Raw `brvehins1` as immutable, partitioned source input.
2. `stg.BrVehIns1` as typed staging with `BatchId`, `SourceFile`,
   `SourceRowNumber`, `SourceRecordHash` and load timestamp.
3. `dwh.DimDriverProfile`, `dwh.DimVehicle` and `dwh.DimGeography` as
   descriptor-group dimensions, not master entities.
4. `dwh.FactRiskObservation` at one source-row grain, preserving all source
   measures and lineage.
5. `dq.sp_RunQualityGate` as a hard gate for schema, reconciliation, numeric,
   geography, fact-grain, FK, lineage and ratio rules.
6. File-level idempotency as implemented incremental behavior. CDC is not
   proven and is not implied by the static source partitions.
7. ML, orchestration, performance and BI only after the foundation contract
   and DQ evidence.

The model deliberately does not create `CustomerId`, `PolicyNumber`,
`Dim_Customer`, `Dim_Policy`, SCD2 history, date dimension or separate premium
and claims facts because the source has no evidence for those semantics.

## 5. Architecture encoded by current scaffold and implementation

### Current implementation

- `migrations/V1__create_dwh_schema.sql`: database, schemas, manifests and
  audit metadata.
- `migrations/V2__create_staging_schema.sql` through V5: typed staging,
  loader registration, removal of the unsupported landing experiment and
  observed decimal precision.
- `migrations/V6__create_canonical_dimensions.sql`: three current dimensions
  and deterministic loader.
- `migrations/V7__create_fact_risk_observation.sql`: current one-row-per-source
  fact and loader.
- `migrations/V8__create_data_quality_gate.sql`: executable DQ log and gate.
- `scripts/load_brvehins1_to_staging.py`: RFC-aware streaming, contract
  validation, lineage and idempotent partition loading.
- `sql/01_load_staging.sql`, `sql/04_load_canonical_dimensions.sql`,
  `sql/05_load_fact_risk_observation.sql` and `sql/07_run_quality_gate.sql`:
  current SQL entry points.

The latest checkpoint set and `reports/foundation-50pct-report.md` report
runtime evidence: five successful batches, staging total 1,965,355, three
dimensions, fact total 1,965,355, zero FK or lineage issues, idempotent reruns
and a controlled DQ failure that raises SQL error 51040 without changing data.

### Stale scaffold

- `sql/02_enable_cdc.sql` assumes `stg_susep_raw` and
  `stg_portoseguro_raw`.
- `sql/03_sp_dim_customer_scd2.sql` assumes `CustomerId` and SCD2.
- `sql/04_sp_dim_others.sql` assumes policy, date and region objects.
- `sql/05_sp_fact_premium.sql` and `sql/06_sp_fact_claims.sql` assume
  separate legacy facts and customer/policy keys.
- `sql/07_data_quality_checks.sql` assumes the legacy fact model.
- `sql/08_sp_load_risk_predictions.sql` assumes customer/date scoring.
- `ml/*.py` contains no real training or scoring; it retains Porto Seguro,
  `ps_*`, `train.csv`, customer and unsupported metric assumptions.
- `dags/insurance_dwh_pipeline.py` contains Python/Airflow stubs for the
  same old customer/policy/premium/claims graph.

## 6. Documentation and code contradictions

| Artifact/evidence | Classification | Contradiction or interpretation |
|---|---|---|
| `README.md` | MIXED: current source intent, stale status | It correctly names `brvehins1`, but still says DWH/DQ are stale scaffolds even though V6–V8 and later checkpoints report runtime evidence. |
| `docs/specs/roadmap.md` | STALE SNAPSHOT / PARTLY CURRENT TARGET | The target sequence is useful, but its final section still says P1-WF-04 is next. The file is ignored locally by the personal Git ignore rule. |
| `docs/architecture/architecture-explained.md` | MIXED | It correctly describes the current contract but still labels broad SQL/migration business work as stale, without reflecting V2–V8 fully. |
| `docs/architecture/data-dictionary.md`, `source-data-contract.md`, `staging-design.md`, `dwh-design.md` | CURRENT | These define the 23-column contract, technical grain, current dimensions/fact and DQ boundaries. |
| `docs/guides/how-to-run.md` and `glossary.md` | CURRENT FOUNDATION GUIDE | They distinguish static/runtime status and warn against running legacy SQL; they do not constitute Airflow/ML runtime evidence. |
| `docs/reports/*` | SCAFFOLD/FUTURE | Insights and performance reports intentionally contain no unproven business results. |
| `log/progress-log.md` | HISTORICAL plus latest status | Early rows say old scaffold tasks were “Done”; the later append-only entries correctly record the canonical foundation and runtime evidence. Old rows are not current runtime proof. |
| `reports/checkpoints/P1-REPO-00.md` before this pass | STALE CHECKPOINT | It described the repository before the committed V1–V8 foundation completion. This report supersedes that understanding. |
| `docs/specs/insurance-dwh-overview.pdf` | HISTORICAL / UNKNOWN | It is a 55,401-byte binary from the initial scaffold period; no reliable current-architecture authority was established from it. |

The repository-wide legacy search was classified as follows:

- `log/`, old reports and explicit warnings in current docs: `HISTORICAL` or
  `VALID_GENERAL_REFERENCE`.
- `sql/02`, `sql/03`, `sql/04_sp_dim_others.sql`, `sql/05_sp_fact_premium.sql`,
  `sql/06_sp_fact_claims.sql`, `sql/07_data_quality_checks.sql`, `sql/08`,
  `ml/` and `dags/`: `STALE_SCAFFOLD`.
- The legacy SUSEP file and explicit non-canonical boundary statements:
  `HISTORICAL` / `CURRENT_CANONICAL_BOUNDARY`, not pipeline input.
- `Porto Alegre` in the profiled canonical data is a geographic source value,
  `VALID_GENERAL_REFERENCE`; it is not evidence that Porto Seguro is current.
- `scripts/validate_repo.py` contains legacy terms intentionally as a guard
  against their reappearance in current documentation; this is
  `VALID_GENERAL_REFERENCE` in validator logic.

## 7. Current subsystem status

| Subsystem | Status | Evidence | Main problem | Required next step |
|---|---|---|---|---|
| Governance | DONE with documentation drift | Five rules; latest foundation checkpoints | README/roadmap snapshots disagree with latest foundation | Normalize status text in a later documentation task. |
| Raw data | RUNTIME_PASS by existing evidence | Five files/header check; P1-DATA-01 count/profile evidence | Raw is local and Git-ignored; legacy source remains visible | Preserve immutability and canonical boundary. |
| Validation | STATIC_PASS / REQUIRES REFACTOR | `validate_repo.py`; latest evidence reports 55 PASS, 0 FAIL, 8 runtime-scope SKIPPED | Checks structure/header, not live SQL/DWH; required legacy file is environment-specific | Keep static checks separate from runtime certification; align required-file policy. |
| EDA | RUNTIME_PASS | `reports/data/*`, 1,965,355-row streaming profile | Notebook is a presentation/evidence reader rather than an executed notebook artifact | Reuse evidence; do not rescan unless contract changes. |
| Data Contract | DONE | `source-data-contract.md`, `data-dictionary.md`, P1-DATA-02 | Future ML time semantics remain unresolved | Define a separate ML contract before training. |
| Docker | RUNTIME_PASS for SQL Server foundation; Airflow deferred | Compose plus P1-INFRA evidence | Stage 0 did not recheck live services; raw is mounted read-only | Revalidate only in a scoped runtime task. |
| SQL Server | RUNTIME_PASS by checkpoint evidence | `DWH_Insurance`, schemas and sqlcmd evidence in P1-INFRA | No fresh live check was performed in Stage 0 | Preserve idempotent migrations and runtime evidence. |
| Migration | RUNTIME_PASS for V1–V8 by existing evidence | Versioned files and foundation report | No external migration runner; execution is sqlcmd-based | Document/automate migration ordering if needed. |
| Staging | RUNTIME_PASS | Five successful batches, source/staging reconciliation, rerun skip | Loader depends on host ODBC Driver 18 and environment credentials | Keep loader as canonical ingest path. |
| DWH | RUNTIME_PASS | V6 dimensions, V7 fact, counts/FK/reconciliation/rerun evidence | README still reports it as stale | Align documentation; do not restore customer/policy objects. |
| DQ | RUNTIME_PASS | V8 production PASS and controlled failure evidence | Legacy DQ file remains beside the current gate | Retain V8 as canonical gate; refactor/remove legacy logic only in scope. |
| Incremental/CDC | PARTIAL | File-batch idempotency is proven; CDC file is old scaffold | Static partitions do not prove source CDC history | Next safe milestone is an explicitly synthetic CDC demonstration. |
| ML | STALE_SCAFFOLD / NOT TRAINED | Stub functions and no model artifact or metrics | Old Porto/customer/leakage assumptions; no frozen ML target/time semantics | Create ML contract and leakage-safe baseline after scope approval. |
| Airflow | STATIC_PASS / STALE_SCAFFOLD | DAG syntax evidence only | Operators are stubs; old graph; no provider/hook or DAG runtime evidence | Refactor against current entry points, then run in orchestration profile. |
| Performance | SCAFFOLD | Template report only | No measured query, plan, IO or timing evidence | Benchmark current fact queries after scope is selected. |
| Power BI | SCAFFOLD | `powerbi/.gitkeep` only | No `.pbix` or semantic model | Build only after stable analytical contract. |

## 8. Stale artifacts to preserve

Do not delete these during onboarding:

- `sql/02_enable_cdc.sql`
- `sql/03_sp_dim_customer_scd2.sql`
- `sql/04_sp_dim_others.sql`
- `sql/05_sp_fact_premium.sql`
- `sql/06_sp_fact_claims.sql`
- `sql/07_data_quality_checks.sql`
- `sql/08_sp_load_risk_predictions.sql`
- `ml/train_risk_model.py`
- `ml/predict_risk_batch.py`
- `dags/insurance_dwh_pipeline.py`
- The historical portions of `log/progress-log.md`, `docs/specs/roadmap.md`
  and `docs/specs/insurance-dwh-overview.pdf`.

They are historical/scaffold artifacts, not current business requirements.

## 9. Rules that must be respected

- `.cursor/rules/01...`: read source-of-truth files first, keep one scoped
  task, do not invent data/metrics, preserve structure and validate honestly.
- `02...`: use canonical paths, do not commit raw/secrets/models, avoid
  parallel files, and append rather than rewrite progress history.
- `03...`: run proportionate static checks, distinguish static from runtime,
  inspect Git before commit, and avoid broad staging commands.
- `04...`: use maintainable typed Python, relative/configured paths, and avoid
  leakage; current ML/DAG stubs do not satisfy the intended implementation
  standard.
- `05...`: keep `docs/guides/how-to-run.md` canonical and document runtime
  status honestly. Its status vocabulary omits some project terms such as
  `DONE` and `FAILED`; this is a minor rule/documentation gap.

Canonical paths are `log/progress-log.md`, `docs/guides/how-to-run.md`,
`reports/checkpoints/`, `data/raw/`, `migrations/`, `sql/`, `ml/`, `dags/` and
`powerbi/`. No rule requires preserving the superseded SUSEP + Porto business
model. The Stage 0 instruction to change only this report takes precedence over
the normal per-task progress-log append rule for this pass.

## 10. Existing user changes

Pre-flight Git state:

```text
Branch: main
git status --short: clean
git diff: empty
git diff --stat: empty
```

There were no tracked or normally visible uncommitted user changes to
preserve. Read-only `git status --ignored` also showed local ignored state:
`.env`, `.venv/`, `.tmp-dependency-check-20260922/`, raw CSV directories,
Python `__pycache__/`, `AGENT_PROMPT_HISTORY.md` and the ignored roadmap. These
were not modified or cleaned.

## 11. Current blockers

Evidence-based blockers for future work are:

1. Incremental/CDC scope is not frozen; file idempotency exists, but the
   source is static and no real source-change history is available.
2. ML has no approved target/time semantics, leakage policy implementation,
   training run, artifact or metrics.
3. Airflow has no current canonical DAG or runtime/provider evidence.
4. README, roadmap and some architecture status statements lag the committed
   foundation evidence.
5. Performance and Power BI have no runtime/data artifacts.

These do not block repository understanding or invalidate the completed
foundation. They block claiming an end-to-end ML/Airflow/BI platform.

## 12. Recommended execution sequence

The requested sequence

```text
P1-WF-04 -> P1-DATA-01 -> P1-DATA-02 -> P1-INFRA
-> P1-INGEST -> P1-DWH -> P1-DQ
```

was valid historically but is no longer the current next-step sequence.
Existing evidence records every item through P1-DQ-03 as complete, with the
foundation milestone `P1-AUTO-FOUNDATION-01` marked `DONE`.

The exact next safe implementation task is:

```text
P1-INC-02 — Synthetic CDC demonstration
```

It must be explicitly labeled an engineering demonstration, not historical
CDC from `brvehins1`, and should begin by freezing the required incremental
scope. If CDC is not a project requirement, stop before coding and select the
next milestone deliberately; do not jump directly to the stale ML or Airflow
scaffolds.

## Repository understanding gate answers

1. **Business domain:** Brazilian motor insurance analytics and DWH foundation.
2. **Canonical dataset:** `data/raw/brvehins1/brvehins1a.csv` through `e.csv`.
3. **Physical raw files:** the five canonical CSVs listed in Section 3, plus
   the legacy CSV.
4. **Legacy source:** `data/raw/susep.gov.br/insurance_dataset.csv`.
5. **Why superseded:** SUSEP + Porto assumed separate sources, customer/policy
   identities and SCD2 semantics absent from the 23-column canonical source.
6. **Current documentation:** source contract, dictionary, staging/DWH design,
   run guide, learning guide and latest checkpoint/runtime evidence.
7. **Stale documentation:** old roadmap snapshot, mixed README status,
   historical log rows, initial PDF and stale portions noted in Section 6.
8. **Old SQL:** the legacy `sql/02`–`sql/03`, `sql/04_sp_*`, `sql/05_sp_*`,
   `sql/06`, `sql/07_data_quality_checks.sql` and `sql/08` files.
9. **DWH runtime proof:** yes, foundation raw-to-staging-to-DWH-to-DQ is
   supported by the latest checkpoint evidence; Airflow is not proven.
10. **ML runtime proof:** no; the model is not trained or validated.
11. **Airflow status:** syntax/static scaffold only, not operational.
12. **Validator behavior:** checks required files, dependency manifests,
   Git-ignore rules, canonical headers, current-doc legacy terms, Compose
   parsing, Python compilation, notebook JSON and SQL block-comment balance;
   it explicitly skips live Docker, SQL, DWH, DQ, Airflow and ML execution.
13. **Applicable rules:** all five `.cursor/rules/*.mdc`, with the gaps in
   Section 9.
14. **Conflicting rules:** no rule requires the old business architecture;
   minor conflicts are task-ID/status vocabulary drift and ignored roadmap
   path drift.
15. **Pre-existing modifications:** none in normal Git status; ignored local
   files are recorded in Section 10 and were preserved.
16. **Exact next safe task:** `P1-INC-02`, only as a synthetic CDC engineering
   demonstration with explicit non-production/source-history labeling.

## Gate conclusion

All required repository areas were inspected: current documentation, rules,
history, scripts, migrations, SQL, ML, DAG, notebook, Docker/configuration,
raw-data presence, legacy references and existing Git state. The stale/current
boundary is understood and every gate question is supported by repository
evidence.

**REPOSITORY UNDERSTANDING GATE: PASS**

Canonical dataset: `brvehins1` (five CSV partitions)

Current project stage: foundation complete through P1-DQ-03

Major stale architecture: SUSEP + Porto customer/policy/SCD2/legacy-fact/ML/Airflow scaffold

Runtime status: raw profile, SQL Server foundation, staging, DWH and DQ have existing runtime evidence; ML and Airflow do not

Next stage: `P1-INC-02` synthetic CDC demonstration, subject to explicit scope freeze
