"""Download Met Eireann daily station data (ground truth for validating POWER and ET0).

Licence: CC BY 4.0. Attribution required: "Copyright Met Eireann. Source www.met.ie.
Licence CC BY 4.0. Data modified (aggregated) from the original."

The station list below holds synoptic/agro stations spread across Ireland. IDs that 404 are
skipped and logged. Check StationDetails.csv (downloaded too) to add more.
Outputs: data/raw/met_eireann/dly<ID>.csv  (raw, with the Met Eireann header block)
No login needed.
"""
from __future__ import annotations

import requests

from common import RAW, ensure, log, retry

BASE = "https://cli.fusio.net/cli/climate_data/webdata"
STATIONS = {  # id: name (verify against StationDetails.csv)
    375: "Oak Park (Carlow)", 575: "Moore Park (Cork)", 675: "Ballyhaise (Cavan)",
    875: "Mullingar", 1475: "Gurteen (Tipperary)", 1775: "Johnstown Castle (Wexford)",
    1875: "Athenry (Galway)", 1375: "Dunsany (Meath)", 532: "Dublin Airport",
    518: "Shannon Airport", 3904: "Cork Airport", 2275: "Valentia", 2175: "Claremorris",
    1575: "Malin Head", 3723: "Casement",
}


def download(url: str, path) -> bool:
    def _get():
        r = requests.get(url, timeout=120)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.content
    content = retry(_get)
    if content is None:
        return False
    path.write_bytes(content)
    return True


def main() -> None:
    out = ensure(RAW / "met_eireann")
    download(f"{BASE}/StationDetails.csv", out / "StationDetails.csv")
    ok = 0
    for sid, name in STATIONS.items():
        path = out / f"dly{sid}.csv"
        if path.exists():
            ok += 1
            continue
        if download(f"{BASE}/dly{sid}.csv", path):
            ok += 1
            log.info("got %s (%s)", path.name, name)
        else:
            log.warning("no daily file for %s (%s) - check StationDetails.csv", sid, name)
    log.info("%d/%d stations downloaded to %s", ok, len(STATIONS), out)


if __name__ == "__main__":
    main()
