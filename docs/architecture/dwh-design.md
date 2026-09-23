# Thiết kế DWH canonical — brvehins1

Trạng thái: `RUNTIME_PASS` cho P1-DWH-01/P1-DWH-02/P1-DWH-03. Ba dimension và fact canonical đã có DDL, load, reconciliation và rerun runtime.

## Phạm vi và nguyên tắc

Thiết kế này chỉ dùng `brvehins1` đã được ingest vào `stg.BrVehIns1` (1,965,355 rows). Nó không đọc, join hoặc dùng `data/raw/susep.gov.br/insurance_dataset.csv`, vì file đó là legacy/non-canonical.

Nguồn không có business customer identifier, policy identifier, thời điểm hiệu lực hay claim event identifier. Do đó không tạo `CustomerId`, `PolicyNumber`, `Dim_Customer`, `Dim_Policy`, SCD2, time dimension, hay fact claim-event. Những tên file scaffold cũ không là bằng chứng để tạo business entity.

## Ý nghĩa các lớp trong dự án này

- **Raw** là năm CSV bất biến `data/raw/brvehins1/brvehins1[a-e].csv`. Raw giữ source text và không bị DWH sửa.
- **Staging** là `stg.BrVehIns1`: một bản ghi nguồn đã parse đúng type, cộng lineage `BatchId`, `SourceFile`, `SourceRowNumber`, hash và timestamp. Nó chưa tổng hợp hay làm sạch business semantics.
- **Dimension** là danh mục mô tả lặp lại dùng để phân tích theo driver, xe và địa lý. Natural grouping của dimension là tổ hợp descriptor nguồn, không phải một khách hàng, xe hay khu vực được master-data xác minh.
- **Fact** là một observation rủi ro tổng hợp từ source, mang các measure exposure, premium, sum insured và claim. Nó không phải hợp đồng, khách hàng, claim transaction hay event.

## Fact đề xuất và grain

Tên được chọn là `dwh.FactRiskObservation` để tránh hàm ý policy không được source chứng minh.

Grain chính xác: **một row `stg.BrVehIns1`, xác định bất biến bởi `(SourceFile, SourceRowNumber)`**. Một fact row giữ đúng một staging row và không collapse 14 raw logical duplicate đã biết.

Fact có `FactRiskObservationKey` là surrogate key warehouse, đồng thời preserve `StageRowId`, `BatchId`, `SourceFile`, `SourceRowNumber`, `SourceRecordHash` và `LoadTimestampUtc` cho lineage. Unique constraint trên `(SourceFile, SourceRowNumber)` đảm bảo one-to-one với staging. `StageRowId` cũng phải unique trong fact; nó là foreign key đến staging, không là business identifier.

Các measure giữ nguyên source contract: `ExposTotal`, `ExposFireRob`, `PremTotal`, `PremFireRob`, `SumInsAvg`, năm `ClaimNb*` và năm `ClaimAmount*`. Fact có thể materialize các measure dẫn xuất đã được contract xác minh: `TotalClaimCount`, `TotalClaimAmount`, `HasClaim`, `ClaimFrequency` và `LossRatio`; hai ratio phải là `NULL` khi mẫu số `<= 0`, không infinity hay cap outlier.

## Dimensions được chấp thuận

### `dwh.DimDriverProfile`

Thuộc tính: `Gender`, `DrivAge`.

Dimension tồn tại vì hai descriptor này lặp lại và phù hợp để slice fact. `Gender` bao gồm cả nhãn `Corporate`, nên nó chỉ được giữ như category nguồn, không diễn giải thành giới tính cá nhân. Dimension không đại diện customer hoặc driver duy nhất.

Natural grouping kỹ thuật là canonical tuple `(Gender, DrivAge)` với phân biệt rõ `NULL` và text thật. Không có SCD2: nguồn không có effective date và không có identity cá nhân để nói một attribute đã thay đổi theo thời gian.

### `dwh.DimVehicle`

Thuộc tính: `VehYear`, `VehModel`, `VehGroup`.

Dimension tồn tại để phân tích theo descriptor xe lặp lại. Nó không là vehicle master vì nguồn không có VIN, registration hoặc identifier xe. `VehYear=0` được preserve là value suspicious/business-review; không tự đổi thành unknown.

Natural grouping kỹ thuật là tuple `(VehYear, VehModel, VehGroup)`, giữ nguyên null source. Không có SCD2 vì không có real vehicle identity hay lịch sử hiệu lực.

