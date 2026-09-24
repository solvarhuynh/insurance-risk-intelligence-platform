# P1-SUSEP-04 — SUSEP Market DWH runtime

## Stage này giải quyết vấn đề gì?

Triển khai star schema Track A bằng dữ liệu thật và chứng minh không có row loss/explosion từ staging sang fact.

## Agent đã sửa những file nào?

- `migrations/V12__create_susep_market_dwh.sql`: bốn dimensions, một market fact, view và stored procedure idempotent.
- `sql/09_load_susep_market_dwh.sql`: entry point load/recheck.
- `scripts/reconcile_susep_source_to_fact.py`: đọc lại raw file và đối chiếu direct với staging/fact.
- `docs/susep/dwh-design.md`: giải thích grain và additive semantics.

## Runtime evidence là gì?

`dwh.sp_LoadSusepDimensions` và `dwh.sp_LoadFactSusepInsuranceMarket` đã chạy thành công. Kết quả:

| Đối tượng | Rows |
|---|---:|
| Raw source | 8.338.214 |
| Accepted staging | 8.338.214 |
| `FactSusepInsuranceMarket` | 8.338.214 |
| `DimSusepMonth` | 247 |
| `DimSusepCompany` | 196 |
| `DimSusepProduct` | 144 |
| `DimSusepState` | 27 canonical uppercase state codes |

Raw/stage lexical `state` có 40 value (27 canonical + 103 lower/mixed-case row variants); dimension map deterministic `UPPER(state)` nên không tạo geography/region giả.

Direct reconciliation `SUCCESS` xác nhận cả count và analytic totals giống nhau ở raw → staging → fact:

- Premiums: `3050108693057.190700567726667268`
- Claims: `735517715559.682615627330218331`

Chạy lại `sql/09_load_susep_market_dwh.sql` trả lại cùng **8.338.214** staging/fact rows; stored procedures không thêm dimension/fact duplicate.

## Owner cần hiểu khái niệm gì?

**Reconciliation** là đối chiếu sổ giao nhận: không chỉ đếm thùng hàng mà còn kiểm tiền premium/claims trước và sau mỗi cửa. `FactSusepInsuranceMarket` giữ `SusepStageRowId` unique nên một stage row chỉ có một fact.

## Điều gì có thể nhìn đúng nhưng thực ra sai?

- Fact count bằng stage count nhưng total measure khác vẫn là lỗi; vì vậy có direct source total check.
- 27 state dimension rows không mâu thuẫn 40 lexical source values: 13 variant chữ thường là cùng canonical state code, và raw lineage được giữ ở stage/source fingerprint.
- `SourceClaimPremiumRatio` vẫn không được cộng hay gọi là derived ratio.

## Stage verdict

**PASS** — dimensions/fact populated, FK/grain/lineage được DQ kiểm tra, direct count và premium/claim reconciliation bằng 0 difference, rerun không duplicate.
