"""Calibration grid of the aggregation (D3.3.2, calibration method draft).

    python maps/calibrate.py maps/calibration/grid-2025.yaml --out output/calibration-2025

Runs the aggregation for every combination of the grid and computes the measures of the
method draft for each one. The problem (travel-time matrix, contiguity, levels) is built
once: the grid parameters are read only when phases 2 and 4 test relevant contiguity and
allowed pairs. Phase 3 does not depend on them (it reads only the travel times and the
levels), so it runs once too. The engine is not modified: this script calls its phases in
the same order as `maps_slo.engine.run`.

Outputs in --out:
- calibration.csv / .parquet: one row per combination, one column per measure;
- roots.npz: the system (root) of every unit for every combination, to compare partitions;
- manifest.json: base scenario, grid, input fingerprints, git commit, timings.

The admissibility thresholds and the choice criterion are applied afterwards, on the table
(paragraph "Procedura"): they are not decided here.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
import yaml

from maps_slo.inputs import Inputs
from maps_slo.labels import resolve
from maps_slo.manifest import _git_commit
from maps_slo.phase2 import phase2
from maps_slo.phase3 import phase3
from maps_slo.phase4 import phase4
from maps_slo.problem import Problem, build_problem
from maps_slo.scenario import Scenario


def _values(spec) -> list[float]:
    if isinstance(spec, list):
        return [float(v) for v in spec]
    n = round((spec["to"] - spec["from"]) / spec["step"])
    return [round(spec["from"] + k * spec["step"], 10) for k in range(n + 1)]


def _components_outside(p: Problem, members: np.ndarray) -> int:
    """Units of a system not reachable from its largest contiguous block (V5)."""
    inside = set(members.tolist())
    seen: set[int] = set()
    sizes = []
    for start in members.tolist():
        if start in seen:
            continue
        q, size = deque([start]), 0
        seen.add(start)
        while q:
            a = q.popleft()
            size += 1
            for b, _ in p.neighbours[a]:
                if b in inside and b not in seen:
                    seen.add(b)
                    q.append(b)
        sizes.append(size)
    return len(members) - max(sizes)


def measures(p: Problem, roots: np.ndarray, paths: list[list[int]], assigned: np.ndarray,
             r3_minutes: np.ndarray, distant: np.ndarray, joins: list[tuple[int, int]],
             far: list[float], service_levels: set[int], small: float) -> dict:
    """Measures of the calibration method draft for one partition."""
    idx = np.flatnonzero(assigned)
    w = p.weight[idx]
    to_root = np.where(roots[idx] == idx, 0.0, p.times[idx, roots[idx]])
    if np.isnan(to_root).any():
        raise ValueError("an assigned unit has no time to the main centre of its system")
    # time to the attracting centrality: phase-3 minutes for non-centralities, 0 for centralities
    to_step = np.where(p.is_centrality[idx], 0.0, r3_minutes[idx])
    a = float((w * to_root).sum() / w.sum())
    a0 = float((w * to_step).sum() / w.sum())
    out = {
        "K1_access_cost": a - a0,
        "mean_minutes_to_centre": a,
        "mean_minutes_to_step": a0,
        "K2_mean_minutes_per_unit": float(to_root.mean()),
    }
    for f in far:
        out[f"K3_pop_share_over_{int(f)}"] = float(w[to_root > f].sum() / w.sum())
    keep = ~distant[idx]
    out["K4_max_minutes_to_centre"] = float(to_root[keep].max())
    out["K4_max_minutes_incl_distant"] = float(to_root.max())

    sys_ids, inv = np.unique(roots[idx], return_inverse=True)
    sys_w = np.bincount(inv, weights=w)
    sys_n = np.bincount(inv)
    head_level = p.level[sys_ids]
    out["V2_n_systems"] = len(sys_ids)
    out["V2_median_units"] = float(np.median(sys_n))
    out["K5_pop_share_service_centre"] = float(
        sys_w[np.isin(head_level, list(service_levels))].sum() / sys_w.sum())
    out["K6_small_systems"] = int((sys_w < small).sum())
    out["V3_single_unit_systems"] = int((sys_n == 1).sum())
    order = np.argsort(inv, kind="stable")
    bounds = np.cumsum(sys_n)[:-1]
    out["V5_non_contiguous_systems"] = int(sum(
        _components_outside(p, idx[g]) > 0 for g in np.split(order, bounds) if len(g) > 1))
    out["V9_max_chain_length"] = int(max(
        (len(paths[i]) - 1 for i in np.flatnonzero(p.is_centrality & assigned)), default=0))
    out["K7_corrections_produced"] = int(sum(roots[x] == roots[y] for x, y in joins))
    out["K7_corrections_total"] = len(joins)
    return out


def run_point(p: Problem, sc: Scenario, r3):
    """Phases 2 and 4 and label resolution for one scenario, as in `maps_slo.engine.run`."""
    ptr2 = phase2(p, sc)
    ptr3 = np.where(p.is_centrality, ptr2, r3.pointers)
    r4 = phase4(p, sc, ptr3)
    roots, paths = resolve(r4.pointers, sc.max_chain_length, p.ids)
    return ptr2, r4, roots, paths


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("grid", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    grid = yaml.safe_load(a.grid.read_text(encoding="utf-8"))
    base_path = (a.grid.parent / grid["base_scenario"]).resolve()
    base = Scenario.model_validate(yaml.safe_load(base_path.read_text(encoding="utf-8")))
    a.out.mkdir(parents=True, exist_ok=True)
    started = datetime.now(UTC).isoformat(timespec="seconds")

    t0 = perf_counter()
    inputs = Inputs.from_scenario(base, base_path.parent)
    p = build_problem(inputs, base)
    t_build = perf_counter() - t0
    r3 = phase3(p, base)
    assigned = ~r3.unassigned

    joins = []
    if grid.get("corrections"):
        corr = pd.read_csv(a.grid.parent / grid["corrections"], dtype=str, keep_default_na=False)
        for c in corr[corr.kind == "join"].itertuples(index=False):
            if c.unit_id not in p.index or c.target_id not in p.index:
                raise SystemExit(f"correction {c.id}: unit not in the problem")
            joins.append((p.index[c.unit_id], p.index[c.target_id]))

    shares = _values(grid["min_shared_share"])
    minutes = _values(grid["max_minutes"])
    variants = grid["phase2_pairs"]
    far = [float(v) for v in grid.get("far_minutes", [30])]
    service = {int(v) for v in grid.get("service_levels", [1, 2, 3])}
    small = float(grid.get("small_system_weight", 10000))

    rows, all_roots = [], []
    t1 = perf_counter()
    for (vname, pairs), share, mins in itertools.product(variants.items(), shares, minutes):
        sc = base.model_copy(update={
            "phase2_pairs": {int(k): list(v) for k, v in pairs.items()},
            "contiguity": base.contiguity.model_copy(
                update={"min_shared_share": share, "max_minutes": mins}),
        })
        Scenario.model_validate(sc.model_dump())  # same checks as a scenario file
        ptr2, r4, roots, paths = run_point(p, sc, r3)
        row = {"pairs": vname, "min_shared_share": share, "max_minutes": mins,
               "n_phase2_merges": int((ptr2 >= 0).sum()),
               "n_phase4_steps": len(r4.rules)}
        row.update(measures(p, roots, paths, assigned, r3.minutes, r3.distant, joins,
                            far, service, small))
        row["partition"] = hashlib.sha256(roots[assigned].tobytes()).hexdigest()[:12]
        rows.append(row)
        all_roots.append(roots.astype(np.int32))
    t_grid = perf_counter() - t1

    df = pd.DataFrame(rows)
    stack = np.stack(all_roots)
    df["stability_max_changed_share"] = _stability(df, stack, assigned, shares, minutes)
    df["pareto_K1_vs_V2"] = _pareto(df["K1_access_cost"].to_numpy(), df["V2_n_systems"].to_numpy())
    df.to_parquet(a.out / "calibration.parquet", index=False)
    df.to_csv(a.out / "calibration.csv", index=False)
    np.savez_compressed(a.out / "roots.npz", roots=stack, ids=p.ids.astype(str))
    manifest = {
        "grid_file": str(a.grid), "grid": grid, "base_scenario": str(base_path),
        "inputs": inputs.fingerprints(), "git_commit": _git_commit(),
        "n_combinations": len(df), "n_distinct_partitions": int(df.partition.nunique()),
        "timings_seconds": {"build_problem": t_build, "grid": t_grid},
        "started_at": started, "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "python": sys.version.split()[0],
    }
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                         encoding="utf-8")
    print(f"{len(df)} combinations, {df.partition.nunique()} distinct partitions; "
          f"build {t_build:.0f}s, grid {t_grid:.0f}s")


def _stability(df: pd.DataFrame, stack: np.ndarray, assigned: np.ndarray,
               shares: list[float], minutes: list[float]) -> list[float]:
    """For every combination, the largest share of units that change system when one grid
    parameter moves by one step (same pairs table). 0 = the partition does not change."""
    pos = {(r.pairs, r.min_shared_share, r.max_minutes): k for k, r in enumerate(df.itertuples())}
    out = []
    for k, r in enumerate(df.itertuples()):
        i, j = shares.index(r.min_shared_share), minutes.index(r.max_minutes)
        worst = 0.0
        for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            if 0 <= i + di < len(shares) and 0 <= j + dj < len(minutes):
                n = pos[(r.pairs, shares[i + di], minutes[j + dj])]
                worst = max(worst, float((stack[k][assigned] != stack[n][assigned]).mean()))
        out.append(worst)
    return out


def _pareto(cost: np.ndarray, n_systems: np.ndarray) -> np.ndarray:
    """True when no other combination has both lower-or-equal cost and fewer-or-equal
    systems, with at least one strictly lower."""
    keep = np.ones(len(cost), dtype=bool)
    for k in range(len(cost)):
        dominated = (cost <= cost[k]) & (n_systems <= n_systems[k]) & (
            (cost < cost[k]) | (n_systems < n_systems[k]))
        keep[k] = not dominated.any()
    return keep


if __name__ == "__main__":
    main()
