import pytest
from builders import problem, scenario

from maps_slo.phase3 import phase3


def attracted_by(p, r, uid):
    j = r.pointers[p.index[uid]]
    return None if j == -1 else p.ids[j]


def test_A3_merged_centrality_keeps_attraction():
    p = problem([("m", 1, 300000), ("s", 3, 60000), ("u", None, 1000)], [("m", "s")],
                {("m", "s"): 10, ("u", "s"): 5, ("u", "m"): 15})
    assert attracted_by(p, phase3(p, scenario()), "u") == "s"


def test_S3_tie_on_time_stronger_level_wins():
    p = problem([("a", 4, 20000), ("b", 5, 30000), ("u", None, 1)],
                times={("u", "a"): 10, ("u", "b"): 10})
    assert attracted_by(p, phase3(p, scenario()), "u") == "a"


def test_S3_tie_on_time_and_level_heavier_wins():
    p = problem([("a", 5, 8000), ("b", 5, 9000), ("u", None, 1)],
                times={("u", "a"): 10, ("u", "b"): 10})
    assert attracted_by(p, phase3(p, scenario()), "u") == "b"


def test_S3_merged_competes_with_its_own_level():
    # s (level 3) is merged into m (level 1); c2 is an unmerged level 2
    p = problem([("m", 1, 300000), ("s", 3, 60000), ("c2", 2, 150000), ("u", None, 1)],
                [("m", "s")],
                {("m", "s"): 10, ("u", "s"): 12, ("u", "c2"): 12, ("u", "m"): 40})
    assert attracted_by(p, phase3(p, scenario()), "u") == "c2"


def test_S3_merged_competes_with_its_own_weight():
    # s (5,000) is merged into m (300,000); t (7,000) heads its own system
    p = problem([("m", 1, 300000), ("s", 5, 5000), ("t", 5, 7000), ("u", None, 1)],
                [("m", "s")], {("m", "s"): 10, ("u", "s"): 10, ("u", "t"): 10, ("u", "m"): 40})
    assert attracted_by(p, phase3(p, scenario()), "u") == "t"


def test_S4_last_tiebreak_follows_declared_id_order():
    units = [("9", 5, 8000), ("10", 5, 8000), ("u", None, 1)]
    times = {("u", "9"): 10, ("u", "10"): 10}
    p = problem(units, times=times)
    assert attracted_by(p, phase3(p, scenario()), "u") == "10"
    sc = scenario(id_order="explicit", id_order_list=["9", "10", "u"])
    p = problem(units, times=times, sc=sc)
    assert attracted_by(p, phase3(p, sc), "u") == "9"


def test_S4_record_order_is_irrelevant():
    units = [("a", 5, 8000), ("b", 5, 8000), ("u", None, 1)]
    times = {("u", "a"): 10, ("u", "b"): 10}
    p1 = problem(units, times=times)
    p2 = problem(list(reversed(units)), times=times)
    assert attracted_by(p1, phase3(p1, scenario()), "u") == attracted_by(
        p2, phase3(p2, scenario()), "u") == "a"


def test_S5_distant_units_are_assigned_and_flagged():
    p = problem([("a", 5, 8000), ("u", None, 1)], times={("u", "a"): 70})
    r = phase3(p, scenario())
    u = p.index["u"]
    assert attracted_by(p, r, "u") == "a" and r.distant[u] and r.minutes[u] == 70


def test_S6_threshold_changes_flags_not_assignment():
    units = [("a", 5, 8000), ("u1", None, 1), ("u2", None, 1)]
    times = {("u1", "a"): 45, ("u2", "a"): 25}
    p = problem(units, times=times)
    r60, r30 = phase3(p, scenario()), phase3(p, scenario(distant_minutes=30))
    assert (r60.pointers == r30.pointers).all()
    assert not r60.distant.any()
    assert r30.distant[p.index["u1"]] and not r30.distant[p.index["u2"]]


def test_R6_unit_without_times_is_unassigned():
    p = problem([("a", 5, 8000), ("u", None, 1)])
    r = phase3(p, scenario())
    assert r.unassigned[p.index["u"]] and r.pointers[p.index["u"]] == -1


def test_time_is_measured_from_the_assigned_unit():
    p = problem([("a", 5, 8000), ("b", 5, 8000), ("u", None, 1)],
                times={("u", "a"): 10, ("a", "u"): 30, ("u", "b"): 20, ("b", "u"): 5})
    assert attracted_by(p, phase3(p, scenario()), "u") == "a"


def test_S5_time_equal_to_threshold_is_not_distant():
    p = problem([("a", 5, 8000), ("u", None, 1)], times={("u", "a"): 60})
    r = phase3(p, scenario())
    assert not r.distant[p.index["u"]]


def test_block_must_be_positive():
    p = problem([("a", 5, 8000), ("u", None, 1)], times={("u", "a"): 5})
    with pytest.raises(ValueError, match="block"):
        phase3(p, scenario(), block=0)
