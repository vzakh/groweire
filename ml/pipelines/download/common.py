"""Shared config and helpers for the AgroLens data downloads (pilot: island of Ireland)."""
from __future__ import annotations

import csv
import json
import logging
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
# Repo-root data/ (brief §12.1): scripts now live in ml/pipelines/download/.
DATA = ROOT.parent.parent / "data"
RAW = Path(os.environ.get("AGROLENS_RAW", DATA / "raw"))
PROCESSED = Path(os.environ.get("AGROLENS_PROCESSED", DATA / "processed"))

# Island of Ireland bounding box (lon_min, lat_min, lon_max, lat_max)
IE_BBOX = (-10.7, 51.3, -5.4, 55.5)

YEAR_START = int(os.environ.get("AGROLENS_YEAR_START", 2001))
YEAR_END = int(os.environ.get("AGROLENS_YEAR_END", 2025))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("agrolens")


def load_env() -> None:
    """Load KEY=VALUE pairs from ROOT/.env into os.environ (no external dependency)."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def read_grid(name: str = "grid_005deg.csv") -> list[dict]:
    with open(CONFIG / name, newline="") as fh:
        return [
            {"cell_id": r["cell_id"], "lon": float(r["lon"]), "lat": float(r["lat"])}
            for r in csv.DictReader(fh)
        ]


def ensure(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json(obj, path: Path) -> None:
    ensure(path.parent)
    path.write_text(json.dumps(obj, indent=2))


def retry(fn, tries: int = 4, base_sleep: float = 5.0):
    """Call fn() with exponential back-off. Re-raises the last error."""
    for attempt in range(1, tries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - we log and retry anything network-ish
            if attempt == tries:
                raise
            wait = base_sleep * 2 ** (attempt - 1)
            log.warning("attempt %d/%d failed (%s); retrying in %.0fs", attempt, tries, exc, wait)
            time.sleep(wait)
    return None
