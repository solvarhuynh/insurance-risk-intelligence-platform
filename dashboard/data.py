"""Load the explicitly dated, aggregate SQL snapshot without opening SQL on page views."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


@lru_cache(maxsize=2)
def _read(path: str, modified_ns: int) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Snapshot không tương thích. Chạy pipeline/export_dashboard.py.")
    return payload


def snapshot() -> dict:
    path = Path(os.getenv("DASHBOARD_DATA_PATH", str(ROOT / "data/dashboard.json")))
    if not path.is_file():
        raise FileNotFoundError("Chưa có data/dashboard.json. Chạy python pipeline/export_dashboard.py.")
    return _read(str(path), path.stat().st_mtime_ns)


def table(section: str, name: str) -> pd.DataFrame:
    spec = snapshot()[section][name]
    return pd.DataFrame.from_records(spec["rows"], columns=spec["columns"])


def market_frames(state: str | None, years: list[int]) -> tuple:
    result = []
    for name in ("monthly", "companies", "products"):
        frame = table("market", name)
        if name == "monthly":
            frame["year"] = frame["month"].str[:4].astype(int)
        frame = frame.loc[frame["year"].between(*years)]
        if state and state != "ALL":
            frame = frame.loc[frame["state"] == state]
        result.append(frame)
    return tuple(result)


def risk_frames(state: str | None) -> tuple:
    frames = [table("risk", "segments"), table("risk", "scores")]
    return tuple(frame.loc[frame["state"] == state] if state and state != "ALL" else frame for frame in frames)
