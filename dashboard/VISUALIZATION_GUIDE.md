# Trực quan hóa dữ liệu: kiến thức bài giảng và áp dụng vào dashboard

Tài liệu này có hai phần: kiến thức có thể tra cứu cho dự án khác, và audit/thiết kế của Insurance Data Platform. Nguồn lý thuyết chính là bộ bài giảng **Tương tác dữ liệu trực quan**, ThS. Đoàn Minh Trí. Không coi màu, CSS hay tính năng tự chọn của dự án là quy định của giảng viên.

## 1. Nguồn, cách đọc và mức độ chắc chắn

Đã trích xuất chữ của toàn bộ **7 PDF / 360 trang**, render toàn bộ trang thành 32 contact sheets, quan sát cả những trang ít/không có text. Các trang quyết định quan trọng được render lớn để đọc chữ trong hình. Số trang dưới đây là **trang vật lý của PDF, đếm từ 1**, không phải số slide in ở chân trang. Không có chương 7/8 riêng trong thư mục; các bài có ghi tích hợp nội dung này không được coi là những PDF bổ sung.

| Mã nguồn | Tên file trong `lecture/` | Số trang | Nội dung thực sự xuất hiện |
|---|---|---:|---|
| C1 | `chuong1_tongquan_rutgon.pdf` | 29 | Mục tiêu, khám phá/trình bày, thông điệp, tối giản, ví dụ mã hóa trực quan, công cụ |
| C2 | `chuong2_Bieudo_dothi.pdf` | 72 | Thành phần chart, lựa chọn chart, màu, bar/line/area/scatter/bubble/pie/donut, tương tác Plotly |
| C3 | `chuong3_Bieudo_nangcao_GUISV.pdf` | 69 | Box/histogram/heatmap/treemap/violin, dual axis, bản đồ, reference/drop lines, tooltip |
| C4 | `GUISV_chuong4_tuongtac_voidulieu.pdf` | 46 | Grain, sorting/filtering/grouping, sets/hierarchy, binning, subtotal/percentage |
| C5 | `chuong5_cactruong_dulieu_tinhtoan.pdf` | 43 | Aggregation/distinct, ratio, ngày/chuỗi, Fixed LoD, báo cáo nhiều chart và bảng |
| C6 | `Chuong6_tableau.pdf` | 48 | Relationships/joins, calculated fields/table calcs, trend/reference, dashboard/story |
| C9 | `GSV_Chuong09_mohinhdubao.pdf` | 53 | Linear/logistic, residual, đánh giá, threshold, confusion matrix, tương tác với mô hình |

PDF là tài liệu học local, được bỏ qua bởi `.gitignore`; bản clone công khai có tài liệu tổng hợp này nhưng không kèm bản sao slide. Chữ trích xuất, ảnh đọc và ảnh kiểm thử nằm ngoài Git tại `D:\insurance-platform-archive-20261111\lecture-review`.

- **EXPLICIT**: slide nói/ghi trực tiếp, kể cả chữ nằm trong ảnh.
- **INFERRED**: suy luận từ minh họa hoặc cách vận dụng sang Dash; không gán thành phát biểu nguyên văn của giảng viên.
- **NOT FOUND**: “Không tìm thấy nội dung này trong bộ bài giảng đã kiểm tra.” Không đồng nghĩa nội dung đó không có giá trị hoặc không được dạy ở nơi khác.

## 2. Nguyên tắc có bằng chứng

