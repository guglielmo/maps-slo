"""Output tables (A1, "Output")."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
import yaml

from .engine import Result

UNIT_OUTPUT_COLUMNS = [
    "id", "name", "level", "missing", "direct_step_id", "system_id", "system_name",
    "full_label", "chain", "role", "minutes", "distant", "phase", "rule",
]
SYSTEM_OUTPUT_COLUMNS = [
    "system_id", "name", "main_centre_id", "main_centre_level", "n_units", "total_weight",
    "merged_centres_phase2", "merged_centres_phase4", "max_chain_length",
]


def units_table(r: Result) -> pd.DataFrame:
    """One row per unit present in the travel-time matrix, in declared id order."""
    p = r.problem
    rows = []
    assigned = sorted(np.flatnonzero(~r.unassigned).tolist(), key=lambda k: p.id_rank[k])
    for i in assigned:
        root, step, cen = int(r.roots[i]), int(r.ptr4[i]), bool(p.is_centrality[i])
        if cen and step == -1:
            role, full = "main_centre", p.names[root]
        elif cen:
            role, full = "merged_centre", f"{p.names[root]}({p.names[i]})"
        else:
            role = "attracted"
            full = p.names[root] if step == root else f"{p.names[root]}({p.names[step]})"
        chain_ids = r.paths[i] if cen else r.paths[i][1:]
        rows.append({
            "id": p.ids[i],
            "name": p.names[i],
            "level": int(p.level[i]) if p.level[i] >= 0 else None,
            "missing": p.missing[i],
            "direct_step_id": p.ids[step] if step >= 0 else None,
            "system_id": p.ids[root],
            "system_name": p.names[root],
            "full_label": full,
            "chain": " → ".join(p.names[k] for k in chain_ids),
            "role": role,
            "minutes": float(r.minutes[i]),
            "distant": bool(r.distant[i]),
            "phase": int(r.phase[i]),
            "rule": r.rule[i],
        })
    df = pd.DataFrame(rows, columns=UNIT_OUTPUT_COLUMNS)
    df["level"] = df["level"].astype("Int64")
    return df


def systems_table(r: Result, units: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per system. `max_chain_length` counts merge steps between centralities
    (attracted units are not counted: they do not add a step to the depth of their centrality)."""
    p = r.problem
    units = units_table(r) if units is None else units
    depth = {p.ids[i]: len(r.paths[i]) - 1 for i in np.flatnonzero(p.is_centrality)}
    rows = []
    for sid, g in units.groupby("system_id", sort=False):
        merged = g[g.role == "merged_centre"]
        head = p.index[sid]
        rows.append({
            "system_id": sid,
            "name": p.names[head],
            "main_centre_id": sid,
            "main_centre_level": int(p.level[head]),
            "n_units": len(g),
            "total_weight": float(sum(p.weight[p.index[x]] for x in g.id)),
            "merged_centres_phase2": int((merged.phase == 2).sum()),
            "merged_centres_phase4": int((merged.phase == 4).sum()),
            "max_chain_length": max(depth.get(x, 0) for x in g.id),
        })
    df = pd.DataFrame(rows, columns=SYSTEM_OUTPUT_COLUMNS)
    order = df.system_id.map(lambda x: p.id_rank[p.index[x]])
    return df.iloc[np.argsort(order.to_numpy(), kind="stable")].reset_index(drop=True)


def distant_table(units: pd.DataFrame) -> pd.DataFrame:
    """Criterion S7: distant units as a dataset of their own."""
    cols = ["id", "name", "system_id", "system_name", "minutes"]
    return units.loc[units.distant, cols].reset_index(drop=True)


def unassigned_table(r: Result) -> pd.DataFrame:
    """Criterion R6: units without travel times."""
    p = r.problem
    idx = sorted(np.flatnonzero(r.unassigned).tolist(), key=lambda k: p.id_rank[k])
    return pd.DataFrame({"id": [p.ids[i] for i in idx], "name": [p.names[i] for i in idx]})



def write_outputs(r: Result, out_dir, *, started_at: str, extra: dict | None = None) -> Path:
    from .manifest import build_manifest
    from .metrics import compute_metrics

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t = perf_counter()
    units = units_table(r)
    systems = systems_table(r, units)
    tables = {
        "units": units,
        "systems": systems,
        "distant": distant_table(units),
        "unassigned": unassigned_table(r),
    }
    for name, df in tables.items():
        df.to_parquet(out / f"{name}.parquet", index=False)
        df.to_csv(out / f"{name}.csv", index=False)
    r.timings["write_tables"] = perf_counter() - t
    t = perf_counter()
    metrics = compute_metrics(r, units, systems)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False),
                                      encoding="utf-8")
    (out / "scenario.yaml").write_text(
        yaml.safe_dump(r.scenario.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    r.timings["metrics"] = perf_counter() - t
    manifest = build_manifest(r, started_at=started_at, extra=extra)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
    return out
