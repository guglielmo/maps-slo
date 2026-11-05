"""Reconduct the contiguity file from 2021 to 2025 codes (decision D10, R6).

Borders do not change with a merger, so the 2025 contiguity is exact: for a 2025 unit N made
of parts P1..Pk (every code_2021 that maps to N, seat or not) the shared length with X is the
sum over the parts and over the neighbours that map to X; borders between parts of the same N
are dropped; the perimeter is the sum of the parts' perimeters minus twice the internal
borders (each counted once).

    python maps/prepare/reconduct_contiguity.py maps/data/contiguity-2025.parquet \
        maps/reference/fusions-2021-2025.csv maps/data/contiguity-2025-reconducted.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

COLUMNS = ["origin", "neighbour", "origin_name", "shared_length", "origin_perimeter"]


def reconduct_contiguity(df: pd.DataFrame, mapping: dict[str, str],
                         names: dict[str, str] | None = None) -> pd.DataFrame:
    """`mapping`: code_2021 -> code_2025 (codes not in it map to themselves).
    `names`: code -> name for the output; where missing the file's own name is kept."""
    def to25(s: pd.Series) -> pd.Series:
        return s.map(lambda c: mapping.get(c, c))

    d = df.assign(o=to25(df.origin), n=to25(df.neighbour))
    internal = d[(d.o == d.n) & (d.origin != d.neighbour)].copy()
    # each internal border once: unordered pair, mean of the directions present
    internal["a"] = internal[["origin", "neighbour"]].min(axis=1)
    internal["b"] = internal[["origin", "neighbour"]].max(axis=1)
    internal_len = (internal.groupby(["o", "a", "b"]).shared_length.mean()
                    .groupby("o").sum())
    parts = d.drop_duplicates("origin")
    perimeter = parts.groupby("o").origin_perimeter.sum()
    perimeter = perimeter - 2 * internal_len.reindex(perimeter.index, fill_value=0.0)
    external = d[d.o != d.n]
    out = (external.groupby(["o", "n"], as_index=False).shared_length.sum()
           .rename(columns={"o": "origin", "n": "neighbour"}))
    out["origin_perimeter"] = out.origin.map(perimeter)
    own = dict(zip(parts.o, parts.origin_name))
    names = {**own, **(names or {})}
    out["origin_name"] = out.origin.map(names)
    return out[COLUMNS].sort_values(["origin", "neighbour"]).reset_index(drop=True)


def internal_asymmetry(df: pd.DataFrame, mapping: dict[str, str]) -> tuple[int, int]:
    """(internal directed rows, internal rows whose reverse direction is missing or differs)."""
    m = df.assign(o=df.origin.map(lambda c: mapping.get(c, c)),
                  n=df.neighbour.map(lambda c: mapping.get(c, c)))
    m = m[(m.o == m.n) & (m.origin != m.neighbour)]
    rev = m.set_index(["origin", "neighbour"]).shared_length
    bad = sum(1 for (a, b), v in rev.items()
              if (b, a) not in rev.index or abs(rev[(b, a)] - v) > 1e-9 * max(1.0, abs(v)))
    return len(m), bad


def read_mapping(path: Path) -> dict[str, str]:
    f = pd.read_csv(path, dtype=str).fillna("")
    return {a: b for a, b in zip(f.code_2021, f.code_2025) if b}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("contiguity", type=Path)
    ap.add_argument("fusions", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--population", type=Path,
                    default=Path(__file__).parents[1] / "data" / "population-2025.csv")
    a = ap.parse_args()
    df = pd.read_parquet(a.contiguity)
    mapping = read_mapping(a.fusions)
    pop = pd.read_csv(a.population, dtype={"id": str, "name": str}, keep_default_na=False)
    pop = pop[pop.name != ""]  # a missing name keeps the one of the contiguity file
    out = reconduct_contiguity(df, mapping, dict(zip(pop.id, pop.name)))
    n_int, n_bad = internal_asymmetry(df, mapping)
    out.to_parquet(a.out, index=False)
    print(f"rows {len(df)} -> {len(out)}; internal directed rows {n_int}, "
          f"asymmetric {n_bad}; written {a.out}")


if __name__ == "__main__":
    main()
