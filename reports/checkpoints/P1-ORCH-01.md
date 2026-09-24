# P1-ORCH-01 — Airflow architecture thực thi đa track

## Stage này giải quyết vấn đề gì?

Biến hai pipeline đã có thành một orchestration runtime thật mà vẫn giữ biên giới data. **Orchestration** nghĩa là điều phối thứ tự/cổng thực thi, giống điều hành sân bay; nó không phải lý do để trộn hành khách của hai chuyến bay thành một danh sách.

## Trước stage này project thiếu gì?

Track A và Track B có evidence runtime riêng, nhưng chưa có Airflow Docker environment chứng minh chúng có thể được gọi bằng DAG hiện hành. Một DAG parse được cũng chưa là runtime pass.

## Agent đã sửa những file nào?

- `airflow/Dockerfile`: image Airflow cài dependency có retry/timeout và xử lý GPG noninteractive.
- `airflow/requirements.txt`: pin NumPy 1.26.4, scikit-learn 1.7.2, joblib 1.5.2 cho container.
- `docker-compose.yml`: profile `orchestration`, mount raw read-only/scripts/ML, và `SQLSERVER_HOST=sqlserver,1433`.
- `dags/insurance_dwh_pipeline.py`: DAG `insurance_data_platform` với hai nhánh độc lập.
- `ml/modeling.py`: nhận `SQLSERVER_HOST` để container kết nối đúng SQL Server.

## Data/code đi qua đâu?

```text
platform_start
 ├─ Track A: ingest SUSEP → market DWH → raw-to-fact reconciliation → SUSEP DQ → market consumer ready
 └─ Track B: foundation precheck → incremental audit → risk DQ → held-out scoring → prediction reconciliation → risk consumer ready
```

Không có edge `Track A → Track B` hay SQL join giữa source. `schedule=None` để không tự chạy theo lịch với run id/semantics không hợp lệ; operator trigger bằng run id có chủ đích.

## Runtime evidence là gì?

- Airflow container đọc DAG không có import error.
- SQL Server reachable từ Airflow bằng `sqlserver,1433`.
- DAG gọi maintained loader/reconciler/scorer, không copy business logic vào operator.
- `track_a_quality_gate` và `track_b_quality_gate` drain toàn bộ result set của stored procedure. Điều này quan trọng vì SQL Server có thể trả rowset trước `THROW`; nếu không drain, pyodbc có thể báo false success dù DQ procedure đã fail.

## Owner cần hiểu khái niệm gì?

- **DAG:** đồ thị task có hướng; arrow là prerequisite, không phải database join.
- **Failure propagation:** upstream hard failure làm downstream phụ thuộc không chạy.
- **Idempotent task:** loader/scorer được gọi lại theo contract mà không silent duplicate.

## Owner chưa cần học gì?

Chưa cần Kubernetes, distributed executor hay scheduling cron. Runtime này dùng `SequentialExecutor` để evidence local dễ kiểm soát.

## Owner tự kiểm tra thế nào?

```powershell
docker compose --profile orchestration up -d --build
docker compose exec -T airflow airflow dags list-import-errors --output plain
docker compose exec -T airflow airflow dags list -o plain
```

## Điều gì có thể nhìn đúng nhưng thực ra sai?

`airflow dags list` hoặc `py_compile` PASS chỉ chứng minh parse. Task phải gọi SQL/Python thật mới chứng minh path, credentials, mounts và dependency. Tương tự, SQL `THROW` không được coi là propagated nếu pyodbc chưa consume result set cuối.

## Stage verdict

**PASS.** Airflow runtime architecture đúng multi-track, path/SQL dependency đã kiểm tra trong container và không có fake data dependency.
