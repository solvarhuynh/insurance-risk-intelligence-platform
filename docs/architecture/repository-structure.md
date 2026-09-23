# Cấu trúc repository hiện tại

```text
insurance-dwh-project/
├── .cursor/rules/             # Quy tắc workflow, file/log, review, Python và handoff
├── data/raw/
│   ├── brvehins1/             # Nguồn chuẩn, năm CSV bất biến
│   └── susep.gov.br/          # LEGACY / NON-CANONICAL
├── docs/
│   ├── architecture/          # Kiến trúc, dictionary, contract và thiết kế DWH
│   ├── guides/                # Hướng dẫn chạy và thuật ngữ
│   ├── reports/               # Báo cáo insight/tuning ở giai đoạn sau
│   └── specs/                 # Phạm vi và lộ trình triển khai
├── log/                       # Nhật ký tiến độ append-only và review lịch sử
├── migrations/                # SQL migration có version
├── sql/                       # Staging, ingest, DWH và DQ SQL
├── scripts/                   # Validator và các công cụ lặp lại được
├── requirements.txt            # Runtime host: profiling và SQL Server staging loader
├── requirements-dev.txt        # Runtime host + validator/notebook tooling
├── notebooks/                 # EDA
├── dags/                      # Airflow, chỉ thực hiện sau nền tảng DQ
├── ml/                        # ML, chỉ thực hiện sau nền tảng DQ
├── powerbi/                   # Artifact Power BI trong tương lai
├── reports/                   # Checkpoint và báo cáo thực thi
├── docker-compose.yml         # Hạ tầng runtime cục bộ
├── .env.example               # Mẫu biến môi trường; .env local bị ignore
└── README.md                  # Điểm bắt đầu hiện hành
```

## Trách nhiệm và trạng thái

| Khu vực | Trách nhiệm | Trạng thái hiện tại |
|---|---|---|
| `data/raw/` | Lưu dữ liệu nguồn, không ghi đầu ra vào đây | `brvehins1` có mặt; raw bất biến. |
| `docs/` | Nguồn sự thật về kiến trúc, contract và vận hành | Đang được chuẩn hóa theo `brvehins1`. |
| `migrations/` | Bootstrap SQL có version | V1–V8 đã RUNTIME_PASS cho bootstrap, staging, dimensions, fact canonical và quality gate. |
| `sql/` | SQL entry point, DWH và DQ SQL | `01_load_staging.sql`, `04_load_canonical_dimensions.sql`, `05_load_fact_risk_observation.sql` và `07_run_quality_gate.sql` là entry point thực. Các SQL legacy khác là STALE SCAFFOLD — REQUIRES REFACTOR. |
| `scripts/` | Kiểm tra tĩnh và công cụ thực thi lặp lại được | Có validator, source profiler và streaming staging loader. |
| `requirements*.txt` | Dependency boundary cho host/dev | Host không có Airflow; Airflow nằm trong Docker image. |
| `notebooks/`, `reports/data/` | EDA và bằng chứng định lượng | P1-DATA-01 đã RUNTIME_PASS. |
| `dags/`, `ml/`, `powerbi/` | Các consumer ở milestone sau | Không phải phạm vi foundation hiện tại. |
| `log/`, `reports/checkpoints/` | Lịch sử append-only và handoff theo stage | Không rewrite lịch sử cũ. |

Không tạo file song song cho cùng một trách nhiệm. Những file tên cũ được giữ lại để refactor theo đúng stage, không phải để suy ra yêu cầu nghiệp vụ.
