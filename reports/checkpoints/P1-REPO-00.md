# P1-REPO-00 — Cổng hiểu repository

Ngày: 2026-09-22

Kết quả: PASS

Phạm vi: Onboarding repository chỉ-đọc. Artifact duy nhất được tạo trong giai đoạn này là báo cáo checkpoint này. Không có dữ liệu thô, mã nguồn, cấu hình, SQL, notebook hoặc log lịch sử nào bị sửa đổi.

## 1. Mục đích dự án

Dự án đang hướng tới việc trở thành một Data Warehouse bảo hiểm xe cơ giới phục vụ phân tích bồi thường và rủi ro. Nguồn dữ liệu nghiệp vụ chuẩn là bộ dữ liệu bảo hiểm xe Brazil `brvehins1`, gồm năm phân vùng CSV. Luồng dự kiến là CSV raw -> staging SQL Server -> kho dữ liệu dạng dimensional -> cổng kiểm tra chất lượng dữ liệu -> xử lý tăng dần, ML, Airflow, tối ưu hiệu năng và Power BI ở các giai đoạn sau.

Hiện tại dự án chưa phải là một nền tảng end-to-end vận hành được. Các thành phần SQL, ML và Airflow hiện có phần lớn là scaffold đã comment hoặc stub của thiết kế cũ dựa trên dữ liệu thị trường SUSEP và Porto Seguro Safe Driver. Chúng không phải bằng chứng về yêu cầu nghiệp vụ hiện tại hay năng lực runtime.

## 2. Bản đồ repository

| Khu vực | Trách nhiệm | Trạng thái thực tế |
|---|---|---|
| `data/raw/` | Lưu trữ CSV nguồn bất biến | Đang có `brvehins1` chuẩn và một CSV SUSEP cũ trên máy; bị Git bỏ qua. |
| `docs/architecture/` | Kiến trúc mục tiêu, từ điển dữ liệu, bản đồ repository | Nội dung hiện tại và cũ bị trộn lẫn, có phần trùng lặp. |
| `docs/guides/` | Hướng dẫn chạy và bảng thuật ngữ | Nội dung hiện tại và cũ bị trộn lẫn, có phần trùng lặp. |
| `docs/reports/` | Báo cáo phân tích và tối ưu trong tương lai | Scaffold/template. |
| `docs/specs/` | Roadmap và đặc tả triển khai | `roadmap.md` là trình tự thực thi hiện tại rõ ràng nhất; `implementation-guide.md` trộn nội dung cũ và mới. |
| `migrations/` | DDL SQL Server có phiên bản | Một scaffold kiến trúc cũ được comment hoàn toàn; chưa có cấu hình migration runner. |
| `sql/` | SQL staging, xử lý tăng dần, ETL, DQ và nạp dự đoán | Tám scaffold kiến trúc cũ được comment hoàn toàn. |
| `ml/` | Huấn luyện model và batch scoring trong tương lai | Python hợp lệ về cú pháp nhưng là stub hướng Porto Seguro/customer. |
| `dags/` | Điều phối Airflow trong tương lai | DAG Airflow hợp lệ về cú pháp nhưng là stub cho thiết kế customer/policy cũ. |
| `scripts/` | Validator tĩnh của repository | Là baseline hữu ích nhưng vẫn giữ checklist runtime cũ và các heading trùng lặp. |
| `notebooks/` | EDA | Notebook JSON hợp lệ, chỉ có các đề mục EDA đã comment; chưa có phân tích được thực thi. |
| `powerbi/` | Artifact Power BI trong tương lai | Chỉ có placeholder; chưa có `.pbix`. |
| `log/` | Bằng chứng tiến độ và review lịch sử | Là bằng chứng lịch sử, không phải bằng chứng runtime hiện tại. |
| `.cursor/rules/` | Quy tắc workflow của dự án | Đang có và nhìn chung còn áp dụng; các điểm không nhất quán cụ thể được liệt kê bên dưới. |
| `docker-compose.yml` | Ý định chạy SQL Server và Airflow cục bộ | Chỉ là cấu hình tĩnh; chưa có bằng chứng runtime. |

## 3. Dữ liệu chuẩn hiện tại

Các file vật lý đã được kiểm tra mà không sửa đổi hoặc phân tích toàn bộ dữ liệu.

