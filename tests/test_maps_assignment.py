"""Assignment error (D3.3.2 draft), maps/assignment.py."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "maps"))
from assignment import assignment, same_system_pairs

# Units 0..3; providers of the service in units 0 and 2.
# Unit 1 is 5 min from provider 0 and 3 min from provider 2.
# Unit 3 is 10 min from provider 0 and 40 from provider 2.
T = np.array([[0, 5, 30, 10], [5, 0, 3, 20], [30, 3, 0, 40], [10, 20, 40, 0]], float)
PROV = np.array([True, False, True, False])
T_ALL = T[:, PROV].min(axis=1)
W = np.array([100.0, 50.0, 200.0, 150.0])


def run(roots, w=W):
    return assignment(np.array(roots), w, T, PROV, T_ALL)


def test_pairs_cover_every_couple_inside_each_system():
    i, j = same_system_pairs(np.array([7, 3, 7, 7]))
    assert sorted(zip(i.tolist(), j.tolist())) == sorted(
        [(a, b) for a in (0, 2, 3) for b in (0, 2, 3)] + [(1, 1)])


def test_every_unit_in_the_system_of_its_fastest_provider_has_no_error():
    m = run([0, 2, 2, 0])
    assert m["cov"] == 1 and m["mis"] == 0 and m["err"] == 0


def test_unit_put_with_the_slower_provider():
    # unit 1 sits with provider 0 (5 min) although provider 2 is at 3 min: error 2
    m = run([0, 0, 2, 0])
    assert m["mis"] == pytest.approx(50 / 500)
    assert m["err"] == pytest.approx(50 * 2 / 500)
    assert m["errq"] == pytest.approx(50 * 4 / 500)
    assert m["mis5"] == 0


def test_system_without_provider_is_uncovered_not_an_error():
    m = run([0, 2, 2, 3])  # unit 3 alone: no provider inside
    assert m["cov"] == pytest.approx(350 / 500)
    assert m["mis"] == 0


def test_zero_weight_units_do_not_count():
    w = W.copy()
    w[1] = 0
    assert run([0, 0, 2, 0], w)["mis"] == 0
