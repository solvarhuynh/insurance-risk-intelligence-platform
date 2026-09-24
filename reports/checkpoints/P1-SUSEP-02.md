# P1-SUSEP-02 — SUSEP staging và ingestion runtime

## Stage này giải quyết vấn đề gì?

Đưa raw CSV lớn của Track A vào SQL Server một cách repeatable mà vẫn truy ngược được từng dòng về file nguồn. Đây là “cổng nhận hàng” riêng của SUSEP, không dùng lại metadata/staging của brvehins1.

## Trước stage này project thiếu gì?

Track A chỉ có EDA. Chưa có table typed, batch audit, rejected-row path, hash lineage hay bằng chứng rerun không duplicate.

## Agent đã sửa những file nào?

- `migrations/V11__create_susep_staging.sql`: `meta.Susep*`, accepted staging và reject table độc lập cho Track A.
- `scripts/load_susep_to_staging.py`: loader RFC-aware, streaming 20.000 row/chunk, application lock, SHA-256 source fingerprint và idempotency.
- `docs/susep/how-to-run-track-a.md`: lệnh chạy/kiểm tra bằng tiếng Việt.

## Data/code đi qua đâu?

```text
raw insurance_dataset.csv (read-only)
  → header + byte contract + SHA-256
  → parse/validate mỗi CSV row
  → stg.SusepInsuranceMarket (accepted)
     hoặc stg.SusepInsuranceMarketReject (invalid)
  → meta.SusepIngestionBatch + meta.SusepPipelineAudit
```

`SourceFile + SourceFileSha256 + SourceRowNumber` là technical identity. Nó giống số lô + mã kiện + số thứ tự dòng trên phiếu giao hàng, không phải business customer/policy key.

## Runtime evidence là gì?

Migrations V11, V12 và V13 đã apply vào `DWH_Insurance` thành công. Ingestion batch `0EDEB285-DB67-4159-A6D5-FE85F00F085A` chạy thật:

| Kiểm tra | Kết quả |
|---|---:|
| Source rows theo manifest | 8.338.214 |
| Accepted staging rows | 8.338.214 |
| Rejected rows | 0 |
| Source bytes | 751.126.569 |
| Load elapsed | 827.331 seconds (13 phút 47 giây) |
| Batch status | `SUCCESS` |

Lần chạy lại với cùng raw SHA-256 đã trả:

```text
[SKIPPED] ... source_rows=8338214; accepted=8338214; rejected=0
```

Nó không thêm staging row. Vì vậy `source = accepted + rejected` và rerun không duplicate đã được kiểm chứng runtime.

## Owner cần hiểu khái niệm gì?

**Idempotent** nghĩa là bấm “nạp lại cùng file” nhiều lần vẫn cho cùng state cuối, không nhân đôi dữ liệu. **Lineage** là đường đi có thể truy tìm ngược: fact về sau có thể chỉ đúng dòng, đúng file fingerprint và đúng batch đã tạo nó.

## Owner chưa cần học gì?

Chưa cần học fact/dimension join hoặc index. Staging là khu kiểm tra/nhập kho; warehouse modeling là bước tiếp theo.

## Owner tự kiểm tra thế nào?

```sql
SELECT Status, ExpectedSourceRows, AcceptedRows, RejectedRows, ElapsedMilliseconds
FROM meta.SusepIngestionBatch;

SELECT COUNT_BIG(*) FROM stg.SusepInsuranceMarket;
SELECT COUNT_BIG(*) FROM stg.SusepInsuranceMarketReject;
```

## Điều gì có thể nhìn đúng nhưng thực ra sai?

- `SUCCESS` không có nghĩa DWH/fact/DQ đã pass; stage này mới chứng minh raw → staging.
- Không reject premium/claims âm chỉ vì nghe có vẻ “financial data phải dương”; source đã chứng minh điều ngược lại.
- `DECIMAL(38,18)` là representation cho SQL analytics, còn `*Raw` giữ lexical evidence để không che giới hạn precision SQL Server.

## Stage verdict

**PASS** — source/staging/reject reconciliation và same-source rerun idempotency đều có runtime evidence; raw không bị thay đổi.
