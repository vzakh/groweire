"""NASA POWER daily point JSON -> tidy daily frame (the input of power_daily_to_monthly)."""

from __future__ import annotations

import pandas as pd

from agrolens_ml.contract import POWER_DAILY_PARAMETERS


def power_json_to_daily(obj: dict) -> pd.DataFrame:
    """POWER `/temporal/daily/point` JSON -> DataFrame[date, *POWER_DAILY_PARAMETERS]."""
    param = obj["properties"]["parameter"]
    missing = [p for p in POWER_DAILY_PARAMETERS if p not in param]
    if missing:
        raise ValueError(f"POWER response lacks parameters: {missing}")
    df = pd.DataFrame({p: param[p] for p in POWER_DAILY_PARAMETERS})
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    return df.rename_axis("date").reset_index()
