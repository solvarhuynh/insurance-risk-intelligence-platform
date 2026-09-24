# P1-INC-01 — Audit nạp file incremental

Ngày: 2026-09-23  
Kết luận: `RUNTIME_PASS`

## Stage này giải quyết vấn đề gì?

Roadmap gọi incremental ingestion là stage tương lai, nhưng foundation đã có
khả năng này ở grain immutable-file batch. Audit này kiểm tra capability có
thật hay chỉ là tên trong roadmap.

## Đã kiểm tra gì?

| Kiểm tra | Kết quả runtime |
|---|---:|
| Partition canonical có batch `SUCCESS` | 5 |
| Số dòng mỗi batch | 393,071 |
| Dòng bị reject mỗi batch | 0 |
| Tổng staging | 1,965,355 |
| Technical identity distinct | 1,965,355 |
| Rerun `brvehins1a.csv` | `SKIPPED`; trả batch `56D062D8-5048-4086-A6A0-0F26E17FD6B3` |
| Fact sau rerun loader | 1,965,355 |

## Cơ chế

```text
SourceFile canonical
  → meta.IngestionBatch SUCCESS
  → loader thấy cùng file thì trả SKIPPED
  → unique (SourceFile, SourceRowNumber) bảo vệ staging
  → fact chỉ insert StageRowId chưa có
```

`SourceFile + SourceRowNumber` là technical identity, không phải customer hay
policy ID. Fact vẫn one-to-one với staging, kể cả 14 logical duplicate nguồn.

## Vì sao không viết thêm implementation?

Loader hiện tại đã có lineage, nhận biết partition thành công, không duplicate
staging khi rerun và không duplicate fact khi downstream rerun. Viết thêm loader
hoặc watermark sẽ tạo behavior cạnh tranh mà không giải quyết gap đã chứng minh.

## Thuật ngữ cần hiểu

- **Incremental load** → chỉ xử lý input mới; ở đây đơn vị là một CSV partition.
- **Idempotency** → bấm lại cho cùng kết quả; lookup batch `SUCCESS` là ví dụ.
- **Lineage** → dấu vết nguồn gốc; `SourceFile` và `SourceRowNumber` truy ngược
  được row về file.

## Tự kiểm tra

1. Chạy `python scripts/load_brvehins1_to_staging.py --source-file brvehins1a.csv`.
2. Xác nhận command trả `SKIPPED`.
3. Query `meta.IngestionBatch` để thấy 5 dòng `SUCCESS`.
4. Chạy `EXEC dwh.sp_LoadFactRiskObservation;`, count vẫn là 1,965,355.

## Kết luận stage

`P1-INC-01 = RUNTIME_PASS`. Bước tiếp theo là synthetic CDC demo cô lập, không
phải viết loader file thứ hai.
