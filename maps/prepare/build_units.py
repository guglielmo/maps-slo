"""Units table for the national run: 2025 population of every municipality + GSSI levels.

    python maps/prepare/build_units.py maps/data/population-2025.csv \
        maps/data/levels-gssi.parquet maps/data/units-2025.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def build_units(population: Path, levels: Path) -> pd.DataFrame:
    pop = pd.read_csv(population, dtype={"id": str, "name": str}, keep_default_na=False)
    pop["id"] = pop["id"].str.zfill(6)
    lv = pd.read_parquet(levels, columns=["id", "level"])
    absent = sorted(set(lv.id) - set(pop.id))
    if absent:
        raise SystemExit(f"GSSI centralities absent from the 2025 population: {absent}")
    units = pop.merge(lv, on="id", how="left").rename(columns={"population": "weight"})
    units["level"] = units["level"].astype("Int64")
    return units[["id", "name", "level", "weight"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("population", type=Path)
    ap.add_argument("levels", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    units = build_units(a.population, a.levels)
    units.to_parquet(a.out, index=False)
    print(len(units), "units,", int(units.level.notna().sum()), "centralities")


if __name__ == "__main__":
    main()