| ID | Chủ đề | Nguyên tắc từ bài giảng | Nguồn/trang PDF | Mức | Ví dụ / cách dùng |
|---|---|---|---|---|---|
| V01 | Mục tiêu | Chuyển dữ liệu phức tạp thành hình để thấy mẫu, xu hướng, bất thường | C1 p4 | EXPLICIT | Đọc xu hướng thay vì đọc hàng trăm dòng tháng |
| V02 | Đối tượng và thông điệp | Bắt đầu từ điều muốn truyền đạt, người xem và ngữ cảnh; Less is More | C1 p7–10,18 | EXPLICIT | Phân biệt khám phá chưa biết với trình bày phát hiện đã biết |
| V03 | Chất lượng | Informative, efficient, aesthetic, novel | C1 p8–9 | EXPLICIT | Đẹp phải đi cùng khả năng đọc thông tin |
| V04 | Quy trình | Hiểu chart → chọn loại → làm rõ → kết hợp thông tin → thực hành | C2 p11 | EXPLICIT | Chọn chart trước khi tinh chỉnh CSS |
| V05 | Thành phần | Tiêu đề, trục, nhãn, chú giải, gridlines có chức năng riêng | C2 p13–14 | EXPLICIT | Tiêu đề nêu nội dung, legend giải thích màu/ký hiệu |
| V06 | Chọn chart | Theo mục tiêu so sánh, quan hệ, thành phần hoặc thời gian | C2 p15; C3 p50 | EXPLICIT | Không có loại biểu đồ tốt cho mọi câu hỏi |
| V07 | Mã hóa | Vị trí là nền; màu, hình, kích thước bổ sung thông tin | C2 p16,26; C1 p9,22 | EXPLICIT | Dùng nét đứt cùng màu để phân biệt đường |
| V08 | Màu nhất quán | Một biến giữ màu giữa các chart; tránh dùng lại màu gây lẫn ý nghĩa | C2 p29 | EXPLICIT | Premium và claim giữ màu qua trend/ranking |
| V09 | Điểm nhấn | Làm nổi bật thông tin chính, giảm nổi bật bối cảnh | C2 p27–28 | EXPLICIT | Một thanh dẫn đầu nổi hơn phần còn lại |
| V10 | Bar | Chiều dài/chiều cao so giá trị; bắt đầu trục số ở 0, dùng 2D, ghi nhãn | C2 p35–39 | EXPLICIT | Với bar ngang, áp dụng yêu cầu 0 cho trục X là INFERRED |
| V11 | Line/area | Theo dõi thời gian; hạn chế khoảng 3–4 đường, chọn tỷ lệ khung hợp lý | C2 p40–48 | EXPLICIT | Hai đường premium/claim đủ để trả lời câu hỏi xu hướng |
| V12 | Pie | Tổng phần bằng 100%; ít phần, tối đa khoảng 3–5, tránh 3D | C2 p15,57 | EXPLICIT | Nhãn trực tiếp thay legend khó dò; không dùng cho top-N thiếu phần còn lại |
| V13 | Histogram | Biến liên tục thành bins; giữ thứ tự trục số và không có khe giữa các bins | C3 p22–24,27,30 | EXPLICIT | Không trình bày score liên tục như danh mục rời rạc |
| V14 | Phân phối | Trung bình/bar có thể che phân tán, lệch và outlier | C3 p5,7–10,43,50 | EXPLICIT | Box/hist/violin trả lời những khía cạnh khác nhau |
| V15 | Dual axis | Có thể méo góc nhìn; ghi rõ trục/đường, cân nhắc small multiples | C3 p51–52 | EXPLICIT | Không ghép % và tiền bằng hai thang tùy ý |
| V16 | Không gian | Bản đồ phải phục vụ thông điệp, không chỉ là hình học đẹp | C1 p11–17; C3 p53,60 | EXPLICIT | Diện tích vùng địa lý có thể làm lệch cảm nhận quy mô |
| V17 | Tham chiếu | Reference/drop lines thêm ngữ cảnh; Plotly có spike line động | C3 p61–62 | EXPLICIT | Đường tham chiếu có mục tiêu thật, không tự tạo target |
| V18 | Tooltip | Giữ mặt chart gọn, bổ sung chi tiết khi hover/chạm | C3 p63; C2 p39,47,56 | EXPLICIT | Tên nguồn dài, cỡ mẫu, đơn vị trong hover; C3 p62–63 là tự học có hướng dẫn |
| V19 | Grain | Mức tổng hợp quyết định chart và lượng chi tiết nên hiển thị | C4 p6–10 | EXPLICIT | Dùng monthly aggregate thay hàng triệu quan sát |
| V20 | Sorting/filtering | Sắp xếp để so sánh; lọc để tập trung câu hỏi | C4 p13–21 | EXPLICIT | Top 10 sắp giảm; chỉ lọc bang khi muốn giới hạn population |
| V21 | Grouping/hierarchy | Split–apply–combine; hierarchy hỗ trợ drill-down/roll-up | C4 p23–29 | EXPLICIT | Year/month là thay mức tổng hợp, không phải mở raw policy |
| V22 | Tổng và tỷ trọng | Phân biệt grand total, subtotal, % toàn bộ, % trong nhóm | C4 p33–38; C5 p13–21 | EXPLICIT | Top-8 premium không phải toàn bộ premium |
| V23 | Đếm | COUNT và COUNT DISTINCT trả lời hai câu hỏi khác nhau | C5 p6–11 | EXPLICIT | Số observation không tự biến thành số customer |
| V24 | Tính tỷ lệ | Aggregate ratio có dạng SUM(numerator)/SUM(denominator) | C6 p11; C5 p13 | EXPLICIT | Claims/premiums của vùng là ratio of sums, không lấy mean các tỷ lệ |
| V25 | Ngày/nhãn | Xử lý chuỗi/ngày trước khi dựng báo cáo | C5 p23–26 | EXPLICIT | Nhãn gọn vẫn giữ mã gốc để tra cứu |
| V26 | LoD cố định | Phân biệt mức chi tiết view với benchmark ở grain cố định | C5 p28–32 | EXPLICIT | Tính theo group rồi gắn ngược bằng transform; hành vi filter phải do pipeline xác định |
| V27 | Phép tính bảng | View dimensions, hướng tính, partition ảnh hưởng kết quả | C6 p12–33 | EXPLICIT | Rank/% chạy trên population nào phải rõ |
| V28 | Dashboard/story | Story sắp logic từ bối cảnh → minh chứng → kết luận; có nhiều story points | C6 p39–45 | EXPLICIT | Một nhóm chart theo cùng câu hỏi, thay vì ghép các hình độc lập |
| V29 | Tổng hợp và bảng | Báo cáo có thể kết hợp subplots với bảng số | C5 p34–36 | EXPLICIT | Bảng là lựa chọn hợp lệ khi cần đọc giá trị chính xác |
| V30 | Mô hình | Đọc quan sát, dự báo, sai số và phạm vi dữ liệu cùng nhau | C9 p9–10,22–27,50 | EXPLICIT | Điểm số đẹp không đủ chứng minh mô hình tốt |
| V31 | Binary model | Logistic trả score/xác suất rồi mới chọn ngưỡng thành nhãn | C9 p28–38 | EXPLICIT | Ngưỡng 0,5 không phải quy luật bắt buộc |
| V32 | Đánh giá | Confusion matrix, precision/recall/F1 thay theo threshold | C9 p39–43,46–49 | EXPLICIT | Không suy TP/FP từ histogram thiếu nhãn thực tế |
| V33 | Chuyển sang Dash | Tách rõ population warehouse và held-out bằng hai nhóm có tiêu đề/cỡ mẫu | V19,V28,V30 | INFERRED | Cách bố trí của dự án, không phải mẫu Dash do giảng viên đưa |

