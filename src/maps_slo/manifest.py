"""Run manifest (A1, "Manifesto dell'esecuzione"; criteria R5, A10, O5, O6, P2)."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from . import __version__
from .engine import Result


def _git_commit() -> str:
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=Path(__file__).parent,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        pyproject = Path(top) / "pyproject.toml"
        if not (pyproject.is_file() and 'name = "maps-slo"' in pyproject.read_text()):
            return "unknown"  # an installed copy inside some other repository
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).parent,
            capture_output=True, text=True, check=True,
        )
        commit = out.stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=Path(__file__).parent,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return commit + "+dirty" if dirty else commit
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_manifest(r: Result, *, started_at: str, extra: dict | None = None) -> dict:
    sc, p = r.scenario, r.problem
    fingerprints = r.inputs.fingerprints()
    manifest = {
        "package": "maps-slo",
        "package_version": __version__,
        "git_commit": _git_commit(),
        "scenario": sc.model_dump(mode="json"),
        "reference_year": sc.reference_year,
        "inputs": fingerprints,
        "travel_times": {
            "description": r.inputs.times_description,
            "fingerprint": fingerprints["travel_times"],
        },
        "thresholds_used": {
            "min_shared_share": sc.contiguity.min_shared_share,
            "max_minutes": sc.contiguity.max_minutes,
            "distant_minutes": sc.distant_minutes,
        },
        "counts": {
            "units": int(p.n),
            "centralities": int(p.is_centrality.sum()),
            "unassigned": int(r.unassigned.sum()),
            "unassigned_ids": [p.ids[i] for i in sorted(
                np.flatnonzero(r.unassigned).tolist(), key=lambda k: p.id_rank[k])],
            "systems": len(set(r.roots[~r.unassigned].tolist())),
        },
        "phase4_centre_changes": len(r.phase4.changed_heads),
        "phase4_ignored_claims": [
            {"claimant": p.ids[a], "claimed": p.ids[b]} for a, b in r.phase4.ignored_claims
        ],
        "timings_seconds": dict(r.timings),
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if extra:
        manifest["extra"] = extra
    return manifest
