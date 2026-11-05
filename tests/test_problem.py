import numpy as np
import pandas as pd
import pytest
from builders import make_inputs, problem, scenario

from maps_slo.inputs import Inputs
from maps_slo.problem import InputError, build_problem


def test_arrays_are_indexed_by_position():
    p = problem([("a", 1, 100), ("b", None, 10)], [("a", "b", 0.2, 0.4)], {("a", "b"): 7})
    a, b = p.index["a"], p.index["b"]
    assert p.is_centrality[a] and not p.is_centrality[b]
    assert p.level[b] == -1 and p.strength[a] == 0
    assert p.times[a, b] == 7 and p.times[b, a] == 7 and p.times[a, a] == 0
    assert p.neighbours[a] == [(b, 0.2)] and p.neighbours[b] == [(a, 0.4)]


def test_missing_times_are_nan():
    p = problem([("a", 1, 100), ("b", None, 10)])
    assert np.isnan(p.times[0, 1])


def test_I6_lexicographic_order():
    p = problem([("9", 1, 1), ("10", 1, 1)])
    assert p.id_rank[p.index["10"]] < p.id_rank[p.index["9"]]


def test_I6_numeric_order():
    p = problem([("9", 1, 1), ("10", 1, 1)], sc=scenario(id_order="numeric"))
    assert p.id_rank[p.index["9"]] < p.id_rank[p.index["10"]]


def test_I6_numeric_order_rejects_non_numeric_ids():
    with pytest.raises(InputError, match="not an integer"):
        problem([("zone-a", 1, 1)], sc=scenario(id_order="numeric"))


def test_numeric_order_rejects_equal_keys():
    with pytest.raises(InputError, match="same numeric key"):
        problem([("01", 1, 1), ("1", 1, 1)], sc=scenario(id_order="numeric"))


def test_explicit_order():
    sc = scenario(id_order="explicit", id_order_list=["b", "a"])
    p = problem([("a", 1, 1), ("b", 1, 1)], sc=sc)
    assert p.id_rank[p.index["b"]] == 0


def test_undeclared_level_rejected():
    with pytest.raises(InputError, match="not declared"):
        problem([("a", 7, 1)])


def test_unknown_id_in_times_rejected():
    inp = make_inputs([("a", 1, 1)], times={("a", "zz"): 3})
    with pytest.raises(InputError, match="zz"):
        build_problem(inp, scenario())


def test_duplicate_ids_rejected():
    with pytest.raises(InputError, match="duplicate"):
        problem([("a", 1, 1), ("a", None, 1)])


# --- review fixes -----------------------------------------------------------------------------


def _frames(units, contig_rows, time_rows):
    u = pd.DataFrame([{"id": i, "name": i, "level": lv, "weight": 1.0} for i, lv in units])
    u["level"] = u["level"].astype("Int64")
    c = pd.DataFrame(
        contig_rows, columns=["origin", "neighbour", "shared_length", "origin_perimeter"]
    )
    t = pd.DataFrame(time_rows, columns=["origin", "destination", "minutes"])
    return u, c, t


def _build(units, contig_rows=(), time_rows=(), sc=None):
    u, c, t = _frames(units, list(contig_rows), list(time_rows))
    return build_problem(Inputs(units=u, contiguity=c, times=t), sc or scenario())


def test_R4_duplicate_time_pairs_rejected():
    with pytest.raises(InputError, match="duplicate") as e:
        _build([("a", 1), ("b", None)], time_rows=[("a", "b", 3.0), ("a", "b", 5.0)])
    assert "a" in str(e.value) and "b" in str(e.value)


def test_R4_duplicate_contiguity_rejected():
    with pytest.raises(InputError, match="duplicate"):
        _build([("a", 1), ("b", None)], [("a", "b", 1.0, 2.0), ("a", "b", 1.0, 2.0)])


def test_R4_neighbours_sorted_by_declared_order():
    units = [("a", 1), ("b", None), ("c", None), ("d", None)]
    rows = [("a", "d", 1.0, 4.0), ("a", "b", 1.0, 4.0), ("a", "c", 1.0, 4.0)]
    p1 = _build(units, rows)
    p2 = _build(units, rows[::-1])
    assert p1.neighbours == p2.neighbours
    assert [j for j, _ in p1.neighbours[p1.index["a"]]] == [p1.index[x] for x in ("b", "c", "d")]


