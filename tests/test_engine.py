import numpy as np
import pandas as pd
import pytest
from builders import make_inputs, run_case, scenario

from maps_slo.engine import run
from maps_slo.output import systems_table, units_table
from maps_slo.problem import InputError

MILANO = (
    [("M", 1, 300000, "Milano"), ("S", 3, 80000, "Sesto San Giovanni"),
     ("X", 5, 9000, "Xtown"), ("u", None, 500, "Ucomune")],
    [("M", "S"), ("S", "X")],
    {("M", "S"): 10, ("S", "X"): 8, ("u", "X"): 3, ("u", "S"): 15, ("u", "M"): 25,
     ("X", "M"): 18},
)


def row(df, uid):
    return df.set_index("id").loc[uid]


def test_A4_A5_three_step_chain_and_labels():
    t = units_table(run_case(*MILANO))
    u = row(t, "u")
    assert u.system_id == "M"
    assert u.full_label == "Milano(Xtown)"
    assert u.chain == "Xtown → Sesto San Giovanni → Milano"
    assert row(t, "S").full_label == "Milano(Sesto San Giovanni)"


def test_A1_centralities_unchanged():
    r = run_case(*MILANO)
    t = units_table(r)
    assert int(t.level.notna().sum()) == 3
    assert t[t.level.notna()].set_index("id").level.to_dict() == {"M": 1, "S": 3, "X": 5}


def test_A2_one_system_less_per_merge():
    r = run_case(*MILANO)
    merges = int((r.ptr2 >= 0).sum())
    assert len(systems_table(r)) == int(r.problem.is_centrality.sum()) - merges == 1


def test_S2_merged_centrality_keeps_its_nature():
    s = row(units_table(run_case(*MILANO)), "S")
    assert s.level == 3 and s.role == "merged_centre" and s.system_id == "M"
    m = row(units_table(run_case(*MILANO)), "M")
    assert m.role == "main_centre" and m.system_id == "M"


def test_S8_every_system_is_headed_by_an_unmerged_centrality():
    r = run_case(*MILANO)
    t = units_table(r)
    heads = t.set_index("id").loc[t.system_id.unique()]
    assert (heads.role == "main_centre").all() and heads.direct_step_id.isna().all()


def test_S3_merged_winner_brings_the_unit_into_the_main_centre_system():
    r = run_case([("m", 1, 300000), ("s", 3, 60000), ("u", None, 1)], [("m", "s")],
                 {("m", "s"): 10, ("u", "s"): 5, ("u", "m"): 15})
    u = row(units_table(r), "u")
    assert u.direct_step_id == "s" and u.system_id == "m"


def test_O1b_phase_and_rule_on_every_row():
    t = units_table(run_case(*MILANO))
    assert t.phase.notna().all() and t.rule.notna().all()
    assert row(t, "S").rule == "P2-MERGE" and row(t, "u").rule == "P3-NEAREST"


def test_O2_O3_unique_units_and_weight_sums():
    r = run_case(*MILANO)
    t, s = units_table(r), systems_table(r)
    assert t.id.is_unique
    assert s.set_index("system_id").total_weight["M"] == 300000 + 80000 + 9000 + 500


def test_R1_two_runs_same_output():
    pd.testing.assert_frame_equal(units_table(run_case(*MILANO)), units_table(run_case(*MILANO)))


def test_R4_record_order_does_not_matter():
    inp = make_inputs(*MILANO)
    r1 = run(scenario(), inp)
    shuffled = make_inputs(*MILANO)
    for name in ("units", "contiguity", "times"):
        df = getattr(shuffled, name)
        setattr(shuffled, name, df.sample(frac=1, random_state=3).reset_index(drop=True))
    r2 = run(scenario(), shuffled)
    pd.testing.assert_frame_equal(units_table(r1), units_table(r2))
    for attr in ("ptr2", "ptr3", "ptr4"):
        a = {r1.problem.ids[i]: getattr(r1, attr)[i] for i in range(r1.problem.n)}
        b = {r2.problem.ids[i]: getattr(r2, attr)[i] for i in range(r2.problem.n)}
        ida = {k: (r1.problem.ids[v] if v >= 0 else None) for k, v in a.items()}
        idb = {k: (r2.problem.ids[v] if v >= 0 else None) for k, v in b.items()}
        assert ida == idb


def test_I1_runs_on_levels_only():
    inp = make_inputs(*MILANO)
    assert list(inp.units.columns) == ["id", "name", "level", "weight"]
    assert len(units_table(run(scenario(), inp))) == 4


def test_I2_seven_levels_without_code_changes():
    sc = scenario(levels=[1, 2, 3, 4, 5, 6, 7],
                  phase2_pairs={2: [1], 3: [1], 4: [1, 2], 5: [1, 2, 3], 6: [1, 2, 3],
                                7: [1, 2, 3]},
                  phase4_levels=[4, 5, 6, 7])
    r = run_case([("a", 7, 1000), ("b", 3, 60000)], [("a", "b")], {("a", "b"): 5}, sc=sc)
    assert row(units_table(r), "a").system_id == "b"


def test_I2_five_levels_without_code_changes():
    sc = scenario(levels=[1, 2, 3, 4, 5],
                  phase2_pairs={2: [1], 3: [1], 4: [1, 2], 5: [1, 2, 3]},
                  phase4_levels=[4, 5])
    r = run_case([("a", 5, 1000), ("b", 3, 60000)], [("a", "b")], {("a", "b"): 5}, sc=sc)
    assert row(units_table(r), "a").system_id == "b"


def synthetic(n=200, seed=7):
    rng = np.random.default_rng(seed)
    side = int(np.ceil(np.sqrt(n)))
    ids = [f"zone-{chr(97 + i % 26)}{i:03d}" for i in range(n)]
    pos = {uid: (i % side, i // side) for i, uid in enumerate(ids)}
    levels = [None] * n
    for i in rng.choice(n, 40, replace=False):
        levels[i] = int(rng.integers(1, 7))
    units = [(ids[i], levels[i], int(rng.integers(100, 300000))) for i in range(n)]
    contig = []
    for i, a in enumerate(ids):
        x, y = pos[a]
        for b in ids[i + 1:]:
            bx, by = pos[b]
            if abs(bx - x) + abs(by - y) == 1:
                contig.append((a, b, float(rng.uniform(0.01, 0.3)), float(rng.uniform(0.01, 0.3))))
    times = {}
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            (ax, ay), (bx, by) = pos[a], pos[b]
            times[(a, b)] = float(round(6 * np.hypot(ax - bx, ay - by)))
    return units, contig, times


def test_I6_synthetic_units_with_non_istat_ids():
    r = run_case(*synthetic())
    t = units_table(r)
    assert len(t) == 200 and t.id.is_unique
    heads = t.set_index("id").loc[t.system_id.unique()]
    assert (heads.role == "main_centre").all()


def test_I6_engine_does_not_assume_numeric_ids():
    with pytest.raises(InputError, match="not an integer"):
        run_case(*synthetic(), sc=scenario(id_order="numeric"))
