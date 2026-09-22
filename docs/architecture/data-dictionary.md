# Data Dictionary — Từ điển Dữ liệu Nguồn và Đích
# Data Dictionary — Từ điển Dữ liệu Nguồn và Đích (brvehins1)

Trạng thái: Khung cấu trúc từ điển dữ liệu. Hai bộ dữ liệu gốc (SUSEP ~8.3M dòng và Porto Seguro ~1.5M dòng) sẽ được tải vào `data/raw/` trong Giai đoạn 1 để điền đầy đủ thông tin chi tiết qua notebook `notebooks/01-eda.ipynb`.
Tài liệu này định nghĩa từ điển dữ liệu chính thức cho nguồn dữ liệu canonical của dự án: **brvehins1** (gồm 5 phân đoạn `brvehins1[a-e].csv` trong `data/raw/brvehins1/`, tổng cộng 1.965.355 dòng, 23 cột).

## 1. Nguồn dữ liệu: SUSEP — Brazilian Insurance Market Data (~8.3M dòng)
> Quyết định kiến trúc dữ liệu:
> - Nguồn dữ liệu canonical duy nhất của dự án là `brvehins1`. Cả 5 phân đoạn có cùng schema 23 cột.
> - Nguồn dữ liệu cũ `data/raw/susep.gov.br/insurance_dataset.csv` được giữ lại dưới dạng **LEGACY / NON-CANONICAL** nhằm bảo toàn lịch sử nghiên cứu, không thuộc luồng dữ liệu xử lý canonical.
> - Tập dữ liệu thô `brvehins1` KHÔNG có các trường như `CustomerId`, `PolicyNumber`, ngày giao dịch cụ thể, hay ngày bắt đầu/kết thúc lịch sử khách hàng (`Start_Date`, `End_Date`). Mô hình kho dữ liệu sẽ không tự bịa đặt các trường này mà sẽ mô hình hóa xoay quanh các thực thể tự nhiên có trong dữ liệu: Người lái (Driver Profile), Phương tiện (Vehicle), Địa lý (Geography), Phơi nhiễm (Exposure), Phí bảo hiểm (Premium) và Bồi thường tổn thất (Claims).
> - Bảng dưới đây khảo sát các cột nguồn thực tế và phân loại sơ bộ; cấu trúc DWH chính thức sẽ được chốt sau khi hoàn thành task EDA (`P1-DATA-01`).

| Tên cột mẫu | Kiểu dữ liệu | Ý nghĩa | Bảng nguồn | Ghi chú chất lượng dữ liệu |
|---|---|---|---|---|
| id_empresa / company_id | INT / NVARCHAR | Mã công ty bảo hiểm | Báo cáo tháng SUSEP | Kiểm tra mã hoá và bảng danh mục công ty |
| id_ramo / product_code | INT / NVARCHAR | Nhóm nghiệp vụ bảo hiểm | Báo cáo tháng SUSEP | Phân loại theo bảo hiểm tài sản, con người, xe |
| id_regiao / region_code | NVARCHAR(10) | Mã bang / khu vực Brazil | Báo cáo tháng SUSEP | Chuẩn hoá mã bang (SP, RJ, MG, etc.) |
| dt_ref / date_ref | DATE | Tháng năm ghi nhận giao dịch | Báo cáo tháng SUSEP | Định dạng ngày tháng, kiểm tra khoảng thời gian từ 2003 |
| vl_premio / premium_amt | DECIMAL(18,2) | Doanh thu phí bảo hiểm phát sinh | Báo cáo tháng SUSEP | Đơn vị BRL, kiểm tra giá trị không âm |
| vl_sinistro / claims_amt | DECIMAL(18,2) | Giá trị bồi thường phát sinh | Báo cáo tháng SUSEP | Đơn vị BRL, kiểm tra giá trị không âm |
---

## 2. Nguồn dữ liệu: Porto Seguro's Safe Driver Prediction (~1.5M dòng)
## 1. Chi tiết 23 cột dữ liệu nguồn canonical (brvehins1)

