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
        raise ValueError("Incompatible snapshot. Run python pipeline/manage.py export.")
    return payload


def snapshot() -> dict:
    path = Path(os.getenv("DASHBOARD_DATA_PATH", str(ROOT / "data/dashboard.json")))
    if not path.is_file():
        raise FileNotFoundError("Missing data/dashboard.json. Run python pipeline/manage.py export.")
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


def latest_market_comparison(monthly: pd.DataFrame, state: str | None) -> dict:
    """Compare the latest selected year's available months with those same prior-year months."""
    if monthly.empty:
        return {}
    latest = int(monthly["year"].max())
    current = monthly.loc[monthly["year"] == latest].copy()
    current["calendar_month"] = current["month"].str[5:7].astype(int)
    measures = ["premium", "claims", "observations"]
    current = current.groupby("calendar_month")[measures].sum()
    previous = table("market", "monthly")
    previous = previous.loc[previous["month"].str[:4] == str(latest - 1)].copy()
    if state and state != "ALL":
        previous = previous.loc[previous["state"] == state]
    previous["calendar_month"] = previous["month"].str[5:7].astype(int)
    previous = previous.groupby("calendar_month")[measures].sum().reindex(current.index)
    if previous.isna().any().any():
        return {}
    now, before = current.sum(), previous.sum()
    if now["premium"] <= 0 or before["premium"] <= 0:
        return {}
    months = list(current.index)
    start = pd.Timestamp(latest, months[0], 1).strftime("%b")
    end = pd.Timestamp(latest, months[-1], 1).strftime("%b")
    period = start if len(months) == 1 else f"{start}–{end}"
    if months != list(range(months[0], months[-1] + 1)):
        period = f"{len(months)} matched months"
    comparison = {
        "period": f"{period} {latest} vs {latest - 1}",
        "premium_change": 100 * (now["premium"] / before["premium"] - 1),
        "ratio_change_pp": 100 * (now["claims"] / now["premium"] - before["claims"] / before["premium"]),
    }
    if before["claims"] > 0:
        comparison["claims_change"] = 100 * (now["claims"] / before["claims"] - 1)
    if before["observations"] > 0:
        comparison["observations_change"] = 100 * (now["observations"] / before["observations"] - 1)
    return comparison
