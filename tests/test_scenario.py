import pytest
from builders import MAPS, scenario

from maps_slo.scenario import load_scenario


def test_maps_scenario_is_valid():
    sc = scenario()
    assert sc.strength(1) == 0 and sc.strength(6) == 5


def test_A6_invariant_rejects_pair_toward_weaker_level():
    with pytest.raises(ValueError, match="invariant"):
        scenario(phase2_pairs={2: [3]})


def test_A6_invariant_rejects_pair_between_equal_levels():
    with pytest.raises(ValueError, match="invariant"):
        scenario(phase2_pairs={4: [4]})


def test_I2_levels_are_a_parameter():
    sc = scenario(levels=[1, 2, 3, 4, 5, 6, 7], phase2_pairs={**MAPS["phase2_pairs"], 7: [1, 2, 3]})
    assert sc.strength(7) == 6


def test_unknown_level_in_phase4_levels_rejected():
    with pytest.raises(ValueError, match="phase4_levels"):
        scenario(phase4_levels=[9])


def test_explicit_order_requires_list():
    with pytest.raises(ValueError, match="id_order_list"):
        scenario(id_order="explicit")


def test_load_scenario_from_yaml(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(
        "name: x\nreference_year: 2025\nlevels: [1, 2]\nphase2_pairs: {2: [1]}\n"
        "phase4_levels: [2]\ncontiguity: {min_shared_share: 0.03, max_minutes: 20}\n"
        "distant_minutes: 60\n",
        encoding="utf-8",
    )
    sc = load_scenario(p)
    assert sc.phase2_pairs == {2: [1]} and sc.id_order == "lexicographic"


def test_empty_levels_rejected():
    with pytest.raises(ValueError, match="levels"):
        scenario(levels=[], phase2_pairs={}, phase4_levels=[])


@pytest.mark.parametrize(
    "over",
    [
        {"contiguity": {"min_shared_share": -0.1, "max_minutes": 20}},
        {"contiguity": {"min_shared_share": float("nan"), "max_minutes": 20}},
        {"contiguity": {"min_shared_share": 0.1, "max_minutes": -1}},
        {"contiguity": {"min_shared_share": 0.1, "max_minutes": float("nan")}},
        {"distant_minutes": -1},
        {"distant_minutes": float("nan")},
    ],
)
def test_negative_or_nan_thresholds_rejected(over):
    with pytest.raises(ValueError):
        scenario(**over)


def test_duplicate_id_order_list_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        scenario(id_order="explicit", id_order_list=["a", "a"])


def test_id_order_list_requires_explicit_order():
    with pytest.raises(ValueError, match="explicit"):
        scenario(id_order="lexicographic", id_order_list=["a"])


@pytest.mark.parametrize("v", [True, 2.5])
def test_max_chain_length_strict_int(v):
    with pytest.raises(ValueError):
        scenario(max_chain_length=v)
