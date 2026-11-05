"""The problem in array form: every unit has a position, every relation an index."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc

from .inputs import CONTIGUITY_COLUMNS, TIMES_COLUMNS, UNIT_COLUMNS, Inputs
from .scenario import Scenario

SHARE_TOLERANCE = 1e-6


class InputError(ValueError):
    """Inputs inconsistent with each other or with the scenario."""


@dataclass
class Problem:
    ids: np.ndarray  # object, str
    names: np.ndarray  # object, str
    level: np.ndarray  # int64, -1 = non-centrality
    strength: np.ndarray  # int64, position in scenario.levels, -1 = non-centrality
    weight: np.ndarray  # float64
    id_rank: np.ndarray  # int64, 0 = first in the declared order
    missing: np.ndarray  # object, passed through to the output
    times: np.ndarray  # float64 n x n, row = origin (the unit that joins), NaN = no time
    neighbours: list[list[tuple[int, float]]]  # (j, shared length / perimeter of i)
    index: dict[str, int]

    @property
    def n(self) -> int:
        return len(self.ids)

    @property
    def is_centrality(self) -> np.ndarray:
        return self.level >= 0

    def is_relevant(self, a: int, b: int, share: float, scenario: Scenario) -> bool:
        """Relevant contiguity (A1, "Contiguità rilevante"): share on the perimeter of `a`,
        time from `a` to `b`; both thresholds strict (decision D15)."""
        t = self.times[a, b]
        return bool(
            share > scenario.contiguity.min_shared_share and t < scenario.contiguity.max_minutes
        )


def build_problem(inputs: Inputs, scenario: Scenario) -> Problem:
    u = inputs.units
    _require(u, UNIT_COLUMNS, "units")
    _require(inputs.contiguity, CONTIGUITY_COLUMNS, "contiguity")
    _require(inputs.times, TIMES_COLUMNS, "travel times")

    for df, cols, what in (
        (u, ["id"], "units"),
        (inputs.contiguity, ["origin", "neighbour"], "contiguity"),
        (inputs.times, ["origin", "destination"], "travel times"),
    ):
        for col in cols:
            if pd.api.types.is_float_dtype(df[col].dtype):
                raise InputError(
                    f"{what}: column {col!r} has float ids; ids must be strings or integers"
                )
    if u["id"].isna().any():
        raise InputError("unit ids must not be missing")

    ids = u["id"].astype(str).to_numpy(dtype=object)
    if len(set(ids)) != len(ids):
        dup = pd.Series(ids)[pd.Series(ids).duplicated()].unique()[:5]
        raise InputError(f"duplicate unit ids: {list(dup)}")
    n = len(ids)
    index = {uid: i for i, uid in enumerate(ids)}

    lv_num = pd.to_numeric(u["level"])
    frac = lv_num.dropna()
    if (frac != np.floor(frac.to_numpy(dtype=np.float64))).any():
        raise InputError("levels must be integers")
    lv = lv_num.astype("Int64")
    has = lv.notna().to_numpy()
    level = np.where(has, lv.fillna(-1).to_numpy(dtype=np.int64), -1)
    undeclared = sorted(set(level[has].tolist()) - set(scenario.levels))
    if undeclared:
        raise InputError(f"levels {undeclared} are not declared in the scenario")
    strength = np.array(
        [scenario.strength(int(x)) if x >= 0 else -1 for x in level], dtype=np.int64
    )

    weight = pd.to_numeric(u["weight"]).to_numpy(dtype=np.float64, na_value=np.nan)
    if np.isnan(weight).any():
        raise InputError("every unit needs a weight")
    if not (np.isfinite(weight).all() and (weight >= 0).all()):
        raise InputError("weights must be finite and >= 0")

    names = u["name"].astype(str).to_numpy(dtype=object)
    missing = (
        u["missing"].astype(object).where(u["missing"].notna(), None).to_numpy(dtype=object)
        if "missing" in u
        else np.full(n, None, dtype=object)
    )

    id_values = pa.array(list(ids), type=pa.string())

    c = inputs.contiguity
    o = _codes(c["origin"], id_values, "contiguity origin")
    nb = _codes(c["neighbour"], id_values, "contiguity neighbour")
    length = pd.to_numeric(c["shared_length"]).to_numpy(np.float64, na_value=np.nan)
    perimeter = pd.to_numeric(c["origin_perimeter"]).to_numpy(np.float64, na_value=np.nan)
    if not (np.isfinite(perimeter).all() and (perimeter > 0).all()):
        raise InputError("contiguity: origin_perimeter must be finite and > 0")
    if not (np.isfinite(length).all() and (length >= 0).all()):
        raise InputError("contiguity: shared_length must be finite and >= 0")
    # Relative tolerance: in the GSSI data a single neighbour can share the whole perimeter
    # and exceed it in the sixth decimal place (coastal and border municipalities).
    if (length > perimeter * (1 + SHARE_TOLERANCE)).any():
        raise InputError("contiguity: shared_length greater than origin_perimeter")
    length = np.minimum(length, perimeter)
    per_origin = pd.Series(perimeter).groupby(o).nunique()
    if (per_origin > 1).any():
        bad = [ids[i] for i in per_origin[per_origin > 1].index[:5]]
        raise InputError(f"contiguity: origin_perimeter differs across rows of origins {bad}")
    share = length / perimeter
    _reject_duplicate_pairs(o, nb, n, ids, "contiguity")
    id_rank = _id_rank(ids, scenario)
    neighbours: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    for a, b, s_ in zip(o.tolist(), nb.tolist(), share.tolist()):
        if a != b:
            neighbours[a].append((b, s_))
    for lst in neighbours:
        lst.sort(key=lambda e: id_rank[e[0]])

    t = inputs.times
    to = _codes(t["origin"], id_values, "travel-time origin")
    td = _codes(t["destination"], id_values, "travel-time destination")
    minutes = t["minutes"].to_numpy(dtype=np.float64, na_value=np.nan)
    if (minutes < 0).any():
        raise InputError("negative travel times")
    _reject_duplicate_pairs(to, td, n, ids, "travel times")
    times = np.full((n, n), np.nan, dtype=np.float64)
    times[to, td] = minutes
    np.fill_diagonal(times, 0.0)

    return Problem(
        ids=ids,
        names=names,
        level=level,
        strength=strength,
        weight=weight,
        id_rank=id_rank,
        missing=missing,
        times=times,
        neighbours=neighbours,
        index=index,
    )


def _reject_duplicate_pairs(
    a: np.ndarray, b: np.ndarray, n: int, ids: np.ndarray, what: str
) -> None:
    keys = a * n + b
    uniq, counts = np.unique(keys, return_counts=True)
    dup = uniq[counts > 1][:5]
    if len(dup):
        pairs = [(str(ids[k // n]), str(ids[k % n])) for k in dup.tolist()]
        raise InputError(f"{what}: duplicate (origin, destination) pairs: {pairs}")


def _require(df: pd.DataFrame, cols: list[str], what: str) -> None:
    absent = [c for c in cols if c not in df.columns]
    if absent:
        raise InputError(f"{what}: missing columns {absent}")


def _codes(col: pd.Series, id_values: pa.Array, what: str) -> np.ndarray:
    arr = pa.array(col.astype(str) if col.dtype.kind in "iuf" else col).cast(pa.string())
    idx = pc.index_in(arr, value_set=id_values)
    if idx.null_count:
        unknown = pc.unique(pc.filter(arr, pc.is_null(idx))).to_pylist()[:5]
        raise InputError(f"{what}: ids not among the units: {unknown}")
    return idx.to_numpy(zero_copy_only=False).astype(np.int64)


def _id_rank(ids: np.ndarray, scenario: Scenario) -> np.ndarray:
    if scenario.id_order == "lexicographic":
        keys = list(ids)
    elif scenario.id_order == "numeric":
        keys = []
        for x in ids:
            try:
                keys.append(int(x))
            except ValueError:
                raise InputError(f"id_order is numeric but id {x!r} is not an integer") from None
        if len(set(keys)) != len(keys):
            raise InputError("id_order is numeric but two ids have the same numeric key")
    else:
        pos = {k: i for i, k in enumerate(scenario.id_order_list or [])}
        absent = [x for x in ids if x not in pos]
        if absent:
            raise InputError(f"ids absent from id_order_list: {absent[:5]}")
        keys = [pos[x] for x in ids]
    order = sorted(range(len(ids)), key=lambda i: keys[i])
    rank = np.empty(len(ids), dtype=np.int64)
    rank[order] = np.arange(len(ids))
    return rank
