"""Downstream corrections of a run (decision D18): a versioned list applied after the algorithm.

    python maps/corrections.py output/maps-2025 maps/reference/corrections.csv \
        maps/data/units-2025.parquet --out output/maps-2025-corrected

The corrections are outside the algorithm: Italian special cases that a library meant to be
reused elsewhere must not know. They are applied after every run, whatever systems come out,
so the list names municipalities, never system ids, and each run resolves them on its own
output. Two kinds:

- `join`: the system headed by `unit_id` joins the system that contains `target_id`;
  `unit_id` becomes a merged centre pointing to `target_id`. If `unit_id` is already in
  that system the correction is `already_satisfied`; if `unit_id` does not head its
  system it is `not_applicable` (moving it would drag another centre's system), reported
  and skipped, or an error with `--strict`.
- `assign`: an unassigned unit (no travel times) joins the system that contains `target_id`.

Corrections apply in file order, each on the state left by the previous ones. The output
directory holds the four tables with a `correction` column (id of the correction that moved
the unit), the files of the run copied unchanged (manifest, scenario, metrics of the
algorithm), and `corrections.json` with the outcome of every correction: the number of
corrections applied is the measure of how well the automatic part works (D18).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd

TABLES = ("units", "systems", "distant", "unassigned")
ARROW = " → "


class CorrectionError(ValueError):
    pass


def _relabel(full_label: str, old_root: str, new_root: str) -> str:
    """`X` → `R(X)`; `X(Z)` → `R(Z)`: the parenthesis keeps the centrality of entry."""
    if full_label == old_root:
        return f"{new_root}({old_root})"
    inner = full_label[len(old_root) + 1:-1]
    return f"{new_root}({inner})"


def _depth(chain: str) -> int:
    return chain.count(ARROW)


def _refresh_system(units: pd.DataFrame, systems: pd.DataFrame, sid: str) -> None:
    g = units[units.system_id == sid]
    cen = g[g.role != "attracted"]
    i = systems.index[systems.system_id == sid][0]
    systems.loc[i, "n_units"] = len(g)
    systems.loc[i, "max_chain_length"] = int(cen.chain.map(_depth).max())


def apply_corrections(units: pd.DataFrame, systems: pd.DataFrame, unassigned: pd.DataFrame,
                      corrections: pd.DataFrame, weights: pd.Series,
                      ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict]]:
    units = units.copy()
    systems = systems.copy()
    unassigned = unassigned.copy()
    units["correction"] = pd.Series([None] * len(units), dtype="object")
    systems["merged_centres_corrections"] = 0
    outcomes = []
    for c in corrections.itertuples(index=False):
        rec = {"id": c.id, "kind": c.kind, "unit_id": c.unit_id, "unit_name": c.unit_name,
               "target_id": c.target_id, "target_name": c.target_name, "reason": c.reason}
        tgt = units[units.id == c.target_id]
        if tgt.empty:
            raise CorrectionError(f"{c.id}: target {c.target_id} is not an assigned unit")
        tgt = tgt.iloc[0]
        if tgt.role == "attracted":
            raise CorrectionError(f"{c.id}: target {c.target_id} is not a centrality")
        sy, root = tgt.system_id, tgt.system_name
        rec["to_system"] = sy
        if c.kind == "join":
            row = units[units.id == c.unit_id]
            if row.empty:
                raise CorrectionError(f"{c.id}: unit {c.unit_id} is not an assigned unit")
            row = row.iloc[0]
            sx = row.system_id
            rec["from_system"] = sx
            if sx == sy:
                rec.update(status="already_satisfied", units_moved=0)
            elif row.role != "main_centre":
                rec.update(status="not_applicable", units_moved=0,
                           note=f"{c.unit_id} does not head its system ({row.system_name})")
            else:
                moved = units.system_id == sx
                old_root = row.system_name
                units.loc[moved, "full_label"] = units.loc[moved, "full_label"].map(
                    lambda s, o=old_root, r=root: _relabel(s, o, r))
                units.loc[moved, "chain"] = units.loc[moved, "chain"] + ARROW + tgt.chain
                units.loc[moved, ["system_id", "system_name", "correction"]] = [sy, root, c.id]
                i = units.index[units.id == c.unit_id][0]
                units.loc[i, ["role", "direct_step_id"]] = ["merged_centre", c.target_id]
                sxr = systems[systems.system_id == sx].iloc[0]
                j = systems.index[systems.system_id == sy][0]
                systems.loc[j, "total_weight"] += sxr.total_weight
                for col in ("merged_centres_phase2", "merged_centres_phase4",
                            "merged_centres_corrections"):
                    systems.loc[j, col] += sxr[col]
                systems.loc[j, "merged_centres_corrections"] += 1
                systems = systems[systems.system_id != sx]
                _refresh_system(units, systems, sy)
                rec.update(status="applied", units_moved=int(moved.sum()))
        elif c.kind == "assign":
            if c.unit_id not in set(unassigned.id):
                row = units[units.id == c.unit_id]
                if row.empty:
                    raise CorrectionError(f"{c.id}: unit {c.unit_id} is in no table of the run")
                status = "already_satisfied" if row.iloc[0].system_id == sy else "not_applicable"
                rec.update(status=status, units_moved=0, from_system=row.iloc[0].system_id)
            else:
                name = unassigned.loc[unassigned.id == c.unit_id, "name"].iloc[0]
                new = {col: None for col in units.columns}
                new.update(id=c.unit_id, name=name, direct_step_id=c.target_id, system_id=sy,
                           system_name=root,
                           full_label=root if c.target_id == sy else f"{root}({tgt['name']})",
                           chain=tgt.chain, role="attracted", distant=False, correction=c.id)
                units = pd.concat([units, pd.DataFrame([new])], ignore_index=True)
                unassigned = unassigned[unassigned.id != c.unit_id]
                j = systems.index[systems.system_id == sy][0]
                systems.loc[j, "total_weight"] += float(weights[c.unit_id])
                _refresh_system(units, systems, sy)
                rec.update(status="applied", units_moved=1, from_system=None)
        else:
            raise CorrectionError(f"{c.id}: unknown kind {c.kind!r} (join or assign)")
        outcomes.append(rec)
    units = units.sort_values("id", kind="stable").reset_index(drop=True)
    for col in ("level", "phase"):
        units[col] = units[col].astype("Int64")
    units["distant"] = units["distant"].astype(bool)
    systems = systems.reset_index(drop=True)
    return units, systems, unassigned.reset_index(drop=True), outcomes


def read_corrections(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    need = ["id", "kind", "unit_id", "unit_name", "target_id", "target_name", "reason"]
    if list(df.columns) != need:
        raise CorrectionError(f"{path}: columns must be {need}")
    if df.id.duplicated().any():
        raise CorrectionError(f"{path}: duplicated ids {sorted(df.id[df.id.duplicated()])}")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path, help="output directory of `maps-sll run`")
    ap.add_argument("corrections", type=Path)
    ap.add_argument("units_input", type=Path, help="units file of the run (for the weights)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--strict", action="store_true", help="fail on a not applicable correction")
    a = ap.parse_args()
    if a.out.resolve() == a.run.resolve():
        raise SystemExit("--out must differ from the run directory: the algorithm output stays as it is")
    t = {n: pd.read_parquet(a.run / f"{n}.parquet") for n in TABLES}
    corr = read_corrections(a.corrections)
    w = pd.read_parquet(a.units_input).set_index("id")["weight"]
    for c in corr.itertuples(index=False):  # names in the list must match the run
        for uid, uname in ((c.unit_id, c.unit_name), (c.target_id, c.target_name)):
            known = pd.concat([t["units"][["id", "name"]], t["unassigned"]])
            got = known.loc[known.id == uid, "name"]
            if not got.empty and got.iloc[0] != uname:
                raise SystemExit(f"{c.id}: {uid} is {got.iloc[0]!r} in the run, not {uname!r}")
    units, systems, unassigned, outcomes = apply_corrections(
        t["units"], t["systems"], t["unassigned"], corr, w)
    skipped = [o["id"] for o in outcomes if o["status"] == "not_applicable"]
    if skipped and a.strict:
        raise SystemExit(f"not applicable: {skipped}")
    a.out.mkdir(parents=True, exist_ok=True)
    for f in a.run.iterdir():
        if f.is_file() and f.stem not in TABLES:
            shutil.copy2(f, a.out / f.name)
    distant = units.loc[units.distant, ["id", "name", "system_id", "system_name", "minutes"]]
    for name, df in {"units": units, "systems": systems, "distant": distant.reset_index(drop=True),
                     "unassigned": unassigned}.items():
        df.to_parquet(a.out / f"{name}.parquet", index=False)
        df.to_csv(a.out / f"{name}.csv", index=False)
    summary = {
        "decision": "D18: corrections outside the algorithm, applied after every run",
        "run": str(a.run),
        "corrections_file": str(a.corrections),
        "corrections_sha256": hashlib.sha256(a.corrections.read_bytes()).hexdigest(),
        "counts": {s: sum(o["status"] == s for o in outcomes)
                   for s in ("applied", "already_satisfied", "not_applicable")},
        "n_systems": {"before": len(t["systems"]), "after": len(systems)},
        "metrics_json": "copied from the run: it describes the algorithm output, not the corrected one",
        "outcomes": outcomes,
    }
    (a.out / "corrections.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                            encoding="utf-8")
    print(json.dumps(summary["counts"]), f"systems {len(t['systems'])} → {len(systems)}")
    for o in outcomes:
        if o["status"] != "applied":
            print(f"  {o['id']} {o['status']}: {o.get('note', '')}")


if __name__ == "__main__":
    main()
