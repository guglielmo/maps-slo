"""Choice of the calibration configuration (D3.3.2 draft, "La funzione di costo").

    python maps/choose.py output/calibration-2025-d16-cost/calibration.parquet
    python maps/choose.py ... --fixed-border --fixed-pairs     # only the time threshold varies
    python maps/choose.py ... --cost errq_all                  # assignment error as the cost

The cost term defaults to K1q; with --cost any column of calibration.parquet or of
assignment.parquet (maps/assignment.py, read from the same directory when present) can be used,
for instance errq_all, the squared assignment error summed over the services.

Energy of a configuration, to be minimised among the admissible ones:

    E(lambda) = K1q - lambda * K5

  K1q    convex cost: population-weighted mean of the squared extra minutes to the main centre
  K5     benefit: population share (percentage points) in systems headed by a level 1-3 centre
  lambda price: how much K1q one accepts for one point of K5

Admissible: K3 <= 1% (population beyond 30 minutes), K4 <= 60 minutes (farthest municipality,
distant ones excluded), V5 <= V5 of the agreed configuration (no more non-contiguous systems).

lambda* is the smallest price for which the minimiser of E produces as many of the GSSI manual
unions (K7) as any admissible configuration can: the experts' corrections are read as revealed
preferences. The script prints the minimiser for every range of lambda and the choice at lambda*.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

AGREED = {"min_shared_share": 0.0309, "max_minutes": 20.0, "pairs": "current"}


def admissible(x: pd.DataFrame, ref: pd.Series) -> pd.Series:
    return ((x.K3_pop_share_over_30 <= 0.01) & (x.K4_max_minutes_to_centre <= 60)
            & (x.V5_non_contiguous_systems <= ref.V5_non_contiguous_systems))


def minimisers(a: pd.DataFrame, lams: np.ndarray, cost: str = "K1q_mean_squared_extra") -> pd.DataFrame:
    rows = [(lam, (a[cost] - lam * a.K5pp).idxmin()) for lam in lams]
    w = pd.DataFrame(rows, columns=["lam", "k"])
    return w.groupby("k", sort=False).lam.agg(["min", "max"]).rename(
        columns={"min": "lambda_from", "max": "lambda_to"})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("calibration", type=Path)
    ap.add_argument("--fixed-border", action="store_true", help="keep the agreed 3.09%%")
    ap.add_argument("--fixed-pairs", action="store_true", help="keep the agreed pairs table")
    ap.add_argument("--lambda-max", type=float, default=20.0)
    ap.add_argument("--lambda-step", type=float, default=0.05)
    ap.add_argument("--cost", default="K1q_mean_squared_extra",
                    help="cost column (calibration.parquet or assignment.parquet)")
    a = ap.parse_args()
    x = pd.read_parquet(a.calibration)
    extra = a.calibration.parent / "assignment.parquet"
    if extra.exists():
        y = pd.read_parquet(extra)
        if len(y) != len(x):
            raise SystemExit(f"{extra} has {len(y)} rows, {a.calibration} has {len(x)}")
        x = pd.concat([x, y], axis=1)
    if a.cost not in x:
        raise SystemExit(f"unknown cost column {a.cost}")
    x["K5pp"] = x.K5_pop_share_service_centre * 100
    agreed = x[(x.pairs == AGREED["pairs"]) & np.isclose(x.min_shared_share, AGREED["min_shared_share"])
               & (x.max_minutes == AGREED["max_minutes"])]
    if agreed.empty:
        raise SystemExit("the grid does not contain the agreed configuration (3.09%, 20 minutes, current)")
    ref = agreed.iloc[0]
    if a.fixed_border:
        x = x[np.isclose(x.min_shared_share, AGREED["min_shared_share"])]
    if a.fixed_pairs:
        x = x[x.pairs == AGREED["pairs"]]
    adm = x[admissible(x, ref)]
    lams = np.round(np.arange(0, a.lambda_max + 1e-9, a.lambda_step), 6)
    w = minimisers(adm, lams, a.cost)
    cols = ["pairs", "min_shared_share", "max_minutes", "V2_n_systems", "K1_access_cost",
            "K1q_mean_squared_extra", *([a.cost] if a.cost != "K1q_mean_squared_extra" else []), "K5pp", "K3_pop_share_over_30", "V5_non_contiguous_systems",
            "K7_corrections_produced", "stability_max_changed_share"]
    table = w.join(adm[cols])
    pd.set_option("display.width", 250)
    print(f"{len(adm)} admissible configurations of {len(x)}")
    print(table.round(3).to_string())
    k7max = int(table.K7_corrections_produced.max())
    star = table[table.K7_corrections_produced == k7max].sort_values("lambda_from").iloc[0]
    print(f"\nlambda* = {star.lambda_from} (smallest price giving {k7max} GSSI unions)")
    print(star[cols].to_string())


if __name__ == "__main__":
    main()