| Nguồn | Bằng chứng vật lý | Phân loại |
|---|---|---|
| `data/raw/brvehins1/brvehins1a.csv` | 60,499,054 bytes | CHUẨN |
| `data/raw/brvehins1/brvehins1b.csv` | 60,497,433 bytes | CHUẨN |
| `data/raw/brvehins1/brvehins1c.csv` | 60,481,086 bytes | CHUẨN |
| `data/raw/brvehins1/brvehins1d.csv` | 60,491,192 bytes | CHUẨN |
| `data/raw/brvehins1/brvehins1e.csv` | 60,501,172 bytes | CHUẨN |
| `data/raw/susep.gov.br/insurance_dataset.csv` | 751,126,569 bytes | CŨ / KHÔNG CHUẨN |

Cả năm file chuẩn đều có cùng header 23 cột có thể đọc được:

`Gender, DrivAge, VehYear, VehModel, VehGroup, Area, State, StateAb, ExposTotal, ExposFireRob, PremTotal, PremFireRob, SumInsAvg, ClaimNbRob, ClaimNbPartColl, ClaimNbTotColl, ClaimNbFire, ClaimNbOther, ClaimAmountRob, ClaimAmountPartColl, ClaimAmountTotColl, ClaimAmountFire, ClaimAmountOther`.

File SUSEP cũ có header tổng hợp thị trường khác: `company_code, company_name, year_month, product, state, premiums, claims, claim_premium_ratio`. File này không được join, stage hoặc sử dụng theo bất kỳ cách nào trong pipeline chuẩn. `.gitignore` bỏ qua cả hai nguồn raw qua `data/raw/*`, đồng thời giữ lại `data/raw/.gitkeep`.

Số dòng chính xác của từng phân vùng và tổng hợp chưa được đo độc lập trong giai đoạn này. Tài liệu trước đây ghi nhận 393,071 dòng mỗi phân vùng và 1,965,355 dòng tổng cộng, nhưng P1-DATA-01 phải tạo ra bằng chứng runtime.

## 4. Kiến trúc theo tài liệu hiện tại

Thiết kế mục tiêu mạch lạc nhất được tìm thấy trong `docs/specs/roadmap.md` và `docs/architecture/architecture-explained.md`:

1. Profile và đóng băng data contract của nguồn `brvehins1`.
2. Tạo runtime SQL Server thực và metadata nền tảng.
3. Stage năm file bất biến dưới dạng các batch ingest có tính idempotent.
4. Thiết kế mô hình dimensional dựa trên grain thực tế của nguồn, có khả năng gồm các dimension driver, vehicle, geography và một fact về hiệu suất/rủi ro policy.
5. Triển khai các cổng DQ cho nguồn/staging và tính toàn vẹn kho dữ liệu.
6. Hoãn CDC, ML, điều phối Airflow, tối ưu hiệu năng và Power BI cho đến khi nền tảng được chứng minh.

Thiết kế này cấm tự tạo `CustomerId`, `PolicyNumber` hoặc ngữ nghĩa SCD2 theo lịch sử khách hàng khi nguồn không có các trường đó.

## 5. Kiến trúc được mã scaffold hiện tại thể hiện

Các scaffold có vẻ như mã thực thi đang thể hiện một thiết kế đã lỗi thời:

| Nhóm artifact | Giả định được mã hóa | Phân loại |
|---|---|---|
| `migrations/V1__create_dwh_schema.sql` | `Dim_Customer` SCD2, `Dim_Policy`, `Dim_Date`, `Dim_Region`, `Fact_Premium`, `Fact_Claims` và `Fact_Customer_Risk_Prediction` | SCAFFOLD CŨ |
| `sql/01_load_staging.sql` | Các bảng staging riêng cho SUSEP và Porto Seguro cùng tên file cũ | SCAFFOLD CŨ |
| `sql/02_enable_cdc.sql` | CDC trên `stg_susep_raw` và `stg_portoseguro_raw` | SCAFFOLD CŨ |
| `sql/03_sp_dim_customer_scd2.sql` đến `sql/06_sp_fact_claims.sql` | SCD2 khách hàng, dimension policy/date/region, các fact premium/claims riêng biệt | SCAFFOLD CŨ |
| `sql/07_data_quality_checks.sql` | Quy tắc DQ cho fact cũ và customer key | SCAFFOLD CŨ |
| `sql/08_sp_load_risk_predictions.sql` | Fact dự đoán theo customer key | SCAFFOLD CŨ |
| `ml/train_risk_model.py` và `ml/predict_risk_batch.py` | Trường `ps_*` của Porto Seguro, `train.csv`, scoring theo customer và artifact stub | PASS TĨNH / SCAFFOLD CŨ |
| `dags/insurance_dwh_pipeline.py` | Dimension customer/policy cũ, các fact premium/claims riêng biệt, operator stub, không có cấu hình SQL hook/provider | PASS TĨNH / SCAFFOLD CŨ |

