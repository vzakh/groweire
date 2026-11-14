"""Download the GeoNames gazetteer for the island of Ireland (fallback place search, brief D20).

Licence: CC BY 4.0. Attribution: "GeoNames (www.geonames.org), CC BY 4.0".
Source dumps: https://download.geonames.org/export/dump/IE.zip and GB.zip.
GB is filtered to the Northern Ireland bounding box; both are filtered to populated places
(feature class P) and localities/areas (L, A).
Outputs: data/raw/geonames/{IE.zip,GB.zip}, data/raw/geonames/gazetteer_ireland.tsv
No login needed. Primary search in the app is the Nominatim proxy; this is the offline fallback.
"""
from __future__ import annotations

import csv
import io
import zipfile

import requests

from common import RAW, ensure, log, retry

BASE = "https://download.geonames.org/export/dump"
BBOX = (-10.7, 51.3, -5.4, 55.5)  # lon_min, lat_min, lon_max, lat_max (island of Ireland)
KEEP_CLASSES = {"P", "L", "A"}
# GeoNames main-table columns (see readme.txt in the dump folder)
COLS = ["geonameid", "name", "asciiname", "alternatenames", "latitude", "longitude",
        "feature_class", "feature_code", "country_code", "cc2", "admin1", "admin2",
        "admin3", "admin4", "population", "elevation", "dem", "timezone", "modified"]


def fetch(cc: str, out_dir) -> bytes:
    path = out_dir / f"{cc}.zip"
    if not path.exists():
        def _get():
            r = requests.get(f"{BASE}/{cc}.zip", timeout=300)
            r.raise_for_status()
            return r.content
        path.write_bytes(retry(_get))
        log.info(f"downloaded {path.name} ({path.stat().st_size/1e6:.1f} MB)")
    return path.read_bytes()


def rows(zbytes: bytes, cc: str):
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        with z.open(f"{cc}.txt") as fh:
            for line in io.TextIOWrapper(fh, encoding="utf-8"):
                parts = line.rstrip("\n").split("\t")
                if len(parts) != len(COLS):
                    continue
                r = dict(zip(COLS, parts))
                lon, lat = float(r["longitude"]), float(r["latitude"])
                if r["feature_class"] not in KEEP_CLASSES:
                    continue
                if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
                    continue
                yield r


def main() -> None:
    out_dir = ensure(RAW / "geonames")
    out = out_dir / "gazetteer_ireland.tsv"
    n = 0
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["place_id", "name", "ascii_name", "feature_class", "feature_code",
                    "country_code", "admin1", "admin2", "lon", "lat", "population"])
        for cc in ("IE", "GB"):
            for r in rows(fetch(cc, out_dir), cc):
                w.writerow([r["geonameid"], r["name"], r["asciiname"], r["feature_class"],
                            r["feature_code"], r["country_code"], r["admin1"], r["admin2"],
                            r["longitude"], r["latitude"], r["population"] or 0])
                n += 1
    log.info(f"wrote {out} with {n} places")


if __name__ == "__main__":
    main()
