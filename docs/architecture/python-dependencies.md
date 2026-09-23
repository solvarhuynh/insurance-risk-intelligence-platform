# Python dependency boundary

Trạng thái: `RUNTIME_PASS`. Một môi trường ảo sạch dùng Python 3.12.6 đã cài thành công `requirements-dev.txt` và import được toàn bộ dependency khai báo. Không cài Apache Airflow vào host Python.

## Kết quả audit import

Standard library duy nhất xuất hiện trong `scripts/`, `notebooks/`, `ml/` và `dags/` gồm `argparse`, `csv`, `decimal`, `hashlib`, `json`, `os`, `pathlib`, `pickle`, `sqlite3`, `subprocess`, `sys`, `tempfile`, `time`, `uuid`, `datetime`, `typing`, `collections` và `dataclasses`.

Third-party import được chứng minh bởi source hiện tại:

- `numpy` và `pandas`: `scripts/profile_brvehins1.py`; `pandas` cũng được import ở `notebooks/01-eda.ipynb`.
- `pyodbc`: `scripts/load_brvehins1_to_staging.py`, kết nối host Python tới SQL Server bằng ODBC Driver 18.
- `yaml` từ PyYAML: import có điều kiện trong `scripts/validate_repo.py` để parse Compose; Docker CLI là fallback nếu PyYAML không có.
- `airflow`: chỉ `dags/insurance_dwh_pipeline.py`. Nó thuộc image Docker `apache/airflow:2.8.1-python3.10`, không thuộc môi trường Python host.

`ml/` hiện chỉ import standard library. Không thêm scikit-learn, LightGBM hoặc package ML trước khi stage ML có implementation thật.

## Manifest

`requirements.txt` là host runtime tối thiểu: `numpy`, `pandas`, `pyodbc`. `requirements-dev.txt` include host runtime rồi thêm `PyYAML` cho validator và `jupyterlab` để chạy notebook EDA. Version pin được chọn từ version đã import thành công trong Python 3.12.6; `jupyterlab==4.6.4` được chọn từ version khả dụng trên package index và được xác minh bằng clean install.

Bằng chứng cài đặt sạch ngày 2026-09-22: `pip install -r requirements-dev.txt` hoàn tất thành công trong virtual environment mới; các import `numpy==2.4.6`, `pandas==3.0.3`, `pyodbc==5.3.0`, `yaml` từ `PyYAML==6.0.3` và `jupyterlab==4.6.4` đều thành công.

Airflow không nằm trong hai manifest. Dependency Airflow được cô lập trong Docker image pin ở `docker-compose.yml`; host chỉ py_compile DAG, không import hoặc chạy nó.

## Cài và xác minh

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -c "import numpy, pandas, pyodbc, yaml, jupyterlab; print('dependency imports OK')"
```

Để chạy staging loader, máy host cần Microsoft ODBC Driver 18 for SQL Server ngoài Python package `pyodbc`. Password chỉ truyền bằng environment variable `SQLSERVER_SA_PASSWORD`; không thêm vào requirements hoặc source control.
