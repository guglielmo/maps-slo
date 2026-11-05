"""Downstream corrections (decision D18), maps/corrections.py."""

import sys
from pathlib import Path

import pandas as pd
import pytest
from builders import run_case

from maps_slo.output import systems_table, units_table

sys.path.insert(0, str(Path(__file__).parents[1] / "maps"))
from corrections import CorrectionError, apply_corrections

# M (level 1) attracts u1; F (level 3) attracts u2; N (level 2) attracts u3.
# No contiguity: three systems.
CASE = (
    [("M", 1, 1000), ("F", 3, 300), ("N", 2, 500),
     ("u1", None, 10), ("u2", None, 20), ("u3", None, 30)],
    [],
    {("u1", "M"): 5, ("u2", "F"): 5, ("u3", "N"): 5, ("F", "M"): 30, ("N", "M"): 40,
     ("u1", "F"): 50, ("u2", "M"): 50, ("u3", "M"): 50, ("u1", "N"): 50, ("u2", "N"): 50,
     ("u3", "F"): 50, ("F", "N"): 50},
)
WEIGHTS = pd.Series({"x": 7.0})


def tables():
    r = run_case(*CASE)
    u = units_table(r)
    return u, systems_table(r, u), pd.DataFrame({"id": ["x"], "name": ["x"]})


def corr(*rows):
    return pd.DataFrame(rows, columns=["id", "kind", "unit_id", "unit_name", "target_id",
                                       "target_name", "reason"])


def test_join_moves_the_whole_system_and_keeps_the_entry_centrality():
    u, s, n = tables()
    assert len(s) == 3
    u2, s2, _, out = apply_corrections(u, s, n, corr(("C1", "join", "F", "F", "M", "M", "")),
                                       WEIGHTS)
    by = u2.set_index("id")
    assert out[0]["status"] == "applied" and out[0]["units_moved"] == 2
    assert by.loc["F", ["system_id", "role", "direct_step_id", "full_label", "chain"]].tolist() \
        == ["M", "merged_centre", "M", "M(F)", "F → M"]
    assert by.loc["u2", ["system_id", "full_label", "chain", "correction"]].tolist() \
        == ["M", "M(F)", "F → M", "C1"]
    assert by.loc["u1", "full_label"] == "M" and pd.isna(by.loc["u1", "correction"])
    row = s2.set_index("system_id").loc["M"]
    assert len(s2) == 2 and row.n_units == 4 and row.total_weight == 1330.0
    assert row.merged_centres_corrections == 1 and row.max_chain_length == 1


def test_join_is_already_satisfied_on_a_corrected_output():
    u, s, n = tables()
    c = corr(("C1", "join", "F", "F", "M", "M", ""))
    u2, s2, n2, _ = apply_corrections(u, s, n, c, WEIGHTS)
    _, s3, _, out = apply_corrections(u2.drop(columns="correction"),
                                      s2.drop(columns="merged_centres_corrections"), n2, c, WEIGHTS)
    assert out[0]["status"] == "already_satisfied" and len(s3) == 2


def test_join_of_a_unit_that_does_not_head_its_system_is_not_applicable():
    u, s, n = tables()
    _, s2, _, out = apply_corrections(
        u, s, n, corr(("C1", "join", "F", "F", "M", "M", ""), ("C2", "join", "F", "F", "N", "N", "")),
        WEIGHTS)
    assert [o["status"] for o in out] == ["applied", "not_applicable"]
    assert set(s2.system_id) == {"M", "N"}


def test_assign_puts_an_unassigned_unit_in_the_target_system():
    u, s, n = tables()
    u2, s2, n2, out = apply_corrections(u, s, n, corr(("C1", "assign", "x", "x", "F", "F", "")),
                                        WEIGHTS)
    by = u2.set_index("id")
    assert out[0]["status"] == "applied" and n2.empty
    assert by.loc["x", ["system_id", "full_label", "role", "correction"]].tolist() \
        == ["F", "F", "attracted", "C1"]
    row = s2.set_index("system_id").loc["F"]
    assert row.n_units == 3 and row.total_weight == 327.0


def test_target_must_be_a_centrality():
    u, s, n = tables()
    with pytest.raises(CorrectionError, match="not a centrality"):
        apply_corrections(u, s, n, corr(("C1", "join", "F", "F", "u1", "u1", "")), WEIGHTS)
