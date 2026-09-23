# P1-DWH-01 — Thiết kế dimensional model canonical

Ngày: 2026-09-22

Kết quả: PASS

## Mục tiêu

Thiết kế DWH chỉ từ source contract và 1,965,355 staging rows đã đối soát, xác định fact grain và chỉ giữ dimensions có bằng chứng.

## File đã thay đổi

- `docs/architecture/dwh-design.md`
- `reports/checkpoints/P1-DWH-01.md`
- `log/progress-log.md`

## Bằng chứng và quyết định

- Source contract đóng băng một row là aggregate risk observation, không có customer ID, policy ID, date hoặc claim-event ID.
- Staging có 1,965,355 rows unique theo `(SourceFile, SourceRowNumber)` và preserve 14 logical duplicate rows.
- Fact được đặt tên `dwh.FactRiskObservation`, grain đúng một staging source row.
- Ba dimensions hợp lệ là `DimDriverProfile` (`Gender`, `DrivAge`), `DimVehicle` (`VehYear`, `VehModel`, `VehGroup`) và `DimGeography` (`Area`, `State`, `StateAb`).
- `FactRiskObservation` preserve `StageRowId`, batch/source lineage và các measure source; điều này cho phép reconciliation one-to-one.
- Dimension keys là surrogate key. Natural grouping là canonical source tuple/hash kỹ thuật, không là business identifier.
- Không tạo Customer, Policy, SCD2, date, fact claim event hoặc tách premium/claims facts vì không có evidence source.

## Tiêu chí PASS

- [x] Model biểu diễn được mọi staging row mà không phát minh entity nghiệp vụ.
- [x] Fact grain chính xác và technical lineage explicit.
- [x] Lý do tồn tại/không tồn tại của từng dimension được ghi rõ.
- [x] Surrogate key, null handling, uniqueness, rerun và no-SCD2 policy được mô tả.

## Bước tiếp theo chính xác

`P1-DWH-02` — implement ba dimension được chấp thuận, nạp từ staging và kiểm chứng row count, uniqueness, rerun.
