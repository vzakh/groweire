"""Download NASA POWER daily agroclimatology for every POWER grid node covering Ireland.

POWER meteorology is on a ~0.5 deg (lat) x 0.625 deg (lon) MERRA-2 grid, so the ~4.5k analysis
cells collapse to a few dozen unique nodes. We query each node once and map cells -> node.

Outputs:
  data/raw/power/node_<lat>_<lon>.json      raw API responses (cache; re-runs skip existing)
  data/processed/power_daily.parquet         long table: node_id, date, <params>
  data/processed/cell_to_power_node.csv      cell_id -> node_id
No login needed.
"""
from __future__ import annotations

import argparse
import csv
import json

import pandas as pd
import requests

from common import PROCESSED, RAW, YEAR_END, YEAR_START, ensure, log, read_grid, retry, save_json

API = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = [
    "T2M", "T2M_MAX", "T2M_MIN", "T2MDEW", "PRECTOTCORR", "RH2M",
    "WS2M", "ALLSKY_SFC_SW_DWN", "GWETROOT", "GWETTOP",
]
LAT_STEP, LON_STEP = 0.5, 0.625


def snap(lat: float, lon: float) -> tuple[float, float]:
    """Nearest POWER MERRA-2 grid-node centre."""
    nlat = round((lat + 90) / LAT_STEP) * LAT_STEP - 90
    nlon = round((lon + 180) / LON_STEP) * LON_STEP - 180
    return round(nlat, 3), round(nlon, 4)


def node_id(lat: float, lon: float) -> str:
    return f"n_{lat:.3f}_{lon:.4f}"


def fetch_node(lat: float, lon: float, start: str, end: str) -> dict:
    url = (f"{API}?parameters={','.join(PARAMS)}&community=AG&latitude={lat}&longitude={lon}"
           f"&start={start}&end={end}&format=JSON&time-standard=LST")
    def _get():
        r = requests.get(url, timeout=180)
        r.raise_for_status()
        return r.json()
    return retry(_get)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="only list nodes")
    args = ap.parse_args()

    cells = read_grid()
    mapping, nodes = [], {}
    for c in cells:
        nlat, nlon = snap(c["lat"], c["lon"])
        nid = node_id(nlat, nlon)
        nodes[nid] = (nlat, nlon)
        mapping.append({"cell_id": c["cell_id"], "node_id": nid})
    log.info("%d cells -> %d POWER nodes", len(cells), len(nodes))

    ensure(PROCESSED)
    with open(PROCESSED / "cell_to_power_node.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["cell_id", "node_id"])
        w.writeheader()
        w.writerows(mapping)
    if args.dry_run:
        for nid, (la, lo) in sorted(nodes.items()):
            print(nid, la, lo)
        return

    raw_dir = ensure(RAW / "power")
    start, end = f"{YEAR_START}0101", f"{YEAR_END}1231"
    frames = []
    for i, (nid, (la, lo)) in enumerate(sorted(nodes.items()), 1):
        path = raw_dir / f"{nid}.json"
        if not path.exists():
            log.info("[%d/%d] POWER %s", i, len(nodes), nid)
            save_json(fetch_node(la, lo, start, end), path)
        data = json.loads(path.read_text())
        param = data["properties"]["parameter"]
        df = pd.DataFrame(param)
        df.index = pd.to_datetime(df.index, format="%Y%m%d")
        df = df.replace(-999.0, pd.NA)
        df["node_id"], df["node_lat"], df["node_lon"] = nid, la, lo
        frames.append(df.rename_axis("date").reset_index())

    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(PROCESSED / "power_daily.parquet", index=False)
    log.info("wrote power_daily.parquet: %d rows, %d nodes", len(out), out.node_id.nunique())


if __name__ == "__main__":
    main()
