"""Phase 1 with the MAPS rules on the 1,259 GSSI centralities, compared with GSSI levels.

Approximation: GSSI has no count of upper-secondary schools, only the number of school types
(n_school_types), used here as n_secondary_schools. Differences are expected where the GSSI
definitions (PNRR Mission 6, SNAI index) differ from decision D16.

    python maps/levels_gssi.py maps/data/levels-gssi.parquet maps/levels/maps-rules.yaml out/
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from maps_sll.levels import assign_levels, load_rules


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("levels", type=Path)
    ap.add_argument("rules", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    g = pd.read_parquet(a.levels)
    attrs = g.rename(columns={"n_school_types": "n_secondary_schools"})
    ours = assign_levels(attrs, load_rules(a.rules)).rename(columns={"level": "level_ours"})
    cmp = g[["id", "name", "level", "gssi_tier", "population", "n_health", "n_dea", "pnrr_m6",
             "n_school_types", "snai_school_index", "station_category"]].merge(ours, on="id")
    cmp = cmp.rename(columns={"level": "level_gssi"})
    a.out.mkdir(parents=True, exist_ok=True)
    cmp.to_csv(a.out / "levels-gssi-comparison.csv", index=False)
    table = pd.crosstab(cmp.level_gssi, cmp.level_ours.astype("string").fillna("none"))
    table.to_csv(a.out / "levels-gssi-crosstab.csv")
    same = int((cmp.level_gssi == cmp.level_ours).fillna(False).sum())
    print(f"same level: {same}/{len(cmp)}")
    print(table)


if __name__ == "__main__":
    main()
