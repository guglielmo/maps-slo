from builders import ix, run_case, scenario, step, system_of


def case1(w_s):
    # s: single-unit system, level 6; h: level 4, heads a system with u
    return run_case([("s", 6, w_s), ("h", 4, 15000), ("u", None, 1000)], [("s", "h")],
                    {("s", "h"): 10, ("u", "h"): 5, ("u", "s"): 30})


def test_A12_case1_heavier_single_becomes_the_centre():
    r = case1(20000)
    assert step(r, "h") == "s" and system_of(r, "u") == "s" and system_of(r, "s") == "s"
    h = ix(r.problem, "h")
    assert r.rule[h] == "P4-CLAIMED" and r.problem.level[h] == 4  # still a centrality
    assert r.phase4.changed_heads == [(h, ix(r.problem, "s"))]  # metric V10


def test_A12_case2_lighter_single_joins_as_merged_centre():
    r = case1(10000)
    assert step(r, "s") == "h" and system_of(r, "s") == "h"
    assert r.rule[ix(r.problem, "s")] == "P4-JOIN"


def test_A11_phase4_does_not_touch_phase3_assignments():
    for w in (20000, 10000):
        r = case1(w)
        non = ~r.problem.is_centrality
        assert (r.ptr3[non] == r.ptr4[non]).all()


def test_A12_case3_single_of_level_2_starts_no_merge():
    r = run_case([("x", 2, 150000), ("h3", 3, 60000), ("u", None, 1000)], [("x", "h3")],
                 {("x", "h3"): 10, ("u", "h3"): 5, ("u", "x"): 30})
    assert step(r, "x") is None and step(r, "h3") is None
    assert r.rule[ix(r.problem, "x")] == "HEAD"


def case4(w_s):
    # a (level 5) merges into T (level 3) in phase 2; s is contiguous only to a
    return run_case([("T", 3, 60000), ("a", 5, 8000), ("s", 6, w_s)], [("a", "T"), ("s", "a")],
                    {("a", "T"): 10, ("s", "a"): 8, ("s", "T"): 25})


def test_A12_case4_lighter_than_merged_neighbour_enters_its_system():
    r = case4(5000)
    assert step(r, "s") == "a" and system_of(r, "s") == "T" and step(r, "a") == "T"


def test_A12_case4_heavier_than_merged_neighbour_stays_alone():
    r = case4(9000)
    assert step(r, "s") is None and step(r, "a") == "T"
    assert r.rule[ix(r.problem, "s")] == "P4-ALONE"


def test_A12_case5_compares_with_the_nearest_even_if_less_populous():
    r = run_case(
        [("s", 6, 10000), ("n", 5, 12000), ("f", 4, 40000), ("u1", None, 1), ("u2", None, 1)],
        [("s", "n"), ("s", "f")],
        {("s", "n"): 5, ("s", "f"): 15, ("u1", "n"): 2, ("u1", "f"): 50, ("u1", "s"): 30,
         ("u2", "f"): 2, ("u2", "n"): 50, ("u2", "s"): 30},
    )
    assert step(r, "s") == "n"


def test_A12_case6_level4_joins_single_unit_level3():
    r = run_case([("s", 4, 30000), ("t", 3, 60000)], [("s", "t")], {("s", "t"): 10})
    assert step(r, "s") == "t" and r.rule[ix(r.problem, "s")] == "P4-D25"


def test_D25_non_eligible_single_wins_regardless_of_weight():
    r = run_case([("s", 4, 30000), ("t", 3, 20000)], [("s", "t")], {("s", "t"): 10})
    assert step(r, "s") == "t"


def case7(w_y):
    # a (level 5) merged into T; y heads a system with u; s nearer to a than to y
    return run_case(
        [("T", 3, 60000), ("a", 5, 8000), ("s", 6, 20000), ("y", 4, w_y), ("u", None, 1)],
        [("a", "T"), ("s", "a"), ("s", "y")],
        {("a", "T"): 10, ("s", "a"): 5, ("s", "y"): 10, ("u", "y"): 3, ("u", "s"): 30,
         ("u", "a"): 40, ("u", "T"): 40},
    )


def test_A12_case7_heavier_than_y_becomes_its_centre():
    r = case7(15000)
    assert step(r, "y") == "s" and system_of(r, "u") == "s" and system_of(r, "s") == "s"


def test_A12_case7_lighter_than_y_joins_y():
    r = case7(25000)
    assert step(r, "s") == "y" and system_of(r, "s") == "y"


def test_determinism_own_choice_prevails_over_a_claim():
    # c chooses d (heavier); s (heavier than c) claims c: the claim has no effect
    r = run_case(
        [("c", 6, 10000), ("d", 5, 20000), ("s", 6, 15000), ("u", None, 1)],
        [("c", "d"), ("c", "s")],
        {("c", "d"): 5, ("c", "s"): 8, ("u", "d"): 3, ("u", "c"): 30, ("u", "s"): 30},
    )
    assert step(r, "c") == "d" and step(r, "s") is None
    assert r.rule[ix(r.problem, "s")] == "P4-CLAIM-IGNORED"


