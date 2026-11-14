"""Pipeline entry point: python -m agrolens_ml.cli <step> [--data data]

Steps so far: power-monthly (task 12). grid, labels, features, train, evaluate, export follow.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("step", choices=["power-monthly"])
    ap.add_argument("--data", default="data", help="data root containing raw/ and processed/")
    args = ap.parse_args()
    data = Path(args.data)
    t0 = time.perf_counter()
    if args.step == "power-monthly":
        from agrolens_ml.features import power_nodes  # pylint: disable=import-outside-toplevel

        out = power_nodes.run(data / "processed", data / "raw")
    print(f"{args.step}: wrote {out} in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
