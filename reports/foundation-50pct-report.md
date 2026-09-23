# Báo cáo foundation 50% — P1-AUTO-FOUNDATION-01

Ngày hoàn tất: 2026-09-22

Kết quả: `DONE` — toàn bộ stage từ P1-WF-04 đến P1-DQ-03 đã PASS.

## 1. Điểm xuất phát và nguồn canonical

Repository bắt đầu với scaffold cũ SUSEP + Porto Seguro, nhiều SQL/ML/DAG chỉ static hoặc commented stub. Nguồn canonical thực tế là năm file bất biến `data/raw/brvehins1/brvehins1[a-e].csv`; `data/raw/susep.gov.br/insurance_dataset.csv` được giữ lại nhưng là LEGACY / NON-CANONICAL và không được pipeline dùng.

Năm partition đều có 393,071 dòng; tổng source là **1,965,355** dòng và schema chung có 23 cột: driver (`Gender`, `DrivAge`), vehicle (`VehYear`, `VehModel`, `VehGroup`), geography (`Area`, `State`, `StateAb`), exposure/premium/sum insured và năm cặp claim count/amount.

## 2. EDA, contract và grain

EDA streaming xác nhận 14 logical duplicate, 0 numeric negative, 51,762 dòng exposure/premium bằng 0, 8 `VehYear=0`, và State/StateAb không mâu thuẫn. Duplicates được giữ nguyên, không deduplicate raw.

Grain đã đóng băng là **một source-delivered aggregate risk observation**. Không có customer ID, policy ID, transaction timestamp hay claim-event ID trong source. Technical identity là `(SourceFile, SourceRowNumber)`; `SourceRecordHash` chỉ là audit fingerprint. Precision lexical được giữ: `ExposTotal DECIMAL(21,17)` và `PremTotal DECIMAL(34,27)`.

## 3. Runtime database, staging và ingest

SQL Server Docker `insurance_sqlserver` đang Up; database `DWH_Insurance` có schemas `meta`, `stg`, `dwh`, `dq`. Migrations V1–V8 đã thực thi an toàn theo thiết kế idempotent.

Staging `stg.BrVehIns1` giữ toàn bộ 23 field source cùng Batch/source lineage. Python streaming loader dùng RFC-aware CSV parser, không sửa raw. Có năm successful batch, mỗi batch 393,071 row, rejected 0; total staging và technical identity distinct đều **1,965,355**. Rerun partition A/E trả `SKIPPED`, không duplicate.

## 4. DWH model và reconciliation

Model hiện hành chỉ có `DimDriverProfile`, `DimVehicle`, `DimGeography` và `FactRiskObservation`; không tạo Customer, Policy, SCD2, Date hay claim-event giả.

- Driver dimension: 24 source tuple + 1 unknown technical member = 25.
- Vehicle dimension: 25,092 source tuple + 1 unknown = 25,093.
- Geography dimension: 42 source tuple + 1 unknown = 43.
- Fact: 1,965,355 row, đúng một row cho một staging source row.

Mỗi dimension có natural hash distinct bằng row count. Fact foreign-key orphan = 0, duplicate grain = 0, batch lineage mismatch = 0, staging-to-fact difference = 0. Rerun dimensions và fact đều insert 0 row.

## 5. Data Quality và failure test

Quality gate `dq.sp_RunQualityGate` kiểm tra schema, partition reconciliation, technical identity, null expectation, measures non-negative, State mapping, claim count/amount pairing, ratio hữu hạn, fact reconciliation, FK, grain, batch lineage và dimension uniqueness. Production run PASS tất cả hard rule; 14 logical duplicate là warning audit được chấp thuận.

Controlled test gọi gate với `@InjectControlledFailure=1`. Nó ghi `CONTROLLED_INVALID_INPUT=FAIL`, trả SQL error 51040/exit code 1, và không đổi raw, staging hoặc fact. Production rerun sau test PASS. Đây là chứng minh load → DQ → fail thì dừng.

## 6. Dependency boundary

