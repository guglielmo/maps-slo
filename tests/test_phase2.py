from builders import MAPS, problem, scenario

from maps_slo.phase2 import phase2


def merged_to(p, ptr, uid):
    j = ptr[p.index[uid]]
    return None if j == -1 else p.ids[j]


def pair(level_a, w_a, level_b, w_b, share=0.5, minutes=10, sc=None):
    p = problem([("a", level_a, w_a), ("b", level_b, w_b)], [("a", "b", share)],
                {("a", "b"): minutes}, sc=sc)
    return p, phase2(p, sc or scenario())


def test_A6_equal_levels_do_not_merge():
    p, ptr = pair(5, 8000, 5, 9000)
    assert merged_to(p, ptr, "a") is None and merged_to(p, ptr, "b") is None


def test_A6_toward_weaker_level_does_not_merge():
    p, ptr = pair(4, 30000, 5, 9000)  # 5 -> 4 is not declared, 4 -> 5 is downward
    assert merged_to(p, ptr, "a") is None and merged_to(p, ptr, "b") is None


def test_A6_undeclared_pair_3_to_2():
    p, ptr = pair(3, 60000, 2, 150000)
    assert merged_to(p, ptr, "a") is None and merged_to(p, ptr, "b") is None


def test_A6_undeclared_pair_4_to_3():
    p, ptr = pair(4, 30000, 3, 60000)
    assert merged_to(p, ptr, "a") is None and merged_to(p, ptr, "b") is None


def test_declared_pair_merges():
    p, ptr = pair(5, 8000, 3, 60000)
    assert merged_to(p, ptr, "a") == "b" and merged_to(p, ptr, "b") is None


def test_D15_share_threshold_is_strict():
    p, ptr = pair(5, 8000, 1, 300000, share=0.0309)
    assert merged_to(p, ptr, "a") is None
    p, ptr = pair(5, 8000, 1, 300000, share=0.031)
    assert merged_to(p, ptr, "a") == "b"


def test_D15_time_threshold_is_strict():
    p, ptr = pair(5, 8000, 1, 300000, minutes=20)
    assert merged_to(p, ptr, "a") is None
    p, ptr = pair(5, 8000, 1, 300000, minutes=19)
    assert merged_to(p, ptr, "a") == "b"


def test_share_is_on_the_perimeter_of_the_joining_unit():
    # a joins b: 2% of a's perimeter is shared, 50% of b's
    p = problem([("a", 5, 8000), ("b", 1, 300000)], [("a", "b", 0.02, 0.5)], {("a", "b"): 10})
    assert merged_to(p, phase2(p, scenario()), "a") is None
    p = problem([("a", 5, 8000), ("b", 1, 300000)], [("a", "b", 0.5, 0.02)], {("a", "b"): 10})
    assert merged_to(p, phase2(p, scenario()), "a") == "b"


def test_A7_row_of_minor_centralities_stays_separate():
    p = problem([("a", 4, 30000), ("b", 5, 9000), ("c", 6, 5000)],
                [("a", "b"), ("b", "c")], {("a", "b"): 5, ("b", "c"): 5, ("a", "c"): 10})
    ptr = phase2(p, scenario())
    assert (ptr == -1).all()


def test_A8_prefers_the_stronger_level():
    p = problem([("x", 5, 8000), ("m1", 1, 300000), ("m2", 2, 150000)],
                [("x", "m1"), ("x", "m2")], {("x", "m1"): 15, ("x", "m2"): 5})
    assert merged_to(p, phase2(p, scenario()), "x") == "m1"


def test_A8_equal_level_prefers_greater_weight():
    p = problem([("x", 5, 8000), ("m1", 1, 300000), ("m2", 1, 400000)],
                [("x", "m1"), ("x", "m2")], {("x", "m1"): 5, ("x", "m2"): 15})
    assert merged_to(p, phase2(p, scenario()), "x") == "m2"


def test_A8_equal_level_and_weight_prefers_smaller_id():
    p = problem([("x", 5, 8000), ("m2", 1, 300000), ("m1", 1, 300000)],
                [("x", "m1"), ("x", "m2")], {("x", "m1"): 15, ("x", "m2"): 5})
    assert merged_to(p, phase2(p, scenario()), "x") == "m1"


def test_I3_added_pair_changes_the_result():
    sc = scenario(phase2_pairs={**MAPS["phase2_pairs"], 4: [1, 2, 3]})
    p, ptr = pair(4, 30000, 3, 60000, sc=sc)
    assert merged_to(p, ptr, "a") == "b"


def test_I3_removed_pair_changes_the_result():
    sc = scenario(phase2_pairs={**MAPS["phase2_pairs"], 5: [1, 2]})
    p, ptr = pair(5, 8000, 3, 60000, sc=sc)
    assert merged_to(p, ptr, "a") is None


def test_D15_time_is_measured_from_the_joining_centrality():
    units = [("a", 5, 8000), ("b", 1, 300000)]
    p = problem(units, [("a", "b")], {("a", "b"): 25, ("b", "a"): 10})
    assert merged_to(p, phase2(p, scenario()), "a") is None
    p = problem(units, [("a", "b")], {("a", "b"): 10, ("b", "a"): 25})
    assert merged_to(p, phase2(p, scenario()), "a") == "b"
