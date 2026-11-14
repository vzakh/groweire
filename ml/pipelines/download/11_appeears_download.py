"""Poll AppEEARS tasks from 10_appeears_submit.py and download finished bundles.

  python scripts/11_appeears_download.py            # check once, download what's done
  python scripts/11_appeears_download.py --wait     # keep polling every 10 min until all done
Files land in data/raw/appeears/<task_name>/ (re-runs skip files already downloaded).
"""
from __future__ import annotations

import argparse
import json
import time

import requests

from common import RAW, ensure, load_env, log

API = "https://appeears.earthdatacloud.nasa.gov/api"
TASKS_FILE = RAW / "appeears" / "tasks.json"


def login() -> str:
    import os
    r = requests.post(f"{API}/login", timeout=60,
                      auth=(os.environ["EARTHDATA_USERNAME"], os.environ["EARTHDATA_PASSWORD"]))
    r.raise_for_status()
    return r.json()["token"]


def download_bundle(name: str, tid: str, headers: dict) -> None:
    out = ensure(RAW / "appeears" / name)
    bundle = requests.get(f"{API}/bundle/{tid}", headers=headers, timeout=120).json()
    for f in bundle.get("files", []):
        dest = out / f["file_name"].replace("/", "_")
        if dest.exists() and dest.stat().st_size == f.get("file_size", -1):
            continue
        log.info("  downloading %s (%.1f MB)", f["file_name"], f.get("file_size", 0) / 1e6)
        with requests.get(f"{API}/bundle/{tid}/{f['file_id']}", headers=headers, stream=True,
                          allow_redirects=True, timeout=600) as r:
            r.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)


def check_all(headers: dict) -> bool:
    tasks = json.loads(TASKS_FILE.read_text())
    all_done = True
    for name, tid in tasks.items():
        status = requests.get(f"{API}/task/{tid}", headers=headers, timeout=60).json().get("status")
        log.info("%-32s %s", name, status)
        if status == "done":
            marker = RAW / "appeears" / name / ".complete"
            if not marker.exists():
                download_bundle(name, tid, headers)
                marker.touch()
        elif status in ("error", "expired"):
            log.error("%s ended with status %s - resubmit it", name, status)
        else:
            all_done = False
    return all_done


def main() -> None:
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", action="store_true")
    ap.add_argument("--interval", type=int, default=600)
    args = ap.parse_args()
    if not TASKS_FILE.exists():
        raise SystemExit("no tasks.json - run 10_appeears_submit.py first")
    headers = {"Authorization": f"Bearer {login()}"}
    while True:
        if check_all(headers) or not args.wait:
            break
        log.info("not finished yet; sleeping %d s", args.interval)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
