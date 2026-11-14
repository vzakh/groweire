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


EXPECTED_UNITS = {
    "ALLSKY_SFC_SW_DWN": "MJ/m^2/day",
    "WS2M": "m/s",
    "PRECTOTCORR": "mm/day",
    "T2M_MAX": "C",
    "T2M_MIN": "C",
    "T2MDEW": "C",
}


def check_units(obj: dict) -> None:
    """Assert the POWER response units FAO-56 ET0 relies on (PLAN_10 task 12)."""
    meta = obj.get("parameters", {})
    for param, unit in EXPECTED_UNITS.items():
        got = meta.get(param, {}).get("units")
        if got is not None and got != unit:
            raise ValueError(f"POWER {param} unit is {got!r}, expected {unit!r}")


def node_metadata(raw_dir) -> "pd.DataFrame":
    """Per POWER node: lat, lon, elevation [m] from the raw responses (data/raw/power/*.json)."""
    import json  # pylint: disable=import-outside-toplevel
    from pathlib import Path  # pylint: disable=import-outside-toplevel

    rows = []
    for path in sorted(Path(raw_dir).glob("n_*.json")):
        obj = json.loads(path.read_text())
        check_units(obj)
        lon, lat, elev = obj["geometry"]["coordinates"][:3]
        rows.append(
            {"node_id": path.stem, "lat": float(lat), "lon": float(lon), "elev_m": float(elev)}
        )
    return pd.DataFrame(rows).set_index("node_id")
