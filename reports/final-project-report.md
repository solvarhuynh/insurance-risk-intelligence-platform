# Báo cáo cuối — Insurance Data Platform

## 1. Executive summary

Repository hiện là **Insurance Data Platform** đa track, không phải một DWH single-track. Track A SUSEP Market DWH/Performance và Track B brvehins1 Risk/ML vận hành độc lập, có runtime evidence; Airflow đã kiểm tra happy path và controlled failure. Không có fake row-level join. Final verdict là **BLOCKED** chỉ vì Power BI Desktop/PBIP artifact và refresh không thể tạo/kiểm tra trong môi trường hiện có.

## 2. Final multi-track scope

| Track | Scope hiện hành | Status |
|---|---|---|
| A — SUSEP | Market staging, dimensions/fact, reconciliation, DQ, performance, Market BI semantic handoff | RUNTIME_PASS; BI artifact `BLOCKED_MANUAL` |
| B — brvehins1 | Risk staging/DWH/DQ, incremental/CDC demonstration, bounded ML, prediction store/scoring | RUNTIME_PASS |
| C — Prudential | Original underwriting intent, physical source absent | `ORIGINAL_PLANNED_SOURCE / NOT_PRESENT / FUTURE` |

## 3. Track A source và grain

Raw file `data/raw/susep.gov.br/insurance_dataset.csv` có 8.338.214 rows, 8 columns, 751.126.569 bytes. Grain được chứng minh là `company_code + year_month + product + state`; một row là market observation, không customer/policy/claim event. Contract: `docs/susep/source-data-contract.md`.

## 4. Track B source và grain

Năm `brvehins1[a-e].csv` có tổng 1.965.355 rows. Grain là aggregate motor-risk observation; technical identity là `SourceFile + SourceRowNumber`. Nó không có customer/policy identity. Contract: `docs/architecture/source-data-contract.md`.

## 5. Prudential status

Không có physical dataset trong repo. Không tải tự động, không tạo pipeline/Dim_Customer và không fake join với SUSEP. Giữ status future minh bạch.

## 6. Track-A reconciliation

Batch `0EDEB285-DB67-4159-A6D5-FE85F00F085A`:

```text
source rows   = 8,338,214
staging rows  = 8,338,214 accepted; 0 rejected
fact rows     = 8,338,214
premium total = 3,050,108,693,057.190700567726667268 (source = staging = fact)
claims total  =   735,517,715,559.682615627330218331 (source = staging = fact)
```

Same source fingerprint rerun trả `SKIPPED`, không duplicate.

## 7. Track-B reconciliation

`stg.BrVehIns1 = dwh.FactRiskObservation = 1.965.355`. Track-B production DQ pass; five canonical partitions và fact technical identity được giữ theo contract.

## 8. DWH architecture

Track A dùng `DimSusepMonth`, `DimSusepCompany`, `DimSusepProduct`, `DimSusepState` và `FactSusepInsuranceMarket`. Track B dùng `DimDriverProfile`, `DimVehicle`, `DimGeography`, `FactRiskObservation` và prediction store. Diagram chính xác: `docs/architecture/overall-architecture.md`. Không có FK/relationship giữa Track A/B.

## 9. Data Quality evidence

Track A production gate pass 14 hard rules; warning source characteristic gồm 116.980 premium âm, 301.382 claims âm, 5.167.094 source ratio NULL/NA và 238.088 ratio âm. Controlled `@InjectControlledFailure=1` fail thật nhưng không mutate canonical data. Track B production DQ pass theo checkpoint preflight.

## 10. Incremental / CDC clarification

SUSEP ingest idempotent theo source fingerprint, không giả là CDC stream. Track B có incremental batch behavior và synthetic CDC demonstration riêng; đó là demonstration có kiểm soát, không biến CSV lịch sử thành event feed thật.

## 11–14. ML contract, metrics, artifact và prediction reconciliation

ML chỉ thuộc Track B. `claim_risk_model_v001` là bounded cross-sectional `HasClaim` association, không future customer/policy probability. Held-out metrics: ROC-AUC **0,808815**, PR-AUC **0,513523**. Artifact reload PASS bằng scikit-learn **1.7.2**; host global version khác không là evidence hợp lệ. Batch scoring `bounded_held_out_test` có **20.000** predictions, duplicate technical identity **0**, rerun idempotent.

## 15–16. Performance baseline và improvements

SUSEP fact 8,3M rows là performance track chính. Q1 company/month: 317.528 → 3.364 logical reads (−98,94%). Q2 state/product/month: 317.528 → 3.734 (−98,82%). Giữ hai covering index có chứng cứ; source-hash trial không cải thiện và đã drop. Chi tiết/trade-off storage/write: `reports/performance-report.md` và `P1-PERF-01/02.md`.

## 17–18. Airflow valid runtime và controlled failure

