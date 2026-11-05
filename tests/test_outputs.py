import json

import yaml
from builders import make_inputs, run_case, scenario

from maps_slo.cli import main
from maps_slo.engine import run
from maps_slo.metrics import compute_metrics
from maps_slo.output import systems_table, units_table, write_outputs

CASE = (
    [("M", 1, 300000), ("u1", None, 1000), ("u2", None, 2000), ("far", None, 500)],
    [("M", "u1")],
    {("u1", "M"): 10, ("u2", "M"): 15, ("far", "M"): 75},
)


def test_I7_structural_metrics_without_comparison_data():
    r = run_case(*CASE)
    m = compute_metrics(r, units_table(r), systems_table(r))
    assert set(m) == {"V2", "V3", "V4", "V5", "V9", "V10"}


def test_V4_share_within_threshold():
    r = run_case(*CASE)
    m = compute_metrics(r, units_table(r), systems_table(r))
    assert m["V4"]["n_distant"] == 1
    assert abs(m["V4"]["weight_share_within"] - 303000 / 303500) < 1e-12


def test_V5_non_contiguous_system_is_listed():
    r = run_case(*CASE)
    m = compute_metrics(r, units_table(r), systems_table(r))
    assert m["V5"]["n_non_contiguous_systems"] == 1
    assert m["V5"]["cases"][0]["isolated_ids"] == ["far", "u2"]


def test_O5_outputs_written(tmp_path):
    r = run_case(*CASE)
    write_outputs(r, tmp_path, started_at="2026-11-05T10:00:00+00:00")
    for name in ("units", "systems", "distant", "unassigned"):
        assert (tmp_path / f"{name}.parquet").exists() and (tmp_path / f"{name}.csv").exists()
    assert (tmp_path / "metrics.json").exists()
    # O5: the scenario travels with the output
    sc = yaml.safe_load((tmp_path / "scenario.yaml").read_text(encoding="utf-8"))
    assert sc["name"] == "test-maps"


def test_R5_A10_O6_P2_manifest(tmp_path):
    r = run_case(*CASE)
    write_outputs(r, tmp_path, started_at="2026-11-05T10:00:00+00:00")
    m = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert m["package_version"] and "git_commit" in m
    assert set(m["inputs"]) == {"units", "contiguity", "travel_times"}
    assert m["reference_year"] == 2025
    assert m["thresholds_used"] == {"min_shared_share": 0.0309, "max_minutes": 20.0,
                                    "distant_minutes": 60.0}
    assert m["travel_times"]["description"] == "test matrix"
    assert {"phase2", "phase3", "phase4", "resolve", "core", "write_tables"} <= set(
        m["timings_seconds"])


def test_O6_two_matrices_are_distinguishable():
    units, contig, times = CASE
    r1 = run(scenario(), make_inputs(units, contig, times))
    r2 = run(scenario(), make_inputs(units, contig, {**times, ("u2", "M"): 16}))
    assert (r1.inputs.fingerprints()["travel_times"]
            != r2.inputs.fingerprints()["travel_times"])


def test_S7_distant_dataset(tmp_path):
    write_outputs(run_case(*CASE), tmp_path, started_at="x")
    import pandas as pd
    d = pd.read_csv(tmp_path / "distant.csv", dtype={"id": str})
    assert d.id.tolist() == ["far"] and d.system_id.tolist() == ["M"]


def test_cli_run(tmp_path):
    units, contig, times = CASE
    inp = make_inputs(units, contig, times)
    inp.units.to_csv(tmp_path / "units.csv", index=False)
    inp.contiguity.to_csv(tmp_path / "contiguity.csv", index=False)
    inp.times.to_csv(tmp_path / "times.csv", index=False)
    sc = scenario().model_dump(mode="json")
    sc["inputs"] = {"units": "units.csv", "contiguity": "contiguity.csv",
                    "travel_times": {"path": "times.csv", "description": "csv test"}}
    (tmp_path / "s.yaml").write_text(yaml.safe_dump(sc), encoding="utf-8")
    assert main(["run", str(tmp_path / "s.yaml"), "--out", str(tmp_path / "out")]) == 0
    m = json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))
    assert m["inputs"]["travel_times"].startswith("sha256:")
    assert "read_inputs" in m["timings_seconds"]


def test_V10_new_centre_is_the_resolved_centre_not_the_direct_claimant():
    # k heads a system with u; j claims k, but j is itself claimed by the heavier w
    r = run_case(
        [("k", 4, 10000), ("j", 6, 20000), ("w", 5, 30000), ("u", None, 100)],
        [("k", "j"), ("j", "w"), ("k", "u")],
        {("j", "k"): 5, ("j", "w"): 10, ("w", "j"): 5, ("u", "k"): 2,
         ("u", "j"): 50, ("u", "w"): 50, ("k", "w"): 50},
    )
    units = units_table(r).set_index("id")
    assert set(units.system_id) == {"w"}
    m = compute_metrics(r, units_table(r), systems_table(r))
    assert m["V10"]["cases"] == [
        {"previous_centre_id": "k", "new_centre_id": "w", "direct_claimant_id": "j"}]


def test_manifest_lists_unassigned_ids(tmp_path):
    r = run_case([("M", 1, 300000), ("zz", None, 10), ("aa", None, 10)], [], {})
    write_outputs(r, tmp_path, started_at="2026-11-05T10:00:00+00:00")
    m = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert m["counts"]["unassigned_ids"] == ["aa", "zz"]
    assert "metrics" in m["timings_seconds"]
