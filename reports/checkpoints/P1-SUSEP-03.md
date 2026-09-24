# P1-SUSEP-03 — Thiết kế dimensional model SUSEP

## Stage này giải quyết vấn đề gì?

Chốt DWH model trước DDL để một dòng market source không bị biến thành hai fact hoặc một entity giả. Đây là bản vẽ trước khi xây nhà.

## Trước stage này project thiếu gì?

EDA biết grain, nhưng chưa có quyết định rõ ràng về fact, dimensions, additive/non-additive measures, lineage và rerun behavior.

## Agent đã sửa những file nào?

- `docs/susep/dwh-design.md`: model, decision và Mermaid star schema.
- `migrations/V12__create_susep_market_dwh.sql`: DDL Track A và stored procedures idempotent sẵn sàng chạy ở A4.

## Data/code đi qua đâu?

```text
stg.SusepInsuranceMarket
  → DimSusepMonth / Company / Product / State
  → FactSusepInsuranceMarket (1:1 accepted stage row)
  → view cho market analytics
```

## Runtime evidence là gì?

Design evidence dựa trên P1-SUSEP-01: 8.338.214 rows, unique candidate grain, 196 companies, 144 products, 40 states và month field đầy đủ. DDL chưa được dùng làm bằng chứng population; điều đó thuộc P1-SUSEP-04.

## Owner cần hiểu khái niệm gì?

**Star schema** là fact trung tâm nối tới các dimension mô tả. Nó giống hóa đơn ở giữa nối với lịch, cửa hàng, sản phẩm và địa điểm. **Surrogate key** là số ID kỹ thuật trong warehouse; **natural key** là mã/text xuất phát từ source.

## Owner chưa cần học gì?

Chưa cần học index hint hay execution plan. Đó là Phase Performance sau khi fact có dữ liệu thật.

## Owner tự kiểm tra thế nào?

Đọc `docs/susep/dwh-design.md`, rồi kiểm tra V12 không tạo `Customer`, `Policy` hay FK Track B.

## Điều gì có thể nhìn đúng nhưng thực ra sai?

- Hai source columns `premiums`/`claims` không buộc phải thành hai facts.
- Có `company` không chứng minh có customer.
- Ratio ở source không thể cộng theo time/state/product.

## Stage verdict

**PASS** — thiết kế đủ rõ, bám actual grain và có thể triển khai mà không fake entity/relationship.
