# Cách đọc và kể câu chuyện của dashboard

Tài liệu này giải thích **ba trang của ứng dụng Plotly Dash** theo cách có thể trình bày khi vấn đáp. Giao diện viết bằng tiếng Anh; tài liệu này viết bằng tiếng Việt để dễ học. Các con số ví dụ lấy từ snapshot SQL xuất ngày **11/11/2026** (`data/dashboard.json`), ở bộ lọc mặc định **All states** và toàn bộ khoảng thời gian. Đổi bộ lọc thì phải đọc lại số trên giao diện. Dashboard không truy vấn SQL trực tiếp mỗi khi tương tác.

Cơ sở lựa chọn biểu đồ, dẫn trang PDF, audit và các quyết định giữ/sửa nằm trong [VISUALIZATION_GUIDE](../docs/VISUALIZATION_GUIDE.md). Tài liệu này tập trung vào cách đọc dữ liệu và kể câu chuyện; không thay thế phần lý thuyết đó.

## Câu chuyện chung: dữ liệu có nguồn gốc → hiểu hiện tượng → kiểm giới hạn

1. **Market:** phí bảo hiểm và claims thay đổi thế nào; phần lớn premium nằm ở công ty và sản phẩm nào?
2. **Motor risk:** trong một nguồn khác, claim quan sát xuất hiện ở nhóm nào; model score có tách được nhóm có/không có `HasClaim` trên tập kiểm thử không?
3. **Data:** các con số trên lấy từ bản aggregate nào; kho dữ liệu đối soát ra sao; đánh đổi để truy vấn SQL nhanh hơn là gì?

Hai nguồn **không có khóa join theo từng bản ghi**. Vì vậy ba trang tạo một câu chuyện về *nền tảng phân tích bảo hiểm*, không phải một câu chuyện nhân quả xuyên từ thị trường SUSEP sang từng rủi ro xe. Hãy nói rõ điều này khi trình bày.

## Trang 1 — Market overview

**Câu hỏi lớn:** Thị trường thay đổi về quy mô và tỷ lệ claims/premiums như thế nào, và premium tập trung ở đâu?

**Trình tự đọc:** KPI tổng → biểu đồ thời gian → xếp hạng công ty → xếp hạng sản phẩm. Cả ba biểu đồ dùng **cùng bộ lọc bang và khoảng năm**, nên là ba góc nhìn trên cùng tập premium SUSEP. Tổng theo công ty và tổng theo sản phẩm đối soát với tổng tháng/bang; chúng không phải bảng giao nhau công ty × sản phẩm.

### KPI ở đầu trang

- `Total premiums`: tổng premium nguồn trong khoảng lọc, đơn vị ghi **source units** vì chưa xác nhận đầy đủ tiền tệ. Mặc định khoảng **3,05 nghìn tỷ**.
- `Total claims`: tổng claims báo cáo, khoảng **735,52 tỷ**. Đây là số tiền tổng hợp của nguồn, không phải số claim event.
- `Claims / premiums`: lấy **tổng claims chia tổng premiums** khi mẫu số dương; mặc định **24,1%**. Không phải lợi nhuận hay loss ratio được chuẩn hóa theo mọi loại sản phẩm.
- `Market observations`: **8.338.214** dòng fact ở bộ lọc mặc định. Một dòng là công ty × tháng × sản phẩm × bang.
- Badge biến động so **cùng các tháng của năm cuối được chọn với năm trước**, cùng bang. Với 2023, chỉ so tháng 01–07 với 01–07/2022: premium **+8,9%**, tỷ lệ claims/premiums **−4,9 điểm phần trăm**. Màu badge chỉ diễn đạt chiều biến động, không chứng minh đạt KPI kinh doanh.

### Biểu đồ “Premiums and claims, in perspective”

**Trả lời:** Premium và claims đi cùng nhau hay tách ra theo thời gian? Đường navy là premium, cam là claims. Chọn `Monthly` để thấy biến động tháng; chọn `Annual` để thấy tổng từng năm. Không ngoại suy phần còn lại của 2023.

**Insight mặc định:** Premium tăng qua phần lớn giai đoạn 2003–07/2023, trong khi claims ở dưới premium. Đọc cùng KPI 24,1% để hiểu quy mô chênh lệch trên **toàn kỳ**. Không suy từ hai đường rằng doanh nghiệp có lãi: chi phí khác và đơn vị tiền còn ngoài biểu đồ.

### Biểu đồ “Which companies lead premium volume?”