Mọi câu lệnh SQL có khả năng tạo hoặc nạp business object đều nằm trong block comment. Chưa có pipeline DWH nào có bằng chứng runtime.

## 6. Mâu thuẫn giữa tài liệu và mã nguồn

| Bằng chứng | Mâu thuẫn |
|---|---|
| `README.md` | Bắt đầu bằng mục đích `brvehins1` chuẩn nhưng vẫn có bảng SUSEP/Porto cũ, các bước trùng lặp, bảng trạng thái trùng lặp và hướng dẫn cũ yêu cầu tải/sử dụng các nguồn đó. |
| `docs/specs/implementation-guide.md` | Lặp lại mô tả nguồn cũ và mới, thiết kế DWH, danh sách DoD và các mục checklist runtime. Vẫn giữ các giả định Customer/Policy/SCD2 cũ và tiêu chí ROC-AUC. |
| `docs/guides/how-to-run.md` | Vừa hướng dẫn tải Porto Seguro vừa nói `brvehins1` đã có; đồng thời đưa tên container Airflow cũ và các thao tác SQL Customer/Policy lỗi thời. |
| `docs/architecture/data-dictionary.md` | Có ma trận 23 trường hiện tại nhưng đứng sau các phần SUSEP/Porto cũ và vẫn mô tả fact dự đoán theo customer. |
| `docs/architecture/repository-structure.md`, `docs/guides/glossary.md` và `docs/reports/insights.md` | Có các phần cũ/mới trùng lặp và vẫn giữ thuật ngữ customer/policy/fact cũ. |
| `log/progress-log.md` và Git commit `0a546b8` | Cả hai đều ghi P1-WF-04 đã hoàn thành, trong khi `docs/specs/roadmap.md` nói đây là bước tiếp theo và tài liệu/scaffold hiện tại vẫn có nhiều tham chiếu cũ. Vì vậy tuyên bố hoàn thành chỉ là bằng chứng tiến độ lịch sử, chưa đủ làm bằng chứng Gate-A hiện tại. |
| `scripts/validate_repo.py` | Validator kiểm tra đúng năm tên file chuẩn và header tương ứng, nhưng checklist runtime bị bỏ qua vẫn giữ thuật ngữ SUSEP, Porto, customer-SCD2, 8–10M dòng và ML cũ. |
| `docker-compose.yml` cùng `ml/predict_risk_batch.py` | Mount raw ở chế độ chỉ-đọc, trong khi ML stub đề xuất ghi `data/raw/stg_risk_predictions.csv`; điều này xung đột với tính bất biến của raw và với mount hiện tại. |

Binary `docs/specs/insurance-dwh-overview.pdf` là artifact nguồn cũ có kích thước 55,401 byte. Không có công cụ trích xuất text PDF cục bộ. Ngày của file và báo cáo review xếp nó vào giai đoạn scaffold ban đầu; file được phân loại LỊCH SỬ / CHƯA XÁC ĐỊNH, không phải nguồn có thẩm quyền về kiến trúc hiện tại.

## 7. Trạng thái các subsystem hiện tại