Không áp dụng lời “lọc outlier” của C4 p14 thành quyền xóa quan sát bảo hiểm: nguồn bất biến, dữ liệu âm và Unknown vẫn giữ theo contract. Ví dụ code trong bài giảng là minh họa, cần đối chiếu ý nghĩa với dữ liệu thật.

## 3. Các loại dữ liệu đã tìm thấy

| Loại | Bằng chứng | Mức | Cách nhận diện |
|---|---|---|---|
| Định tính / phân loại | C2 p22–23; C3 p24; C4 p29 | EXPLICIT | Danh mục, quốc gia, sản phẩm, nhóm màu |
| Định lượng liên tục | C3 p22–24; C4 p29; C9 p8 | EXPLICIT | Tuổi/chiều cao, giá trị mục tiêu liên tục |
| Rời rạc / count | C3 p24; C5 p8 | EXPLICIT | Số dòng, số lượng theo nhóm; p24 đặt phân loại/rời rạc cạnh bar |
| Có thứ tự | C2 p24–25; C4 p29–31 | INFERRED | Dải màu mức độ, nhóm tuổi thấp→cao; chưa tìm thấy một phân loại lý thuyết độc lập về ordinal scale |
| Thời gian | C2 p40–48; C5 p24–26 | EXPLICIT | Ngày/tháng/năm có trình tự |
| Địa lý | C3 p53–60; C6 p38 | EXPLICIT | Tọa độ, địa giới hành chính |
| Nhị phân | C9 p28–31,39 | EXPLICIT | Nhãn 0/1; khác đầu ra số liên tục |
| Phân cấp | C3 p41–42; C4 p26–28 | EXPLICIT | Category→subcategory, quốc gia→thành phố |

## 4. Bảng lựa chọn biểu đồ

Các loại dưới đây đều được giới thiệu hoặc dùng làm ví dụ trong PDF. Cột lợi ích/hạn chế có nhãn riêng nếu phần đó do người viết suy luận. “Không nêu riêng” nghĩa là không tìm thấy phát biểu tương ứng; không tự thêm thành lời giảng.