**Trả lời:** Những công ty nào chiếm nhiều premium nhất trong cùng bang/khoảng năm? Top 10 được xếp theo tổng premium; di chuột để xem tên nguồn đầy đủ.

**Insight mặc định:** BRADESCO VIDA khoảng **455,2 tỷ** và BRASILPREV khoảng **443,0 tỷ** source units, lần lượt xấp xỉ **14,9%** và **14,5%** tổng premium. Đây là tập trung về *quy mô*, chưa phải xếp hạng hiệu quả claims vì biểu đồ này không so claims theo công ty.

### Biểu đồ “Where is premium volume concentrated?”

**Trả lời:** Dòng sản phẩm nào tạo nhiều premium? Top 8 là một lát cắt khác của **cùng tổng premium** đang lọc; tên ngắn trên trục, mã nguồn trong hover.

**Insight mặc định:** “VGBL & related plans” khoảng **1,10 nghìn tỷ** source units, tương đương **36,0%** premium toàn kỳ; “Motor own damage” khoảng **382,3 tỷ**. Không suy ra công ty đứng đầu bán sản phẩm đứng đầu: snapshot hiện không chứa bảng giao công ty × sản phẩm.

**Câu kết cho trang:** “Premium tăng và tập trung ở một số công ty/dòng sản phẩm. Tỷ lệ claims/premiums là một chỉ báo tổng hợp cần theo dõi theo thời gian; ba biểu đồ cho biết *bao nhiêu, khi nào, và tập trung ở đâu*, chứ chưa giải thích nguyên nhân.”

Trong app có đoạn nối câu chuyện tự thay theo filter: mặc định top 10 công ty chiếm **63,2%**, top 8 dòng sản phẩm chiếm **74,3%** toàn premium đang chọn. Mẫu số là **tất cả premium của selection**, không chỉ tổng top-N. Đường premium là navy liền, claim là cam đứt; legend nằm trong chart nên vẫn đi cùng file PNG. Nhãn và đơn vị vẫn cần đọc dù đã phân biệt màu.

## Trang 2 — Motor risk & ML

**Câu hỏi lớn:** Claim quan sát phân bố thế nào trong dữ liệu motor, và model score liên hệ ra sao với `HasClaim` trên mẫu kiểm thử?

Trang này có **hai population khác nhau**. KPI `Risk observations`, `Total exposure`, `Claims / exposure` và biểu đồ tuổi/nhãn hồ sơ dùng **toàn warehouse Track B** (1.965.355 quan sát mặc định). `Mean model score`, hai biểu đồ score và ROC-AUC/AP dùng **20.000 dòng held-out** ở toàn bộ trạng thái mặc định. Bộ lọc bang áp dụng cho số liệu hiển thị theo bang; ROC-AUC/AP giữ nguyên vì là bằng chứng lịch sử của **toàn bộ held-out**, không phải metric theo bang.

**Trình tự đọc:** quy mô/exposure → tỷ lệ `HasClaim` theo tuổi → cấu trúc nhãn hồ sơ → phân bố score → tỷ lệ `HasClaim` quan sát theo score. Không cộng tổng các nhóm score với 1.965.355 quan sát warehouse.

Giao diện nay chia thành **01 / Observed portfolio** và **02 / Held-out evaluation** theo đúng trình tự này. Ba KPI đầu đi cùng warehouse; `Mean model score` nằm riêng trong phần held-out, kèm cỡ mẫu đang lọc. Chọn bang có thể làm hai cỡ mẫu thay đổi khác nhau; đó là hai population có sẵn, không phải mất dữ liệu hay join sai.

### KPI trong hai phần của trang

- `Risk observations`: số dòng quan sát rủi ro tổng hợp trong warehouse; không đồng nghĩa số khách hàng hay hợp đồng.
- `Total exposure`: tổng `ExposTotal` của nguồn, mặc định khoảng **6,26 triệu source units**. Không phải số lượng dòng.
- `Claims / exposure`: tổng **claim count / exposure**, mặc định khoảng **0,237**. Đây là tần suất count theo exposure, không phải xác suất có claim của từng người.
- `Mean model score`: trung bình score trên held-out theo bang đang chọn; là **association score**, chưa được xác nhận là xác suất underwriting tương lai.

### Biểu đồ “Observed claim share varies by age group”

**Trả lời:** Nhóm `DrivAge` nào có tỷ lệ quan sát `HasClaim=1` cao hơn trong warehouse đã lọc? Mỗi cột là `số quan sát HasClaim / số quan sát của nhóm`; `Unknown` vẫn được giữ.

