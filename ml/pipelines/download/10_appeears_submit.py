"""Submit NASA AppEEARS jobs for Ireland. RUN THIS FIRST: jobs take hours to process.

Needs an Earthdata Login (https://urs.earthdata.nasa.gov) in .env:
  EARTHDATA_USERNAME=...   EARTHDATA_PASSWORD=...

Jobs (task names are prefixed 'agrolens_'):
  area   MOD13Q1.061  NDVI + pixel reliability, Feb-Oct, split into 5-year chunks (Terra)
  area   MYD13Q1.061  same (Aqua)  -> Terra+Aqua composite improves cloud gaps
  area   MCD12Q1.061  LC_Type1 (IGBP land cover, agricultural mask)
  area   SRTMGL1_NC.003  elevation (slope is derived later)
  point  SPL4SMGP.008 root-zone soil moisture + percentile at the 0.25 deg grid (2015-04 ->)

Layer names are resolved against the live AppEEARS product catalogue, so a renamed layer fails
loudly with the list of available layers instead of silently submitting a bad job.
Task IDs are saved to data/raw/appeears/tasks.json for 11_appeears_download.py.

  python 10_appeears_submit.py --dry-run     # print the job JSON, submit nothing
  python 10_appeears_submit.py --only ndvi   # submit a subset: ndvi|landcover|srtm|smap
"""
from __future__ import annotations

import argparse
import json
import os

import requests

from common import CONFIG, IE_BBOX, RAW, YEAR_END, YEAR_START, load_env, log, read_grid, save_json

API = "https://appeears.earthdatacloud.nasa.gov/api"
TASKS_FILE = RAW / "appeears" / "tasks.json"
NDVI_CHUNK_YEARS = 5

# (product, wanted-layer substrings). Substring match keeps us robust to small name changes.
NDVI_LAYERS = ["250m_16_days_NDVI", "250m_16_days_pixel_reliability"]
SMAP_LAYERS = ["sm_rootzone", "sm_rootzone_pctl"]


def login() -> str:
    user, pwd = os.environ.get("EARTHDATA_USERNAME"), os.environ.get("EARTHDATA_PASSWORD")
    if not user or not pwd:
        raise SystemExit("Set EARTHDATA_USERNAME / EARTHDATA_PASSWORD in .env")
    r = requests.post(f"{API}/login", auth=(user, pwd), timeout=60)
    r.raise_for_status()
    return r.json()["token"]


def resolve_layers(product: str, wanted: list[str]) -> list[str]:
    r = requests.get(f"{API}/product/{product}", timeout=60)
    r.raise_for_status()
    available = list(r.json().keys())
    picked = []
    for w in wanted:
        exact = [a for a in available if a.lstrip("_") == w.lstrip("_")]
        # prefer an exact match, then the shortest name containing the substring
        cands = exact or sorted((a for a in available if w in a), key=len)
        if not cands:
            raise SystemExit(f"{product}: no layer matching '{w}'. Available: {available}")
        picked.append(cands[0])
    return picked


def bbox_geo() -> dict:
    x0, y0, x1, y1 = IE_BBOX
    ring = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"name": "ireland_bbox"},
         "geometry": {"type": "Polygon", "coordinates": [ring]}}]}


def area_task(name: str, product: str, layers: list[str], dates: list[dict]) -> dict:
    return {
        "task_type": "area",
        "task_name": name,
        "params": {
            "dates": dates,
            "layers": [{"product": product, "layer": lyr} for lyr in layers],
            "output": {"format": {"type": "netcdf4"}, "projection": "geographic"},
            "geo": bbox_geo(),
        },
    }


def point_task(name: str, product: str, layers: list[str], dates: list[dict], grid: str) -> dict:
    coords = [{"id": c["cell_id"], "category": "grid", "latitude": c["lat"], "longitude": c["lon"]}
              for c in read_grid(grid)]
    return {
        "task_type": "point",
        "task_name": name,
        "params": {
            "dates": dates,
            "layers": [{"product": product, "layer": lyr} for lyr in layers],
            "coordinates": coords,
        },
    }


def build_tasks(only: set[str], offline: bool) -> list[dict]:
    def layers(product, wanted):
        return wanted if offline else resolve_layers(product, wanted)

    tasks = []
    if "ndvi" in only:
        for product in ("MOD13Q1.061", "MYD13Q1.061"):
            lyr = layers(product, NDVI_LAYERS)
            for y0 in range(YEAR_START, YEAR_END + 1, NDVI_CHUNK_YEARS):
                y1 = min(y0 + NDVI_CHUNK_YEARS - 1, YEAR_END)
                # recurring Feb-Oct window each year (we only model Mar-Oct; Feb gives lag-1)
                dates = [{"startDate": "02-01", "endDate": "10-31", "recurring": True,
                          "yearRange": [y0, y1]}]
                tasks.append(area_task(f"agrolens_{product.split('.')[0]}_{y0}_{y1}",
                                       product, lyr, dates))
    if "landcover" in only:
        tasks.append(area_task("agrolens_MCD12Q1", "MCD12Q1.061", layers("MCD12Q1.061", ["LC_Type1"]),
                               [{"startDate": "01-01-2019", "endDate": "12-31-2023"}]))
    if "srtm" in only:
        tasks.append(area_task("agrolens_SRTM", "SRTMGL1_NC.003",
                               layers("SRTMGL1_NC.003", ["SRTMGL1_DEM"]),
                               [{"startDate": "02-11-2000", "endDate": "02-21-2000"}]))
    if "smap" in only:
        tasks.append(point_task("agrolens_SPL4SMGP", "SPL4SMGP.008",
                                layers("SPL4SMGP.008", SMAP_LAYERS),
                                [{"startDate": "04-01-2015", "endDate": f"12-31-{YEAR_END}"}],
                                "grid_025deg.csv"))
    return tasks


def main() -> None:
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="ndvi,landcover,srtm,smap")
    args = ap.parse_args()
    only = {s.strip() for s in args.only.split(",")}

    tasks = build_tasks(only, offline=args.dry_run)
    if args.dry_run:
        for t in tasks:
            preview = json.loads(json.dumps(t))
            if "coordinates" in preview["params"]:
                n = len(preview["params"]["coordinates"])
                preview["params"]["coordinates"] = f"<{n} points from {CONFIG.name}/grid_025deg.csv>"
            print(json.dumps(preview, indent=2))
        log.info("dry run: %d tasks built, nothing submitted", len(tasks))
        return

    token = login()
    headers = {"Authorization": f"Bearer {token}"}
    saved = json.loads(TASKS_FILE.read_text()) if TASKS_FILE.exists() else {}
    for t in tasks:
        if t["task_name"] in saved:
            log.info("skip %s (already submitted: %s)", t["task_name"], saved[t["task_name"]])
            continue
        r = requests.post(f"{API}/task", json=t, headers=headers, timeout=120)
        if r.status_code >= 400:
            log.error("submit %s failed: %s %s", t["task_name"], r.status_code, r.text[:500])
            continue
        tid = r.json()["task_id"]
        saved[t["task_name"]] = tid
        save_json(saved, TASKS_FILE)
        log.info("submitted %s -> %s", t["task_name"], tid)
    log.info("%d tasks recorded in %s", len(saved), TASKS_FILE)


if __name__ == "__main__":
    main()
