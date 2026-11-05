"""Helpers to write hand-built test cases."""

from __future__ import annotations

import pandas as pd

from maps_sll.engine import run
from maps_sll.inputs import Inputs
from maps_sll.problem import Problem, build_problem
from maps_sll.scenario import Scenario

MAPS = {
    "name": "test-maps",
    "reference_year": 2025,
    "levels": [1, 2, 3, 4, 5, 6],
    "phase2_pairs": {2: [1], 3: [1], 4: [1, 2], 5: [1, 2, 3], 6: [1, 2, 3]},
    "phase4_levels": [4, 5, 6],
    "contiguity": {"min_shared_share": 0.0309, "max_minutes": 20},
    "distant_minutes": 60,
    "id_order": "lexicographic",
    "max_chain_length": 16,
}


def scenario(**overrides) -> Scenario:
    """MAPS parametrisation (decisions D5, D13, D14, D15), with overrides."""
    return Scenario.model_validate({**MAPS, **overrides})


def make_inputs(units, contig=(), times=None, description="test matrix") -> Inputs:
    """units: (id, level|None, weight[, name]); contig: (a, b[, share_ab[, share_ba]]);
    times: {(a, b): minutes}, mirrored to (b, a) unless given; diagonal is 0.
    Shares are written as shared_length with perimeter 1.0, so thresholds compare exactly."""
    u = pd.DataFrame(
        [
            {"id": x[0], "name": x[3] if len(x) > 3 else x[0], "level": x[1], "weight": float(x[2])}
            for x in units
        ]
    )
    u["level"] = u["level"].astype("Int64")
    rows = []
    for e in contig:
        a, b = e[0], e[1]
        sab = e[2] if len(e) > 2 else 0.5
        sba = e[3] if len(e) > 3 else sab
        rows.append({"origin": a, "neighbour": b, "shared_length": sab, "origin_perimeter": 1.0})
        rows.append({"origin": b, "neighbour": a, "shared_length": sba, "origin_perimeter": 1.0})
    c = pd.DataFrame(rows, columns=["origin", "neighbour", "shared_length", "origin_perimeter"])
    t = dict(times or {})
    for (a, b), m in list(t.items()):
        t.setdefault((b, a), m)
    for x in units:
        t[(x[0], x[0])] = 0.0
    tr = pd.DataFrame(
        [{"origin": a, "destination": b, "minutes": float(m)} for (a, b), m in t.items()],
        columns=["origin", "destination", "minutes"],
    )
    return Inputs(units=u, contiguity=c, times=tr, times_description=description)


def problem(units, contig=(), times=None, sc=None) -> Problem:
    return build_problem(make_inputs(units, contig, times), sc or scenario())


def ix(p: Problem, uid: str) -> int:
    return p.index[uid]


def run_case(units, contig=(), times=None, sc=None):
    return run(sc or scenario(), make_inputs(units, contig, times))


def step(r, uid: str):
    j = r.ptr4[ix(r.problem, uid)]
    return None if j == -1 else r.problem.ids[j]


def system_of(r, uid: str) -> str:
    return r.problem.ids[r.roots[ix(r.problem, uid)]]
