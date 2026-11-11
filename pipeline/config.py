"""Shared local environment and SQL Server settings."""

from __future__ import annotations

import os
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)


def connection_string(database: str | None = None) -> str:
    def quote(value: str) -> str:
        return "{" + value.replace("}", "}}") + "}"

    password = os.environ.get("SQLSERVER_SA_PASSWORD")
    if not password:
        raise RuntimeError("Thiếu SQLSERVER_SA_PASSWORD. Tạo .env theo .env.example.")
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={quote(os.getenv('SQLSERVER_HOST', 'localhost,1433'))};"
        f"DATABASE={quote(database or os.getenv('SQLSERVER_DATABASE', 'DWH_Insurance'))};"
        f"UID={quote(os.getenv('SQLSERVER_USER', 'sa'))};PWD={quote(password)};"
        "Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=10;"
    )


def connect(database: str | None = None, *, autocommit: bool = False) -> pyodbc.Connection:
    return pyodbc.connect(connection_string(database), autocommit=autocommit)
