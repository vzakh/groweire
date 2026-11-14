"""Grid helpers: MODIS sinusoidal geometry, cell keys, soil depth weighting (PLAN_10 task 10)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agrolens_ml import grid


def test_sinusoidal_tile_h17v03_covers_ireland():
    lon, lat = grid.sinusoidal_to_lonlat(17, 3, 2400)
    assert lat[0, 0] == pytest.approx(60.0, abs=0.01)  # northern edge of v03
    assert lat[-1, 0] == pytest.approx(50.0, abs=0.01)  # southern edge
    row = np.argmin(np.abs(lat[:, 0] - 53.0))  # at 53°N the tile spans ~-16.6° .. 0°
    assert lon[row, 0] == pytest.approx(-16.6, abs=0.1)
    assert lon[row, -1] == pytest.approx(0.0, abs=0.01)


def test_cell_index_matches_grid_centroids():
    # a centroid and points inside its 0.05° box share one key; neighbours differ
    k = grid.cell_index(np.array([-9.775]), np.array([51.475]))[0]
    inside = grid.cell_index(np.array([-9.7999, -9.7501]), np.array([51.4501, 51.4999]))
    assert (inside == k).all()
    assert grid.cell_index(np.array([-9.7499]), np.array([51.475]))[0] != k


def test_soil_depth_weighting_and_nan():
    soil = pd.DataFrame(
        {
            f"{p}_{d}": [v]
            for p in grid.SOIL_PROPS
            for (d, _), v in zip(grid.SOIL_DEPTHS, (10.0, 20.0, 30.0))
        }
    )
    out = grid.soil_0_30(soil)
    assert out.loc[0, "clay"] == pytest.approx((10 * 5 + 20 * 10 + 30 * 15) / 30)
    soil.loc[0, "clay_15_30cm"] = np.nan
    assert grid.soil_0_30(soil).loc[0, "clay"] == pytest.approx((10 * 5 + 20 * 10) / 15)


def test_wkt_box_is_closed_square():
    [wkt] = grid._wkt_box(np.array([-9.775]), np.array([51.475]))
    assert wkt.startswith("POLYGON ((-9.800 51.450") and wkt.endswith("-9.800 51.450))")


def test_ifs_drainage_mapping_is_ordinal_1_to_5():
    from agrolens_ml.grid import IFS_DRAINAGE

    vals = {v for v in IFS_DRAINAGE.values() if v is not None}
    assert vals <= {1, 2, 3, 4, 5}
    assert IFS_DRAINAGE[11] == 2 and IFS_DRAINAGE[31] == 4 and IFS_DRAINAGE[63] == 5
    assert IFS_DRAINAGE[76] is None  # water is not a soil
