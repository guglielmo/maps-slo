import numpy as np
import pytest

from maps_slo.labels import ChainError, resolve


def test_A4_chain_resolves_to_the_root():
    # 3 -> 2 -> 1 -> 0, 0 is a root
    roots, paths = resolve(np.array([-1, 0, 1, 2]), max_chain_length=16)
    assert roots.tolist() == [0, 0, 0, 0]
    assert paths[3] == [3, 2, 1, 0]


def test_A9_cycle_raises():
    with pytest.raises(ChainError, match="cycle"):
        resolve(np.array([1, 0]), max_chain_length=16, ids=np.array(["a", "b"], dtype=object))


def test_A9_chain_longer_than_declared_raises():
    with pytest.raises(ChainError, match="max_chain_length=2"):
        resolve(np.array([-1, 0, 1, 2]), max_chain_length=2)


@pytest.mark.parametrize("bad", [[-2, -1], [2, -1], [0, 5]])
def test_resolve_rejects_out_of_range_pointers(bad):
    with pytest.raises(ValueError, match="pointer"):
        resolve(np.array(bad), max_chain_length=16)
