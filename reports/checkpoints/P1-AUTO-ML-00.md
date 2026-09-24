# P1-AUTO-ML-00 — Kiểm tra foundation hiện hành

Ngày: 2026-09-23  
Kết luận: `PASS`

## Stage này giải quyết vấn đề gì?

Gate này bảo đảm các bước ML/Airflow bắt đầu từ foundation hiện tại, không
dựa nhầm vào tên scaffold lịch sử hoặc report cũ.

## Đã kiểm tra runtime gì?

`docker compose ps` xác nhận `insurance_sqlserver` đang chạy trên port 1433.
Kết nối SQL Server xác nhận:

| Kiểm tra | Kết quả |
|---|---:|
| Database | `DWH_Insurance` tồn tại và truy cập được |
| Schema đã áp dụng | V1 đến V8 |
| Canonical batch thành công | 5 |
| `stg.BrVehIns1` | 1,965,355 dòng |
| `dwh.FactRiskObservation` | 1,965,355 dòng |
| Chênh lệch staging–fact | 0 |
| Production DQ | `dq.sp_RunQualityGate` chạy thành công |

Object hiện hành gồm staging, ba dimension driver/vehicle/geography,
`FactRiskObservation` và quality gate. Không cần mô hình customer/policy lịch
sử.

## Phân loại artifact

| Phân loại | Artifact |
|---|---|
| CURRENT IMPLEMENTATION | V1–V8, loader canonical, entry point SQL, source contract, DWH design, DQ gate |
| STALE SCAFFOLD | CDC stub cũ, customer/policy SQL, code ML/DAG cũ |
| HISTORICAL | log cũ, SUSEP legacy, thiết kế Porto Seguro trước đây |
| FUTURE | ML training/scoring, Airflow runtime, performance, Power BI |

## Phát hiện quan trọng

- `brvehins1` là input canonical duy nhất; SUSEP không được dùng.
- Grain là aggregate risk observation; không có customer, policy, event time
  hoặc future-claim label đã chứng minh.
- Batch idempotency và fact rerun cần audit, không cần viết lại.
- SQL Server Developer Edition 16.0.4295.3 có CDC procedure; SQL Server Agent
  cần được bật trước demo CDC.
- Airflow image cần dependency ML/database riêng.

## Cách tự kiểm tra

1. Chạy `docker compose ps` và xác nhận SQL Server `Up`.
2. Query count staging/fact; cả hai phải là 1,965,355.
3. Chạy `EXEC dq.sp_RunQualityGate @RunLabel=N'manual-foundation-check';`.
4. Kiểm tra `meta.SchemaVersion` có V1–V8.

## Kết luận stage

`PASS`. Foundation đủ khỏe để audit incremental ingestion và làm synthetic
CDC demo cô lập.