def test_I6_csv_ids_like_NA_are_kept(tmp_path):
    (tmp_path / "u.csv").write_text(
        "id,name,level,weight\nNA,x,1,1\nNULL,y,,2\n001,z,,3\n,w,,4\nNone,v,,5\n",
        encoding="utf-8",
    )
    (tmp_path / "c.csv").write_text(
        "origin,neighbour,shared_length,origin_perimeter\nNA,NULL,1,4\nNULL,NA,1,4\n001,,1,4\n",
        encoding="utf-8",
    )
    (tmp_path / "t.csv").write_text(
        "origin,destination,minutes\nNA,NULL,5\nNULL,NA,5\nNone,001,3\n", encoding="utf-8"
    )
    inp = Inputs.from_paths(tmp_path / "u.csv", tmp_path / "c.csv", tmp_path / "t.csv", "x")
    p = build_problem(inp, scenario())
    assert sorted(p.ids.tolist()) == ["", "001", "NA", "NULL", "None"]
    assert p.level[p.index["NA"]] == 1 and p.level[p.index["NULL"]] == -1
    assert p.times[p.index["NA"], p.index["NULL"]] == 5
    assert [j for j, _ in p.neighbours[p.index["NA"]]] == [p.index["NULL"]]


def test_missing_unit_id_rejected():
    u, c, t = _frames([("a", 1), ("b", None)], [], [])
    u["id"] = pd.Series(["a", None], dtype=object)
    with pytest.raises(InputError, match="unit ids must not be missing"):
        build_problem(Inputs(units=u, contiguity=c, times=t), scenario())


def test_float_id_columns_rejected():
    u, c, t = _frames([("a", 1)], [], [])
    u["id"] = [10.0]
    with pytest.raises(InputError, match="strings or integers"):
        build_problem(Inputs(units=u, contiguity=c, times=t), scenario())
    u, c, t = _frames([("a", 1)], [], [("a", 10.0, 3.0)])
    t["destination"] = [10.0]
    with pytest.raises(InputError, match="strings or integers"):
        build_problem(Inputs(units=u, contiguity=c, times=t), scenario())


def test_non_integer_level_rejected():
    u, c, t = _frames([("a", 1)], [], [])
    u["level"] = [1.5]
    with pytest.raises(InputError, match="integer"):
        build_problem(Inputs(units=u, contiguity=c, times=t), scenario())


@pytest.mark.parametrize(
    "length,perimeter",
    [
        (1.0, 0.0),
        (1.0, -1.0),
        (1.0, float("nan")),
        (-1.0, 4.0),
        (float("inf"), 4.0),
        (float("nan"), 4.0),
    ],
)
def test_contiguity_measures_validated(length, perimeter):
    with pytest.raises(InputError, match="contiguity"):
        _build([("a", 1), ("b", None)], [("a", "b", length, perimeter)])


@pytest.mark.parametrize("w", [-1.0, float("inf")])
def test_weights_validated(w):
    u, c, t = _frames([("a", 1)], [], [])
    u["weight"] = [w]
    with pytest.raises(InputError, match="weight"):
        build_problem(Inputs(units=u, contiguity=c, times=t), scenario())


def test_input_suffix_case_insensitive(tmp_path):
    (tmp_path / "u.CSV").write_text("id,name,level,weight\na,a,1,1\n", encoding="utf-8")
    df = pd.DataFrame({"origin": ["a"], "destination": ["a"], "minutes": [0.0]})
    df.to_parquet(tmp_path / "t.Parquet")
    (tmp_path / "c.csv").write_text(
        "origin,neighbour,shared_length,origin_perimeter\n", encoding="utf-8"
    )
    inp = Inputs.from_paths(tmp_path / "u.CSV", tmp_path / "c.csv", tmp_path / "t.Parquet", "x")
    assert len(inp.units) == 1 and len(inp.times) == 1


def test_S3_close_times_are_not_merged_by_precision():
    from maps_slo.phase3 import phase3

    p = problem([("a", 5, 8000), ("b", 4, 20000), ("u", None, 1)],
                times={("u", "a"): 10.0, ("u", "b"): 10.0000001})
    r = phase3(p, scenario())
    assert p.ids[r.pointers[p.index["u"]]] == "a"


def test_I2_nullable_weight_with_na_is_an_input_error():
    inp = make_inputs([("a", 1, 10), ("b", None, 5)])
    inp.units["weight"] = pd.array([10.0, None], dtype="Float64")
    with pytest.raises(InputError, match="weight"):
        build_problem(inp, scenario())


def test_I2_contiguity_share_above_one_or_varying_perimeter_is_rejected():
    inp = make_inputs([("a", 1, 10), ("b", None, 5), ("c", None, 5)],
                      contig=[("a", "b"), ("a", "c")])
    inp.contiguity.loc[0, "shared_length"] = 2.0
    with pytest.raises(InputError, match="greater than origin_perimeter"):
        build_problem(inp, scenario())
    inp = make_inputs([("a", 1, 10), ("b", None, 5), ("c", None, 5)],
                      contig=[("a", "b"), ("a", "c")])
    inp.contiguity.loc[inp.contiguity.origin == "a", "origin_perimeter"] = [1.0, 2.0]
    with pytest.raises(InputError, match="differs"):
        build_problem(inp, scenario())
