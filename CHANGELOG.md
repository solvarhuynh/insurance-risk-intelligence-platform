# Nhật ký dự án và bằng chứng quan trọng

File này là nơi ghi lịch sử phát triển/kiểm tra duy nhất. [GUIDE](GUIDE.md) giải thích kiến trúc và cách học; [AGENTS](AGENTS.md) bàn giao trạng thái hiện hành. Log tác vụ Airflow và audit ingestion/DQ vẫn nằm trong volume/database vì có vai trò vận hành riêng.

## 11/11/2026 — Tối giản thêm cấu trúc và tên file

- Rút gọn tên Python dài trong `pipeline/`: `load_market`, `load_risk`, `profile_market`, `profile_risk`, `profile_precision`, `reconcile_market`, `model`, `train_risk`, `score_risk`, `export_dash`, `cdc_demo`, `dag`, `validate`. Các import, Airflow path, CLI và tài liệu đã cập nhật theo tên mới.
- Xóa `dashboard/__init__.py`, `pipeline/__init__.py` vì Python hiện đại chạy được namespace package và hai file không có chức năng. Xóa các `.gitkeep` placeholder trong `data/models` và `data/generated`; thư mục output được tạo lúc command cần dùng. Model local thật trong `data/models` vẫn giữ nguyên.
- Giữ 14 migration riêng vì mỗi file là một version schema đã áp dụng; không gộp chúng thành một file làm mất lịch sử nâng cấp. Giữ `infra/requirements-*` riêng vì Airflow và Dash có dependency/runtime khác nhau.
- `.env` hiện chỉ có password là hợp lệ: host/database/user dùng default trong `config.py`, còn `AIRFLOW_SECRET_KEY` chỉ cần khi muốn tự đặt secret cho Airflow. Hướng dẫn thêm biến thủ công nằm trong GUIDE; không commit `.env`.
- Cây Git hiện chỉ giữ các nhóm cần thiết: dashboard, pipeline, database, infra, data, tests và tài liệu root. Tên dài của các thư mục/file cũ đã bị loại hoặc thay thế; file mẫu/tạm/log cũ nằm ngoài repo trong archive.

## 11/11/2026 — Chuyển sang Plotly Dash và tinh gọn repository

### Phạm vi thay đổi

- Thay handoff Power BI bằng ứng dụng Dash có ba trang, filter độc lập cho Market/Risk, biểu đồ, KPI, CSV và health endpoint. Giao diện tiếng Việt, sidebar navy, nền sáng, biểu đồ teal/cam, có bố cục desktop/mobile.
- Xuất aggregate SQL thật qua `pipeline/export_dash.py`; giữ thời điểm xuất, đối soát tổng số quan sát và thay file nguyên tử. Trang không dùng credential SQL và không truy vấn full fact ở mỗi callback.
- Gom Python vào `pipeline/`; SQL versioned vào `database/migrations/`; Dockerfile vào `infra/`; model local vào `data/models/`. Giữ đủ V1–V14 và binary đã train.
- Thêm CLI `pipeline/manage.py` để migrate/load/quality/status/score/export, không cần rải entrypoint SQL. Sửa Airflow paths, dùng config chung, đổi run ID sang UUID5, thêm persistent metadata/log volumes.
- Gom toàn bộ tài liệu học/vận hành/phỏng vấn vào `GUIDE.md`; nhật ký quan trọng vào file này; handoff AI vào `AGENTS.md`. README dùng bố cục/banner/badges/ảnh ứng dụng, tham khảo hình thức `D:\aws\README.md`, không sao chép scope đồ án hoặc AWS.
- Loại code Customer SCD2/policy/premium/claims scaffold cũ không phù hợp nguồn. Các SQL entrypoint đang dùng được thay bằng CLI, logic procedure giữ trong migration. Loại notebook/handoff Power BI và thư mục docs/reports/log phân tán sau khi lưu trữ.

### Bằng chứng hiện tại