| Loại và nguồn | Dữ liệu / mục tiêu | Cách đọc | Lợi ích từ bài giảng | Hạn chế / mức nguồn | Ví dụ slide |
|---|---|---|---|---|---|
| Bar/column, gồm bar ngang — C2 p35–39 | Nhóm + số; so sánh/xếp hạng | So chiều dài từ 0 | Đơn giản, hiệu quả so danh mục — EXPLICIT | 3D gây khó đọc, cần trục 0 — EXPLICIT | Số lượng trái cây |
| Grouped / stacked / 100% stacked bar — C4 p45; C5 p19–21 | Nhóm và nhóm con; thành phần/tỷ trọng | Tổng cột và từng phần | So đóng góp trong nhóm — INFERRED từ bài tập | Nhiều phần khó dò; không nêu riêng | % tip theo nhóm hóa đơn/giới; đơn hàng trong vùng |
| Line — C2 p40–48 | Thời gian + số; xu hướng | Chiều thay đổi theo X | Theo dõi thay đổi thời gian — EXPLICIT | Nhiều đường rối, tỷ lệ khung có thể gây sai cảm nhận — EXPLICIT | Doanh thu theo tháng |
| Area — C2 p15,40–48 | Thời gian + số; nhấn lượng | Giá trị/diện tích dưới đường | Nhấn tổng lượng — EXPLICIT | Phần phủ có thể làm khuất chuỗi khác — INFERRED; không phải mặc định cộng dồn | Doanh thu hai năm |
| Scatter — C2 p49–56 | Hai số; quan hệ/cụm/outlier | Mỗi điểm có X/Y | Thấy tương quan, cụm, ngoại lệ — EXPLICIT | Quan hệ không tự chứng minh nhân quả — INFERRED | Chi phí quảng cáo và doanh thu |
| Bubble — C2 p54–56,63 | Hai số + cỡ + nhóm | Vị trí, diện tích/cỡ điểm, màu | Kết hợp nhiều chiều — EXPLICIT | Phải giải thích kích thước; so diện tích khó hơn chiều dài — INFERRED | GDP, tuổi thọ, dân số |
| Pie/donut — C2 p57–62 | Phần của tổng 100% | So phần/quạt, đọc nhãn | Thấy quan hệ phần–tổng — EXPLICIT | Khó so diện tích chính xác; khoảng 3–5 phần, tránh 3D — EXPLICIT | Thị phần 5 công ty |
| Box plot — C3 p7–21 | Phân phối số theo nhóm | Median, quartiles, whiskers, outlier | Cô đọng độ phân tán/lệch/ngoại lệ — EXPLICIT | Có thể giấu hai đỉnh — EXPLICIT p50 | Lương phòng ban, điểm sinh viên |
| Histogram — C3 p22–30 | Số liên tục đã chia bins | Count/mật độ theo khoảng có thứ tự | Thấy hình dáng/hội tụ phân phối — EXPLICIT | Kết quả phụ thuộc bins; thiếu mốc tứ phân vị — EXPLICIT p27,50 | Điểm, chiều cao |
| Heatmap — C3 p31–37 | Ma trận và số | Màu ô + colorbar + nhãn | Thấy mức độ, mẫu/correlation — EXPLICIT | Cần đúng dải màu/phạm vi; giới hạn đọc chính xác là INFERRED | Ma trận Pearson |
| Treemap — C3 p31,38–42 | Phân cấp + giá trị không âm | Diện tích ô, cha→con, màu | Thấy tỷ trọng/phân cấp — EXPLICIT | Không nêu riêng; so diện tích chính xác khó là INFERRED | Category→subcategory, Sales/Profit |
| Violin — C3 p43–50 | Phân phối số từng nhóm | Bề rộng mật độ và box/quartiles | Thấy hình dạng phân phối lẫn thống kê — EXPLICIT | Cần chọn smoothing; không dựng KDE từ aggregate bins như raw — INFERRED | Chi tiêu Nam/Nữ |
| Dual-axis combination — C3 p51–52 | Hai số khác đơn vị | Đọc đúng trục của từng chuỗi | So biến khác đơn vị — EXPLICIT | Perspective distortion; cân nhắc small multiples — EXPLICIT | Doanh số và % tăng trưởng |
| Proportional-symbol map — C3 p53–56 | Tọa độ + số | Vị trí địa lý và cỡ điểm | Khám phá ngữ cảnh không gian — EXPLICIT | Chồng lấp điểm; không nêu riêng | Doanh thu tại thành phố |
| Choropleth — C3 p53,57–60 | Vùng địa lý + số/mức | Màu vùng theo colorbar | Thấy pattern địa lý — EXPLICIT | Diện tích vật lý có thể gây lệch cảm nhận — EXPLICIT p60 | Chỉ số quốc gia/tỉnh |
| Cartogram minh họa — C1 p15–16; C3 p60 | Vùng được biến dạng/ô hóa theo thông điệp | Đọc vùng theo tỷ trọng được quy định | Ưu tiên thông điệp hơn diện tích vật lý — EXPLICIT | Cần hiểu cách biến đổi — INFERRED; không có hướng dẫn code riêng | Bản đồ bầu cử Mỹ |
| Table / crosstab — C4 p34–36; C5 p35–36; C6 p22–25 | Nhiều nhóm và số chính xác | Hàng/cột, subtotal/grand total | Kết hợp bảng và chart — EXPLICIT | Khó nhìn xu hướng dài — INFERRED | Pivot tổng doanh số, báo cáo category |
| Scatter + regression / residual plot — C9 p16–27 | X/Y/ŷ và sai số | Đường xu hướng, residual quanh 0 | Chẩn đoán tuyến tính, ngoại lệ, phương sai — EXPLICIT | Không ngoại suy mù quáng; đẹp không đảm bảo đúng — EXPLICIT | Giờ học và điểm |
| Sigmoid / decision-boundary plot — C9 p36–38,48 | z→p hoặc hai biến đầu vào | p và đường ngưỡng/vùng phân lớp | Hiểu score→class — EXPLICIT | Không bắt buộc ngưỡng 0,5; cần phạm vi dữ liệu — EXPLICIT | Đạt/không đạt |
| Confusion-matrix heatmap — C9 p39–43 | Nhãn thật và nhãn dự đoán | TN/FP/FN/TP theo trục thật/dự đoán | Nhìn loại lỗi — EXPLICIT | Đổi threshold đổi ma trận; không chỉ nhìn accuracy — EXPLICIT | Logistic học tập |
| Metric vs threshold — C9 p41–43,47 | Ngưỡng và precision/recall/F1 | X là τ, Y là metric | Khám phá trade-off — EXPLICIT | Xu hướng “thường” tăng/giảm không là bảo đảm mọi mẫu — EXPLICIT theo cách diễn đạt p42 | Slider cập nhật nhiều tín hiệu |

