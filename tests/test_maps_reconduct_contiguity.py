import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "maps" / "prepare"))
from reconduct_contiguity import reconduct_contiguity


def toy():
    # A (perimeter 10) and B (perimeter 8) merge into N; both border X (perimeter 20);
    # A-B internal border of 2 (both directions present)
    rows = [("A", "B", 2.0, 10.0), ("B", "A", 2.0, 8.0),
            ("A", "X", 3.0, 10.0), ("B", "X", 4.0, 8.0),
            ("X", "A", 3.0, 20.0), ("X", "B", 4.0, 20.0)]
    return pd.DataFrame(rows, columns=["origin", "neighbour", "shared_length",
                                       "origin_perimeter"]).assign(origin_name="old")


def test_merge_sums_shares_drops_internal_and_fixes_perimeter():
    out = reconduct_contiguity(toy(), {"A": "N", "B": "N"}, {"N": "New", "X": "Ex"})
    got = out.set_index(["origin", "neighbour"])
    assert set(got.index) == {("N", "X"), ("X", "N")}
    assert got.loc[("N", "X"), "shared_length"] == pytest.approx(7.0)
    assert got.loc[("X", "N"), "shared_length"] == pytest.approx(7.0)
    assert got.loc[("N", "X"), "origin_perimeter"] == pytest.approx(10 + 8 - 2 * 2.0)
    assert got.loc[("X", "N"), "origin_perimeter"] == pytest.approx(20.0)
    assert got.loc[("N", "X"), "origin_name"] == "New"


def test_pairs_are_symmetric_and_unmapped_codes_are_kept():
    out = reconduct_contiguity(toy(), {"A": "N", "B": "N"})
    pairs = set(zip(out.origin, out.neighbour))
    assert pairs == {(b, a) for a, b in pairs}
    out2 = reconduct_contiguity(toy(), {})
    assert len(out2) == 6