- SQL Server còn nguyên dữ liệu: `stg.SusepInsuranceMarket = dwh.FactSusepInsuranceMarket = 8.338.214`; `stg.BrVehIns1 = dwh.FactRiskObservation = 1.965.355`; prediction =20.000.
- `manage.py migrate` nhận đủ14 version đã áp dụng và SKIPPED toàn bộ; không chạy lại DDL trên volume hiện hữu.
- `manage.py quality`: `dq.sp_RunSusepQualityGate` và `dq.sp_RunQualityGate` đều PASS trong phiên11/11/2026. Code nhận lỗi SQL qua tất cả result sets.
- `manage.py export` xuất snapshot từ database thật; nguồn/thời điểm được hiển thị trên UI. JSON có Market monthly/company/product aggregates và Risk segments/score buckets, không có row identities.
- Năm test kiểm aggregate/filter, population risk, denominator và numeric migration order đã PASS. Kiểm trình duyệt/container và kiểm cuối đợt được ghi bổ sung sau khi hoàn tất.

### Nghiệm thu sau khi đổi toàn bộ đường dẫn

- Browser Playwright + Microsoft Edge: ba trang, filter bang/năm, nội dung CSV, health endpoint và độ rộng 390/768/1440 px PASS; không page error hoặc HTTP 500. Đã kiểm cả local Python và container Gunicorn, ảnh README chụp app thật.
- Hai Docker image Dash/Airflow build PASS. Dashboard container health `healthy`; native ODBC 18 và sklearn 1.7.2 có trong image Airflow; DagBag đọc đúng 12 task, không import error.
- Airflow `dags test` chạy thật toàn DAG mới: run `manual__2026-11-11T00:00:00+00:00`, **12/12 task SUCCESS**. Thực thi thực tế khoảng 01:19:54→01:25:06 UTC (khoảng 5 phút 12 giây); đây là test CLI, không gọi là lịch production đã vận hành. A ingest SKIPPED đúng fingerprint, DWH rerun an toàn, full raw-to-fact reconciliation và DQ PASS; B foundation/DQ/artifact scoring/prediction reconciliation PASS.
- Model không train lại: binary 180.770 bytes, metadata 5.773 bytes giữ từ trước; SHA-256 binary `9cd7e2f374caeba5a27afab487a74f5e42d5c659b3feaa1b19f8077d77d8ddaf`. Scoring sử dụng artifact đã có, không ghi đè model.
- Snapshot được export lại sau DAG lúc **2026-11-11T01:26:23+00:00**, tổng số dòng A/B vẫn khớp. Metric ML/performance vẫn là bằng chứng lịch sử, không tái huấn luyện/tái benchmark.
- Static validation có raw headers PASS; 5 unit tests PASS; `pip check`, Compose config và `git diff --check` PASS. Git có cảnh báo LF/CRLF thông thường, không có lỗi whitespace.
- Giữ nguyên nội dung 14 SQL migration so với commit trước (so sánh sau chuẩn hóa line endings). Tài liệu markdown hoạt động từ hơn 70 file phân tán được gom thành 4 file root; source còn 6 thư mục chính.
- Airflow metadata/log đã chuyển sang named volumes. Lỗi quyền tạo SQLite ở volume mới được sửa bằng ownership của `/opt/airflow/state` trong Dockerfile; không đụng volume SQL. Lịch sử trước refactor nằm trong archive; metadata Airflow mới giữ run nghiệm thu hiện tại.
- Sau khi recreate container từ image đã sửa, metadata vẫn giữ đủ 12/12 task SUCCESS; DagBag không import error, prediction validator đọc metadata/model hiện tại và xác nhận 20.000 dòng. Browser và 5 unit tests tiếp tục PASS với snapshot xuất sau DAG. Log kiểm tra tạm được chuyển vào thư mục archive ngoài repo; CHANGELOG và evidence JSON giữ kết quả cần đọc lại.

Chưa nghiệm thu fresh database rebuild/backup restore hoặc triển khai có auth/RBAC; controlled failure hai nhánh vẫn dựa trên run lịch sử 24/09, không tuyên bố chạy lại toàn failure scenario trong phiên này. Không có commit/push trong đợt refactor.

### Bản đồ đường dẫn cũ → hiện tại

- `scripts/*.py`, `ml/*.py`, `dags/insurance_dwh_pipeline.py` → `pipeline/`.
- `migrations/` → `database/migrations/`; `sql/` entrypoints → `pipeline/manage.py`; workload tuning → `database/performance.sql`.
- `airflow/Dockerfile`, `airflow/requirements.txt` → `infra/Dockerfile.airflow`, `infra/requirements-airflow.txt`.
- `ml/artifacts/*` → `data/models/*` (local, ignored); `reports/data` bằng chứng JSON quan trọng → `data/evidence.json`; output chạy mới → `data/generated/`.
- `docs/**`, `FINAL_PROJECT_GUIDE.md`, `REPO_LEARNING_GUIDE.md` → `GUIDE.md`; checkpoints/progress/final reports → nhật ký này + evidence JSON; Power BI → `dashboard/`.
- `.cursor/rules/` có nhiều hướng dẫn trỏ đường dẫn cũ → `AGENTS.md` duy nhất ở root.