Các biến thể reference line, drop line, marker/line style là kỹ thuật bổ trợ, không phải lý do phải tăng số chart. Không suy quartiles hoặc dữ liệu điểm chính xác từ các bin count.

## 5. Nguyên tắc màu

| ID / chủ đề | Điều giảng viên hướng dẫn | Ví dụ | Trang PDF | Mức |
|---|---|---|---|---|
| M01 / phối màu | Có complementary, triadic, analogous qua color wheel | Ba sơ đồ vòng màu | C2 p17 | EXPLICIT |
| M02 / phân loại | Màu phân biệt nhóm không có thứ tự | Tên người/nhóm thành các màu khác nhau | C2 p22–23,30 | EXPLICIT |
| M03 / tuần tự | Sáng→đậm cho đại lượng tăng; tránh rainbow cho mức độ | Bản đồ hai cách tô | C2 p24,33 | EXPLICIT |
| M04 / phân kỳ | Hai phía của trung điểm rõ ràng | Giá trị dưới/trên trung bình | C2 p25 | EXPLICIT |
| M05 / tối giản | Hạn chế quá nhiều màu, tạo điểm nhấn | Pie ít phần, một cột được nhấn | C2 p22,27–28,31 | EXPLICIT |
| M06 / tiếp cận | Bảng màu vẫn hiểu với người mù màu | Ví dụ dạng suy giảm nhận biết màu | C2 p19,22 | EXPLICIT |
| M07 / ngữ nghĩa | Giữ màu cho biến; giải thích ý nghĩa bằng chú thích/legend/nhãn màu | Gradient, swatches, tên chuỗi cùng màu | C2 p29,32 | EXPLICIT |
| M08 / hình và nét | Dùng nét đậm/nhạt, hình để thêm phân biệt | Hình vuông/tròn/tam giác, đường đậm | C2 p26–28 | EXPLICIT |
| M09 / nền | Giảm nổi bật phần nền để thấy dữ liệu | Các đường bối cảnh nhạt, điểm trọng tâm rõ | C1 p17; C2 p27–28 | INFERRED cho màu nền/card UI |

**Thiết kế triển khai của repo**, không phải palette bắt buộc của bài giảng: premium navy `#003366`; claim và observed HasClaim đất cam `#b66a45`; model score tím `#7560a6`; counts/context xám; sau index teal `#007c83`. Nền xanh xám/card trắng giữ theo yêu cầu owner. Nét đứt/marker, nhãn và tooltip bổ sung màu; việc chọn HEX hay kiểm tỷ lệ tương phản là quyết định kỹ thuật. Màu cam chỉ nhận diện đại lượng, không tự khẳng định “xấu”. Xanh/đỏ chỉ dùng khi có phép so sánh và hướng đánh giá đã nói rõ.

## 6. Bố cục, tương tác và storytelling

| Thành phần / ID | Nguyên tắc | Bằng chứng và mức |
|---|---|---|
| D01 / câu hỏi | Xác định câu hỏi → trường tính → tổng hợp → trực quan | C5 p34, EXPLICIT |
| D02 / tiêu đề, nhãn, legend | Nêu nội dung, giá trị, hệ trục, ý nghĩa màu/ký hiệu | C2 p13,35, EXPLICIT |
| D03 / thứ tự | Dẫn từ bối cảnh qua minh chứng đến kết luận | C6 p43–45, EXPLICIT |
| D04 / nhóm chart | Gom chart liên quan vào dashboard; nhiều dashboard thành story | C6 p39–45, EXPLICIT |
| D05 / mật độ | Giữ thông tin có lý do xuất hiện; tránh quá nhiều đường/màu | C1 p10,18; C2 p31,40, EXPLICIT |
| D06 / bảng | Bảng cùng subplots là một cấu trúc báo cáo hợp lệ | C5 p35–36, EXPLICIT |
| D07 / tương tác | Filter, highlight, drill-down; tooltip và zoom/pan Plotly | C6 p43; C4 p26; C2 p39,47; C1 p28, EXPLICIT |
| D08 / model | Một điều khiển threshold có thể cập nhật nhiều visual/metric | C9 p43,47–49, EXPLICIT |
| D09 / đơn vị | Ghi đơn vị/khung tham chiếu theo trục; không ghép thang thiếu nhãn | C2 p35–36; C3 p52, EXPLICIT |
| D10 / khoảng cách và chữ | Chừa chỗ nhãn/legend, tăng cỡ chữ trên màn hình nhỏ | V05,V18 và tính dễ đọc; INFERRED, không có số px bắt buộc |
| D11 / responsive | Grid 2 cột xuống 1 cột trên mobile, bảng có vùng cuộn riêng | INFERRED cho Dash; không có breakpoint cụ thể trong PDF |