| Nhóm cột | Kiểu dữ liệu | Ý nghĩa | Vai trò trong DWH / ML |
|---|---|---|---|
| id | INT | Mã định danh khách hàng / hợp đồng | Khóa nghiệp vụ (Business Key) cho Dim_Customer |
| target | INT (0/1) | Khách hàng có phát sinh bồi thường hay không | Biến mục tiêu (Target Label) cho mô hình Machine Learning |
| ps_ind_* | INT / FLOAT | Đặc trưng nhân khẩu học cá nhân (tuổi, giới tính, khu vực) | Thuộc tính cho Dim_Customer và Feature cho ML |
| ps_reg_* | FLOAT | Đặc trưng khu vực địa lý nơi đăng ký bảo hiểm | Thuộc tính phân nhóm vùng rủi ro |
| ps_car_* | INT / FLOAT | Đặc trưng phương tiện xe cơ giới (loại xe, độ tuổi xe) | Thuộc tính hợp đồng/phương tiện |
| ps_calc_* | FLOAT | Các chỉ số rủi ro tính toán nội bộ | Feature đầu vào cho mô hình dự đoán |
| STT | Tên cột nguồn (Source Column) | Nhóm nguồn (Source Group) | Kiểu dữ liệu thực tế (Physical Observed) | Kiểu logic đề xuất (Proposed Logical) | Đề xuất vai trò (Current Use Candidate) | Ý nghĩa nghiệp vụ & Ghi chú |
|---|---|---|---|---|---|---|
| 1 | `Gender` | DRIVER | string ('Female', 'Male', 'Corporate', nan) | VARCHAR(20) | DIMENSION CANDIDATE | Giới tính của người lái xe hoặc chính sách doanh nghiệp/tổ chức |
| 2 | `DrivAge` | DRIVER | string ('>55', '36-45', '18-25', '26-35', '46-55', nan) | VARCHAR(10) | DIMENSION CANDIDATE, ML CANDIDATE | Nhóm độ tuổi của người lái xe chính |
| 3 | `VehYear` | VEHICLE | int64 (1997, 2008, 2010, ...) | SMALLINT | DIMENSION CANDIDATE, ML CANDIDATE | Năm sản xuất / đời xe |
| 4 | `VehModel` | VEHICLE | string (tên hãng, dòng xe, thông số) | NVARCHAR(150) | DIMENSION CANDIDATE | Nhãn hiệu và model xe chi tiết |
| 5 | `VehGroup` | VEHICLE | string (tên nhóm dòng xe tổng hợp) | NVARCHAR(100) | DIMENSION CANDIDATE, ML CANDIDATE | Nhóm dòng xe chuẩn hóa |
| 6 | `Area` | GEOGRAPHY | string ('Interior', 'Met. Porto Alegre...', ...) | NVARCHAR(100) | DIMENSION CANDIDATE, ML CANDIDATE | Khu vực vận hành (vùng đô thị, nội địa, tiểu vùng) |
| 7 | `State` | GEOGRAPHY | string ('Rio de Janeiro', 'Sao Paulo', ...) | NVARCHAR(50) | DIMENSION CANDIDATE | Tên đầy đủ của bang tại Brazil (27 bang/đơn vị liên bang) |
| 8 | `StateAb` | GEOGRAPHY | string (2 ký tự: 'RJ', 'SP', 'RS', ...) | CHAR(2) | DIMENSION CANDIDATE, ML CANDIDATE | Mã viết tắt bưu chính của bang tại Brazil |
| 9 | `ExposTotal` | EXPOSURE | float64 (1.01, 3.0, 4.55, ...) | DECIMAL(6,4) | FACT MEASURE, ML CANDIDATE | Tổng thời gian phơi nhiễm rủi ro tính theo xe-năm (car-years) |
| 10 | `ExposFireRob` | EXPOSURE | int64 / float64 | DECIMAL(6,4) | FACT MEASURE, REQUIRES REVIEW | Thời gian phơi nhiễm riêng cho rủi ro cháy và cướp xe |
| 11 | `PremTotal` | PREMIUM | float64 (742.75, 5025.68, ...) | DECIMAL(12,2) | FACT MEASURE | Tổng doanh thu phí bảo hiểm đã thu (đơn vị BRL) |
| 12 | `PremFireRob` | PREMIUM | int64 / float64 | DECIMAL(12,2) | FACT MEASURE, REQUIRES REVIEW | Phí bảo hiểm thu riêng cho rủi ro cháy và cướp xe (BRL) |
| 13 | `SumInsAvg` | SUM_INSURED | float64 (10852.99, 301889.74, ...) | DECIMAL(14,2) | FACT MEASURE, ML CANDIDATE | Giá trị bảo hiểm trung bình / giá trị ước tính của xe (BRL) |
| 14 | `ClaimNbRob` | CLAIM_COUNT | int64 (0, 1, 2, ...) | INT | FACT MEASURE, TARGET/LEAKAGE | Số vụ bồi thường do cướp xe (Robbery) |
| 15 | `ClaimNbPartColl` | CLAIM_COUNT | int64 (0, 1, 2, ...) | INT | FACT MEASURE, TARGET/LEAKAGE | Số vụ bồi thường do va chạm một phần (Partial Collision) |
| 16 | `ClaimNbTotColl` | CLAIM_COUNT | int64 (0, 1, 2, ...) | INT | FACT MEASURE, TARGET/LEAKAGE | Số vụ bồi thường do va chạm toàn bộ / tổn thất toàn bộ (Total Collision) |
| 17 | `ClaimNbFire` | CLAIM_COUNT | int64 (0, 1, 2, ...) | INT | FACT MEASURE, TARGET/LEAKAGE | Số vụ bồi thường do hỏa hoạn (Fire) |
| 18 | `ClaimNbOther` | CLAIM_COUNT | int64 (0, 1, 2, ...) | INT | FACT MEASURE, TARGET/LEAKAGE | Số vụ bồi thường do các nguyên nhân khác (Other) |
| 19 | `ClaimAmountRob` | CLAIM_AMOUNT | int64 / float64 | DECIMAL(14,2) | FACT MEASURE, TARGET/LEAKAGE | Số tiền chi trả bồi thường do cướp xe (BRL) |
| 20 | `ClaimAmountPartColl` | CLAIM_AMOUNT | int64 / float64 | DECIMAL(14,2) | FACT MEASURE, TARGET/LEAKAGE | Số tiền chi trả bồi thường do va chạm một phần (BRL) |
| 21 | `ClaimAmountTotColl` | CLAIM_AMOUNT | int64 / float64 | DECIMAL(14,2) | FACT MEASURE, TARGET/LEAKAGE | Số tiền chi trả bồi thường do va chạm toàn bộ (BRL) |
| 22 | `ClaimAmountFire` | CLAIM_AMOUNT | int64 / float64 | DECIMAL(14,2) | FACT MEASURE, TARGET/LEAKAGE | Số tiền chi trả bồi thường do hỏa hoạn (BRL) |
| 23 | `ClaimAmountOther` | CLAIM_AMOUNT | int64 / float64 | DECIMAL(14,2) | FACT MEASURE, TARGET/LEAKAGE | Số tiền chi trả bồi thường do các nguyên nhân khác (BRL) |