**Insight mặc định:** Nhóm **36–45** khoảng **19,9%**, nhóm **18–25** khoảng **16,6%**. Đây là quan hệ mô tả ở dữ liệu quan sát. Không kết luận tuổi *gây ra* claim hoặc so sánh công bằng giữa nhóm khi chưa kiểm các yếu tố khác.

Đường chấm là tỷ lệ `HasClaim` của **toàn warehouse đang lọc**, tính `SUM(has_claim)/SUM(observations)`, không lấy trung bình tỷ lệ các nhóm tuổi. Đường này giúp đọc nhóm cao/thấp hơn bối cảnh chung; không phải mục tiêu kinh doanh hoặc ranh giới chấp nhận bảo hiểm. Cam nhận diện observed claim, xám cho nhóm tuổi Unknown; hover có cả số HasClaim và số observation.

### Biểu đồ “The observation mix behind the analysis”

**Trả lời:** Dữ liệu gồm bao nhiêu quan sát theo nhãn `Gender` của nguồn? Có Male, Female, Corporate và Unknown.

**Insight mặc định:** Male khoảng **857.074**, Female **644.600**, Corporate **375.492**, Unknown **88.189** quan sát. Biểu đồ là **số lượng**, không phải tỷ lệ claim theo nhãn. Nó giúp người xem biết thành phần mẫu trước khi diễn giải các biểu đồ rủi ro.

Các thanh count dùng xám trung tính, không phải trạng thái tốt/xấu. Hover cho cả số lượng và tỷ trọng trong warehouse đang lọc. Biểu đồ không được dùng để suy ra claim rate theo Gender, và không biến Corporate thành một giới tính cá nhân.

### Biểu đồ “Where model scores are concentrated”

**Trả lời:** Score của model tập trung ở khoảng nào trên held-out? Mỗi cột là một khoảng rộng 0,05.

**Insight mặc định:** **13.526/20.000 (67,6%)** score dưới 0,20. Phân bố nghiêng về score thấp; tự nó chưa chứng minh model chính xác hay sai. Đừng gọi đây là phân bố score của toàn bộ warehouse.

Đây là **histogram của score liên tục đã tổng hợp thành bins**, không phải xếp hạng danh mục: 20 khoảng giữ thứ tự 0→1, mỗi khoảng rộng 0,05 và các thanh liền nhau. Khoảng không có mẫu vẫn hiện count 0. Tím đậm dưới 0,20 chỉ nhấn nhóm được mô tả trong headline; **0,20 không phải threshold phân lớp**. Không khôi phục score cá nhân hay quartiles từ hình này.

### Biểu đồ “How scores relate to observed claims”

**Trả lời:** Trong từng khoảng score, tỷ lệ `HasClaim=1` thật có tăng cùng score không? Đường cam liền là tỷ lệ quan sát, đường tím đứt là score trung bình của khoảng. Trục X là **trung điểm khoảng score**, không phải score trung bình thật; score trung bình là giá trị đường tím trên trục Y, đổi sang thang % để so cùng hình.

**Insight mặc định:** Gộp các khoảng dưới 0,20 cho **8,8%** `HasClaim`; gộp từ 0,50 trở lên cho **69,9%** trên **1.091** quan sát. Điều này cho thấy score phân tách nhóm trên **tập held-out**, không bảo đảm xác suất claim ở tương lai. Các khoảng cao có ít quan sát hơn nên đường có thể dao động. ROC-AUC **0,808815** và AP **0,513523** là kết quả lịch sử tháng 09/2026 trên 20.000 dòng, không phải đo mới sau khi đổi filter.

Hover hiện biên khoảng, số observation và số HasClaim thật. Nếu một bang không có mẫu trong một bin thì hai đường có **khoảng ngắt**, không tự gán tỷ lệ 0 hoặc nối qua bin vắng. Đoạn insight dưới hai chart lấy cùng held-out để nối phân bố score với claim quan sát; không suy thành so sánh tuổi của warehouse.

**Câu kết cho trang:** “Nguồn motor có khác biệt claim quan sát theo nhóm tuổi và cấu trúc hồ sơ. Trên mẫu held-out riêng, score cao đi kèm tỷ lệ `HasClaim` quan sát cao hơn. Đây là phân tích mô tả và đánh giá cắt ngang; chưa thể dùng như xác suất bồi thường tương lai.”

## Trang 3 — Data & performance

**Câu hỏi lớn:** Tôi có thể kiểm trực tiếp những aggregate nào cấp dữ liệu cho dashboard, và việc tối ưu SQL đã đánh đổi điều gì?

