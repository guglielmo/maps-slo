from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from builders import make_inputs, scenario

from maps_slo.engine import run
from maps_slo.levels import LevelsError, Rule, RuleSet, assign_levels, load_rules
from maps_slo.output import units_table

RULES = load_rules(Path(__file__).parents[1] / "maps" / "levels" / "maps-rules.yaml")
NONE = {"n_health": 0, "n_dea": 0, "n_secondary_schools": 0, "station_category": None}
ALL = {"n_health": 2, "n_dea": 1, "n_secondary_schools": 3, "station_category": "gold"}


def levels(rows, rules=RULES):
    df = pd.DataFrame([{"id": k, **v} for k, v in rows.items()])
    return assign_levels(df, rules).set_index("id")


def test_C2_population_boundaries_fall_in_the_upper_class():
    out = levels({
        "a": {"population": 250000, **NONE}, "b": {"population": 249999, **NONE},
        "c": {"population": 100000, **NONE}, "d": {"population": 50000, **NONE},
        "e": {"population": 49999, **NONE},
    })
    assert out.level.tolist()[:4] == [1, 2, 2, 3] and pd.isna(out.level["e"])


def test_C2_sixty_thousand_with_all_services_is_level_3():
    assert levels({"a": {"population": 60000, **ALL}}).level["a"] == 3


def test_C5_dea_two_schools_silver_is_level_4():
    row = {"population": 20000, "n_health": 1, "n_dea": 1, "n_secondary_schools": 2,
           "station_category": "silver"}
    assert levels({"a": row}).level["a"] == 4


def test_C5_dea_two_schools_bronze_is_level_5():
    row = {"population": 20000, "n_health": 1, "n_dea": 1, "n_secondary_schools": 2,
           "station_category": "bronze"}
    assert levels({"a": row}).level["a"] == 5


def test_C5_dea_one_school_silver_is_level_5():
    row = {"population": 20000, "n_health": 1, "n_dea": 1, "n_secondary_schools": 1,
           "station_category": "silver"}
    assert levels({"a": row}).level["a"] == 5


def test_C6_level_6_records_the_missing_service():
    base = {"population": 8000, "n_dea": 0}
    out = levels({
        "nostation": {**base, "n_health": 1, "n_secondary_schools": 1, "station_category": None},
        "nohealth": {**base, "n_health": 0, "n_secondary_schools": 1, "station_category": "bronze"},
        "noschool": {**base, "n_health": 1, "n_secondary_schools": 0, "station_category": "bronze"},
    })
    assert out.level.tolist() == [6, 6, 6]
    assert out.missing.to_dict() == {"nostation": "station", "nohealth": "health",
                                     "noschool": "school"}


def test_C1_every_unit_receives_exactly_one_class():
    rng = np.random.default_rng(1)
    cats = [None, "bronze", "silver", "gold", "platinum"]
    rows = {f"u{i}": {"population": int(rng.integers(100, 400000)),
                      "n_health": int(rng.integers(0, 3)), "n_dea": int(rng.integers(0, 2)),
                      "n_secondary_schools": int(rng.integers(0, 4)),
                      "station_category": cats[int(rng.integers(0, 5))]} for i in range(500)}
    out = levels(rows)
    assert len(out) == 500 and out.index.is_unique
    assert set(out.level.dropna().astype(int)) <= {1, 2, 3, 4, 5, 6}


def test_C3_rule_is_recorded():
    out = levels({"a": {"population": 300000, **NONE}, "b": {"population": 10, **NONE}})
    assert out.rule_id["a"] == "L1" and out.rule_id["b"] is None


def test_C4_rules_are_data():
    changed = RULES.model_copy(deep=True)
    changed.rules[2].all_[0].value = 55000
    row = {"a": {"population": 52000, **NONE}}
    assert levels(row).level["a"] == 3 and pd.isna(levels(row, changed).level["a"])


def test_I5_new_dimension_without_engine_changes():
    rules = RuleSet.model_validate({"rules": [
        {"id": "C1", "level": 1, "all": [{"attr": "n_cinemas", "op": ">=", "value": 3}]},
    ]})
    lv = levels({"a": {"n_cinemas": 5}, "u": {"n_cinemas": 0}}, rules)
    units = [("a", int(lv.level["a"]), 1000), ("u", None, 10)]
    r = run(scenario(levels=[1], phase2_pairs={}, phase4_levels=[]),
            make_inputs(units, times={("u", "a"): 5}))
    assert units_table(r).set_index("id").system_id["u"] == "a"


def test_unknown_attribute_is_an_error():
    rules = RuleSet.model_validate({"rules": [
        {"id": "X", "level": 1, "all": [{"attr": "nope", "op": ">=", "value": 1}]}]})
    with pytest.raises(LevelsError, match="nope"):
        levels({"a": {"population": 1}}, rules)


