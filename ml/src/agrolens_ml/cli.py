"""Pipeline entry point: python -m agrolens_ml.cli <step> [--data data]

Steps: power-monthly, grid, labels, features (tasks 10-12). grid, labels, features, train, evaluate, export follow.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument(
        "step",
        choices=[
            "power-monthly",
            "grid",
            "labels",
            "features",
            "train",
            "risk-grid",
            "risk-counts",
        ],
    )
    ap.add_argument("--out", default="ml/artifacts/stress_lgbm_v1", help="train: bundle directory")
    ap.add_argument("--splits", type=int, default=5, help="train: GroupKFold splits by year")
    ap.add_argument("--config", default="ml/config")
    ap.add_argument("--data", default="data", help="data root containing raw/ and processed/")
    args = ap.parse_args()
    data = Path(args.data)
    t0 = time.perf_counter()
    if args.step == "power-monthly":
        from agrolens_ml.features import power_nodes  # pylint: disable=import-outside-toplevel

        out = power_nodes.run(data / "processed", data / "raw")
    elif args.step == "grid":
        from agrolens_ml import grid  # pylint: disable=import-outside-toplevel

        cells = grid.build_grid(Path(args.config), data / "raw", data / "processed")
        out = data / "processed" / "grid_cells.parquet"
        kept = grid.write_grid(cells, out)
        grid.preview_png(cells, kept, Path("ml/artifacts/_scratch/grid.png"))
        print(
            f"retained {len(kept)} / {len(cells)} cells; null elev_m in retained: "
            f"{int(kept['elev_m'].isna().sum())}"
        )
    elif args.step in ("labels", "features"):
        from agrolens_ml import pipeline  # pylint: disable=import-outside-toplevel

        out = (pipeline.run_labels if args.step == "labels" else pipeline.run_features)(data)
    elif args.step == "train":
        from agrolens_ml.model.train import run_train  # pylint: disable=import-outside-toplevel

        out = run_train(data, Path(args.out), args.splits)["out"]
    elif args.step == "risk-grid":
        from agrolens_ml.risk_grid import write_risk_grid  # pylint: disable=import-outside-toplevel

        out = write_risk_grid(data / "processed", Path(args.out))
    elif args.step == "risk-counts":
        from agrolens_ml.risk_counts import (
            write_risk_counts,
        )  # pylint: disable=import-outside-toplevel

        out = write_risk_counts(data / "processed")
    print(f"{args.step}: wrote {out} in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
