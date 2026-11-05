"""Phase 3: assignment of non-centralities (A1, "Fase 3", decisions D21, D22, D1, D2)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .problem import Problem
from .scenario import Scenario


@dataclass
class Phase3Result:
    pointers: np.ndarray  # int64; -1 for centralities and unassigned units
    minutes: np.ndarray  # float64; time to the attracting centrality, NaN otherwise
    distant: np.ndarray  # bool
    unassigned: np.ndarray  # bool; non-centralities without any finite time


def phase3(p: Problem, scenario: Scenario, block: int = 1024) -> Phase3Result:
    if block < 1:
        raise ValueError(f"block must be >= 1, got {block}")
    n = p.n
    pointers = np.full(n, -1, dtype=np.int64)
    minutes = np.full(n, np.nan)
    cen = np.flatnonzero(p.is_centrality)
    non = np.flatnonzero(~p.is_centrality)
    if cen.size:
        # tie-break rank of every centrality: level, weight (desc), declared id order
        order = np.lexsort((p.id_rank[cen], -p.weight[cen], p.strength[cen]))
        tie = np.empty(cen.size, dtype=np.int64)
        tie[order] = np.arange(cen.size)
        for start in range(0, non.size, block):
            rows = non[start : start + block]
            t = p.times[np.ix_(rows, cen)].copy()
            t[np.isnan(t)] = np.inf
            best = t.min(axis=1)
            candidates = np.where(t == best[:, None], tie[None, :], cen.size)
            k = candidates.argmin(axis=1)
            ok = np.isfinite(best)
            pointers[rows[ok]] = cen[k[ok]]
            minutes[rows[ok]] = best[ok]
    unassigned = ~p.is_centrality & (pointers == -1)
    distant = np.nan_to_num(minutes, nan=-np.inf) > scenario.distant_minutes
    return Phase3Result(pointers, minutes, distant, unassigned)