C6 p47 còn có rubric mini project: bố cục rõ/dễ đọc, filter/parameter dễ tương tác, caption hợp lý và insight ngắn gọn (**EXPLICIT**, chữ nằm trong ảnh đề). Yêu cầu ≥8 sheet/loại chart, ≥3 story points và publish Tableau Public là **yêu cầu bài tập cụ thể**, không áp thành số chart tối thiểu hay yêu cầu đổi công nghệ của dự án cá nhân này.

**Những giới hạn đã tìm nguồn:** slicer như một loại control riêng; drill-through sang trang đích; giao thức cross-filter giữa hai chart; tỷ lệ tương phản WCAG cụ thể; font Inter; mã HEX; grid 12 cột, F/Z pattern và breakpoint mobile; biểu đồ calibration/reliability diagram chuyên biệt; ROC/PR curve và công thức ROC-AUC/AP: **NOT FOUND — Không tìm thấy nội dung này trong bộ bài giảng đã kiểm tra.** PDF có filter, drill-down, confusion matrix và precision/recall nhưng không được đồng nhất chúng với những mục trên. Calibration ở repo là so score theo bin với quan sát, không gán đây là kỹ thuật giảng viên đã dạy.

Với dự án khác: viết câu hỏi và grain trước; chọn chart từ bảng; định nghĩa denominator và phạm vi filter; chỉ thêm tương tác phục vụ câu hỏi; kiểm số rồi xem hình trên màn hình thật. Không chuyển yêu cầu sinh data trong bài tập thành quyền tạo data cho dự án thực.

## 7. Audit phiên bản trước khi chỉnh code

Audit ngày 11/11/2026, dựa vào `dashboard/app.py`, `data/dashboard.json`, `dashboard/STORY.md` và trình duyệt. Không ghi nhận lỗi tính tổng/ratio hiện hữu. Cỡ mẫu, đơn vị nguồn chưa xác nhận và ngày benchmark vẫn là ranh giới nghiệp vụ. Ảnh ban đầu phải đợi callback có dữ liệu; trục mặc định khi callback chưa xong không phải một chart rỗng đã nghiệm thu.

| Trang / visual | Câu hỏi, dữ liệu, khả năng đọc | Vấn đề và mức | Quy tắc | Quyết định / đề xuất |
|---|---|---|---|---|
| Market / KPI | Tổng premium/claim, ratio of sums, số observation cùng filter | LOW: màu icon claim chưa trùng series; badge rõ cùng kỳ, không cần tạo thêm KPI xấu | V08,V24 | **REVISE** màu nhận diện; giữ công thức và so tháng tương ứng |
| Market / trend | Premium và claims biến động khi nào? Monthly/annual cùng population, cùng source units | MEDIUM: area fill không cần thiết, hai đường chỉ phân biệt bằng màu; legend ngoài chart không đi cùng PNG | V05,V07,V11,V18 | **REVISE** giữ line, bỏ fill, claim nét đứt, đưa legend trong plot; trục 0; hover nêu kỳ và partial year |
| Market / company ranking | Công ty nào dẫn premium? 10 nhóm cùng filter, full name trên hover | LOW: chưa có tỷ trọng so toàn selection; trục số thiếu tên trong ảnh PNG | V10,V18,V20,V22 | **REVISE** bar ngang sorted; ghi đơn vị ở trục, % selection trong hover; không biến top10 thành toàn market |
| Market / product ranking | Dòng nào tập trung premium? 8 nhóm, khác chiều company | LOW: tương tự company; hai chart bổ sung nhau, không phải trùng dữ liệu | V06,V10,V22 | **REVISE** giữ bar, mã nguồn/nhãn đầy đủ trong hover; không thay bằng pie thiếu phần còn lại |
| Motor / KPI | 3 KPI warehouse; mean score held-out | HIGH: đặt cạnh nhau khiến hai population trông cùng mẫu | V19,V28,V30,V33 | **REVISE** tách nhóm warehouse và held-out, giữ cả 4 KPI; không thay denominator |
| Motor / score histogram | Count theo score 0–1, bins đều 0,05; 20.000 held-out mặc định | HIGH: width 0,038 tạo khe cho biến liên tục; tô navy dưới 0,20 chưa có chú thích ý nghĩa | V13,V08,V18 | **REVISE** bins liền rộng 0,05, đủ 20 bins kể cả zero, score màu tím, chú thích mốc 0,20 là mô tả chứ không ngưỡng quyết định |
| Motor / observed vs score | Hai số theo band có thứ tự; cỡ mẫu hover | MEDIUM: X midpoint chưa phải mean score; hai màu trùng nghĩa với market; không thấy bin range trên hover; dễ nối qua band không có mẫu | V08,V18,V30 | **REVISE** giữ 2 line, observed cam / mean score tím đứt; hiện range/count; gap khi zero observations; không gọi future probability |
| Motor / age | HasClaim/observations theo nhóm tuổi có thứ tự | MEDIUM: teal có thể nhầm nghĩa favorable; thiếu benchmark selected population | V17,V18,V24 | **REVISE** bar cam, Unknown xám; reference = ratio of sums của warehouse đang lọc, hover nêu tử/mẫu; không suy nhân quả |
| Motor / Gender label counts | Thành phần observation, không phải claim rate; có Corporate/Unknown | LOW: màu teal làm giống trạng thái tích cực; vị trí hiện tại không giải thích rõ sample cho age | V19,V20,V28 | **REVISE** giữ bar ngang, màu count xám; đặt cạnh age trong cùng nhóm warehouse; hover có % và count |
| Data / KPI | Tổng 2 fact độc lập, count reconciliation 2/2, historical reads/storage | LOW: giữ ngày evidence, không coi reconciliation thay full DQ | V19,V23,V30 | **KEEP** chỉ dẫn nguồn/phạm vi; không biến benchmark thành số đo mới |
| Data / aggregate table | Xem giá trị month/state hoặc segment thật; 15 hàng/trang | LOW: đơn vị risk premium/claim chưa rõ ngay cạnh bảng | V19,V24,V29 | **REVISE** giữ bảng/filter/pagination; thêm caption đơn vị, không ép thành chart |
| Data / SQL benchmark | Before/after logical reads của 2 workload lịch sử | HIGH: thanh bắt đầu trên log axis làm độ dài không tỷ lệ giá trị, trái yêu cầu bar từ 0 | V10,V05 | **REVISE** giữ grouped bar nhưng đổi **linear từ 0**, nhãn Q1/Q2 ngắn, số đọc chính xác trên thanh/hover; số after nhỏ là đúng độ lớn, bên cạnh có %/absolute |