## 3. Bảng đích DWH: Fact_Customer_Risk_Prediction (Kết quả Machine Learning)
---

| Tên cột | Kiểu dữ liệu | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| PredictionFactKey | BIGINT | PRIMARY KEY IDENTITY | Khóa thay thế (Surrogate Key) của bảng sự kiện dự đoán |
| CustomerKey | INT | FOREIGN KEY | Liên kết tới Dim_Customer(CustomerKey) |
| DateKey | INT | FOREIGN KEY | Ngày thực hiện dự đoán, liên kết tới Dim_Date(DateKey) |
| PredictedClaimProbability | DECIMAL(6,4) | NOT NULL | Xác suất dự đoán phát sinh tổn thất (0.0000 - 1.0000) |
| RiskCategory | NVARCHAR(20) | NOT NULL | Phân loại mức độ rủi ro ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') |
| ModelVersion | NVARCHAR(50) | NOT NULL | Phiên bản mô hình ML được sử dụng (VD: 'LightGBM_v1.0') |
| CreatedDate | DATETIME2 | DEFAULT UTC | Thời điểm ghi nhận bản ghi |
## 2. Phân loại theo nhóm nguồn (Source Groups)

- **DRIVER**: `Gender`, `DrivAge` (nhân khẩu học và đặc tính người lái).
- **VEHICLE**: `VehYear`, `VehModel`, `VehGroup` (đặc điểm phương tiện tham gia bảo hiểm).
- **GEOGRAPHY**: `Area`, `State`, `StateAb` (vùng địa lý rủi ro và mã bang tại Brazil).
- **EXPOSURE**: `ExposTotal`, `ExposFireRob` (thời gian phơi nhiễm rủi ro tính bằng car-years).
- **PREMIUM**: `PremTotal`, `PremFireRob` (doanh thu phí bảo hiểm).
- **SUM_INSURED**: `SumInsAvg` (giá trị được bảo hiểm).
- **CLAIM_COUNT**: `ClaimNbRob`, `ClaimNbPartColl`, `ClaimNbTotColl`, `ClaimNbFire`, `ClaimNbOther` (tần suất sự kiện bồi thường theo từng loại rủi ro).
- **CLAIM_AMOUNT**: `ClaimAmountRob`, `ClaimAmountPartColl`, `ClaimAmountTotColl`, `ClaimAmountFire`, `ClaimAmountOther` (mức độ nghiêm trọng tổn thất theo từng loại rủi ro).

---

## 3. Ghi chú về nguồn dữ liệu Legacy (susep.gov.br)

- File: `data/raw/susep.gov.br/insurance_dataset.csv` (~751 MB).
- Bản chất: Đây là dữ liệu báo cáo thống kê thị trường vĩ mô theo tháng của cơ quan quản lý bảo hiểm Brazil (SUSEP) thu thập từ năm 2003.
- Định vị: Được phân loại là **LEGACY / NON-CANONICAL SOURCE**. Giữ lại để đối chiếu vĩ mô khi cần thiết, nhưng không tham gia vào luồng ETL, Staging, DWH Star Schema hay Machine Learning của hệ thống hiện tại.
