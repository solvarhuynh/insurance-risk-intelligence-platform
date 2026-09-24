FROM apache/airflow:2.8.1-python3.10
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg2 ca-certificates unixodbc-dev \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --batch --yes --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -sSL https://packages.microsoft.com/config/debian/12/prod.list -o /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*
USER airflow
COPY airflow/requirements.txt /tmp/airflow-ml-requirements.txt
RUN pip install --no-cache-dir --retries 10 --timeout 120 -r /tmp/airflow-ml-requirements.txt
