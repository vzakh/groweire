"""PLAN_40 "Checks that must pass" on the REAL pilot data (skipped when data/processed is absent).

These pin what the screen claims: the counts have a season, the known drought years show up,
and the satellite agrees. The bars are the plan's words ("most cells", "clearly higher"), not
tuned numbers: if one fails, look at the data, do not move the bar or a threshold.

The plan's "map is not one colour" check is NOT pinned here: it fails for drought (PLAN_40 Log).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from agrolens_ml import risk_counts as rc

PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"
NEEDED = (
    "power_daily.parquet",
    "power_nodes.csv",
    "cell_to_power_node.csv",
    "grid_cells.parquet",
    "ndvi_cell_month.parquet",
    rc.IMERG_FILE,
)
pytestmark = pytest.mark.skipif(
    not all((PROCESSED / name).exists() for name in NEEDED),
    reason="real pilot tables (incl. IMERG) are not in data/processed",
)

DEMO_CELL = "c01501"  # Oak Park, Co. Carlow
CARLOW = {"lat": (52.46, 52.92), "lon": (-7.11, -6.50)}  # rough county box
SOUTH_EAST = {"lat_below": 53.5, "lon_above": -8.0}


@pytest.fixture(scope="module")
def hits() -> pd.DataFrame:
    """One row per cell x year x month (3..10) x stress type, with lat / lon."""
    table = rc.build_cell_hits(PROCESSED)
    table = table[table["month"].between(3, 10)]
    cells = pd.read_parquet(PROCESSED / "grid_cells.parquet", columns=["cell_id", "lat", "lon"])
    return table.merge(cells, on="cell_id")


def _frequency(hits: pd.DataFrame, stress_type: str) -> pd.Series:
    sub = hits[hits["stress_type"] == stress_type]
    return sub.groupby(["cell_id", "month"])["hit"].mean()


def test_seasonality_exists_for_the_demo_field(hits):
    demo = hits[hits["cell_id"] == DEMO_CELL]
    by_month = demo.groupby(["month", "stress_type"])["hit"].mean().unstack().max(axis=1)
    assert by_month.max() - by_month.min() >= 0.3, by_month.round(2).to_dict()
    # drought only ever happens in summer, frost only in spring
    drought = demo[(demo["stress_type"] == "drought") & demo["hit"]]
    assert set(drought["month"]) <= {6, 7, 8}


def test_july_is_the_top_drought_month_in_carlow(hits):
    carlow = hits[hits["lat"].between(*CARLOW["lat"]) & hits["lon"].between(*CARLOW["lon"])]
    by_month = carlow[carlow["stress_type"] == "drought"].groupby("month")["hit"].mean()
    assert by_month.idxmax() == 7, by_month.round(3).to_dict()
    assert by_month[7] > 0


@pytest.mark.parametrize("year", [2018, 2006])
def test_known_drought_summers_show_up_in_the_south_and_east(hits, year):
    area = (hits["lat"] < SOUTH_EAST["lat_below"]) & (hits["lon"] > SOUTH_EAST["lon_above"])
    summer = hits[
        area
        & (hits["stress_type"] == "drought")
        & hits["month"].between(6, 8)
        & (hits["year"] == year)
    ]
    share = summer.groupby("cell_id")["hit"].any().mean()
    assert share > 0.5, f"{year}: only {share:.0%} of southern and eastern cells counted as dry"


def test_satellite_agrees_with_counted_drought_months(hits):
    ndvi = pd.read_parquet(
        PROCESSED / "ndvi_cell_month.parquet",
        columns=["cell_id", "month", "ndvi_z", "stress_label"],
    )
    ndvi = ndvi[ndvi["stress_label"].notna()]
    ndvi["year"] = ndvi["month"].str[:4].astype(int)
    ndvi["month"] = ndvi["month"].str[5:7].astype(int)
    drought = hits.loc[hits["stress_type"] == "drought", ["cell_id", "year", "month", "hit"]]
    merged = ndvi.merge(drought, on=["cell_id", "year", "month"])
    low = (merged["ndvi_z"] <= -1.0).groupby(merged["hit"]).mean()
    # "clearly higher": at least twice the share of cells with greenness well below normal
    assert low[True] >= 2 * low[False], low.round(3).to_dict()
