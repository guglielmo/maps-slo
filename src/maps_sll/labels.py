"""Recursive resolution of the attraction label (A1, "Che cosa significa «unita»")."""

from __future__ import annotations

import numpy as np


class ChainError(RuntimeError):
    """A cycle, or a chain longer than the scenario allows (criterion A9)."""


def resolve(
    pointers: np.ndarray, max_chain_length: int, ids: np.ndarray | None = None
) -> tuple[np.ndarray, list[list[int]]]:
    """Follow every pointer to a unit without outgoing pointer.

    Returns the root of every unit and the path from the unit to its root, both ends included.
    """

    def name(k: int) -> str:
        return str(ids[k]) if ids is not None else str(k)

    n = len(pointers)
    if n and (pointers.min() < -1 or pointers.max() >= n):
        raise ValueError(f"pointers must lie in [-1, {n}): found out-of-range values")
    roots = np.empty(n, dtype=np.int64)
    paths: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        path = [i]
        seen = {i}
        cur = i
        while pointers[cur] != -1:
            cur = int(pointers[cur])
            if cur in seen:
                raise ChainError(
                    "cycle in the attraction chain: " + " → ".join(name(k) for k in path + [cur])
                )
            path.append(cur)
            seen.add(cur)
            if len(path) - 1 > max_chain_length:
                raise ChainError(
                    f"attraction chain longer than max_chain_length={max_chain_length}: "
                    + " → ".join(name(k) for k in path)
                )
        roots[i] = cur
        paths[i] = path
    return roots, paths
