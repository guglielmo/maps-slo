"""Structural metrics V2-V5, V9, V10 (D3.2.1, "Misure strutturali")."""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .engine import Result

BINS = [0, 1, 5, 10, 20, 50, np.inf]
BIN_LABELS = ["1", "2-5", "6-10", "11-20", "21-50", "51+"]


def _quantiles(s: pd.Series) -> dict[str, float]:
    if s.empty:
        return {}
    q = s.quantile([0, 0.25, 0.5, 0.75, 1])
    return {f"p{int(k * 100)}": float(v) for k, v in q.items()}


def compute_metrics(r: Result, units: pd.DataFrame, systems: pd.DataFrame) -> dict:
    p = r.problem
    hist = (
        pd.cut(systems.n_units, bins=BINS, labels=BIN_LABELS)
        .value_counts()
        .reindex(BIN_LABELS, fill_value=0)
    )
    single = systems[systems.n_units == 1]
    weight = {uid: float(p.weight[p.index[uid]]) for uid in units.id}
    total = sum(weight.values())
    within = sum(weight[uid] for uid in units.id[~units.distant])
    return {
        "V2": {
            "n_systems": len(systems),
            "units_per_system": _quantiles(systems.n_units),
            "weight_per_system": _quantiles(systems.total_weight),
            "units_per_system_histogram": {k: int(v) for k, v in hist.items()},
        },
        "V3": {
            "n_single_unit_systems": len(single),
            "by_centre_level": {
                str(k): int(v)
                for k, v in single.main_centre_level.value_counts().sort_index().items()
            },
        },
        "V4": {
            "distant_minutes": float(r.scenario.distant_minutes),
            "weight_share_within": within / total if total else None,
            "n_distant": int(units.distant.sum()),
        },
        "V5": _non_contiguous(r, units),
        "V9": {
            "max_merged_centres_phase2": _max(systems.merged_centres_phase2),
            "max_merged_centres_phase4": _max(systems.merged_centres_phase4),
            "n_systems_with_merged_centres": int(
                ((systems.merged_centres_phase2 + systems.merged_centres_phase4) > 0).sum()
            ),
            "max_chain_length": _max(systems.max_chain_length),
        },
        "V10": {
            "n_centre_changes": len(r.phase4.changed_heads),
            "cases": [
                {"previous_centre_id": p.ids[h], "new_centre_id": p.ids[r.roots[h]],
                 "direct_claimant_id": p.ids[s]}
                for h, s in r.phase4.changed_heads
            ],
        },
    }


def _non_contiguous(r: Result, units: pd.DataFrame) -> dict:
    """V5: systems whose units are not all connected to the main centre by contiguity."""
    p = r.problem
    adjacency: dict[int, set[int]] = defaultdict(set)
    for i, nbrs in enumerate(p.neighbours):
        for j, _ in nbrs:
            adjacency[i].add(j)
            adjacency[j].add(i)
    cases = []
    for sid, g in units.groupby("system_id", sort=False):
        members = {p.index[x] for x in g.id}
        start = p.index[sid]
        seen, stack = {start}, [start]
        while stack:
            k = stack.pop()
            for j in adjacency[k]:
                if j in members and j not in seen:
                    seen.add(j)
                    stack.append(j)
        if len(seen) < len(members):
            isolated = sorted(members - seen, key=lambda k: p.id_rank[k])
            cases.append({"system_id": sid, "isolated_ids": [p.ids[k] for k in isolated]})
    cases.sort(key=lambda c: p.id_rank[p.index[c["system_id"]]])
    return {"n_non_contiguous_systems": len(cases), "cases": cases}


def _max(s: pd.Series) -> int:
    return int(s.max()) if len(s) else 0