### `dwh.DimGeography`

Thuộc tính: `Area`, `State`, `StateAb`.

Dimension tồn tại để phân tích địa lý; mapping `State`/`StateAb` đã được EDA xác nhận không mâu thuẫn khi cả hai có dữ liệu. Nó không là geography master/reference table ngoài source.

Natural grouping kỹ thuật là tuple `(Area, State, StateAb)`, giữ null source. Không tạo geography hierarchy hoặc map ngoài dataset vì chưa có evidence nghiệp vụ.

## Surrogate key, uniqueness và null

Mỗi dimension dùng integer surrogate key. P1-DWH-02 sẽ tạo một `DimensionNaturalHash` SHA-256 trên serialization canonical, có type tag, separator an toàn và sentinel riêng cho NULL; hash này chỉ phục vụ deterministic lookup/uniqueness, không là business key. Các natural attribute được giữ trong dimension để truy vết/readability.

Các row staging có attribute NULL vẫn được map tới dimension member của đúng tuple null-preserved, thay vì mất dữ liệu hay gom mọi partial null thành một member. Có thể có default member `Unknown / not supplied` key `0` chỉ cho trường hợp lookup không resolve; với dữ liệu staging hợp lệ, lookup không resolve là lỗi integrity/DQ, không là fallback im lặng.

Không dùng SCD2. Năm file là partition source, không phải lịch sử thay đổi của customer/vehicle/geography; chúng không chứng minh entity identity hay effective dating.

## Quan hệ và luồng nạp

```text
stg.BrVehIns1 (1 row nguồn)
  ├─ lookup tuple driver ───► dwh.DimDriverProfile
  ├─ lookup tuple vehicle ──► dwh.DimVehicle
  ├─ lookup tuple geography ► dwh.DimGeography
  └─ preserve lineage + measures ─► dwh.FactRiskObservation (chính xác 1 row)
```

P1-DWH-02 nạp các dimension distinct từ toàn staging và rerun theo upsert deterministic. P1-DWH-03 chỉ insert fact row chưa tồn tại theo technical identity, sau khi cả ba dimension lookup resolve. Không có aggregate hay deduplicate trong hai bước.

## Không tạo các cấu trúc sau

- `Dim_Customer`/`Dim_Policy`: không có source identifier hoặc semantics.
- Fact `Premium` và Fact `Claims` tách rời: các measure thuộc cùng một observation nguồn; tách chúng sẽ gây grain không có evidence.
- Claim-type dimension và fact claim-event: claim category là các cột aggregate, không là rows/event trong source.
- Date dimension: không có date/timestamp nghiệp vụ.
- SCD2: không có natural entity key hay history.

## Tiêu chí implementation cho stage sau

- Dimension natural tuples phải unique, row counts phải được ghi từ runtime.
- Fact phải có đúng 1,965,355 rows sau load đầu tiên, trừ khi bất kỳ difference nào được DQ giải thích và gate chặn.
- Mọi fact foreign key phải resolve; staging-to-fact đối soát theo `(SourceFile, SourceRowNumber)`.
- Rerun dimension/fact không tạo duplicate và 14 raw logical duplicate vẫn được preserve thành fact rows tách biệt.

## Kết quả P1-DWH-02

Migration `V6__create_canonical_dimensions.sql` đã tạo ba dimension cùng procedure `dwh.sp_LoadCanonicalDimensions`. Lần nạp đầu chèn 24 driver profile, 25,092 vehicle và 42 geography tuple, ngoài ba default member key `0`; tổng count table tương ứng là 25, 25,093 và 43. Mỗi table có count bằng count `DimensionNaturalHash` distinct. Rerun procedure chèn `0` row ở cả ba dimension.

`sql/04_load_canonical_dimensions.sql` là entry point thực thi hiện hành. `sql/04_sp_dim_others.sql` chỉ là stale historical scaffold, được giữ để map kiến trúc cũ và không được chạy.

## Kết quả P1-DWH-03

Migration `V7__create_fact_risk_observation.sql` đã tạo `dwh.FactRiskObservation`; nạp đầu tiên thêm đúng 1,965,355 fact rows, one-to-one với staging. Rerun thêm 0 row. Foreign-key assertion không có orphan; fact count, source identity và staging count đều là 1,965,355.