**Trình tự đọc:** KPI quy mô/đối soát → bảng data explorer → benchmark index. Bảng và KPI lấy từ snapshot SQL **11/11/2026**; benchmark index đo **24/09/2026**. Hai mốc thời gian phải được nói tách biệt.

### KPI ở đầu trang

- `Warehouse observations`: tổng số dòng fact của **hai track độc lập**, khoảng **10,30 triệu**. Đây chỉ là tổng quy mô; không có phép join giữa chúng.
- `Row-count reconciliation`: **2/2** track có số dòng staging bằng fact trong snapshot. Khớp số dòng là một kiểm tra, **không thay thế** toàn bộ SQL quality gate.
- `Q1 logical reads saved`: **98,94%** ít page reads hơn cho workload công ty/tháng trong benchmark lịch sử.
- `Additional index storage`: khoảng **924,51 MB** cho hai covering indexes, kèm chi phí ghi/bảo trì index.

### Bảng “Inspect the data behind the charts”

**Trả lời:** Các hàng dữ liệu nào tạo thành các phép tổng hợp hiển thị? Chọn `SUSEP market` để duyệt **6.669** hàng month × state aggregate với premium, claims, ratio, observations. Chọn `Motor risk` để duyệt **644** hàng state × Gender × age aggregate với exposure, premium, claims, claim count và `HasClaim` share. Có lọc bang và nút trang trước/sau, mỗi trang 15 hàng. Đây là **dữ liệu aggregate thật trong `data/dashboard.json`**, không phải 8,3 triệu + 1,96 triệu bản ghi raw; dashboard cố ý không công khai raw hay danh tính khách hàng.

**Cách dùng để kiểm:** chọn một bang, nhìn các hàng tháng/nhóm; sau đó quay lại trang Market hoặc Motor và đặt cùng bang để đối chiếu xu hướng hoặc nhóm quan sát. Bảng Market theo tháng/bang không có chiều công ty/sản phẩm, nên không thể dùng nó để kiểm từng cột ranking. Bảng Motor theo state/Gender/age không có score band; score được tổng hợp riêng trong snapshot.

### Biểu đồ “Fewer reads, with an explicit storage cost”

**Trả lời:** Hai covering indexes làm thay đổi số logical reads của hai workload SUSEP đã đo như thế nào? Trục ngang dùng **thang tuyến tính bắt đầu từ 0**, thanh xám là trước index, thanh teal là sau index. Q1 là company/month; Q2 là state/product/month, có tên đầy đủ ở phần số liệu bên cạnh và hover.

**Insight lịch sử:** workload công ty/tháng từ **317.528 → 3.364** logical reads (**−98,94%**); state/sản phẩm/tháng từ **317.528 → 3.734** (**−98,82%**). Đổi lại khoảng **924,51 MB** index và thêm chi phí ghi. Đó không phải lời hứa mọi truy vấn nhanh hơn 99%, cũng không đo tốc độ end-to-end của dashboard (Dash đọc JSON snapshot, không gọi SQL khi đổi filter).

Thanh sau index rất ngắn là **đúng độ lớn**, không phải lỗi hiển thị. Nhãn exact giúp đọc số nhỏ. Không kéo dài thanh bằng log axis, vì người xem bar thường so chiều dài từ gốc; lựa chọn này bám nguyên tắc bar từ 0 ở C2 p35. Không dùng % giảm logical reads để nói elapsed time cũng giảm cùng mức.

**Câu kết cho trang:** “Tôi cho xem các aggregate thật thay vì chỉ số tổng, giữ mốc xuất dữ liệu để truy vết, và trình bày cả lợi ích đọc SQL lẫn chi phí lưu/ghi của index. Đối soát số dòng cho biết tính đầy đủ ở một mức; quality gates SQL mới kiểm sâu hơn.”

## Cách kể ngắn khi phỏng vấn

“Em xây hai track bảo hiểm độc lập trong SQL Server, kiểm chất lượng trước khi xuất aggregate cho Dash. Với SUSEP, em xem tổng premium/claims theo thời gian rồi kiểm xem quy mô tập trung ở công ty và sản phẩm nào. Với dữ liệu motor, em tách số liệu toàn warehouse khỏi mẫu held-out để không diễn giải sai model score. Cuối cùng em cho xem các hàng aggregate cấp dashboard và benchmark SQL có cả lợi ích lẫn chi phí index. Snapshot có ngày xuất, không realtime; hai nguồn không join theo bản ghi.”