`requirements.txt` chứa host runtime tối thiểu `numpy==2.4.6`, `pandas==3.0.3`, `pyodbc==5.3.0`; `requirements-dev.txt` thêm `PyYAML==6.0.3` và `jupyterlab==4.6.4`. Clean virtual environment Python 3.12.6 đã install/import thành công. Airflow được cô lập trong image Docker, không được cài vào host Python.

## 7. Final validation

- `python scripts/validate_repo.py`: **55 PASSED, 0 FAILED, 8 SKIPPED** (các runtime scope được static validator cố ý không claim).
- `python -m py_compile` trên maintained scripts/ML/DAG: PASS.
- `git diff --check`: PASS.
- `docker compose ps`: SQL Server Up trên port 1433.
- SQL object inventory, staging/fact reconciliation và production DQ: PASS.

## 8. Stage status

P1-WF-04, P1-DATA-01, P1-DATA-02, P1-INFRA-01/02, P1-INGEST-01/02/03, P1-INFRA-DEPS, P1-DWH-01/02/03, P1-DQ-01/02/03 đều `PASS`/`RUNTIME_PASS` theo checkpoint tương ứng.

## 9. Files thay đổi và stale artifacts còn lại

Các artifact nền tảng mới/chỉnh sửa gồm migrations V1–V8, canonical loaders, profiler, manifests Python, source/staging/DWH/dependency docs, DQ entry point, checkpoints và progress log. SQL/ML/DAG mang tên architecture cũ như `03_sp_dim_customer_scd2.sql`, `05_sp_fact_premium.sql`, `06_sp_fact_claims.sql`, `08_sp_load_risk_predictions.sql`, `ml/` và `dags/` vẫn là STALE SCAFFOLD — REQUIRES REFACTOR; chúng không được chạy trong foundation này.

Working tree vẫn dirty vì thay đổi foundation và các thay đổi pre-existing của user được preserve. Không có commit, push, reset, stash hay raw-data deletion. Virtual environment tạm `.tmp-dependency-check-20260922/` còn untracked vì policy runtime chặn lệnh xóa chính xác; nó không thuộc source/manifest và nên được xóa cục bộ sau khi không cần.

## 10. Hạn chế và bước khuyến nghị tiếp theo

Foundation dừng đúng scope: chưa chạy CDC, ML, Airflow orchestration, performance tuning hay Power BI. Bước tiếp theo nên là milestone riêng `P1-INC-02` hoặc refactor orchestration sau khi xác định yêu cầu incremental thực tế; không suy diễn CDC/SCD2 từ năm partition nguồn.

## What I need to understand before continuing

- **Raw:** năm CSV nguyên gốc ở `data/raw/brvehins1/`; ví dụ row A-1 không bị pipeline viết lại. Raw tồn tại để luôn có bằng chứng source.
- **Staging:** `stg.BrVehIns1` là raw đã parse đúng kiểu cộng `SourceFile`/`SourceRowNumber`; nó giúp đối chiếu row A-1 đã vào database chưa.
- **Grain:** “một row nghĩa là gì”. Ở đây là một aggregate risk observation, không phải một khách hàng hay policy.
- **Dimension:** danh mục lặp lại để phân tích. Ví dụ `DimVehicle` giữ tuple model/group/year, không tuyên bố đó là một chiếc xe duy nhất.
- **Fact:** bảng measure tại grain đã chốt. `FactRiskObservation` chứa premium, exposure và claim của đúng một staging row.
- **Surrogate key:** key kỹ thuật warehouse, như `VehicleKey`; nó liên kết fact với dimension mà không bịa VIN/customer ID.
- **Idempotency:** chạy lại không thay đổi kết quả. Ví dụ rerun `brvehins1e.csv` là `SKIPPED`; rerun fact insert 0 row.
- **Reconciliation:** so sánh số lượng giữa các lớp. Ví dụ source = staging = fact = 1,965,355.
- **Data Quality Gate:** hàng rào sau load. Ví dụ controlled invalid input làm procedure ném SQL error, còn production source hợp lệ PASS.
