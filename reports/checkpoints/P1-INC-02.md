# P1-INC-02 — Demo CDC tổng hợp

Ngày: 2026-09-23  
Kết luận: `RUNTIME_PASS`

## Stage này giải quyết vấn đề gì?

File `brvehins1` là static snapshot, nên không thể chứng minh natural source
change history. Stage này chứng minh SQL Server Change Data Capture (CDC) như
một capability kỹ thuật cô lập, không giả vờ rằng source có lịch sử thay đổi
và không bật CDC trên fact canonical.

## File đã thay đổi

| File | Vai trò |
|---|---|
| `docker-compose.yml` | bật SQL Server Agent để chạy CDC capture/cleanup jobs |
| `migrations/V9__create_synthetic_cdc_demo.sql` | bật CDC và tạo object demo/consumer trong `meta` |
| `sql/02_enable_cdc.sql` | entry point kiểm tra hiện hành, thay stub SUSEP/Porto |
| `scripts/run_synthetic_cdc_demo.py` | tạo thay đổi demo, đợi capture, kiểm tra LSN và replay |
| `reports/data/p1-inc-02-cdc-demo.json` | runtime evidence dạng machine-readable |

Không có raw CSV, staging, dimension hoặc `FactRiskObservation` nào bị sửa.
Foundation fact vẫn là 1,965,355 dòng.

## Luồng demo

```text
meta.CdcDemoOperationalRecord
  initial INSERT → synthetic UPDATE → synthetic INSERT
        ↓ SQL Server Agent capture
cdc.meta_CdcDemoOperationalRecord_CT
        ↓ ledger consumed-event + LSN watermark
meta.CdcDemoConsumedChange / meta.CdcConsumerWatermark
```

Bảng nguồn nằm trong `meta`; mỗi row có `DemoRunId` và ghi chú P1-INC-02.
Nó không thuộc fact pipeline.

## Runtime evidence

SQL Server Developer Edition 16.0.4295.3 hỗ trợ CDC. Sau khi bật compose,
`SQL Server Agent (MSSQLSERVER)` ở trạng thái `Running`, CDC được bật cho
`DWH_Insurance` và capture instance tồn tại.

| Item | Kết quả |
|---|---|
| Demo run | `f82755d1-1082-4f93-9e85-20a582738675` |
| CDC changes captured | 4 |
| Insert (`__$operation = 2`) | 2 |
| Update-before (`__$operation = 3`) | 1 |
| Update-after (`__$operation = 4`) | 1 |
| Captured LSN | `0x000000d6000177780007` |
| Lần consume đầu | 4 change mới |
| Replay lần hai | 0 change mới |
| Consumer watermark | `0x000000d6000177780007` |

Lần chạy đầu phát hiện lỗi expression parameter trước bước consume; chỉ tạo
demo row được đánh dấu. Script được sửa một lần và fresh run thứ hai PASS.
Canonical pipeline không bị ảnh hưởng.

## Watermark và idempotency

`meta.CdcConsumerWatermark` lưu `__$start_lsn` cao nhất đã consume.
`meta.CdcDemoConsumedChange` lưu identity đầy đủ
`(ConsumerName, StartLsn, SequenceValue, OperationCode)` bằng primary key.
Ledger là replay guard chính; watermark là marker tiến độ gọn. Kết hợp này xử
lý được nhiều event cùng LSN.

## Thuật ngữ cần hiểu

- **CDC** → SQL Server chép insert/update/delete từ transaction log vào capture
  table; giống camera giao hàng, không phải chỉ là timestamp.
- **LSN** → vị trí change trong transaction log; giống số serial.
- **Watermark** → bookmark change position cuối consumer ghi nhận.
- **Idempotent consumer** → replay cùng change không tạo record consume thứ hai.

## Tự kiểm tra

1. `docker compose ps` xác nhận SQL Server `Up`.
2. Chạy `sql/02_enable_cdc.sql` qua sqlcmd và xác nhận capture source duy nhất
   là `meta.CdcDemoOperationalRecord`.
3. Chạy `python scripts/run_synthetic_cdc_demo.py` sau khi set password.
4. Xem JSON evidence có operation 2, 3, 4.
5. Xác nhận fact vẫn có 1,965,355 dòng.

## Kết luận stage

`PASS`. Đây là demo CDC kỹ thuật có kiểm soát; không khẳng định source tĩnh có
historical CDC events.
