# Python dependency boundary

## Dependency nào phục vụ thành phần nào?

Host runtime trong requirements.txt có các nhóm rõ ràng:

- numpy và pandas phục vụ profiling/EDA Track B.
- pyodbc kết nối host loader Track B tới SQL Server.
- scikit-learn và joblib phục vụ preprocessing, training, artifact reload và batch scoring Track B.
- PyYAML và JupyterLab thuộc requirements-dev.txt cho static validator/notebook tooling.
- Airflow được cô lập trong Docker image, không được cài vào host chỉ để import DAG.

Scikit-learn và joblib là dependency hiện hành, không phải future placeholder: ml/modeling.py, train_risk_model.py và predict_risk_batch.py dùng chúng cho Track B.

## Boundary này liên quan gì đến nhiều track?

Dependency boundary là platform-level. Nó không có nghĩa SUSEP đã dùng pandas/pyodbc để ingest hoặc Airflow đã chạy orchestration. Khi P1-SUSEP-01 tạo tool thật, dependency mới chỉ được thêm nếu source code và verification chứng minh cần thiết.

## Tôi cài và kiểm tra thế nào?

~~~powershell
python -m venv .venv
./.venv/Scripts/python -m pip install --upgrade pip
./.venv/Scripts/python -m pip install -r requirements-dev.txt
./.venv/Scripts/python -c "import numpy, pandas, pyodbc, sklearn, joblib, yaml, jupyterlab; print('dependency imports OK')"
~~~

ODBC Driver 18 for SQL Server là dependency hệ điều hành ngoài Python package pyodbc. Password chỉ truyền qua SQLSERVER_SA_PASSWORD; không đưa credential vào dependency manifest hay source control.