Không có **CRITICAL** đã xác nhận. HIGH là nguy cơ diễn giải/encoding, không phải phát hiện dữ liệu nguồn sai. LOW/MEDIUM không có nghĩa phải bỏ chart. Mỗi visual hiện hữu đã có quyết định; không có chart bị bỏ chỉ vì trông đơn giản.

### Không thêm chart khi thiếu dữ liệu hoặc không phục vụ câu hỏi

- **BLOCKED:** ROC/PR curve chính xác, confusion matrix tương tác theo ngưỡng tùy ý: snapshot không có từng score/label. Bins có count và positives hỗ trợ một số ngưỡng đúng biên nhưng không khôi phục được thứ tự trong bin; không thêm approximation như kết quả chính xác. Bài C9 dạy threshold/confusion matrix, không có nghĩa dự án buộc phải thêm.
- **BLOCKED:** box/violin của score thô hoặc claim event: aggregate bins không cung cấp phân phối điểm thật/quartiles, nguồn không có claim-event identity được chứng minh.
- **Không chọn / không phải REMOVE chart hiện hữu:** pie/treemap/map/dual axis. Ranking cần so độ dài chính xác; top-N thiếu phần còn lại; geography filter hiện đủ cho câu hỏi; không cần tải geometry, tạo điểm tọa độ hay thêm hai trục. Dựa V06,V12,V15,V16.
- Cross-filter click giữa chart và drill-through chưa có trong baseline. Giữ filter chung/state/year và đổi monthly/annual; không báo đã kiểm tính năng chưa được triển khai. Monthly/annual là roll-up mức tổng hợp, không phải truy cập policy raw.

## 8. Thiết kế đã chọn trước khi sửa app

1. **Market:** phạm vi → KPI → xu hướng → hai lát cắt concentration cùng premium. Hai ranking cùng state/year, không join company với product. Insight phải thay theo filter và không gọi ratio là lợi nhuận.
2. **Motor:** bối cảnh toàn warehouse → age và observation mix → bối cảnh mẫu held-out → histogram và observed-vs-score. Hai phần có tiêu đề/cỡ mẫu riêng, cùng geography filter nhưng denominator khác. Một câu insight kết nối phân bố score và quan sát theo score; mẫu nhỏ vẫn hiện cỡ mẫu.
3. **Data:** counts/reconciliation → bảng aggregate → bằng chứng benchmark lịch sử và cost. Số liệu table/snapshot và benchmark dùng hai mốc thời gian riêng.

Giữ Dash, snapshot, CSV/PNG, reset, filter session, sidebar ba mục tiếng Anh, KPI căn giữa và banner SVG của owner. Cải thiện typography/spacing có mục tiêu, không thay logo hay biến tài liệu thành đồ án môn học.

**Backup trước sửa code:** `D:\insurance-platform-archive-20261111\lecture-review\before-redesign.zip`, gồm README đang có phần engineering chưa commit, dashboard/assets, tests và aggregate evidence; không gồm `.env`/raw/model binary. Hash snapshot/evidence/model được ghi ngoài Git để đối chiếu sau sửa. Tài liệu này được tạo trước chỉnh app; mục nghiệm thu bên dưới chỉ cập nhật sau khi chạy thật.

