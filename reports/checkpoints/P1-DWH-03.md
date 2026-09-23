# P1-DWH-03 — FactRiskObservation

Ngày: 2026-09-22

Kết quả: PASS

## Mục tiêu và file thay đổi

Tạo fact canonical one-to-one với staging mà không suy diễn policy/customer. Thay đổi: `migrations/V7__create_fact_risk_observation.sql`, `sql/05_load_fact_risk_observation.sql`, `docs/architecture/dwh-design.md`, checkpoint này và progress log.

## Bằng chứng runtime

- `FactRiskObservation` có grain `(SourceFile, SourceRowNumber)` và FK tới staging cùng ba dimension.
- First load: 1,965,355 rows; rerun: 0 rows.
- Fact = staging = distinct fact source identity = 1,965,355.
- Orphan FK: 0; batch/source lineage mismatch: 0.
- Computed measures giữ công thức contract và trả `NULL` ratio khi denominator `<= 0`.

Lần chạy đầu V7 dừng trước khi tạo table vì thiếu SQL Server SET options bắt buộc cho persisted computed columns. Migration được bổ sung đủ SET options, rerun thành công; raw và staging không bị thay đổi.

## Tiêu chí PASS

- [x] Fact grain đúng một source row, không customer/policy/event giả.
- [x] Toàn bộ staging row được reconcile vào fact.
- [x] FK resolve, lineage được preserve, rerun an toàn.

## Bước tiếp theo

`P1-DQ-01` — chạy source/staging DQ hard rules.