def test_rule_needs_exactly_one_form():
    with pytest.raises(ValueError):
        Rule.model_validate({"id": "X", "level": 1})


def test_R5_levels_run_writes_its_own_manifest(tmp_path):
    import json

    from maps_slo.levels import assign_levels_file
    attrs = tmp_path / "attrs.csv"
    pd.DataFrame([{"id": "a", "population": 300000, **NONE},
                  {"id": "b", "population": 10, **NONE}]).to_csv(attrs, index=False)
    rules = Path(__file__).parents[1] / "maps" / "levels" / "maps-rules.yaml"
    out = tmp_path / "levels.csv"
    assign_levels_file(rules, attrs, out)
    m = json.loads((tmp_path / "levels.csv.manifest.json").read_text(encoding="utf-8"))
    assert m["step"] == "levels"
    assert m["rules"]["fingerprint"].startswith("sha256:")
    assert m["attributes"]["fingerprint"].startswith("sha256:")
    assert m["counts"] == {"units": 2, "by_level": {"1": 1}, "without_level": 1,
                           "incomplete": 0, "by_rule": {"L1": 1}}
    assert m["git_commit"] and m["package_version"]


def test_missing_population_with_all_services_is_incomplete_not_level_4():
    out = levels({"a": {"population": np.nan, **ALL}})
    assert pd.isna(out.level["a"]) and out.rule_id["a"] == "INCOMPLETE"
    assert out.incomplete_attrs["a"] == "population"


def test_missing_health_is_incomplete_not_level_6():
    out = levels({"a": {"population": 8000, "n_dea": 0, "n_health": np.nan,
                        "n_secondary_schools": 1, "station_category": "bronze"}})
    assert pd.isna(out.level["a"]) and out.rule_id["a"] == "INCOMPLETE"
    assert out.incomplete_attrs["a"] == "n_health"


def test_missing_datum_after_a_deciding_rule_does_not_matter():
    out = levels({"a": {"population": 300000, "n_dea": 0, "n_health": np.nan,
                        "n_secondary_schools": 0, "station_category": None}})
    assert out.level["a"] == 1 and out.rule_id["a"] == "L1"


def test_missing_datum_that_cannot_change_the_outcome_is_not_incomplete():
    # L5 needs school>=1 (false); L6 needs two of three and only health is unknown
    out = levels({"a": {"population": 8000, "n_dea": 0, "n_health": np.nan,
                        "n_secondary_schools": 0, "station_category": None}})
    assert pd.isna(out.level["a"]) and out.rule_id["a"] is None
    assert out.incomplete_attrs["a"] is None


def test_ordinal_values_are_stripped_and_unknown_values_are_errors():
    row = {"population": 20000, "n_health": 1, "n_dea": 1, "n_secondary_schools": 2}
    assert levels({"a": {**row, "station_category": "Silver "}}).level["a"] == 4
    with pytest.raises(LevelsError, match="argento"):
        levels({"a": {**row, "station_category": "argento"}})


def test_ordinal_na_or_empty_means_absent_not_unknown():
    row = {"population": 8000, "n_dea": 0, "n_health": 1, "n_secondary_schools": 1}
    out = levels({"a": {**row, "station_category": None}, "b": {**row, "station_category": " "}})
    assert out.level.tolist() == [6, 6] and set(out.missing) == {"station"}



def test_C4_rule_with_both_forms_or_partial_form_is_rejected():
    p = {"attr": "population", "op": ">=", "value": 1}
    for bad in ({"all": [p], "exactly": 2}, {"all": [p], "of": [p]}, {"exactly": 1},
                {"all": []}, {"exactly": 1, "of": []}):
        with pytest.raises(ValueError):
            Rule.model_validate({"id": "X", "level": 1, **bad})


def test_I1_phase1_rejects_duplicate_and_missing_ids():
    with pytest.raises(LevelsError, match="duplicate"):
        assign_levels(pd.DataFrame([{"id": "a", "population": 1, **NONE},
                                    {"id": "a", "population": 2, **NONE}]), RULES)
    with pytest.raises(LevelsError, match="missing"):
        assign_levels(pd.DataFrame([{"id": None, "population": 1, **NONE}]), RULES)


def test_I1_phase1_csv_keeps_na_like_ids(tmp_path):
    from maps_slo.levels import assign_levels_file
    src = tmp_path / "attrs.csv"
    src.write_text("id,population,n_health,n_dea,n_secondary_schools,station_category\n"
                   "NA,300000,0,0,0,\nNone,10,NA,0,1,bronze\n", encoding="utf-8")
    rules = Path(__file__).parents[1] / "maps" / "levels" / "maps-rules.yaml"
    out = assign_levels_file(rules, src, tmp_path / "levels.csv")
    assert out.id.tolist() == ["NA", "None"]
    assert out.level.iloc[0] == 1 and out.rule_id.iloc[1] == "INCOMPLETE"
