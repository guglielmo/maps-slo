"""Command line: maps-sll run | levels."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from .engine import run
from .inputs import Inputs
from .output import write_outputs
from .scenario import load_scenario


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="maps-sll")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run phases 2-4 on a scenario")
    r.add_argument("scenario")
    r.add_argument("--out", required=True)
    r.add_argument("--manifest-extra", help="JSON file copied into the manifest under 'extra'")
    lv = sub.add_parser("levels", help="phase 1: assign levels from attributes")
    lv.add_argument("rules")
    lv.add_argument("attributes")
    lv.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "run":
        started = datetime.now(UTC).isoformat(timespec="seconds")
        scenario_path = Path(args.scenario)
        scenario = load_scenario(scenario_path)
        t = perf_counter()
        inputs = Inputs.from_scenario(scenario, scenario_path.parent)
        read_s = perf_counter() - t
        result = run(scenario, inputs)
        result.timings["read_inputs"] = read_s
        extra = (
            json.loads(Path(args.manifest_extra).read_text(encoding="utf-8"))
            if args.manifest_extra
            else None
        )
        write_outputs(result, args.out, started_at=started, extra=extra)
        print(f"{scenario.name}: {result.problem.n} units, "
              f"{int(result.unassigned.sum())} unassigned, output in {args.out}")
        return 0

    from .levels import assign_levels_file

    assign_levels_file(args.rules, args.attributes, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
