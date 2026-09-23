# P1-INFRA-DEPS — Dependency Python cho foundation

Ngày: 2026-09-22

Kết quả: RUNTIME_PASS

## Mục tiêu

Kiểm toán import Python trong `scripts/`, `notebooks/`, `ml/` và `dags/`; tạo manifest dependency tối thiểu, tách host/dev khỏi Airflow container, rồi chứng minh manifest cài được trong môi trường sạch.

## File đã thay đổi

- `requirements.txt`
- `requirements-dev.txt`
- `docs/architecture/python-dependencies.md`
- `README.md`
- `docs/guides/how-to-run.md`
- `docs/architecture/repository-structure.md`
- `scripts/validate_repo.py`
- `log/progress-log.md`
- `reports/checkpoints/P1-INFRA-DEPS.md`

## Kết quả audit import

| Nhóm | Dependency | Lý do và nơi dùng |
|---|---|---|
| Standard library | Không khai báo package | Các import như `csv`, `decimal`, `pathlib`, `json`, `sqlite3`, `typing` thuộc Python chuẩn trong toàn bộ bốn thư mục audit. |
| Host runtime | `numpy==2.4.6`, `pandas==3.0.3` | `scripts/profile_brvehins1.py`; `pandas` cũng được notebook EDA dùng. |
| Host runtime | `pyodbc==5.3.0` | `scripts/load_brvehins1_to_staging.py` kết nối SQL Server qua ODBC Driver 18 của hệ điều hành. |
| Development/notebook | `PyYAML==6.0.3` | `scripts/validate_repo.py` parse Compose khi có sẵn; Docker CLI là fallback. |
| Development/notebook | `jupyterlab==4.6.4` | Chạy `notebooks/01-eda.ipynb`. |
| Airflow container | Không có package trong host manifest | `dags/insurance_dwh_pipeline.py` import `airflow`; runtime này nằm trong image `apache/airflow:2.8.1-python3.10` ở Compose. |

`ml/` hiện chỉ dùng standard library. Không thêm thư viện ML chưa được sử dụng bởi foundation workflow.

## Lệnh đã chạy

```text
python --version
<clean-venv>\\Scripts\\python -m pip install --upgrade pip
<clean-venv>\\Scripts\\python -m pip install -r requirements-dev.txt
<clean-venv>\\Scripts\\python -c "import numpy, pandas, pyodbc, yaml, jupyterlab"
python scripts/validate_repo.py
git diff --check
```

## Bằng chứng runtime

- Python host là `3.12.6`.
- Một virtual environment mới đã cài thành công `requirements-dev.txt`.
- Import đã thành công với `numpy 2.4.6`, `pandas 3.0.3`, `pyodbc 5.3.0`, `PyYAML 6.0.3` và `JupyterLab 4.6.4`.
- `python scripts/validate_repo.py` kết thúc `49 PASSED | 0 FAILED | 8 SKIPPED`.
- `git diff --check` exit code `0`.
- `pyodbc` vẫn cần Microsoft ODBC Driver 18 for SQL Server ở cấp hệ điều hành; đây không phải dependency pip và đã được hướng dẫn trong tài liệu chạy.

## Quyết định

- `requirements.txt` chỉ chứa dependency runtime cần thiết cho profiler và staging loader trên host.
- `requirements-dev.txt` include runtime manifest và thêm công cụ validator/notebook.
- Airflow không được khai báo trong hai manifest để tránh cài runtime Docker vào host Python.
- Version chỉ được pin sau khi clean install/import trên Python 3.12.6 thành công.

## Lưu ý môi trường

Virtual environment tạm `D:\\1-personal-project\\.tmp-dependency-check-20260922` còn tồn tại tại thời điểm checkpoint. Đường dẫn đã được xác minh là môi trường kiểm tra tạm; lệnh xóa chính xác bằng `Remove-Item -LiteralPath ... -Recurse -Force` bị chính sách thực thi của môi trường chặn trước khi chạy. Nó không là một phần của manifest hay source; cần xóa cục bộ sau khi không còn dùng nếu Git vẫn hiển thị untracked.

## Tiêu chí PASS

- [x] Import bốn phạm vi được audit và phân loại.
- [x] Không thêm package không có bằng chứng sử dụng.
- [x] Có `requirements.txt` và `requirements-dev.txt` có pin tương thích với Python 3.12.6 đã kiểm chứng.
- [x] Airflow được cô lập trong Docker environment.
- [x] Clean install và import thực tế thành công.
- [x] README, hướng dẫn chạy, repository structure và validator đã được cập nhật phù hợp.

## Bước tiếp theo chính xác

`P1-DWH-01` — thiết kế dimensional model dựa trên contract và staging đã được đối soát, trước khi tạo DDL dimensions/fact.