| Subsystem | Trạng thái | Bằng chứng | Vấn đề chính | Bước tiếp theo bắt buộc |
|---|---|---|---|---|
| Governance | PASS TĨNH | Có rules và baseline static validator | Tài liệu và snapshot log hiện tại mâu thuẫn | Hợp nhất tài liệu chuẩn trong P1-WF-04. |
| Dữ liệu raw | PASS TĨNH | Năm CSV chuẩn không rỗng, có cùng header và tồn tại vật lý | Chưa có bằng chứng runtime được ghi nhận về số dòng và profiling | Chạy EDA tiết kiệm bộ nhớ trong P1-DATA-01. |
| Validation | PASS TĨNH / CẦN REFACTOR | Validator kiểm tra file, header, YAML, cú pháp Python, JSON notebook, cân bằng comment SQL | Checklist runtime vẫn giữ giả định cũ; validator chưa kiểm tra business contract | Cập nhật ngôn ngữ/phạm vi trong P1-WF-04; chỉ mở rộng sau data contract. |
| EDA | SCAFFOLD | Notebook JSON hợp lệ | Chưa có cell được thực thi hoặc profile nguồn | Triển khai P1-DATA-01. |
| Data contract | SCAFFOLD | Đã có bảng ứng viên 23 cột | Nội dung cũ bị trộn; chưa có chính sách grain/null/trùng lặp dựa trên bằng chứng | Đóng băng P1-DATA-02. |
| Docker | PASS TĨNH | Compose khai báo SQL Server và Airflow với mount raw chỉ-đọc | Chưa xác minh runtime; compose có placeholder | Xác thực/xây dựng lại nền SQL trong P1-INFRA. |
| SQL Server | CHỜ RUNTIME | Service được cấu hình ở port 1433 | Chưa có bằng chứng container hoặc kết nối | Khởi động và kết nối trong P1-INFRA. |
| Migration | SCAFFOLD CŨ | Một file DDL cũ được comment hoàn toàn | Chưa có migration runner hoặc model chuẩn | Thay thế sau data contract trong phần INFRA/DWH. |
| Staging | SCAFFOLD CŨ | Script BULK INSERT cũ được comment hoàn toàn | Không khớp 23 trường nguồn | Xây dựng P1-INGEST-01. |
| DWH | SCAFFOLD CŨ | DDL dimensional cũ và ETL stub | Tự tạo entity customer/policy và tách fact không có bằng chứng | Thiết kế P1-DWH-01 sau profiling. |
| DQ | SCAFFOLD CŨ | Draft log/procedure DQ được comment | Kiểm tra key/bảng cũ, không kiểm tra data contract nguồn | Triển khai P1-DQ-01 đến P1-DQ-03. |
| Incremental/CDC | SCAFFOLD CŨ | Draft CDC/watermark được comment | Các partition nguồn tĩnh không chứng minh lịch sử thay đổi nguồn | Trước hết triển khai idempotency theo partition-batch; hoãn minh chứng CDC. |
| ML | PASS TĨNH / SCAFFOLD CŨ | Python parse được | Feature theo Porto/customer và chưa có huấn luyện/scoring thực | Hoãn đến khi DWH và ML contract sẵn sàng. |
| Airflow | PASS TĨNH / SCAFFOLD CŨ | Mã DAG parse được | Operator stub, task graph cũ, chưa có bằng chứng provider/runtime | Hoãn đến khi ingestion/DWH/DQ là thành phần thực. |
| Performance | SCAFFOLD | Có template báo cáo | Chưa có database, query, execution plan hoặc phép đo đang chạy | Hoãn đến khi warehouse được nạp. |
| Power BI | SCAFFOLD | Chỉ có `powerbi/.gitkeep` | Chưa có semantic model hoặc `.pbix` | Hoãn đến khi warehouse được nạp. |

## 8. Artifact cũ cần bảo toàn

- `migrations/V1__create_dwh_schema.sql`
- `sql/01_load_staging.sql` đến `sql/08_sp_load_risk_predictions.sql`
- `ml/train_risk_model.py`
- `ml/predict_risk_batch.py`
- `dags/insurance_dwh_pipeline.py`
- Các phần cũ bị trộn trong `README.md`, `docs/specs/implementation-guide.md`, `docs/guides/how-to-run.md`, `docs/architecture/data-dictionary.md`, `docs/architecture/repository-structure.md`, `docs/guides/glossary.md` và `docs/reports/insights.md`
- `docs/specs/insurance-dwh-overview.pdf` (lịch sử / chưa xác định)

Các artifact này phải được refactor hoặc đánh dấu rõ ràng; không được xóa chỉ vì chúng đã cũ.

## 9. Các quy tắc phải tuân thủ

| Rule | Trạng thái so với repository | Hướng dẫn áp dụng |
|---|---|---|
| `01-quy-trinh-thuc-hien.mdc` | HIỆN HÀNH | Đọc tài liệu nguồn sự thật, giới hạn một task, xác thực trung thực và bảo toàn cấu trúc dự án. Các ví dụ task-ID không có prefix là điểm lệch quy ước đặt tên, không phải blocker. |
| `02-quan-ly-file-va-log.mdc` | HIỆN HÀNH | Dùng path chuẩn, không commit raw data/secret, append thay vì viết lại lịch sử tiến độ và tránh các file trùng lặp song song. |
| `03-kiem-tra-git-va-review.mdc` | HIỆN HÀNH, có chi tiết cũ | Chạy kiểm tra tĩnh phù hợp và kiểm tra Git trước commit. Các tham chiếu đến số lượng validator cố định đã cũ vì script báo cáo kết quả động. |
| `04-python.mdc` | HIỆN HÀNH | Dùng type hint/docstring, tránh path cá nhân hard-code và leakage, đồng thời compile Python trước khi bàn giao. Các stub hiện tại chưa đáp ứng tinh thần của rule. |
| `05-setup-handoff.mdc` | HIỆN HÀNH, có thiếu sót nhỏ về từ vựng trạng thái | Giữ `docs/guides/how-to-run.md` làm tài liệu chuẩn khi hành vi chạy thay đổi và phân biệt scaffold/static/runtime. Rule chưa nêu `DONE` và `FAILED`, dù hai trạng thái này được định nghĩa ở nơi khác. |

