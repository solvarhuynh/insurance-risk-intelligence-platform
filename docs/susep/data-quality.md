# Data Quality — Track A SUSEP

## DQ bảo vệ điều gì?

`dq.sp_RunSusepQualityGate` là cổng executable chỉ cho Track A. Nó chạy sau reconciliation raw → staging → fact. Gate không gọi `dq.sp_RunQualityGate` của Track B và cũng không thay đổi raw/fact để “sửa cho pass”.

## Hard failure và warning khác nhau thế nào?

| Nhóm | Rule | Nếu fail thì sao? |
|---|---|---|
| Staging contract | Required columns, batch reconciliation, zero rejected source rows, technical identity | Chặn DWH consumer/downstream |
| Source grain | Required fields, month-start date, unique company-month-product-state, company code/name mapping | Chặn vì fact không còn ý nghĩa 1:1 |
| Warehouse | fact=accepted staging, foreign keys, fact technical grain, copied lineage/measure equality, dimension natural-key uniqueness | Chặn vì warehouse sai hoặc mất data |
| Reconciliation | Mỗi `SUCCESS` source version có direct raw-to-fact reconciliation `SUCCESS` | Chặn vì chưa có chứng cứ measure total |
| Financial characteristics | negative premiums, negative claims, `NA`/NULL ratio, negative source ratio | `WARNING`; giữ data và yêu cầu business review |

Với Track A, “non-negative financial measures” không phải hard rule. EDA đã chứng minh premium và claims âm tồn tại trong raw. Chặn chúng chẳng khác nào vứt hóa đơn điều chỉnh chỉ vì có dấu trừ.

## Ratio được kiểm soát ra sao?

Gate chỉ kiểm tra rằng `NA` được biểu diễn `NULL` và source ratio được mang qua fact đúng. Gate không khẳng định ratio là `claims / premiums`, không ép non-negative, không cộng ratio. Derived market ratio phải được tính ở report layer với aggregate có denominator guard.

## Controlled failure có an toàn không?

Gọi:

```sql
EXEC dq.sp_RunSusepQualityGate
    @RunLabel=N'controlled-invalid-test',
    @InjectControlledFailure=1;
```

Procedure chỉ thêm rule in-memory `CONTROLLED_INVALID_INPUT` (observed `1`, expected `0`), ghi DQ log rồi `THROW`. Nó không insert/update/delete source, staging, reject table, dimension hay fact. Đây là chuông báo cháy thử: hệ thống phải kêu nhưng tòa nhà không bị đốt.

## Tôi kiểm tra log ở đâu?

```sql
SELECT TOP (100) RunLabel, RuleName, Severity, Status, ObservedValue, ExpectedValue, Detail, CheckedAtUtc
FROM dq.SusepQualityCheckLog
ORDER BY SusepQualityCheckLogId DESC;
```

`PASS` của static validator không thay thế được gate này. Chỉ execution của stored procedure với data thật mới là runtime DQ evidence.
