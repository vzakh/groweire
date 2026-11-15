"""Print what has been downloaded so far (sizes, row counts, date ranges)."""
from __future__ import annotations

import pandas as pd

from common import PROCESSED, RAW


def main() -> None:
    print("== raw")
    for d in sorted(p for p in RAW.glob("*") if p.is_dir()):
        files = [f for f in d.rglob("*") if f.is_file()]
        size = sum(f.stat().st_size for f in files) / 1e6
        print(f"  {d.name:<14} {len(files):>5} files  {size:>9.1f} MB")
    print("== processed")
    for f in sorted(PROCESSED.glob("*")):
        line = f"  {f.name:<28} {f.stat().st_size / 1e6:>8.1f} MB"
        if f.suffix == ".parquet":
            df = pd.read_parquet(f)
            line += f"  rows={len(df)}"
            for col in ("date", "month"):
                if col in df:
                    line += f"  {col}: {df[col].min()} .. {df[col].max()}"
        print(line)


if __name__ == "__main__":
    main()
