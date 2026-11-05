"""Checks on a national run (criteria C1, S1, S5, S6, S8, O2, O3, R1, R6, P1, P2, P3).

    python maps/checks.py output/maps-2025 maps/data/units-2025.parquet \
        [--reference-run output/maps-2025-bis] [--variant-run output/maps-2025-d30]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

P1_LIMIT_SECONDS = 600  # decision D20


def check(run_dir: Path, units_input: Path, reference: Path | None,
          variant: Path | None = None) -> dict:
    units = pd.read_parquet(run_dir / "units.parquet")
    systems = pd.read_parquet(run_dir / "systems.parquet")
    unassigned = pd.read_parquet(run_dir / "unassigned.parquet")
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    weight = pd.read_parquet(units_input, columns=["id", "weight"]).set_index("id").weight
    levels = set(manifest["scenario"]["levels"])
    timings = manifest["timings_seconds"]
    total = sum(v for k, v in timings.items() if k != "core")
    heads = units.set_index("id").loc[systems.system_id]
    recomputed = units.assign(w=units.id.map(weight)).groupby("system_id").w.sum()
    res = {
        "C1": bool(units.level.dropna().astype(int).isin(levels).all()),
        "S1": bool(units[units.level.isna()].direct_step_id.notna().all()),
        "S5": {"n_distant": int(units.distant.sum()),
               "distant_all_assigned": bool(units[units.distant].system_id.notna().all())},
        "S8": bool((heads.role == "main_centre").all()),
        "O2": bool(units.id.is_unique),
        "O3": bool(np.allclose(systems.set_index("system_id").total_weight.sort_index(),
                               recomputed.sort_index())),
        "R6": {"units_without_times": unassigned.id.tolist(),
               "reconducted": len(manifest.get("extra", {}).get("travel_time_reconduction", {})
                                  .get("reconducted", []))},
        "P1": {"total_seconds": round(total, 2), "limit": P1_LIMIT_SECONDS,
               "ok": total <= P1_LIMIT_SECONDS},
        "P2": {k: round(v, 3) for k, v in timings.items()},
    }
    if reference is not None:  # R1: same scenario, same data, identical tables
        res["R1"] = all(
            pd.read_parquet(run_dir / f"{t}.parquet").equals(
                pd.read_parquet(reference / f"{t}.parquet"))
            for t in ("units", "systems", "distant", "unassigned")
        )
    if variant is not None:  # S6, P3: only distant_minutes changes; times are only read
        other = pd.read_parquet(variant / "units.parquet")
        vt = json.loads((variant / "manifest.json").read_text(encoding="utf-8"))
        res["S6"] = {"same_assignment": bool(units.system_id.equals(other.system_id)),
                     "n_distant": [int(units.distant.sum()), int(other.distant.sum())]}
        # P3 is verified by reading the code (tools/criteria.yaml); here only the timings.
        res["P3"] = {"variant_seconds": round(sum(v for k, v in vt["timings_seconds"].items()
                                                  if k != "core"), 2)}
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("units_input", type=Path)
    ap.add_argument("--reference-run", type=Path)
    ap.add_argument("--variant-run", type=Path, help="same scenario, other distant_minutes")
    a = ap.parse_args()
    res = check(a.run_dir, a.units_input, a.reference_run, a.variant_run)
    (a.run_dir / "checks.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