def test_several_claimants_the_heaviest_wins():
    r = run_case(
        [("h", 5, 10000), ("s1", 6, 15000), ("s2", 6, 18000), ("u", None, 1)],
        [("s1", "h"), ("s2", "h")],
        {("s1", "h"): 5, ("s2", "h"): 6, ("u", "h"): 2, ("u", "s1"): 30, ("u", "s2"): 30},
    )
    assert step(r, "h") == "s2" and system_of(r, "u") == "s2"
    assert r.rule[ix(r.problem, "s1")] == "P4-CLAIM-LOST"


def test_I4_phase4_levels_are_declared_in_the_scenario():
    units = [("s", 6, 10000), ("h", 4, 15000), ("u", None, 1000)]
    times = {("s", "h"): 10, ("u", "h"): 5, ("u", "s"): 30}
    r = run_case(units, [("s", "h")], times, sc=scenario(phase4_levels=[4, 5]))
    assert step(r, "s") is None and r.rule[ix(r.problem, "s")] == "HEAD"


def test_I4_four_level_scheme():
    sc = scenario(levels=[1, 2, 3, 4], phase2_pairs={2: [1], 3: [1, 2]}, phase4_levels=[3, 4])
    r = run_case([("s", 4, 10000), ("h", 3, 15000), ("u", None, 1000)], [("s", "h")],
                 {("s", "h"): 10, ("u", "h"): 5, ("u", "s"): 30}, sc=sc)
    assert step(r, "s") == "h"


def test_A12_mutual_choice_equal_weight():
    r = run_case([("A", 6, 10000), ("B", 6, 10000)], [("A", "B")], {("A", "B"): 5})
    assert step(r, "B") == "A" and system_of(r, "B") == "A"
    assert r.rule[ix(r.problem, "A")] == "P4-CLAIM"
    assert r.phase4.ignored_claims == []


def test_A12_mutual_choice_different_weight():
    r = run_case([("s", 6, 20000), ("j", 5, 5000)], [("s", "j")], {("s", "j"): 5})
    assert step(r, "j") == "s"
    assert r.rule[ix(r.problem, "s")] == "P4-CLAIM"
    assert r.phase4.ignored_claims == []


def _r4_case(reverse):
    from maps_slo.inputs import Inputs

    units = [("t", 6, 30000), ("j", 6, 20000), ("k", 5, 10000), ("j2", 6, 25000), ("u", None, 1)]
    contig = [("t", "j"), ("j", "k"), ("j2", "k")]
    times = {("t", "j"): 5, ("j", "k"): 5, ("j2", "k"): 5, ("u", "k"): 2, ("u", "t"): 50,
             ("u", "j"): 50, ("u", "j2"): 50}
    if reverse:
        units, contig = units[::-1], [(b, a) for a, b in contig[::-1]]
        times = dict(reversed(list(times.items())))
    from builders import make_inputs

    inp: Inputs = make_inputs(units, contig, times)
    from maps_slo.engine import run

    return run(scenario(), inp)


def test_R4_phase4_rules_do_not_depend_on_record_order():
    from maps_slo.output import units_table

    a, b = _r4_case(False), _r4_case(True)
    ua = units_table(a).sort_values("id").reset_index(drop=True)
    ub = units_table(b).sort_values("id").reset_index(drop=True)
    assert ua.equals(ub)

    def ids(r, pairs):
        return [(r.problem.ids[x], r.problem.ids[y]) for x, y in pairs]

    assert ids(a, a.phase4.ignored_claims) == ids(b, b.phase4.ignored_claims)
    assert ids(a, a.phase4.changed_heads) == ids(b, b.phase4.changed_heads)
    # j joins t (its own join), so t's claim on j is satisfied; j2 claims k (a head)
    rule = dict(zip(ua.id, ua.rule))
    assert rule["j"] == "P4-JOIN" and rule["t"] == "P4-CLAIM"
    assert rule["k"] == "P4-CLAIMED" and rule["j2"] == "P4-CLAIM"
    assert ids(a, a.phase4.changed_heads) == [("k", "j2")]
    assert ids(a, a.phase4.ignored_claims) == []


def test_R4_claimed_with_own_join_and_other_claimant_is_deterministic():
    # j joins d (own join prevails): both claimants are ignored, j keeps rule P4-JOIN
    r = run_case(
        [("j", 6, 10000), ("d", 5, 20000), ("s1", 6, 15000), ("s2", 6, 12000), ("u", None, 1)],
        [("j", "d"), ("j", "s1"), ("j", "s2")],
        {("j", "d"): 5, ("j", "s1"): 8, ("j", "s2"): 9, ("u", "d"): 3, ("u", "j"): 30,
         ("u", "s1"): 30, ("u", "s2"): 30},
    )
    p = r.problem
    assert step(r, "j") == "d" and r.rule[ix(p, "j")] == "P4-JOIN"
    assert [(p.ids[a], p.ids[b]) for a, b in r.phase4.ignored_claims] == [("s1", "j"), ("s2", "j")]


