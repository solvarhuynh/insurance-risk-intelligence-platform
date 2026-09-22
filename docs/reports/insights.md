# Insight Nghiệp vụ — Phân tích & Dự đoán Rủi ro
# Insight Nghiệp vụ — Phân tích & Dự đoán Rủi ro Xe cơ giới

Trạng thái: Khung cấu trúc insight phân tích và đối chiếu rủi ro dự đoán (Giai đoạn 8 — Power BI & Insight).
Trạng thái: Khung cấu trúc insight phân tích và đối chiếu rủi ro dự đoán (Giai đoạn 8 — Power BI & Insight) dựa trên dataset canonical `brvehins1`.

Khi hoàn thành Giai đoạn 8, tài liệu này sẽ tổng hợp các nhận định phân tích cụ thể, có số liệu dẫn chứng và đề xuất hành động kinh doanh:

## 1. Xu hướng phí và bồi thường theo thời gian
- Phân tích chu kỳ mùa vụ của doanh thu phí bảo hiểm (`Fact_Premium`) và bồi thường tổn thất (`Fact_Claims`) từ 2003 đến nay.
## 1. Xu hướng phí, thời gian chịu rủi ro và tổn thất bồi thường
- Phân tích tương quan giữa doanh thu phí bảo hiểm (`PremTotal`), thời gian chịu rủi ro (`ExposTotal`), và tổng chi trả bồi thường theo 5 loại rủi ro (Robbery, Partial Collision, Total Collision, Fire, Other).
- [Chờ số liệu từ DWH].

## 2. Phân tích Loss Ratio theo bang và dòng sản phẩm
- Tỷ lệ tổn thất (Loss Ratio = Claims / Premium) theo từng bang tại Brazil (SP, RJ, MG, RS, etc.).
- Nhận diện các bang có tỷ lệ tổn thất vượt ngưỡng an toàn (>70%).
## 2. Phân tích Loss Ratio theo bang và nhóm loại xe
- Tỷ lệ tổn thất (Loss Ratio = Total Claims Amount / Total Premium) theo từng bang tại Brazil (SP, RJ, MG, RS, v.v.) và phân nhóm xe (`VehGroup`, `VehYear`).
- Nhận diện các phân khúc xe hoặc khu vực địa lý có tỷ lệ tổn thất vượt ngưỡng an toàn (>70%).
- [Chờ số liệu từ DWH].

## 3. Đối chiếu giữa Rủi ro Dự đoán (ML Risk Scoring) và Tổn thất Thực tế
- Đánh giá mức độ tương quan giữa nhóm rủi ro dự đoán của mô hình (`Fact_Customer_Risk_Prediction`: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL') và tỷ lệ phát sinh bồi thường thực tế.
- Kiểm chứng hiệu quả phân tầng rủi ro phục vụ thẩm định hợp đồng (Underwriting Risk Stratification).
- Đánh giá mức độ tương quan giữa phân tầng rủi ro từ mô hình Machine Learning (`Fact_Vehicle_Risk_Prediction`: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL') và tần suất/chi phí bồi thường thực tế.
- Kiểm chứng hiệu quả phân tầng rủi ro phục vụ thẩm định và định giá xe cơ giới (Underwriting Risk Stratification).
- [Chờ số liệu từ DWH].

## 4. Phát hiện bất thường và khuyến nghị hành động
- Đề xuất điều chỉnh chính sách định phí (Pricing Strategy) cho các nhóm rủi ro cao.
- Cảnh báo các khu vực có tỷ lệ tổn thất đột biến để tăng cường thẩm định hiện trường.
- Đề xuất điều chỉnh chính sách định phí (Pricing Strategy) cho các nhóm xe có tỷ lệ rủi ro cao hoặc độ tuổi tài xế trẻ (`DrivAge`).
- Cảnh báo các khu vực có tỷ lệ mất cắp/cướp giật (`ClaimNbRob`, `ClaimAmountRob`) đột biến để tăng cường thẩm định hiện trường.
- [Chờ số liệu từ DWH].