Không có rule hiện tại nào yêu cầu giữ lại kiến trúc nghiệp vụ SUSEP + Porto đã bị thay thế.

## 10. Thay đổi có sẵn của người dùng

Bằng chứng Git pre-flight được ghi nhận trước giai đoạn này:

```text
On branch main
nothing to commit, working tree clean
```

Không có thay đổi nào của người dùng, dù tracked hay untracked, tồn tại từ trước. Git phát cảnh báo ngoài dự án rằng không thể đọc `C:\Users\Nghia/.config/git/ignore`; cảnh báo này không ảnh hưởng đến kết quả working tree sạch hoặc các kiểm tra `.gitignore` của repository.

## 11. Blocker hiện tại

1. Chưa có EDA nguồn tạo ra bằng chứng về số dòng, dtype, null/trùng lặp, grain hoặc ràng buộc nghiệp vụ.
2. Tài liệu hiện tại còn trùng lặp cũ/mới chưa được xử lý, nên chưa thể dùng an toàn như một nguồn sự thật duy nhất.
3. Chưa có bằng chứng runtime cho SQL Server, migration tool, staging load, DWH load, DQ execution hoặc Airflow run.
4. Chưa có dependency manifest hoặc cấu hình migration runner. Việc setup runtime phải được xác thực, không được giả định.
5. Thiết kế customer/policy cũ không tương thích với header chuẩn đã quan sát và không được tiếp tục mang sang.

Các blocker này không ngăn cản task an toàn tiếp theo là P1-WF-04.

## 12. Trình tự thực thi được đề xuất

Trình tự dự kiến vẫn hợp lệ, với cách diễn giải sau:

```text
P1-WF-04
-> P1-DATA-01
-> P1-DATA-02
-> P1-INFRA-01 / P1-INFRA-02
-> P1-INGEST-01 / 02 / 03
-> P1-DWH-01 / 02 / 03
-> P1-DQ-01 / 02 / 03
```

P1-WF-04 phải được thực hiện như một task hiệu chỉnh/xác thực lại, dù log lịch sử và commit đã ghi nhận hoàn thành: bằng chứng Gate-A chưa được thỏa mãn bởi các tài liệu hỗn hợp và ngôn ngữ cũ trong validator hiện tại.

## Câu trả lời cho cổng hiểu repository

1. Domain hiện tại: Motor Insurance DWH, phân tích bồi thường/rủi ro và ML trong tương lai.
2. Dataset chuẩn: năm file `data/raw/brvehins1/brvehins1[a-e].csv`.
3. Các file raw chuẩn có trên máy: cả năm file được liệt kê ở mục 3.
4. Nguồn cũ: `data/raw/susep.gov.br/insurance_dataset.csv`.
5. Kiến trúc trước đây bị thay thế vì kết hợp các nguồn riêng biệt và tự giả định customer/policy/SCD2, trong khi các trường này không được bộ trường chuẩn `brvehins1` hỗ trợ.
6. Tài liệu hiện tại: chủ yếu là `docs/specs/roadmap.md` và các phần chuẩn trong tài liệu kiến trúc.
7. Tài liệu cũ: các phần SUSEP/Porto bị trùng lặp được xác định ở mục 6.
8. SQL cũ: toàn bộ artifact migration hiện tại và các artifact `sql/*.sql`.
9. Pipeline DWH đã chứng minh runtime: chưa có.
10. Pipeline ML đã huấn luyện và validate: chưa có.
11. Trạng thái Airflow: chỉ là scaffold cũ hợp lệ về cú pháp, chưa vận hành.
12. Validator: kiểm tra file/header tĩnh, parse compose, cú pháp Python, JSON notebook, cân bằng comment SQL, tên trùng lặp và checklist runtime bị bỏ qua.
13. Rule còn áp dụng: cả năm `.cursor/rules/*.mdc`, theo inventory ở mục 9.
14. Xung đột rule: không có rule nào bắt buộc kiến trúc cũ; các lệch nhỏ về tên, trạng thái và số lượng đã được ghi nhận.
15. File đã bị sửa trước đó: không có.
16. Task an toàn tiếp theo chính xác: P1-WF-04, chuẩn hóa tài liệu hiện tại và ngôn ngữ validator theo `brvehins1` mà không thay đổi dữ liệu raw.