def test_claimed_centrality_minutes_use_claimant_to_claimed_time():
    import numpy as np
    from builders import make_inputs

    from maps_slo.engine import run

    inp = make_inputs([("s", 6, 20000), ("h", 4, 15000), ("u", None, 1000)], [("s", "h")],
                      {("s", "h"): 10, ("u", "h"): 5, ("u", "s"): 30})
    t = inp.times
    inp.times = t[~((t.origin == "h") & (t.destination == "s"))]
    r = run(scenario(), inp)
    h = ix(r.problem, "h")
    assert step(r, "h") == "s" and r.rule[h] == "P4-CLAIMED"
    assert np.isfinite(r.minutes[h]) and r.minutes[h] == 10


def test_chain_of_single_unit_systems():
    r = run_case([("s1", 6, 10000), ("s2", 6, 20000), ("c", 5, 30000)],
                 [("s1", "s2"), ("s2", "c")], {("s1", "s2"): 5, ("s2", "c"): 5, ("s1", "c"): 50})
    assert step(r, "s1") == "s2" and step(r, "s2") == "c"
    assert system_of(r, "s1") == "c"


def test_claimed_centrality_with_merged_centre_moves_whole_system():
    from maps_slo.output import systems_table, units_table

    # j (level 3) heads a system with k (level 5, merged into j in phase 2) and attracted v
    r = run_case(
        [("j", 3, 20000), ("k", 5, 8000), ("v", None, 500), ("s", 4, 30000)],
        [("k", "j"), ("s", "j")],
        {("k", "j"): 5, ("s", "j"): 6, ("v", "k"): 2, ("v", "j"): 20, ("v", "s"): 50,
         ("k", "s"): 50},
    )
    assert step(r, "j") == "s" and system_of(r, "k") == "s" and system_of(r, "v") == "s"
    sysd = systems_table(r)
    row = sysd[sysd.system_id == "s"].iloc[0]
    assert row.merged_centres_phase4 == 1  # j, claimed in phase 4
    assert row.merged_centres_phase2 == 1  # k, merged in phase 2
    units = units_table(r)
    assert row.n_units == (units.system_id == "s").sum() == 4
    assert row.total_weight == 20000 + 8000 + 500 + 30000


def test_contiguity_direction_in_phase_4():
    # share is measured on the perimeter of the single unit s; h (level 3) never acts
    units = [("s", 6, 10000), ("h", 3, 5000)]
    sc = scenario(phase2_pairs={2: [1], 3: [1], 4: [1, 2], 5: [1, 2], 6: [1, 2]})
    r = run_case(units, [("s", "h", 0.02, 0.5)], {("s", "h"): 5}, sc=sc)
    assert step(r, "s") is None and r.rule[ix(r.problem, "s")] == "P4-ALONE"
    r = run_case(units, [("s", "h", 0.5, 0.02)], {("s", "h"): 5}, sc=sc)
    assert step(r, "s") == "h" and r.rule[ix(r.problem, "s")] == "P4-D25"


def test_time_tie_in_phase_4_broken_by_weight_then_id():
    # s has two merged-free candidates at the same time; heavier first (s joins it: heavier than s)
    r = run_case(
        [("s", 6, 5000), ("a", 5, 6000), ("b", 5, 9000)], [("s", "a"), ("s", "b")],
        {("s", "a"): 5, ("s", "b"): 5, ("a", "b"): 50},
    )
    assert step(r, "s") == "b"
    r = run_case(
        [("s", 6, 5000), ("a", 5, 9000), ("b", 5, 9000)], [("s", "a"), ("s", "b")],
        {("s", "a"): 5, ("s", "b"): 5, ("a", "b"): 50},
    )
    assert step(r, "s") == "a"


def test_single_skips_two_lighter_merged_centralities_then_stays_alone():
    # T1, T2 level 3 heads; m1, m2 (level 5, light) merged into them; s heavier than both
    r = run_case(
        [("T1", 3, 60000), ("T2", 3, 60000), ("m1", 5, 3000), ("m2", 5, 4000), ("s", 6, 9000)],
        [("m1", "T1"), ("m2", "T2"), ("s", "m1"), ("s", "m2")],
        {("m1", "T1"): 5, ("m2", "T2"): 5, ("s", "m1"): 6, ("s", "m2"): 7,
         ("T1", "T2"): 90, ("s", "T1"): 90, ("s", "T2"): 90},
    )
    assert step(r, "m1") == "T1" and step(r, "m2") == "T2"
    assert step(r, "s") is None and r.rule[ix(r.problem, "s")] == "P4-ALONE"