## 9. Nghiệm thu

Đã thực hiện ngày **11/11/2026** trên snapshot có `exported_at_utc = 2026-11-11T01:26:23+00:00`:

- **11 unit tests PASS.** Kiểm tổng khi Monthly/Annual, filter/grain, phân trang aggregate; khôi phục count/positives/score sum từ 20 bins cho ALL/SP/AC; band rỗng không nối đường; reference tuổi là ratio of sums theo bang; share ranking dùng toàn selection; benchmark giữ đúng số đọc và trục linear từ 0.
- **Static validator PASS** cho Python, thứ tự migration, liên kết tài liệu và snapshot. `git diff --check` không có lỗi whitespace.
- **Edge/Playwright PASS trên Python local 8052 và Docker/Gunicorn 8050.** Cả ba trang ở 390/768/1024/1440/1920 px; filter bang/năm, Reset, Monthly/Annual, hai nguồn bảng và phân trang, CSV/PNG, tooltip thực tế, nhãn population, font local, `/healthz`; không có page error/HTTP lỗi hoặc tràn ngang cả trang. Bảng rộng cuộn trong vùng riêng.
- **Đã xem ảnh từng trang ở desktop/mobile và tablet.** Rút tên trục ranking thành `Premiums (B)` để không bị cắt ở mobile; subtitle/hover vẫn giải thích billions of source units. Chú thích reference tuổi nằm trên vùng vẽ, không đè nhãn cột. Chụp lại trạng thái nghỉ, không để tooltip/focus kiểm thử dính vào ảnh README.
- **Sửa lỗi chuyển trang phát hiện qua browser:** nội dung Data có thể bị tái sử dụng sai sau Motor khi phân trang. Mỗi trang nay có React key riêng; kiểm tra lại bảng chỉ xuất hiện ở Data, model KPI chỉ ở Motor, và nút Next đổi hàng đúng.
- **Đối chiếu SHA-256 PASS:** `data/dashboard.json`, `data/evidence.json`, artifact `claim_risk_model_v001.joblib` giữ nguyên so backup. Không sửa raw, không train hay export lại snapshot. Chỉ rebuild/recreate service Dashboard với `--no-deps`; giữ volume SQL.

Ảnh đầy đủ và bảy crop README nằm ngoài Git tại `D:\insurance-platform-archive-20261111\lecture-review\local` và `...\docker`. Bảy crop mặc định từ bản Docker được cập nhật vào `dashboard/assets/`; banner và sơ đồ công cụ giữ nguyên. [STORY.md](STORY.md) giải thích câu hỏi và mạch chuyện từng trang; [README](../README.md) giữ nội dung insight và bổ sung phần Data Engineering.

**Giới hạn nghiệm thu:** không triển khai cross-filter bằng click chart hay drill-through; không báo PASS cho hai tính năng đó. ROC/PR curves chính xác, confusion theo threshold tùy ý và phân phối raw vẫn BLOCKED như mục 7. Đợt này không chạy lại SQL quality gates, DAG, training hoặc benchmark; evidence tháng 09 và lần kiểm SQL/DAG trước đợt giao diện giữ nguyên thời điểm, không coi là kết quả mới. Dashboard tiếp tục phục vụ aggregate snapshot, chưa có dữ liệu realtime hoặc xác thực người dùng.

## 10. Điều chỉnh theo phản hồi ngày 12/11/2026

- Badge Market dùng tam giác ▲/▼ và xanh/đỏ cho **dấu tăng/giảm của số**, kể cả tỷ lệ claims/premiums. Giá trị mặc định ▼ −4,9 điểm phần trăm nay đỏ. Đây là quy ước giao diện theo yêu cầu owner, **không phải kết luận nghiệp vụ** tỷ lệ thấp hơn là xấu.
- So sánh SQL trước đây dùng bar từ 0 theo V10 nên đúng tỉ lệ độ dài; nhưng mức giảm gần 99% khiến hai thanh sau rất nhỏ, còn Q1/Q2 thiếu nghĩa khi đọc nhanh. Theo mục tiêu **chọn cách biểu đạt giúp người xem trả lời câu hỏi** (V05,V19,V24; C2 p11, C5 p34–36), dùng hai thẻ số rõ tên workload, số reads trước/sau và % giảm. Không còn mã Q1/Q2 trong UI. Đây là quyết định triển khai theo dữ liệu hiện có, không gán thành quy tắc giảng viên dạy phải bỏ bar trong mọi trường hợp.
- Giữ **hai mốc thời gian riêng**: snapshot warehouse 11/11/2026 và benchmark SQL 24/09/2026. Hai covering indexes thêm 924,51 MB storage và có chi phí ghi; số page reads giảm không tự chứng minh thời gian end-to-end của dashboard giảm tương ứng.
