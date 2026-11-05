"""Execution of phases 2-4 and label resolution."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import numpy as np

from .inputs import Inputs
from .labels import resolve
from .phase2 import phase2
from .phase3 import phase3
from .phase4 import Phase4Result, phase4
from .problem import Problem, build_problem
from .scenario import Scenario


@dataclass
class Result:
    scenario: Scenario
    inputs: Inputs
    problem: Problem
    ptr2: np.ndarray
    ptr3: np.ndarray
    ptr4: np.ndarray
    minutes: np.ndarray  # time to the direct step
    distant: np.ndarray
    unassigned: np.ndarray
    # Phase that produced the unit's own direct step: attracted units keep 3 even if their
    # centrality changes system in phase 4 (the full path is in `chain`).
    phase: np.ndarray  # 2, 3 or 4
    rule: np.ndarray  # object
    roots: np.ndarray
    paths: list[list[int]]
    phase4: Phase4Result
    timings: dict[str, float]


def run(scenario: Scenario, inputs: Inputs) -> Result:
    timings: dict[str, float] = {}

    def timed(name, fn, *args):
        t = perf_counter()
        out = fn(*args)
        timings[name] = perf_counter() - t
        return out

    p = timed("build_problem", build_problem, inputs, scenario)
    ptr2 = timed("phase2", phase2, p, scenario)
    r3 = timed("phase3", phase3, p, scenario)
    ptr3 = np.where(p.is_centrality, ptr2, r3.pointers)
    r4 = timed("phase4", phase4, p, scenario, ptr3)
    roots, paths = timed("resolve", resolve, r4.pointers, scenario.max_chain_length, p.ids)
    timings["core"] = sum(timings[k] for k in ("phase2", "phase3", "phase4", "resolve"))

    ptr4 = r4.pointers
    minutes = r3.minutes.copy()
    merged = np.flatnonzero(p.is_centrality & (ptr4 >= 0))
    minutes[merged] = p.times[merged, ptr4[merged]]
    for c, rr in r4.rules.items():
        if rr == "P4-CLAIMED":  # the step was set by the claimant: time claimant -> claimed
            minutes[c] = p.times[ptr4[c], c]

    phase = np.full(p.n, 3, dtype=np.int64)
    rule = np.full(p.n, "P3-NEAREST", dtype=object)
    rule[r3.unassigned] = "UNASSIGNED"
    for c in np.flatnonzero(p.is_centrality):
        phase[c] = 2
        rule[c] = "P2-MERGE" if ptr2[c] >= 0 else "HEAD"
    for c, rr in r4.rules.items():
        phase[c] = 4
        rule[c] = rr

    return Result(
        scenario=scenario, inputs=inputs, problem=p, ptr2=ptr2, ptr3=ptr3, ptr4=ptr4,
        minutes=minutes, distant=r3.distant, unassigned=r3.unassigned, phase=phase, rule=rule,
        roots=roots, paths=paths, phase4=r4, timings=timings,
    )