Valid DAG run `44294f58-1808-4cd8-8a22-2c90687bf321` state `success`, 12/12 task success, khoảng 5 phút 33 giây. Controlled run `0d2f017a-1f52-46b2-9671-2f1e3d95f488` state `failed` đúng kỳ vọng: Track-A DQ failed (sau retry), Track-A consumer `upstream_failed`, Track-B consumer `success`. Đây là evidence independent orchestration, không phải regression. Chi tiết: `P1-ORCH-02.md`.

## 19–20. Power BI artifact và subject areas

Đã hoàn tất semantic model/handoff ở `docs/bi/semantic-model.md` và `powerbi/README.md`: Market subject area (SUSEP) và Risk/ML subject area (brvehins1) tách hoàn toàn, không cross-filter. Không có Power BI Desktop, PBIP hoặc `pbi-tools` supported runtime; không tạo `.pbix` giả. Status: **BLOCKED_MANUAL**.

## 21–22. Fresh environment và failure path evidence

Fresh temporary venv cài `requirements.txt`, import package và reload Pipeline PASS với sklearn 1.7.2. Failure tests đã chứng minh missing source path, invalid header, unavailable SQL port, duplicate rerun, SQL controlled DQ và Airflow propagation đều fail/succeed theo boundary an toàn. Chi tiết: `P1-E2E-01.md`, `P1-E2E-02.md`.

## 23. Known limitations

- Không có actual Power BI `.pbix`/PBIP artifact hay refresh evidence; manual GUI/toolchain là blocker duy nhất.
- Track B ML bị giới hạn deterministic bounded population do resource; không được diễn giải là full-data/future-policy production model.
- Prudential raw absent nên không có Track C runtime.
- Fresh test không reset database volume hiện có; destructive rebuild không an toàn trên instance evidence.

## 24. Historical artifacts retained

Historical reports/scaffold được giữ nguyên để bảo toàn audit history. Current docs đã realign multi-track; không rewrite lịch sử để che sự thay đổi kiến trúc.

### P1-DOC-03 stale-claim audit

Search các cụm như single canonical source, SUSEP legacy, Porto/Safe Driver, CustomerId/PolicyNumber và old prediction fact cho kết quả được phân loại như sau:

- **CURRENT_VALID:** `CustomerId`/`PolicyId` trong README, contract và guide là lệnh cấm fake entity; Prudential `FUTURE` là status hợp lệ.
- **HISTORICAL:** `AGENT_PROMPT_HISTORY.md`, `log/progress-log.md`, P1-REPO/P1-WF historical checkpoints và foundation report ghi scope cũ; được giữ nguyên để audit.
- **STALE_BUT_INTENTIONALLY_PRESERVED:** scaffold SQL customer/policy/premium/claims cũ; không phải maintained entry point và không được execute cho Track A/B.
- **BUG đã sửa:** current docs từng nói Airflow/SUSEP/performance là future hoặc chưa runtime; đã realign README, learning guide, source strategy, roadmap, run guide, repository structure và architecture explanation.

## 25. Important files

- `README.md`, `FINAL_PROJECT_GUIDE.md`
- `docs/architecture/overall-architecture.md`
- `docs/susep/*`, `scripts/load_susep_to_staging.py`, `scripts/reconcile_susep_source_to_fact.py`, V11–V14
- `ml/modeling.py`, `ml/predict_risk_batch.py`, `ml/artifacts/claim_risk_model_v001.*`
- `dags/insurance_dwh_pipeline.py`, `airflow/Dockerfile`
- `reports/checkpoints/P1-SUSEP-*`, `P1-PERF-*`, `P1-ORCH-*`, `P1-E2E-*`

## 26. Final architecture

Raw SUSEP → separate staging → Market DWH → reconciliation/DQ → performance/Market BI; raw brvehins1 partitions → separate staging → Risk DWH → DQ → bounded ML/predictions → Risk BI. Airflow orchestrates both branches independently. Detailed eight-diagram architecture is in `docs/architecture/overall-architecture.md`.

## 27. Remaining manual work

Install/use Power BI Desktop or an approved PBIP toolchain, create two disconnected subject-area pages/models, refresh against SQL Server, reconcile measures to SQL, then save a real artifact. Do not create a cross-track relationship.

## 28. Final git status

Working tree was already dirty trước task và vẫn intentionally uncommitted. Existing changes được preserve; không có reset, clean, stash, restore, commit hay push. Final status gồm current-document/runtime files đã sửa/cập nhật và historical user changes từ trước; exact list được ghi cuối `log/progress-log.md`.

## 29. Final verdict

**BLOCKED — MANUAL_POWER_BI.** All non-BI finalization gates have runtime/static evidence; standards are not lowered to claim COMPLETE without an actual Power BI artifact and refresh validation.

## Final static validation

`98 PASSED | 0 FAILED | 9 SKIPPED` bằng `.\.venv\Scripts\python.exe scripts\validate_repo.py`. `SKIPPED` chỉ là runtime categories mà static validator cố ý không chứng nhận; runtime evidence nằm trong checkpoints. `py_compile`, `docker compose --profile orchestration config -q` và `git diff --check` cũng PASS (line-ending warning chỉ là Git warning, không phải whitespace error).
