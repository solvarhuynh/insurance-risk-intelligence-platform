# P1-DWH-02 — Canonical dimensions

Ngày: 2026-09-22

Kết quả: PASS

## Mục tiêu

Implement ba dimension đã được P1-DWH-01 phê duyệt, nạp từ staging và chứng minh uniqueness cùng rerun deterministic.

## File đã thay đổi

- `migrations/V6__create_canonical_dimensions.sql`
- `sql/04_load_canonical_dimensions.sql`
- `sql/04_sp_dim_others.sql` (đánh dấu historical scaffold, không thực thi)
- `docs/architecture/dwh-design.md`
- `docs/architecture/repository-structure.md`
- `docs/guides/how-to-run.md`
- `reports/checkpoints/P1-DWH-02.md`
- `log/progress-log.md`

## Lệnh đã chạy

```text
sqlcmd < migrations/V6__create_canonical_dimensions.sql
sqlcmd < sql/04_load_canonical_dimensions.sql
sqlcmd < sql/04_load_canonical_dimensions.sql   # rerun
sqlcmd < dimension count/unique/audit assertion
```

Lần đầu chạy V6 bị dừng tại default member `Gender` dài hơn `NVARCHAR(20)`; migration chưa có dữ liệu dimension được commit. Giá trị label được rút gọn thành `Unknown / missing`, sau đó rerun V6 thành công. Attempt chạy entry point lịch sử phát hiện nested block comment không executable; entry point canonical riêng được tạo thay vì dùng scaffold cũ. Entry point mới có một lỗi alias `RowCount` trước khi truy vấn output; procedure nạp dimension đã thành công trong batch trước đó, và lần chạy kế tiếp sau khi đổi alias là rerun kiểm chứng. Đây là các lỗi kỹ thuật đã sửa trong giới hạn retry; không có raw/staging row nào bị thay đổi.

## Bằng chứng runtime

| Dimension | Tuple nguồn đã nạp | Default key 0 | Total rows | Distinct natural hash |
|---|---:|---:|---:|---:|
| `DimDriverProfile` | 24 | 1 | 25 | 25 |
| `DimVehicle` | 25,092 | 1 | 25,093 | 25,093 |
| `DimGeography` | 42 | 1 | 43 | 43 |

- Audit first load: `Driver=24; Vehicle=25092; Geography=42`, `RowsAffected=25158`.
- Audit rerun: `Driver=0; Vehicle=0; Geography=0`, `RowsAffected=0`.
- Unique constraint trên `DimensionNaturalHash` và count runtime xác nhận không có dimension member trùng.
- Source tuple có NULL được preserve trong tuple riêng; default member chỉ dành cho lookup không resolve, không thay thế source null.

## Tiêu chí PASS

- [x] Ba dimension chỉ phản ánh driver profile, vehicle và geography thực tế.
- [x] Row count runtime và uniqueness đã được kiểm tra.
- [x] Nạp lại an toàn, không thêm duplicate.
- [x] Không tạo fake Customer/Policy hoặc SCD2.

## Bước tiếp theo chính xác

`P1-DWH-03` — tạo và nạp `FactRiskObservation` theo grain một staging source row, rồi đối soát staging-to-fact và foreign key.
