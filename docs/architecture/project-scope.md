# Project này đang xây gì?

Repository này là **Insurance Data Platform** — nền tảng dữ liệu bảo hiểm trên SQL Server để thể hiện năng lực Data Engineering, T-SQL ETL, Data Warehouse, Data Quality, incremental engineering và Performance Tuning. Risk Analytics, Machine Learning, Airflow và Power BI là các năng lực mở rộng trên cùng nền tảng; chúng không biến toàn bộ repository thành một dự án ML xe cơ giới.

## Kiến trúc hiện tại đã được sửa như thế nào?

Project dùng nhiều **data track** — luồng dữ liệu độc lập cùng thuộc business domain bảo hiểm. Hãy hình dung một trung tâm thương mại có nhiều cửa hàng: cùng toà nhà không có nghĩa hoá đơn của cửa hàng này là hoá đơn của cửa hàng khác.

```text
Insurance Data Platform
├── Track A — SUSEP Market DWH / Performance / Market BI
├── Track B — brvehins1 Motor Risk Analytics / ML
└── Track C — Prudential Life Underwriting (planned, chưa có raw data)
```

`canonical source` nghĩa là nguồn chuẩn **trong track của nó**, không phải một file duy nhất phải thay thế mọi nguồn khác trong repository.

## Track nào đã chạy thật và track nào mới là kế hoạch?

- **Track A — SUSEP:** raw CSV là `ACTIVE_CANONICAL` cho market DWH, Performance Tuning và Market BI. EDA/contract/staging/DWH/reconciliation/DQ đã `RUNTIME_PASS`; Market Power BI artifact thật vẫn `BLOCKED_MANUAL` nếu môi trường không có supported tooling.
- **Track B — brvehins1:** raw, staging, risk DWH, DQ, bounded ML artifact và out-of-sample batch scoring đã có runtime evidence. `FactRiskObservation` là fact trung tâm của Track B, không phải fact trung tâm của cả platform.
- **Track C — Prudential:** là hướng nguồn life-underwriting trong ý định gốc, nhưng không có file physical trong workspace. Status là `ORIGINAL_PLANNED_SOURCE / NOT_PRESENT`; không tải dữ liệu hoặc dựng pipeline giả trong task này.

## Vì sao các track không được join theo row?

**Row identity** — căn cước của một dòng — phải được source chứng minh. SUSEP chỉ quan sát market measures theo company/time/product/state. brvehins1 quan sát aggregate motor-risk record. Không source nào cung cấp khóa nối record-level giữa hai nguồn. Prudential cũng không được giả định có chung customer với SUSEP.

Vì vậy repository cấm tạo `CustomerId`, `PolicyId`, customer mapping hoặc relationship SUSEP ↔ brvehins1 ↔ Prudential giả. Các track có thể chia sẻ SQL Server, DQ patterns, orchestration layer và báo cáo ở mức đã được diễn giải rõ; chúng không chia sẻ một star schema hay một join nghiệp vụ không có bằng chứng.

## Lịch sử đã dẫn tới quyết định này là gì?

1. Ý định ban đầu đúng: Insurance DWH & Performance Tuning với SUSEP market data, đồng thời để ngỏ Prudential cho life/underwriting.
2. Scaffold cũ đã sai khi giả định Prudential `Dim_Customer` có thể join với SUSEP facts mà không có key thật. Các SQL scaffold customer/policy/fact cũ là bằng chứng lịch sử, không phải thiết kế hiện hành.
3. brvehins1 được bổ sung và được triển khai đúng theo grain thật của nó: aggregate risk observation, không phải customer/policy/event. Đây là thành quả Track B hợp lệ và đã có evidence runtime.
4. Repository sau đó over-correct: brvehins1 bị gọi là canonical duy nhất và SUSEP bị gọi legacy. Điều đó làm mất vai trò primary DWH/performance của SUSEP, dù không làm Track B sai.
5. `P1-ARCH-REALIGN-01` khôi phục SUSEP thành Track A active canonical, giữ nguyên Track B, và loại bỏ mọi giả định join giả.

Các report/checkpoint trước realignment vẫn là **historical evidence** của thời điểm chúng được viết. Chúng không bị sửa số liệu hoặc bị dùng để thay thế kiến trúc owner-approved hiện tại.

## Khi tài liệu mâu thuẫn, tôi tin nguồn nào?

Thứ tự ưu tiên là: kiến trúc owner-approved hiện tại → physical data → runtime evidence → original project intent → validated data contract → implementation → current documentation → historical reports → old scaffold/comments.

Nói đơn giản: bản vẽ cũ hữu ích để biết ý tưởng ban đầu, nhưng file CSV thật và quy tắc không-bịa-key quyết định model nào được phép xây.

## Bước kế tiếp phải là gì?

`P1-SUSEP-01` phải profile CSV SUSEP bằng streaming và đóng **source contract** trước khi tạo staging hoặc bảng DWH. Sau đó là SUSEP ingestion, dimensional model, reconciliation, DQ và performance tuning. Airflow chỉ điều phối các đường đã được chạy tay; không được triển khai lại trong task realignment này.

Xem inventory cụ thể tại [source-strategy.md](source-strategy.md) và sơ đồ tại [overall-architecture.md](overall-architecture.md).
