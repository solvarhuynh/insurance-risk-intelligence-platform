# Báo cáo file không đưa vào Git

Các file dưới đây không được push vì là raw data lớn, credential, binary artifact hoặc output runtime cục bộ. Chúng đã được giữ trong `.gitignore` và không nằm trong các commit của nhánh `task1`.

| Đường dẫn | Lý do không push | Rule `.gitignore` |
|---|---|---|
| `.env` | Chứa SQL Server/Airflow secret | `.env`, `*.env` |
| `data/raw/brvehins1/` | Raw CSV nguồn, dữ liệu lớn và immutable | `data/raw/*` |
| `data/raw/susep.gov.br/` | Raw SUSEP CSV khoảng 751 MB, không đưa vào Git | `data/raw/*` |
| `ml/artifacts/claim_risk_model_v001.joblib` | Binary model artifact, tái tạo/reload cục bộ theo dependency contract | `ml/artifacts/*` |
| `ml/artifacts/claim_risk_model_v001.metadata.json` | Metadata đi cùng artifact runtime cục bộ | `ml/artifacts/*` |
| `ml/**/__pycache__/`, `scripts/**/__pycache__/` | Python cache | `__pycache__/` |
| `log/scheduler/`, `log/dag_processor_manager/`, `log/dag_id=*/` | Airflow live runtime logs | explicit `log/...` rules |
| `reports/data/*.log` | Profiler/ML execution logs trung gian | `reports/data/*.log` |
| `.tmp-*`, `.venv/` | Temporary dependency/runtime environment | `.tmp-dependency-check-*/`, `.venv/` |
| `AGENT_PROMPT_HISTORY.md` | Local agent-session history, không phải project source | explicit history rule |

Các file evidence dạng `.md`/`.json`/`.csv` nhỏ trong `reports/data/` vẫn được push khi Git nhận diện chúng là deliverable; chỉ execution log bị loại.

## Cách tái tạo sau khi clone

1. Tạo `.env` từ `.env.example` và tự đặt secret local.
2. Đặt raw CSV vào đúng `data/raw/` theo source contract.
3. Dùng `.venv` và Docker Compose theo `docs/guides/how-to-run.md`.
4. Reload model bằng dependency pin; không cần commit binary artifact.

Kết luận: không có file bị mất ngoài ý muốn; các file excluded đều có lý do và đường dẫn phục hồi rõ ràng.
