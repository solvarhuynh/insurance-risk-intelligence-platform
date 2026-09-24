# Tôi triển khai Insurance Data Platform theo nguyên tắc nào?

## Mục tiêu hiện hành là gì?

Project xây nền tảng dữ liệu bảo hiểm nhiều track, không phải một warehouse duy nhất giả vờ có chung customer/policy identity. Mục tiêu ưu tiên là:

1. Track A: SUSEP Market DWH để phục vụ ingestion lớn, DQ, Performance Tuning và Market BI.
2. Track B: bảo toàn risk DWH và ML runtime-validated từ brvehins1.
3. Track C: Prudential chỉ được triển khai khi physical source có mặt và có contract riêng.

## Quy tắc model nào không được vi phạm?

- Bắt đầu từ physical schema và source contract, không từ table name cũ.
- Một fact chỉ được mô tả ở grain mà source chứng minh.
- Same business domain không tạo ra same row identity.
- Không tạo CustomerId, PolicyId, customer mapping hoặc claim-event grain giả.
- Không dùng code/comment historical scaffold làm specification.
- Chỉ gọi RUNTIME_PASS khi lệnh, environment, input, output và evidence đã tồn tại.

## Track A sẽ được triển khai theo thứ tự nào?

P1-SUSEP-01 profile CSV theo streaming: exact row count, header/types, uniqueness, null/range, refresh/time, premium/claim/ratio semantics và candidate grain.

P1-SUSEP-02 tạo staging ingest có lineage, batch metadata và reconciliation dựa trên contract đã freeze.

P1-SUSEP-03 tạo dimensional design theo fields thật. Candidate hiện tại là month, company, product, geography và market-observation fact; đây không phải DDL đã được chấp thuận.

P1-SUSEP-04 load fact/dimension và chứng minh reconciliation/idempotency.

P1-SUSEP-05 tạo DQ executable. Chỉ khi đó P1-PERF mới đo execution plan, STATISTICS IO/TIME và index experiment trên workload market.

## Track B được giữ như thế nào?

Track B giữ nguyên brvehins1 raw, stg.BrVehIns1, DimDriverProfile, DimVehicle, DimGeography, FactRiskObservation, DQ, incremental/CDC demo, ML contract, model artifact, RiskObservationPrediction và scoring idempotency. Không đổi grain để ép nó vào SUSEP.

ML Track B là HasClaim association cross-sectional cho aggregate risk observation. Nó không được tái diễn giải thành market prediction hay customer-level forecast.

## Các file SQL cũ phải được xử lý thế nào?

Các scaffold Dim_Customer, Dim_Policy, Fact_Premium, Fact_Claims và SCD2 cũ không được chạy hay nâng cấp trực tiếp. P1-SUSEP-01 sẽ quyết định replacement dựa trên actual CSV. Việc giữ file lịch sử không tạo authorization để invent entities.

## Roadmap chuẩn ở đâu?

Đọc docs/specs/roadmap.md. Tài liệu này thay thế các roadmap cũ tập trung vào Motor Insurance-only. Chi tiết source status nằm tại docs/architecture/source-strategy.md.
