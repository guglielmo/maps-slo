"""Calibration grid (D3.3.2 draft), maps/calibrate.py."""

import sys
from pathlib import Path

import numpy as np
import pytest
from builders import make_inputs, scenario

from maps_slo.engine import run
from maps_slo.phase3 import phase3
from maps_slo.problem import build_problem

sys.path.insert(0, str(Path(__file__).parents[1] / "maps"))
from calibrate import _pareto, measures, run_point

# M (level 1) and S (level 3) are contiguous; 18 minutes apart. u1 -> M, u2 -> S.
UNITS = [("M", 1, 1000), ("S", 3, 400), ("u1", None, 100), ("u2", None, 50)]
CONTIG = [("S", "M", 0.2), ("u1", "M"), ("u2", "S")]
TIMES = {("S", "M"): 18, ("u1", "M"): 5, ("u2", "S"): 4, ("u2", "M"): 22, ("u1", "S"): 23}


@pytest.mark.parametrize("share,minutes", [(0.0309, 20), (0.0309, 15), (0.3, 20)])
def test_grid_point_equals_a_full_engine_run(share, minutes):
    sc = scenario(contiguity={"min_shared_share": share, "max_minutes": minutes})
    inputs = make_inputs(UNITS, CONTIG, TIMES)
    p = build_problem(inputs, scenario())  # built once with other thresholds
    _, _, roots, _ = run_point(p, sc, phase3(p, sc))
    assert np.array_equal(roots, run(sc, inputs).roots)


def test_access_cost_of_a_merge():
    sc = scenario()
    p = build_problem(make_inputs(UNITS, CONTIG, TIMES), sc)
    r3 = phase3(p, sc)
    _, _, roots, paths = run_point(p, sc, r3)
    m = measures(p, roots, paths, ~r3.unassigned, r3.minutes, r3.distant, [], [20], {1}, 500)
    # S merges into M: S (400) is 18 min from M, u2 (50) is 22 min from M instead of 4
    total = 1550
    assert m["mean_minutes_to_centre"] == pytest.approx((400 * 18 + 100 * 5 + 50 * 22) / total)
    assert m["mean_minutes_to_step"] == pytest.approx((100 * 5 + 50 * 4) / total)
    assert m["V2_n_systems"] == 1 and m["K5_pop_share_service_centre"] == 1.0
    assert m["K3_pop_share_over_20"] == pytest.approx(50 / total)
    assert m["K6_small_systems"] == 0 and m["V5_non_contiguous_systems"] == 0


def test_pareto_keeps_only_non_dominated():
    cost = np.array([1.0, 2.0, 2.0, 0.5])
    n = np.array([10, 5, 8, 12])
    assert _pareto(cost, n).tolist() == [True, True, False, True]
