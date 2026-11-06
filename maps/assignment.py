"""Assignment error of SLO tessellations (D3.3.2 draft): does a municipality's own system contain
the provider of a service that it reaches fastest?

    python maps/assignment.py output/calibration-2025-d16-cost \
        --services maps/data/services-2025.csv --times maps/data/times-2025.parquet \
        --weights maps/data/units-2025-d16.parquet

For every municipality c and service k (services sit at municipality level, one presence flag
per municipality; times are centroid to centroid, self time 0):

  t_all(c, k) = minutes to the nearest municipality offering k, anywhere
  t_in(c, k)  = minutes to the nearest municipality offering k inside c's system
  error       = t_in - t_all, defined only when c's system offers k ("covered")

Per tessellation and service the script writes, all as shares or means over the whole population
(municipalities without travel times are left out):

  cov_<k>   population share whose system offers k (a benefit, grows with aggregation)
  mis_<k>   population share covered but not by the fastest provider (error > 0)
  mis5_<k>  same, error > 5 minutes
  err_<k>   mean error in minutes per inhabitant (uncovered count 0)
  errq_<k>  mean squared error per inhabitant (convex, the cost term candidate)

and errq_all, the sum of errq over the services. The output assignment.parquet has one row per
combination, in the order of calibration.parquet and roots.npz.

Only pairs of municipalities in the same system are looked at, so one tessellation costs the
sum of the squared system sizes, not municipalities x providers.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

SERVICES = {
    "health": "n_health > 0",
    "dea": "n_dea > 0",
    "school": "n_secondary_schools > 0",
    "station_major": "station_category IN ('gold', 'platinum')",
    "station": "station_category IS NOT NULL",
}


def same_system_pairs(roots: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """All ordered pairs (i, j), i and j in the same system, i == j included."""
    order = np.argsort(roots, kind="stable")
    _, start, size = np.unique(roots[order], return_index=True, return_counts=True)
    reps = np.repeat(size, size)                       # for each member, its system size
    first = np.repeat(start, size)                     # system start, per member
    i = np.repeat(order, reps)
    offs = np.arange(reps.sum()) - np.repeat(np.cumsum(reps) - reps, reps)
    j = order[np.repeat(first, reps) + offs]
    return i, j


def assignment(roots: np.ndarray, weight: np.ndarray, times: np.ndarray,
               is_prov: np.ndarray, t_all: np.ndarray, pairs=None) -> dict[str, float]:
    """roots: system of each unit; weight: population (0 for units to leave out);
    times: minutes unit x unit; is_prov: whether each unit offers the service;
    t_all: minutes from each unit to its nearest provider anywhere."""
    i, j = pairs if pairs is not None else same_system_pairs(roots)
    k = is_prov[j]
    t_in = np.full(len(roots), np.inf)
    np.minimum.at(t_in, i[k], times[i[k], j[k]])
    covered = np.isfinite(t_in) & np.isfinite(t_all)
    err = np.zeros(len(roots))
    err[covered] = t_in[covered] - t_all[covered]
    tot = weight.sum()
    return {
        "cov": float(weight[covered].sum() / tot),
        "mis": float(weight[err > 0].sum() / tot),
        "mis5": float(weight[err > 5].sum() / tot),
        "err": float((weight * err).sum() / tot),
        "errq": float((weight * err ** 2).sum() / tot),
    }


def load(services: Path, times: Path, weights: Path, ids: np.ndarray):
    """Dense minutes (inf where missing), weights aligned to ids (0 without times), and the
    provider flags per service."""
    con = duckdb.connect()
    con.execute("CREATE TABLE ids AS SELECT * FROM (SELECT unnest($1) id, generate_subscripts($1, 1) - 1 i)",
                [ids.tolist()])
    t = con.execute(f"""SELECT a.i oi, b.i di, minutes FROM read_parquet('{times}') t
                        JOIN ids a ON a.id = t.origin JOIN ids b ON b.id = t.destination""").fetchnumpy()
    m = np.full((len(ids), len(ids)), np.inf, dtype=np.float32)
    m[t["oi"], t["di"]] = t["minutes"]
    np.fill_diagonal(m, 0)
    has_times = np.isfinite(m).sum(axis=1) > 1
    w = con.execute(f"""SELECT i, weight FROM read_parquet('{weights}') JOIN ids USING (id)""").fetchnumpy()
    weight = np.zeros(len(ids))
    weight[w["i"]] = w["weight"]
    weight[~has_times] = 0.0
    con.execute(f"CREATE TABLE s AS SELECT * FROM read_csv('{services}', types={{'id': 'VARCHAR'}})")
    prov = {}
    for key, cond in SERVICES.items():
        p = con.execute(f"SELECT i FROM s JOIN ids USING (id) WHERE {cond}").fetchnumpy()["i"]
        flag = np.zeros(len(ids), bool)
        flag[p] = True
        prov[key] = (flag, m[:, flag].min(axis=1))
    return m, weight, prov


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("calibration_dir", type=Path)
    ap.add_argument("--services", type=Path, default=Path("maps/data/services-2025.csv"))
    ap.add_argument("--times", type=Path, default=Path("maps/data/times-2025.parquet"))
    ap.add_argument("--weights", type=Path, default=Path("maps/data/units-2025-d16.parquet"))
    a = ap.parse_args()
    z = np.load(a.calibration_dir / "roots.npz")
    stack, ids = z["roots"], z["ids"]
    times, weight, prov = load(a.services, a.times, a.weights, ids)
    rows = []
    for roots in stack:
        pairs = same_system_pairs(roots)
        row = {}
        for key, (flag, t_all) in prov.items():
            for name, v in assignment(roots, weight, times, flag, t_all, pairs).items():
                row[f"{name}_{key}"] = v
        row["errq_all"] = sum(row[f"errq_{k}"] for k in prov)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_parquet(a.calibration_dir / "assignment.parquet", index=False)
    print(f"{len(df)} combinations -> {a.calibration_dir / 'assignment.parquet'}")


if __name__ == "__main__":
    main()