### Bảo toàn và khôi phục

Tài liệu gốc, reports, notebooks, Power BI handoff, hai guide cũ, agent history và progress log đã được zip trước khi dọn tại `D:\insurance-platform-archive-20261111\documents-before-restructure.zip`. Các thư mục/file cũ được đưa khỏi workspace vào `D:\insurance-platform-archive-20261111\removed-from-repo` để có thể phục hồi, kể cả log runtime cũ và môi trường thử tạm. Đây là lưu trữ ngoài repo để tra lại chi tiết, không phải tài liệu hoạt động thứ hai. Code tracked cũ có thể tra bằng Git ở commit trước refactor `a36ef1b`. Không reset/clean hay xóa volume SQL; raw không sửa/xóa/di chuyển. Model binary và metadata giữ local ở đường dẫn mới.

Các file không push theo chủ đích: `.env` (secret), `data/raw/**` (CSV lớn/bất biến), `data/models/**` (artifact runtime), `data/generated/**` (output tái tạo), `.venv/**`, `__pycache__`, `.tmp-*`, `*.log`. Rule nằm trong `.gitignore`; các `.gitkeep` giữ nơi đặt dữ liệu sau clone. `data/dashboard.json` và `data/evidence.json` nhỏ, có ý nghĩa review, được giữ tracked. Đợt này chưa commit/push.

## 24/09/2026 — SUSEP, tối ưu hiệu năng và orchestration hoàn chỉnh

Đây là bằng chứng lịch sử được gom từ checkpoint/final report cũ; không phải phép đo lại ngày11/11.

- SUSEP profiling xác nhận CSV751.126.569 bytes,8.338.214 dòng,8 cột, giai đoạn2003-01→2023-07; không duplicate grain company/month/product/state. Nguồn state có40 lexical values, DWH normalize về27 mã,103 dòng case variant.
- Batch SUSEP `0EDEB285-DB67-4159-A6D5-FE85F00F085A`: accepted8.338.214, rejected0, fact8.338.214; cùng fingerprint rerun SKIPPED.
- Tổng premium nguồn/staging/fact: `3050108693057.190700567726667268`; claims: `735517715559.682615627330218331`. Nguồn text giữ audit; numeric representation DECIMAL(38,18) có rounding policy công khai.
- DQ A pass14 hard rules. Warning:116.980 phí âm,301.382 claims âm,5.167.094 ratio NA,238.088 ratio âm; không loại dữ liệu để “làm sạch” giả.
- Q1 company6572/month>=2018:317.528→3.364 logical reads; CPU1.320→127ms; elapsed176→129ms. Index CompanyMonth khoảng454,04MB.
- Q2 SP/0588-DPVAT/month>=2018:317.528→3.734 reads; CPU1.425→88ms; elapsed177→101ms. Index StateProductMonth khoảng470,47MB.
- Trial index SourceRecordHash không cải thiện workload, thêm~639,23MB, đã drop. Giữ hai covering indexes bằng migration V14; chấp nhận~924,51MB và chi phí ghi.
- Airflow happy path run `44294f58-1808-4cd8-8a22-2c90687bf321`:12/12 task success, khoảng5phút33giây.
- Controlled run `0d2f017a-1f52-46b2-9671-2f1e3d95f488`: DQ A failed thật sau retry, consumer A upstream_failed, consumer B success. Không sửa canonical data để tạo lỗi.
- Một controlled run trước từng báo success giả do Python chưa đọc resultset chứa terminal THROW. Đã sửa bằng drain `cursor.nextset()`; giữ bài học này khi đổi code.
- Fresh temporary venv cài dependency/reload artifact sklearn1.7.2 PASS; test missing path/header, SQL port lỗi và rerun đạt hành vi dự kiến. Không reset database volume để thử rebuild phá hủy.
- Trạng thái lúc đó còn `BLOCKED_MANUAL` riêng Power BI vì không có `.pbix`/PBIP/refresh thật. Theo yêu cầu11/11, scope này đã thay bằng Dash; không cần tiếp tục tạo Power BI artifact.
- Static validator cũ cuối cùng98PASS/0FAIL/9runtime-scopeSKIPPED sau V14. Kết quả96PASS trước đó là snapshot trước thêm V14, không phải sai lệch cần che.

