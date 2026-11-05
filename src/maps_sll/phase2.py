"""Phase 2: merges between contiguous centralities (A1, "Fase 2")."""

from __future__ import annotations

import numpy as np

from .problem import Problem
from .scenario import Scenario


def phase2(p: Problem, scenario: Scenario) -> np.ndarray:
    """Direct step of every centrality toward the main centre it merges into, -1 if none.

    One pass reaches the fixpoint: the candidates of a centrality depend only on level,
    contiguity and times, which phase 2 never changes. Chains come from the resolution.
    """
    ptr = np.full(p.n, -1, dtype=np.int64)
    centrality = p.is_centrality
    for c in np.flatnonzero(centrality):
        allowed = set(scenario.phase2_pairs.get(int(p.level[c]), []))
        if not allowed:
            continue
        best, best_key = -1, None
        for j, share in p.neighbours[c]:
            if not centrality[j] or int(p.level[j]) not in allowed:
                continue
            if not p.is_relevant(c, j, share, scenario):
                continue
            key = (int(p.strength[j]), -float(p.weight[j]), int(p.id_rank[j]))
            if best_key is None or key < best_key:
                best, best_key = j, key
        ptr[c] = best
    return ptr
