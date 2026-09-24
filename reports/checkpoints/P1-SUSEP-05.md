# P1-SUSEP-05 — SUSEP Data Quality runtime

## Stage này giải quyết vấn đề gì?

Đưa contract Track A thành một gate có thể chặn downstream. Code/table tồn tại không đủ; stored procedure phải chạy với 8,3 triệu row thật và phải biết fail an toàn.

## Agent đã sửa những file nào?

- `migrations/V13__create_susep_quality_gate.sql`: log riêng, reconciliation evidence table và `dq.sp_RunSusepQualityGate`.
- `sql/10_run_susep_quality_gate.sql`: production entry point.
- `docs/susep/data-quality.md`: giải thích hard rule, warning và controlled failure.

## Runtime evidence là gì?

Production gate đã pass toàn bộ **14 hard rules**: staging/batch/count/grain/company mapping, fact=stage, FK, fact lineage, dimension uniqueness và direct reconciliation evidence.

Các warning được ghi nhận nhưng không bị xóa/biến thành hard failure:

| Characteristic | Observed rows |
|---|---:|
| Negative premiums | 116.980 |
| Negative claims | 301.382 |
| Source ratio `NA` → NULL | 5.167.094 |
| Negative source ratio | 238.088 |

Controlled test `@InjectControlledFailure=1` đã tạo rule `CONTROLLED_INVALID_INPUT = FAIL` và procedure throw đúng như thiết kế. Sau test, count được kiểm tra lại vẫn `staging=8.338.214`, `fact=8.338.214`: canonical data không bị mutate.

## Owner cần hiểu khái niệm gì?

**Hard failure** là khóa cửa pipeline. **Warning** là biển cảnh báo cho người vận hành. Có dấu âm trong accounting data không tự động là bad data; đây là lý do rules phải dựa evidence, không dựa trực giác.

## Owner tự kiểm tra thế nào?

```sql
EXEC dq.sp_RunSusepQualityGate @RunLabel=N'manual-production';
SELECT TOP (100) * FROM dq.SusepQualityCheckLog ORDER BY SusepQualityCheckLogId DESC;
```

## Stage verdict

**PASS** — valid production data pass; injected invalid condition fail và không làm hỏng raw/staging/fact.