## 23/09/2026 — Incremental, CDC và ML có giới hạn tài nguyên

- CSV brvehins1 là static snapshot; incremental theo batch/file, không gọi là event stream. CDC demo chỉ trên `meta.CdcDemoOperationalRecord`.
- Demo run `f82755d1-1082-4f93-9e85-20a582738675` capture4changes:2insert,1update-before,1update-after; lần consume đầu4, replay0. LSN watermark `0x000000d6000177780007`, ledger giữ event identity.
- Các thử ML materialize full DWH rồi mẫu300k gặp giới hạn RAM/runtime; một thử đạt khoảng0,92GB working set trước khi bị dừng. Thiết kế chuyển sang deterministic population100.004, sparse float32 OHE, single-process, cap4k/24k/60k.
- So sánh majority dummy, SGD logistic và ComplementNB trên validation; giữ `claim_risk_model_v001` SGDClassifier(log_loss), final train cap60.000 từ train+validation, held-out20.000 không dùng fit/chọn model.
- Feature: Gender,DrivAge,VehYear,VehModel,VehGroup,Area,StateAb. Loại target/outcome-derived fields; split theo hash để duplicate nội dung không đi qua nhiều split.
- Test ROC-AUC0,8088149078; Average Precision0,5135228123; precision@0,5=0,699358; recall=0,202441; F1=0,313992; confusion matrix `[[15903,328],[3006,763]]`. Đây là cross-sectional association, không future customer/policy prediction.
- Artifact chứa preprocessing+estimator, metadata có version/feature/split/metric/dependency; reload100row có probability trùng tuyệt đối với pipeline trong memory.
- Scoring first run `88b2133f-71aa-42c0-92d3-3639b67bb779`, rerun `e800b561-9eb7-4819-bcc3-2ffd10edcfc1`:expected=predicted=stored20.000, difference0,duplicate0. Predict_proba~0,09s; không tính extraction/SQL trong số đó.
- Kiến trúc được realign thành hai track active canonical; Prudential chỉ planned/not present. Không tự thêm Customer/Policy hoặc cross-track mapping.

## 22/09/2026 — Foundation Track B

- Đọc năm partition thực tế,23 cột,393.071 dòng/file, tổng1.965.355. Giữ14logical duplicate, descriptor nullable, không sửa raw.
- Precision audit chốt ExposTotal DECIMAL(21,17), PremTotal DECIMAL(34,27); không làm tròn về kiểu tiện tay. V5 cập nhật theo evidence.
- Streaming loader, manifest, ingestion audit, application lock/unique key và retry semantics được xây trước DWH. Bulk CSV landing không phù hợp được bỏ ở V4; Python giữ RFC-aware parsing.
- Dimensions DriverProfile24,Vehicle25.092,Geography42 observed tuples, mỗi bảng có unknown member kỹ thuật thêm riêng. Rerun chèn0; natural hash unique.
- FactRiskObservation=staging1.965.355,orphan FK0,rerun thêm0. Grain source file+ordinal, không Customer/Policy/SCD2/date giả.
- Production DQ pass; controlled failure ghi FAIL và THROW51040, không mutate canonical data; production rerun pass.
- Dependency host/dev được tách khỏi Airflow. Foundation lúc đó55PASS/0FAIL/8runtime-scopeSKIPPED; chưa có ML/Airflow/BI. Các phase sau đã thay trạng thái này, không dùng báo cáo foundation làm mức hoàn thành hiện tại.

## Nguyên tắc ghi tiếp

Thêm entry có ngày, thay đổi, đường dẫn chuẩn, kiểm tra thật và giới hạn. Không chép nguyên terminal log dài, không tạo hàng loạt checkpoint mới. Phân biệt `static`, `runtime hiện tại`, `bằng chứng lịch sử`; không dùng phần trăm hoàn thành không có tiêu chí. Khi đổi cách chạy, cập nhật GUIDE/README/AGENTS trong cùng thay đổi.
