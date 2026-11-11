# Bàn giao Insurance Data Platform cho AI

## Trạng thái và tài liệu chuẩn

- Cập nhật 11/11/2026. Repo cá nhân tại `D:\1-personal-project`; đang refactor trực tiếp trên `main`, chưa commit/push đợt thay đổi này. Không tạo nhánh hoặc push chỉ vì tài liệu lịch sử có lệnh Git.
- Đọc `README.md` để chạy nhanh, `GUIDE.md` để hiểu kiến trúc/contract/vận hành, `CHANGELOG.md` để biết lịch sử và bằng chứng. Đây là bốn file markdown chuẩn ở root; không tạo thêm guide/checkpoint/report cạnh tranh.
- Power BI đã được thay bằng ứng dụng thật trong `dashboard/`. Snapshot `data/dashboard.json` là aggregate SQL xuất 11/11/2026, có timestamp; không realtime và không cần secret để xem local.
- Nghiệm thu hiện tại: 5 unit tests, browser desktop/mobile + CSV, hai DQ SQL và Airflow DAG test 12/12 task PASS. Dash chạy Docker/Gunicorn tại 8050. Run hiện tại và giới hạn xem CHANGELOG, không nhầm với scheduler production.
- Sáu thư mục chính: `dashboard`, `pipeline`, `database`, `infra`, `data`, `tests`. Không khôi phục các thư mục cũ chỉ để đáp ứng hướng dẫn đã lỗi thời.

## Ranh giới phải giữ

- Track A SUSEP: 8.338.214 dòng, grain company/month/product/state. Track B brvehins1: 1.965.355 dòng quan sát motor risk tổng hợp. Không có row-level join, CustomerId, PolicyId hoặc claim event identity được chứng minh giữa hai nguồn.
- Prudential chưa có raw (`NOT_PRESENT/FUTURE`). Không tự tải, tạo nguồn giả hoặc pipeline thứ ba.
- `data/raw/**` bất biến: không sửa/xóa/di chuyển. `.env`, raw, model binary, generated output và `.venv` không đưa lên Git. `.env.example`, snapshot aggregate và evidence lịch sử được track.
- Giữ volume `sqlserver_data`; không `down -v`, không đổi project name Compose vô tình. Chưa chạy destructive fresh rebuild trong lần refactor này.
- Giữ artifact `data/models/claim_risk_model_v001.joblib` và metadata hiện hữu; không train lại nếu task không cần. Model là cross-sectional HasClaim association trên mẫu100.004, test20.000; không future underwriting probability.
- Chỉ số ROC-AUC0,808815/AP0,513523 và benchmark reads là evidence tháng09/2026. Không biến thành phép đo mới. Đơn vị tiền SUSEP chưa xác nhận; không tự gắn BRL.

## Lệnh chuẩn và kiểm tra

- Local Python3.12: `.venv\Scripts\python.exe -m dashboard.app`, mở `http://127.0.0.1:8050`.
- CLI SQL: `python pipeline/manage.py migrate|load-market|load-risk|quality|status|score|export` (chọn một action). Migrate giữ nguyên version V1–V14, sort theo số, skip lịch sử đã áp dụng.
- Config SQL: `pipeline/config.py` đọc `.env`; không in secret/connection string ra output. Migration hiện cố định tên `DWH_Insurance`.
- Static: `python pipeline/validate_repo.py`; tùy chọn `--raw` khi đã có CSV local.
- Tests: `python -m unittest discover -s tests -p test_*.py`; browser: chạy app rồi `python tests/browser_check.py` (Playwright + Edge).
- Compose: `docker compose --profile analytics up -d --build dashboard`; Airflow profile `orchestration`. Dockerfile nằm trong `infra/`.
- SQL quality gate phải drain tất cả resultsets (`cursor.nextset`) để nhận terminal THROW. Airflow run ID được đổi UUID5 trước batch scoring.
- Airflow DAG ở `pipeline/airflow_dag.py`, scan qua `.airflowignore`. B yêu cầu foundation/model có sẵn; DAG không tự train và chưa tự export snapshot.

## Tiếp quản và cập nhật

- Kết quả kiểm tra mới nhất và giới hạn nằm trong CHANGELOG. Đọc phần 11/11/2026 trước khi nói thành phần nào đã được nghiệm thu.
- Cập nhật GUIDE khi thay cách chạy/contract; cập nhật CHANGELOG khi có thay đổi đáng kể và bằng chứng thật; cập nhật file này khi trạng thái/cấu trúc thay đổi.
- Không xóa SQL migration còn dùng chỉ vì thấy comment lịch sử; code scaffold Customer/Policy cũ đã bị loại theo yêu cầu owner. Nâng schema mới bằng migration mới.
- Tài liệu cũ được sao lưu ngoài Git: `D:\insurance-platform-archive-20261111\documents-before-restructure.zip`. Chỉ phục hồi phần cần thiết, không bung toàn bộ lại vào repo.
- Hướng phát triển có giá trị: nghiệm thu fresh rebuild/restore trên database cô lập; CI cho tests; tự export sau quality gates; model validation theo thời gian khi có nguồn phù hợp. Không tự nhận production-ready.
