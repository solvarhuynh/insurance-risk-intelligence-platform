# Thuật ngữ nào giúp tôi đọc đa track repository?

## Canonical source có nghĩa gì?

**Canonical source** là nguồn chuẩn được chấp nhận cho một track. Nó giống sổ cái chính của từng cửa hàng, không phải một sổ cái buộc mọi cửa hàng dùng chung. SUSEP là canonical của Track A; brvehins1 là canonical của Track B.

## Data track là gì?

**Data track** là một luồng raw → staging → DWH → DQ → consumer có grain và mục đích riêng. Track A là market data; Track B là aggregate motor-risk data. Track C là future life-underwriting source khi file xuất hiện.

## Grain và row identity là gì?

**Grain** là một row đại diện cho gì. **Row identity** là cách chứng minh row đó là ai. brvehins1 có technical identity SourceFile + SourceRowNumber, không phải customer/policy. SUSEP có company/time/product/state fields nhưng exact candidate grain còn chờ P1-SUSEP-01 kiểm tra.

## Fact và dimension là gì?

**Fact** là bảng measures ở một grain, như sổ doanh thu theo tháng. **Dimension** là catalog để lọc/group, như danh mục công ty, sản phẩm hoặc bang. `FactRiskObservation` thuộc Track B; `FactSusepInsuranceMarket` cùng bốn market dimensions thuộc Track A. Chúng không join chéo track.

## Staging, lineage và reconciliation là gì?

**Staging** là khu nhận hàng đã parse nhưng chưa biến nghĩa nghiệp vụ. **Lineage** là dấu vết raw file đến row DWH. **Reconciliation** là đối chiếu số lượng/identity giữa các lớp, như đếm kiện ở cổng nhận và trên kệ phải bằng nhau.

## Data Quality gate là gì?

**DQ gate** là rule có thể chặn downstream khi data vi phạm contract. Track B có dq.sp_RunQualityGate runtime evidence. Track A phải định nghĩa rule từ SUSEP contract của chính nó, không copy rule một cách máy móc.

## Data leakage, ML artifact và batch scoring là gì?

**Data leakage** là dùng outcome như input, giống nhìn đáp án trước khi thi. Trong Track B, ClaimNb* và ClaimAmount* bị cấm làm feature cho HasClaim.

**Model artifact** là gói preprocessing + estimator đã fit. **Batch scoring** là dùng gói đó để score một lô. Artifact Track B không được dùng để score SUSEP market records hoặc Prudential customers.

## Static validation và runtime validation khác nhau thế nào?

**Static validation** kiểm tra file/header/syntax/structure, giống xem bản vẽ. **Runtime validation** chạy thật với data/environment và giữ evidence. File SUSEP hiện qua static file/header validation; Track B có các milestone runtime được ghi tại reports/checkpoints.

## Những thuật ngữ nào không được tự suy diễn?

Customer, policy, claim event và SCD2 chỉ được dùng khi source có identity/time semantics tương ứng. Same business domain không phải license để tạo relationship giữa tracks.
